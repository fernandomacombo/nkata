import { useCallback, useEffect, useState } from "react";
import {
  fetchMyAccountPreferences,
  updateMyAccountPreferences,
} from "../services/api.js";

export const DEFAULT_APP_PREFERENCES = {
  idioma: "PT",
  tema_perfil: "CLASSICO",
  fundo_conversa: "SERENO",
  opcoes: {},
};

const PREFERENCES_CACHE_PREFIX = "nkata:app-preferences:";

function readCachedPreferences(identity) {
  if (!identity || identity === "guest") return null;

  try {
    const cached = window.localStorage.getItem(`${PREFERENCES_CACHE_PREFIX}${identity}`);
    return cached ? normalizePreferences(JSON.parse(cached)) : null;
  } catch {
    return null;
  }
}

function cachePreferences(identity, preferences) {
  if (!identity || identity === "guest") return;

  try {
    window.localStorage.setItem(
      `${PREFERENCES_CACHE_PREFIX}${identity}`,
      JSON.stringify(normalizePreferences(preferences)),
    );
  } catch {
    // A preferência continua guardada no servidor quando o armazenamento local não está disponível.
  }
}

function normalizePreferences(payload) {
  return {
    ...DEFAULT_APP_PREFERENCES,
    ...(payload || {}),
    idioma: String(payload?.idioma || "PT").toUpperCase(),
    tema_perfil: String(payload?.tema_perfil || "CLASSICO").toUpperCase(),
    fundo_conversa: String(payload?.fundo_conversa || "SERENO").toUpperCase(),
  };
}

function applyPreferences(preferences) {
  const root = document.documentElement;
  root.lang = preferences.idioma === "EN" ? "en" : "pt";
  root.dataset.nkataLanguage = preferences.idioma;
  root.dataset.nkataTheme = preferences.tema_perfil;
  root.dataset.nkataChatBackground = preferences.fundo_conversa;

  const themeMeta = document.querySelector('meta[name="theme-color"]');
  if (themeMeta) {
    themeMeta.setAttribute(
      "content",
      preferences.tema_perfil === "NOITE"
        ? "#171313"
        : preferences.tema_perfil === "AREIA" ? "#8a3e48" : "#7d2638",
    );
  }

  window.dispatchEvent(new CustomEvent("nkata:preferences-applied", {
    detail: preferences,
  }));
}

export default function useAppPreferences({ authenticated, identity }) {
  const [preferences, setPreferences] = useState(DEFAULT_APP_PREFERENCES);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authenticated) {
      setPreferences(DEFAULT_APP_PREFERENCES);
      applyPreferences(DEFAULT_APP_PREFERENCES);
      return undefined;
    }

    const controller = new AbortController();
    const cached = readCachedPreferences(identity);

    if (cached) {
      setPreferences(cached);
      applyPreferences(cached);
    }

    setLoading(true);
    setError("");

    fetchMyAccountPreferences({ signal: controller.signal })
      .then((payload) => {
        const next = normalizePreferences(payload);
        setPreferences(next);
        applyPreferences(next);
        cachePreferences(identity, next);
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          setError(requestError.message || "Não foi possível abrir as preferências.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [authenticated, identity]);

  const savePreferences = useCallback(async (values) => {
    setSaving(true);
    setError("");
    try {
      const next = normalizePreferences(await updateMyAccountPreferences(values));
      setPreferences(next);
      applyPreferences(next);
      cachePreferences(identity, next);
      return next;
    } catch (requestError) {
      setError(requestError.message || "Não foi possível guardar as preferências.");
      throw requestError;
    } finally {
      setSaving(false);
    }
  }, [identity]);

  const previewPreferences = useCallback((values) => {
    const next = normalizePreferences({ ...preferences, ...values });
    setPreferences(next);
    applyPreferences(next);
    return next;
  }, [preferences]);

  return {
    preferences,
    loading,
    saving,
    error,
    previewPreferences,
    savePreferences,
  };
}
