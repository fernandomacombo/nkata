import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import AccessRequestPage from "./pages/AccessRequestPage.jsx";
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

const normalizedPath = window.location.pathname.endsWith("/")
  ? window.location.pathname
  : `${window.location.pathname}/`;
const accessMode = normalizedPath === "/pedir-acesso/";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {accessMode ? (
      <AccessRequestPage
        onBack={() => window.location.assign("/")}
        onLogin={() => window.location.assign("/entrar/")}
        onFinish={() => window.location.assign("/")}
      />
    ) : (
      <App />
    )}
  </React.StrictMode>
);
