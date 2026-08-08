import { API_BASE_URL } from "./api.js";

let trackedCall = null;

export class CallApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "CallApiError";
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

function trackCall(matchId, call) {
  if (!call?.id) {
    if (trackedCall?.matchId === Number(matchId)) trackedCall = null;
    return;
  }
  trackedCall = {
    matchId: Number(matchId),
    callId: Number(call.id),
  };
}

async function request(path, { method = "GET", body, signal, keepalive = false } = {}) {
  const normalizedMethod = method.toUpperCase();
  const headers = { Accept: "application/json" };
  if (!["GET", "HEAD", "OPTIONS"].includes(normalizedMethod)) {
    headers["Content-Type"] = "application/json";
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: normalizedMethod,
    credentials: "include",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
    keepalive,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    throw new CallApiError(
      payload?.detail || `Não foi possível concluir a chamada (${response.status}).`,
      response.status,
      payload,
    );
  }
  return payload;
}

export async function fetchCallState(matchId, { sinceSignalId = 0, signal } = {}) {
  const params = new URLSearchParams();
  if (sinceSignalId) params.set("since_signal_id", String(sinceSignalId));
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const payload = await request(`/api/minha-conta/matches/${matchId}/call/${suffix}`, { signal });
  trackCall(matchId, payload?.call || null);
  return {
    call: payload?.call || null,
    signals: Array.isArray(payload?.signals) ? payload.signals : [],
    iceServers: Array.isArray(payload?.ice_servers) ? payload.ice_servers : [],
    ringTimeoutSeconds: Number(payload?.ring_timeout_seconds || 45),
    setupRequired: Boolean(payload?.setup_required),
  };
}

export async function startMatchCall(matchId, type) {
  const payload = await request(`/api/minha-conta/matches/${matchId}/call/`, {
    method: "POST",
    body: { action: "start", type },
  });
  trackCall(matchId, payload?.call || null);
  return payload;
}

export async function updateMatchCall(matchId, callId, action) {
  const payload = await request(`/api/minha-conta/matches/${matchId}/call/`, {
    method: "POST",
    body: { action, call_id: callId },
  });
  if (["end", "decline", "failed"].includes(String(action))) {
    trackedCall = null;
  } else if (payload?.call) {
    trackCall(matchId, payload.call);
  }
  return payload;
}

export async function endTrackedCall(matchId = null) {
  if (!trackedCall) return;
  if (matchId !== null && Number(matchId) !== trackedCall.matchId) return;

  const current = trackedCall;
  trackedCall = null;
  try {
    await request(`/api/minha-conta/matches/${current.matchId}/call/`, {
      method: "POST",
      body: { action: "end", call_id: current.callId },
      keepalive: true,
    });
  } catch {
    // Encerramento best-effort ao sair da conversa.
  }
}

export async function sendCallSignal(matchId, callId, signalType, payload) {
  return request(`/api/minha-conta/matches/${matchId}/call/`, {
    method: "POST",
    body: {
      action: "signal",
      call_id: callId,
      signal_type: signalType,
      payload,
    },
  });
}

export async function fetchIncomingCall({ signal } = {}) {
  const payload = await request("/api/minha-conta/chamadas/entrada/", { signal });
  return {
    call: payload?.call || null,
    setupRequired: Boolean(payload?.setup_required),
  };
}

if (typeof window !== "undefined") {
  window.addEventListener("pagehide", () => {
    if (!trackedCall) return;
    const current = trackedCall;
    trackedCall = null;
    const csrfToken = getCookie("csrftoken");
    fetch(`${API_BASE_URL}/api/minha-conta/matches/${current.matchId}/call/`, {
      method: "POST",
      credentials: "include",
      keepalive: true,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      },
      body: JSON.stringify({ action: "end", call_id: current.callId }),
    }).catch(() => {});
  });
}
