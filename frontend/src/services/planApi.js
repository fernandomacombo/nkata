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

async function paymentRequest(path, body) {
  const csrf = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith("csrftoken="));
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: body === undefined ? "GET" : "POST",
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json",
      ...(csrf ? { "X-CSRFToken": decodeURIComponent(csrf.slice("csrftoken=".length)) } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new PlanApiError(payload?.detail || "Não foi possível consultar o pagamento.", response.status, payload);
  return payload;
}

export const fetchPayments = () => paymentRequest("/api/minha-conta/pagamentos/");
export const createPayment = (product, key) => paymentRequest("/api/minha-conta/pagamentos/", { product, key });
export const checkPayment = (id) => paymentRequest(`/api/minha-conta/pagamentos/${encodeURIComponent(id)}/verificar/`, {});
