import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { LoaderCircle, UserCheck, UserMinus, UserPlus } from "lucide-react";
import { fetchFollowState, toggleFollowProfile } from "../../services/followApi.js";

function usePortalTarget(selector) {
  const [target, setTarget] = useState(() => document.querySelector(selector));

  useEffect(() => {
    const findTarget = () => {
      const next = document.querySelector(selector);
      setTarget((current) => current === next ? current : next);
    };

    findTarget();
    const observer = new MutationObserver(findTarget);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [selector]);

  return target;
}

export default function ProfileFollowAction({ profileId }) {
  const target = usePortalTarget(".nk-profile-detail__quick-actions");
  const [active, setActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [requiresLogin, setRequiresLogin] = useState(false);
  const [message, setMessage] = useState("");

  const validProfileId = useMemo(() => {
    const value = Number(profileId);
    return Number.isInteger(value) && value > 0 ? value : null;
  }, [profileId]);

  useEffect(() => {
    if (!validProfileId) return undefined;

    const controller = new AbortController();
    setLoading(true);
    setRequiresLogin(false);
    setMessage("");

    fetchFollowState(validProfileId, { signal: controller.signal })
      .then((result) => setActive(Boolean(result.active)))
      .catch((error) => {
        if (error.name === "AbortError") return;
        if (error.status === 401 || error.status === 403) {
          setRequiresLogin(true);
          return;
        }
        setMessage(error.message || "Não foi possível consultar esta ligação.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [validProfileId]);

  const handleToggle = async () => {
    if (requiresLogin) {
      const next = encodeURIComponent(window.location.pathname);
      window.location.assign(`/entrar/?next=${next}`);
      return;
    }
    if (!validProfileId || busy) return;

    setBusy(true);
    setMessage("");
    try {
      const result = await toggleFollowProfile(validProfileId);
      setActive(Boolean(result.active));
      setMessage(result.message || "Ligação atualizada.");
      window.setTimeout(() => setMessage(""), 2400);
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        setRequiresLogin(true);
        setMessage("Entre na sua conta para seguir este perfil.");
      } else {
        setMessage(error.message || "Não foi possível atualizar esta ligação.");
      }
    } finally {
      setBusy(false);
    }
  };

  if (!target || !validProfileId) return null;

  const Icon = loading || busy
    ? LoaderCircle
    : active
      ? UserCheck
      : UserPlus;

  return createPortal(
    <div className="nk-profile-follow-wrap">
      <button
        type="button"
        className={`nk-profile-follow ${active ? "is-active" : ""}`}
        onClick={handleToggle}
        disabled={loading || busy}
        aria-pressed={active}
        title={active ? "Deixar de seguir" : "Seguir perfil"}
      >
        <Icon size={18} className={loading || busy ? "is-spinning" : ""} />
        <span>
          {loading
            ? "A confirmar…"
            : busy
              ? "A atualizar…"
              : requiresLogin
                ? "Entrar para seguir"
                : active
                  ? "A seguir"
                  : "Seguir"}
        </span>
        {active && !loading && !busy && <UserMinus size={14} className="nk-profile-follow__remove" />}
      </button>
      {message && <small className="nk-profile-follow__message" role="status">{message}</small>}
    </div>,
    target,
  );
}
