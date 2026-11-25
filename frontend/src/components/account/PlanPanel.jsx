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
import { fetchMyPlan, fetchPayments, createPayment, claimWelcome, simulatePayment } from "../../services/planApi.js";
import WalletDashboard from "./WalletDashboard.jsx";

const planIcon = {
  LIVRE: Sparkles,
  ESSENCIAL: Gem,
  QUINZENAL: Gem,
  PREMIUM: Crown,
};

function planLabel(plan, english) {
  if (!english) return plan?.label;
  if (plan?.is_launch_bonus) return "Launch bonus";
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

const blocksCheckout = order => order.blocks_checkout ?? ["CRIADO", "PENDENTE", "INCERTO", "REVISAO"].includes(order.status);

export default function PlanPanel({ language = "PT" }) {
  const english = language === "EN";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [payments, setPayments] = useState([]);
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [paymentMessage, setPaymentMessage] = useState("");
  const [bonusBusy,setBonusBusy] = useState(false);
  const [bonusMessage,setBonusMessage] = useState("");

  const loadPayments = useCallback(async () => {
    try { setPayments((await fetchPayments()).results || []); }
    catch (failure) { setPaymentMessage(failure.message); }
  }, []);

  useEffect(() => { loadPayments(); }, [loadPayments]);

  async function buy(product) {
    const existing = payments.find(blocksCheckout);
    if (existing) {
      if (existing.product === product && existing.checkout_url) {
        window.location.assign(existing.checkout_url);
        return;
      }
      setPaymentMessage(english
        ? "You already have a payment awaiting confirmation. Review it below before starting another purchase."
        : "Já existe um pagamento por confirmar. Consulte-o abaixo antes de iniciar outra compra.");
      document.getElementById("nkata-payment-history")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
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
      else {
        setPaymentMessage(order.simulated ? (english ? "Choose the simulated result below." : "Escolha o resultado da simulação abaixo.") : (english ? "Check the payment status below." : "Consulte o estado do pagamento abaixo."));
        document.getElementById("nkata-payment-history")?.scrollIntoView({behavior:"smooth",block:"start"});
      }
    } catch (failure) {
      setPaymentMessage(failure.message || (english ? "Could not start payment." : "Não foi possível iniciar o pagamento."));
      await loadPayments();
      document.getElementById("nkata-payment-history")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } finally { setPaymentBusy(false); }
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

  async function finishSimulation(order, outcome) {
    if(paymentBusy || !data?.payment_simulation || !order.simulated) return;
    setPaymentBusy(true); setPaymentMessage("");
    try { const result=await simulatePayment(order.id,outcome); setPaymentMessage(result.status==="PAGO" ? (english ? "Test credits added. No real payment." : "Créditos de teste atribuídos. Sem pagamento real.") : (english ? "Simulation: "+result.status : "Simulação: "+result.status)); await loadPayments(); await load(); }
    catch(failure){setPaymentMessage(failure.message);}
    finally{setPaymentBusy(false);}
  }

  async function receiveWelcome() {
    setBonusBusy(true); setBonusMessage("");
    try { await claimWelcome(); await load(); }
    catch (failure) { setBonusMessage(failure.message); }
    finally { setBonusBusy(false); }
  }

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
        <h2>{data.credit_transition ? (english ? "Credits and wallet" : "Créditos e carteira") : (english ? "Plan" : "Plano")}</h2>
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
      <p>{data.credit_only ? (english ? "Use your credits for available paid actions. No daily free credits." : "Utilize os créditos nas funcionalidades disponíveis. Sem créditos gratuitos diários.") : data.credit_transition ? (english ? "No daily free credits. Existing benefits remain valid until expiry." : "Sem créditos gratuitos diários. Os benefícios existentes mantêm-se até ao fim da validade.") : (english ? "Start or answer calls with an active Fortnightly, Essential or Premium plan. Renewals are manual." : "Para iniciar ou atender chamadas, ative o plano Quinzenal, Essencial ou Premium. A renovação é manual.")}</p>

      {data.wallet && <section className="nk-wallet-preview" aria-label={english ? "NKATA Wallet" : "Carteira NKATA"}>
        <div className="nk-wallet-preview__header"><WalletCards size={24}/><div><small>{english ? "NKATA Wallet" : "Carteira NKATA"}</small><strong>{data.wallet.saldo} {english ? "credits" : "créditos"}</strong></div></div>
        {data.welcome_bonus?.enabled && <div className="nk-wallet-welcome"><span className="nk-wallet-welcome__icon"><Sparkles size={20}/></span><div className="nk-wallet-welcome__copy"><strong>{english ? "Welcome bonus" : "Bónus de boas-vindas"}</strong><small>{data.welcome_bonus.credits} {english ? "credits, one time only" : "créditos, uma única vez"}</small>{!data.welcome_bonus.claimable && <small>{data.welcome_bonus.granted ? (english ? "Already granted" : "Já atribuído") : data.welcome_bonus.blocker === "IDENTITY_ALREADY_AWARDED" ? (english ? "This identity has already received a welcome bonus." : "Esta identidade já recebeu um bónus. Contacte o suporte se necessário.") : data.welcome_bonus.blocker === "ACCOUNT_INACTIVE" ? (english ? "Available after account activation." : "Disponível após activação da conta.") : (english ? "Complete NKATA ID verification to receive your bonus." : "Conclua a verificação NKATA ID para receber o seu bónus.")}</small>}{bonusMessage && <small role="alert">{bonusMessage}</small>}</div>{data.welcome_bonus.claimable && <button className="nk-wallet-welcome__claim" type="button" disabled={bonusBusy} onClick={receiveWelcome}>{bonusBusy ? (english ? "Processing…" : "A processar…") : (english ? "Receive credits" : "Receber créditos")}</button>}</div>}
        <p>{data.wallet.catalogo.packs.some(p => p.purchase_enabled) ? (english ? "Choose a top-up. Credits arrive after payment confirmation." : "Escolha uma recarga. Os créditos entram após confirmação do pagamento.") : (english ? "Credit purchases are not available yet." : "As recargas de créditos ainda não estão disponíveis.")}</p>
        {data.payment_simulation && <p role="status"><strong>{english ? "TEST MODE — no real money" : "MODO DE TESTE — nenhum dinheiro real"}</strong></p>}
        <div className="nk-wallet-packs" id="nk-wallet-recharge">{data.wallet.catalogo.packs.map(pack => <article key={pack.code}><strong>{pack.label}</strong><b>{pack.credits} {english ? "credits" : "créditos"}</b><span>{pack.price_mzn} MT</span>{!!pack.bonus && <small>+{pack.bonus} {english ? "bonus included" : "de bónus incluídos"}</small>}<button type="button" disabled={!pack.purchase_enabled || paymentBusy} onClick={() => buy(pack.product)}>{pack.purchase_enabled ? (data.payment_simulation ? (english ? "Simulate top-up" : "Simular recarga") : (english ? "Top up" : "Recarregar")) : (english ? "Coming soon" : "Em breve")}</button></article>)}</div>
        <WalletDashboard english={english} simulation={data.payment_simulation} refreshKey={data} onRecharge={() => document.getElementById("nk-wallet-recharge")?.scrollIntoView({behavior:"smooth", block:"center"})} />
      </section>}
      {!data.credit_only && (!data.credit_transition || current.expires_at || recharge.balance > 0) && <div className="nk-plan-current">
        <div className="nk-plan-current__identity">
          <span><CurrentIcon size={24} /></span>
          <div>
            <small>{data.credit_transition ? (english ? "Previous benefit" : "Benefício anterior") : (english ? "Current plan" : "Plano atual")}</small>
            <strong>{planLabel(current, english)}</strong>
            <em>{current.legacy_origin === "PAYSUITE" ? (english ? "Paid plan" : "Plano pago") : current.legacy_origin === "ADMINISTRATIVA" ? (english ? "Administratively granted" : "Atribuído pela administração") : current.is_launch_bonus ? (english ? "Launch promotion" : "Promoção de lançamento") : current.paid ? (english ? "Active benefit" : "Benefício activo") : (english ? "Free access" : "Acesso gratuito")}</em>
            {current.expires_at && <small>{english ? "Valid until: " : "Válido até: "}{new Date(current.expires_at).toLocaleString(english ? "en-GB" : "pt-PT")}</small>}
          </div>
        </div>

        {(!data.credit_transition || current.expires_at) && <div className="nk-plan-current__usage">
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
        </div>}

        <div className="nk-plan-current__recharge">
          <span><WalletCards size={19} /></span>
          <div><small>{english ? "Top-up balance" : "Saldo de recarga"}</small><strong>{recharge.balance} {english ? "signals" : "sinais"}</strong></div>
        </div>
      </div>}

      {!data.credit_transition && <><div className="nk-plan-catalog" aria-label={english ? "Subscription plans" : "Planos de subscrição"}>
        {[...data.available_plans].sort((a, b) => ({"LIVRE": 0, "QUINZENAL": 1, "ESSENCIAL": 2, "PREMIUM": 3}[a.code] ?? 9) - ({"LIVRE": 0, "QUINZENAL": 1, "ESSENCIAL": 2, "PREMIUM": 3}[b.code] ?? 9)).map((plan) => {
          const Icon = planIcon[plan.code] || Sparkles;
          const active = plan.code === current.code && !current.is_launch_bonus;
          return (
            <article key={plan.code} className={`nk-plan-card ${active ? "is-current" : ""} ${plan.code === "ESSENCIAL" ? "is-popular" : ""}`}>
              <div className="nk-plan-card__top">
                <span><Icon size={21} /></span>
                <div className="nk-plan-card__badges">
                  {plan.code === "ESSENCIAL" && <em className="nk-plan-card__popular">{english ? "Most popular" : "Mais popular"}</em>}
                  {active && <em>{english ? "Current" : "Atual"}</em>}
                </div>
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
      </>}
      <section id="nkata-payment-history" aria-label={english ? "NKATA payments" : "Pagamentos NKATA"}>
        <h3>{english ? "NKATA payment history" : "Histórico de pagamentos NKATA"}</h3>
        <p>{english ? "Benefits activate only after payment confirmation." : "Os benefícios são ativados apenas após confirmação do pagamento."}</p>
        {payments.some(blocksCheckout) && (
          <p role="status">{english ? "A payment awaits confirmation. Review its status before choosing another top-up." : "Existe um pagamento por confirmar. Consulte o seu estado antes de escolher outra recarga."}</p>
        )}
        {paymentMessage && <p role="status">{paymentMessage}</p>}
        {payments.map((order) => (
          <article key={order.id} className="nk-plan-card">
            <strong>{order.wallet_credits ? `${order.wallet_credits} ${english ? "credits" : "créditos"}` : order.product} · {order.amount_mzn} MT {order.simulated ? (english ? "(test value)" : "(valor de teste)") : ""}</strong>
            <small>{order.reference}{order.simulated ? (english ? " · SIMULATED" : " · SIMULADO") : ""}</small>
            {data.payment_simulation && order.simulated && order.status==="PENDENTE" && <div className="nk-wallet-packs"><button type="button" disabled={paymentBusy} onClick={()=>finishSimulation(order,"completed")}>{english ? "Simulate success" : "Simular confirmação"}</button><button type="button" disabled={paymentBusy} onClick={()=>finishSimulation(order,"failed")}>{english ? "Simulate failure" : "Simular falha"}</button></div>}
            <p>{({PAGO: order.simulated ? (english ? "Simulation confirmed" : "Simulação confirmada") : (english ? "Paid" : "Pago"), PENDENTE: english ? "Pending" : "Pendente", FALHOU: english ? "Failed" : "Falhou", CRIADO: english ? "Preparing" : "A preparar", INCERTO: english ? "Awaiting verification" : "A aguardar verificação", REVISAO: english ? "Under review" : "Em revisão"})[order.status] || order.status}</p>
            {order.retired_product && <small>{english ? "Historical product — no longer for sale." : "Produto antigo — indisponível para compra."}</small>}
            {!order.retired_product && order.checkout_url && !["PAGO", "FALHOU"].includes(order.status) && (
              <a className="nk-plan-payment-continue" href={order.checkout_url}>
                {english ? "Continue payment" : "Continuar pagamento"}
              </a>
            )}
          </article>
        ))}
      </section>
    </section>
  );
}
