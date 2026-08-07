/*
 * NKATA — produto idealizado e criado por Fernando Macombo.
 * Moçambique, 2026. Consulte /AUTHORSHIP.md para registo de autoria.
 */
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import AccessRequestPage from "./pages/AccessRequestPage.jsx";
import AccessStatusPage from "./pages/AccessStatusPage.jsx";
import PasswordResetConfirmPage from "./pages/PasswordResetConfirmPage.jsx";
import PasswordResetPage from "./pages/PasswordResetPage.jsx";
import QuestionnairePage from "./pages/QuestionnairePage.jsx";
import "./styles.css";
import "./profile-detail.css";
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
import "./global-motion.css";
import "./login-polish.css";
import "./mobile-menu.css";
import "./mobile-menu-close-fix.css";
import "./community-empty.css";
import "./questionnaire.css";
import "./password-recovery.css";

const normalizedPath = window.location.pathname.endsWith("/")
  ? window.location.pathname
  : `${window.location.pathname}/`;
const accessMode = normalizedPath === "/pedir-acesso/";
const accessStatusMode = normalizedPath === "/acompanhar-pedido/";
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
    {accessMode ? (
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
      <App />
    )}
  </React.StrictMode>
);
