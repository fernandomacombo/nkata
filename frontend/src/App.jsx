import { useCallback, useEffect, useState } from "react";
import { LockKeyhole, ShieldCheck } from "lucide-react";
import AppHeader from "./components/layout/AppHeader.jsx";
import BottomNavigation from "./components/layout/BottomNavigation.jsx";
import { demoProfiles } from "./data/demoProfiles.js";
import DiscoverPage from "./pages/DiscoverPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import { fetchProfiles } from "./services/api.js";

function ReservedArea({ title }) {
  return (
    <main className="nk-reserved">
      <section className="nk-shell nk-reserved__card">
        <span className="nk-reserved__icon"><LockKeyhole size={25} /></span>
        <span className="nk-eyebrow nk-eyebrow--dark"><ShieldCheck size={15} /> Área reservada</span>
        <h1>{title}</h1>
        <p>Esta área será ligada à tua conta NKATA depois da autenticação React estar concluída.</p>
        <button type="button" className="nk-button nk-button--wine" onClick={() => window.location.assign("/entrar/")}>Entrar na conta</button>
      </section>
    </main>
  );
}

const reservedTitles = {
  matches: "Os teus matches",
  messages: "Mensagens privadas",
  account: "A tua conta NKATA",
};

export default function App() {
  const [activePage, setActivePage] = useState("home");
  const [profiles, setProfiles] = useState(demoProfiles);
  const [loading, setLoading] = useState(true);
  const [usingDemoData, setUsingDemoData] = useState(true);

  const loadProfiles = useCallback(async () => {
    const controller = new AbortController();
    setLoading(true);

    try {
      const apiProfiles = await fetchProfiles({ signal: controller.signal });
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
      }
    } finally {
      setLoading(false);
    }

    return () => controller.abort();
  }, []);

  useEffect(() => {
    loadProfiles();
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

  return (
    <div className="nk-app">
      <AppHeader activePage={activePage} onNavigate={handleNavigate} />

      {activePage === "home" && (
        <HomePage profiles={profiles} onNavigate={handleNavigate} />
      )}

      {activePage === "discover" && (
        <DiscoverPage
          profiles={profiles}
          loading={loading}
          usingDemoData={usingDemoData}
          onReload={loadProfiles}
        />
      )}

      {reservedTitles[activePage] && (
        <ReservedArea title={reservedTitles[activePage]} />
      )}

      <BottomNavigation activePage={activePage} onNavigate={handleNavigate} />
    </div>
  );
}
