import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  Camera,
  Check,
  CheckCircle2,
  FileImage,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  Smartphone,
  Sun,
  UserRoundCheck,
} from "lucide-react";
import {
  fetchNkataIdSession,
  previewNkataIdCapture,
  uploadNkataIdCapture,
} from "../services/api.js";
import {
  advanceNkataIdDetectionStability,
  fitNkataIdCaptureDimensions,
} from "../services/nkataIdRuntime.js";

const MAX_CAPTURE_SIDE = 1280;
const CAPTURE_JPEG_QUALITY = 0.84;
const PREVIEW_MAX_SIDE = 480;
const PREVIEW_JPEG_QUALITY = 0.62;
const PREVIEW_INTERVAL_MS = 850;

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

function frameFile(video, canvas, captureType, { maxSide, quality, suffix = "" }) {
  if (!video || !canvas || !video.videoWidth || !video.videoHeight) {
    return Promise.resolve(null);
  }
  const dimensions = fitNkataIdCaptureDimensions(
    video.videoWidth,
    video.videoHeight,
    maxSide,
  );
  canvas.width = dimensions.width;
  canvas.height = dimensions.height;
  const context = canvas.getContext("2d", { alpha: false });
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        resolve(null);
        return;
      }
      resolve(new File(
        [blob],
        `${captureType}${suffix}.jpg`,
        { type: "image/jpeg" },
      ));
    }, "image/jpeg", quality);
  });
}

