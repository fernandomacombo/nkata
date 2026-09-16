import { useEffect, useState } from "react";
import { MapPin, Phone, PhoneOff, Video } from "lucide-react";
import { fetchIncomingCall, updateMatchCall } from "../../services/callApi.js";
import {
  installCallAttentionUnlock,
  startIncomingCallAttention,
  stopIncomingCallAttention,
} from "../../services/callAttention.js";
import useInterfaceLanguage from "../../hooks/useInterfaceLanguage.js";

const INCOMING_POLL_MS = 2000;

function isCurrentConversation(matchId) {
  const normalized = window.location.pathname.endsWith("/")
    ? window.location.pathname
    : `${window.location.pathname}/`;
  return normalized === `/matches/${matchId}/conversa/`;
}

function hasAuthenticatedMemberShell() {
  return Boolean(document.querySelector(".nk-header__member"));
}

export default function IncomingCallWatcher() {
  const english = useInterfaceLanguage() === "EN";
  const [call, setCall] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => installCallAttentionUnlock(), []);

  useEffect(() => {
    if (call) {
      startIncomingCallAttention();
    } else {
      stopIncomingCallAttention();
    }
    return () => stopIncomingCallAttention();
  }, [call?.id]);

  useEffect(() => {
    let disposed = false;

    const poll = async () => {
      if (disposed || document.visibilityState !== "visible") return;
      if (!hasAuthenticatedMemberShell()) {
        setCall(null);
        return;
      }

      try {
        const result = await fetchIncomingCall();
        if (disposed) return;
        const incoming = result.call || null;
        setCall(incoming && !isCurrentConversation(incoming.match_id) ? incoming : null);
      } catch {
        if (!disposed) setCall(null);
      }
    };

    poll();
    const id = window.setInterval(poll, INCOMING_POLL_MS);
    const visibility = () => {
      if (document.visibilityState === "visible") poll();
    };
    document.addEventListener("visibilitychange", visibility);

    return () => {
      disposed = true;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);

  if (!call) return null;

  const caller = call.caller || {};
  const isVideo = call.tipo === "VIDEO";

  const decline = async () => {
    if (busy) return;
    stopIncomingCallAttention();
    setBusy(true);
    try {
      await updateMatchCall(call.match_id, call.id, "decline");
    } catch {
      // O aviso fecha mesmo se a chamada tiver expirado no servidor.
    } finally {
      setCall(null);
      setBusy(false);
    }
  };

  const openConversation = () => {
    stopIncomingCallAttention();
    window.location.assign(`/matches/${call.match_id}/conversa/`);
  };

  return (
    <div className="nk-incoming-call" role="dialog" aria-modal="true" aria-label={english ? "Incoming call" : "Chamada recebida"}>
      <div className="nk-incoming-call__photo">
        {caller.foto_url ? (
          <img src={caller.foto_url} alt={`${english ? "Photo of" : "Foto de"} ${caller.nome_publico || (english ? "NKATA member" : "membro NKATA")}`} />
        ) : (
          isVideo ? <Video size={28} /> : <Phone size={27} />
        )}
      </div>

      <div className="nk-incoming-call__body">
        <span>{isVideo ? (english ? "Incoming video call" : "Videochamada recebida") : (english ? "Incoming call" : "Chamada recebida")}</span>
        <strong>{caller.nome_publico || (english ? "NKATA member" : "Membro NKATA")}</strong>
        <small><MapPin size={12} /> {caller.cidade || "Moçambique"}</small>
      </div>

      <div className="nk-incoming-call__actions">
        <button type="button" className="is-decline" onClick={decline} disabled={busy} aria-label={english ? "Decline call" : "Recusar chamada"}>
          <PhoneOff size={20} />
        </button>
        <button type="button" className="is-open" onClick={openConversation} aria-label={english ? "Open call" : "Abrir chamada"}>
          {isVideo ? <Video size={21} /> : <Phone size={20} />}
          <span>{english ? "Open" : "Abrir"}</span>
        </button>
      </div>
    </div>
  );
}
