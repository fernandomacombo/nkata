import { resolveApiBaseUrl } from "./apiRuntime.js";

const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, window.location);

export class SignalApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "SignalApiError";
    this.status = status;
    this.payload = payload;
  }
}

function getCookie(name) {
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
}

async function readJson(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) return null;
  return response.json();
}

async function request(profileId, options = {}) {
  const headers = { Accept: "application/json" };
  const method = (options.method || "GET").toUpperCase();

  if (options.body) headers["Content-Type"] = "application/json";
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}/api/perfis/${profileId}/sinais/`, {
    method,
    credentials: "include",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  const payload = await readJson(response);
  if (!response.ok) {
    throw new SignalApiError(
      payload?.detail || `Não foi possível concluir o envio (${response.status}).`,
      response.status,
      payload,
    );
  }
  return payload;
}

export function fetchProfileSignals(profileId, { signal } = {}) {
  return request(profileId, { signal });
}

export function sendProfileSignal(profileId, type) {
  return request(profileId, {
    method: "POST",
    body: { tipo: type },
  });
}
