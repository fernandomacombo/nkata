import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";
import "./profile-detail.css";
import "./integration.css";
import "./features.css";
import "./auth.css";
import "./messaging.css";
import "./account.css";
import "./account-enhancements.css";
import "./home-refresh.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
