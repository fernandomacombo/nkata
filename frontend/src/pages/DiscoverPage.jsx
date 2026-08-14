import { useMemo, useState } from "react";
import { RefreshCw, ShieldCheck } from "lucide-react";
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";
import ProfileCard from "../components/profiles/ProfileCard.jsx";
import ProfileFilters from "../components/profiles/ProfileFilters.jsx";

export default function DiscoverPage({
  profiles,
  loading,
  loadError,
  onReload,
  onOpenProfile,
  isSaved,
  onToggleSaved,
}) {
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [objective, setObjective] = useState("");
  const [minAge, setMinAge] = useState("");
  const [maxAge, setMaxAge] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const clearFilters = () => {
    setQuery("");
    setCity("");
    setObjective("");
    setMinAge("");
    setMaxAge("");
  };

  const hasActiveFilters = Boolean(query || city || objective || minAge || maxAge);
  const hasProfiles = profiles.length > 0;

  const filteredProfiles = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const minimum = minAge ? Number(minAge) : null;
    const maximum = maxAge ? Number(maxAge) : null;

    return profiles.filter((profile) => {
      const matchesCity = !city || profile.cidade === city;
      const matchesObjective = !objective || profile.objetivo_display === objective;
      const matchesMinimum = !minimum || Number(profile.idade) >= minimum;
      const matchesMaximum = !maximum || Number(profile.idade) <= maximum;
      const searchableText = [
        profile.nome_publico,
        profile.cidade,
        profile.objetivo_display,
        profile.sobre_si,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return (
        matchesCity &&
        matchesObjective &&
        matchesMinimum &&
        matchesMaximum &&
        (!normalizedQuery || searchableText.includes(normalizedQuery))
      );
    });
  }, [profiles, query, city, objective, minAge, maxAge]);

  return (
    <main className="nk-discover">
      <CompactPageHeader title="Perfis" />

      <section className="nk-shell nk-discover__content">
        <ProfileFilters
          query={query}
          city={city}
          objective={objective}
          minAge={minAge}
          maxAge={maxAge}
          showAdvanced={showAdvanced}
          onQueryChange={setQuery}
          onCityChange={setCity}
          onObjectiveChange={setObjective}
          onMinAgeChange={setMinAge}
          onMaxAgeChange={setMaxAge}
          onToggleAdvanced={() => setShowAdvanced((current) => !current)}
          onClear={clearFilters}
        />

        {loadError && (
          <div className="nk-api-notice" role="status">
            <div>
              <strong>Não foi possível atualizar os perfis</strong>
              <span>Tente novamente.</span>
            </div>
          </div>
        )}

        <div className="nk-results-heading">
          <strong>{filteredProfiles.length} {filteredProfiles.length === 1 ? "perfil" : "perfis"}</strong>
          <button type="button" onClick={onReload} disabled={loading} aria-label="Atualizar perfis">
            <RefreshCw size={16} className={loading ? "is-spinning" : ""} />
          </button>
        </div>

        {loading ? (
          <div className="nk-profile-grid" aria-label="A carregar perfis">
            {[1, 2, 3].map((item) => (
              <div key={item} className="nk-profile-skeleton">
                <div />
                <span />
                <span />
              </div>
            ))}
          </div>
        ) : filteredProfiles.length ? (
          <div className="nk-profile-grid">
            {filteredProfiles.map((profile) => (
              <ProfileCard
                key={profile.id}
                profile={profile}
                onOpen={onOpenProfile}
                saved={isSaved(profile)}
                onToggleSaved={onToggleSaved}
              />
            ))}
          </div>
        ) : !hasProfiles ? (
          <div className="nk-empty-state nk-empty-state--community">
            <ShieldCheck size={28} />
            <h2>Ainda não há perfis</h2>
            <p>Novos membros aparecerão aqui após aprovação.</p>
            <button type="button" onClick={() => window.location.assign("/pedir-acesso/")}>
              Pedir acesso
            </button>
          </div>
        ) : (
          <div className="nk-empty-state">
            <ShieldCheck size={28} />
            <h2>Nenhum resultado</h2>
            <p>
              {hasActiveFilters
                ? "Altere ou limpe os filtros."
                : "Atualize para tentar novamente."}
            </p>
            <button type="button" onClick={hasActiveFilters ? clearFilters : onReload}>
              {hasActiveFilters ? "Limpar filtros" : "Atualizar perfis"}
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
