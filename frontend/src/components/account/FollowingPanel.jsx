import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  ArrowUpRight,
  BadgeCheck,
  CirclePlay,
  LoaderCircle,
  MapPin,
  RefreshCw,
  ShieldCheck,
  UserMinus,
  UserRound,
  UsersRound,
} from "lucide-react";
import { fetchFollowingProfiles, toggleFollowProfile } from "../../services/followApi.js";

function useAccountTarget() {
  const [target, setTarget] = useState(() => document.querySelector(".nk-account__main"));

  useEffect(() => {
    const refresh = () => {
      const next = document.querySelector(".nk-account__main");
      setTarget((current) => current === next ? current : next);
    };

    refresh();
    const observer = new MutationObserver(refresh);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  return target;
}

function navigateApp(path) {
  if (window.location.pathname === path) return;
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function FollowingPerson({ profile, busy, onOpen, onUnfollow }) {
  return (
    <article className="nk-following-person">
      <button
        type="button"
        className="nk-following-person__identity"
        onClick={() => onOpen(profile)}
        aria-label={`Abrir perfil de ${profile.nome_publico}`}
      >
        <span className="nk-following-person__photo">
          {profile.foto_url ? (
            <img src={profile.foto_url} alt="" />
          ) : (
            <UserRound size={34} strokeWidth={1.35} />
          )}
          {profile.verificado && (
            <em aria-label="Perfil verificado"><BadgeCheck size={15} /></em>
          )}
        </span>

        <span className="nk-following-person__copy">
          <strong>
            {profile.nome_publico}
            {profile.idade ? `, ${profile.idade}` : ""}
          </strong>
          <small><MapPin size={13} /> {profile.cidade}</small>
          <span>{profile.objetivo_display}</span>
        </span>

        <ArrowUpRight size={18} />
      </button>

      <button
        type="button"
        className="nk-following-person__remove"
        onClick={() => onUnfollow(profile)}
        disabled={busy}
      >
        {busy ? <LoaderCircle size={16} className="is-spinning" /> : <UserMinus size={16} />}
        {busy ? "A atualizar" : "Deixar de seguir"}
      </button>
    </article>
  );
}

export default function FollowingPanel() {
  const target = useAccountTarget();
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  const load = async ({ signal } = {}) => {
    if (!target) return;

    setLoading(true);
    setError("");
    try {
      const result = await fetchFollowingProfiles({ signal });
      setProfiles(result.results);
    } catch (requestError) {
      if (requestError.name !== "AbortError") {
        setError(requestError.message || "Não foi possível carregar as pessoas que segue.");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  };

  useEffect(() => {
    if (!target) {
      setProfiles([]);
      setError("");
      return undefined;
    }

    const controller = new AbortController();
    load({ signal: controller.signal });
    return () => controller.abort();
  }, [target]);

  const handleOpen = (profile) => {
    navigateApp(`/perfis/${profile.id}/`);
    window.scrollTo({ top: 0, behavior: "auto" });
  };

  const handleUnfollow = async (profile) => {
    if (busyId) return;
    setBusyId(profile.id);
    setError("");

    try {
      const result = await toggleFollowProfile(profile.id);
      if (!result.active) {
        setProfiles((current) => current.filter((item) => item.id !== profile.id));
      }
    } catch (requestError) {
      setError(requestError.message || "Não foi possível atualizar esta ligação.");
    } finally {
      setBusyId(null);
    }
  };

  if (!target) return null;

  return createPortal(
    <section className="nk-following-panel" aria-labelledby="nk-following-title">
      <header className="nk-following-panel__header">
        <div>
          <span><UserRound size={16} /> Ligações privadas</span>
          <h2 id="nk-following-title">A seguir</h2>
          <p>As pessoas que acompanha aparecem com prioridade nos Momentos.</p>
        </div>

        <div className="nk-following-panel__header-actions">
          <span className="nk-following-panel__private">
            <ShieldCheck size={15} /> Só você vê esta lista
          </span>
          <button type="button" onClick={() => load()} disabled={loading} aria-label="Atualizar A seguir">
            <RefreshCw size={17} className={loading ? "is-spinning" : ""} />
          </button>
        </div>
      </header>

      {error && <div className="nk-following-panel__error">{error}</div>}

      {loading && !profiles.length ? (
        <div className="nk-following-panel__loading" aria-label="A carregar">
          <LoaderCircle size={24} className="is-spinning" />
          <span>A carregar as suas ligações</span>
        </div>
      ) : profiles.length ? (
        <div className="nk-following-panel__people">
          {profiles.map((profile) => (
            <FollowingPerson
              key={profile.id}
              profile={profile}
              busy={busyId === profile.id}
              onOpen={handleOpen}
              onUnfollow={handleUnfollow}
            />
          ))}
        </div>
      ) : (
        <div className="nk-following-panel__empty">
          <span><UsersRound size={25} /></span>
          <div>
            <strong>Ainda não segue ninguém</strong>
            <p>Ao seguir um perfil, ele aparecerá aqui e os Momentos dessa pessoa terão prioridade.</p>
          </div>
          <button type="button" onClick={() => navigateApp("/perfis/")}>
            <UserRound size={17} /> Explorar perfis
          </button>
        </div>
      )}

      {profiles.length > 0 && (
        <button
          type="button"
          className="nk-following-panel__moments"
          onClick={() => navigateApp("/momentos/")}
        >
          <CirclePlay size={18} /> Ver Momentos com prioridade
        </button>
      )}
    </section>,
    target,
  );
}
