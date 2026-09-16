import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { LoaderCircle, UserCheck, UserMinus, UserPlus } from "lucide-react";
import { fetchFollowState, toggleFollowProfile } from "../../services/followApi.js";
import useInterfaceLanguage from "../../hooks/useInterfaceLanguage.js";

function currentProfileId() {
  const match = window.location.pathname.match(/^\/perfis\/(\d+)\/?$/);
  if (!match) return null;
  const value = Number(match[1]);
  return Number.isInteger(value) && value > 0 ? value : null;
}

function useProfilePortalContext(selector) {
  const initialTarget = document.querySelector(selector);
  const [context, setContext] = useState({
    target: initialTarget,
    profileId: initialTarget ? currentProfileId() : null,
  });

  useEffect(() => {
    const refresh = () => {
      const target = document.querySelector(selector);
      const profileId = target ? currentProfileId() : null;
      setContext((current) => (
        current.target === target && current.profileId === profileId
          ? current
          : { target, profileId }
      ));
    };

    refresh();
    const observer = new MutationObserver(refresh);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("popstate", refresh);

    return () => {
      observer.disconnect();
      window.removeEventListener("popstate", refresh);
    };
  }, [selector]);

  return context;
}

export default function ProfileFollowAction() {
  const english = useInterfaceLanguage() === "EN";
  const { target, profileId } = useProfilePortalContext(".nk-profile-detail__quick-actions");
  const [active, setActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [requiresLogin, setRequiresLogin] = useState(false);
  const [message, setMessage] = useState("");

  const validProfileId = useMemo(() => {
    const value = Number(profileId);
    return Number.isInteger(value) && value > 0 ? value : null;
  }, [profileId]);

  useEffect(() => {
    if (!validProfileId || !target) {
      setActive(false);
      setLoading(false);
      setBusy(false);
      setRequiresLogin(false);
      setMessage("");
      return undefined;
    }

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
        setMessage(error.message || (english ? "Unable to check this connection." : "Não foi possível consultar esta ligação."));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [target, validProfileId]);

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
      setMessage(result.message || (english ? "Connection updated." : "Ligação atualizada."));
      window.setTimeout(() => setMessage(""), 2400);
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        setRequiresLogin(true);
        setMessage(english ? "Sign in to follow this profile." : "Entre na sua conta para seguir este perfil.");
      } else {
        setMessage(error.message || (english ? "Unable to update this connection." : "Não foi possível atualizar esta ligação."));
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
        title={active ? (english ? "Unfollow" : "Deixar de seguir") : (english ? "Follow profile" : "Seguir perfil")}
      >
        <Icon size={18} className={loading || busy ? "is-spinning" : ""} />
        <span>
          {loading
            ? (english ? "Checking…" : "A confirmar…")
            : busy
              ? (english ? "Updating…" : "A atualizar…")
              : requiresLogin
                ? (english ? "Sign in to follow" : "Entrar para seguir")
                : active
                  ? (english ? "Following" : "A seguir")
                  : (english ? "Follow" : "Seguir")}
        </span>
        {active && !loading && !busy && <UserMinus size={14} className="nk-profile-follow__remove" />}
      </button>
      {message && <small className="nk-profile-follow__message" role="status">{message}</small>}
    </div>,
    target,
  );
}
