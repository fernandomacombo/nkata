import { useMemo, useState } from "react";
import {
  Bell,
  CheckCheck,
  Heart,
  MessageCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";

const iconByType = {
  INTERESSE: Heart,
  MATCH: Sparkles,
  MENSAGEM: MessageCircle,
  EQUIPA: ShieldCheck,
};

function formatActivityDate(value) {
  if (!value) return "";

  const date = new Date(value);
  const now = new Date();
  const minutes = Math.floor((now - date) / 60000);

  if (minutes < 1) return "Agora";
  if (minutes < 60) return `Há ${minutes} min`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Há ${hours} h`;

  return new Intl.DateTimeFormat("pt-MZ", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function NotificationItem({ notification, onOpen }) {
  const Icon = iconByType[notification.type] || Bell;

  return (
    <button
      type="button"
      className={`nk-notification ${notification.read ? "" : "is-unread"}`}
      onClick={() => onOpen(notification)}
    >
      <span className={`nk-notification__icon is-${notification.type.toLowerCase()}`}>
        <Icon size={19} />
      </span>

      <span className="nk-notification__content">
        <span className="nk-notification__topline">
          <strong>{notification.title}</strong>
          <time>{formatActivityDate(notification.updatedAt)}</time>
        </span>
        <span className="nk-notification__text">{notification.text}</span>
        <small>{notification.typeLabel}</small>
      </span>

      <span className="nk-notification__person">
        {notification.profile?.foto_url ? (
          <img
            src={notification.profile.foto_url}
            alt={`Foto de ${notification.profile.nome_publico}`}
          />
        ) : (
          <UserRound size={22} />
        )}
      </span>

      {!notification.read && <span className="nk-notification__dot" aria-label="Não lida" />}
    </button>
  );
}

export default function NotificationsPage({
  notifications,
  unread,
  loading,
  error,
  onReload,
  onMarkAll,
  onOpen,
}) {
  const [filter, setFilter] = useState("all");

  const visibleNotifications = useMemo(() => (
    filter === "unread"
      ? notifications.filter((item) => !item.read)
      : notifications
  ), [filter, notifications]);

  return (
    <main className="nk-notifications-page">
      <section className="nk-notifications-page__intro">
        <div className="nk-shell nk-notifications-page__intro-inner">
          <div>
            <span className="nk-eyebrow nk-eyebrow--dark">
              <Bell size={15} /> Atividade
            </span>
            <h1>Notificações</h1>
            <p>Interesses, matches e mensagens num só lugar.</p>
          </div>

          <div className="nk-notifications-page__intro-actions">
            {unread > 0 && (
              <button type="button" onClick={onMarkAll}>
                <CheckCheck size={17} /> Marcar todas como lidas
              </button>
            )}
            <button type="button" onClick={onReload} disabled={loading}>
              <RefreshCw size={17} className={loading ? "is-spinning" : ""} />
              Atualizar
            </button>
          </div>
        </div>
      </section>

      <section className="nk-shell nk-notifications-page__content">
        <div className="nk-notifications-page__toolbar">
          <div>
            <button
              type="button"
              className={filter === "all" ? "is-active" : ""}
              onClick={() => setFilter("all")}
            >
              Todas <span>{notifications.length}</span>
            </button>
            <button
              type="button"
              className={filter === "unread" ? "is-active" : ""}
              onClick={() => setFilter("unread")}
            >
              Não lidas <span>{unread}</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="nk-notifications-page__error">
            <Bell size={18} />
            <span>{error}</span>
            <button type="button" onClick={onReload}>Tentar novamente</button>
          </div>
        )}

        {loading && !notifications.length ? (
          <div className="nk-notifications-page__loading">
            <span />
            <span />
            <span />
          </div>
        ) : visibleNotifications.length ? (
          <div className="nk-notifications-list">
            {visibleNotifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onOpen={onOpen}
              />
            ))}
          </div>
        ) : (
          <div className="nk-notifications-page__empty">
            <span><Bell size={28} /></span>
            <h2>{filter === "unread" ? "Está tudo visto" : "Ainda não há notificações"}</h2>
            <p>
              {filter === "unread"
                ? "Não tem notificações por ler."
                : "Os novos interesses, matches e mensagens aparecerão aqui."}
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
