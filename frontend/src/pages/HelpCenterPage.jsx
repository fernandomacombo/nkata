import SocialLinks from "../components/brand/SocialLinks.jsx";
import { useEffect, useMemo, useState } from "react";
import { CircleHelp, Headset, Search, ShieldCheck, ArrowLeft } from "lucide-react";

const CATEGORIES = [
  ["conta", "Conta e acesso"],
  ["identidade", "Verificação de identidade"],
  ["pagamentos", "Pagamentos e pacotes"],
  ["mensagens", "Mensagens e momentos"],
  ["seguranca", "Segurança e denúncias"],
  ["outro", "Outro assunto"],
];

const FAQ = [
  ["Como recuperar a palavra-passe?", "Na página de entrada, selecione Recuperar palavra-passe e siga as instruções enviadas para o seu email.", "conta"],
  ["Como funciona a verificação de identidade?", "Siga as instruções do NKATA ID para apresentar a frente e o verso do BI e a selfie solicitada. Nunca envie documentos pelo formulário de suporte.", "identidade"],
  ["Onde posso consultar o meu pacote?", "Inicie sessão, abra a sua conta e consulte o plano e os pagamentos associados.", "pagamentos"],
  ["Como denunciar um comportamento inadequado?", "Use a opção Denunciar no perfil ou conteúdo em questão. Se existir uma ameaça imediata, contacte também as autoridades locais.", "seguranca"],
  ["Não consigo iniciar sessão. Posso pedir ajuda?", "Sim. Pode enviar um pedido nesta página sem iniciar sessão. Indique um email a que tenha acesso.", "conta"],
];

export default function HelpCenterPage({ authenticated, email = "", onNavigate }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("conta");
  const [formEmail, setFormEmail] = useState(email);
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [tickets, setTickets] = useState([]);
  const filteredFAQ = useMemo(() => FAQ.filter(([q, a]) => (q + " " + a).toLowerCase().includes(query.toLowerCase())), [query]);

  useEffect(() => { if (email) setFormEmail(email); }, [email]);
  useEffect(() => {
    if (!authenticated) return;
    let live = true;
    fetch("/api/ajuda/pedidos/", { credentials: "same-origin" })
      .then((res) => res.ok ? res.json() : null)
      .then((data) => { if (live) setTickets(data?.results || []); })
      .catch(() => {});
    return () => { live = false; };
  }, [authenticated, success]);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setSending(true);
    try {
      const cookie = document.cookie.split("; ").find((item) => item.startsWith("csrftoken="));
      const csrf = cookie ? decodeURIComponent(cookie.slice("csrftoken=".length)) : "";
      const response = await fetch("/api/ajuda/pedidos/", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ email: formEmail, category, subject, description }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Não foi possível enviar o pedido.");
      setSuccess(`Pedido recebido. Referência: ${result.id}`);
      setSubject("");
      setDescription("");
    } catch (err) {
      setError(err.message || "Não foi possível enviar o pedido.");
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="nk-help nk-shell">
      <div className="nk-help__intro">
        <span className="nk-help__eyebrow"><CircleHelp size={17} /> Centro de Ajuda NKATA</span>
        <h1>Como podemos ajudar?</h1>
        <p>Pesquise nas perguntas frequentes ou contacte a equipa de suporte.</p>
        <label className="nk-help__search">
          <Search size={19} aria-hidden="true" />
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Pesquisar respostas..." aria-label="Pesquisar perguntas frequentes" />
        </label>
        <div className="nk-help__links">
          <a className="nk-help__contact-link" href="#contactar-suporte">Contactar suporte</a>
          <SocialLinks />
        </div>
      </div>

      <div className="nk-help__content">
        <section aria-label="Perguntas frequentes">
          <h2>Perguntas frequentes</h2>
          {filteredFAQ.length ? filteredFAQ.map(([question, answer]) => (
            <details key={question} className="nk-help__faq">
              <summary>{question}</summary>
              <p>{answer}</p>
            </details>
          )) : <p>Não encontrámos uma resposta. Envie-nos um pedido abaixo.</p>}
        </section>

        <section id="contactar-suporte" className="nk-help__form-section" aria-label="Contactar suporte">
          <h2><Headset size={21} /> Contactar suporte</h2>
          <p>Descreva o problema. Não envie palavras-passe, dados completos de cartões ou fotografias do BI.</p>
          <form onSubmit={submit} className="nk-help__form">
            {!authenticated && <label>Email para contacto<input required type="email" maxLength={254} value={formEmail} onChange={(event) => setFormEmail(event.target.value)} placeholder="nome@exemplo.com" /></label>}
            <label>Categoria<select required value={category} onChange={(event) => setCategory(event.target.value)}>{CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label>Assunto<input required minLength={5} maxLength={140} value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="Qual é o problema?" /></label>
            <label>Descrição<textarea required minLength={15} maxLength={4000} rows={5} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Explique o que aconteceu, sem incluir dados sensíveis." /></label>
            {error && <p className="nk-help__error" role="alert">{error}</p>}
            {success && <p className="nk-help__success" role="status">{success}</p>}
            <button type="submit" className="nk-help__submit" disabled={sending}>{sending ? "A enviar..." : "Enviar pedido"}</button>
          </form>
          <p className="nk-help__hint"><ShieldCheck size={16} /> Os pedidos são privados e analisados pela equipa NKATA.</p>
        </section>
      </div>

      {authenticated && <section className="nk-help__history">
        <h2>Os meus pedidos</h2>
        {tickets.length ? <ul>{tickets.map((ticket) => <li key={ticket.id}><strong>{ticket.subject}</strong><span>{ticket.status.replaceAll("_", " ")}</span><small>{ticket.id}</small>{ticket.replies?.length > 0 && <details><summary>Ver respostas ({ticket.replies.length})</summary>{ticket.replies.map((answer, index) => <p key={index} className="nk-help__reply">{answer.body}</p>)}</details>}</li>)}</ul> : <p>Ainda não existem pedidos nesta conta.</p>}
      </section>}
      <button type="button" className="nk-help__back" onClick={() => onNavigate("home")}><ArrowLeft size={17} /> Voltar ao início</button>
    </main>
  );
}
