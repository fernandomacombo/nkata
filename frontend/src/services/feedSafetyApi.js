import { API_BASE_URL } from "./api.js";

export class FeedSafetyApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "FeedSafetyApiError";
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

async function readPayload(response) {
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : null;
}

async function request(path, { method = "GET", body = null } = {}) {
  const headers = { Accept: "application/json" };
  const csrfToken = getCookie("csrftoken");
  if (method !== "GET" && csrfToken) headers["X-CSRFToken"] = csrfToken;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    body,
    headers,
    credentials: "include",
  });
  const payload = await readPayload(response);

  if (!response.ok) {
    throw new FeedSafetyApiError(
      payload?.detail || "Não foi possível concluir esta ação.",
      response.status,
      payload,
    );
  }
  return payload;
}

export function hidePublication(publicationId) {
  return request(`/api/publicacoes/${publicationId}/ocultar/`, { method: "POST" });
}

export function reportPublication(publicationId, reason) {
  const form = new FormData();
  form.append("motivo", reason);
  return request(`/api/publicacoes/${publicationId}/denunciar/`, {
    method: "POST",
    body: form,
  });
}
