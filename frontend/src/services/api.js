import { normalizeAppUrl } from "./url.js";

const browserApiBase = window.location.protocol === "https:"
  ? window.location.origin
  : `${window.location.protocol}//${window.location.hostname}:8000`;
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

  const gallery = (profile.gallery || []).map((item) => ({
    id: item.id,
    mediaUrl: normalizeAppUrl(item.media_url || null),
    mediaType: item.media_type || "IMAGEM",
    caption: item.caption || "",
    visibility: item.visibility || "TODOS",
    createdAt: item.created_at || null,
    isCover: Boolean(item.is_cover),
    canBeCover: Boolean(item.can_be_cover),
  }));

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
    sobre_si: profile.sobre_si || "Este perfil ainda não acrescentou uma apresentação.",
    o_que_valoriza: profile.o_que_valoriza || "",
    o_que_nao_aceita: profile.o_que_nao_aceita || "",
    foto_url: normalizeAppUrl(
      profile.foto_url ||
      profile.foto_principal_url ||
      profile.foto_principal ||
      profile.foto ||
      null,
    ),
    verificado: profile.verificado ?? false,
    interesse_ativo: profile.interesse_ativo ?? false,
    status: profile.status || "",
    visivel: profile.visivel ?? true,
    tema_perfil: String(profile.tema_perfil || "CLASSICO").toLowerCase(),
    criado_em: profile.criado_em || null,
    cover_url: normalizeAppUrl(profile.cover_url || null),
    gallery,
    gallery_count: Number(profile.gallery_count ?? gallery.length),
  };
}

function normalizeProfileGallery(payload) {
  const source = payload?.gallery || payload || {};
  return {
    count: Number(source.count || 0),
    coverPublicationId: source.cover_publication_id || null,
    coverUrl: normalizeAppUrl(source.cover_url || null),
    results: (source.results || []).map((item) => ({
      id: item.id,
      mediaUrl: normalizeAppUrl(item.media_url || null),
      mediaType: item.media_type || "IMAGEM",
      caption: item.caption || "",
      visibility: item.visibility || "TODOS",
      createdAt: item.created_at || null,
      isCover: Boolean(item.is_cover),
      canBeCover: Boolean(item.can_be_cover),
    })),
  };
}

function normalizeAccount(account) {
  if (!account) return null;
  return {
    ...normalizeProfile(account),
    email: account.email || "",
    membro_desde: account.membro_desde || account.criado_em || null,
    total_matches: Number(account.total_matches || 0),
    total_interesses_enviados: Number(account.total_interesses_enviados || 0),
    destaque_publico: Boolean(account.destaque_publico),
    destaque_publico_consentido_em: account.destaque_publico_consentido_em || null,
    destaque_publico_exibicoes: Number(account.destaque_publico_exibicoes || 0),
    foto_destaque_publico_aprovada: Boolean(account.foto_destaque_publico_aprovada),
    destaque_publico_elegivel: Boolean(account.destaque_publico_elegivel),
  };
}

function normalizeMessage(message) {
  if (!message) return null;
  const rawType = String(message.tipo || "TEXTO").toUpperCase();
  const type = rawType === "AUDIO" ? "audio" : rawType === "CALL" ? "call" : "text";
  return {
    id: message.id,
    audioId: message.audio_id || null,
    callId: message.call_id || null,
    callType: message.call_type || null,
    callState: message.call_state || null,
    callLabel: message.call_label || message.texto || "Chamada",
    callDirection: message.call_direction || null,
    callMissed: Boolean(message.call_missed),
    matchId: message.match,
    senderId: message.remetente_id,
    senderName: message.remetente_nome || "Membro NKATA",
    type,
    text: message.texto || "",
    audioUrl: normalizeAppUrl(message.audio_url || null),
    durationSeconds: Number(message.duracao_segundos || 0),
    read: Boolean(message.lida),
    mine: Boolean(message.minha),
    createdAt: message.criado_em,
  };
}

function normalizeCallHistoryItem(item) {
  if (!item) return null;
  return normalizeMessage({
    id: `call-${item.id}`,
    tipo: "CALL",
    match: item.match_id,
    call_id: item.id,
    call_type: item.type,
    call_state: item.state,
    call_label: item.status_label,
    call_direction: item.direction,
    call_missed: item.missed,
    duracao_segundos: item.duration_seconds,
    texto: item.status_label,
    lida: true,
    minha: item.direction === "OUTGOING",
    criado_em: item.activity_at || item.ended_at || item.created_at,
  });
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

function normalizeNotification(notification) {
  if (!notification) return null;
  return {
    id: notification.id,
    type: notification.tipo,
    typeLabel: notification.tipo_display || "Notificação",
    title: notification.titulo || "Atualização no NKATA",
    text: notification.texto || "",
    read: Boolean(notification.lida),
    profile: normalizeProfile(notification.perfil),
    matchId: notification.match_id || null,
    createdAt: notification.criado_em,
    updatedAt: notification.atualizado_em || notification.criado_em,
  };
}

async function readJson(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) return null;
  return response.json();
}

