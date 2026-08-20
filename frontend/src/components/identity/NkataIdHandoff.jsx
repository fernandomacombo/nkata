import { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Clock3,
  ExternalLink,
  LoaderCircle,
  MessageCircle,
  MonitorSmartphone,
  QrCode,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
import {
  createNkataIdSession,
  fetchNkataIdSession,
  nkataIdQrUrl,
} from "../../services/api.js";

function phoneCaptureUrl(token) {
  return `${window.location.origin}/verificar-identidade/${token}/`;
}

export default function NkataIdHandoff({ email, age, value, onChange, error }) {
  const [accepted, setAccepted] = useState(Boolean(value?.token));
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState("");
  const token = value?.token || "";
  const captureUrl = useMemo(() => (token ? phoneCaptureUrl(token) : ""), [token]);

  useEffect(() => {
    if (!token || value?.can_submit || value?.expired) return undefined;
    const controller = new AbortController();
    const refresh = async () => {
      try {
        const result = await fetchNkataIdSession(token, { signal: controller.signal });
        onChange?.(result);
      } catch (requestError) {
        if (requestError.name !== "AbortError") {
          setLocalError(requestError.message || "Não foi possível atualizar o NKATA ID.");
        }
      }
    };
    refresh();
    const intervalId = window.setInterval(refresh, 5000);
    return () => {
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, [onChange, token, value?.can_submit, value?.expired]);

  const begin = async () => {
    if (!accepted || loading) return;
    setLoading(true);
    setLocalError("");
    try {
      const result = await createNkataIdSession({ email, age });
      onChange?.(result);
    } catch (requestError) {
      setLocalError(requestError.message || "Não foi possível iniciar o NKATA ID.");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <section className="nk-id-start">
        <span className="nk-id-mark"><ShieldCheck size={28} /></span>
        <small>NKATA ID</small>
        <h3>Verifique a sua identidade.</h3>
        <p>
          Vamos confirmar o BI e duas selfies privadas. A câmara do telemóvel
          ajuda a obter imagens mais nítidas.
        </p>
        <div className="nk-id-start__checks">
          <span><CheckCircle2 size={17} /> Documento inteiro e legível</span>
          <span><CheckCircle2 size={17} /> Selfie frontal comparável ao BI</span>
          <span><CheckCircle2 size={17} /> Análise automática antes da equipa</span>
        </div>
        <label className="nk-id-consent">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(event) => setAccepted(event.target.checked)}
          />
          <span>
            <strong>Autorizo a verificação do documento e do rosto.</strong>
            <small>As evidências ficam privadas e não aparecem no perfil.</small>
          </span>
        </label>
        {(localError || error) && <div className="nk-id-error">{localError || error}</div>}
        <button
          type="button"
          className="nk-button nk-button--wine"
          onClick={begin}
          disabled={!accepted || loading}
        >
          {loading ? <LoaderCircle className="is-spinning" size={18} /> : <Smartphone size={18} />}
          {loading ? "A preparar…" : "Preparar NKATA ID"}
        </button>
      </section>
    );
  }

  if (value?.can_submit) {
    return (
      <section className="nk-id-complete">
        <span><CheckCircle2 size={34} /></span>
        <small>NKATA ID</small>
        <h3>Capturas concluídas.</h3>
        <p>
          {value.automatically_approved
            ? "A identidade passou pelas verificações automáticas."
            : "As imagens passaram pelo controlo de qualidade e seguiram para a análise final."}
        </p>
        <div>
          <strong>{value.status_label}</strong>
          <small>Risco inicial: {String(value.risk || "indefinido").toLowerCase()}</small>
        </div>
      </section>
    );
  }

  const whatsappText = encodeURIComponent(
    `Continue a verificação NKATA ID neste endereço seguro: ${captureUrl}`,
  );
  const smsText = encodeURIComponent(`NKATA ID: ${captureUrl}`);

  return (
    <section className="nk-id-handoff">
      <header>
        <span><MonitorSmartphone size={25} /></span>
        <div>
          <small>NKATA ID</small>
          <h3>Continue no seu telemóvel.</h3>
          <p>Use a câmara traseira para fotografar o BI com mais nitidez.</p>
        </div>
      </header>

      <div className="nk-id-handoff__grid">
        <div className="nk-id-qr">
          <img src={nkataIdQrUrl(token)} alt="Código QR seguro do NKATA ID" />
          <strong><QrCode size={16} /> Leia este código QR</strong>
          <small><Clock3 size={14} /> Sessão temporária e privada</small>
        </div>

        <div className="nk-id-handoff__instructions">
          <ol>
            <li><span>1</span> Abra a câmara do telemóvel.</li>
            <li><span>2</span> Leia o código QR.</li>
            <li><span>3</span> Fotografe o BI e faça as selfies.</li>
          </ol>
          <div className="nk-id-share">
            <a href={`sms:?&body=${smsText}`}><MessageCircle size={16} /> Enviar por SMS</a>
            <a href={`https://wa.me/?text=${whatsappText}`} target="_blank" rel="noreferrer">
              <MessageCircle size={16} /> Enviar por WhatsApp
            </a>
          </div>
          <button type="button" onClick={() => window.open(captureUrl, "_blank", "noopener,noreferrer")}>
            <Smartphone size={17} /> Continuar neste dispositivo <ExternalLink size={14} />
          </button>
        </div>
      </div>

      <footer>
        <LoaderCircle size={17} className="is-spinning" />
        <span>
          <strong>Aguardando as capturas…</strong>
          <small>Esta página será atualizada automaticamente.</small>
        </span>
      </footer>
      {localError && <div className="nk-id-error">{localError}</div>}
    </section>
  );
}
