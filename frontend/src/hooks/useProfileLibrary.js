import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

  const activeUser = useRef(null);
  const savedRequest = useRef(null);
  const loadSaved = useCallback(async () => {
    const userId = activeUser.current;
    if (!userId) return false;
    savedRequest.current?.abort();
    const controller = new AbortController();
    savedRequest.current = controller;
    try {
      const profiles = await fetchSavedProfiles({ signal: controller.signal });
      if (controller.signal.aborted || activeUser.current !== userId) return false;
      setSavedProfiles(profiles);
      return true;
    } catch (error) {
      if (controller.signal.aborted || activeUser.current !== userId) return false;
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
      const userId = session.authenticated && !session.user?.is_staff ? session.user?.id || null : null;
      savedRequest.current?.abort();
      if (activeUser.current !== userId) {
        activeUser.current = userId;
        setSavedProfiles([]);
        setCurrentUserId(userId);
        setRecentProfiles(readRecent(userId));
      }

      if (userId) {
        loadSaved();
      } else {
        setSavedProfiles([]);
      }
    };

    window.addEventListener("nkata:session-changed", handleSessionChanged);

    return () => {
      savedRequest.current?.abort();
      activeUser.current = null;
      window.removeEventListener("nkata:session-changed", handleSessionChanged);
    };
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
    const userId = activeUser.current;
    if (!userId) {
      window.history.pushState({}, "", "/entrar/");
      window.dispatchEvent(new PopStateEvent("popstate"));
      return false;
    }

    try {
      const result = await toggleSavedProfile(profile.id);
      if (activeUser.current !== userId) return false;
      savedRequest.current?.abort();
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
      if (activeUser.current !== userId) return false;
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
