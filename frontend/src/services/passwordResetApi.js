import { API_BASE_URL, ApiError } from "./api.js";

async function call(path, { method = "GET", body, signal } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    throw new ApiError(
      payload?.detail || "Não foi possível concluir a recuperação da palavra-passe.",
      response.status,
      payload,
    );
  }

  return payload;
}

export function requestPasswordReset(email) {
  return call("/api/auth/password-reset/", {
    method: "POST",
    body: { email: String(email || "").trim().toLowerCase() },
  });
}

export function validatePasswordReset(uid, token, { signal } = {}) {
  return call(`/api/auth/password-reset/${encodeURIComponent(uid)}/${encodeURIComponent(token)}/`, {
    signal,
  });
}

export function confirmPasswordReset(uid, token, { password, confirmation }) {
  return call(`/api/auth/password-reset/${encodeURIComponent(uid)}/${encodeURIComponent(token)}/`, {
    method: "POST",
    body: { password, confirmation },
  });
}
