const browserApiBase = `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || browserApiBase).replace(/\/$/, "");

export class QuestionnaireApiError extends Error {
  constructor(message, status, payload = null) {
    super(message);
    this.name = "QuestionnaireApiError";
    this.status = status;
    this.payload = payload;
  }
}

async function readJson(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) return null;
  return response.json();
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });

  const payload = await readJson(response);
  if (!response.ok) {
    throw new QuestionnaireApiError(
      payload?.detail || `Não foi possível concluir o pedido (${response.status}).`,
      response.status,
      payload,
    );
  }
  return payload;
}

export function fetchQuestionnaire(token, { signal } = {}) {
  return request(`/api/questionario/${token}/`, { signal });
}

export function submitQuestionnaire(token, values) {
  return request(`/api/questionario/${token}/`, {
    method: "POST",
    body: values,
  });
}

export function createQuestionnairePassword(token, { password, confirmation }) {
  return request(`/api/questionario/${token}/criar-senha/`, {
    method: "POST",
    body: { password, confirmation },
  });
}
