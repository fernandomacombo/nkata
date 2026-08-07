const browserApiBase = `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || browserApiBase).replace(/\/$/, "");

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

export async function changeAccountPassword({ currentPassword, newPassword, confirmation }) {
  const headers = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
  const csrfToken = getCookie("csrftoken");
  if (csrfToken) headers["X-CSRFToken"] = csrfToken;

  const response = await fetch(`${API_BASE_URL}/api/auth/password-change/`, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
      confirmation,
    }),
  });

  const payload = await readJson(response);
  if (!response.ok) {
    throw new AccountSecurityApiError(
      payload?.detail || `Não foi possível alterar a palavra-passe (${response.status}).`,
      response.status,
      payload,
    );
  }

  return payload;
}
