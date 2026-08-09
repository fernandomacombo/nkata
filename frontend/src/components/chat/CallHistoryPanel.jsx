import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  Clock3,
  PhoneIncoming,
  PhoneMissed,
  PhoneOutgoing,
  Video,
} from "lucide-react";
import { fetchCallHistory } from "../../services/callApi.js";

const REFRESH_MS = 5000;

function currentConversationMatchId() {
  const normalized = window.location.pathname.endsWith("/")
    ? window.location.pathname
    : `${window.location.pathname}/`;
  const match = normalized.match(/^\/matches\/(\d+)\/conversa\/$/);
  return match ? Number(match[1]) : null;
}

function formatDuration(value) {
  const seconds = Math.max(0, Number(value) || 0);
  if (!seconds) return "";
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  if (!minutes) return `${rest} s`;
  return rest ? `${minutes} min ${rest} s` : `${minutes} min`;
}

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
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function CallDirectionIcon({ item }) {
  if (item.missed) return <PhoneMissed size={17} />;
  if (item.direction === "OUTGOING") return <PhoneOutgoing size={17} />;
  return <PhoneIncoming size={17} />;
}

export default function CallHistoryPanel() {
  const [target, setTarget] = useState(null);
  const [matchId, setMatchId] = useState(() => currentConversationMatchId());
  const [calls, setCalls] = useState([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const sync = () => {
      setMatchId(currentConversationMatchId());
      setTarget(document.querySelector(".nk-conversation__body"));
    };
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("popstate", sync);
    return () => {
      observer.disconnect();
      window.removeEventListener("popstate", sync);
    };
  }, []);

  useEffect(() => {
    if (!matchId) {
      setCalls([]);
      return undefined;
    }

    let disposed = false;
    let busy = false;

    const load = async () => {
      if (disposed || busy || document.visibilityState !== "visible") return;
      busy = true;
      try {
        const payload = await fetchCallHistory(matchId);
        if (!disposed) setCalls(payload.results || []);
      } catch {
        if (!disposed) setCalls([]);
      } finally {
        busy = false;
      }
    };

    const activity = (event) => {
      if (Number(event.detail?.matchId) === Number(matchId)) load();
    };

    load();
    const interval = window.setInterval(load, REFRESH_MS);
    window.addEventListener("nkata:call-activity", activity);
    return () => {
      disposed = true;
      window.clearInterval(interval);
      window.removeEventListener("nkata:call-activity", activity);
    };
  }, [matchId]);

  if (!target || !matchId || !calls.length) return null;

  const visibleCalls = expanded ? calls.slice(0, 12) : calls.slice(0, 3);

  return createPortal(
    <section className="nk-call-history" aria-label="Histórico de chamadas">
      <div className="nk-call-history__heading">
        <div>
          <strong>Chamadas</strong>
          <small>Atividade desta ligação</small>
        </div>
        {calls.length > 3 && (
          <button type="button" onClick={() => setExpanded((current) => !current)}>
            {expanded ? "Mostrar menos" : "Ver histórico"}
          </button>
        )}
      </div>

      <div className="nk-call-history__list">
        {visibleCalls.map((item) => (
          <div
            key={item.id}
            className={`nk-call-history__item ${item.missed ? "is-missed" : ""}`}
          >
            <span className="nk-call-history__icon">
              <CallDirectionIcon item={item} />
            </span>

            <div className="nk-call-history__body">
              <div className="nk-call-history__title">
                <strong>{item.statusLabel}</strong>
                {item.type === "VIDEO" && <Video size={13} />}
              </div>
              <small>
                {item.typeLabel}
                {item.direction === "OUTGOING" ? " · feita por si" : " · recebida"}
              </small>
            </div>

            <div className="nk-call-history__meta">
              <span>{formatDate(item.createdAt)}</span>
              {item.durationSeconds > 0 && (
                <small><Clock3 size={11} /> {formatDuration(item.durationSeconds)}</small>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>,
    target,
  );
}
