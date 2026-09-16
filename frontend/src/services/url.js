export function normalizeAppUrl(value) {
  if (!value) return null;
  const raw = String(value).trim();
  if (!raw) return null;
  if (raw.startsWith("/")) return raw;

  try {
    const parsed = new URL(raw, window.location.origin);
    const localBackendHost = ["127.0.0.1", "localhost", window.location.hostname].includes(parsed.hostname);
    const djangoDevPort = parsed.port === "8000";
    const appResource = parsed.pathname.startsWith("/api/") || parsed.pathname.startsWith("/media/");

    if (localBackendHost && djangoDevPort && appResource) {
      return `${parsed.pathname}${parsed.search}${parsed.hash}`;
    }
  } catch {
    return raw;
  }

  return raw;
}

export function normalizeProfileMedia(profile) {
  if (!profile) return profile;
  return {
    ...profile,
    foto_url: normalizeAppUrl(
      profile.foto_url
      || profile.foto_principal_url
      || profile.foto_principal
      || profile.foto
      || null,
    ),
  };
}
