import { useCallback, useEffect, useState } from "react";
import { Clock3, LockKeyhole, ShieldCheck } from "lucide-react";
import AppHeader from "./components/layout/AppHeader.jsx";
import BottomNavigation from "./components/layout/BottomNavigation.jsx";
import { demoProfiles } from "./data/demoProfiles.js";
import useProfileLibrary from "./hooks/useProfileLibrary.js";
import useSession from "./hooks/useSession.js";
import DiscoverPage from "./pages/DiscoverPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import ProfileDetailPage from "./pages/ProfileDetailPage.jsx";
import SavedProfilesPage from "./pages/SavedProfilesPage.jsx";
import {
  fetchProfileDetail,
  fetchProfiles,
  toggleProfileInterest,
} from "./services/api.js";

function ReservedArea({ title, onLogin, authenticated }) {
  if (authenticated) {
    return (
      <main className="nk-reserved">
        <section className="nk-shell nk-reserved__card">
          <span className="nk-reserved__icon"><Clock3 size={25} /></span>
          <span className="nk-eyebrow nk-eyebrow--dark"><ShieldCheck size={15} /> Próxima etapa</span>
          <h1>{title}</h1>
          <p>Esta área está a ser ligada à nova interface. A sua sessão continua ativa.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="nk-reserved">
      <section className="nk-shell nk-reserved__card">
        <span className="nk-reserved__icon"><LockKeyhole size={25} /></span>
        <span className="nk-eyebrow nk-eyebrow--dark"><ShieldCheck size={15} /> Precisa de entrar</span>
        <h1>{title}</h1>
        <p>Entre na sua conta para consultar esta área.</p>
        <button type="button" className="nk-button nk-button--wine" onClick={onLogin}>Entrar</button>
      </section>
    </main>
  );
}

const reservedTitles = {
  matches: "Os seus matches",
  messages: "Mensagens",
  account: "A sua conta",
};

export default function App() {
  const [activePage, setActivePage] = useState("home");
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

  useEffect(() => {
    const controller = new AbortController();
    loadProfiles({ signal: controller.signal });
    return () => controller.abort();
  }, [loadProfiles]);

  const openLogin = (returnPage = activePage) => {
    setReturnPageAfterLogin(returnPage === "login" ? "home" : returnPage);
    setLoginError("");
    setActivePage("login");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleNavigate = (page) => {
    if (page === "security") {
      setActivePage("home");
      window.setTimeout(() => {
        document.getElementById("seguranca")?.scrollIntoView({ behavior: "smooth" });
      }, 40);
      return;
    }

    if (page === "login") {
      openLogin(activePage);
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
      setActivePage(returnPageAfterLogin || "home");
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
      if (["matches", "messages", "account"].includes(activePage)) {
        setActivePage("home");
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
    setActivePage("profile");
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

  const handleBackFromProfile = () => {
    setActivePage(previousPage || "discover");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const visiblePage = activePage === "profile" || activePage === "login"
    ? previousPage
    : activePage;

  return (
    <div className="nk-app">
      <AppHeader
        activePage={visiblePage}
        onNavigate={handleNavigate}
        savedCount={savedProfiles.length}
        session={session}
        sessionLoading={sessionLoading}
        onSignOut={handleSignOut}
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

      {reservedTitles[activePage] && (
        <ReservedArea
          title={reservedTitles[activePage]}
          authenticated={authenticated}
          onLogin={() => openLogin(activePage)}
        />
      )}

      <BottomNavigation
        activePage={visiblePage}
        onNavigate={handleNavigate}
        savedCount={savedProfiles.length}
      />
    </div>
  );
}