function firstPayloadMessage(payload) {
  if (!payload) return "";
  if (typeof payload === "string") return payload;
  if (Array.isArray(payload)) {
    for (const value of payload) {
      const message = firstPayloadMessage(value);
      if (message) return message;
    }
    return "";
  }
  if (typeof payload !== "object") return "";

  for (const value of Object.values(payload)) {
    const message = firstPayloadMessage(value);
    if (message) return message;
  }
  return "";
}

export async function request(path, { method = "GET", body, signal, headers = {} } = {}) {
  const requestHeaders = { Accept: "application/json", ...headers };
  const normalizedMethod = method.toUpperCase();
  const isFormData = body instanceof FormData;

  if (body !== undefined && !isFormData) requestHeaders["Content-Type"] = "application/json";

  if (!["GET", "HEAD", "OPTIONS"].includes(normalizedMethod)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) requestHeaders["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: normalizedMethod,
    credentials: "include",
    headers: requestHeaders,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
    signal,
  });

  const payload = await readJson(response);
  if (!response.ok) {
    const message =
      payload?.detail ||
      payload?.message ||
      firstPayloadMessage(payload) ||
      `Não foi possível concluir o pedido (${response.status}).`;
    throw new ApiError(message, response.status, payload);
  }
  return payload;
}

export async function fetchSession({ signal } = {}) {
  return request("/api/session/", { signal });
}

export async function loginUser({ email, password }) {
  return request("/api/auth/login/", { method: "POST", body: { email, password } });
}

export async function logoutUser() {
  return request("/api/auth/logout/", { method: "POST" });
}

export async function submitAccessRequest(values, files) {
  const form = new FormData();
  Object.entries(values).forEach(([key, value]) => {
    if (typeof value === "boolean") {
      if (value) form.append(key, "on");
      return;
    }
    form.append(key, value ?? "");
  });
  Object.entries(files).forEach(([key, file]) => {
    if (file) form.append(key, file);
  });
  return request("/api/pedir-acesso/", { method: "POST", body: form });
}

export async function fetchAccessRequestStatus({ email, code }) {
  return request("/api/acompanhar-pedido/", {
    method: "POST",
    body: {
      email: String(email || "").trim().toLowerCase(),
      codigo: String(code || "").trim(),
    },
  });
}

export async function fetchProfiles({ signal } = {}) {
  const payload = await request("/api/perfis/", { signal });
  const results = Array.isArray(payload) ? payload : payload?.results || [];
  return results.map(normalizeProfile);
}

export async function fetchPublicProfilePreviews({ signal } = {}) {
  const payload = await request("/api/publico/perfis/", { signal });
  return {
    profiles: (payload?.results || []).map(normalizeProfile).filter(Boolean),
    rotationSeconds: Math.max(5, Number(payload?.rotation_seconds || 7)),
  };
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
  return request(`/api/perfis/${profileId}/interesse/`, { method: "POST" });
}

export async function fetchSavedProfiles({ signal } = {}) {
  const payload = await request("/api/minha-conta/guardados/", { signal });
  const results = Array.isArray(payload) ? payload : payload?.results || [];
  return results.map(normalizeProfile).filter(Boolean);
}

export async function toggleSavedProfile(profileId) {
  if (!profileId || String(profileId).startsWith("demo-")) {
    throw new ApiError("Entre para guardar este perfil na sua conta.", 403);
  }
  return request(`/api/perfis/${profileId}/guardar/`, { method: "POST" });
}

export async function reportProfile(profileId, { reason, details = "" }) {
  if (!profileId || String(profileId).startsWith("demo-")) throw new ApiError("Este perfil não pode ser denunciado.", 400);
  return request(`/api/perfis/${profileId}/denunciar/`, {
    method: "POST",
    body: { motivo: reason, detalhes: details },
  });
}

export async function blockProfile(profileId) {
  if (!profileId || String(profileId).startsWith("demo-")) throw new ApiError("Este perfil não pode ser bloqueado.", 400);
  return request(`/api/perfis/${profileId}/bloquear/`, { method: "POST" });
}

export async function fetchMyAccount({ signal } = {}) {
  const payload = await request("/api/minha-conta/", { signal });
  return normalizeAccount(payload);
}

export async function fetchMyAccountSummary({ signal } = {}) {
  return request("/api/minha-conta/resumo/", { signal });
}

export async function fetchMyAccountPreferences({ signal } = {}) {
  return request("/api/minha-conta/preferencias/", { signal });
}

export async function updateMyAccountPreferences(values) {
  return request("/api/minha-conta/preferencias/", { method: "PATCH", body: values });
}

