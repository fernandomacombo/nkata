import { useCallback, useEffect, useState } from "react";
import { fetchSession, loginUser, logoutUser } from "../services/api.js";

const EMPTY_SESSION = {
  authenticated: false,
  user: null,
  profile: null,
};

export default function useSession() {
  const [session, setSession] = useState(EMPTY_SESSION);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refreshSession = useCallback(async ({ signal } = {}) => {
    setLoading(true);
    setError("");

    try {
      const payload = await fetchSession({ signal });
      setSession(payload || EMPTY_SESSION);
      return payload;
    } catch (requestError) {
      if (requestError.name !== "AbortError") {
        setSession(EMPTY_SESSION);
        setError(requestError.message || "Não foi possível verificar a sessão.");
      }
      return EMPTY_SESSION;
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    refreshSession({ signal: controller.signal });
    return () => controller.abort();
  }, [refreshSession]);

  const signIn = useCallback(async ({ email, password }) => {
    setError("");
    const payload = await loginUser({ email, password });
    setSession(payload || EMPTY_SESSION);
    return payload;
  }, []);

  const signOut = useCallback(async () => {
    setError("");
    await logoutUser();
    setSession(EMPTY_SESSION);
  }, []);

  return {
    session,
    loading,
    error,
    authenticated: Boolean(session?.authenticated),
    signIn,
    signOut,
    refreshSession,
  };
}
