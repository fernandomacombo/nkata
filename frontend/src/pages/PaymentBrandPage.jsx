import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, CreditCard, LockKeyhole, ShieldCheck, Sparkles } from "lucide-react";
import { checkPayment, fetchPayments } from "../services/planApi.js";

const labels = {
  LIVRE: "Livre", QUINZENAL: "Quinzenal", ESSENCIAL: "Essencial",
  PREMIUM: "Premium", RECARGA10: "Recarga de 10 sinais",
};
const allowedCheckoutHosts = new Set(["paysuite.tech"]);

function approvedCheckoutUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && allowedCheckoutHosts.has(url.hostname) && !url.username && !url.password && !url.port
      ? url.href : "";
  } catch { return ""; }
}

export default function PaymentBrandPage() {
  const id = new URLSearchParams(window.location.search).get("pedido");
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchPayments().then((data) => {
      if (!active) return;
      setOrder((data.results || []).find((item) => item.id === id) || null);
    }).catch((cause) => { if (active) setError(cause.message || "Não foi possível consultar o pedido."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  async function verify() {
    if (!order) return;
    setChecking(true);
    setError("");
    try { setOrder(await checkPayment(order.id)); }
    catch (cause) { setError(cause.message || "Não foi possível verificar o pagamento."); }
    finally { setChecking(false); }
  }

  const checkout = approvedCheckoutUrl(order?.checkout_url);
  const amount = Number(order?.amount_mzn);
  const amountLabel = Number.isFinite(amount)
    ? new Intl.NumberFormat("pt-MZ", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount)
    : "—";
  const canContinue = order?.status === "PENDENTE" && checkout;

  return (
    <main className="nk-payment-page">
      <header className="nk-payment-header">
        <a className="nk-payment-logo" href="/" aria-label="NKATA — Início"><span className="nk-payment-monogram">NK</span><strong>NKATA</strong></a>
        <a className="nk-payment-back" href="/conta/"><ArrowLeft size={17} /> Voltar à conta</a>
      </header>

      <div className="nk-payment-layout">
        <aside className="nk-payment-summary">
          <div className="nk-payment-summary__mark"><Sparkles size={27} /></div>
          <p className="nk-payment-kicker">O seu pedido NKATA</p>
          <h1>{order ? (labels[order.product] || "Pagamento NKATA") : "Pagamento NKATA"}</h1>
          <p className="nk-payment-summary__description">Uma experiência discreta, segura e pensada para si.</p>
          <div className="nk-payment-summary__total"><span>Total do pedido</span><strong>{amountLabel} MT</strong></div>
          {order && <p className="nk-payment-reference">Referência: {order.reference}</p>}
          <div className="nk-payment-summary__decoration" aria-hidden="true" />
        </aside>

        <section className="nk-payment-details" aria-live="polite">
          <span className="nk-payment-eyebrow"><LockKeyhole size={14} /> Checkout protegido</span>
          <h2>Confirme o seu pagamento</h2>
          <p>Revise o valor e continue para escolher o método de pagamento no ambiente seguro da PaySuite.</p>
          {loading ? <p>A carregar o pedido...</p> : error && !order ? (
            <p role="alert" className="nk-payment-alert">{error}</p>
          ) : !order ? (
            <div className="nk-payment-alert">Pedido não encontrado nesta conta. Inicie a compra a partir dos seus planos.</div>
          ) : (
            <>
              <div className="nk-payment-order">
                <div><small>Produto</small><strong>{labels[order.product] || order.product}</strong></div>
                <div><small>Montante</small><strong>{amountLabel} MT</strong></div>
                <div><small>Estado</small><strong>{({ PENDENTE: "Aguardando pagamento", PAGO: "Pago", FALHOU: "Não concluído", CRIADO: "A preparar", INCERTO: "Em verificação", REVISAO: "Em revisão" })[order.status] || order.status}</strong></div>
              </div>
              <h3>Formas de pagamento</h3>
              <p className="nk-payment-method-note">A disponibilidade e seleção final são apresentadas pela PaySuite.</p>
              <div className="nk-payment-methods" aria-label="Métodos anunciados pelo prestador">
                {["M-Pesa", "e-Mola", "mKesh", "Cartão", "Referência"].map((method) =>
                  <span key={method}><CreditCard size={16} />{method}</span>)}
              </div>
              {error && <p role="alert" className="nk-payment-alert">{error}</p>}
              {order.status === "PAGO" ? <p className="nk-payment-success"><CheckCircle2 size={20} /> Pagamento confirmado.</p>
                : canContinue ? (
                  <a className="nk-payment-continue" href={checkout} rel="noreferrer">
                    Continuar no pagamento seguro <ArrowRight size={19} />
                  </a>
                ) : <p className="nk-payment-alert">Este pedido não tem checkout disponível. Verifique o seu estado antes de tentar novamente.</p>}
              {!["PAGO", "FALHOU"].includes(order.status) && (
                <button type="button" className="nk-payment-verify" disabled={checking} onClick={verify}>
                  {checking ? "A verificar..." : "Verificar estado do pagamento"}
                </button>
              )}
            </>
          )}
          <p className="nk-payment-disclosure"><ShieldCheck size={17} /> O pagamento é processado pela PaySuite. No checkout externo poderá aparecer a identificação legal do comerciante. O NKATA não recolhe dados de cartão nesta página.</p>
        </section>
      </div>
    </main>
  );
}
