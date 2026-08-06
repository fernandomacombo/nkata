import { useMemo, useState } from "react";
import { LockKeyhole, RefreshCw, ShieldCheck } from "lucide-react";
import ProfileCard from "../components/profiles/ProfileCard.jsx";
import ProfileFilters from "../components/profiles/ProfileFilters.jsx";

export default function DiscoverPage({
  profiles,
  loading,
  usingDemoData,
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
      <section className="nk-discover__intro">
        <div className="nk-shell nk-discover__intro-grid">
          <div>
            <span className="nk-eyebrow nk-eyebrow--dark">
              <ShieldCheck size={15} />
              Perfis verificados
            </span>
            <h1>Encontre alguém que procura o mesmo que você.</h1>
            <p>
              Veja a cidade, a idade e o que cada pessoa procura antes de abrir o perfil.
            </p>
          </div>

          <aside className="nk-discover__privacy">
            <LockKeyhole size={21} />
            <div>
              <strong>Os seus contactos não aparecem aqui</strong>
              <span>Telefone, email e documentos ficam fora da área pública.</span>
            </div>
          </aside>
        </div>
      </section>

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
              <span>Nenhum perfil fictício será mostrado. Tente atualizar novamente.</span>
            </div>
          </div>
        )}

        <div className="nk-results-heading">
          <div>
            <strong>{filteredProfiles.length} {filteredProfiles.length === 1 ? "perfil" : "perfis"}</strong>
            <span>
              {usingDemoData && hasProfiles
                ? "Ambiente de demonstração"
                : hasProfiles
                  ? "Perfis aprovados e disponíveis"
                  : "Aguardando perfis aprovados"}
            </span>
          </div>
          <button type="button" onClick={onReload} disabled={loading}>
            <RefreshCw size={16} className={loading ? "is-spinning" : ""} />
            Atualizar
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
            <h2>A comunidade está a ser preparada</h2>
            <p>
              Ainda não existem perfis aprovados e visíveis. O NKATA não apresenta pessoas
              fictícias como se fossem membros reais.
            </p>
            <button type="button" onClick={() => window.location.assign("/pedir-acesso/")}>
              Pedir acesso
            </button>
          </div>
        ) : (
          <div className="nk-empty-state">
            <ShieldCheck size={28} />
            <h2>Nenhum perfil corresponde aos filtros</h2>
            <p>
              {hasActiveFilters
                ? "Tente outra cidade, faixa etária ou uma pesquisa mais simples."
                : "Atualize a página para consultar novamente os perfis disponíveis."}
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
