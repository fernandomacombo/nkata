import { useCallback, useEffect, useRef, useState } from "react";

const STATIC_PATHS = {
  home: "/",
  discover: "/perfis/",
  moments: "/momentos/",
  saved: "/guardados/",
  matches: "/matches/",
  notifications: "/notificacoes/",
  security: "/seguranca/",
  account: "/conta/",
  admin: "/painel/",
  login: "/entrar/",
  access: "/pedir-acesso/",
};

function cleanPath(pathname = "/") {
  const path = pathname.split("?")[0].split("#")[0] || "/";
  if (path === "/") return path;
  return path.endsWith("/") ? path : `${path}/`;
}

export function pathForPage(page, { profileId, matchId } = {}) {
  if (page === "profile" && profileId) return `/perfis/${profileId}/`;
  if (page === "conversation" && matchId) return `/matches/${matchId}/conversa/`;
  return STATIC_PATHS[page] || "/";
}

export function routeFromPath(pathname) {
  const path = cleanPath(pathname);

  const profileMatch = path.match(/^\/perfis\/([^/]+)\/$/);
  if (profileMatch) {
    return {
      page: "profile",
      profileId: profileMatch[1],
      matchId: null,
      canonicalPath: path,
    };
  }

  const conversationMatch = path.match(/^\/matches\/(\d+)\/conversa\/$/);
  if (conversationMatch) {
    return {
      page: "conversation",
      profileId: null,
      matchId: Number(conversationMatch[1]),
      canonicalPath: path,
    };
  }

  const page = Object.entries(STATIC_PATHS).find(([, value]) => value === path)?.[0];
  if (page) {
    return {
      page,
      profileId: null,
      matchId: null,
      canonicalPath: path,
    };
  }

  return {
    page: "home",
    profileId: null,
    matchId: null,
    canonicalPath: "/",
  };
}

export default function useAppRoute() {
  const initialRoute = routeFromPath(window.location.pathname);
  const [route, setRoute] = useState(initialRoute);
  const lastProfileId = useRef(initialRoute.profileId);
  const lastMatchId = useRef(initialRoute.matchId);

  const setActivePage = useCallback((page, options = {}) => {
    const profileId = options.profileId
      ?? (page === "profile" ? lastProfileId.current : null);
    const matchId = options.matchId
      ?? (page === "conversation" ? lastMatchId.current : null);

    if (profileId) lastProfileId.current = profileId;
    if (matchId) lastMatchId.current = matchId;

    const nextRoute = { page, profileId, matchId };
    const path = pathForPage(page, nextRoute);
    const method = options.replace ? "replaceState" : "pushState";

    window.history[method]({}, "", path);
    setRoute({ ...nextRoute, canonicalPath: path });
  }, []);

  useEffect(() => {
    const initial = routeFromPath(window.location.pathname);
    if (initial.profileId) lastProfileId.current = initial.profileId;
    if (initial.matchId) lastMatchId.current = initial.matchId;

    if (initial.canonicalPath !== cleanPath(window.location.pathname)) {
      window.history.replaceState({}, "", initial.canonicalPath);
      setRoute(initial);
    }

    const handlePopState = () => {
      const next = routeFromPath(window.location.pathname);
      if (next.profileId) lastProfileId.current = next.profileId;
      if (next.matchId) lastMatchId.current = next.matchId;
      setRoute(next);
      window.scrollTo({ top: 0, behavior: "auto" });
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  return {
    activePage: route.page,
    routeProfileId: route.profileId,
    routeMatchId: route.matchId,
    setActivePage,
  };
}
