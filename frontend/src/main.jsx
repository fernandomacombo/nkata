/*
 * NKATA — produto idealizado e criado por Fernando Macombo.
 * Moçambique, 2026. Consulte /AUTHORSHIP.md para registo de autoria.
 */
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import AccessRequestPage from "./pages/AccessRequestPage.jsx";
import AccessStatusPage from "./pages/AccessStatusPage.jsx";
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

const normalizedPath = window.location.pathname.endsWith("/")
  ? window.location.pathname
  : `${window.location.pathname}/`;
const accessMode = normalizedPath === "/pedir-acesso/";
const accessStatusMode = normalizedPath === "/acompanhar-pedido/";

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
    ) : (
      <App />
    )}
  </React.StrictMode>
);
