import { useMemo, useState } from "react";
import { LockKeyhole, RefreshCw, ShieldCheck } from "lucide-react";
import ProfileCard from "../components/profiles/ProfileCard.jsx";
import ProfileFilters from "../components/profiles/ProfileFilters.jsx";

export default function DiscoverPage({ profiles, loading, usingDemoData, onReload }) {
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");

  const filteredProfiles = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return profiles.filter((profile) => {
      const matchesCity = !city || profile.cidade === city;
      const searchableText = [
        profile.nome_publico,
        profile.cidade,
        profile.objetivo_display,
        profile.sobre_si,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return matchesCity && (!normalizedQuery || searchableText.includes(normalizedQuery));
    });
  }, [profiles, query, city]);

  return (
    <main className="nk-discover">
      <section className="nk-discover__intro">
        <div className="nk-shell nk-discover__intro-grid">
          <div>
            <span className="nk-eyebrow nk-eyebrow--dark">
              <ShieldCheck size={15} />
              Descoberta protegida
            </span>
            <h1>Conheça com calma. Escolha com clareza.</h1>
            <p>
              Perfis organizados para ajudar-te a perceber intenção, contexto e compatibilidade sem exposição desnecessária.
            </p>
          </div>

          <aside className="nk-discover__privacy">
            <LockKeyhole size={21} />
            <div>
              <strong>A tua navegação é privada</strong>
              <span>Os teus dados de contacto não são mostrados nesta área.</span>
            </div>
          </aside>
        </div>
      </section>

      <section className="nk-shell nk-discover__content">
        <ProfileFilters
          query={query}
          city={city}
          onQueryChange={setQuery}
          onCityChange={setCity}
        />

        <div className="nk-results-heading">
          <div>
            <strong>{filteredProfiles.length} perfis</strong>
            <span>{usingDemoData ? "Pré-visualização da interface" : "Atualizados a partir do NKATA"}</span>
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
              <ProfileCard key={profile.id} profile={profile} />
            ))}
          </div>
        ) : (
          <div className="nk-empty-state">
            <ShieldCheck size={28} />
            <h2>Nenhum perfil encontrado</h2>
            <p>Altera a cidade ou simplifica a pesquisa para ver outras opções.</p>
            <button type="button" onClick={() => { setQuery(""); setCity(""); }}>
              Limpar filtros
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
