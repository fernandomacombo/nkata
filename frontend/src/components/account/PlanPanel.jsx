import { useCallback, useEffect, useState } from "react";
import {
  Check,
  Crown,
  Gem,
  Images,
  LoaderCircle,
  RefreshCw,
  Sparkles,
  Volume2,
  WalletCards,
} from "lucide-react";
import { fetchMyPlan } from "../../services/planApi.js";

const planIcon = {
  LIVRE: Sparkles,
  ESSENCIAL: Gem,
  PREMIUM: Crown,
};

function planLabel(plan, english) {
  if (!english) return plan?.label;
  return ({ LIVRE: "Free", ESSENCIAL: "Essential", PREMIUM: "Premium" })[plan?.code] || plan?.label;
}

function featureLabels(plan, english) {
  const features = plan?.features || {};
  const labels = [
    `${plan?.daily_signal_limit || 0} ${english ? "signals per day" : "sinais por dia"}`,
    english ? "Text chat after a match" : "Chat de texto após match",
  ];
  if (features.chat_audio) labels.push(english ? "Audio in chat" : "Áudio no chat");
  if (features.chat_video) labels.push(english ? "Video in chat" : "Vídeo no chat");
  if (features.status_media) labels.push(english ? "Photo and video status" : "Status com foto e vídeo");
  if (features.feed_media_publish) labels.push(english ? "Photo and video posts" : "Publicações com foto e vídeo");
  if (features.advanced_filters) labels.push(english ? "Advanced filters" : "Filtros avançados");
  if (features.priority_discovery) labels.push(english ? "Priority discovery" : "Prioridade na descoberta");
  return labels;
}

export default function PlanPanel({ language = "PT" }) {
  const english = language === "EN";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async ({ signal } = {}) => {
    setLoading(true);
    setError("");
    try {
      const result = await fetchMyPlan({ signal });
      setData(result);
    } catch (requestError) {
      if (requestError.name !== "AbortError") {
        setError(requestError.message || (english ? "Could not load your plan." : "Não foi possível consultar o seu plano."));
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [english]);

  useEffect(() => {
    const controller = new AbortController();
    load({ signal: controller.signal });
    return () => controller.abort();
  }, [load]);

  if (loading && !data) {
    return (
      <section className="nk-plan-panel nk-plan-panel--loading">
        <LoaderCircle size={24} className="is-spinning" />
        <div><strong>{english ? "Loading plan…" : "A carregar o plano…"}</strong></div>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="nk-plan-panel nk-plan-panel--error">
        <WalletCards size={24} />
        <div>
          <strong>{english ? "Could not load the plan" : "Não foi possível consultar o plano"}</strong>
          <span>{error}</span>
        </div>
        <button type="button" onClick={() => load()}><RefreshCw size={16} /> {english ? "Refresh" : "Atualizar"}</button>
      </section>
    );
  }

  const current = data.current_plan;
  const quota = data.signal_quota;
  const recharge = data.recharge;
  const CurrentIcon = planIcon[current.code] || Sparkles;
  const progress = quota.daily_limit
    ? Math.min(100, Math.round((quota.used_today / quota.daily_limit) * 100))
    : 0;

  return (
    <section className="nk-plan-panel">
      <header className="nk-plan-panel__heading">
        <h2>{english ? "Plan" : "Plano"}</h2>
        <button
          type="button"
          className="nk-plan-panel__refresh"
          onClick={() => load()}
          disabled={loading}
          aria-label={english ? "Refresh plan" : "Atualizar plano"}
        >
          <RefreshCw size={16} className={loading ? "is-spinning" : ""} />
        </button>
      </header>

      <div className="nk-plan-current">
        <div className="nk-plan-current__identity">
          <span><CurrentIcon size={24} /></span>
          <div>
            <small>{english ? "Current plan" : "Plano atual"}</small>
            <strong>{planLabel(current, english)}</strong>
            <em>{current.paid ? (english ? "Paid plan" : "Plano pago") : (english ? "Free access" : "Acesso gratuito")}</em>
          </div>
        </div>

        <div className="nk-plan-current__usage">
          <div>
            <span>{english ? "Today's signals" : "Sinais de hoje"}</span>
            <strong>{quota.used_today} / {quota.daily_limit}</strong>
          </div>
          <div className="nk-plan-current__progress" aria-hidden="true">
            <span style={{ width: `${progress}%` }} />
          </div>
          <small>
            {quota.remaining_today > 0
              ? `${quota.remaining_today} ${english ? "still available in your plan today." : "ainda disponíveis no plano hoje."}`
              : quota.recharge_balance > 0
                ? (english
                  ? `Daily allowance used. Your top-up still has ${quota.recharge_balance}.`
                  : `Franquia diária usada. A recarga ainda tem ${quota.recharge_balance}.`)
                : (english ? "Daily allowance used and no top-up balance." : "Franquia diária utilizada e sem saldo de recarga.")}
          </small>
        </div>

        <div className="nk-plan-current__recharge">
          <span><WalletCards size={19} /></span>
          <div><small>{english ? "Top-up balance" : "Saldo de recarga"}</small><strong>{recharge.balance} {english ? "signals" : "sinais"}</strong></div>
        </div>
      </div>

      <div className="nk-plan-catalog">
        {data.available_plans.map((plan) => {
          const Icon = planIcon[plan.code] || Sparkles;
          const active = plan.code === current.code;
          return (
            <article key={plan.code} className={`nk-plan-card ${active ? "is-current" : ""}`}>
              <div className="nk-plan-card__top">
                <span><Icon size={21} /></span>
                {active && <em>{english ? "Current" : "Atual"}</em>}
              </div>
              <h3>{planLabel(plan, english)}</h3>
              <strong className="nk-plan-card__price">
                {plan.code === "LIVRE" ? "0 MT" : plan.price_status}
              </strong>
              <ul>
                {featureLabels(plan, english).map((feature) => (
                  <li key={feature}><Check size={15} /> {feature}</li>
                ))}
              </ul>
              <button type="button" disabled>
                {active ? (english ? "Current" : "Atual") : (english ? "Coming soon" : "Em breve")}
              </button>
            </article>
          );
        })}
      </div>

      <div className="nk-recharge-panel">
        <div className="nk-recharge-panel__copy">
          <span><Volume2 size={19} /></span>
          <div>
            <strong>{english ? "More signals" : "Mais sinais"}</strong>
            <p>{english ? "Use top-ups after the daily limit." : "Use recargas após o limite diário."}</p>
          </div>
        </div>
        <div className="nk-recharge-panel__packs">
          {recharge.packs.map((pack) => (
            <button type="button" key={pack.credits} disabled>
              <Images size={16} />
              <strong>+{pack.credits}</strong>
              <span>{pack.price_status}</span>
            </button>
          ))}
        </div>
        <small>{english ? "Payments are not available yet." : "Pagamentos ainda não disponíveis."}</small>
      </div>
    </section>
  );
}
