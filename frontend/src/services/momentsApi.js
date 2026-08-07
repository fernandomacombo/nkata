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

export async function createMoment({ text, visibility, media }) {
  const form = new FormData();
  form.append("texto", text || "");
  form.append("visibilidade", visibility || "TODOS");
  if (media) form.append("media", media);

  const headers = { Accept: "application/json" };
  const csrfToken = getCookie("csrftoken");
  if (csrfToken) headers["X-CSRFToken"] = csrfToken;

  const response = await fetch(`${API_BASE_URL}/api/momentos/`, {
    method: "POST",
    credentials: "include",
    headers,
    body: form,
  });
  const payload = await readPayload(response);
  if (!response.ok) {
    throw new MomentsApiError(
      payload?.detail || payload?.media?.[0] || payload?.texto?.[0] || "Não foi possível publicar o Momento.",
      response.status,
      payload,
    );
  }
  return payload;
}

export async function deleteMoment(momentId) {
  const headers = { Accept: "application/json" };
  const csrfToken = getCookie("csrftoken");
  if (csrfToken) headers["X-CSRFToken"] = csrfToken;

  const response = await fetch(`${API_BASE_URL}/api/momentos/${momentId}/`, {
    method: "DELETE",
    credentials: "include",
    headers,
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
