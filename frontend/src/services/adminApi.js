import { request } from "./api.js";

export function fetchAdminSummary({ signal } = {}) {
  return request("/api/painel/resumo/", { signal });
}

export function fetchAdminList({ section, stage, query = "", status = "", kind = "", offset = 0, auditScope, auditEntry, signal } = {}) {
  const params = new URLSearchParams({ section, limit: "50" });
  if (stage) params.set("stage", stage);
  if (query.trim()) params.set("q", query.trim());
  if (status) params.set("status", status);
  if (kind) params.set("kind", kind);
  if (section === "audit" && auditScope && auditEntry) {
    params.set("audit_scope", auditScope);
    params.set("audit_entry", String(auditEntry));
  }
  if (offset) params.set("offset", String(offset));
  return request(`/api/painel/lista/?${params.toString()}`, { signal });
}

export function fetchAdminAccessDetail(id, { signal } = {}) {
  return request(`/api/painel/pedidos/${id}/`, { signal });
}

export function performAdminAction(payload) {
  return request("/api/painel/acoes/", {
    method: "POST",
    body: payload,
  });
}

export function fetchAdminStaff({ signal } = {}) {
  return request("/api/painel/equipa/", { signal });
}

export function createAdminStaff(payload) {
  return request("/api/painel/equipa/", { method: "POST", body: payload });
}

export function updateAdminStaff(id, payload) {
  return request(`/api/painel/equipa/${id}/`, { method: "PATCH", body: payload });
}

export function fetchAdminMemberDossier(id, { signal } = {}) {
  return request(`/api/painel/membros/${id}/ficha/`, { signal });
}
