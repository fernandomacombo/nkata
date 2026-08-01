const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function normalizeProfile(profile) {
  return {
    id: profile.id,
    nome_publico: profile.nome_publico || profile.nome || "Perfil NKATA",
    idade: profile.idade,
    cidade: profile.cidade || "Moçambique",
    objetivo: profile.objetivo,
    objetivo_display:
      profile.objetivo_display ||
      profile.objetivo_label ||
      profile.objetivo ||
      "Conhecer com intenção",
    sobre_si:
      profile.sobre_si ||
      "Perfil aprovado pela comunidade NKATA, com intenção clara e dados pessoais protegidos.",
    foto_url:
      profile.foto_url ||
      profile.foto_principal_url ||
      profile.foto_principal ||
      profile.foto ||
      null,
    verificado: profile.verificado ?? true,
  };
}

export async function fetchProfiles({ signal } = {}) {
  const response = await fetch(`${API_BASE_URL}/api/perfis/`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Não foi possível carregar os perfis (${response.status}).`);
  }

  const payload = await response.json();
  const results = Array.isArray(payload) ? payload : payload.results || [];
  return results.map(normalizeProfile);
}

export { API_BASE_URL };
