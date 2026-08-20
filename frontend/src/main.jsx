/*
 * NKATA — produto idealizado e criado por Fernando Macombo.
 * Moçambique, 2026. Consulte /AUTHORSHIP.md para registo de autoria.
 */
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import FollowingPanel from "./components/account/FollowingPanel.jsx";
import ConversationCallBridge from "./components/chat/ConversationCallBridge.jsx";
import IncomingCallWatcher from "./components/chat/IncomingCallWatcher.jsx";
import PublicationSafetyOverlay from "./components/feed/PublicationSafetyOverlay.jsx";
import ProfileFollowAction from "./components/profile/ProfileFollowAction.jsx";
import AccessRequestPage from "./pages/AccessRequestPage.jsx";
import AccessStatusPage from "./pages/AccessStatusPage.jsx";
import IdentityCapturePage from "./pages/IdentityCapturePage.jsx";
import PasswordChangePage from "./pages/PasswordChangePage.jsx";
import PasswordResetConfirmPage from "./pages/PasswordResetConfirmPage.jsx";
import PasswordResetPage from "./pages/PasswordResetPage.jsx";
import QuestionnairePage from "./pages/QuestionnairePage.jsx";
import "./styles.css";
import "./profile-detail.css";
import "./profile-signals.css";
import "./profile-follow.css";
import "./following-panel.css";
import "./integration.css";
import "./features.css";
import "./auth.css";
import "./messaging.css";
import "./account.css";
import "./account-enhancements.css";
import "./home-refresh.css";
import "./safety.css";
import "./safety-layout.css";
import "./notifications.css";
import "./notifications-motion.css";
import "./access.css";
import "./access-status.css";
import "./nkata-id.css";
import "./global-motion.css";
import "./login-polish.css";
import "./mobile-menu.css";
import "./mobile-menu-close-fix.css";
import "./community-empty.css";
import "./questionnaire.css";
import "./password-recovery.css";
import "./password-change.css";
import "./plan.css";
import "./mobile-native.css";
import "./mobile-native-screens.css";
import "./moments.css";
import "./moments-safety.css";
import "./moments-autoplay.css";
import "./moments-reactions.css";
import "./feed.css";
import "./feed-cleanup.css";
import "./feed-safety.css";
import "./profile-cards-premium.css";
import "./chat-native-premium.css";
import "./chat-realtime.css";
import "./call-webrtc.css";
import "./call-mobile-layout.css";
import "./call-history.css";
import "./mobile-app-contract.css";

const appModeMedia = window.matchMedia("(max-width: 820px)");

function syncAppMode(event = appModeMedia) {
  const enabled = Boolean(event.matches);
  document.body.classList.toggle("nk-app-mode", enabled);
  document.documentElement.dataset.nkataMode = enabled ? "app" : "web";
}

syncAppMode();
if (typeof appModeMedia.addEventListener === "function") {
  appModeMedia.addEventListener("change", syncAppMode);
} else {
  appModeMedia.addListener(syncAppMode);
}

const normalizedPath = window.location.pathname.endsWith("/")
  ? window.location.pathname
  : `${window.location.pathname}/`;
const accessMode = normalizedPath === "/pedir-acesso/";
const accessStatusMode = normalizedPath === "/acompanhar-pedido/";
const identityVerificationMatch = normalizedPath.match(
  /^\/verificar-identidade\/([0-9a-f-]{36})\/$/i,
);
const identityVerificationToken = identityVerificationMatch?.[1] || "";
const passwordChangeMode = normalizedPath === "/alterar-senha/";
const passwordResetMode = normalizedPath === "/recuperar-senha/";
const questionnaireMatch = normalizedPath.match(/^\/questionario\/([0-9a-f-]{36})\/$/i);
const questionnaireToken = questionnaireMatch?.[1] || "";
const passwordResetConfirmMatch = normalizedPath.match(/^\/nova-senha\/([^/]+)\/([^/]+)\/$/);
const passwordResetUid = passwordResetConfirmMatch?.[1] || "";
const passwordResetToken = passwordResetConfirmMatch?.[2] || "";

function go(path) {
  window.location.assign(path);
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {identityVerificationToken ? (
      <IdentityCapturePage
        token={identityVerificationToken}
        onExit={() => {
          if (window.opener) window.close();
          else go("/");
        }}
      />
    ) : accessMode ? (
      <AccessRequestPage
        onBack={() => go("/")}
        onLogin={() => go("/entrar/")}
        onFinish={() => go("/")}
        onTrack={() => go("/acompanhar-pedido/")}
      />
    ) : accessStatusMode ? (
      <AccessStatusPage
        onBack={() => go("/")}
        onRequest={() => go("/pedir-acesso/")}
        onLogin={() => go("/entrar/")}
      />
    ) : questionnaireToken ? (
      <QuestionnairePage
        token={questionnaireToken}
        onBack={() => go("/")}
        onLogin={() => go("/entrar/")}
      />
    ) : passwordChangeMode ? (
      <PasswordChangePage
        onBack={() => go("/conta/")}
        onLogin={() => go("/entrar/")}
      />
    ) : passwordResetMode ? (
      <PasswordResetPage
        onBack={() => go("/")}
        onLogin={() => go("/entrar/")}
      />
    ) : passwordResetUid && passwordResetToken ? (
      <PasswordResetConfirmPage
        uid={passwordResetUid}
        token={passwordResetToken}
        onBack={() => go("/")}
        onLogin={() => go("/entrar/")}
        onRestart={() => go("/recuperar-senha/")}
      />
    ) : (
      <>
        <App />
        <ProfileFollowAction />
        <FollowingPanel />
        <PublicationSafetyOverlay />
        <ConversationCallBridge />
        <IncomingCallWatcher />
      </>
    )}
  </React.StrictMode>
);
