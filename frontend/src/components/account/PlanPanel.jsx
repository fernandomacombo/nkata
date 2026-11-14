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
import { fetchMyPlan, fetchPayments, createPayment, checkPayment, closePaymentIfTerminal } from "../../services/planApi.js";

const planIcon = {
  LIVRE: Sparkles,
  ESSENCIAL: Gem,
  QUINZENAL: Gem,
  PREMIUM: Crown,
};

function planLabel(plan, english) {
  if (!english) return plan?.label;
  return ({ LIVRE: "Free", ESSENCIAL: "Essential", PREMIUM: "Premium", QUINZENAL: "Fortnightly" })[plan?.code] || plan?.label;
}

function featureLabels(plan, english) {
  const features = plan?.features || {};
  const labels = [
    `${plan?.daily_signal_limit || 0} ${english ? "signals per day" : "sinais por dia"}`,
    features.chat_text ? (english ? "Text chat after a match" : "Mensagens livres após match") : (english ? "Preset messages after a match" : "Mensagens predefinidas após match"),
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
  const [payments, setPayments] = useState([]);
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [paymentMessage, setPaymentMessage] = useState("");

  const loadPayments = useCallback(async () => {
    try { setPayments((await fetchPayments()).results || []); }
    catch (failure) { setPaymentMessage(failure.message); }
  }, []);

  useEffect(() => { loadPayments(); }, [loadPayments]);

  async function buy(product) {
    setPaymentBusy(true);
    setPaymentMessage("");
    const storageKey = `nkata-checkout-${product}`;
    try {
      let key = sessionStorage.getItem(storageKey);
      if (!key) { key = crypto.randomUUID(); sessionStorage.setItem(storageKey, key); }
      const order = await createPayment(product, key);
      sessionStorage.removeItem(storageKey);
      await loadPayments();
      if (order.checkout_url) window.location.assign(order.checkout_url);
      else setPaymentMessage(english ? "Check the payment status below." : "Consulte o estado do pagamento abaixo.");
    } catch (failure) { setPaymentMessage(failure.message); await loadPayments(); }
    finally { setPaymentBusy(false); }
  }

  async function verifyPayment(order) {
    setPaymentBusy(true);
    setPaymentMessage("");
    try {
      const result = await checkPayment(order.id);
      if (["PAGO", "FALHOU"].includes(result.status)) sessionStorage.removeItem(`nkata-checkout-${order.product}`);
      setPaymentMessage(result.status === "PAGO"
        ? (english ? "Payment confirmed. Benefits activated." : "Pagamento confirmado. Benefícios ativados.")
        : (english ? "Payment has not activated benefits yet." : "Este pagamento ainda não ativou benefícios."));
      await load();
      await loadPayments();
    } catch (failure) { setPaymentMessage(failure.message); }
    finally { setPaymentBusy(false); }
  }

  async function closeIfTerminal(order) {
    setPaymentBusy(true);
    setPaymentMessage("");
    try {
      const result = await closePaymentIfTerminal(order.id);
      setPaymentMessage(result.status === "FALHOU"
        ? (english ? "PaySuite confirmed this request is closed. You can choose another plan." : "A PaySuite confirmou o encerramento. Pode escolher outro plano.")
        : (english ? "Check the payment status." : "Verifique o estado do pagamento."));
      await loadPayments();
    } catch (failure) {
      setPaymentMessage(failure.message);
      await loadPayments();
    } finally {
      setPaymentBusy(false);
    }
  }

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
      <p>{english
        ? "Calls require an active Essential or Premium plan for both people. Renewals are manual. A different plan can be selected when the current one expires."
        : "As chamadas exigem Essencial ou Premium ativo nas duas contas. A renovação é manual. Pode escolher outro plano quando o atual terminar."}</p>

      <div className="nk-plan-current">
        <div className="nk-plan-current__identity">
          <span><CurrentIcon size={24} /></span>
          <div>
            <small>{english ? "Current plan" : "Plano atual"}</small>
            <strong>{planLabel(current, english)}</strong>
            <em>{current.paid ? (english ? "Paid plan" : "Plano pago") : (english ? "Free access" : "Acesso gratuito")}</em>
            {current.expires_at && <small>{english ? "Valid until: " : "Válido até: "}{new Date(current.expires_at).toLocaleString(english ? "en-GB" : "pt-PT")}</small>}
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
                {plan.code === "LIVRE" ? "0 MT" : `${plan.price_status} / ${plan.duration_days} ${english ? "days" : "dias"}`}
              </strong>
              <ul>
                {featureLabels(plan, english).map((feature) => (
                  <li key={feature}><Check size={15} /> {feature}</li>
                ))}
              </ul>
              <button type="button"
                disabled={!data.payments_enabled || !plan.paid || paymentBusy || (current.paid && !active)}
                onClick={() => buy(plan.code)}>
                {!plan.paid ? (english ? "Free" : "Gratuito") : !data.payments_enabled ? (english ? "Coming soon" : "Em breve") : active ? (english ? `Renew for ${plan.duration_days} days` : `Renovar por ${plan.duration_days} dias`) : (english ? "Choose plan" : "Escolher plano")}
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
            <button type="button" key={pack.credits} disabled={!data.payments_enabled || paymentBusy} onClick={() => buy(`RECARGA${pack.credits}`)}>
              <Images size={16} />
              <strong>+{pack.credits}</strong>
              <span>{pack.price_status}</span>
            </button>
          ))}
        </div>
        <small>{english ? "Plans last 14 or 30 days. No automatic charge. Top-ups do not unlock paid features." : "Planos válidos por 14 ou 30 dias. Sem cobrança automática. Recargas não desbloqueiam recursos pagos."}</small>
        {!data.payments_enabled && <small>{english ? "Payments are not available yet." : "Pagamentos ainda não disponíveis."}</small>}
      </div>
      <section aria-label={english ? "NKATA payments" : "Pagamentos NKATA"}>
        <h3>{english ? "NKATA payment history" : "Histórico de pagamentos NKATA"}</h3>
        <p>{english ? "Benefits activate only after payment confirmation." : "Os benefícios são ativados apenas após confirmação do pagamento."}</p>
        {paymentMessage && <p role="status">{paymentMessage}</p>}
        {payments.map((order) => (
          <article key={order.id} className="nk-plan-card">
            <strong>{order.product} · {order.amount_mzn} MT</strong>
            <small>{order.reference}</small>
            <p>{({PAGO: english ? "Paid" : "Pago", PENDENTE: english ? "Pending" : "Pendente", FALHOU: english ? "Failed" : "Falhou", CRIADO: english ? "Preparing" : "A preparar", INCERTO: english ? "Awaiting verification" : "A aguardar verificação", REVISAO: english ? "Under review" : "Em revisão"})[order.status] || order.status}</p>
            {order.checkout_url && <a href={order.checkout_url}>{english ? "Continue payment" : "Continuar pagamento"}</a>}
            {!["PAGO", "FALHOU"].includes(order.status) && <button type="button" disabled={paymentBusy} onClick={() => verifyPayment(order)}>{english ? "Check payment" : "Verificar pagamento"}</button>}
            {["CRIADO", "PENDENTE", "INCERTO"].includes(order.status) && (
              <button type="button" disabled={paymentBusy}
                onClick={() => closeIfTerminal(order)}>
                {english ? "Confirm cancellation with PaySuite" : "Confirmar cancelamento na PaySuite"}
              </button>
            )}
          </article>
        ))}
      </section>
    </section>
  );
}
