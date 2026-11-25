import { useEffect, useRef, useState } from "react";
import { request } from "../services/api.js";
import { ChatSafetyNotice } from "./ConversationPage.jsx";
import "./chats.css";

function Thread({ id, onLegacy, safetyAccepted, onAcceptSafety, onClosed }) {
  const lastTyping = useRef(0);
  const [thread, setThread] = useState(null);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [reply, setReply] = useState(null);
  const [sending, setSending] = useState(false);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function refresh() {
      try {
        const result = await request(`/api/chats/${id}/`, { signal: controller.signal });
        if (!controller.signal.aborted) setThread(result);
      } catch (err) {
        if (!controller.signal.aborted) {
          setThread(null);
          setError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(refresh, 2500);
      }
    }
    refresh();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [id, revision]);

  function write(value) {
    setText(value);
    if (value.trim() && Date.now() - lastTyping.current > 2200) {
      lastTyping.current = Date.now();
      request(`/api/chats/${id}/escrita/`, { method: "POST" }).catch(() => {});
    }
  }

  async function close() {
    if (!window.confirm("Encerrar esta conversa? Ambos deixarão de poder enviar mensagens.")) return;
    try {
      await request(`/api/chats/${id}/encerrar/`, { method: "POST" });
      onClosed();
    } catch (err) { setError(err.message); }
  }

  async function remove(messageId) {
    try {
      await request(`/api/chats/${id}/mensagens/${messageId}/`, { method: "DELETE" });
      setRevision(value => value + 1);
    } catch (err) { setError(err.message); }
  }

  async function send(event) {
    event.preventDefault();
    if (sending || !text.trim()) return;
    setSending(true);
    setError("");
    try {
      await request(`/api/chats/${id}/`, { method: "POST", body: { texto: text.trim(), resposta_a: reply?.id } });
      setText("");
      setReply(null);
      setRevision(value => value + 1);
    } catch (err) { setError(err.message); }
    finally { setSending(false); }
  }

  return <section aria-label="Conversa">
    {error && <p role="alert">{error}</p>}
    {thread && <>
      <h2>{thread.nome}</h2>
      <button type="button" onClick={close}>Encerrar conversa</button>
      {thread.match_id && <button type="button" onClick={() => onLegacy(thread.match_id)}>Áudio, chamadas e histórico completo</button>}
      <ol className="nk-chat-lines">{thread.mensagens.map(message =>
        <li key={message.id}><strong>{message.minha ? "Eu" : thread.nome}</strong>
          {message.resposta_a && <small>Resposta a {thread.mensagens.find(m => m.id === message.resposta_a)?.texto || "mensagem indisponível"}</small>}
          <p>{message.apagada_em ? "Mensagem apagada" : message.texto}</p>
          {!message.apagada_em && thread.texto_livre && <button type="button" onClick={() => setReply(message)}>Responder</button>}
          {!message.apagada_em && message.minha && <button type="button" onClick={() => remove(message.id)}>Apagar</button>}</li>)}</ol>
      {thread.a_escrever && <p role="status">{thread.nome} está a escrever…</p>}
      <form onSubmit={send}>{reply && <p>A responder a {reply.texto} <button type="button" onClick={() => setReply(null)}>Cancelar</button></p>}
        {thread.texto_livre ? <label>Mensagem<textarea value={text} maxLength={1200} onChange={e => write(e.target.value)} /></label> : thread.frases.length ? <label>Mensagem predefinida<select value={text} onChange={e => setText(e.target.value)}>
          <option value="">Escolher mensagem</option>{thread.frases.map(phrase => <option key={phrase}>{phrase}</option>)}</select></label>
          : <p>Active um pacote com chat para responder. <a href="/conta/?section=plan">Ver pacotes</a></p>}
        <button className="nk-button nk-button--wine" disabled={sending || !text.trim()}>Enviar</button></form>
      {!safetyAccepted && <ChatSafetyNotice name={thread.nome} onAccept={onAcceptSafety} />}
    </>}
  </section>;
}

export default function ChatsPage({ conversationId, requestId, onSelect, ...threadProps }) {
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [closedId, setClosedId] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function load() {
      try {
        const options = { signal: controller.signal };
        const [next, selected] = await Promise.all([
          request("/api/chats/", options),
          requestId ? request(`/api/chats/pedidos/${requestId}/`, options) : null,
        ]);
        if (!controller.signal.aborted) setSelectedRequest(selected);
        if (!controller.signal.aborted) setData(next);
      } catch (err) {
        if (!controller.signal.aborted) setError(err.message);
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(load, 10000);
      }
    }
    load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [conversationId, requestId, revision]);

  async function decide(id, decisao) {
    setBusy(true);
    setError("");
    try {
      const result = await request(`/api/chats/pedidos/${id}/`, { method: "POST", body: { decisao } });
      if (result.conversation_id) onSelect(result.conversation_id);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); setRevision(value => value + 1); }
  }

  return <main className="nk-shell"><h1>Chats</h1>
    {error && <p role="alert">{error}</p>}
    <div className="nk-chats-layout"><aside>
      <h2>Pedidos de conversa</h2>
      {requestId && selectedRequest && selectedRequest.estado !== "PENDENTE" && <p role="status">
        Pedido de {selectedRequest.nome} · {{ACEITE: "Aceite", RECUSADO: "Recusado", EXPIRADO: "Expirado"}[selectedRequest.estado]}
        {selectedRequest.conversation_id && <button onClick={() => onSelect(selectedRequest.conversation_id)}>Abrir conversa</button>}
      </p>}
      {data?.pedidos.length === 0 && <p>Sem pedidos pendentes.</p>}
      {data?.pedidos.map(p => <div key={p.id}><strong>{p.nome}</strong>
        {p.recebido ? <div><button disabled={busy} onClick={() => decide(p.id, "ACEITE")}>Aceitar</button>
          <button disabled={busy} onClick={() => decide(p.id, "RECUSADO")}>Recusar</button></div> : <p>Pedido enviado</p>}</div>)}
      <h2>Conversas</h2>
      {data?.conversas.length === 0 && <p>Pode pedir conversa ao visitar um perfil.</p>}
      {data?.conversas.map(c => <button key={c.id} aria-current={conversationId === c.id ? "page" : undefined}
        onClick={() => onSelect(c.id)}>{c.nome}</button>)}
    </aside>
    {conversationId && conversationId !== closedId && <Thread key={conversationId} id={conversationId} {...threadProps} onClosed={() => { setClosedId(conversationId); setRevision(value => value + 1); }} />}
    </div></main>;
}
