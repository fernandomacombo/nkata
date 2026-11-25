import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Check, CheckCheck, Clock, HeartHandshake, MessageCircle, MoreVertical, Search, Send, ShieldCheck, UserRound, X } from "lucide-react";
import { request, blockProfile, reportProfile } from "../services/api.js";
import SafetyDialog from "../components/safety/SafetyDialog.jsx";
import Presence, { usePresence } from "../components/profiles/Presence.jsx";
import { ChatSafetyNotice } from "./ConversationPage.jsx";
import "./chats.css";

const STATES = { PENDENTE: "Pendente", ACEITE: "Aceite", RECUSADO: "Recusado", EXPIRADO: "Expirado", CANCELADO: "Cancelado" };
const TABS = [["all", "Todas"], ["unread", "Não lidas"], ["received", "Pedidos"], ["sent", "Enviados"], ["connections", "Conexões"]];
const stamp = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "";
  return new Intl.DateTimeFormat("pt-MZ", date.toDateString() === new Date().toDateString()
    ? { hour: "2-digit", minute: "2-digit" } : { day: "2-digit", month: "short" }).format(date);
};
function remaining(item) {
  const seconds = Math.max(0, Math.ceil((new Date(item.expira_em).getTime() - Date.now()) / 1000));
  if (!seconds) return "A expirar";
  if (seconds >= 86400) return Math.ceil(seconds / 86400) + " dias restantes";
  if (seconds >= 3600) return Math.ceil(seconds / 3600) + " h restantes";
  return Math.ceil(seconds / 60) + " min restantes";
}
function Avatar({ profile }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [profile?.foto_url]);
  return <span className="nk-chat-avatar">
    {profile?.foto_url && !failed ? <img src={profile.foto_url} alt="" loading="lazy" onError={() => setFailed(true)} /> : <UserRound size={24} aria-hidden="true" />}
    <Presence profile={profile} english={false} />
  </span>;
}
function Thread({ id, onLegacy, safetyAccepted, onAcceptSafety, onClosed, onBack, onOpenProfile }) {
  const lastTyping = useRef(0), scroll = useRef(null), lastId = useRef(null);
  const history = useRef([]), initialized = useRef(false), hasOlder = useRef(false), olderController = useRef(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const restoreScroll = useRef(null);
  const [thread, setThread] = useState(null), [text, setText] = useState(""), [error, setError] = useState("");
  const [reply, setReply] = useState(null), [sending, setSending] = useState(false), [revision, setRevision] = useState(0);
  const [menu, setMenu] = useState(false);
  const [messageMenu, setMessageMenu] = useState(null);
  const [safetyMode, setSafetyMode] = useState(""), [safetyBusy, setSafetyBusy] = useState(false), [safetyError, setSafetyError] = useState(""), [safetyStatus, setSafetyStatus] = useState("");
  async function confirmSafety({reason, details} = {}) {
    if (!thread?.perfil?.id || safetyBusy) return;
    setSafetyBusy(true); setSafetyError("");
    try {
      if (safetyMode === "report") {
        await reportProfile(thread.perfil.id, {reason, details});
        setSafetyStatus("Denúncia enviada à equipa NKATA.");
      } else if (safetyMode === "block") {
        await blockProfile(thread.perfil.id); onClosed();
      }
      setSafetyMode("");
    } catch (err) { setSafetyError(err.message); }
    finally { setSafetyBusy(false); }
  }
  const { label: presenceLabel } = usePresence(thread?.perfil?.id);
  function mergePage(result) {
    const merged = new Map(history.current.map(message => [message.id, message]));
    for (const message of result.mensagens) merged.set(message.id, message);
    const deleted = new Set(result.apagadas || []);
    history.current = Array.from(merged.values()).sort((a, b) => a.id - b.id).map(message => ({
      ...message,
      ...(deleted.has(message.id) ? { apagada_em: message.apagada_em || "deleted", texto: "" } : {}),
      ...(message.minha && message.id <= result.lidas_ate ? { lida: true } : {}),
    }));
    if (result.modo !== "depois") hasOlder.current = result.mais;
    setThread(current => ({ ...current, ...result, mensagens: history.current, mais_antigas: hasOlder.current }));
  }
  useEffect(() => {
    const controller = new AbortController();
    let timer, busy = false;
    async function refresh() {
      if (busy || controller.signal.aborted || document.hidden) return;
      busy = true;
      let delay = 2500;
      try {
        const params = new URLSearchParams({ paginado: "1" });
        if (initialized.current) {
          params.set("depois", String(history.current.at(-1)?.id || 0));
          if (history.current.length) params.set("estado_desde", String(history.current[0].id));
        }
        const result = await request(`/api/chats/${id}/?${params}`, { signal: controller.signal });
        if (!controller.signal.aborted) {
          mergePage(result);
          initialized.current = true;
          setError("");
          if (result.modo === "depois" && result.mais) delay = 0;
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          if ([401, 403, 404].includes(err.status)) {
            olderController.current?.abort(); setLoadingOlder(false);
            history.current = []; initialized.current = false; hasOlder.current = false;
            restoreScroll.current = null; lastId.current = null; setReply(null); setText("");
            setThread(null);
          }
          setError(err.message);
          delay = 5000;
        }
      } finally {
        busy = false;
        if (!controller.signal.aborted && !document.hidden) timer = setTimeout(refresh, delay);
      }
    }
    function visibility() {
      clearTimeout(timer);
      if (!document.hidden) refresh();
    }
    refresh();
    document.addEventListener("visibilitychange", visibility);
    return () => { controller.abort(); clearTimeout(timer); document.removeEventListener("visibilitychange", visibility); };
  }, [id, revision]);
  useEffect(() => () => olderController.current?.abort(), [id]);
  async function loadOlder() {
    if (loadingOlder || !history.current.length || !hasOlder.current) return;
    const controller = new AbortController();
    olderController.current = controller;
    setLoadingOlder(true);
    try {
      const first = history.current[0].id;
      const params = new URLSearchParams({ paginado: "1", antes: String(first), estado_desde: String(first) });
      const result = await request(`/api/chats/${id}/?${params}`, { signal: controller.signal });
      if (controller.signal.aborted || !initialized.current) return;
      // Never allow an old page to overwrite state already received via polling.
      result.mensagens = result.mensagens.filter(message => !history.current.some(current => current.id === message.id));
      if (scroll.current) restoreScroll.current = { top: scroll.current.scrollTop, height: scroll.current.scrollHeight };
      mergePage(result);
    } catch (err) {
      if (!controller.signal.aborted) {
        if ([401, 403, 404].includes(err.status)) {
          history.current = []; initialized.current = false; hasOlder.current = false;
          restoreScroll.current = null; lastId.current = null; setReply(null); setText(""); setThread(null);
          setRevision(v => v + 1);
        }
        setError(err.message);
      }
    } finally {
      if (!controller.signal.aborted) setLoadingOlder(false);
    }
  }
  useEffect(() => {
    const latest = thread?.mensagens?.at(-1)?.id;
    const el = scroll.current;
    if (el && restoreScroll.current) {
      el.scrollTop = restoreScroll.current.top + el.scrollHeight - restoreScroll.current.height;
      restoreScroll.current = null;
    } else if (el && latest !== lastId.current) {
      const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 180;
      if (lastId.current === null || nearBottom || thread?.mensagens?.at(-1)?.minha) el.scrollTop = el.scrollHeight;
      lastId.current = latest ?? null;
    }
  }, [thread]);
  function write(value) {
    setText(value);
    if (value.trim() && Date.now() - lastTyping.current > 2200) {
      lastTyping.current = Date.now();
      request(`/api/chats/${id}/escrita/`, { method: "POST" }).catch(() => {});
    }
  }
  async function close() {
    setMenu(false);
    if (!window.confirm("Encerrar esta conversa? Ambos deixarão de poder enviar mensagens.")) return;
    try { await request(`/api/chats/${id}/encerrar/`, { method: "POST" }); onClosed(); }
    catch (err) { setError(err.message); }
  }
  async function remove(messageId) {
    if (!window.confirm("Apagar esta mensagem?")) return;
    try { await request(`/api/chats/${id}/mensagens/${messageId}/`, { method: "DELETE" }); setRevision(v => v + 1); }
    catch (err) { setError(err.message); }
  }
  async function send(event) {
    event.preventDefault();
    if (sending || !text.trim() || !safetyAccepted) return;
    setSending(true); setError("");
    try {
      await request(`/api/chats/${id}/`, { method: "POST", body: { texto: text.trim(), resposta_a: reply?.id } });
      setText(""); setReply(null); setRevision(v => v + 1);
    } catch (err) { setError(err.message); }
    finally { setSending(false); }
  }
  return <section className="nk-chat-thread" aria-label="Conversa">
    <header className="nk-chat-thread-head">
      <button className="nk-chat-icon nk-chat-back" type="button" onClick={onBack} aria-label="Voltar aos chats"><ArrowLeft size={22} /></button>
      {thread && <><Avatar profile={thread.perfil} /><div className="nk-chat-title"><strong>{thread.nome}</strong><small>{thread.a_escrever ? "A escrever..." : presenceLabel || "Conversa privada"}</small></div>
        <div className="nk-chat-menu-wrap"><button className="nk-chat-icon" aria-label="Opções da conversa" aria-expanded={menu} type="button" onClick={() => setMenu(!menu)}><MoreVertical size={22} /></button>
          {menu && <div className="nk-chat-menu">
            {thread.perfil && <button type="button" onClick={() => { setMenu(false); onOpenProfile(thread.perfil); }}>Ver perfil</button>}
            {thread.match_id && <button type="button" onClick={() => onLegacy(thread.match_id)}>Áudio, chamadas e histórico</button>}
            <button type="button" onClick={() => { setMenu(false); setSafetyMode("help"); }}>Golpes e ameaças</button>
            <button type="button" onClick={() => { setMenu(false); setSafetyError(""); setSafetyMode("report"); }}>Denunciar perfil</button>
            <button type="button" onClick={() => { setMenu(false); setSafetyError(""); setSafetyMode("block"); }}>Bloquear pessoa</button>
            <button type="button" onClick={close}>Encerrar conversa</button>
          </div>}
        </div></>}
    </header>
    {error && <p className="nk-chat-error" role="alert">{error}</p>}
    {safetyStatus && <p className="nk-chat-placeholder" role="status">{safetyStatus}</p>}
    {!thread && !error && <p className="nk-chat-placeholder">A carregar conversa...</p>}
    {thread && <>
      <ol className="nk-chat-lines" ref={scroll}>
        {thread.mais_antigas && <li className="nk-chat-load-older"><button type="button" disabled={loadingOlder} onClick={loadOlder}>{loadingOlder ? "A carregar..." : "Carregar mensagens anteriores"}</button></li>}
        {!thread.mensagens.length && <li className="nk-chat-empty-thread"><ShieldCheck size={24} /><strong>Conversa aceite</strong><span>Comece a conhecer esta pessoa, com respeito e segurança.</span></li>}
        {thread.mensagens.map(message => <li key={message.id} className={message.minha ? "nk-chat-bubble-row is-mine" : "nk-chat-bubble-row"}>
          <div className="nk-chat-bubble">
            {message.resposta_a && <blockquote>{thread.mensagens.find(m => m.id === message.resposta_a)?.texto || "Mensagem anterior ou indisponível"}</blockquote>}
            <p>{message.apagada_em ? "Mensagem apagada" : message.texto}</p>
            <div className="nk-chat-meta"><time dateTime={message.criado_em}>{stamp(message.criado_em)}</time>
              {message.minha && (message.lida ? <CheckCheck size={14} aria-label="Lida" /> : <Check size={14} aria-label="Enviada" />)}</div>
            
          </div>
          {!message.apagada_em && (thread.texto_livre || message.minha) && <div className="nk-chat-action-wrap">
            <button type="button" className="nk-chat-message-trigger" aria-label="Opções da mensagem" aria-expanded={messageMenu === message.id} onClick={() => setMessageMenu(v => v === message.id ? null : message.id)}><MoreVertical size={17}/></button>
            {messageMenu === message.id && <div className="nk-chat-message-menu">
              {thread.texto_livre && <button type="button" onClick={() => { setReply(message); setMessageMenu(null); }}>Responder</button>}
              {message.minha && <button type="button" onClick={() => { setMessageMenu(null); remove(message.id); }}>Apagar</button>}
            </div>}
          </div>}
        </li>)}
      </ol>
      {thread.a_escrever && <p className="nk-chat-typing" role="status">{thread.nome} está a escrever...</p>}
      <form className="nk-chat-compose" onSubmit={send}>
        {reply && <div className="nk-independent-chat-reply"><span>A responder a: {reply.texto}</span><button className="nk-chat-icon" type="button" aria-label="Cancelar resposta" onClick={() => setReply(null)}><X size={18} /></button></div>}
        {thread.texto_livre || thread.frases.length ? <div className="nk-chat-compose-line">
          {thread.texto_livre ? <textarea aria-label="Mensagem" placeholder="Escrever mensagem..." rows={1} value={text} maxLength={1200} onChange={e => write(e.target.value)} /> :
            <select aria-label="Mensagem predefinida" value={text} onChange={e => setText(e.target.value)}><option value="">Escolher mensagem</option>{thread.frases.map(phrase => <option key={phrase}>{phrase}</option>)}</select>}
          <button type="submit" className="nk-chat-send" aria-label="Enviar mensagem" disabled={sending || !text.trim() || !safetyAccepted}><Send size={20} /></button>
        </div> : <p>Active um pacote com chat para responder. <a href="/conta/?section=plan">Ver pacotes</a></p>}
      </form>
      {(!safetyAccepted || safetyMode === "help") && <ChatSafetyNotice name={thread.nome} helpOnly={safetyMode === "help"} onAccept={safetyMode === "help" ? async () => setSafetyMode("") : onAcceptSafety} onExit={safetyMode === "help" ? () => setSafetyMode("") : onBack} />}
      <SafetyDialog open={["report", "block"].includes(safetyMode)} mode={safetyMode} personName={thread.nome} loading={safetyBusy} error={safetyError} onClose={() => setSafetyMode("")} onConfirm={confirmSafety} />
    </>}
  </section>;
}
function RequestRow({ item, busy, decide, cancel, onSelect, onOpenProfile }) {
  return <article className="nk-chat-request">
    <div className="nk-chat-row"><Avatar profile={item.perfil} /><div className="nk-chat-title">
      <button className="nk-chat-name" type="button" onClick={() => onOpenProfile(item.perfil)}>{item.nome}</button>
      <small>{item.estado === "PENDENTE" ? (item.recebido ? "Pedido recebido" : "A aguardar resposta") : STATES[item.estado]}</small>
      {item.estado === "PENDENTE" && <small className="nk-chat-expiry"><Clock size={13} />{remaining(item)}</small>}
    </div></div>
    {item.estado === "PENDENTE" ? <div className="nk-chat-request-actions">
      {item.recebido ? <><button className="nk-chat-primary" disabled={busy} onClick={() => decide(item.id, "ACEITE")}>Aceitar</button><button disabled={busy} onClick={() => decide(item.id, "RECUSADO")}>Recusar</button></> :
        <button disabled={busy} onClick={() => cancel(item.id)}>Cancelar pedido</button>}
    </div> : item.conversation_id && <button type="button" onClick={() => onSelect(item.conversation_id)}>Abrir conversa</button>}
  </article>;
}
export default function ChatsPage({ conversationId, requestId, onSelect, onBack, onOpenProfile, onDiscover, ...threadProps }) {
  const [data, setData] = useState(null), [error, setError] = useState(""), [busy, setBusy] = useState(false), [revision, setRevision] = useState(0);
  const [tab, setTab] = useState("all"), [query, setQuery] = useState(""), [selectedRequest, setSelectedRequest] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function load() {
      if (document.hidden) { timer = setTimeout(load, 10000); return; }
      try {
        const options = { signal: controller.signal };
        const next = await request("/api/chats/", options);
        if (controller.signal.aborted) return;
        setData(next);
        if (requestId) {
          try {
            const item = await request(`/api/chats/pedidos/${requestId}/`, options);
            if (!controller.signal.aborted) setSelectedRequest(item);
          } catch (err) { if (!controller.signal.aborted) { setSelectedRequest(null); setError(err.message); } }
        } else setSelectedRequest(null);
      } catch (err) { if (!controller.signal.aborted) setError(err.message); }
      finally { if (!controller.signal.aborted) timer = setTimeout(load, 10000); }
    }
    load(); return () => { controller.abort(); clearTimeout(timer); };
  }, [conversationId, requestId, revision]);
  useEffect(() => {
    if (requestId && selectedRequest?.id === requestId) setTab(selectedRequest.recebido ? "received" : "sent");
  }, [requestId, selectedRequest?.id, selectedRequest?.recebido]);
  async function decide(id, decisao) {
    setBusy(true); setError("");
    try { const result = await request(`/api/chats/pedidos/${id}/`, { method: "POST", body: { decisao } }); if (result.conversation_id) { setTab("all"); setQuery(""); onSelect(result.conversation_id); } }
    catch (err) { setError(err.message); }
    finally { setBusy(false); setRevision(v => v + 1); }
  }
  async function cancel(id) {
    if (!window.confirm("Cancelar este pedido de conversa?")) return;
    setBusy(true); setError("");
    try { await request(`/api/chats/pedidos/${id}/cancelar/`, { method: "POST" }); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); setRevision(v => v + 1); }
  }
  const normalize = value => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const matches = name => normalize(name).includes(normalize(query.trim()));
  const chats = data?.conversas || [], requests = data?.pedidos || [], history = data?.historico_pedidos || [];
  const visibleChats = chats.filter(c => matches(c.nome) && (tab !== "unread" || c.nao_lidas > 0));
  const received = requests.filter(p => p.recebido), sent = requests.filter(p => !p.recebido);
  const counts = { unread: chats.filter(c => c.nao_lidas > 0).length, received: received.length, sent: sent.length };
  const visibleRequests = (tab === "received" ? received : sent).filter(p => matches(p.nome));
  const visibleHistory = history.filter(p => p.recebido === (tab === "received") && matches(p.nome));
  const connections = (data?.conexoes || []).filter(c => matches(c.nome));
  function chooseTab(key) { setTab(key); if (requestId || (conversationId && key !== "all" && key !== "unread")) onBack(); }
  const showChats = tab === "all" || tab === "unread";
  return <main className="nk-shell nk-chats-page">
    <div className={"nk-chats-layout" + (conversationId ? " has-thread" : "")}>
      <aside className="nk-chat-sidebar" aria-label="Lista de chats">
        <div className="nk-chat-sidebar-head"><div><h1>Chats</h1><p>As suas conversas e conexões</p></div><button type="button" className="nk-chat-icon" aria-label="Explorar perfis" onClick={onDiscover}><MessageCircle size={23} /></button></div>
        <label className="nk-chat-search"><Search size={18} /><input aria-label="Pesquisar chats" placeholder="Pesquisar por nome" value={query} onChange={e => setQuery(e.target.value)} />{query && <button className="nk-chat-icon" type="button" aria-label="Limpar pesquisa" onClick={() => setQuery("")}><X size={16} /></button>}</label>
        <nav className="nk-chat-tabs" aria-label="Filtrar chats">{TABS.map(([key,label]) => <button type="button" key={key} aria-pressed={tab === key} onClick={() => chooseTab(key)}>{label}{counts[key] > 0 && <span>{counts[key]}</span>}</button>)}</nav>
        {error && <p role="alert" className="nk-chat-error">{error}</p>}
        <div className="nk-chat-list">
          {!data && !error && <p className="nk-chat-placeholder">A carregar...</p>}
          {data && showChats && <>{visibleChats.map(c => <button type="button" className="nk-chat-row nk-chat-conversation" key={c.id} aria-current={conversationId === c.id ? "page" : undefined} onClick={() => onSelect(c.id)}>
            <Avatar profile={c.perfil} /><span className="nk-chat-title"><strong>{c.nome}</strong><small>{c.ultima_mensagem ? (c.ultima_mensagem.minha ? "Eu: " : "") + c.ultima_mensagem.texto : "Conversa aceite"}</small></span>
            <span className="nk-chat-row-meta"><time>{stamp(c.atividade_em)}</time>{c.nao_lidas > 0 && <span className="nk-chat-unread">{c.nao_lidas > 99 ? "99+" : c.nao_lidas}</span>}</span>
          </button>)}{!visibleChats.length && <p className="nk-chat-placeholder">{query ? "Nenhum resultado." : tab === "unread" ? "Está em dia com as mensagens." : "Ainda não tem conversas. Explore os perfis para começar."}</p>}</>}
          {data && (tab === "received" || tab === "sent") && <>
            {selectedRequest && selectedRequest.id === requestId && !visibleRequests.some(p => p.id === requestId) && !visibleHistory.some(p => p.id === requestId) && <RequestRow item={selectedRequest} {...{busy, decide, cancel, onSelect, onOpenProfile}} />}
            {visibleRequests.map(p => <RequestRow key={p.id} item={p} {...{busy, decide, cancel, onSelect, onOpenProfile}} />)}
            {!visibleRequests.length && <p className="nk-chat-placeholder">{query ? "Nenhum resultado." : "Sem pedidos pendentes."}</p>}
            {!!visibleHistory.length && <details className="nk-chat-history"><summary>Histórico de pedidos</summary>{visibleHistory.map(p => <RequestRow key={p.id} item={p} {...{busy, decide, cancel, onSelect, onOpenProfile}} />)}</details>}
          </>}
          {data && tab === "connections" && <>{connections.map(c => <button type="button" className="nk-chat-row nk-chat-conversation" key={c.perfil.id} onClick={() => onOpenProfile(c.perfil)}><Avatar profile={c.perfil} /><span className="nk-chat-title"><strong>{c.nome}</strong><small>{c.tipos.join(" · ")}</small></span><HeartHandshake size={18} /></button>)}{!connections.length && <p className="nk-chat-placeholder">{query ? "Nenhum resultado." : "Os seus matches e sinais aparecem aqui."}</p>}</>}
        </div>
      </aside>
      {conversationId ? <Thread key={conversationId} id={conversationId} {...threadProps} onBack={onBack} onOpenProfile={onOpenProfile} onClosed={() => { onBack(); setRevision(v => v + 1); }} /> :
        <section className="nk-chat-empty-panel"><MessageCircle size={46} strokeWidth={1.4} /><h2>Uma boa conversa começa aqui</h2><p>Escolha uma conversa ou conheça alguém novo.</p><button className="nk-chat-primary" onClick={onDiscover}>Explorar perfis</button></section>}
    </div>
  </main>;
}
