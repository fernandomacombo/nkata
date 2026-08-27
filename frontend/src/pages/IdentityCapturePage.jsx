import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  Camera,
  Check,
  CheckCircle2,
  FileImage,
  LoaderCircle,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  Smartphone,
  Sun,
  UserRoundCheck,
} from "lucide-react";
import {
  fetchNkataIdSession,
  uploadNkataIdCapture,
} from "../services/api.js";
import { fitNkataIdCaptureDimensions } from "../services/nkataIdRuntime.js";

const CAPTURE_COUNTDOWN_SECONDS = 3;
const MAX_CAPTURE_SIDE = 1280;
const CAPTURE_JPEG_QUALITY = 0.84;

const CAPTURES = {
  bi_frente: {
    title: "Fotografe a frente do BI",
    help: "Coloque o documento inteiro dentro da moldura.",
    facingMode: "environment",
    icon: FileImage,
    stage: 1,
  },
  bi_verso: {
    title: "Agora fotografe o verso",
    help: "Evite sombras, dedos sobre o documento e reflexos.",
    facingMode: "environment",
    icon: FileImage,
    stage: 1,
  },
  selfie_ao_vivo: {
    title: "Faça uma selfie frontal",
    help: "Olhe diretamente para a câmara, sem óculos escuros ou filtros.",
    facingMode: "user",
    icon: UserRoundCheck,
    stage: 2,
  },
  selfie_desafio: {
    title: "Conclua o desafio ao vivo",
    help: "Siga a instrução apresentada antes de tirar a fotografia.",
    facingMode: "user",
    icon: UserRoundCheck,
    stage: 2,
  },
};

function stopStream(stream) {
  stream?.getTracks?.().forEach((track) => track.stop());
}

