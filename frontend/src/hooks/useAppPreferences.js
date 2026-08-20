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
  root.dataset.nkataChatBackground = preferences.fundo_conversa;
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
    setLoading(true);
    setError("");

    fetchMyAccountPreferences({ signal: controller.signal })
      .then((payload) => {
        const next = normalizePreferences(payload);
        setPreferences(next);
        applyPreferences(next);
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
      return next;
    } catch (requestError) {
      setError(requestError.message || "Não foi possível guardar as preferências.");
      throw requestError;
    } finally {
      setSaving(false);
    }
  }, []);

  return {
    preferences,
    loading,
    saving,
    error,
    savePreferences,
  };
}
