import { useCallback, useEffect, useState } from "react";
import { LockKeyhole, ShieldCheck } from "lucide-react";
import AppHeader from "./components/layout/AppHeader.jsx";
import BottomNavigation from "./components/layout/BottomNavigation.jsx";
import { demoProfiles } from "./data/demoProfiles.js";
import useProfileLibrary from "./hooks/useProfileLibrary.js";
import DiscoverPage from "./pages/DiscoverPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import ProfileDetailPage from "./pages/ProfileDetailPage.jsx";
import SavedProfilesPage from "./pages/SavedProfilesPage.jsx";
import { fetchProfileDetail, fetchProfiles } from "./services/api.js";

function ReservedArea({ title }) {
  return (
    <main className="nk-reserved">
      <section className="nk-shell nk-reserved__card">
        <span className="nk-reserved__icon"><LockKeyhole size={25} /></span>
        <span className="nk-eyebrow nk-eyebrow--dark"><ShieldCheck size={15} /> Precisa de entrar</span>
        <h1>{title}</h1>
        <p>Entre na sua conta para consultar esta área.</p>
        <button type="button" className="nk-button nk-button--wine" onClick={() => window.location.assign("/entrar/")}>Entrar</button>
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
  const [profiles, setProfiles] = useState(demoProfiles);
  const [loading, setLoading] = useState(true);
  const [usingDemoData, setUsingDemoData] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");
  const {
    savedProfiles,
    recentProfiles,
    isSaved,
    toggleSaved,
    addRecent,
    clearRecent,
  } = useProfileLibrary();

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

  const handleNavigate = (page) => {
    if (page === "security") {
      setActivePage("home");
      window.setTimeout(() => {
        document.getElementById("seguranca")?.scrollIntoView({ behavior: "smooth" });
      }, 40);
      return;
    }

    setActivePage(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleOpenProfile = async (profile) => {
    setPreviousPage(activePage === "profile" ? "discover" : activePage);
    setSelectedProfile(profile);
    addRecent(profile);
    setProfileError("");
    setActivePage("profile");
    window.scrollTo({ top: 0, behavior: "smooth" });

    if (!profile?.id || String(profile.id).startsWith("demo-")) return;

    setProfileLoading(true);
    try {
      const detail = await fetchProfileDetail(profile.id);
      setSelectedProfile((current) => ({ ...current, ...detail }));
      addRecent({ ...profile, ...detail });
    } catch (error) {
      setProfileError(error.message || "Alguns dados não foram carregados.");
    } finally {
      setProfileLoading(false);
    }
  };

  const handleBackFromProfile = () => {
    setActivePage(previousPage || "discover");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const visiblePage = activePage === "profile" ? previousPage : activePage;

  return (
    <div className="nk-app">
      <AppHeader
        activePage={visiblePage}
        onNavigate={handleNavigate}
        savedCount={savedProfiles.length}
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

      {activePage === "profile" && (
        <ProfileDetailPage
          profile={selectedProfile}
          loading={profileLoading}
          error={profileError}
          saved={selectedProfile ? isSaved(selectedProfile) : false}
          onToggleSaved={toggleSaved}
          onBack={handleBackFromProfile}
        />
      )}

      {reservedTitles[activePage] && (
        <ReservedArea title={reservedTitles[activePage]} />
      )}

      <BottomNavigation
        activePage={visiblePage}
        onNavigate={handleNavigate}
        savedCount={savedProfiles.length}
      />
    </div>
  );
}
