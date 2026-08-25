import { useMemo, useState } from "react";
import {
  Bell,
  CheckCheck,
  CirclePlay,
  Heart,
  Images,
  MessageCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";
import useInterfaceLanguage from "../hooks/useInterfaceLanguage.js";

const iconByType = {
  INTERESSE: Heart,
  SINAL: Sparkles,
  MOMENTO: CirclePlay,
  PUBLICACAO: Images,
  MATCH: Sparkles,
  MENSAGEM: MessageCircle,
  EQUIPA: ShieldCheck,
};

const typeLabels = {
  INTERESSE: "New interest",
  SINAL: "New signal",
  MOMENTO: "Moment reaction",
  PUBLICACAO: "Post reaction",
  MATCH: "New match",
  MENSAGEM: "New message",
  EQUIPA: "Team notice",
};

function formatActivityDate(value, english) {
  if (!value) return "";

  const date = new Date(value);
  const now = new Date();
  const minutes = Math.max(0, Math.floor((now - date) / 60000));

  if (minutes < 1) return english ? "Now" : "Agora";
  if (minutes < 60) return english ? `${minutes} min ago` : `Há ${minutes} min`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return english ? `${hours} h ago` : `Há ${hours} h`;

  return new Intl.DateTimeFormat(english ? "en-GB" : "pt-MZ", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function NotificationItem({ notification, index, onOpen, english }) {
  const Icon = iconByType[notification.type] || Bell;

  return (
    <button
      type="button"
      className={`nk-notification ${notification.read ? "" : "is-unread"}`}
      style={{ "--nk-notification-order": index }}
      onClick={() => onOpen(notification)}
      aria-label={`${notification.title}. ${notification.text}`}
    >
      <span className={`nk-notification__icon is-${notification.type.toLowerCase()}`}>
        <Icon size={19} />
      </span>

      <span className="nk-notification__content">
        <span className="nk-notification__topline">
          <strong>{notification.title}</strong>
          <time>{formatActivityDate(notification.updatedAt, english)}</time>
        </span>
        <span className="nk-notification__text">{notification.text}</span>
        <small>{english ? (typeLabels[notification.type] || notification.typeLabel) : notification.typeLabel}</small>
      </span>

      <span className="nk-notification__person">
        {notification.profile?.foto_url ? (
          <img
            src={notification.profile.foto_url}
            alt={`${english ? "Photo of" : "Foto de"} ${notification.profile.nome_publico}`}
          />
        ) : (
          <UserRound size={22} />
        )}
      </span>

      {!notification.read && <span className="nk-notification__dot" aria-label={english ? "Unread" : "Não lida"} />}
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
  const english = useInterfaceLanguage() === "EN";
  const [filter, setFilter] = useState("all");

  const visibleNotifications = useMemo(() => (
    filter === "unread"
      ? notifications.filter((item) => !item.read)
      : notifications
  ), [filter, notifications]);

  return (
    <main className="nk-notifications-page">
      <CompactPageHeader title={english ? "Notifications" : "Notificações"}>
        {unread > 0 && (
          <button type="button" onClick={onMarkAll}>
            <CheckCheck size={17} /> {english ? "Mark all as read" : "Marcar como lidas"}
          </button>
        )}
        <button type="button" onClick={onReload} disabled={loading}>
          <RefreshCw size={17} className={loading ? "is-spinning" : ""} />
          {english ? "Refresh" : "Atualizar"}
        </button>
      </CompactPageHeader>

      <section className="nk-shell nk-notifications-page__content">
        <div className="nk-notifications-page__toolbar">
          <div>
            <button
              type="button"
              className={filter === "all" ? "is-active" : ""}
              onClick={() => setFilter("all")}
            >
              {english ? "All" : "Todas"} <span>{notifications.length}</span>
            </button>
            <button
              type="button"
              className={filter === "unread" ? "is-active" : ""}
              onClick={() => setFilter("unread")}
            >
              {english ? "Unread" : "Por ver"} <span>{unread}</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="nk-notifications-page__error">
            <Bell size={18} />
            <span>{error}</span>
            <button type="button" onClick={onReload}>{english ? "Try again" : "Tentar novamente"}</button>
          </div>
        )}

        {loading && !notifications.length ? (
          <div className="nk-notifications-page__loading" aria-label={english ? "Loading notifications" : "A carregar notificações"}>
            <span />
            <span />
            <span />
          </div>
        ) : visibleNotifications.length ? (
          <div className="nk-notifications-list" aria-live="polite">
            {visibleNotifications.map((notification, index) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                index={index}
                onOpen={onOpen}
                english={english}
              />
            ))}
          </div>
        ) : (
          <div className="nk-notifications-page__empty">
            <span><Bell size={28} /></span>
            <h2>{filter === "unread" ? (english ? "All caught up" : "Tudo visto") : (english ? "No notifications" : "Nenhuma notificação")}</h2>
            <p>
              {filter === "unread"
                ? (english ? "There are no unread notifications." : "Não há notificações por ler.")
                : (english ? "Updates will appear here." : "As novidades aparecerão aqui.")}
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
