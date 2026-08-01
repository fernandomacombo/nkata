import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Ban,
  Flag,
  Link2Off,
  LockKeyhole,
  MapPin,
  MessageCircle,
  MoreHorizontal,
  Send,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import SafetyDialog from "../components/safety/SafetyDialog.jsx";
import { blockProfile, closeMatch, reportProfile } from "../services/api.js";

function formatMessageTime(value) {
  if (!value) return "";

  return new Intl.DateTimeFormat("pt-MZ", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function MessageBubble({ message }) {
  return (
    <div className={`nk-message-row ${message.mine ? "is-mine" : ""}`}>
      <div className="nk-message-bubble">
        <p>{message.text}</p>
        <span>
          {formatMessageTime(message.createdAt)}
          {message.mine && <small>{message.read ? "Lida" : "Enviada"}</small>}
        </span>
      </div>
    </div>
  );
}

export default function ConversationPage({
  match,
  messages,
  loading,
  sending,
  error,
  onBack,
  onSend,
}) {
  const [draft, setDraft] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [safetyMode, setSafetyMode] = useState("");
  const [safetyLoading, setSafetyLoading] = useState(false);
  const [safetyError, setSafetyError] = useState("");
  const [safetyStatus, setSafetyStatus] = useState("");
  const endRef = useRef(null);
  const profile = match?.otherProfile;

  useEffect(() => {
    setDraft("");
    setMenuOpen(false);
    setSafetyMode("");
    setSafetyError("");
    setSafetyStatus("");
  }, [match?.id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, loading]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const text = draft.trim();

    if (!text || sending) return;

    const sent = await onSend(text);
    if (sent) setDraft("");
  };

  const openSafetyAction = (mode) => {
    setMenuOpen(false);
    setSafetyError("");
    setSafetyMode(mode);
  };

  const handleSafetyConfirm = async ({ reason, details } = {}) => {
    if (!match || !profile || !safetyMode) return;

    const currentMode = safetyMode;
    setSafetyLoading(true);
    setSafetyError("");

    try {
      let result;

      if (currentMode === "report") {
        result = await reportProfile(profile.id, { reason, details });
      } else if (currentMode === "block") {
        result = await blockProfile(profile.id);
      } else {
        result = await closeMatch(match.id);
      }

      setSafetyMode("");
      setSafetyStatus(result?.message || "A ação foi concluída.");

      if (["block", "close"].includes(currentMode)) {
        window.setTimeout(() => window.location.assign("/matches/"), 1000);
      } else {
        window.setTimeout(() => setSafetyStatus(""), 3200);
      }
    } catch (requestError) {
      setSafetyError(requestError.message || "Não foi possível concluir esta ação.");
    } finally {
      setSafetyLoading(false);
    }
  };

  if (!match) {
    return (
      <main className="nk-conversation nk-conversation--empty">
        <div className="nk-shell nk-conversation__empty-card">
          <MessageCircle size={30} />
          <h1>Conversa não disponível</h1>
          <p>Volte aos matches e escolha uma conversa.</p>
          <button type="button" className="nk-button nk-button--wine" onClick={onBack}>
            Voltar aos matches
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="nk-conversation">
      <div className="nk-shell nk-conversation__shell">
        <header className="nk-conversation__header">
          <button type="button" className="nk-conversation__back" onClick={onBack}>
            <ArrowLeft size={19} />
            <span>Matches</span>
          </button>

          <div className="nk-conversation__person">
            <span className="nk-conversation__avatar">
              {profile?.foto_url ? (
                <img src={profile.foto_url} alt={`Foto de ${profile.nome_publico}`} />
              ) : (
                <UserRound size={28} />
              )}
            </span>
            <div>
              <strong>{profile?.nome_publico || "Membro NKATA"}</strong>
              <small><MapPin size={12} /> {profile?.cidade || "Moçambique"}</small>
            </div>
          </div>

          <div className="nk-conversation__options">
            <span className="nk-conversation__secure">
              <ShieldCheck size={16} />
              Privada
            </span>
            <button
              type="button"
              className="nk-conversation__options-trigger"
              onClick={() => setMenuOpen((current) => !current)}
              aria-label="Opções da conversa"
              aria-expanded={menuOpen}
            >
              <MoreHorizontal size={20} />
            </button>

            {menuOpen && (
              <div className="nk-conversation__safety-menu">
                <button type="button" onClick={() => openSafetyAction("report")}>
                  <Flag size={16} /> Denunciar perfil
                </button>
                <button type="button" onClick={() => openSafetyAction("close")}>
                  <Link2Off size={16} /> Encerrar ligação
                </button>
                <button
                  type="button"
                  className="is-danger"
                  onClick={() => openSafetyAction("block")}
                >
                  <Ban size={16} /> Bloquear pessoa
                </button>
              </div>
            )}
          </div>
        </header>

        <section className="nk-conversation__body" aria-live="polite">
          <div className="nk-conversation__opening">
            <span><LockKeyhole size={17} /></span>
            <div>
              <strong>É um match</strong>
              <p>Conversem com respeito. Os contactos pessoais não precisam de ser partilhados logo no início.</p>
            </div>
          </div>

          {safetyStatus && (
            <div className="nk-interest-message is-active" role="status">
              {safetyStatus}
            </div>
          )}

          {error && (
            <div className="nk-conversation__error" role="status">
              {error}
            </div>
          )}

          {loading ? (
            <div className="nk-conversation__loading">
              <span />
              <span />
              <span />
            </div>
          ) : messages.length ? (
            <div className="nk-message-list">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              <div ref={endRef} />
            </div>
          ) : (
            <div className="nk-conversation__first-message">
              <MessageCircle size={28} />
              <h2>Comece a conversa</h2>
              <p>Uma mensagem simples e respeitosa é suficiente.</p>
              <button
                type="button"
                onClick={() => setDraft("Olá, gostei de conhecer o seu perfil. Como está?")}
              >
                Usar uma sugestão
              </button>
            </div>
          )}
        </section>

        <form className="nk-composer" onSubmit={handleSubmit}>
          <label>
            <span className="sr-only">Mensagem</span>
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value.slice(0, 1200))}
              placeholder="Escreva uma mensagem…"
              rows={1}
              disabled={sending}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  handleSubmit(event);
                }
              }}
            />
          </label>

          <span className="nk-composer__count">{draft.length}/1200</span>

          <button
            type="submit"
            className="nk-composer__send"
            disabled={!draft.trim() || sending}
            aria-label="Enviar mensagem"
          >
            <Send size={19} />
            <span>{sending ? "A enviar…" : "Enviar"}</span>
          </button>
        </form>
      </div>

      <SafetyDialog
        open={Boolean(safetyMode)}
        mode={safetyMode}
        personName={profile?.nome_publico}
        loading={safetyLoading}
        error={safetyError}
        onClose={() => !safetyLoading && setSafetyMode("")}
        onConfirm={handleSafetyConfirm}
      />
    </main>
  );
}
