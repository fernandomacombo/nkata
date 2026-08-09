import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { fetchMatchConversation } from "../../services/api.js";
import { endTrackedCall, fetchWebRtcReadiness } from "../../services/callApi.js";
import { fetchMyPlan } from "../../services/planApi.js";
import NkataCallExperience from "./NkataCallExperience.jsx";

function currentConversationMatchId() {
  const normalized = window.location.pathname.endsWith("/")
    ? window.location.pathname
    : `${window.location.pathname}/`;
  const match = normalized.match(/^\/matches\/(\d+)\/conversa\/$/);
  return match ? Number(match[1]) : null;
}

export default function ConversationCallBridge() {
  const [target, setTarget] = useState(null);
  const [matchId, setMatchId] = useState(() => currentConversationMatchId());
  const [match, setMatch] = useState(null);
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [videoEnabled, setVideoEnabled] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const sync = () => {
      setMatchId(currentConversationMatchId());
      setTarget(document.querySelector(".nk-conversation__options"));
    };
    sync();

    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("popstate", sync);
    return () => {
      observer.disconnect();
      window.removeEventListener("popstate", sync);
    };
  }, []);

  useEffect(() => {
    if (!matchId) return undefined;
    const currentMatchId = matchId;
    return () => {
      endTrackedCall(currentMatchId).catch(() => {});
    };
  }, [matchId]);

  useEffect(() => {
    if (!matchId || !target) {
      setMatch(null);
      return undefined;
    }

    const controller = new AbortController();
    Promise.all([
      fetchMatchConversation(matchId, { signal: controller.signal }),
      fetchMyPlan({ signal: controller.signal }),
      fetchWebRtcReadiness({ signal: controller.signal }),
    ])
      .then(([conversation, planPayload, readiness]) => {
        if (controller.signal.aborted) return;
        setMatch(conversation?.match || null);
        const features = planPayload?.current_plan?.features || {};
        const hasCallFeature = Boolean(features.chat_audio || features.chat_video);
        setAudioEnabled(Boolean(features.chat_audio));
        setVideoEnabled(Boolean(features.chat_video));

        if (hasCallFeature && !readiness.turnConfigured) {
          const warningKey = `nkata-turn-warning:${matchId}`;
          if (!window.sessionStorage.getItem(warningKey)) {
            window.sessionStorage.setItem(warningKey, "1");
            setNotice("As chamadas podem ter limitações nesta rede.");
          }
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setMatch(null);
      });

    return () => controller.abort();
  }, [matchId, target]);

  useEffect(() => {
    if (!notice) return undefined;
    const id = window.setTimeout(() => setNotice(""), 3000);
    return () => window.clearTimeout(id);
  }, [notice]);

  if (!target || !match) return null;

  return createPortal(
    <>
      <NkataCallExperience
        match={match}
        profile={match.otherProfile}
        audioEnabled={audioEnabled}
        videoEnabled={videoEnabled}
        onNotice={setNotice}
      />
      {notice && (
        <div className="nk-call-toast" role="status">
          {notice}
        </div>
      )}
    </>,
    target,
  );
}
