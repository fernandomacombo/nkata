import { Bookmark, Clock3, Trash2 } from "lucide-react";
import ProfileCard from "../components/profiles/ProfileCard.jsx";

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
  return (
    <main className="nk-library">
      <section className="nk-library__intro">
        <div className="nk-shell">
          <span className="nk-eyebrow nk-eyebrow--dark">
            <Bookmark size={15} />
            A tua seleção
          </span>
          <h1>Perfis que guardaste</h1>
          <p>Volta a estes perfis quando quiseres, sem precisar de procurar novamente.</p>
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
            <h2>Ainda não guardaste nenhum perfil</h2>
            <p>Quando encontrares alguém que te interesse, toca no coração para guardar o perfil aqui.</p>
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
                <h2>Perfis que abriste</h2>
                <p>Uma forma rápida de retomar a tua pesquisa.</p>
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
