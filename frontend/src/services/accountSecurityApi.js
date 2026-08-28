import { resolveApiBaseUrl } from "./apiRuntime.js";

const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, window.location);

export class AccountSecurityApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "AccountSecurityApiError";
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

async function securityRequest(path, { method = "GET", body } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";

  if (!["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    credentials: "include",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const payload = await readJson(response);
  if (!response.ok) {
    throw new AccountSecurityApiError(
      payload?.detail || `Não foi possível concluir o pedido (${response.status}).`,
      response.status,
      payload,
    );
  }

  return payload;
}

export async function changeAccountPassword({ currentPassword, newPassword, confirmation }) {
  return securityRequest("/api/auth/password-change/", {
    method: "POST",
    body: {
      current_password: currentPassword,
      new_password: newPassword,
      confirmation,
    },
  });
}

export async function fetchAccountSessions() {
  return securityRequest("/api/auth/sessions/");
}

export async function terminateOtherSessions() {
  return securityRequest("/api/auth/sessions/terminate-others/", {
    method: "POST",
  });
}