export async function updateMyAccount(values) {
  const payload = await request("/api/minha-conta/", { method: "PATCH", body: values });
  return normalizeAccount(payload);
}

export async function uploadMyProfilePhoto(file) {
  const form = new FormData();
  form.append("foto", file);
  const payload = await request("/api/minha-conta/foto/", { method: "POST", body: form });
  return {
    message: payload?.message || "Fotografia atualizada.",
    account: normalizeAccount(payload?.account),
  };
}

export async function fetchMyProfileGallery({ signal } = {}) {
  const payload = await request("/api/minha-conta/galeria/", { signal });
  return normalizeProfileGallery(payload);
}

export async function updateMyProfileCover(publicationId) {
  const payload = await request("/api/minha-conta/capa/", {
    method: "PATCH",
    body: { publication_id: publicationId || null },
  });
  return {
    message: payload?.message || "Capa atualizada.",
    gallery: normalizeProfileGallery(payload),
  };
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

export async function closeMatch(matchId) {
  return request(`/api/minha-conta/matches/${matchId}/encerrar/`, { method: "POST" });
}

export async function fetchMatchConversation(matchId, { signal } = {}) {
  const [textPayload, audioPayload, callPayload] = await Promise.all([
    request(`/api/minha-conta/matches/${matchId}/conversa/`, { signal }),
    request(`/api/minha-conta/matches/${matchId}/audio/`, { signal }),
    request(`/api/minha-conta/matches/${matchId}/calls/history/`, { signal }),
  ]);

  const textMessages = (textPayload?.results || []).map(normalizeMessage).filter(Boolean);
  const audioMessages = (audioPayload?.results || []).map(normalizeMessage).filter(Boolean);
  const callMessages = (callPayload?.results || []).map(normalizeCallHistoryItem).filter(Boolean);
  const messages = [...textMessages, ...audioMessages, ...callMessages].sort((a, b) => (
    new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
  ));

  return {
    match: normalizeMatch(textPayload?.match),
    messages,
    capabilities: audioPayload?.capabilities || {
      text_enabled: true,
      audio_enabled: false,
      video_enabled: false,
      max_audio_seconds: 180,
    },
    audioSetupRequired: Boolean(audioPayload?.setup_required),
    callSetupRequired: Boolean(callPayload?.setup_required),
  };
}

export async function sendMatchMessage(matchId, text) {
  const payload = await request(`/api/minha-conta/matches/${matchId}/conversa/`, {
    method: "POST",
    body: { texto: text },
  });
  return normalizeMessage(payload);
}

export async function sendMatchAudio(matchId, blob, durationSeconds) {
  const form = new FormData();
  const mimeType = blob?.type || "audio/webm";
  const extension = mimeType.includes("mp4") ? "m4a" : mimeType.includes("ogg") ? "ogg" : "webm";
  form.append("audio", blob, `nota-voz.${extension}`);
  form.append("duracao_segundos", String(Math.max(1, Math.round(durationSeconds || 0))));

  const payload = await request(`/api/minha-conta/matches/${matchId}/audio/`, {
    method: "POST",
    body: form,
  });
  return normalizeMessage(payload);
}

export async function fetchMatchLive(matchId, { since = "", signal } = {}) {
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const payload = await request(`/api/minha-conta/matches/${matchId}/live/${suffix}`, { signal });
  return {
    messages: (payload?.results || []).map(normalizeMessage).filter(Boolean),
    typing: Boolean(payload?.presence?.typing),
    active: Boolean(payload?.presence?.active),
    readTextIds: (payload?.read_receipts?.text || []).map(Number),
    readAudioIds: (payload?.read_receipts?.audio || []).map(Number),
    serverTime: payload?.server_time || "",
    setupRequired: Boolean(payload?.setup_required),
  };
}

export async function updateMatchTyping(matchId, typing) {
  return request(`/api/minha-conta/matches/${matchId}/live/`, {
    method: "POST",
    body: { typing: Boolean(typing) },
  });
}

export async function fetchNotifications({ signal } = {}) {
  const payload = await request("/api/minha-conta/notificacoes/", { signal });
  return {
    unread: Number(payload?.unread || 0),
    setupRequired: Boolean(payload?.setup_required),
    results: (payload?.results || []).map(normalizeNotification).filter(Boolean),
  };
}

export async function markNotificationRead(notificationId) {
  return request(`/api/minha-conta/notificacoes/${notificationId}/ler/`, { method: "POST" });
}

export async function markAllNotificationsRead() {
  return request("/api/minha-conta/notificacoes/marcar-todas-lidas/", { method: "POST" });
}

export async function markMatchNotificationsRead(matchId) {
  return request(`/api/minha-conta/matches/${matchId}/notificacoes/lidas/`, { method: "POST" });
}

export {
  API_BASE_URL,
  normalizeAccount,
  normalizeMatch,
  normalizeMessage,
  normalizeNotification,
  normalizeProfile,
};
