import { useCallback, useEffect, useState } from "react";
import {
  BadgeCheck,
  Crown,
  Eye,
  Heart,
  Images,
  MessageCircle,
  Phone,
  RefreshCw,
  Sparkles,
  UsersRound,
} from "lucide-react";
import { fetchMyAccountSummary } from "../../services/api.js";


function formatDuration(seconds) {
  const totalMinutes = Math.floor(Number(seconds || 0) / 60);
  if (totalMinutes < 60) return `${totalMinutes} min`;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return minutes ? `${hours}h ${minutes}min` : `${hours}h`;
}


function Metric({ icon: Icon, value, label }) {
  return (
    <article className="nk-account-summary__metric">
      <span><Icon size={18} /></span>
      <strong>{value}</strong>
      <small>{label}</small>
    </article>
  );
}


export default function AccountSummaryPanel({ onOpenSection }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async ({ signal } = {}) => {
    setLoading(true);
    setError("");
    try {
      setData(await fetchMyAccountSummary({ signal }));
    } catch (requestError) {
      if (requestError.name !== "AbortError") {
        setError(requestError.message || "Não foi possível atualizar o resumo.");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load({ signal: controller.signal });
    return () => controller.abort();
  }, [load]);

  if (loading && !data) {
    return (
      <section className="nk-account-summary nk-account-summary--loading" aria-label="A carregar resumo">
        <span /><span /><span /><span />
      </section>
    );
  }

  if (!data) {
    return (
      <section className="nk-account-summary nk-account-summary--error">
        <strong>Resumo indisponível</strong>
        <span>{error}</span>
        <button type="button" onClick={() => load()}><RefreshCw size={16} /> Atualizar</button>
      </section>
    );
  }

  const profile = data.profile;
  const plan = data.plan;
  const quota = plan.signal_quota;
  const performance = data.performance;
  const activity = data.activity;
  const signalProgress = quota.daily_limit
    ? Math.min(100, Math.round((quota.used_today / quota.daily_limit) * 100))
    : 0;

  return (
    <section className="nk-account-summary">
      <header className="nk-account-summary__heading">
        <div>
          <span>Conta</span>
          <h2>O seu resumo</h2>
        </div>
        <div>
          <strong><Crown size={15} /> {plan.label}</strong>
          <button type="button" onClick={() => load()} disabled={loading} aria-label="Atualizar resumo">
            <RefreshCw size={16} className={loading ? "is-spinning" : ""} />
          </button>
        </div>
      </header>

      {error && <div className="nk-account-summary__notice">{error}</div>}

      <div className="nk-account-summary__top">
        <article className="nk-account-summary__completion">
          <div
            className="nk-account-summary__ring"
            style={{ "--nk-summary-progress": `${profile.completeness * 3.6}deg` }}
          >
            <span>{profile.completeness}%</span>
          </div>
          <div>
            <small>Perfil</small>
            <strong>{profile.verified ? "Verificado" : profile.status_label}</strong>
            <span>{profile.visible ? "Visível" : "Oculto"}</span>
          </div>
          <BadgeCheck size={19} />
        </article>

        <article className="nk-account-summary__signals">
          <div>
            <span><Sparkles size={18} /></span>
            <div>
              <small>Sinais de hoje</small>
              <strong>{quota.used_today} de {quota.daily_limit}</strong>
            </div>
          </div>
          <div className="nk-account-summary__bar" aria-hidden="true">
            <span style={{ width: `${signalProgress}%` }} />
          </div>
          <small>{quota.remaining_today} disponíveis · recarga {quota.recharge_balance}</small>
        </article>
      </div>

      <div className="nk-account-summary__metrics">
        <Metric icon={UsersRound} value={performance.active_matches} label="Matches" />
        <Metric icon={Heart} value={performance.interests_received} label="Interesses" />
        <Metric icon={UsersRound} value={performance.followers} label="Seguidores" />
        <Metric icon={Eye} value={performance.public_impressions} label="Aparições" />
      </div>

      <div className="nk-account-summary__activity">
        <Metric icon={Images} value={activity.approved_publications} label="Publicações" />
        <Metric icon={MessageCircle} value={activity.messages_sent} label="Mensagens" />
        <Metric icon={Phone} value={activity.calls.total} label="Chamadas" />
        <Metric icon={Phone} value={formatDuration(activity.calls.duration_seconds)} label="Em chamada" />
      </div>

      <footer className="nk-account-summary__actions">
        <button type="button" onClick={() => onOpenSection("profile")}>Editar perfil</button>
        <button type="button" onClick={() => onOpenSection("plan")}>Ver plano</button>
      </footer>
    </section>
  );
}
