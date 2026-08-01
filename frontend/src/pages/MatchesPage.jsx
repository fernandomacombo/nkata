import {
  ArrowRight,
  HeartHandshake,
  MapPin,
  MessageCircle,
  RefreshCw,
  ShieldCheck,
  UserRound,
} from "lucide-react";

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

function MatchCard({ match, onOpen }) {
  const profile = match.otherProfile;
  const lastMessage = match.lastMessage;

  return (
    <button type="button" className="nk-match-card" onClick={() => onOpen(match)}>
      <span className="nk-match-card__photo">
        {profile?.foto_url ? (
          <img src={profile.foto_url} alt={`Foto de ${profile.nome_publico}`} />
        ) : (
          <UserRound size={34} strokeWidth={1.4} />
        )}
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
          {lastMessage
            ? `${lastMessage.mine ? "Você: " : ""}${lastMessage.text}`
            : "O interesse é mútuo. Pode começar a conversa."}
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
      <section className="nk-matches__intro">
        <div className="nk-shell nk-matches__intro-inner">
          <div>
            <span className="nk-eyebrow nk-eyebrow--dark">
              <HeartHandshake size={15} />
              Matches
            </span>
            <h1>O interesse é dos dois lados.</h1>
            <p>As conversas aparecem aqui quando duas pessoas demonstram interesse.</p>
          </div>

          <button type="button" className="nk-matches__refresh" onClick={onReload} disabled={loading}>
            <RefreshCw size={17} className={loading ? "is-spinning" : ""} />
            Atualizar
          </button>
        </div>
      </section>

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
            <h2>Ainda não há matches</h2>
            <p>Quando o interesse for mútuo, a pessoa aparecerá aqui e poderão conversar.</p>
            <button type="button" className="nk-button nk-button--wine" onClick={onDiscover}>
              Ver perfis
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
