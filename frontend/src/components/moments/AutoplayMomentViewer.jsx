import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  ChevronLeft,
  ChevronRight,
  Clock3,
  Flower2,
  Heart,
  LockKeyhole,
  Sparkles,
  Trash2,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import {
  fetchMomentReactions,
  toggleMomentReaction,
} from "../../services/momentsApi.js";
import useInterfaceLanguage from "../../hooks/useInterfaceLanguage.js";

const STILL_DURATION_MS = 6000;
const REACTION_ICONS = {
  CORACAO: Heart,
  FLOR: Flower2,
  APLAUSO: Sparkles,
};

function remainingLabel(moment, english) {
  if (!moment?.expires_at) return "";

  const expires = new Date(moment.expires_at);
  const milliseconds = Math.max(0, expires.getTime() - Date.now());
  const minutes = Math.ceil(milliseconds / 60000);
  if (minutes <= 1) return english ? "Ends in under 1 min" : "Termina em menos de 1 min";
  if (minutes < 60) return english ? `Ends in ${minutes} min` : `Termina em ${minutes} min`;
  return english ? `Ends in ${Math.ceil(minutes / 60)} h` : `Termina em ${Math.ceil(minutes / 60)} h`;
}

function MomentMedia({ moment, onVideoProgress, onVideoEnded }) {
  if (moment.media_type === "IMAGEM" && moment.media_url) {
    return <img className="nk-moment-viewer__media" src={moment.media_url} alt="" />;
  }

  if (moment.media_type === "VIDEO" && moment.media_url) {
    return (
      <video
        key={moment.id}
        className="nk-moment-viewer__media"
        src={moment.media_url}
        autoPlay
        playsInline
        preload="auto"
        onTimeUpdate={(event) => {
          const video = event.currentTarget;
          if (!Number.isFinite(video.duration) || video.duration <= 0) return;
          onVideoProgress(Math.min(100, (video.currentTime / video.duration) * 100));
        }}
        onEnded={onVideoEnded}
      />
    );
  }

  return <div className="nk-moment-viewer__text-only" aria-hidden="true" />;
}

function ReactionIcon({ type, size = 20 }) {
  const Icon = REACTION_ICONS[type] || Sparkles;
  return <Icon size={size} strokeWidth={1.7} aria-hidden="true" />;
}

function ReactionTray({ moment, reactions, loading, busy, error, onReact, english }) {
  if (loading && !reactions) {
    return <div className="nk-moment-reactions is-loading" aria-label={english ? "Loading reactions" : "A carregar reações"} />;
  }

  if (!reactions || reactions.setup_required) return null;

  if (moment.mine) {
    const activeCounts = (reactions.options || [])
      .map((option) => ({
        ...option,
        count: Number(reactions.counts?.[option.value] || 0),
      }))
      .filter((item) => item.count > 0);

    return (
      <div className="nk-moment-reactions is-own" aria-label={english ? "Reactions received" : "Reações recebidas"}>
        {activeCounts.length ? activeCounts.map((item) => (
          <span key={item.value} title={item.label}>
            <b><ReactionIcon type={item.value} size={18} /></b>
            <em>{item.count}</em>
          </span>
        )) : <small>{english ? "No reactions yet" : "Ainda sem reações"}</small>}
      </div>
    );
  }

  if (!reactions.enabled) return null;

  return (
    <div className="nk-moment-reactions" aria-label={english ? "React to Moment" : "Reagir ao Momento"}>
      <div className="nk-moment-reactions__buttons">
        {(reactions.options || []).map((option) => {
          const active = reactions.mine === option.value;
          const count = Number(reactions.counts?.[option.value] || 0);
          return (
            <button
              key={option.value}
              type="button"
              className={active ? "is-active" : ""}
              disabled={Boolean(busy)}
              aria-pressed={active}
              aria-label={active ? `${english ? "Remove" : "Remover"} ${option.label}` : option.label}
              title={active ? `${english ? "Remove" : "Remover"} ${option.label}` : option.label}
              onClick={() => onReact(option.value)}
            >
              <span><ReactionIcon type={option.value} /></span>
              {count > 0 && <em>{count}</em>}
            </button>
          );
        })}
      </div>
      {error && <small className="nk-moment-reactions__error">{error}</small>}
    </div>
  );
}

