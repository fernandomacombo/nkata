import HeartLoader from "../components/HeartLoader.jsx";
import Presence from "../components/profiles/Presence.jsx";
import { deleteMatchMessage } from "../services/api.js";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownLeft,
  ArrowLeft,
  ArrowUpRight,
  Ban,
  Flag,
  Link2Off,
  LockKeyhole,
  MapPin,
  MessageCircle,
  Mic,
  MoreHorizontal,
  Pause,
  PenLine,
  Phone,
  Play,
  Send,
  ShieldCheck,
  Square,
  Trash2,
  UserRound,
  Video,
} from "lucide-react";
import SafetyDialog from "../components/safety/SafetyDialog.jsx";
import {
  blockProfile,
  closeMatch,
  fetchMatchLive,
  reportProfile,
  sendMatchAudio,
  updateMatchTyping,
} from "../services/api.js";
import { fetchMyPlan } from "../services/planApi.js";
import useInterfaceLanguage from "../hooks/useInterfaceLanguage.js";

const LIVE_POLL_INTERVAL_MS = 2500;
const TYPING_HEARTBEAT_MS = 2000;

function formatMessageTime(value, english) {
  if (!value) return "";

  return new Intl.DateTimeFormat(english ? "en-GB" : "pt-MZ", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatDuration(value) {
  const seconds = Math.max(0, Math.round(Number(value) || 0));
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

function messageIdentity(message) {
  if (message?.type === "call") {
    return `call:${message.callId || String(message.id || "").replace("call-", "")}`;
  }
  if (message?.type === "audio") {
    return `audio:${message.audioId || String(message.id || "").replace("audio-", "")}`;
  }
  return `text:${message?.id}`;
}

function ProfileAvatar({ profile, english }) {
  const [failed, setFailed] = useState(false);
  const src = profile?.foto_url || "";

  useEffect(() => {
    setFailed(false);
  }, [src]);

  if (!src || failed) return <UserRound size={28} />;

  return (
    <img
      src={src}
      alt={`${english ? "Photo of" : "Foto de"} ${profile?.nome_publico || (english ? "NKATA member" : "membro NKATA")}`}
      onError={() => setFailed(true)}
    />
  );
}

function VoiceNote({ message, english }) {
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
        preload="none"
        controlsList="nodownload noremoteplayback"
        disableRemotePlayback
        onContextMenu={event=>event.preventDefault()}
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
        <span className="sr-only">{playing ? (english ? "Pause voice note" : "Pausar nota de voz") : (english ? "Play voice note" : "Reproduzir nota de voz")}</span>
      </button>

      <div className="nk-voice-note__track" aria-hidden="true">
        <span style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
      </div>

      <strong>{formatDuration(duration)}</strong>
    </div>
  );
}

const callStatusLabel = (status, english) => english ? ({
  "Chamada não atendida": "Unanswered call",
  "Chamada perdida": "Missed call",
  "Chamada recusada": "Declined call",
  "Chamada cancelada": "Cancelled call",
  "Chamada terminada": "Call ended",
  "Videochamada": "Video call",
  "Chamada de áudio": "Audio call",
})[status] || status : status;

function CallEvent({ message, english }) {
  const outgoing = message.callDirection === "OUTGOING" || message.mine;
  const isVideo = message.callType === "VIDEO";
  const duration = Math.max(0, Number(message.durationSeconds || 0));
  const status = callStatusLabel(message.callLabel || (isVideo ? "Videochamada" : "Chamada de áudio"), english);

  return (
    <div className={`nk-call-history ${message.callMissed ? "is-missed" : ""}`}>
      <div className="nk-call-history__icon" aria-hidden="true">
        {isVideo ? <Video size={19} /> : <Phone size={18} />}
      </div>
      <div className="nk-call-history__content">
        <strong>{isVideo ? (english ? "Video call" : "Videochamada") : (english ? "Audio call" : "Chamada de áudio")}</strong>
        <span className="nk-call-history__status">
          {outgoing ? <ArrowUpRight size={14} /> : <ArrowDownLeft size={14} />}
          {status}
        </span>
      </div>
      <div className="nk-call-history__meta">
        {duration > 0 && <strong>{english ? "Duration" : "Duração"} {formatDuration(duration)}</strong>}
        <small>{formatMessageTime(message.createdAt, english)}</small>
      </div>
    </div>
  );
}

function MessageBubble({ message, english, onDelete, onReply, original }) {
  if (message.type === "call") return <CallEvent message={message} english={english} />;

  return (
    <div className={`nk-message-row ${message.mine ? "is-mine" : ""}`}>
      <div className={`nk-message-bubble ${message.deleted ? "is-deleted" : ""} ${message.type === "audio" ? "is-audio" : ""}`}>
        {!message.deleted && message.replyId && <blockquote className="nk-chat-quote">
          <strong>{original?.senderName}</strong>
          {original && !original.deleted ? original.text : (english ? "Original unavailable" : "Mensagem original indisponível")}
        </blockquote>}
        {message.type === "audio" ? (
          <VoiceNote message={message} english={english} />
        ) : (
          <p>{message.deleted ? (english ? "Message deleted" : "Mensagem apagada") : message.text}</p>
        )}
        <span>
          {formatMessageTime(message.createdAt, english)}
          {!message.deleted && message.type === "text" && (onReply || message.mine) && <details className="nk-bubble-menu">
            <summary aria-label={english ? "Message options" : "Opções da mensagem"}><MoreHorizontal size={17}/></summary>
            <div onClick={(event) => { event.currentTarget.parentElement.open = false; }}>
              {onReply && <button type="button" onClick={() => onReply(message)}>{english ? "Reply" : "Responder"}</button>}
              {message.mine && <button type="button" onClick={() => onDelete(message)}>{english ? "Delete" : "Apagar"}</button>}
            </div>
          </details>}
          {message.mine && !message.deleted && <small>{message.read ? (english ? "Read" : "Lida") : (english ? "Sent" : "Enviada")}</small>}
        </span>
      </div>
    </div>
  );
}

export function ChatSafetyNotice({ english, onAccept, name, helpOnly, onExit }) {
  const dialog = useRef(null);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const element = dialog.current;
    if (element && !element.open) element.showModal();
    return () => { if (element?.open) element.close(); };
  }, []);

  async function confirm() {
    setSaving(true);
    setFailed(false);
    try {
      await onAccept();
    } catch {
      setFailed(true);
      setSaving(false);
    }
  }

  return (
    <dialog ref={dialog} className="nk-chat-welcome" aria-labelledby="chat-warning-title"
      aria-describedby="chat-warning-text" onCancel={(event) => { event.preventDefault(); onExit?.(); }}>
      <ShieldCheck size={34} aria-hidden="true" />
      {name && <p className="nk-chat-recipient">{english ? "Your conversation with" : "A sua conversa com"} <strong>{name}</strong></p>}
      <h2 id="chat-warning-title">{english ? "Before you say hello" : "Antes do primeiro olá"}</h2>
      <p id="chat-warning-text">{english
        ? "Watch out for scams. Keep your money, banking details and verification codes to yourself. If someone pressures you, use the conversation menu to report them."
        : "Tenha cuidado com golpes. Guarde para si o seu dinheiro, os dados bancários e os códigos de confirmação. Se alguém insistir, pode denunciar a pessoa no menu da conversa."}</p>
      <details open={helpOnly || undefined} className="nk-chat-guide">
        <summary>{english ? "Learn more · Scams and threats" : "Ver mais · Golpes e ameaças"}</summary>
        <p>{english ? "If someone threatens you, you can ask for help. It is not your fault." : "Se alguém o ameaçar, pode pedir ajuda. A culpa não é sua."}</p>
        <ol>{(english ? [
          "Stop responding. Keep your money, codes and private photos to yourself.",
          "If safe, keep the profile name, dates and threatening messages as evidence.",
          "Open the conversation menu (⋯) to report the profile. You can also block the person.",
          "Tell someone you trust. If you are in immediate danger, seek safety and contact local police."
        ] : [
          "Interrompa o contacto. Guarde consigo o dinheiro, os códigos e as fotografias íntimas.",
          "Se for seguro, guarde o nome do perfil, as datas e as mensagens de ameaça.",
          "Abra o menu da conversa (⋯) e escolha Denunciar perfil. Também pode bloquear a pessoa.",
          "Fale com alguém de confiança. Se estiver em perigo imediato, procure um lugar seguro e contacte a polícia local."
        ]).map(step => <li key={step}>{step}</li>)}</ol>
      </details>
      {failed && <p role="alert">{english ? "Could not save. Please try again." : "Não foi possível guardar. Tente novamente."}</p>}
      <div className="nk-chat-safety-actions">
        <button autoFocus type="button" className="nk-button nk-button--wine" disabled={saving} onClick={confirm}>{saving ? "…" : "OK"}</button>
        {onExit && <button type="button" className="nk-button" onClick={onExit}>{english ? "Leave conversation" : "Sair da conversa"}</button>}
      </div>
    </dialog>
  );
}

