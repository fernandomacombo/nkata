import { useCallback, useEffect, useMemo, useState } from "react";

const SAVED_KEY = "nkata_saved_profiles";
const RECENT_KEY = "nkata_recent_profiles";

function readProfiles(key) {
  try {
    const stored = window.localStorage.getItem(key);
    const parsed = stored ? JSON.parse(stored) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function profileKey(profileOrId) {
  const id = typeof profileOrId === "object" ? profileOrId?.id : profileOrId;
  return String(id ?? "");
}

export default function useProfileLibrary() {
  const [savedProfiles, setSavedProfiles] = useState(() => readProfiles(SAVED_KEY));
  const [recentProfiles, setRecentProfiles] = useState(() => readProfiles(RECENT_KEY));

  useEffect(() => {
    window.localStorage.setItem(SAVED_KEY, JSON.stringify(savedProfiles));
  }, [savedProfiles]);

  useEffect(() => {
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(recentProfiles));
  }, [recentProfiles]);

  const savedIds = useMemo(
    () => new Set(savedProfiles.map((profile) => profileKey(profile))),
    [savedProfiles],
  );

  const isSaved = useCallback(
    (profileOrId) => savedIds.has(profileKey(profileOrId)),
    [savedIds],
  );

  const toggleSaved = useCallback((profile) => {
    if (!profile?.id) return;

    setSavedProfiles((current) => {
      const key = profileKey(profile);
      const exists = current.some((item) => profileKey(item) === key);
      return exists
        ? current.filter((item) => profileKey(item) !== key)
        : [profile, ...current];
    });
  }, []);

  const addRecent = useCallback((profile) => {
    if (!profile?.id) return;

    setRecentProfiles((current) => {
      const key = profileKey(profile);
      const withoutCurrent = current.filter((item) => profileKey(item) !== key);
      return [profile, ...withoutCurrent].slice(0, 8);
    });
  }, []);

  const clearRecent = useCallback(() => setRecentProfiles([]), []);

  return {
    savedProfiles,
    recentProfiles,
    isSaved,
    toggleSaved,
    addRecent,
    clearRecent,
  };
}
