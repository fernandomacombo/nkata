import { resolveApiBaseUrl } from "./apiRuntime.js";

const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, window.location);

export class PlanApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "PlanApiError";
    this.status = status;
    this.payload = payload;
  }
}

export async function fetchMyPlan({ signal } = {}) {
  const response = await fetch(`${API_BASE_URL}/api/minha-conta/plano/`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: "application/json" },
    signal,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    throw new PlanApiError(
      payload?.detail || `Não foi possível consultar o plano (${response.status}).`,
      response.status,
      payload,
    );
  }

  return payload;
}