export default function ConversationPage({
  safetyAccepted,
  onAcceptSafety,
  match,
  messages,
  loading,
  sending,
  error,
  onBack,
  onSend,
}) {
  const english = useInterfaceLanguage() === "EN";
  const [draft, setDraft] = useState("");
  const [emojiPickerOpen, setEmojiPickerOpen] = useState(false);
  const chatEmojis = [String.fromCodePoint(0x1F60A), String.fromCodePoint(0x2764, 0xFE0F), String.fromCodePoint(0x1F970), String.fromCodePoint(0x1F60D), String.fromCodePoint(0x1F602), String.fromCodePoint(0x1F618), String.fromCodePoint(0x1F495), String.fromCodePoint(0x1F44B), String.fromCodePoint(0x1F44D), String.fromCodePoint(0x1F64F), String.fromCodePoint(0x1F339), String.fromCodePoint(0x2728), String.fromCodePoint(0x1F389), String.fromCodePoint(0x1F917), String.fromCodePoint(0x1F60E), String.fromCodePoint(0x1F4AC)];
  const [menuOpen, setMenuOpen] = useState(false);
  const [safetyMode, setSafetyMode] = useState("");
  const [safetyLoading, setSafetyLoading] = useState(false);
  const [safetyError, setSafetyError] = useState("");
  const [safetyStatus, setSafetyStatus] = useState("");
  const [textEnabled, setTextEnabled] = useState(false);
  const [presetsEnabled, setPresetsEnabled] = useState(false);
  const [presetData, setPresetData] = useState({restantes:0,frases:[],phrases_en:[]});
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [voiceOffer,setVoiceOffer] = useState(null);
  const voiceKey = useRef(null);
  const canRecordVoice = audioEnabled || Boolean(voiceOffer?.enabled && voiceOffer.balance >= voiceOffer.cost);
  const [audioPlanLabel, setAudioPlanLabel] = useState("NKATA Livre");
  const [audioNotice, setAudioNotice] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recordedDuration, setRecordedDuration] = useState(0);
  const [previewUrl, setPreviewUrl] = useState("");
  const [sendingAudio, setSendingAudio] = useState(false);
  const [localAudioMessages, setLocalAudioMessages] = useState([]);
  const [liveMessages, setLiveMessages] = useState([]);
  const [deleteError, setDeleteError] = useState("");
  const [readReceiptKeys, setReadReceiptKeys] = useState(() => new Set());
  const [remoteTyping, setRemoteTyping] = useState(false);
  const [previewPlaying, setPreviewPlaying] = useState(false);
  const endRef = useRef(null);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const recordingStartedRef = useRef(0);
  const cancelRecordingRef = useRef(false);
  const previewAudioRef = useRef(null);
  const composerTextareaRef = useRef(null);
  const liveCursorRef = useRef("");
  const liveBusyRef = useRef(false);
  const [reply, setReply] = useState(null);
  const [showHelp, setShowHelp] = useState(false);
  const [remoteRecording, setRemoteRecording] = useState(false);
  const profile = match?.otherProfile;
  const isComposingText = Boolean(draft.trim()) && !recording && !recordedBlob;

  const timeline = useMemo(() => {
    const merged = new Map();
    [...messages, ...localAudioMessages, ...liveMessages].forEach((message) => {
      if (!message) return;
      const key = messageIdentity(message);
      const previous = merged.get(key) || {};
      merged.set(key, {
        ...previous,
        ...message,
        deleted: Boolean(previous.deleted || message.deleted),
        read: Boolean(previous.read || message.read || readReceiptKeys.has(key)),
      });
    });

    return [...merged.values()].sort((a, b) => (
      new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
    ));
  }, [liveMessages, localAudioMessages, messages, readReceiptKeys]);

  const textById = useMemo(() => new Map(timeline.filter(item => item.type === "text").map(item => [item.id, item])), [timeline]);

  async function removeMessage(message) {
    if (!window.confirm(english ? "Delete this message for everyone?" : "Apagar esta mensagem para todos?")) return;
    setDeleteError("");
    try {
      const deleted = await deleteMatchMessage(match.id, message.id);
      setLiveMessages((current) => [...current.filter((item) => messageIdentity(item) !== messageIdentity(deleted)), deleted]);
    } catch (error) {
      setDeleteError(error.message);
    }
  }

  const canUsePreset = presetsEnabled && presetData.restantes > 0;
  const presetChoices = english ? presetData.phrases_en : presetData.frases;

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
    voiceKey.current = null;
    setRecordedDuration(0);
    setPreviewPlaying(false);
  };

  useEffect(() => {
    setDraft("");
    setDeleteError("");
    setMenuOpen(false);
    setSafetyMode("");
    setSafetyError("");
    setSafetyStatus("");
    setAudioNotice("");
    setLocalAudioMessages([]);
    setLiveMessages([]);
    setReadReceiptKeys(new Set());
    setRemoteTyping(false);
    liveCursorRef.current = "";
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
        setVoiceOffer(payload?.voice_credit || null);
        setTextEnabled(Boolean(currentPlan?.features?.chat_text));
        setPresetsEnabled(Boolean(currentPlan?.features?.chat_presets));
        setPresetData(payload?.chat_presets || {restantes:0,frases:[],phrases_en:[]});
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
  }, [timeline.length, loading, remoteTyping]);

  useEffect(() => {
    const textarea = composerTextareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 116)}px`;
  }, [draft]);

  useEffect(() => {
    if (!match?.id || loading) return undefined;

    if (!liveCursorRef.current && messages.length) {
      const latest = messages.reduce((current, message) => {
        if (!message?.createdAt) return current;
        if (!current) return message.createdAt;
        return new Date(message.createdAt) > new Date(current) ? message.createdAt : current;
      }, "");
      liveCursorRef.current = latest;
    }

    let disposed = false;

    const poll = async () => {
      if (disposed || liveBusyRef.current || document.visibilityState !== "visible") return;
      liveBusyRef.current = true;
      try {
        const result = await fetchMatchLive(match.id, { since: liveCursorRef.current });
        if (disposed) return;

        if (result.serverTime) liveCursorRef.current = result.serverTime;
        setRemoteTyping(Boolean(result.typing));
        setRemoteRecording(Boolean(result.recording));

        if (result.messages.length) {
          setLiveMessages((current) => {
            const merged = new Map(current.map((item) => [messageIdentity(item), item]));
            result.messages.forEach((item) => {
              const key = messageIdentity(item);
              merged.set(key, { ...(merged.get(key) || {}), ...item });
            });
            return [...merged.values()];
          });
        }

        if (result.readTextIds.length || result.readAudioIds.length) {
          setReadReceiptKeys((current) => {
            const next = new Set(current);
            result.readTextIds.forEach((id) => next.add(`text:${id}`));
            result.readAudioIds.forEach((id) => next.add(`audio:${id}`));
            return next;
          });
        }
      } catch {
        // A conversa continua funcional mesmo se a atualização incremental falhar.
      } finally {
        liveBusyRef.current = false;
      }
    };

    poll();
    const intervalId = window.setInterval(poll, LIVE_POLL_INTERVAL_MS);
    const handleVisibility = () => {
      if (document.visibilityState === "visible") poll();
    };
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      disposed = true;
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [loading, match?.id, messages]);

  useEffect(() => {
    if (!match?.id) return undefined;

    updateMatchTyping(match.id, isComposingText, recording).catch(() => {});
    if (!isComposingText && !recording) return undefined;

    const heartbeatId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        updateMatchTyping(match.id, isComposingText, recording).catch(() => {});
      }
    }, TYPING_HEARTBEAT_MS);

    return () => window.clearInterval(heartbeatId);
  }, [isComposingText, recording, match?.id]);

  useEffect(() => () => {
    if (match?.id) updateMatchTyping(match.id, false).catch(() => {});
  }, [match?.id]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const text = draft.trim();

    if (!text || sending || recording || recordedBlob || (!textEnabled && (!canUsePreset || !presetChoices.includes(text)))) return;

    const sent = await onSend(text, reply?.id);
    if (sent) {
      if (!textEnabled) setPresetData(current => ({...current, restantes:Math.max(0,current.restantes-1)}));
      setReply(null);
      setDraft("");
      updateMatchTyping(match.id, false).catch(() => {});
    }
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

    if (!canRecordVoice) {
      setAudioNotice(english ? "Voice notes require an active plan or sufficient credits." : "Notas de voz exigem um plano activo ou saldo suficiente de créditos.");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setAudioNotice(english ? "This device or browser cannot record voice notes." : "Este dispositivo ou navegador não permite gravar notas de voz.");
      return;
    }

    clearRecordedAudio();
    updateMatchTyping(match.id, false).catch(() => {});

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
        voiceKey.current = crypto.randomUUID();
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
      setAudioNotice(english ? "Unable to access the microphone. Check your browser permission." : "Não foi possível aceder ao microfone. Confirme a permissão do navegador.");
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

    const cost = audioEnabled ? 0 : voiceOffer?.cost;
    if (!canRecordVoice) return;
    setSendingAudio(true);
    setAudioNotice("");
    try {
      const message = await sendMatchAudio(match.id, recordedBlob, recordedDuration, {key:voiceKey.current, expectedCost:cost});
      setLocalAudioMessages((current) => [...current, message]);
      clearRecordedAudio();
      fetchMyPlan().then(payload => { setVoiceOffer(payload?.voice_credit || null); setAudioEnabled(Boolean(payload?.current_plan?.features?.chat_audio)); }).catch(() => {});
    } catch (requestError) {
      setAudioNotice(requestError.message || (english ? "Unable to send the voice note." : "Não foi possível enviar a nota de voz."));
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
      setSafetyStatus(result?.message || (english ? "Action completed." : "A ação foi concluída."));

      if (["block", "close"].includes(currentMode)) {
        window.setTimeout(() => window.location.assign("/matches/"), 1000);
      } else {
        window.setTimeout(() => setSafetyStatus(""), 3200);
      }
    } catch (requestError) {
      setSafetyError(requestError.message || (english ? "Unable to complete this action." : "Não foi possível concluir esta ação."));
    } finally {
      setSafetyLoading(false);
    }
  };

  if (!match) {
    return (
      <main className="nk-conversation nk-conversation--empty">
        <div className="nk-shell nk-conversation__empty-card">
          <MessageCircle size={30} />
          <h1>{english ? "Conversation unavailable" : "Conversa não disponível"}</h1>
          <p>{english ? "Go back to Matches and choose a conversation." : "Volte aos matches e escolha uma conversa."}</p>
          <button type="button" className="nk-button nk-button--wine" onClick={onBack}>
            {english ? "Back to matches" : "Voltar aos matches"}
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="nk-conversation">
      {(!safetyAccepted || showHelp) && <ChatSafetyNotice english={english} name={profile?.nome_publico} helpOnly={showHelp} onAccept={showHelp ? () => setShowHelp(false) : onAcceptSafety} />}
      <div className="nk-shell nk-conversation__shell">
        <header className="nk-conversation__header">
          <button type="button" className="nk-conversation__back" onClick={onBack}>
            <ArrowLeft size={19} />
            <span>{english ? "Chats" : "Chats"}</span>
          </button>

          <div className="nk-conversation__person">
            <span className="nk-conversation__avatar">
              <ProfileAvatar profile={profile} english={english} />
            </span>
            <div>
              <strong>{profile?.nome_publico || (english ? "NKATA member" : "Membro NKATA")}</strong>
              <small className={remoteTyping ? "is-typing" : ""}>
                {remoteRecording ? <><Mic size={12}/> {english ? "Recording audio…" : "A gravar áudio…"}</> : remoteTyping ? (
                  <><PenLine size={12} /> {english ? "Typing…" : "A escrever…"}</>
                ) : (
                  <Presence profile={profile} english={english} />
                )}
              </small>
            </div>
          </div>

          <div className="nk-conversation__options">
            <span className="nk-conversation__secure">
              <ShieldCheck size={16} />
              {english ? "Private" : "Privada"}
            </span>
            <button
              type="button"
              className="nk-conversation__options-trigger"
              onClick={() => setMenuOpen((current) => !current)}
              aria-label={english ? "Conversation options" : "Opções da conversa"}
              aria-expanded={menuOpen}
            >
              <MoreHorizontal size={20} />
            </button>

            {menuOpen && (
              <div className="nk-conversation__safety-menu">
                <button type="button" onClick={() => { setMenuOpen(false); setShowHelp(true); }}><ShieldCheck size={16}/> {english ? "Scams and threats" : "Golpes e ameaças"}</button>
                <button type="button" onClick={() => openSafetyAction("report")}>
                  <Flag size={16} /> {english ? "Report profile" : "Denunciar perfil"}
                </button>
                <button type="button" onClick={() => openSafetyAction("close")}>
                  <Link2Off size={16} /> {english ? "End connection" : "Encerrar ligação"}
                </button>
                <button
                  type="button"
                  className="is-danger"
                  onClick={() => openSafetyAction("block")}
                >
                  <Ban size={16} /> {english ? "Block person" : "Bloquear pessoa"}
                </button>
              </div>
            )}
          </div>
        </header>

        <section className="nk-conversation__body" aria-live="polite">
          {!timeline.length && <div className="nk-conversation__opening">
            <span><LockKeyhole size={17} /></span>
            <div>
              <strong>{english ? "It's a match" : "É um match"}</strong>
              <p>{english ? "Talk with respect. Personal contact details do not need to be shared straight away." : "Conversem com respeito. Os contactos pessoais não precisam de ser partilhados logo no início."}</p>
            </div>
          </div>}

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
            <HeartLoader page="conversation" compact/>
          ) : timeline.length ? (
            <div className="nk-message-list">
              {timeline.map((message) => (
                <MessageBubble key={messageIdentity(message)} message={message} english={english} original={textById.get(message.replyId)} onDelete={removeMessage} onReply={textEnabled ? (item) => { setReply(item); composerTextareaRef.current?.focus(); } : null} />
              ))}
              {remoteTyping && (
                <div className="nk-typing-row" aria-label={`${profile?.nome_publico || (english ? "The other person" : "A outra pessoa")} ${english ? "is typing" : "está a escrever"}`}>
                  <div className="nk-typing-indicator">
                    <PenLine size={14} />
                    <span aria-hidden="true" />
                    <span aria-hidden="true" />
                    <span aria-hidden="true" />
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>
          ) : (
            <div className="nk-conversation__first-message">
              <MessageCircle size={28} />
              <h2>{english ? "Start the conversation" : "Comece a conversa"}</h2>
              <p>{english ? "A simple, respectful message is enough." : "Uma mensagem simples e respeitosa é suficiente."}</p>
              <button
                type="button"
                onClick={() => setDraft(english ? "Hello, I enjoyed reading your profile. How are you?" : "Olá, gostei de conhecer o seu perfil. Como está?")}
              >
                {english ? "Use a suggestion" : "Usar uma sugestão"}
              </button>
              {textEnabled && (
                <button
                  type="button"
                  disabled={Boolean(draft.trim()) || sending}
                  onClick={() => {
                    setDraft(english ? "What would your ideal date be like?" : "Como seria o seu encontro ideal?");
                    composerTextareaRef.current?.focus();
                  }}
                >
                  {english ? "Use an icebreaker" : "Usar um quebra-gelo"}
                </button>
              )}
            </div>
          )}
        </section>

        <div className="nk-chat-dock">
          {reply && <div className="nk-chat-reply"><div><strong>{english ? "Replying to" : "A responder a"} {reply.senderName}</strong><p>{textById.get(reply.id)?.deleted ? (english ? "Message deleted" : "Mensagem apagada") : reply.text}</p></div>
            <button type="button" onClick={() => setReply(null)}>{english ? "Cancel" : "Cancelar"}</button></div>}
          {deleteError && <p className="nk-chat-dock__notice" role="alert">{deleteError}</p>}
          {audioNotice && (
            <div className="nk-chat-dock__notice" role="status">
              <LockKeyhole size={14} />
              <span>{audioNotice}</span>
              {!audioEnabled && <small>{audioPlanLabel}</small>}
            </div>
          )}

          {!textEnabled && canUsePreset && <div className="nk-chat-dock__notice" role="status">{presetData.restantes} {english ? "free messages left" : "mensagens gratuitas restantes"}</div>}
          {!textEnabled && !canUsePreset && !recording && !recordedBlob ? (
            <div className="nk-chat-dock__notice" role="status">
              <LockKeyhole size={14} />
              <span>{english ? "Text chat access required." : "Texto livre bloqueado."}</span>
              <a href="/conta/?section=plan">{english ? "Wallet" : "Carteira"}</a>
              {canRecordVoice && <button type="button" onClick={startRecording}><Mic size={18}/> {english ? "Voice note" : "Nota de voz"}</button>}
            </div>
          ) : recording ? (
            <div className="nk-recorder-bar">
              <button type="button" className="nk-recorder-bar__cancel" onClick={cancelRecording} aria-label={english ? "Cancel recording" : "Cancelar gravação"}>
                <Trash2 size={19} />
              </button>
              <div className="nk-recorder-bar__status">
                <span className="nk-recorder-bar__dot" />
                <strong>{formatDuration(recordingSeconds)}</strong>
                <small>{english ? "Recording" : "A gravar"}</small>
              </div>
              <button type="button" className="nk-recorder-bar__stop" onClick={stopRecording} aria-label={english ? "Stop recording" : "Terminar gravação"}>
                <Square size={17} fill="currentColor" />
              </button>
            </div>
          ) : recordedBlob ? (
            <div className="nk-recorder-preview">
              <audio
                ref={previewAudioRef}
                src={previewUrl}
                controlsList="nodownload noremoteplayback"
                disableRemotePlayback
                onContextMenu={event=>event.preventDefault()}
                onPlay={() => setPreviewPlaying(true)}
                onPause={() => setPreviewPlaying(false)}
                onEnded={() => setPreviewPlaying(false)}
              />
              <button type="button" className="nk-recorder-preview__delete" onClick={clearRecordedAudio} aria-label={english ? "Delete recording" : "Apagar gravação"}>
                <Trash2 size={19} />
              </button>
              <button type="button" className="nk-recorder-preview__play" onClick={togglePreview} aria-label={previewPlaying ? (english ? "Pause recording" : "Pausar gravação") : (english ? "Play recording" : "Ouvir gravação")}>
                {previewPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
              </button>
              <div className="nk-recorder-preview__meta">
                <strong>{english ? "Voice note" : "Nota de voz"}</strong>
                <small>{formatDuration(recordedDuration)}{!audioEnabled && voiceOffer?.enabled ? ` · ${voiceOffer.cost} créditos` : ""}</small>
              </div>
              <button
                type="button"
                className="nk-recorder-preview__send"
                onClick={sendRecordedAudio}
                disabled={sendingAudio}
                aria-label={english ? "Send voice note" : "Enviar nota de voz"}
              >
                <Send size={18} />
              </button>
            </div>
          ) : (
            <form className="nk-composer" onSubmit={handleSubmit}>
              <button
                type="button"
                className={`nk-composer__mic ${canRecordVoice ? "" : "is-locked"}`}
                onClick={startRecording}
                aria-label={canRecordVoice ? (english ? "Record voice note" : "Gravar nota de voz") : (english ? "Voice notes require a paid plan" : "Notas de voz exigem plano pago")}
                title={canRecordVoice ? (english ? "Record voice note" : "Gravar nota de voz") : "NKATA Fortnightly, Essential or Premium"}
              >
                <Mic size={20} />
                {!canRecordVoice && <LockKeyhole className="nk-composer__mic-lock" size={10} />}
              </button>

              <label>
                <span className="sr-only">{english ? "Message" : "Mensagem"}</span>
                {!textEnabled ? <select value={draft} onChange={(event) => setDraft(event.target.value)} aria-label={english ? "Preset message" : "Mensagem predefinida"} disabled={sending}>
                  <option value="">{english ? "Choose a message" : "Escolha uma mensagem"}</option>
                  {presetChoices.map((phrase) => <option key={phrase} value={phrase}>{phrase}</option>)}
                </select> : <textarea
                  ref={composerTextareaRef}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value.slice(0, 1200))}
                  placeholder={english ? "Message…" : "Mensagem…"}
                  rows={1}
                  disabled={sending}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      handleSubmit(event);
                    }
                  }}
                />}
              </label>

              {textEnabled && (
                <div className="nk-emoji-control">
                  <button type="button" className="nk-emoji-trigger" aria-label={english ? "Choose emoji" : "Escolher emoji"} aria-expanded={emojiPickerOpen} onClick={() => setEmojiPickerOpen((open) => !open)}><span aria-hidden="true">{String.fromCodePoint(0x1F60A)}</span></button>
                  {emojiPickerOpen && <div className="nk-emoji-picker" role="group" aria-label={english ? "Emoji" : "Emojis"}>
                    {chatEmojis.map((emoji) => (
                      <button key={emoji} type="button" aria-label={emoji} onClick={() => {
                        setDraft((current) => (current + emoji).slice(0, 1200));
                        setEmojiPickerOpen(false);
                        composerTextareaRef.current?.focus();
                      }}>{emoji}</button>
                    ))}
                  </div>}
                </div>
              )}
              {textEnabled && <span className="nk-composer__count">{draft.length}/1200</span>}

              <button
                type="submit"
                className="nk-composer__send"
                disabled={!draft.trim() || sending}
                aria-label={english ? "Send message" : "Enviar mensagem"}
              >
                <Send size={19} />
                <span>{sending ? (english ? "Sending…" : "A enviar…") : (english ? "Send" : "Enviar")}</span>
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
