import { useCallback, useEffect, useState } from "react";
import AppHeader from "./components/layout/AppHeader.jsx";
import BottomNavigation from "./components/layout/BottomNavigation.jsx";
import { demoProfiles } from "./data/demoProfiles.js";
import useProfileLibrary from "./hooks/useProfileLibrary.js";
import useSession from "./hooks/useSession.js";
import AccountPage from "./pages/AccountPage.jsx";
import ConversationPage from "./pages/ConversationPage.jsx";
import DiscoverPage from "./pages/DiscoverPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import MatchesPage from "./pages/MatchesPage.jsx";
import ProfileDetailPage from "./pages/ProfileDetailPage.jsx";
import SavedProfilesPage from "./pages/SavedProfilesPage.jsx";
import useAppRoute from "./routing.js";
import {
  fetchMatchConversation,
  fetchMyAccount,
  fetchMyInterests,
  fetchMyMatches,
  fetchProfileDetail,
  fetchProfiles,
  sendMatchMessage,
  toggleProfileInterest,
  updateMyAccount,
} from "./services/api.js";

export default function App() {
  const {
    activePage,
    routeProfileId,
    routeMatchId,
    setActivePage,
  } = useAppRoute();

  const [previousPage, setPreviousPage] = useState("discover");
  const [returnPageAfterLogin, setReturnPageAfterLogin] = useState("home");
  const [profiles, setProfiles] = useState(demoProfiles);
  const [loading, setLoading] = useState(true);
  const [usingDemoData, setUsingDemoData] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [interestState, setInterestState] = useState({
    profileId: null,
    active: false,
    loading: false,
    message: "",
  });
  const [matches, setMatches] = useState([]);
  const [matchesLoading, setMatchesLoading] = useState(false);
  const [matchesError, setMatchesError] = useState("");
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [conversationMessages, setConversationMessages] = useState([]);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [conversationError, setConversationError] = useState("");
  const [messageSending, setMessageSending] = useState(false);
  const [account, setAccount] = useState(null);
  const [accountInterests, setAccountInterests] = useState([]);
  const [accountLoading, setAccountLoading] = useState(false);
  const [accountSaving, setAccountSaving] = useState(false);
  const [accountError, setAccountError] = useState("");
  const [accountSuccess, setAccountSuccess] = useState("");

  const {
    savedProfiles,
    recentProfiles,
    isSaved,
    toggleSaved,
    addRecent,
    clearRecent,
  } = useProfileLibrary();

  const {
    session,
    loading: sessionLoading,
    authenticated,
    signIn,
    signOut,
    refreshSession,
  } = useSession();

  const loadProfiles = useCallback(async ({ signal } = {}) => {
    setLoading(true);
    setLoadError("");

    try {
      const apiProfiles = await fetchProfiles({ signal });
      if (apiProfiles.length) {
        setProfiles(apiProfiles);
        setUsingDemoData(false);
      } else {
        setProfiles(demoProfiles);
        setUsingDemoData(true);
      }
    } catch (error) {
      if (error.name !== "AbortError") {
        setProfiles(demoProfiles);
        setUsingDemoData(true);
        setLoadError(error.message || "Não foi possível atualizar os perfis.");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  const loadMatches = useCallback(async ({ signal } = {}) => {
    if (!authenticated) return;

    setMatchesLoading(true);
    setMatchesError("");

    try {
      const results = await fetchMyMatches({ signal });
      setMatches(results);
    } catch (error) {
      if (error.name !== "AbortError") {
        setMatchesError(error.message || "Não foi possível atualizar os matches.");
      }
    } finally {
      if (!signal?.aborted) setMatchesLoading(false);
    }
  }, [authenticated]);

  const loadAccount = useCallback(async ({ signal } = {}) => {
    if (!authenticated) return;

    setAccountLoading(true);
    setAccountError("");

    try {
      const [accountData, interestsData] = await Promise.all([
        fetchMyAccount({ signal }),
        fetchMyInterests({ signal }),
      ]);
      setAccount(accountData);
      setAccountInterests(interestsData);
    } catch (error) {
      if (error.name !== "AbortError") {
        setAccountError(error.message || "Não foi possível atualizar a sua conta.");
      }
    } finally {
      if (!signal?.aborted) setAccountLoading(false);
    }
  }, [authenticated]);

  useEffect(() => {
    const controller = new AbortController();
    loadProfiles({ signal: controller.signal });
    return () => controller.abort();
  }, [loadProfiles]);

  useEffect(() => {
    if (!["matches", "conversation"].includes(activePage) || !authenticated) {
      return undefined;
    }

    const controller = new AbortController();
    loadMatches({ signal: controller.signal });
    return () => controller.abort();
  }, [activePage, authenticated, loadMatches]);

  useEffect(() => {
    if (activePage !== "account" || !authenticated) return undefined;

    const controller = new AbortController();
    loadAccount({ signal: controller.signal });
    return () => controller.abort();
  }, [activePage, authenticated, loadAccount]);

  useEffect(() => {
    if (sessionLoading) return;

    if (["matches", "conversation", "account"].includes(activePage) && !authenticated) {
      const returnPage = activePage === "conversation" ? "matches" : activePage;
      setReturnPageAfterLogin(returnPage);
      setLoginError("");
      setActivePage("login", { replace: true });
    }
  }, [activePage, authenticated, sessionLoading, setActivePage]);

  useEffect(() => {
    if (activePage !== "profile" || !routeProfileId) return undefined;
    if (String(selectedProfile?.id) === String(routeProfileId)) return undefined;

    const localProfile = profiles.find(
      (profile) => String(profile.id) === String(routeProfileId),
    );

    if (localProfile) {
      setSelectedProfile(localProfile);
      setInterestState({
        profileId: localProfile.id,
        active: Boolean(localProfile.interesse_ativo),
        loading: false,
        message: "",
      });
      addRecent(localProfile);
    }

    if (String(routeProfileId).startsWith("demo-")) return undefined;

    const controller = new AbortController();
    setProfileLoading(true);
    setProfileError("");

    fetchProfileDetail(routeProfileId, { signal: controller.signal })
      .then((detail) => {
        setSelectedProfile(detail);
        setInterestState({
          profileId: detail.id,
          active: Boolean(detail.interesse_ativo),
          loading: false,
          message: "",
        });
        addRecent(detail);
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          setProfileError(error.message || "Não foi possível abrir este perfil.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setProfileLoading(false);
      });

    return () => controller.abort();
  }, [
    activePage,
    addRecent,
    profiles,
    routeProfileId,
    selectedProfile?.id,
  ]);

  useEffect(() => {
    if (
      activePage !== "conversation"
      || !authenticated
      || !routeMatchId
      || String(selectedMatch?.id) === String(routeMatchId)
    ) {
      return undefined;
    }

    const controller = new AbortController();
    setConversationMessages([]);
    setConversationError("");
    setConversationLoading(true);

    fetchMatchConversation(routeMatchId, { signal: controller.signal })
      .then((result) => {
        setSelectedMatch(result.match);
        setConversationMessages(result.messages);
        setMatches((current) => current.map((item) => (
          item.id === Number(routeMatchId)
            ? { ...(result.match || item), unreadCount: 0 }
            : item
        )));
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          setConversationError(error.message || "Não foi possível abrir a conversa.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setConversationLoading(false);
      });

    return () => controller.abort();
  }, [activePage, authenticated, routeMatchId, selectedMatch?.id]);

  const openLogin = (returnPage = activePage) => {
    const safeReturnPage = returnPage === "conversation" ? "matches" : returnPage;
    setReturnPageAfterLogin(safeReturnPage === "login" ? "home" : safeReturnPage);
    setLoginError("");
    setActivePage("login");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleNavigate = (page) => {
    if (page === "security") {
      setActivePage("home");
      window.setTimeout(() => {
        document.getElementById("seguranca")?.scrollIntoView({ behavior: "smooth" });
      }, 50);
      return;
    }

    if (page === "login") {
      openLogin(activePage);
      return;
    }

    if (["matches", "account"].includes(page) && !authenticated) {
      openLogin(page);
      return;
    }

    setActivePage(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleLogin = async ({ email, password }) => {
    setLoginLoading(true);
    setLoginError("");

    try {
      await signIn({ email, password });
      setActivePage(returnPageAfterLogin || "home", { replace: true });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      setLoginError(error.message || "Não foi possível entrar.");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut();
    } finally {
      setInterestState({ profileId: null, active: false, loading: false, message: "" });
      setMatches([]);
      setSelectedMatch(null);
      setConversationMessages([]);
      setAccount(null);
      setAccountInterests([]);
      if (["matches", "conversation", "account"].includes(activePage)) {
        setActivePage("home", { replace: true });
      }
    }
  };

  const handleOpenProfile = async (profile) => {
    setPreviousPage(activePage === "profile" ? "discover" : activePage);
    setSelectedProfile(profile);
    addRecent(profile);
    setProfileError("");
    setInterestState({
      profileId: profile.id,
      active: Boolean(profile.interesse_ativo),
      loading: false,
      message: "",
    });
    setActivePage("profile", { profileId: profile.id });
    window.scrollTo({ top: 0, behavior: "smooth" });

    if (!profile?.id || String(profile.id).startsWith("demo-")) return;

    setProfileLoading(true);
    try {
      const detail = await fetchProfileDetail(profile.id);
      setSelectedProfile((current) => ({ ...current, ...detail }));
      setInterestState((current) => ({
        ...current,
        profileId: detail.id,
        active: Boolean(detail.interesse_ativo),
      }));
      addRecent({ ...profile, ...detail });
    } catch (error) {
      setProfileError(error.message || "Alguns dados não foram carregados.");
    } finally {
      setProfileLoading(false);
    }
  };

  const handleToggleInterest = async (profile) => {
    if (!authenticated) {
      openLogin("profile");
      return;
    }

    setInterestState((current) => ({
      ...current,
      profileId: profile.id,
      loading: true,
      message: "",
    }));

    try {
      const result = await toggleProfileInterest(profile.id);
      setInterestState({
        profileId: profile.id,
        active: Boolean(result.active),
        loading: false,
        message: result.message || "",
      });
      setSelectedProfile((current) => ({
        ...current,
        interesse_ativo: Boolean(result.active),
      }));

      if (result.active) {
        setAccountInterests((current) => {
          const exists = current.some((item) => item.id === profile.id);
          return exists ? current : [profile, ...current];
        });
      } else {
        setAccountInterests((current) => current.filter((item) => item.id !== profile.id));
      }

      if (result.match) loadMatches();
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        setInterestState((current) => ({ ...current, loading: false }));
        openLogin("profile");
        return;
      }

      setInterestState((current) => ({
        ...current,
        loading: false,
        message: error.message || "Não foi possível guardar o interesse.",
      }));
    }
  };

  const handleOpenConversation = async (match) => {
    setSelectedMatch(match);
    setConversationMessages([]);
    setConversationError("");
    setConversationLoading(true);
    setActivePage("conversation", { matchId: match.id });
    window.scrollTo({ top: 0, behavior: "smooth" });

    try {
      const result = await fetchMatchConversation(match.id);
      setSelectedMatch(result.match || match);
      setConversationMessages(result.messages);
      setMatches((current) => current.map((item) => (
        item.id === match.id
          ? { ...(result.match || item), unreadCount: 0 }
          : item
      )));
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        openLogin("matches");
        return;
      }
      setConversationError(error.message || "Não foi possível abrir a conversa.");
    } finally {
      setConversationLoading(false);
    }
  };

  const handleSendMessage = async (text) => {
    if (!selectedMatch || !text.trim()) return false;

    setMessageSending(true);
    setConversationError("");

    try {
      const message = await sendMatchMessage(selectedMatch.id, text.trim());
      setConversationMessages((current) => [...current, message]);
      setMatches((current) => current.map((item) => (
        item.id === selectedMatch.id
          ? {
              ...item,
              lastMessage: message,
              unreadCount: 0,
              updatedAt: message.createdAt,
            }
          : item
      )));
      return true;
    } catch (error) {
      setConversationError(error.message || "Não foi possível enviar a mensagem.");
      return false;
    } finally {
      setMessageSending(false);
    }
  };

  const handleSaveAccount = async (values) => {
    setAccountSaving(true);
    setAccountError("");
    setAccountSuccess("");

    try {
      const updated = await updateMyAccount(values);
      setAccount(updated);
      setAccountSuccess("Alterações guardadas.");
      await refreshSession();
      loadProfiles();
      window.setTimeout(() => setAccountSuccess(""), 2600);
      return true;
    } catch (error) {
      setAccountError(error.message || "Não foi possível guardar as alterações.");
      return false;
    } finally {
      setAccountSaving(false);
    }
  };

  const handleToggleVisibility = async (visible) => {
    setAccountSaving(true);
    setAccountError("");
    setAccountSuccess("");

    try {
      const updated = await updateMyAccount({ visivel: visible });
      setAccount(updated);
      setAccountSuccess(
        visible ? "O seu perfil voltou a ficar visível." : "O seu perfil está oculto.",
      );
      await refreshSession();
      loadProfiles();
      window.setTimeout(() => setAccountSuccess(""), 2600);
    } catch (error) {
      setAccountError(error.message || "Não foi possível alterar a visibilidade.");
    } finally {
      setAccountSaving(false);
    }
  };

  const handleBackFromProfile = () => {
    const destination = previousPage === "profile" ? "discover" : previousPage;
    setActivePage(destination || "discover");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleBackFromConversation = () => {
    setActivePage("matches");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const visiblePage = activePage === "profile" || activePage === "login"
    ? previousPage
    : activePage === "conversation"
      ? "matches"
      : activePage;

  const totalUnread = matches.reduce((total, match) => total + match.unreadCount, 0);

  return (
    <div className="nk-app">
      <AppHeader
        activePage={visiblePage}
        onNavigate={handleNavigate}
        savedCount={savedProfiles.length}
        unreadMatches={totalUnread}
        session={session}
        sessionLoading={sessionLoading}
        onSignOut={handleSignOut}
        heroMode={activePage === "home"}
      />

      {activePage === "home" && (
        <HomePage
          profiles={profiles}
          onNavigate={handleNavigate}
          onOpenProfile={handleOpenProfile}
          isSaved={isSaved}
          onToggleSaved={toggleSaved}
        />
      )}

      {activePage === "discover" && (
        <DiscoverPage
          profiles={profiles}
          loading={loading}
          usingDemoData={usingDemoData}
          loadError={loadError}
          onReload={() => loadProfiles()}
          onOpenProfile={handleOpenProfile}
          isSaved={isSaved}
          onToggleSaved={toggleSaved}
        />
      )}

      {activePage === "saved" && (
        <SavedProfilesPage
          savedProfiles={savedProfiles}
          recentProfiles={recentProfiles}
          onOpenProfile={handleOpenProfile}
          isSaved={isSaved}
          onToggleSaved={toggleSaved}
          onClearRecent={clearRecent}
          onDiscover={() => handleNavigate("discover")}
        />
      )}

      {activePage === "login" && (
        <LoginPage
          onBack={() => setActivePage(returnPageAfterLogin || "home")}
          onSubmit={handleLogin}
          loading={loginLoading}
          error={loginError}
        />
      )}

      {activePage === "profile" && (
        <ProfileDetailPage
          profile={selectedProfile}
          loading={profileLoading}
          error={profileError}
          saved={selectedProfile ? isSaved(selectedProfile) : false}
          authenticated={authenticated}
          interestActive={
            interestState.profileId === selectedProfile?.id
              ? interestState.active
              : Boolean(selectedProfile?.interesse_ativo)
          }
          interestLoading={interestState.loading}
          interestMessage={interestState.message}
          onToggleSaved={toggleSaved}
          onToggleInterest={handleToggleInterest}
          onRequireLogin={() => openLogin("profile")}
          onBack={handleBackFromProfile}
        />
      )}

      {activePage === "matches" && authenticated && (
        <MatchesPage
          matches={matches}
          loading={matchesLoading}
          error={matchesError}
          onReload={() => loadMatches()}
          onOpenConversation={handleOpenConversation}
          onDiscover={() => handleNavigate("discover")}
        />
      )}

      {activePage === "conversation" && authenticated && (
        <ConversationPage
          match={selectedMatch}
          messages={conversationMessages}
          loading={conversationLoading}
          sending={messageSending}
          error={conversationError}
          onBack={handleBackFromConversation}
          onSend={handleSendMessage}
        />
      )}

      {activePage === "account" && authenticated && (
        <AccountPage
          account={account}
          interests={accountInterests}
          loading={accountLoading}
          saving={accountSaving}
          error={accountError}
          success={accountSuccess}
          onReload={() => loadAccount()}
          onSave={handleSaveAccount}
          onToggleVisibility={handleToggleVisibility}
          onOpenProfile={handleOpenProfile}
          onSignOut={handleSignOut}
        />
      )}

      <BottomNavigation
        activePage={visiblePage}
        onNavigate={handleNavigate}
        savedCount={savedProfiles.length}
        unreadMatches={totalUnread}
      />
    </div>
  );
}
