import { Fragment, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowLeft, Check, CheckCheck, Clock, Flower2, Hand, Heart, HeartHandshake, MessageCircle, MoreVertical, Reply, Search, Send, ShieldCheck, Sparkles, Trash2, UserRound, X, Plus, WalletCards, LockKeyhole } from "lucide-react";
import { request, blockProfile, reportProfile } from "../services/api.js";
import SafetyDialog from "../components/safety/SafetyDialog.jsx";
import { usePresence } from "../components/profiles/Presence.jsx";
import { ChatSafetyNotice } from "./ConversationPage.jsx";
import "./chats.css";
import VoiceRecorder from "../components/chat/VoiceRecorder.jsx";
import PrivateVoicePlayer from "../components/chat/PrivateVoicePlayer.jsx";
import CallPanel, { CallActions } from "../components/chat/CallPanel.jsx";
import useNativeCalls from "../components/chat/useNativeCalls.js";
import useNativeCallConfig from "../components/chat/useNativeCallConfig.js";

const SIGNAL_ICONS = {OLA:Hand,FLOR:Flower2,BEIJINHO:Heart};
function SignalIcon({type,size=24}) { const Icon=SIGNAL_ICONS[type] || Sparkles; return <Icon size={size} strokeWidth={1.6} aria-hidden="true"/>; }
const STATES = { PENDENTE: "Pendente", ACEITE: "Aceite", RECUSADO: "Recusado", EXPIRADO: "Expirado", CANCELADO: "Cancelado" };
const TABS = [["all", "Todas"], ["unread", "Não lidas"], ["received", "Pedidos"], ["sent", "Enviados"], ["connections", "Conexões"]];
const stamp = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "";
  return new Intl.DateTimeFormat("pt-MZ", date.toDateString() === new Date().toDateString()
    ? { hour: "2-digit", minute: "2-digit" } : { day: "2-digit", month: "short" }).format(date);
};
const messageTime = value => {
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat("pt-MZ", {hour:"2-digit",minute:"2-digit"}).format(date) : "";
};
const dayKey = value => new Date(value).toDateString();
function dayLabel(value) {
  const date = new Date(value), today = new Date(), yesterday = new Date();
  yesterday.setDate(today.getDate()-1);
  if (dayKey(value) === today.toDateString()) return "Hoje";
  if (dayKey(value) === yesterday.toDateString()) return "Ontem";
  return Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat("pt-MZ", {day:"numeric",month:"long",...(date.getFullYear() !== today.getFullYear() ? {year:"numeric"} : {})}).format(date) : "";
}
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
  const { online, label } = usePresence(profile?.id);
  return <span className="nk-chat-avatar">
    <span className="nk-chat-avatar-photo">
      {profile?.foto_url && !failed ? <img src={profile.foto_url} alt="" loading="lazy" onError={() => setFailed(true)} /> : <UserRound size={24} aria-hidden="true" />}
    </span>
    {profile?.id && <span data-presence-id={profile.id} className={"nk-chat-avatar-dot" + (online ? " is-online" : "")}
      role={label ? "img" : undefined} aria-label={label || undefined} title={label || undefined} />}
  </span>;
}
function Thread({ id, onLegacy, safetyAccepted, onAcceptSafety, onClosed, onBack, onOpenProfile, onVerifyIdentity, callController }) {
  const lastTyping = useRef(0), scroll = useRef(null), lastId = useRef(null);
  const history = useRef([]), initialized = useRef(false), hasOlder = useRef(false), olderController = useRef(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const restoreScroll = useRef(null);
  const [thread, setThread] = useState(null), [text, setText] = useState(""), [error, setError] = useState("");
  const [reply, setReply] = useState(null), [sending, setSending] = useState(false), [revision, setRevision] = useState(0);
  const [loadError, setLoadError] = useState("");
  const [menu, setMenu] = useState(false);
  const [messageMenu, setMessageMenu] = useState(null);
  const [voiceActive,setVoiceActive] = useState(false);
  const [extrasOpen, setExtrasOpen] = useState(false), [extraBusy, setExtraBusy] = useState(false);
  const extrasRef = useRef(null), extrasTrigger = useRef(null);
  useEffect(() => {
    if (!extrasOpen) return;
    function dismiss(event) { if (!extrasRef.current?.contains(event.target) && !extrasTrigger.current?.contains(event.target)) setExtrasOpen(false); }
    function key(event) { if (event.key === "Escape") { setExtrasOpen(false); extrasTrigger.current?.focus(); } }
    document.addEventListener("pointerdown", dismiss); document.addEventListener("keydown", key);
    return () => { document.removeEventListener("pointerdown", dismiss); document.removeEventListener("keydown", key); };
  }, [extrasOpen]);
  async function sendExtra(kind, body) {
    if (extraBusy || !safetyAccepted) return;
    setExtraBusy(true); setError("");
    try { await request(`/api/chats/${id}/${kind}/`, {method:"POST", body}); setExtrasOpen(false); setRevision(v => v+1); }
    catch(err) { setError(err.message); }
    finally { setExtraBusy(false); }
  }
  function sendSignal(item) {
    sendExtra("sinais", {tipo:item.type, expected_cost:item.cost});
  }
  async function buyText() {
    const offer = thread?.credito_chat;
    if (!offer?.can_unlock || extraBusy || !safetyAccepted || offer.balance < offer.cost) return;
    await sendExtra("desbloquear", {key:crypto.randomUUID(), expected_cost:offer.cost});
  }
  const messageMenuRef = useRef(null), composerRef = useRef(null);
  const messageAnchor = useRef(null), nearEnd = useRef(true);
  useEffect(() => {
    if (!messageMenu) return;
    const dismiss = event => { if (!messageMenuRef.current?.contains(event.target) && !messageAnchor.current?.contains(event.target)) setMessageMenu(null); };
    const keyboard = event => { if (event.key === "Escape") { setMessageMenu(null); messageAnchor.current?.focus(); } };
    const closeMenu = () => setMessageMenu(null);
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", keyboard);
    window.addEventListener("resize", closeMenu);
    window.addEventListener("scroll", closeMenu, true);
    return () => { document.removeEventListener("pointerdown", dismiss); document.removeEventListener("keydown", keyboard); window.removeEventListener("resize", closeMenu); window.removeEventListener("scroll", closeMenu, true); };
  }, [messageMenu]);
  function openMessageMenu(event, message) {
    if (messageMenu?.id === message.id) { setMessageMenu(null); return; }
    const anchor = event.currentTarget;
    messageAnchor.current = anchor;
    const rect = anchor.getBoundingClientRect(), height = message.minha && thread.texto_livre ? 96 : 52, width = Math.min(176, window.innerWidth - 16);
    setMessageMenu({id:message.id, left:Math.max(8, Math.min(rect.left, window.innerWidth-width-8)), top:Math.max(8, rect.bottom+height+8>window.innerHeight ? rect.top-height-4 : rect.bottom+4), width});
  }
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
          setLoadError("");
          if (result.modo === "depois" && result.mais) delay = 0;
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          if ([401, 403, 404].includes(err.status)) {
            olderController.current?.abort(); setLoadingOlder(false);
            history.current = []; initialized.current = false; hasOlder.current = false;
            restoreScroll.current = null; lastId.current = null; setReply(null); setText(""); setExtrasOpen(false); setVoiceActive(false);
            setThread(null);
          }
          setLoadError(err.message);
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
          restoreScroll.current = null; lastId.current = null; setReply(null); setText(""); setExtrasOpen(false); setThread(null);
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
      if (lastId.current === null || nearEnd.current || thread?.mensagens?.at(-1)?.minha) el.scrollTop = el.scrollHeight;
      lastId.current = latest ?? null;
    }
  }, [thread]);
  useEffect(() => {
    if (!thread?.credito_voz?.enabled || !safetyAccepted) setVoiceActive(false);
  }, [thread?.credito_voz?.enabled, safetyAccepted]);
  useEffect(() => {
    if (thread && !thread.texto_livre) {
      setReply(null);
      setText(value => thread.frases.includes(value) ? value : "");
    }
  }, [thread?.texto_livre]);
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
    if (sending || voiceActive || thread?.read_only || !text.trim() || !safetyAccepted) return;
    setSending(true); setError("");
    try {
      const submittedText = text, submittedReply = reply;
      await request(`/api/chats/${id}/`, { method: "POST", body: { texto: submittedText.trim(), resposta_a: submittedReply?.id } });
      // Do not discard a new draft typed while the previous request was in flight.
      setText(current => current === submittedText ? "" : current);
      setReply(current => current === submittedReply ? null : current);
      setRevision(v => v + 1);
    } catch (err) { setError(err.message); }
    finally { setSending(false); }
  }
  return <section className="nk-chat-thread" aria-label="Conversa">
    <header className="nk-chat-thread-head">
      <button className="nk-chat-icon nk-chat-back" type="button" onClick={onBack} aria-label="Voltar aos chats"><ArrowLeft size={22} /></button>
      {thread && <><Avatar profile={thread.perfil} /><div className="nk-chat-title"><strong>{thread.nome}</strong><small>{thread.a_escrever ? "A escrever..." : presenceLabel || "Conversa privada"}</small></div>
        <CallActions enabled={callController?.enabled === true && typeof callController.start === "function"} disabled={!safetyAccepted || voiceActive || !!callController?.call} onStart={kind => callController.start(id,kind)}/>
        <div className="nk-chat-menu-wrap"><button className="nk-chat-icon" aria-label="Opções da conversa" aria-expanded={menu} type="button" onClick={() => setMenu(!menu)}><MoreVertical size={22} /></button>
          {menu && <div className="nk-chat-menu">
            {thread.perfil && <button type="button" onClick={() => { setMenu(false); onOpenProfile(thread.perfil); }}>Ver perfil</button>}
            {thread.match_id && <button type="button" onClick={() => onLegacy(thread.match_id)}>Histórico da conversa</button>}
            <button type="button" onClick={() => { setMenu(false); setSafetyMode("help"); }}>Golpes e ameaças</button>
            <button type="button" onClick={() => { setMenu(false); setSafetyError(""); setSafetyMode("report"); }}>Denunciar perfil</button>
            <button type="button" onClick={() => { setMenu(false); setSafetyError(""); setSafetyMode("block"); }}>Bloquear pessoa</button>
            <button type="button" onClick={close}>Encerrar conversa</button>
          </div>}
        </div></>}
    </header>
    {loadError && <p className="nk-chat-error" role="alert">{loadError}</p>}
    {error && <p className="nk-chat-error" role="alert">{error} <button type="button" aria-label="Fechar aviso" onClick={()=>setError("")}>×</button></p>}
    {safetyStatus && <p className="nk-chat-placeholder" role="status">{safetyStatus}</p>}
    {!thread && !loadError && !error && <p className="nk-chat-placeholder">A carregar conversa...</p>}
    {thread && <>
      <ol className="nk-chat-lines" ref={scroll} onScroll={e => { const el=e.currentTarget; nearEnd.current=el.scrollHeight-el.scrollTop-el.clientHeight<150; }}>
        {thread.mais_antigas && <li className="nk-chat-load-older"><button type="button" disabled={loadingOlder} onClick={loadOlder}>{loadingOlder ? "A carregar..." : "Carregar mensagens anteriores"}</button></li>}
        {!thread.mensagens.length && <li className="nk-chat-empty-thread"><ShieldCheck size={24} /><strong>{thread.consent_state === "ACEITE" ? "Conversa aceite" : "Conversa anterior"}</strong><span>Comece a conhecer esta pessoa, com respeito e segurança.</span></li>}
        {thread.mensagens.map((message,index) => <Fragment key={message.id}>
          {(index === 0 || dayKey(thread.mensagens[index-1].criado_em) !== dayKey(message.criado_em)) && <li className="nk-chat-day"><time>{dayLabel(message.criado_em)}</time></li>}
          <li className={"nk-chat-bubble-row" + (message.minha ? " is-mine" : "") + (index > 0 && thread.mensagens[index-1].minha === message.minha && dayKey(thread.mensagens[index-1].criado_em) === dayKey(message.criado_em) ? " is-grouped" : "")}>
          <div className="nk-chat-bubble">
            {message.resposta_a && <blockquote>{thread.mensagens.find(m => m.id === message.resposta_a)?.texto || "Mensagem anterior ou indisponível"}</blockquote>}
            {!message.apagada_em && message.tipo === "SINAL" && <span className="nk-chat-signal-art" aria-hidden="true"><SignalIcon type={message.sinal} size={28}/></span>}
            {!message.apagada_em && message.tipo === "QUEBRA_GELO" && <span className="nk-chat-extra-label"><Sparkles size={13}/>Quebra-gelo</span>}
            {!message.apagada_em && message.tipo === "AUDIO" && message.audio_url ? <PrivateVoicePlayer src={message.audio_url} duration={message.duracao_segundos}/> : <p className={message.apagada_em ? "nk-chat-deleted" : undefined}>{message.apagada_em ? "Mensagem apagada" : message.texto}</p>}
            <div className="nk-chat-meta"><time dateTime={message.criado_em}>{messageTime(message.criado_em)}</time>
              {message.minha && (message.lida ? <CheckCheck size={14} aria-label="Lida" /> : <Check size={14} aria-label="Enviada" />)}</div>
            
          </div>
          {!message.apagada_em && (thread.texto_livre || message.minha) && <div className="nk-chat-action-wrap">
            <button type="button" className="nk-chat-message-trigger" aria-label="Opções da mensagem" aria-expanded={messageMenu?.id === message.id} onClick={event => openMessageMenu(event,message)}><MoreVertical size={17}/></button>
            {messageMenu?.id === message.id && createPortal(<div ref={messageMenuRef} className="nk-chat-floating-actions" style={{left:messageMenu.left,top:messageMenu.top,width:messageMenu.width}}>
              {thread.texto_livre && <button type="button" onClick={() => { setReply(message); setMessageMenu(null); composerRef.current?.focus(); }}><Reply size={16}/>Responder</button>}
              {message.minha && <button type="button" className="is-danger" onClick={() => { setMessageMenu(null); remove(message.id); }}><Trash2 size={16}/>Apagar</button>}
            </div>,document.body)}
          </div>}
        </li></Fragment>)}
      </ol>
      {thread.read_only ? <div className="nk-chat-compose"><p><LockKeyhole size={16}/> Pode ler as mensagens. Verifique a sua identidade para responder.</p><button type="button" className="nk-chat-primary" onClick={onVerifyIdentity}>Verificar identidade</button></div> : <form className="nk-chat-compose" onSubmit={send}>
        {extrasOpen && <section ref={extrasRef} id="nk-chat-extras-panel" className="nk-chat-extras nk-chat-extras--popover" aria-label="Acções da conversa">
          <div className="nk-chat-extras-title"><strong>Acções da conversa</strong><button className="nk-chat-icon" type="button" aria-label="Fechar acções" onClick={() => {setExtrasOpen(false);extrasTrigger.current?.focus();}}><X size={18}/></button></div>
          {thread.sinais?.quota?.credit_mode && <a className="nk-chat-wallet-link" href="/conta/?section=plan"><WalletCards size={17}/><span>Carteira · {thread.sinais.quota.credit_balance} créditos</span></a>}
          {thread.credito_chat?.expires_at && <small>Texto livre até {new Date(thread.credito_chat.expires_at).toLocaleString("pt-MZ")}</small>}
          {!thread.texto_livre && <small>{thread.predefinidas?.restantes ?? 0} mensagens gratuitas restantes hoje</small>}
          {!thread.texto_livre && thread.credito_chat?.can_unlock && thread.credito_chat.balance >= thread.credito_chat.cost && <button type="button" className="nk-chat-unlock" disabled={extraBusy || !safetyAccepted} onClick={buyText}><LockKeyhole size={16}/>Texto livre 24 h · {thread.credito_chat.cost} créditos</button>}
          {!thread.texto_livre && (!thread.credito_chat?.can_unlock || thread.credito_chat.balance < thread.credito_chat.cost) && <a className="nk-chat-wallet-link" href="/conta/?section=plan"><LockKeyhole size={16}/> Carteira</a>}
          {!!thread.sinais?.signals?.length && <><strong>Sinais</strong>{!thread.sinais.quota?.credit_mode && <small>{thread.sinais.quota?.remaining_today ?? 0} disponíveis hoje</small>}<div className="nk-chat-signal-buttons">{thread.sinais.signals.map(item => <button type="button" key={item.type} disabled={extraBusy || item.available === false || item.sent_to_profile_today || thread.sinais.quota?.limit_reached || !safetyAccepted} onClick={() => sendSignal(item)}><span><SignalIcon type={item.type}/></span>{item.label}{thread.sinais.quota?.credit_mode && <small>{item.cost ? `${item.cost} crédito${item.cost === 1 ? "" : "s"}` : "Incluído"}</small>}</button>)}</div></>}
          <strong>Quebra-gelo · {thread.quebra_gelo?.restantes ?? 0} restantes</strong>
          {thread.quebra_gelo?.perguntas?.map(item => <button className="nk-chat-icebreaker" type="button" key={item.codigo} disabled={extraBusy || !thread.quebra_gelo.restantes || !safetyAccepted} onClick={() => sendExtra("quebra-gelo", {codigo:item.codigo})}>{item.texto}<Send size={15}/></button>)}
        </section>}
        {reply && <div className="nk-independent-chat-reply"><span>A responder a: {reply.texto}</span><button className="nk-chat-icon" type="button" aria-label="Cancelar resposta" onClick={() => setReply(null)}><X size={18} /></button></div>}
        <div className="nk-chat-compose-line">
          {!voiceActive && <>
          <button ref={extrasTrigger} className="nk-chat-icon nk-chat-plus" type="button" aria-label="Acções da conversa" aria-expanded={extrasOpen} aria-controls={extrasOpen ? "nk-chat-extras-panel" : undefined} onClick={() => setExtrasOpen(v => !v)} disabled={!safetyAccepted}>{extrasOpen?<X size={22}/>:<Plus size={22}/>}</button>
          {thread.texto_livre ? <textarea ref={composerRef} aria-label="Mensagem" placeholder="Escrever mensagem..." rows={1} value={text} maxLength={1200} onChange={e => write(e.target.value)} /> :
            thread.frases.length ? <select aria-label="Mensagem predefinida" value={text} onChange={e => setText(e.target.value)}><option value="">Escolher mensagem</option>{thread.frases.map(phrase => <option key={phrase}>{phrase}</option>)}</select> :
            <span className="nk-chat-compose-locked">Texto bloqueado</span>}
          {thread.texto_livre || thread.frases.length ? <button type="submit" className="nk-chat-send" aria-label="Enviar mensagem" disabled={sending || !text.trim() || !safetyAccepted || (!thread.texto_livre && !thread.frases.includes(text))}><Send size={20} /></button> : null}
          {!thread.texto_livre && <button type="button" className="nk-chat-icon nk-chat-unlock-short" aria-label="Opções para desbloquear texto livre" title="Desbloquear texto livre" disabled={!safetyAccepted} onClick={() => setExtrasOpen(true)}><LockKeyhole size={18}/></button>}
          </>}
          {thread.credito_voz?.enabled && safetyAccepted && <VoiceRecorder key={id} conversationId={id} offer={thread.credito_voz} onActive={setVoiceActive} onSent={()=>setRevision(v=>v+1)}/>}
        </div>
      </form>}
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
export default function ChatsPage({ conversationId, requestId, onSelect, onBack, onOpenProfile, onDiscover, identityRequired, onVerifyIdentity, nativeCallConfig, callController: suppliedCallController, ...threadProps }) {
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
  const discoveredCallConfig = useNativeCallConfig(threadProps.safetyAccepted === true);
  const internalCallController = useNativeCalls(nativeCallConfig || discoveredCallConfig, chats, setError);
  const callController = suppliedCallController || internalCallController;
  const visibleChats = chats.filter(c => matches(c.nome) && (tab !== "unread" || c.nao_lidas > 0));
  const received = requests.filter(p => p.recebido), sent = requests.filter(p => !p.recebido);
  const counts = { unread: chats.filter(c => c.nao_lidas > 0).length, received: received.length, sent: sent.length };
  const visibleRequests = (tab === "received" ? received : sent).filter(p => matches(p.nome));
  const visibleHistory = history.filter(p => p.recebido === (tab === "received") && matches(p.nome));
  const connections = (data?.conexoes || []).filter(c => matches(c.nome));
  function chooseTab(key) { setTab(key); if (requestId || (conversationId && key !== "all" && key !== "unread")) onBack(); }
  const showChats = tab === "all" || tab === "unread";
  const selectedChat = chats.find(c => String(c.id) === String(conversationId));
  const lockedThread = Boolean(selectedChat?.identity_pending && selectedChat?.read_only === undefined);
  return <main className="nk-shell nk-chats-page">
    {callController?.enabled === true && callController.call && <CallPanel call={callController.call} onAccept={callController.accept} onDecline={callController.decline} onEnd={callController.end} onDismiss={callController.dismiss} onToggleMic={callController.toggleMic} onToggleCamera={callController.toggleCamera}/>}

    <div className={"nk-chats-layout" + (conversationId ? " has-thread" : "")}>
      <aside className="nk-chat-sidebar" aria-label="Lista de chats">
        <div className="nk-chat-sidebar-head"><div><h1>Chats</h1><p>Conversas privadas e pedidos</p></div><button type="button" className="nk-chat-icon" aria-label="Explorar perfis" onClick={onDiscover}><MessageCircle size={23} /></button></div>
        <label className="nk-chat-search"><Search size={18} /><input aria-label="Pesquisar chats" placeholder="Pesquisar por nome" value={query} onChange={e => setQuery(e.target.value)} />{query && <button className="nk-chat-icon" type="button" aria-label="Limpar pesquisa" onClick={() => setQuery("")}><X size={16} /></button>}</label>
        <nav className="nk-chat-tabs" aria-label="Filtrar chats">{TABS.map(([key,label]) => <button type="button" key={key} aria-pressed={tab === key} onClick={() => chooseTab(key)}>{label}{counts[key] > 0 && <span>{counts[key]}</span>}</button>)}</nav>
        {error && <p role="alert" className="nk-chat-error">{error}</p>}
        <div className="nk-chat-list">
          {!data && !error && <p className="nk-chat-placeholder">A carregar...</p>}
          {data && showChats && <>{visibleChats.map(c => <button type="button" className="nk-chat-row nk-chat-conversation" key={c.id} aria-current={conversationId === c.id ? "page" : undefined} onClick={() => onSelect(c.id)}>
            <Avatar profile={c.perfil} /><span className="nk-chat-title"><strong>{c.nome}</strong><small>{c.ultima_mensagem ? (c.ultima_mensagem.minha ? "Eu: " : "") + c.ultima_mensagem.texto : c.identity_pending ? "A aguardar verificação de identidade" : c.consent_state === "ACEITE" ? "Conversa aceite" : "Conversa anterior"}</small></span>
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
      {conversationId && data && !selectedChat ? <section className="nk-chat-empty-panel"><MessageCircle size={42}/><h2>Conversa ainda indisponível</h2><p>Consulte os pedidos enviados ou recebidos para confirmar o estado do pedido.</p><button type="button" className="nk-chat-primary" onClick={() => { setTab("sent"); onBack(); }}>Ver pedidos enviados</button><button type="button" className="nk-chat-icon" onClick={onBack}>Voltar</button></section> : conversationId && lockedThread ? <section className="nk-chat-empty-panel">
        <ShieldCheck size={42} strokeWidth={1.5}/><h2>{selectedChat?.consent_state === "ACEITE" ? "Pedido aceite" : "A aguardar verificação de identidade"}</h2>
        <p>{identityRequired ? "Verifique a sua identidade para trocar mensagens." : "A outra pessoa ainda precisa de verificar a identidade. A conversa ficará disponível quando ambos estiverem verificados."}</p>
        {identityRequired && <button type="button" className="nk-chat-primary" onClick={onVerifyIdentity}>Verificar identidade</button>}
        <button type="button" className="nk-chat-icon" onClick={onBack}>Voltar</button>
      </section> : conversationId && !data ? <section className="nk-chat-empty-panel">A carregar conversa...</section> : conversationId ? <Thread key={conversationId} id={conversationId} {...threadProps} callController={callController} onBack={onBack} onOpenProfile={onOpenProfile} onVerifyIdentity={onVerifyIdentity} onClosed={() => { onBack(); setRevision(v => v + 1); }} /> :
        <section className="nk-chat-empty-panel"><MessageCircle size={46} strokeWidth={1.4} /><h2>Uma boa conversa começa aqui</h2><p>Escolha uma conversa ou conheça alguém novo.</p><button className="nk-chat-primary" onClick={onDiscover}>Explorar perfis</button></section>}
    </div>
  </main>;
}
