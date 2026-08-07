import { API_BASE_URL } from "./api.js";

export class FollowApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "FollowApiError";
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

async function requestFollow(profileId, method = "GET", { signal } = {}) {
  const headers = { Accept: "application/json" };
  if (method !== "GET") {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}/api/perfis/${profileId}/seguir/`, {
    method,
    credentials: "include",
    headers,
    signal,
  });
  const payload = await readPayload(response);

  if (!response.ok) {
    throw new FollowApiError(
      payload?.detail || "Não foi possível atualizar esta ligação.",
      response.status,
      payload,
    );
  }

  return payload;
}

export function fetchFollowState(profileId, options = {}) {
  return requestFollow(profileId, "GET", options);
}

export function toggleFollowProfile(profileId) {
  return requestFollow(profileId, "POST");
}
