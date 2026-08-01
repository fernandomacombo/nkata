const browserApiBase = `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || browserApiBase).replace(/\/$/, "");

function normalizeProfile(profile) {
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
      "Perfil aprovado pela comunidade NKATA, com intenção clara e dados pessoais protegidos.",
    o_que_valoriza: profile.o_que_valoriza || "",
    o_que_nao_aceita: profile.o_que_nao_aceita || "",
    foto_url:
      profile.foto_url ||
      profile.foto_principal_url ||
      profile.foto_principal ||
      profile.foto ||
      null,
    verificado: profile.verificado ?? false,
    criado_em: profile.criado_em || null,
  };
}

async function readJson(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) return null;
  return response.json();
}

async function request(path, { signal } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  const payload = await readJson(response);

  if (!response.ok) {
    const message = payload?.detail || `Não foi possível concluir o pedido (${response.status}).`;
    throw new Error(message);
  }

  return payload;
}

export async function fetchProfiles({ signal } = {}) {
  const payload = await request("/api/perfis/", { signal });
  const results = Array.isArray(payload) ? payload : payload?.results || [];
  return results.map(normalizeProfile);
}

export async function fetchProfileDetail(profileId, { signal } = {}) {
  if (!profileId || String(profileId).startsWith("demo-")) {
    throw new Error("Este é um perfil demonstrativo.");
  }

  const payload = await request(`/api/perfis/${profileId}/`, { signal });
  return normalizeProfile(payload);
}

export { API_BASE_URL, normalizeProfile };
