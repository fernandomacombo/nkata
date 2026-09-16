import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchSavedProfiles, toggleSavedProfile } from "../services/api.js";

const LEGACY_SAVED_KEY = "nkata_saved_profiles";
const RECENT_PREFIX = "nkata_recent_profiles_user_";

function profileKey(profileOrId) {
  const id = typeof profileOrId === "object" ? profileOrId?.id : profileOrId;
  return String(id ?? "");
}

function readRecent(userId) {
  if (!userId) return [];
  try {
    const stored = window.localStorage.getItem(`${RECENT_PREFIX}${userId}`);
    const parsed = stored ? JSON.parse(stored) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export default function useProfileLibrary() {
  const [savedProfiles, setSavedProfiles] = useState([]);
  const [recentProfiles, setRecentProfiles] = useState([]);
  const [currentUserId, setCurrentUserId] = useState(null);

  const loadSaved = useCallback(async () => {
    try {
      const profiles = await fetchSavedProfiles();
      setSavedProfiles(profiles);
      return true;
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        setSavedProfiles([]);
        setRecentProfiles([]);
        setCurrentUserId(null);
        if (window.location.pathname === "/guardados/") {
          window.history.replaceState({}, "", "/entrar/");
          window.dispatchEvent(new PopStateEvent("popstate"));
        }
        return false;
      }
      return false;
    }
  }, []);

  useEffect(() => {
    // Remove a lista antiga que era partilhada por todas as contas do navegador.
    window.localStorage.removeItem(LEGACY_SAVED_KEY);

    const handleSessionChanged = (event) => {
      const session = event.detail || {};
      const userId = session?.user?.id || null;
      setCurrentUserId(userId);
      setRecentProfiles(readRecent(userId));

      if (session?.authenticated) {
        loadSaved();
      } else {
        setSavedProfiles([]);
      }
    };

    window.addEventListener("nkata:session-changed", handleSessionChanged);
    loadSaved();

    return () => window.removeEventListener("nkata:session-changed", handleSessionChanged);
  }, [loadSaved]);

  useEffect(() => {
    if (!currentUserId) return;
    window.localStorage.setItem(
      `${RECENT_PREFIX}${currentUserId}`,
      JSON.stringify(recentProfiles),
    );
  }, [currentUserId, recentProfiles]);

  const savedIds = useMemo(
    () => new Set(savedProfiles.map((profile) => profileKey(profile))),
    [savedProfiles],
  );

  const isSaved = useCallback(
    (profileOrId) => savedIds.has(profileKey(profileOrId)),
    [savedIds],
  );

  const toggleSaved = useCallback(async (profile) => {
    if (!profile?.id) return false;

    try {
      const result = await toggleSavedProfile(profile.id);
      setSavedProfiles((current) => {
        const key = profileKey(profile);
        const exists = current.some((item) => profileKey(item) === key);

        if (result.active && !exists) return [profile, ...current];
        if (!result.active && exists) {
          return current.filter((item) => profileKey(item) !== key);
        }
        return current;
      });
      return Boolean(result.active);
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        window.history.pushState({}, "", "/entrar/");
        window.dispatchEvent(new PopStateEvent("popstate"));
      }
      return false;
    }
  }, []);

  const addRecent = useCallback((profile) => {
    if (!profile?.id || !currentUserId) return;

    setRecentProfiles((current) => {
      const key = profileKey(profile);
      const withoutCurrent = current.filter((item) => profileKey(item) !== key);
      return [profile, ...withoutCurrent].slice(0, 8);
    });
  }, [currentUserId]);

  const clearRecent = useCallback(() => setRecentProfiles([]), []);

  return {
    savedProfiles,
    recentProfiles,
    isSaved,
    toggleSaved,
    addRecent,
    clearRecent,
    reloadSaved: loadSaved,
  };
}