export default function IdentityCapturePage({ token, onExit }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const countdownTimerRef = useRef(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cameraStarting, setCameraStarting] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [qualityMessages, setQualityMessages] = useState([]);
  const [useAsProfilePhoto, setUseAsProfilePhoto] = useState(false);
  const [captureCountdown, setCaptureCountdown] = useState(null);

  const captureType = session?.current_capture || "";
  const config = CAPTURES[captureType];
  const complete = Boolean(session?.capture_complete && session?.can_submit);
  const progress = useMemo(() => {
    const count = session?.completed_captures?.length || 0;
    return Math.min(100, Math.round((count / 4) * 100));
  }, [session?.completed_captures]);

  useEffect(() => {
    const controller = new AbortController();
    fetchNkataIdSession(token, { signal: controller.signal })
      .then(setSession)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          setError(requestError.message || "Não foi possível abrir esta sessão.");
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [token]);

  const clearCaptureCountdown = () => {
    if (countdownTimerRef.current !== null) {
      window.clearInterval(countdownTimerRef.current);
      countdownTimerRef.current = null;
    }
    setCaptureCountdown(null);
  };

  useEffect(() => () => {
    stopStream(streamRef.current);
    if (countdownTimerRef.current !== null) {
      window.clearInterval(countdownTimerRef.current);
    }
  }, []);

  useEffect(() => {
    stopStream(streamRef.current);
    streamRef.current = null;
    setCameraReady(false);
    setQualityMessages([]);
    clearCaptureCountdown();
  }, [captureType]);

  const startCamera = async () => {
    if (!config || cameraStarting) return;
    setCameraStarting(true);
    setError("");
    setQualityMessages([]);
    try {
      stopStream(streamRef.current);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: config.facingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraReady(true);
    } catch (_cameraError) {
      setError("Não foi possível abrir a câmara. Use o botão para escolher ou tirar uma fotografia.");
    } finally {
      setCameraStarting(false);
    }
  };

  const uploadCapture = async (file) => {
    if (!file || uploading || !captureType) return;
    setUploading(true);
    setError("");
    setQualityMessages([]);
    try {
      const result = await uploadNkataIdCapture(token, captureType, file, {
        useAsProfilePhoto: captureType === "selfie_ao_vivo" && useAsProfilePhoto,
      });
      setSession(result);
      clearCaptureCountdown();
      stopStream(streamRef.current);
      streamRef.current = null;
      setCameraReady(false);
    } catch (requestError) {
      const messages = requestError.payload?.quality?.messages || [];
      setQualityMessages(messages);
      setError(requestError.message || "Não foi possível analisar esta fotografia.");
    } finally {
      setUploading(false);
    }
  };

  const captureFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth || uploading) return;
    const dimensions = fitNkataIdCaptureDimensions(
      video.videoWidth,
      video.videoHeight,
      MAX_CAPTURE_SIDE,
    );
    canvas.width = dimensions.width;
    canvas.height = dimensions.height;
    const context = canvas.getContext("2d", { alpha: false });
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) return;
      uploadCapture(new File([blob], `${captureType}.jpg`, { type: "image/jpeg" }));
    }, "image/jpeg", CAPTURE_JPEG_QUALITY);
  };

  const beginTimedCapture = () => {
    if (!cameraReady || uploading || captureCountdown !== null) return;
    let remaining = CAPTURE_COUNTDOWN_SECONDS;
    setCaptureCountdown(remaining);
    countdownTimerRef.current = window.setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        window.clearInterval(countdownTimerRef.current);
        countdownTimerRef.current = null;
        setCaptureCountdown(null);
        captureFrame();
        return;
      }
      setCaptureCountdown(remaining);
    }, 1000);
  };

  if (loading) {
    return (
      <main className="nk-id-mobile nk-id-mobile--center">
        <LoaderCircle className="is-spinning" size={32} />
        <strong>A abrir o NKATA ID…</strong>
      </main>
    );
  }

  if (!session || session.expired || error && !config && !complete) {
    return (
      <main className="nk-id-mobile nk-id-mobile--center">
        <span className="nk-id-mobile__brand">NK <strong>NKATA ID</strong></span>
        <ShieldCheck size={42} />
        <h1>Sessão indisponível</h1>
        <p>{error || "Esta verificação expirou. Volte ao computador e crie uma nova sessão."}</p>
        <button type="button" className="nk-button nk-button--wine" onClick={onExit}>Voltar ao NKATA</button>
      </main>
    );
  }

  if (complete) {
    return (
      <main className="nk-id-mobile nk-id-mobile--center nk-id-mobile--success">
        <span className="nk-id-mobile__brand">NK <strong>NKATA ID</strong></span>
        <span className="nk-id-success-icon"><CheckCircle2 size={42} /></span>
        <small>IDENTIDADE RECEBIDA</small>
        <h1>Capturas concluídas</h1>
        <p>
          {session.automatically_approved
            ? "A verificação automática foi aprovada. Já pode regressar ao pedido de acesso."
            : "A qualidade foi confirmada. O caso seguirá apenas para a análise final necessária."}
        </p>
        <div className="nk-id-mobile__result">
          <strong>{session.status_label}</strong>
          <span><Check size={15} /> Documento protegido</span>
          <span><Check size={15} /> Selfies recebidas</span>
        </div>
        <button type="button" className="nk-button nk-button--wine" onClick={onExit}>
          Voltar ao pedido
        </button>
      </main>
    );
  }

  const Icon = config?.icon || Camera;
  const selfieChallenge = captureType === "selfie_desafio" ? session.selfie_challenge : "";

  return (
    <main className="nk-id-mobile">
      <header className="nk-id-mobile__header">
        <button type="button" onClick={onExit} aria-label="Voltar"><ArrowLeft size={20} /></button>
        <span className="nk-id-mobile__brand">NK <strong>NKATA ID</strong></span>
        <span><LockKeyhole size={16} /> Privado</span>
      </header>

      <div className="nk-id-mobile__progress" aria-label={`${progress}% concluído`}>
        <span style={{ width: `${progress}%` }} />
      </div>

      <section className="nk-id-mobile__copy">
        <small>PASSO {config.stage} DE 3</small>
        <h1>{config.title}</h1>
        <p>{selfieChallenge || config.help}</p>
      </section>

      <section className={`nk-id-camera ${config.facingMode === "user" ? "is-selfie" : "is-document"}`}>
        <video ref={videoRef} autoPlay muted playsInline />
        {!cameraReady && (
          <div className="nk-id-camera__empty">
            <Icon size={38} />
            <strong>A câmara ainda não está ativa</strong>
            <small>Permita o acesso para obter a melhor qualidade.</small>
          </div>
        )}
        <div className="nk-id-camera__guide" aria-hidden="true"><span /></div>
        {captureCountdown !== null && (
          <div className="nk-id-camera__countdown" role="status" aria-live="assertive">
            <strong>{captureCountdown}</strong>
            <span>Mantenha o telefone firme</span>
          </div>
        )}
      </section>
      <canvas ref={canvasRef} hidden />

      <div className="nk-id-quality-hints">
        <span><Sun size={15} /> Boa iluminação</span>
        <span><Smartphone size={15} /> Telefone firme</span>
        <span><Check size={15} /> Sem reflexos</span>
      </div>

      {captureType === "selfie_ao_vivo" && (
        <label className="nk-id-photo-choice">
          <input
            type="checkbox"
            checked={useAsProfilePhoto}
            onChange={(event) => setUseAsProfilePhoto(event.target.checked)}
          />
          <span>
            <strong>Usar também como fotografia principal</strong>
            <small>Será publicada apenas depois da aprovação do perfil.</small>
          </span>
        </label>
      )}

      {(error || qualityMessages.length > 0) && (
        <div className="nk-id-capture-error" role="alert">
          <strong>{error}</strong>
          {qualityMessages.map((message) => <span key={message}>{message}</span>)}
        </div>
      )}

      <footer className="nk-id-mobile__actions">
        {!cameraReady ? (
          <button type="button" className="nk-button nk-button--wine" onClick={startCamera} disabled={cameraStarting}>
            {cameraStarting ? <LoaderCircle className="is-spinning" size={18} /> : <Camera size={18} />}
            {cameraStarting ? "A abrir…" : "Abrir câmara"}
          </button>
        ) : (
          <button
            type="button"
            className="nk-button nk-button--wine"
            onClick={beginTimedCapture}
            disabled={uploading || captureCountdown !== null}
          >
            {uploading ? <LoaderCircle className="is-spinning" size={18} /> : <Camera size={18} />}
            {uploading
              ? "A verificar qualidade…"
              : captureCountdown !== null
                ? `A capturar em ${captureCountdown}…`
                : "Capturar em 3 segundos"}
          </button>
        )}

        <label className="nk-id-file-fallback">
          <RefreshCw size={16} /> Outra forma
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture={config.facingMode === "user" ? "user" : "environment"}
            disabled={uploading || captureCountdown !== null}
            onChange={(event) => uploadCapture(event.target.files?.[0])}
          />
        </label>
      </footer>
    </main>
  );
}
