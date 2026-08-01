import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  LockKeyhole,
  MapPin,
  MessageCircle,
  Send,
  ShieldCheck,
  UserRound,
} from "lucide-react";

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
  const endRef = useRef(null);
  const profile = match?.otherProfile;

  useEffect(() => {
    setDraft("");
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

          <span className="nk-conversation__secure">
            <ShieldCheck size={16} />
            Privada
          </span>
        </header>

        <section className="nk-conversation__body" aria-live="polite">
          <div className="nk-conversation__opening">
            <span><LockKeyhole size={17} /></span>
            <div>
              <strong>É um match</strong>
              <p>Conversem com respeito. Os contactos pessoais não precisam de ser partilhados logo no início.</p>
            </div>
          </div>

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
    </main>
  );
}
