const browserApiBase = `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || browserApiBase).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "ApiError";
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

function normalizeProfile(profile) {
  if (!profile) return null;

  return {
    id: profile.id,
    nome_publico: profile.nome_publico || profile.nome || "Perfil NKATA",
    idade: profile.idade,
    cidade: profile.cidade || "Moçambique",
    genero: profile.genero,
    genero_display: profile.genero_display || profile.genero || "",
    objetivo: profile.objetivo,
    objetivo_display:
      profile.objetivo_display ||
      profile.objetivo_label ||
      profile.objetivo ||
      "Conhecer com intenção",
    sobre_si:
      profile.sobre_si ||
      "Este perfil ainda não acrescentou uma apresentação.",
    o_que_valoriza: profile.o_que_valoriza || "",
    o_que_nao_aceita: profile.o_que_nao_aceita || "",
    foto_url:
      profile.foto_url ||
      profile.foto_principal_url ||
      profile.foto_principal ||
      profile.foto ||
      null,
    verificado: profile.verificado ?? false,
    interesse_ativo: profile.interesse_ativo ?? false,
    criado_em: profile.criado_em || null,
  };
}

function normalizeMessage(message) {
  if (!message) return null;

  return {
    id: message.id,
    matchId: message.match,
    senderId: message.remetente_id,
    senderName: message.remetente_nome || "Membro NKATA",
    text: message.texto || "",
    read: Boolean(message.lida),
    mine: Boolean(message.minha),
    createdAt: message.criado_em,
  };
}

function normalizeMatch(match) {
  if (!match) return null;

  return {
    id: match.id,
    otherProfile: normalizeProfile(match.outro_perfil || match.perfil_2 || match.perfil_1),
    type: match.tipo_origem,
    typeLabel: match.tipo_origem_display || "Interesse mútuo",
    status: match.status,
    lastMessage: normalizeMessage(match.ultima_mensagem),
    unreadCount: Number(match.mensagens_nao_lidas || 0),
    createdAt: match.criado_em,
    updatedAt: match.atualizado_em,
  };
}

async function readJson(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) return null;
  return response.json();
}

async function request(
  path,
  {
    method = "GET",
    body,
    signal,
    headers = {},
  } = {},
) {
  const requestHeaders = {
    Accept: "application/json",
    ...headers,
  };

  const normalizedMethod = method.toUpperCase();

  if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
  }

  if (!["GET", "HEAD", "OPTIONS"].includes(normalizedMethod)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) requestHeaders["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: normalizedMethod,
    credentials: "include",
    headers: requestHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  const payload = await readJson(response);

  if (!response.ok) {
    const message =
      payload?.detail ||
      payload?.message ||
      `Não foi possível concluir o pedido (${response.status}).`;
    throw new ApiError(message, response.status, payload);
  }

  return payload;
}

export async function fetchSession({ signal } = {}) {
  return request("/api/session/", { signal });
}

export async function loginUser({ email, password }) {
  return request("/api/auth/login/", {
    method: "POST",
    body: { email, password },
  });
}

export async function logoutUser() {
  return request("/api/auth/logout/", { method: "POST" });
}

export async function fetchProfiles({ signal } = {}) {
  const payload = await request("/api/perfis/", { signal });
  const results = Array.isArray(payload) ? payload : payload?.results || [];
  return results.map(normalizeProfile);
}

export async function fetchProfileDetail(profileId, { signal } = {}) {
  if (!profileId || String(profileId).startsWith("demo-")) {
    throw new ApiError("Este é um perfil demonstrativo.", 400);
  }

  const payload = await request(`/api/perfis/${profileId}/`, { signal });
  return normalizeProfile(payload);
}

export async function toggleProfileInterest(profileId) {
  if (!profileId || String(profileId).startsWith("demo-")) {
    throw new ApiError("Entre numa conta aprovada para usar esta função.", 403);
  }

  return request(`/api/perfis/${profileId}/interesse/`, {
    method: "POST",
  });
}

export async function fetchMyInterests({ signal } = {}) {
  const payload = await request("/api/minha-conta/interesses/", { signal });
  const results = Array.isArray(payload) ? payload : payload?.results || [];
  return results.map(normalizeProfile);
}

export async function fetchMyMatches({ signal } = {}) {
  const payload = await request("/api/minha-conta/matches/", { signal });
  const results = Array.isArray(payload) ? payload : payload?.results || [];
  return results.map(normalizeMatch).filter(Boolean);
}

export async function fetchMatchConversation(matchId, { signal } = {}) {
  const payload = await request(
    `/api/minha-conta/matches/${matchId}/conversa/`,
    { signal },
  );

  return {
    match: normalizeMatch(payload?.match),
    messages: (payload?.results || []).map(normalizeMessage).filter(Boolean),
  };
}

export async function sendMatchMessage(matchId, text) {
  const payload = await request(
    `/api/minha-conta/matches/${matchId}/conversa/`,
    {
      method: "POST",
      body: { texto: text },
    },
  );

  return normalizeMessage(payload);
}

export {
  API_BASE_URL,
  normalizeMatch,
  normalizeMessage,
  normalizeProfile,
};
