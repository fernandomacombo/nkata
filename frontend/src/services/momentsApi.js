import { API_BASE_URL } from "./api.js";

export class MomentsApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "MomentsApiError";
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

function csrfHeaders() {
  const headers = { Accept: "application/json" };
  const csrfToken = getCookie("csrftoken");
  if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  return headers;
}

export async function fetchMoments({ signal } = {}) {
  const response = await fetch(`${API_BASE_URL}/api/momentos/`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
    signal,
  });
  const payload = await readPayload(response);
  if (!response.ok) {
    throw new MomentsApiError(
      payload?.detail || `Não foi possível consultar os Momentos (${response.status}).`,
      response.status,
      payload,
    );
  }
  return payload;
}

export async function createMoment({ caption, visibility, media }) {
  const form = new FormData();
  form.append("legenda", caption || "SEM_LEGENDA");
  form.append("visibilidade", visibility || "TODOS");
  if (media) form.append("media", media);

  const response = await fetch(`${API_BASE_URL}/api/momentos/`, {
    method: "POST",
    credentials: "include",
    headers: csrfHeaders(),
    body: form,
  });
  const payload = await readPayload(response);
  if (!response.ok) {
    throw new MomentsApiError(
      payload?.detail
        || payload?.media?.[0]
        || payload?.legenda?.[0]
        || "Não foi possível publicar o Momento.",
      response.status,
      payload,
    );
  }
  return payload;
}

export async function deleteMoment(momentId) {
  const response = await fetch(`${API_BASE_URL}/api/momentos/${momentId}/`, {
    method: "DELETE",
    credentials: "include",
    headers: csrfHeaders(),
  });
  const payload = await readPayload(response);
  if (!response.ok) {
    throw new MomentsApiError(
      payload?.detail || "Não foi possível remover o Momento.",
      response.status,
      payload,
    );
  }
  return payload;
}

export async function fetchMomentReactions(momentId, { signal } = {}) {
  const response = await fetch(`${API_BASE_URL}/api/momentos/${momentId}/reacoes/`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
    signal,
  });
  const payload = await readPayload(response);
  if (!response.ok) {
    throw new MomentsApiError(
      payload?.detail || "Não foi possível consultar as reações deste Momento.",
      response.status,
      payload,
    );
  }
  return payload?.reactions || null;
}

export async function toggleMomentReaction(momentId, reactionType) {
  const response = await fetch(`${API_BASE_URL}/api/momentos/${momentId}/reacoes/`, {
    method: "POST",
    credentials: "include",
    headers: {
      ...csrfHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ tipo: reactionType }),
  });
  const payload = await readPayload(response);
  if (!response.ok) {
    throw new MomentsApiError(
      payload?.detail || payload?.tipo?.[0] || "Não foi possível enviar a reação.",
      response.status,
      payload,
    );
  }
  return payload;
}
