import { API_BASE_URL } from "./api.js";

export class FeedApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "FeedApiError";
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

async function request(path, { method = "GET", body = null, signal } = {}) {
  const headers = { Accept: "application/json" };
  const csrfToken = getCookie("csrftoken");
  if (method !== "GET" && csrfToken) headers["X-CSRFToken"] = csrfToken;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    body,
    credentials: "include",
    headers,
    signal,
  });
  const payload = await readPayload(response);

  if (!response.ok) {
    throw new FeedApiError(
      payload?.detail || "Não foi possível concluir esta ação.",
      response.status,
      payload,
    );
  }

  return payload;
}

export function fetchPublications(options = {}) {
  return request("/api/publicacoes/", options);
}

export function createPublication({ media, caption, visibility }) {
  const form = new FormData();
  form.append("media", media);
  form.append("legenda", caption || "SEM_LEGENDA");
  form.append("visibilidade", visibility || "TODOS");
  return request("/api/publicacoes/", { method: "POST", body: form });
}

export function togglePublicationReaction(publicationId, type) {
  const form = new FormData();
  form.append("tipo", type);
  return request(`/api/publicacoes/${publicationId}/reacoes/`, {
    method: "POST",
    body: form,
  });
}

export function deletePublication(publicationId) {
  return request(`/api/publicacoes/${publicationId}/`, { method: "DELETE" });
}