export default function AutoplayMomentViewer({
  groups,
  initialGroupIndex = 0,
  onClose,
  onDelete,
  onOpenProfile,
}) {
  const english = useInterfaceLanguage() === "EN";
  const safeInitialGroup = Math.max(0, Math.min(initialGroupIndex, Math.max(0, groups.length - 1)));
  const [groupIndex, setGroupIndex] = useState(safeInitialGroup);
  const [momentIndex, setMomentIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [reactions, setReactions] = useState(null);
  const [reactionsLoading, setReactionsLoading] = useState(false);
  const [reactionBusy, setReactionBusy] = useState("");
  const [reactionError, setReactionError] = useState("");
  const timerRef = useRef(null);
  const intervalRef = useRef(null);
  const currentMomentIdRef = useRef(null);

  const group = groups[groupIndex] || null;
  const moments = group?.moments || [];
  const moment = moments[momentIndex] || null;
  currentMomentIdRef.current = moment?.id || null;

  const clearStillTimer = useCallback(() => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    if (intervalRef.current) window.clearInterval(intervalRef.current);
    timerRef.current = null;
    intervalRef.current = null;
  }, []);

  const goNext = useCallback(() => {
    clearStillTimer();

    if (momentIndex < moments.length - 1) {
      setMomentIndex((current) => current + 1);
      return;
    }

    if (groupIndex < groups.length - 1) {
      setGroupIndex((current) => current + 1);
      setMomentIndex(0);
      return;
    }

    onClose();
  }, [clearStillTimer, groupIndex, groups.length, momentIndex, moments.length, onClose]);

  const goPrevious = useCallback(() => {
    clearStillTimer();

    if (momentIndex > 0) {
      setMomentIndex((current) => current - 1);
      return;
    }

    if (groupIndex > 0) {
      const previousGroupIndex = groupIndex - 1;
      const previousMoments = groups[previousGroupIndex]?.moments || [];
      setGroupIndex(previousGroupIndex);
      setMomentIndex(Math.max(0, previousMoments.length - 1));
    }
  }, [clearStillTimer, groupIndex, groups, momentIndex]);

  useEffect(() => {
    setGroupIndex(safeInitialGroup);
    setMomentIndex(0);
  }, [safeInitialGroup]);

  useEffect(() => {
    setProgress(0);
    clearStillTimer();

    if (!moment || moment.media_type === "VIDEO") return undefined;

    const startedAt = Date.now();
    intervalRef.current = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      const elapsed = Date.now() - startedAt;
      setProgress(Math.min(100, (elapsed / STILL_DURATION_MS) * 100));
    }, 80);

    timerRef.current = window.setTimeout(goNext, STILL_DURATION_MS);

    return clearStillTimer;
  }, [clearStillTimer, goNext, moment?.id, moment?.media_type]);

  useEffect(() => {
    if (!moment?.id) return undefined;

    const controller = new AbortController();
    setReactions(null);
    setReactionError("");
    setReactionBusy("");
    setReactionsLoading(true);

    fetchMomentReactions(moment.id, { signal: controller.signal })
      .then((result) => setReactions(result))
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          setReactionError(requestError.message || (english ? "Reactions unavailable." : "Reações indisponíveis."));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setReactionsLoading(false);
      });

    return () => controller.abort();
  }, [moment?.id]);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKey = (event) => {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowRight") goNext();
      if (event.key === "ArrowLeft") goPrevious();
    };

    window.addEventListener("keydown", handleKey);
    return () => {
      clearStillTimer();
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKey);
    };
  }, [clearStillTimer, goNext, goPrevious, onClose]);

  const handleReaction = async (reactionType) => {
    if (!moment?.id || moment.mine || reactionBusy) return;

    const reactionMomentId = moment.id;
    setReactionBusy(reactionType);
    setReactionError("");

    try {
      const result = await toggleMomentReaction(reactionMomentId, reactionType);
      if (currentMomentIdRef.current === reactionMomentId) {
        setReactions(result.reactions || null);
      }
    } catch (requestError) {
      if (currentMomentIdRef.current === reactionMomentId) {
        setReactionError(requestError.message || (english ? "Unable to react." : "Não foi possível reagir."));
      }
    } finally {
      if (currentMomentIdRef.current === reactionMomentId) {
        setReactionBusy("");
      }
    }
  };

  if (!moment || !group) return null;

  return createPortal(
    <div
      className="nk-moment-viewer nk-moment-viewer--autoplay"
      role="dialog"
      aria-modal="true"
      aria-label={`${english ? "Moment by" : "Momento de"} ${moment.profile.nome_publico}`}
    >
      <div className="nk-moment-viewer__frame">
        <div className="nk-moment-viewer__progress" aria-hidden="true">
          {moments.map((item, itemIndex) => {
            const itemProgress = itemIndex < momentIndex
              ? 100
              : itemIndex === momentIndex
                ? progress
                : 0;
            return (
              <span key={item.id} className={itemIndex < momentIndex ? "is-complete" : ""}>
                <i style={{ width: `${itemProgress}%` }} />
              </span>
            );
          })}
        </div>

        <header className="nk-moment-viewer__header">
          <button
            type="button"
            className="nk-moment-viewer__person"
            onClick={() => !moment.mine && onOpenProfile?.(moment.profile)}
            disabled={moment.mine}
            title={moment.mine ? (english ? "Manage your profile in Account" : "O seu perfil é gerido em Minha conta") : (english ? "Open profile" : "Abrir perfil")}
          >
            <span>
              {moment.profile.foto_url
                ? <img src={moment.profile.foto_url} alt="" />
                : <UserRound size={22} />}
            </span>
            <div>
              <strong>{moment.mine ? (english ? "Your Moment" : "O seu Momento") : moment.profile.nome_publico}</strong>
              <small><Clock3 size={12} /> {remainingLabel(moment, english)}</small>
            </div>
          </button>

          <div className="nk-moment-viewer__header-actions">
            {moment.mine && (
              <button type="button" onClick={() => onDelete(moment)} aria-label={english ? "Delete Moment" : "Remover Momento"}>
                <Trash2 size={18} />
              </button>
            )}
            <button type="button" onClick={onClose} aria-label={english ? "Close Moment" : "Fechar Momento"}>
              <X size={20} />
            </button>
          </div>
        </header>

        <div className={`nk-moment-viewer__content is-${moment.media_type.toLowerCase()}`}>
          <MomentMedia
            moment={moment}
            onVideoProgress={setProgress}
            onVideoEnded={goNext}
          />
          <div className="nk-moment-viewer__shade" />
          {moment.text && <p>{moment.text}</p>}

          <ReactionTray
            moment={moment}
            reactions={reactions}
            loading={reactionsLoading}
            busy={reactionBusy}
            error={reactionError}
            onReact={handleReaction}
            english={english}
          />

          <span className="nk-moment-viewer__privacy">
            {moment.visibility === "MATCHES" ? <LockKeyhole size={14} /> : <UsersRound size={14} />}
            {english ? (moment.visibility === "MATCHES" ? "Matches only" : "All members") : moment.visibility_label}
          </span>
        </div>

        {(groupIndex > 0 || momentIndex > 0) && (
          <button
            type="button"
            className="nk-moment-viewer__nav is-prev"
            onClick={goPrevious}
            aria-label={english ? "Previous Moment" : "Momento anterior"}
          >
            <ChevronLeft size={24} />
          </button>
        )}

        {(groupIndex < groups.length - 1 || momentIndex < moments.length - 1) && (
          <button
            type="button"
            className="nk-moment-viewer__nav is-next"
            onClick={goNext}
            aria-label={english ? "Next Moment" : "Próximo Momento"}
          >
            <ChevronRight size={24} />
          </button>
        )}
      </div>
    </div>,
    document.body,
  );
}
