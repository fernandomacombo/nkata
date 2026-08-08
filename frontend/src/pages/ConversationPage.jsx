import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  Ban,
  Flag,
  Link2Off,
  LockKeyhole,
  MapPin,
  MessageCircle,
  Mic,
  MoreHorizontal,
  Pause,
  Play,
  Send,
  ShieldCheck,
  Square,
  Trash2,
  UserRound,
} from "lucide-react";
import SafetyDialog from "../components/safety/SafetyDialog.jsx";
import { blockProfile, closeMatch, reportProfile, sendMatchAudio } from "../services/api.js";
import { fetchMyPlan } from "../services/planApi.js";

function formatMessageTime(value) {
  if (!value) return "";

  return new Intl.DateTimeFormat("pt-MZ", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatDuration(value) {
  const seconds = Math.max(0, Math.round(Number(value) || 0));
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

function VoiceNote({ message }) {
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(message.durationSeconds || 0);

  const togglePlayback = async () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (audio.paused) {
      try {
        await audio.play();
      } catch {
        setPlaying(false);
      }
    } else {
      audio.pause();
    }
  };

  return (
    <div className="nk-voice-note">
      <audio
        ref={audioRef}
        src={message.audioUrl}
        preload="metadata"
        crossOrigin="use-credentials"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => {
          setPlaying(false);
          setProgress(0);
        }}
        onLoadedMetadata={(event) => {
          if (Number.isFinite(event.currentTarget.duration)) {
            setDuration(event.currentTarget.duration);
          }
        }}
        onTimeUpdate={(event) => {
          const audio = event.currentTarget;
          setProgress(audio.duration ? (audio.currentTime / audio.duration) * 100 : 0);
        }}
      />

      <button type="button" className="nk-voice-note__play" onClick={togglePlayback}>
        {playing ? <Pause size={17} fill="currentColor" /> : <Play size={17} fill="currentColor" />}
        <span className="sr-only">{playing ? "Pausar nota de voz" : "Reproduzir nota de voz"}</span>
      </button>

      <div className="nk-voice-note__track" aria-hidden="true">
        <span style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
      </div>

      <strong>{formatDuration(duration)}</strong>
    </div>
  );
}

function MessageBubble({ message }) {
  return (
    <div className={`nk-message-row ${message.mine ? "is-mine" : ""}`}>
      <div className={`nk-message-bubble ${message.type === "audio" ? "is-audio" : ""}`}>
        {message.type === "audio" ? (
          <VoiceNote message={message} />
        ) : (
          <p>{message.text}</p>
        )}
        <span>
          {formatMessageTime(message.createdAt)}
          {message.mine && <small>{message.read ? "Lida" : "Enviada"}</small>}
        </span>
      </div>
    </div>
  );
}

export default function ConversationPage({
  match,
  messages,
  loading,
  sending,
  error,
  onBack,
  onSend,
}) {
  const [draft, setDraft] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [safetyMode, setSafetyMode] = useState("");
  const [safetyLoading, setSafetyLoading] = useState(false);
  const [safetyError, setSafetyError] = useState("");
  const [safetyStatus, setSafetyStatus] = useState("");
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [audioPlanLabel, setAudioPlanLabel] = useState("NKATA Livre");
  const [audioNotice, setAudioNotice] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recordedDuration, setRecordedDuration] = useState(0);
  const [previewUrl, setPreviewUrl] = useState("");
  const [sendingAudio, setSendingAudio] = useState(false);
  const [localAudioMessages, setLocalAudioMessages] = useState([]);
  const [previewPlaying, setPreviewPlaying] = useState(false);
  const endRef = useRef(null);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const recordingStartedRef = useRef(0);
  const cancelRecordingRef = useRef(false);
  const previewAudioRef = useRef(null);
  const profile = match?.otherProfile;

  const timeline = useMemo(() => (
    [...messages, ...localAudioMessages].sort((a, b) => (
      new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
    ))
  ), [localAudioMessages, messages]);

  const releaseRecordingResources = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    streamRef.current?.getTracks?.().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
    setRecording(false);
  };

  const clearRecordedAudio = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl("");
    setRecordedBlob(null);
    setRecordedDuration(0);
    setPreviewPlaying(false);
  };

  useEffect(() => {
    setDraft("");
    setMenuOpen(false);
    setSafetyMode("");
    setSafetyError("");
    setSafetyStatus("");
    setAudioNotice("");
    setLocalAudioMessages([]);
    clearRecordedAudio();
    releaseRecordingResources();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [match?.id]);

  useEffect(() => {
    const controller = new AbortController();
    fetchMyPlan({ signal: controller.signal })
      .then((payload) => {
        const currentPlan = payload?.current_plan || {};
        setAudioEnabled(Boolean(currentPlan?.features?.chat_audio));
        setAudioPlanLabel(currentPlan?.label || "NKATA Livre");
      })
      .catch(() => {
        if (!controller.signal.aborted) setAudioEnabled(false);
      });
    return () => controller.abort();
  }, [match?.id]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (timerRef.current) window.clearInterval(timerRef.current);
    streamRef.current?.getTracks?.().forEach((track) => track.stop());
  }, [previewUrl]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [timeline.length, loading]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const text = draft.trim();

    if (!text || sending || recording || recordedBlob) return;

    const sent = await onSend(text);
    if (sent) setDraft("");
  };

  const chooseRecordingMimeType = () => {
    if (typeof MediaRecorder === "undefined") return "";
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/mp4",
      "audio/webm",
      "audio/ogg;codecs=opus",
    ];
    return candidates.find((type) => MediaRecorder.isTypeSupported?.(type)) || "";
  };

  const startRecording = async () => {
    setAudioNotice("");

    if (!audioEnabled) {
      setAudioNotice("Notas de voz estão disponíveis no NKATA Essencial e Premium.");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setAudioNotice("Este dispositivo ou navegador não permite gravar notas de voz.");
      return;
    }

    clearRecordedAudio();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = chooseRecordingMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      chunksRef.current = [];
      cancelRecordingRef.current = false;
      streamRef.current = stream;
      recorderRef.current = recorder;
      recordingStartedRef.current = Date.now();

      recorder.addEventListener("dataavailable", (event) => {
        if (event.data?.size) chunksRef.current.push(event.data);
      });

      recorder.addEventListener("stop", () => {
        const duration = Math.max(1, Math.round((Date.now() - recordingStartedRef.current) / 1000));
        const chunks = chunksRef.current;
        const type = recorder.mimeType || chunks[0]?.type || "audio/webm";
        releaseRecordingResources();

        if (cancelRecordingRef.current || !chunks.length) {
          chunksRef.current = [];
          setRecordingSeconds(0);
          return;
        }

        const blob = new Blob(chunks, { type });
        const url = URL.createObjectURL(blob);
        setRecordedBlob(blob);
        setRecordedDuration(Math.min(180, duration));
        setPreviewUrl(url);
        setRecordingSeconds(0);
        chunksRef.current = [];
      });

      recorder.start(250);
      setRecording(true);
      setRecordingSeconds(0);
      timerRef.current = window.setInterval(() => {
        const elapsed = Math.floor((Date.now() - recordingStartedRef.current) / 1000);
        setRecordingSeconds(Math.min(180, elapsed));
        if (elapsed >= 180 && recorder.state === "recording") recorder.stop();
      }, 500);
    } catch {
      releaseRecordingResources();
      setAudioNotice("Não foi possível aceder ao microfone. Confirme a permissão do navegador.");
    }
  };

  const stopRecording = () => {
    const recorder = recorderRef.current;
    if (recorder?.state === "recording") recorder.stop();
  };

  const cancelRecording = () => {
    cancelRecordingRef.current = true;
    const recorder = recorderRef.current;
    if (recorder?.state === "recording") {
      recorder.stop();
    } else {
      releaseRecordingResources();
    }
    clearRecordedAudio();
    setRecordingSeconds(0);
  };

  const sendRecordedAudio = async () => {
    if (!match?.id || !recordedBlob || sendingAudio) return;

    setSendingAudio(true);
    setAudioNotice("");
    try {
      const message = await sendMatchAudio(match.id, recordedBlob, recordedDuration);
      setLocalAudioMessages((current) => [...current, message]);
      clearRecordedAudio();
    } catch (requestError) {
      setAudioNotice(requestError.message || "Não foi possível enviar a nota de voz.");
    } finally {
      setSendingAudio(false);
    }
  };

  const togglePreview = async () => {
    const audio = previewAudioRef.current;
    if (!audio) return;
    if (audio.paused) {
      try {
        await audio.play();
      } catch {
        setPreviewPlaying(false);
      }
    } else {
      audio.pause();
    }
  };

  const openSafetyAction = (mode) => {
    setMenuOpen(false);
    setSafetyError("");
    setSafetyMode(mode);
  };

  const handleSafetyConfirm = async ({ reason, details } = {}) => {
    if (!match || !profile || !safetyMode) return;

    const currentMode = safetyMode;
    setSafetyLoading(true);
    setSafetyError("");

    try {
      let result;

      if (currentMode === "report") {
        result = await reportProfile(profile.id, { reason, details });
      } else if (currentMode === "block") {
        result = await blockProfile(profile.id);
      } else {
        result = await closeMatch(match.id);
      }

      setSafetyMode("");
      setSafetyStatus(result?.message || "A ação foi concluída.");

      if (["block", "close"].includes(currentMode)) {
        window.setTimeout(() => window.location.assign("/matches/"), 1000);
      } else {
        window.setTimeout(() => setSafetyStatus(""), 3200);
      }
    } catch (requestError) {
      setSafetyError(requestError.message || "Não foi possível concluir esta ação.");
    } finally {
      setSafetyLoading(false);
    }
  };

  if (!match) {
    return (
      <main className="nk-conversation nk-conversation--empty">
        <div className="nk-shell nk-conversation__empty-card">
          <MessageCircle size={30} />
          <h1>Conversa não disponível</h1>
          <p>Volte aos matches e escolha uma conversa.</p>
          <button type="button" className="nk-button nk-button--wine" onClick={onBack}>
            Voltar aos matches
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="nk-conversation">
      <div className="nk-shell nk-conversation__shell">
        <header className="nk-conversation__header">
          <button type="button" className="nk-conversation__back" onClick={onBack}>
            <ArrowLeft size={19} />
            <span>Matches</span>
          </button>

          <div className="nk-conversation__person">
            <span className="nk-conversation__avatar">
              {profile?.foto_url ? (
                <img src={profile.foto_url} alt={`Foto de ${profile.nome_publico}`} />
              ) : (
                <UserRound size={28} />
              )}
            </span>
            <div>
              <strong>{profile?.nome_publico || "Membro NKATA"}</strong>
              <small><MapPin size={12} /> {profile?.cidade || "Moçambique"}</small>
            </div>
          </div>

          <div className="nk-conversation__options">
            <span className="nk-conversation__secure">
              <ShieldCheck size={16} />
              Privada
            </span>
            <button
              type="button"
              className="nk-conversation__options-trigger"
              onClick={() => setMenuOpen((current) => !current)}
              aria-label="Opções da conversa"
              aria-expanded={menuOpen}
            >
              <MoreHorizontal size={20} />
            </button>

            {menuOpen && (
              <div className="nk-conversation__safety-menu">
                <button type="button" onClick={() => openSafetyAction("report")}>
                  <Flag size={16} /> Denunciar perfil
                </button>
                <button type="button" onClick={() => openSafetyAction("close")}>
                  <Link2Off size={16} /> Encerrar ligação
                </button>
                <button
                  type="button"
                  className="is-danger"
                  onClick={() => openSafetyAction("block")}
                >
                  <Ban size={16} /> Bloquear pessoa
                </button>
              </div>
            )}
          </div>
        </header>

        <section className="nk-conversation__body" aria-live="polite">
          <div className="nk-conversation__opening">
            <span><LockKeyhole size={17} /></span>
            <div>
              <strong>É um match</strong>
              <p>Conversem com respeito. Os contactos pessoais não precisam de ser partilhados logo no início.</p>
            </div>
          </div>

          {safetyStatus && (
            <div className="nk-interest-message is-active" role="status">
              {safetyStatus}
            </div>
          )}

          {error && (
            <div className="nk-conversation__error" role="status">
              {error}
            </div>
          )}

          {loading ? (
            <div className="nk-conversation__loading">
              <span />
              <span />
              <span />
            </div>
          ) : timeline.length ? (
            <div className="nk-message-list">
              {timeline.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              <div ref={endRef} />
            </div>
          ) : (
            <div className="nk-conversation__first-message">
              <MessageCircle size={28} />
              <h2>Comece a conversa</h2>
              <p>Uma mensagem simples e respeitosa é suficiente.</p>
              <button
                type="button"
                onClick={() => setDraft("Olá, gostei de conhecer o seu perfil. Como está?")}
              >
                Usar uma sugestão
              </button>
            </div>
          )}
        </section>

        <div className="nk-chat-dock">
          {audioNotice && (
            <div className="nk-chat-dock__notice" role="status">
              <LockKeyhole size={14} />
              <span>{audioNotice}</span>
              {!audioEnabled && <small>{audioPlanLabel}</small>}
            </div>
          )}

          {recording ? (
            <div className="nk-recorder-bar">
              <button type="button" className="nk-recorder-bar__cancel" onClick={cancelRecording} aria-label="Cancelar gravação">
                <Trash2 size={19} />
              </button>
              <div className="nk-recorder-bar__status">
                <span className="nk-recorder-bar__dot" />
                <strong>{formatDuration(recordingSeconds)}</strong>
                <small>A gravar</small>
              </div>
              <button type="button" className="nk-recorder-bar__stop" onClick={stopRecording} aria-label="Terminar gravação">
                <Square size={17} fill="currentColor" />
              </button>
            </div>
          ) : recordedBlob ? (
            <div className="nk-recorder-preview">
              <audio
                ref={previewAudioRef}
                src={previewUrl}
                onPlay={() => setPreviewPlaying(true)}
                onPause={() => setPreviewPlaying(false)}
                onEnded={() => setPreviewPlaying(false)}
              />
              <button type="button" className="nk-recorder-preview__delete" onClick={clearRecordedAudio} aria-label="Apagar gravação">
                <Trash2 size={19} />
              </button>
              <button type="button" className="nk-recorder-preview__play" onClick={togglePreview} aria-label={previewPlaying ? "Pausar gravação" : "Ouvir gravação"}>
                {previewPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
              </button>
              <div className="nk-recorder-preview__meta">
                <strong>Nota de voz</strong>
                <small>{formatDuration(recordedDuration)}</small>
              </div>
              <button
                type="button"
                className="nk-recorder-preview__send"
                onClick={sendRecordedAudio}
                disabled={sendingAudio}
                aria-label="Enviar nota de voz"
              >
                <Send size={18} />
              </button>
            </div>
          ) : (
            <form className="nk-composer" onSubmit={handleSubmit}>
              <button
                type="button"
                className={`nk-composer__mic ${audioEnabled ? "" : "is-locked"}`}
                onClick={startRecording}
                aria-label={audioEnabled ? "Gravar nota de voz" : "Notas de voz exigem plano pago"}
                title={audioEnabled ? "Gravar nota de voz" : "NKATA Essencial ou Premium"}
              >
                <Mic size={20} />
                {!audioEnabled && <LockKeyhole className="nk-composer__mic-lock" size={10} />}
              </button>

              <label>
                <span className="sr-only">Mensagem</span>
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value.slice(0, 1200))}
                  placeholder="Mensagem…"
                  rows={1}
                  disabled={sending}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      handleSubmit(event);
                    }
                  }}
                />
              </label>

              <span className="nk-composer__count">{draft.length}/1200</span>

              <button
                type="submit"
                className="nk-composer__send"
                disabled={!draft.trim() || sending}
                aria-label="Enviar mensagem"
              >
                <Send size={19} />
                <span>{sending ? "A enviar…" : "Enviar"}</span>
              </button>
            </form>
          )}
        </div>
      </div>

      <SafetyDialog
        open={Boolean(safetyMode)}
        mode={safetyMode}
        personName={profile?.nome_publico}
        loading={safetyLoading}
        error={safetyError}
        onClose={() => !safetyLoading && setSafetyMode("")}
        onConfirm={handleSafetyConfirm}
      />
    </main>
  );
}
