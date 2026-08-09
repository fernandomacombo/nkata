import { request } from "./api.js";

export function fetchAdminSummary({ signal } = {}) {
  return request("/api/painel/resumo/", { signal });
}

export function fetchAdminList({ section, query = "", status = "", kind = "", signal } = {}) {
  const params = new URLSearchParams({ section, limit: "50" });
  if (query.trim()) params.set("q", query.trim());
  if (status) params.set("status", status);
  if (kind) params.set("kind", kind);
  return request(`/api/painel/lista/?${params.toString()}`, { signal });
}

export function performAdminAction(payload) {
  return request("/api/painel/acoes/", {
    method: "POST",
    body: payload,
  });
}
