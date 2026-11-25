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
export const closePaymentIfTerminal = (id) => paymentRequest(`/api/minha-conta/pagamentos/${encodeURIComponent(id)}/encerrar/`, {});

export const claimWelcome = () => paymentRequest("/api/minha-conta/carteira/boas-vindas/", {});

export async function fetchWalletStatement({period="30", kind="ALL", before=0, signal} = {}) {
  const params = new URLSearchParams({period, kind, before:String(before)});
  const response = await fetch(`${API_BASE_URL}/api/minha-conta/carteira/movimentos/?${params}`, {
    credentials:"include", headers:{Accept:"application/json"}, signal, cache:"no-store",
  });
  const payload = await response.json().catch(()=>null);
  if (!response.ok) throw new PlanApiError(payload?.detail || "Não foi possível consultar os movimentos.", response.status, payload);
  return payload;
}


export async function downloadWalletStatement({period="30",kind="ALL"}={}) {
  const params=new URLSearchParams({period,kind});
  const response=await fetch(`${API_BASE_URL}/api/minha-conta/carteira/extrato.pdf?${params}`,{
    credentials:"include",headers:{Accept:"application/pdf, application/json"},cache:"no-store"
  });
  if(!response.ok || !(response.headers.get("content-type")||"").includes("application/pdf")){
    const payload=await response.json().catch(()=>null);
    throw new PlanApiError(payload?.detail || "Não foi possível descarregar o extrato.",response.status,payload);
  }
  const blob=await response.blob();
  const url=URL.createObjectURL(blob);
  const link=document.createElement("a");
  link.href=url;link.download="NKATA-extrato-creditos.pdf";document.body.appendChild(link);
  link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
}
