import { useEffect } from "react";
import { Bookmark, Trash2 } from "lucide-react";
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";
import ProfileCard from "../components/profiles/ProfileCard.jsx";
import { fetchSavedProfiles } from "../services/api.js";
import useInterfaceLanguage from "../hooks/useInterfaceLanguage.js";

function ProfileSection({ title, description, profiles, onOpenProfile, isSaved, onToggleSaved }) {
  if (!profiles.length) return null;

  return (
    <section className="nk-library__section">
      <div className="nk-section-heading">
        <div>
          <h2>{title}</h2>
          {description && <p>{description}</p>}
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
  const english = useInterfaceLanguage() === "EN";
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
      <CompactPageHeader title={english ? "Saved" : "Guardados"} />

      <div className="nk-shell nk-library__content">
        {savedProfiles.length ? (
          <ProfileSection
            title={`${savedProfiles.length} ${english ? (savedProfiles.length === 1 ? "profile" : "profiles") : (savedProfiles.length === 1 ? "perfil" : "perfis")}`}
            profiles={savedProfiles}
            onOpenProfile={onOpenProfile}
            isSaved={isSaved}
            onToggleSaved={onToggleSaved}
          />
        ) : (
          <section className="nk-library__empty">
            <span><Bookmark size={27} /></span>
            <h2>{english ? "No saved profiles" : "Nenhum perfil guardado"}</h2>
            <p>{english ? "Save a profile to find it here." : "Guarde um perfil para encontrá-lo aqui."}</p>
            <button type="button" className="nk-button nk-button--wine" onClick={onDiscover}>
              {english ? "View profiles" : "Ver perfis"}
            </button>
          </section>
        )}

        {recentProfiles.length > 0 && (
          <section className="nk-library__section nk-library__recent">
            <div className="nk-section-heading">
              <div>
                <h2>{english ? "Recently viewed" : "Vistos recentemente"}</h2>
              </div>
              <button type="button" className="nk-library__clear" onClick={onClearRecent}>
                <Trash2 size={16} /> {english ? "Clear history" : "Limpar histórico"}
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
