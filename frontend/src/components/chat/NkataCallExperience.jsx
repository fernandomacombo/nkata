import { useEffect, useRef, useState } from "react";
import {
  Camera,
  LockKeyhole,
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Video,
  VideoOff,
  Volume2,
  VolumeX,
} from "lucide-react";
import {
  fetchCallState,
  sendCallSignal,
  startMatchCall,
  updateMatchCall,
} from "../../services/callApi.js";

const CALL_POLL_MS = 1000;
const TERMINAL_STATES = new Set(["RECUSADA", "TERMINADA", "PERDIDA", "FALHOU"]);

function formatDuration(totalSeconds) {
  const seconds = Math.max(0, Number(totalSeconds) || 0);
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function mediaErrorMessage(error, type) {
  if (!window.isSecureContext) {
    return "Para chamadas no telemóvel, abra o NKATA por HTTPS para permitir microfone e câmara.";
  }
  if (["NotAllowedError", "PermissionDeniedError"].includes(error?.name)) {
    return type === "VIDEO"
      ? "Permita o acesso ao microfone e à câmara para iniciar a videochamada."
      : "Permita o acesso ao microfone para iniciar a chamada.";
  }
  return "Não foi possível preparar o dispositivo para a chamada.";
}

export default function NkataCallExperience({
  match,
  profile,
  audioEnabled,
  videoEnabled,
  onNotice,
}) {
  const [call, setCall] = useState(null);
  const [iceServers, setIceServers] = useState([]);
  const [phase, setPhase] = useState("idle");
  const [error, setError] = useState("");
  const [localStream, setLocalStream] = useState(null);
  const [remoteStream, setRemoteStream] = useState(null);
  const [muted, setMuted] = useState(false);
  const [cameraOff, setCameraOff] = useState(false);
  const [speakerOff, setSpeakerOff] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const callRef = useRef(null);
  const peerRef = useRef(null);
  const localStreamRef = useRef(null);
  const remoteStreamRef = useRef(null);
  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const remoteAudioRef = useRef(null);
  const signalCursorRef = useRef(0);
  const signalBufferRef = useRef([]);
  const pendingIceRef = useRef([]);
  const pollingBusyRef = useRef(false);
  const connectedAtRef = useRef(0);

  const callType = call?.tipo || "AUDIO";
  const isVideoCall = callType === "VIDEO";
  const incoming = Boolean(call?.recebida && call?.estado === "CHAMANDO" && !peerRef.current);
  const overlayOpen = Boolean(call);

  const syncVideoElements = () => {
    if (localVideoRef.current && localStreamRef.current) {
      localVideoRef.current.srcObject = localStreamRef.current;
    }
    if (remoteVideoRef.current && remoteStreamRef.current) {
      remoteVideoRef.current.srcObject = remoteStreamRef.current;
      remoteVideoRef.current.muted = speakerOff;
    }
    if (remoteAudioRef.current && remoteStreamRef.current) {
      remoteAudioRef.current.srcObject = remoteStreamRef.current;
      remoteAudioRef.current.muted = speakerOff;
    }
  };

  useEffect(syncVideoElements, [localStream, remoteStream, speakerOff, callType]);

  const stopMedia = () => {
    localStreamRef.current?.getTracks?.().forEach((track) => track.stop());
    remoteStreamRef.current?.getTracks?.().forEach((track) => track.stop());
    localStreamRef.current = null;
    remoteStreamRef.current = null;
    setLocalStream(null);
    setRemoteStream(null);
  };

  const resetCall = ({ notice = "" } = {}) => {
    peerRef.current?.close?.();
    peerRef.current = null;
    stopMedia();
    callRef.current = null;
    signalCursorRef.current = 0;
    signalBufferRef.current = [];
    pendingIceRef.current = [];
    connectedAtRef.current = 0;
    setCall(null);
    setPhase("idle");
    setMuted(false);
    setCameraOff(false);
    setSpeakerOff(false);
    setElapsed(0);
    if (notice) onNotice?.(notice);
  };

  useEffect(() => () => resetCall(), []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (phase !== "active") return undefined;
    if (!connectedAtRef.current) connectedAtRef.current = Date.now();
    const update = () => {
      setElapsed(Math.floor((Date.now() - connectedAtRef.current) / 1000));
    };
    update();
    const id = window.setInterval(update, 1000);
    return () => window.clearInterval(id);
  }, [phase]);

  const prepareLocalMedia = async (type) => {
    if (!navigator.mediaDevices?.getUserMedia || typeof RTCPeerConnection === "undefined") {
      throw new Error("WEBRTC_UNAVAILABLE");
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
      },
      video: type === "VIDEO"
        ? {
            facingMode: "user",
            width: { ideal: 1280 },
            height: { ideal: 720 },
          }
        : false,
    });
    localStreamRef.current = stream;
    setLocalStream(stream);
    return stream;
  };

  const flushPendingIce = async (peer) => {
    if (!peer?.remoteDescription) return;
    const candidates = [...pendingIceRef.current];
    pendingIceRef.current = [];
    for (const candidate of candidates) {
      try {
        await peer.addIceCandidate(new RTCIceCandidate(candidate));
      } catch {
        // Um candidato ICE inválido não deve derrubar toda a chamada.
      }
    }
  };

  const createPeer = (activeCall, stream, servers) => {
    peerRef.current?.close?.();
    const peer = new RTCPeerConnection({ iceServers: servers || [] });
    peerRef.current = peer;

    stream.getTracks().forEach((track) => peer.addTrack(track, stream));

    const remote = new MediaStream();
    remoteStreamRef.current = remote;
    setRemoteStream(remote);

    peer.addEventListener("track", (event) => {
      const incomingStream = event.streams?.[0];
      if (incomingStream) {
        incomingStream.getTracks().forEach((track) => {
          if (!remote.getTracks().some((current) => current.id === track.id)) {
            remote.addTrack(track);
          }
        });
      } else if (event.track && !remote.getTracks().some((track) => track.id === event.track.id)) {
        remote.addTrack(event.track);
      }
      setRemoteStream(new MediaStream(remote.getTracks()));
    });

    peer.addEventListener("icecandidate", (event) => {
      if (!event.candidate || !activeCall?.id) return;
      const payload = event.candidate.toJSON
        ? event.candidate.toJSON()
        : {
            candidate: event.candidate.candidate,
            sdpMid: event.candidate.sdpMid,
            sdpMLineIndex: event.candidate.sdpMLineIndex,
            usernameFragment: event.candidate.usernameFragment,
          };
      sendCallSignal(match.id, activeCall.id, "ICE", payload).catch(() => {});
    });

    peer.addEventListener("connectionstatechange", () => {
      if (peer.connectionState === "connected") {
        setPhase("active");
        if (!connectedAtRef.current) connectedAtRef.current = Date.now();
        updateMatchCall(match.id, activeCall.id, "active").catch(() => {});
      } else if (peer.connectionState === "failed") {
        updateMatchCall(match.id, activeCall.id, "failed").catch(() => {});
        resetCall({ notice: "A chamada não conseguiu estabelecer ligação." });
      }
    });

    return peer;
  };

  const processSignals = async (signals, activeCall = callRef.current) => {
    if (!signals?.length || !activeCall) return;
    const peer = peerRef.current;
    if (!peer) {
      signalBufferRef.current = [...signalBufferRef.current, ...signals];
      return;
    }

    for (const signal of signals) {
      try {
        if (signal.tipo === "OFFER" && activeCall.recebida) {
          if (!peer.remoteDescription) {
            await peer.setRemoteDescription(new RTCSessionDescription(signal.payload));
            await flushPendingIce(peer);
            const answer = await peer.createAnswer();
            await peer.setLocalDescription(answer);
            await sendCallSignal(match.id, activeCall.id, "ANSWER", {
              type: answer.type,
              sdp: answer.sdp,
            });
            setPhase("connecting");
          }
        } else if (signal.tipo === "ANSWER" && activeCall.iniciada_por_mim) {
          if (!peer.remoteDescription) {
            await peer.setRemoteDescription(new RTCSessionDescription(signal.payload));
            await flushPendingIce(peer);
            setPhase("connecting");
          }
        } else if (signal.tipo === "ICE") {
          if (peer.remoteDescription) {
            await peer.addIceCandidate(new RTCIceCandidate(signal.payload));
          } else {
            pendingIceRef.current.push(signal.payload);
          }
        }
      } catch {
        setError("Houve um problema ao negociar a ligação da chamada.");
      }
    }
  };

  const pollCall = async () => {
    if (!match?.id || pollingBusyRef.current || document.visibilityState !== "visible") return;
    pollingBusyRef.current = true;
    try {
      const result = await fetchCallState(match.id, {
        sinceSignalId: signalCursorRef.current,
      });
      setIceServers(result.iceServers || []);

      const current = callRef.current;
      if (!result.call) {
        if (current) resetCall({ notice: "A chamada terminou." });
        return;
      }

      if (!current || current.id !== result.call.id) {
        callRef.current = result.call;
        signalCursorRef.current = 0;
        signalBufferRef.current = [];
        pendingIceRef.current = [];
        setCall(result.call);
        setPhase(result.call.recebida ? "incoming" : "calling");
      } else {
        callRef.current = { ...current, ...result.call };
        setCall(callRef.current);
        if (result.call.estado === "ATIVA") setPhase("active");
        if (result.call.estado === "CONECTANDO" && phase !== "active") setPhase("connecting");
      }

      if (result.signals.length) {
        signalCursorRef.current = Math.max(
          signalCursorRef.current,
          ...result.signals.map((signal) => Number(signal.id || 0)),
        );
        await processSignals(result.signals, callRef.current);
      }
    } catch (requestError) {
      if (requestError.status === 503) {
        setError("As chamadas ainda precisam de ser preparadas neste ambiente.");
      }
    } finally {
      pollingBusyRef.current = false;
    }
  };

  useEffect(() => {
    if (!match?.id) return undefined;
    let disposed = false;
    const run = () => {
      if (!disposed) pollCall();
    };
    run();
    const id = window.setInterval(run, CALL_POLL_MS);
    const visibility = () => {
      if (document.visibilityState === "visible") run();
    };
    document.addEventListener("visibilitychange", visibility);
    return () => {
      disposed = true;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, [match?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const startCall = async (type) => {
    setError("");
    const permitted = type === "VIDEO" ? videoEnabled : audioEnabled;
    if (!permitted) {
      onNotice?.("Chamadas estão disponíveis no NKATA Essencial e Premium.");
      return;
    }

    let stream;
    try {
      stream = await prepareLocalMedia(type);
      const result = await startMatchCall(match.id, type);
      const activeCall = result.call;
      callRef.current = activeCall;
      setCall(activeCall);
      setIceServers(result.ice_servers || []);
      setPhase("calling");
      signalCursorRef.current = 0;

      const peer = createPeer(activeCall, stream, result.ice_servers || []);
      const offer = await peer.createOffer();
      await peer.setLocalDescription(offer);
      await sendCallSignal(match.id, activeCall.id, "OFFER", {
        type: offer.type,
        sdp: offer.sdp,
      });
    } catch (requestError) {
      stream?.getTracks?.().forEach((track) => track.stop());
      stopMedia();
      setError(
        requestError?.message && requestError.name !== "NotAllowedError"
          ? requestError.message
          : mediaErrorMessage(requestError, type),
      );
      if (requestError?.message === "WEBRTC_UNAVAILABLE") {
        setError("Este navegador não suporta chamadas WebRTC.");
      }
    }
  };

  const acceptCall = async () => {
    const activeCall = callRef.current;
    if (!activeCall) return;
    setError("");

    try {
      const stream = await prepareLocalMedia(activeCall.tipo);
      await updateMatchCall(match.id, activeCall.id, "accept");
      setPhase("connecting");
      const state = await fetchCallState(match.id, { sinceSignalId: 0 });
      setIceServers(state.iceServers || []);
      const peer = createPeer(activeCall, stream, state.iceServers || []);
      void peer;
      const allSignals = [...signalBufferRef.current, ...(state.signals || [])];
      signalBufferRef.current = [];
      if (state.signals?.length) {
        signalCursorRef.current = Math.max(
          signalCursorRef.current,
          ...state.signals.map((signal) => Number(signal.id || 0)),
        );
      }
      await processSignals(allSignals, activeCall);
    } catch (requestError) {
      stopMedia();
      setError(mediaErrorMessage(requestError, activeCall.tipo));
    }
  };

  const declineCall = async () => {
    const activeCall = callRef.current;
    if (!activeCall) return;
    try {
      await updateMatchCall(match.id, activeCall.id, "decline");
    } catch {
      // A UI deve fechar mesmo que a resposta chegue depois do timeout.
    }
    resetCall({ notice: "Chamada recusada." });
  };

  const endCall = async () => {
    const activeCall = callRef.current;
    if (activeCall) {
      try {
        await updateMatchCall(match.id, activeCall.id, "end");
      } catch {
        // O media local deve ser sempre libertado.
      }
    }
    resetCall({ notice: "Chamada terminada." });
  };

  const toggleMic = () => {
    const nextMuted = !muted;
    localStreamRef.current?.getAudioTracks?.().forEach((track) => {
      track.enabled = !nextMuted;
    });
    setMuted(nextMuted);
  };

  const toggleCamera = () => {
    const nextOff = !cameraOff;
    localStreamRef.current?.getVideoTracks?.().forEach((track) => {
      track.enabled = !nextOff;
    });
    setCameraOff(nextOff);
  };

  const toggleSpeaker = () => {
    setSpeakerOff((current) => !current);
  };

  return (
    <>
      <div className="nk-call-launchers" aria-label="Chamadas">
        <button
          type="button"
          className={`nk-call-launcher ${audioEnabled ? "" : "is-locked"}`}
          onClick={() => startCall("AUDIO")}
          aria-label="Iniciar chamada de áudio"
          title={audioEnabled ? "Chamada de áudio" : "NKATA Essencial ou Premium"}
        >
          <Phone size={18} />
          {!audioEnabled && <LockKeyhole size={10} className="nk-call-launcher__lock" />}
        </button>
        <button
          type="button"
          className={`nk-call-launcher ${videoEnabled ? "" : "is-locked"}`}
          onClick={() => startCall("VIDEO")}
          aria-label="Iniciar videochamada"
          title={videoEnabled ? "Videochamada" : "NKATA Essencial ou Premium"}
        >
          <Video size={19} />
          {!videoEnabled && <LockKeyhole size={10} className="nk-call-launcher__lock" />}
        </button>
      </div>

      {overlayOpen && (
        <div className={`nk-call-screen ${isVideoCall ? "is-video" : "is-audio"}`} role="dialog" aria-modal="true">
          {isVideoCall && (
            <video
              ref={remoteVideoRef}
              className="nk-call-screen__remote-video"
              autoPlay
              playsInline
              muted={speakerOff}
            />
          )}
          {!isVideoCall && (
            <audio ref={remoteAudioRef} autoPlay muted={speakerOff} />
          )}

          <div className="nk-call-screen__backdrop" />

          <div className="nk-call-screen__top">
            <span>{isVideoCall ? "Videochamada NKATA" : "Chamada NKATA"}</span>
            {phase === "active" && <strong>{formatDuration(elapsed)}</strong>}
          </div>

          <div className="nk-call-screen__identity">
            {!isVideoCall && (
              <div className="nk-call-screen__portrait">
                {profile?.foto_url ? (
                  <img src={profile.foto_url} alt={`Foto de ${profile.nome_publico}`} />
                ) : (
                  <div className="nk-call-screen__portrait-fallback">
                    <Camera size={34} />
                  </div>
                )}
              </div>
            )}
            <h2>{profile?.nome_publico || "Membro NKATA"}</h2>
            <p>
              {incoming
                ? (isVideoCall ? "Videochamada recebida" : "Chamada de áudio recebida")
                : phase === "calling"
                  ? "A chamar…"
                  : phase === "connecting"
                    ? "A conectar…"
                    : phase === "active"
                      ? "Ligação segura entre os dispositivos"
                      : "A preparar chamada…"}
            </p>
            {error && <div className="nk-call-screen__error" role="status">{error}</div>}
          </div>

          {isVideoCall && localStream && (
            <video
              ref={localVideoRef}
              className={`nk-call-screen__local-video ${cameraOff ? "is-off" : ""}`}
              autoPlay
              playsInline
              muted
            />
          )}

          <div className="nk-call-screen__controls">
            {incoming ? (
              <>
                <button type="button" className="nk-call-control is-decline" onClick={declineCall}>
                  <PhoneOff size={22} />
                  <span>Recusar</span>
                </button>
                <button type="button" className="nk-call-control is-accept" onClick={acceptCall}>
                  {isVideoCall ? <Video size={23} /> : <Phone size={22} />}
                  <span>Atender</span>
                </button>
              </>
            ) : (
              <>
                <button type="button" className={`nk-call-control ${muted ? "is-active" : ""}`} onClick={toggleMic}>
                  {muted ? <MicOff size={21} /> : <Mic size={21} />}
                  <span>{muted ? "Ativar" : "Microfone"}</span>
                </button>
                {isVideoCall && (
                  <button type="button" className={`nk-call-control ${cameraOff ? "is-active" : ""}`} onClick={toggleCamera}>
                    {cameraOff ? <VideoOff size={21} /> : <Video size={21} />}
                    <span>{cameraOff ? "Câmara" : "Vídeo"}</span>
                  </button>
                )}
                <button type="button" className={`nk-call-control ${speakerOff ? "is-active" : ""}`} onClick={toggleSpeaker}>
                  {speakerOff ? <VolumeX size={21} /> : <Volume2 size={21} />}
                  <span>{speakerOff ? "Sem som" : "Som"}</span>
                </button>
                <button type="button" className="nk-call-control is-end" onClick={endCall}>
                  <PhoneOff size={22} />
                  <span>Terminar</span>
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