export default function IdentityCapturePage({ token, onExit }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const activeFacingModeRef = useRef("");
  const cameraStartingRef = useRef(false);
  const previewTimerRef = useRef(null);
  const previewControllerRef = useRef(null);
  const detectionStabilityRef = useRef({ captureType: "", count: 0 });
  const automaticCaptureRef = useRef(false);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cameraStarting, setCameraStarting] = useState(false);
  const [cameraActivated, setCameraActivated] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [qualityMessages, setQualityMessages] = useState([]);
  const [useAsProfilePhoto, setUseAsProfilePhoto] = useState(false);
  const [detection, setDetection] = useState({
    detected: false,
    ready: false,
    message: "Aguardando a câmara ao vivo.",
  });

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

  const stopPreviewAnalysis = () => {
    if (previewTimerRef.current !== null) {
      window.clearTimeout(previewTimerRef.current);
      previewTimerRef.current = null;
    }
    previewControllerRef.current?.abort?.();
    previewControllerRef.current = null;
  };

  useEffect(() => () => {
    stopPreviewAnalysis();
    stopStream(streamRef.current);
  }, []);

  useEffect(() => {
    detectionStabilityRef.current = { captureType, count: 0 };
    automaticCaptureRef.current = false;
    setQualityMessages([]);
    setDetection({
      detected: false,
      ready: false,
      message: captureType.startsWith("selfie")
        ? "A procurar um rosto na câmara…"
        : "A procurar o BI na câmara…",
    });
  }, [captureType]);

  const startCamera = async (requestedFacingMode = config?.facingMode) => {
    if (!requestedFacingMode || cameraStartingRef.current) return;
    const currentTrack = streamRef.current?.getVideoTracks?.()[0];
    if (
      currentTrack?.readyState === "live"
      && activeFacingModeRef.current === requestedFacingMode
    ) {
      if (videoRef.current) {
        videoRef.current.srcObject = streamRef.current;
        await videoRef.current.play();
      }
      setCameraReady(true);
      return;
    }
    cameraStartingRef.current = true;
    setCameraStarting(true);
    setCameraReady(false);
    setError("");
    setQualityMessages([]);
    try {
      stopPreviewAnalysis();
      stopStream(streamRef.current);
      streamRef.current = null;
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: requestedFacingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      streamRef.current = stream;
      activeFacingModeRef.current = requestedFacingMode;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraActivated(true);
      setCameraReady(true);
    } catch (_cameraError) {
      setError("Não foi possível abrir a câmara ao vivo. Confirme a permissão da câmara e tente novamente.");
    } finally {
      cameraStartingRef.current = false;
      setCameraStarting(false);
    }
  };

  useEffect(() => {
    if (!cameraActivated || !config || complete) return;
    startCamera(config.facingMode);
  }, [captureType, cameraActivated, complete, config?.facingMode]);

  const uploadCapture = async (file, requestedCaptureType, liveCaptureProof) => {
    if (!file || uploading || !requestedCaptureType || !liveCaptureProof) return;
    setUploading(true);
    stopPreviewAnalysis();
    setError("");
    setQualityMessages([]);
    setDetection((current) => ({
      ...current,
      ready: true,
      message: "A verificar e guardar a captura ao vivo…",
    }));
    try {
      const result = await uploadNkataIdCapture(token, requestedCaptureType, file, {
        useAsProfilePhoto: requestedCaptureType === "selfie_ao_vivo" && useAsProfilePhoto,
        liveCaptureProof,
      });
      setSession(result);
      if (result.capture_complete) {
        stopStream(streamRef.current);
        streamRef.current = null;
        activeFacingModeRef.current = "";
        setCameraReady(false);
      }
    } catch (requestError) {
      const messages = requestError.payload?.quality?.messages || [];
      setQualityMessages(messages);
      setError(requestError.message || "Não foi possível analisar esta fotografia.");
      automaticCaptureRef.current = false;
      detectionStabilityRef.current = { captureType: requestedCaptureType, count: 0 };
    } finally {
      setUploading(false);
    }
  };

  const captureFrame = async (requestedCaptureType, liveCaptureProof) => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth || uploading) return;
    const file = await frameFile(video, canvas, requestedCaptureType, {
      maxSide: MAX_CAPTURE_SIDE,
      quality: CAPTURE_JPEG_QUALITY,
    });
    await uploadCapture(file, requestedCaptureType, liveCaptureProof);
  };

  useEffect(() => {
    if (!cameraReady || uploading || complete || !captureType) return undefined;
    let stopped = false;

    const schedule = (delay = PREVIEW_INTERVAL_MS) => {
      if (stopped || automaticCaptureRef.current) return;
      previewTimerRef.current = window.setTimeout(analyseFrame, delay);
    };

    const analyseFrame = async () => {
      if (stopped || automaticCaptureRef.current) return;
      const file = await frameFile(videoRef.current, canvasRef.current, captureType, {
        maxSide: PREVIEW_MAX_SIDE,
        quality: PREVIEW_JPEG_QUALITY,
        suffix: "-preview",
      });
      if (!file || stopped) {
        schedule(500);
        return;
      }

      const controller = new AbortController();
      previewControllerRef.current = controller;
      try {
        const result = await previewNkataIdCapture(token, captureType, file, {
          signal: controller.signal,
        });
        if (stopped) return;
        setDetection(result);
        const stability = advanceNkataIdDetectionStability(
          detectionStabilityRef.current,
          result,
          captureType,
        );
        detectionStabilityRef.current = stability;
        if (stability.shouldCapture && result.live_capture_proof) {
          automaticCaptureRef.current = true;
          setDetection({ ...result, message: "Enquadramento confirmado. A capturar…" });
          await captureFrame(captureType, result.live_capture_proof);
          return;
        }
        schedule();
      } catch (requestError) {
        if (stopped || requestError.name === "AbortError") return;
        setDetection((current) => ({
          ...current,
          ready: false,
          message: requestError.status === 429
            ? "A deteção vai retomar dentro de instantes."
            : "A confirmar o enquadramento…",
        }));
        schedule(requestError.status === 429 ? 4000 : 1400);
      } finally {
        if (previewControllerRef.current === controller) {
          previewControllerRef.current = null;
        }
      }
    };

    schedule(450);
    return () => {
      stopped = true;
      stopPreviewAnalysis();
    };
  }, [cameraReady, captureType, uploading, complete, token]);

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

      <section className={`nk-id-camera ${config.facingMode === "user" ? "is-selfie" : "is-document"} ${detection.detected ? "has-detection" : ""} ${detection.ready ? "is-ready" : ""}`}>
        <video ref={videoRef} autoPlay muted playsInline />
        {!cameraReady && (
          <div className="nk-id-camera__empty">
            <Icon size={38} />
            <strong>A câmara ainda não está ativa</strong>
            <small>Permita o acesso para obter a melhor qualidade.</small>
          </div>
        )}
        <div className="nk-id-camera__guide" aria-hidden="true">
          {config.facingMode === "user" && (
            <svg
              className="nk-id-selfie-outline"
              viewBox="0 0 260 320"
              preserveAspectRatio="xMidYMid meet"
            >
              <path d="M130 27C85 27 55 62 55 108C55 157 87 190 130 190C173 190 205 157 205 108C205 62 175 27 130 27Z" />
              <path d="M27 298C29 239 70 205 130 205C190 205 231 239 233 298" />
            </svg>
          )}
        </div>
        {cameraReady && (
          <div className="nk-id-camera__status" role="status" aria-live="polite">
            <span />
            {detection.message}
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
          <button type="button" className="nk-button nk-button--wine" onClick={() => startCamera(config.facingMode)} disabled={cameraStarting}>
            {cameraStarting ? <LoaderCircle className="is-spinning" size={18} /> : <Camera size={18} />}
            {cameraStarting ? "A abrir…" : cameraActivated ? "Retomar câmara" : "Ativar câmara ao vivo"}
          </button>
        ) : (
          <div className={`nk-id-auto-status ${detection.ready ? "is-ready" : ""}`}>
            <LoaderCircle className={uploading ? "is-spinning" : "nk-id-scanner"} size={20} />
            <span>
              <strong>{uploading ? "A guardar captura" : "Deteção automática ativa"}</strong>
              <small>{detection.message}</small>
            </span>
          </div>
        )}
      </footer>
    </main>
  );
}
