import { useCallback, useEffect, useState } from "react";
import { Headset, RefreshCw, Send } from "lucide-react";

function csrfToken() {
  const cookie = document.cookie.split("; ").find((part) => part.startsWith("csrftoken="));
  return cookie ? decodeURIComponent(cookie.slice("csrftoken=".length)) : "";
}

export default function SupportAdminPanel() {
  const [tickets, setTickets] = useState([]);
  const [selected, setSelected] = useState("");
  const [reply, setReply] = useState("");
  const [status, setStatus] = useState("aguarda_resposta");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/ajuda/painel/pedidos/", { credentials: "same-origin" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Não foi possível carregar os pedidos.");
      setTickets(data.results || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  const ticket = tickets.find((item) => item.id === selected);

  async function submit(event) {
    event.preventDefault();
    if (!ticket || !reply.trim()) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`/api/ajuda/painel/pedidos/${ticket.id}/responder/`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify({ body: reply, status }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Falha ao enviar resposta.");
      setMessage("Resposta enviada ao endereço associado ao pedido.");
      setReply("");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return <section className="nk-admin-support">
    <header className="nk-admin-section-header">
      <div><small>Exclusivo do administrador principal</small><h2><Headset size={23} /> Ajuda e Suporte</h2><p>Pedidos privados de utilizadores e visitantes.</p></div>
      <button type="button" onClick={load} disabled={loading} aria-label="Atualizar pedidos"><RefreshCw size={19} /></button>
    </header>
    {error && <p role="alert" className="nk-help__error">{error}</p>}
    {message && <p role="status" className="nk-help__success">{message}</p>}
    <div className="nk-admin-support__grid">
      <div className="nk-admin-support__list">
        {loading && <p>A carregar...</p>}
        {!loading && !tickets.length && <p>Ainda não há pedidos.</p>}
        {tickets.map((item) => <button type="button" key={item.id} onClick={() => {setSelected(item.id);setReply("");setMessage("");setStatus("aguarda_resposta");}} className={selected === item.id ? "is-selected" : ""}>
          <strong>{item.subject}</strong><span>{item.category} · {item.status.replaceAll("_"," ")}</span><small>{new Date(item.created_at).toLocaleDateString("pt-PT")}</small>
        </button>)}
      </div>
      <div className="nk-admin-support__detail">
        {!ticket ? <p>Selecione um pedido para consultar e responder.</p> : <>
          <h3>{ticket.subject}</h3><p><strong>Categoria:</strong> {ticket.category}</p>
          <p><strong>Email:</strong> {ticket.email}</p>
          <p><strong>Estado:</strong> {ticket.status.replaceAll("_", " ")}</p>
          <p className="nk-admin-support__description">{ticket.description}</p>
          <h4>Respostas anteriores</h4>
          {ticket.replies.length ? ticket.replies.map((item, index) => <p key={index} className="nk-admin-support__previous">{item.body}</p>) : <p>Ainda sem respostas.</p>}
          <form onSubmit={submit}>
            <label>Responder<textarea required minLength={5} maxLength={4000} rows={5} value={reply} onChange={(event) => setReply(event.target.value)} /></label>
            <label>Estado após a resposta<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="aguarda_resposta">A aguardar resposta</option><option value="em_analise">Em análise</option><option value="resolvido">Resolvido</option></select></label>
            <button type="submit" disabled={busy}><Send size={17} /> {busy ? "A enviar..." : "Enviar resposta por email"}</button>
          </form>
        </>}
      </div>
    </div>
  </section>;
}
