import { useEffect, useState } from "react";
import {
  ArrowRight,
  HeartHandshake,
  MapPin,
  MessageCircle,
  Mic,
  Phone,
  RefreshCw,
  ShieldCheck,
  UserRound,
  Video,
} from "lucide-react";
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";

function formatDate(value) {
  if (!value) return "";

  const date = new Date(value);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();

  if (sameDay) {
    return new Intl.DateTimeFormat("pt-MZ", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  return new Intl.DateTimeFormat("pt-MZ", {
    day: "2-digit",
    month: "short",
  }).format(date);
}

function MatchAvatar({ profile }) {
  const [failed, setFailed] = useState(false);
  const src = profile?.foto_url || "";

  useEffect(() => setFailed(false), [src]);

  if (!src || failed) return <UserRound size={34} strokeWidth={1.4} />;
  return (
    <img
      src={src}
      alt={`Foto de ${profile?.nome_publico || "membro NKATA"}`}
      onError={() => setFailed(true)}
    />
  );
}

function LastMessagePreview({ message }) {
  if (!message) return <>O interesse é mútuo. Pode começar a conversa.</>;

  if (message.type === "audio") {
    return (
      <span className="nk-match-card__voice-preview">
        <Mic size={14} strokeWidth={2} />
        {message.mine ? "Você: Nota de voz" : "Nota de voz"}
      </span>
    );
  }

  if (message.type === "call") {
    return (
      <span className={`nk-match-card__voice-preview ${message.callMissed ? "is-missed" : ""}`}>
        {message.callType === "VIDEO" ? <Video size={14} /> : <Phone size={14} />}
        {message.callLabel || "Chamada"}
      </span>
    );
  }

  return <>{`${message.mine ? "Você: " : ""}${message.text}`}</>;
}

function MatchCard({ match, onOpen }) {
  const profile = match.otherProfile;
  const lastMessage = match.lastMessage;

  return (
    <button type="button" className="nk-match-card" onClick={() => onOpen(match)}>
      <span className="nk-match-card__photo">
        <MatchAvatar profile={profile} />
        <em><ShieldCheck size={12} /></em>
      </span>

      <span className="nk-match-card__body">
        <span className="nk-match-card__topline">
          <strong>
            {profile?.nome_publico || "Membro NKATA"}
            {profile?.idade ? `, ${profile.idade}` : ""}
          </strong>
          <small>{formatDate(lastMessage?.createdAt || match.updatedAt)}</small>
        </span>

        <span className="nk-match-card__location">
          <MapPin size={13} />
          {profile?.cidade || "Moçambique"}
        </span>

        <span className={`nk-match-card__preview ${match.unreadCount ? "is-unread" : ""}`}>
          <LastMessagePreview message={lastMessage} />
        </span>
      </span>

      <span className="nk-match-card__side">
        {match.unreadCount > 0 && (
          <em className="nk-match-card__unread">
            {match.unreadCount > 9 ? "9+" : match.unreadCount}
          </em>
        )}
        <ArrowRight size={18} />
      </span>
    </button>
  );
}

export default function MatchesPage({
  matches,
  loading,
  error,
  onReload,
  onOpenConversation,
  onDiscover,
}) {
  return (
    <main className="nk-matches">
      <CompactPageHeader title="Matches">
        <button type="button" className="nk-matches__refresh" onClick={onReload} disabled={loading}>
          <RefreshCw size={17} className={loading ? "is-spinning" : ""} />
          Atualizar
        </button>
      </CompactPageHeader>

      <section className="nk-shell nk-matches__content">
        {error && (
          <div className="nk-matches__notice" role="status">
            <MessageCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="nk-match-list" aria-label="A carregar matches">
            {[1, 2, 3].map((item) => (
              <div className="nk-match-skeleton" key={item}>
                <span />
                <div><em /><em /><em /></div>
              </div>
            ))}
          </div>
        ) : matches.length ? (
          <div className="nk-match-list">
            {matches.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                onOpen={onOpenConversation}
              />
            ))}
          </div>
        ) : (
          <div className="nk-matches__empty">
            <span><HeartHandshake size={30} /></span>
            <h2>Nenhum match</h2>
            <p>Novos matches aparecerão aqui.</p>
            <button type="button" className="nk-button nk-button--wine" onClick={onDiscover}>
              Ver perfis
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
