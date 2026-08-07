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

function featureLabels(plan) {
  const features = plan?.features || {};
  const labels = [`${plan?.daily_signal_limit || 0} sinais por dia`, "Chat de texto após match"];
  if (features.chat_audio) labels.push("Áudio no chat");
  if (features.chat_video) labels.push("Vídeo no chat");
  if (features.status_media) labels.push("Status com foto e vídeo");
  if (features.feed_media_publish) labels.push("Publicações com foto e vídeo");
  if (features.advanced_filters) labels.push("Filtros avançados");
  if (features.priority_discovery) labels.push("Prioridade na descoberta");
  return labels;
}

export default function PlanPanel() {
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
        setError(requestError.message || "Não foi possível consultar o seu plano.");
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
      <section className="nk-plan-panel nk-plan-panel--loading">
        <LoaderCircle size={24} className="is-spinning" />
        <div><strong>A preparar o seu plano…</strong><span>A confirmar limites e benefícios.</span></div>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="nk-plan-panel nk-plan-panel--error">
        <WalletCards size={24} />
        <div>
          <strong>Não foi possível consultar o plano</strong>
          <span>{error}</span>
        </div>
        <button type="button" onClick={() => load()}><RefreshCw size={16} /> Atualizar</button>
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
        <div>
          <span className="nk-eyebrow nk-eyebrow--dark"><WalletCards size={15} /> Plano e recargas</span>
          <h2>O seu acesso ao NKATA</h2>
          <p>O plano define limites e recursos. A recarga acrescenta sinais sem alterar o plano.</p>
        </div>
        <button type="button" className="nk-plan-panel__refresh" onClick={() => load()} disabled={loading}>
          <RefreshCw size={16} className={loading ? "is-spinning" : ""} />
          Atualizar
        </button>
      </header>

      <div className="nk-plan-current">
        <div className="nk-plan-current__identity">
          <span><CurrentIcon size={24} /></span>
          <div>
            <small>Plano atual</small>
            <strong>{current.label}</strong>
            <em>{current.paid ? "Plano pago" : "Acesso gratuito"}</em>
          </div>
        </div>

        <div className="nk-plan-current__usage">
          <div>
            <span>Sinais de hoje</span>
            <strong>{quota.used_today} / {quota.daily_limit}</strong>
          </div>
          <div className="nk-plan-current__progress" aria-hidden="true">
            <span style={{ width: `${progress}%` }} />
          </div>
          <small>
            {quota.remaining_today > 0
              ? `${quota.remaining_today} ainda disponíveis no plano hoje.`
              : quota.recharge_balance > 0
                ? `Franquia diária usada. A recarga ainda tem ${quota.recharge_balance}.`
                : "Franquia diária utilizada e sem saldo de recarga."}
          </small>
        </div>

        <div className="nk-plan-current__recharge">
          <span><WalletCards size={19} /></span>
          <div><small>Saldo de recarga</small><strong>{recharge.balance} sinais</strong></div>
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
                {active && <em>Atual</em>}
              </div>
              <h3>{plan.label}</h3>
              <strong className="nk-plan-card__price">
                {plan.code === "LIVRE" ? "0 MT" : plan.price_status}
              </strong>
              <ul>
                {featureLabels(plan).map((feature) => (
                  <li key={feature}><Check size={15} /> {feature}</li>
                ))}
              </ul>
              <button type="button" disabled>
                {active ? "Plano atual" : "Pagamento em preparação"}
              </button>
            </article>
          );
        })}
      </div>

      <div className="nk-recharge-panel">
        <div className="nk-recharge-panel__copy">
          <span><Volume2 size={19} /></span>
          <div>
            <strong>Precisa de mais sinais no mesmo dia?</strong>
            <p>A recarga só começa a ser consumida depois de terminar a franquia diária do seu plano.</p>
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
        <small>Os pagamentos ainda não estão ativos. Nesta fase, os pacotes servem para testar o motor de permissões.</small>
      </div>
    </section>
  );
}
