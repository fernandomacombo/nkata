import { useEffect } from "react";
import { Bookmark, Clock3, Trash2 } from "lucide-react";
import ProfileCard from "../components/profiles/ProfileCard.jsx";
import { fetchSavedProfiles } from "../services/api.js";

function ProfileSection({ title, description, profiles, onOpenProfile, isSaved, onToggleSaved }) {
  if (!profiles.length) return null;

  return (
    <section className="nk-library__section">
      <div className="nk-section-heading">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
      </div>

      <div className="nk-profile-grid">
        {profiles.map((profile) => (
          <ProfileCard
            key={profile.id}
            profile={profile}
            onOpen={onOpenProfile}
            saved={isSaved(profile)}
            onToggleSaved={onToggleSaved}
          />
        ))}
      </div>
    </section>
  );
}

export default function SavedProfilesPage({
  savedProfiles,
  recentProfiles,
  onOpenProfile,
  isSaved,
  onToggleSaved,
  onClearRecent,
  onDiscover,
}) {
  useEffect(() => {
    fetchSavedProfiles().catch((error) => {
      if (error.status === 401 || error.status === 403) {
        window.history.replaceState({}, "", "/entrar/");
        window.dispatchEvent(new PopStateEvent("popstate"));
      }
    });
  }, []);

  return (
    <main className="nk-library">
      <section className="nk-library__intro">
        <div className="nk-shell">
          <span className="nk-eyebrow nk-eyebrow--dark">
            <Bookmark size={15} />
            A sua seleção
          </span>
          <h1>Perfis que guardou</h1>
          <p>Regresse a estes perfis quando desejar, sem precisar de procurar novamente.</p>
        </div>
      </section>

      <div className="nk-shell nk-library__content">
        {savedProfiles.length ? (
          <ProfileSection
            title="Guardados"
            description={`${savedProfiles.length} ${savedProfiles.length === 1 ? "perfil guardado" : "perfis guardados"}`}
            profiles={savedProfiles}
            onOpenProfile={onOpenProfile}
            isSaved={isSaved}
            onToggleSaved={onToggleSaved}
          />
        ) : (
          <section className="nk-library__empty">
            <span><Bookmark size={27} /></span>
            <h2>Ainda não guardou nenhum perfil</h2>
            <p>Quando encontrar alguém que lhe interesse, toque no coração para guardar o perfil na sua conta.</p>
            <button type="button" className="nk-button nk-button--wine" onClick={onDiscover}>
              Ver perfis
            </button>
          </section>
        )}

        {recentProfiles.length > 0 && (
          <section className="nk-library__section nk-library__recent">
            <div className="nk-section-heading">
              <div>
                <span className="nk-library__recent-label"><Clock3 size={15} /> Vistos recentemente</span>
                <h2>Perfis que abriu</h2>
                <p>Uma forma rápida de continuar de onde parou.</p>
              </div>
              <button type="button" className="nk-library__clear" onClick={onClearRecent}>
                <Trash2 size={16} /> Limpar histórico
              </button>
            </div>

            <div className="nk-profile-grid">
              {recentProfiles.map((profile) => (
                <ProfileCard
                  key={profile.id}
                  profile={profile}
                  onOpen={onOpenProfile}
                  saved={isSaved(profile)}
                  onToggleSaved={onToggleSaved}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
