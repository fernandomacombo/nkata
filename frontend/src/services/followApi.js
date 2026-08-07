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

async function request(path, method = "GET", { signal } = {}) {
  const headers = { Accept: "application/json" };
  if (method !== "GET") {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
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

function normalizeFollowProfile(profile) {
  return {
    id: profile.id,
    nome_publico: profile.nome_publico || "Perfil NKATA",
    idade: profile.idade || null,
    cidade: profile.cidade || "Moçambique",
    objetivo_display: profile.objetivo_display || profile.objetivo || "Conhecer com intenção",
    foto_url: profile.foto_principal || null,
    verificado: Boolean(profile.verificado),
  };
}

export function fetchFollowState(profileId, options = {}) {
  return request(`/api/perfis/${profileId}/seguir/`, "GET", options);
}

export function toggleFollowProfile(profileId) {
  return request(`/api/perfis/${profileId}/seguir/`, "POST");
}

export async function fetchFollowingProfiles(options = {}) {
  const payload = await request("/api/minha-conta/a-seguir/", "GET", options);
  return {
    count: Number(payload?.count || 0),
    results: (payload?.results || []).map(normalizeFollowProfile),
  };
}
