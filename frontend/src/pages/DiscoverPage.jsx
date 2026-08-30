import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  LockKeyhole,
  MapPin,
  RefreshCw,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";
import ProfileCard from "../components/profiles/ProfileCard.jsx";
import ProfileFilters from "../components/profiles/ProfileFilters.jsx";
import useInterfaceLanguage from "../hooks/useInterfaceLanguage.js";
import { fetchPublicProfilePreviews } from "../services/api.js";

const translateObjective = (value, english) => {
  if (!english) return value;
  return ({
    "Relacionamento sério": "Serious relationship",
    "Conhecer com intenção": "Meet with intention",
    "Casamento no futuro": "Marriage in the future",
    "Amizade que pode evoluir": "Friendship that may grow",
  })[value] || value;
};

function GuestPreviewCard({ profile, position, onOpen, english }) {
  const isMain = position === "main";
  const Tag = isMain && profile ? "button" : "article";
  const theme = profile?.tema_perfil || "classico";
  const className = `nk-guest-preview nk-guest-preview--${position} nk-guest-preview--theme-${theme} ${profile ? "has-profile" : ""}`;

  return (
    <Tag
      className={className}
      {...(isMain && profile
        ? {
            type: "button",
            onClick: onOpen,
            "aria-label": `${english ? "Sign in to meet" : "Entrar para conhecer"} ${profile.nome_publico}`,
          }
        : { "aria-hidden": true })}
    >
      <UserRound
        className={isMain ? "nk-guest-preview__person" : undefined}
        size={isMain ? 104 : 72}
        strokeWidth={isMain ? 0.9 : 1.05}
      />

      {profile?.foto_url && (
        <img
          src={profile.foto_url}
          alt=""
          loading="lazy"
          decoding="async"
          onError={(event) => {
            event.currentTarget.hidden = true;
          }}
        />
      )}

      {isMain ? (
        <>
          <span className="nk-guest-preview__lock"><LockKeyhole size={17} /></span>
          <div className="nk-guest-preview__caption">
            <span>{translateObjective(profile?.objetivo_display, english) || (english ? "Members only" : "Apenas membros")}</span>
            <strong>
              {profile
                ? `${profile.nome_publico}${profile.idade ? `, ${profile.idade}` : ""}`
                : (english ? "Protected profile" : "Perfil protegido")}
            </strong>
            <small>
              {profile ? <MapPin size={14} /> : <ShieldCheck size={14} />}
              {profile?.cidade || (english ? "NKATA verified" : "Verificação NKATA")}
              {profile && <ShieldCheck className="nk-guest-preview__verified" size={14} />}
            </small>
          </div>
        </>
      ) : (
        <LockKeyhole size={17} />
      )}
    </Tag>
  );
}

function GuestProfilesExperience({ onRequireLogin }) {
  const language = useInterfaceLanguage();
  const english = language === "EN";
  const [profiles, setProfiles] = useState([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [rotationSeconds, setRotationSeconds] = useState(7);

  useEffect(() => {
    const controller = new AbortController();
    fetchPublicProfilePreviews({ signal: controller.signal })
      .then((result) => {
        setProfiles(result.profiles);
        setRotationSeconds(result.rotationSeconds);
        setActiveIndex(0);
      })
      .catch(() => {
        if (!controller.signal.aborted) setProfiles([]);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (profiles.length < 2) return undefined;
    const intervalId = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % profiles.length);
    }, rotationSeconds * 1000);
    return () => window.clearInterval(intervalId);
  }, [profiles.length, rotationSeconds]);

  const mainProfile = profiles[activeIndex] || null;
  const leftProfile = profiles.length > 1
    ? profiles[(activeIndex + 1) % profiles.length]
    : null;
  const rightProfile = profiles.length > 2
    ? profiles[(activeIndex + 2) % profiles.length]
    : null;

  return (
    <main className="nk-discover nk-guest-profiles">
      <CompactPageHeader title={english ? "Profiles" : "Perfis"} />

      <section className="nk-shell nk-guest-profiles__stage">
        <div className="nk-guest-profiles__copy">
          <span className="nk-guest-profiles__eyebrow">
            <ShieldCheck size={15} />
            {english ? "Members area" : "Área de membros"}
          </span>

          <h1>{english ? <>Real profiles.<br />Private access.</> : <>Perfis reais.<br />Acesso reservado.</>}</h1>
          <p>{english ? "Sign in to meet verified NKATA members." : "Entre para conhecer membros aprovados do NKATA."}</p>

          <div className="nk-guest-profiles__actions">
            <button type="button" onClick={onRequireLogin}>
              {english ? "Sign in to view profiles" : "Entrar para ver perfis"}
              <ArrowRight size={18} />
            </button>
            <a href="/pedir-acesso/">{english ? "Request access" : "Pedir acesso"}</a>
          </div>

          <span className="nk-guest-profiles__privacy">
            <LockKeyhole size={15} />
            {english ? "Only profiles that opted in appear here" : "Apenas perfis que autorizaram aparecem aqui"}
          </span>
        </div>

        <div className="nk-guest-profiles__visual">
          <div className="nk-guest-profiles__halo" />

          <GuestPreviewCard profile={leftProfile} position="left" english={english} />
          <GuestPreviewCard profile={rightProfile} position="right" english={english} />
          <GuestPreviewCard
            key={mainProfile?.id || "protected"}
            profile={mainProfile}
            position="main"
            onOpen={onRequireLogin}
            english={english}
          />
        </div>
      </section>
    </main>
  );
}

export default function DiscoverPage({
  authenticated,
  profiles,
  loading,
  loadError,
  onReload,
  onOpenProfile,
  isSaved,
  onToggleSaved,
  onRequireLogin,
}) {
  const language = useInterfaceLanguage();
  const english = language === "EN";
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

  if (!authenticated) {
    return <GuestProfilesExperience onRequireLogin={onRequireLogin} />;
  }

  return (
    <main className="nk-discover">
      <CompactPageHeader title={english ? "Profiles" : "Perfis"} />

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
              <strong>{english ? "Unable to refresh profiles" : "Não foi possível atualizar os perfis"}</strong>
              <span>{english ? "Please try again." : "Tente novamente."}</span>
            </div>
          </div>
        )}

        <div className="nk-results-heading">
          <strong>{filteredProfiles.length} {english ? (filteredProfiles.length === 1 ? "profile" : "profiles") : (filteredProfiles.length === 1 ? "perfil" : "perfis")}</strong>
          <button type="button" onClick={onReload} disabled={loading} aria-label={english ? "Refresh profiles" : "Atualizar perfis"}>
            <RefreshCw size={16} className={loading ? "is-spinning" : ""} />
          </button>
        </div>

        {loading ? (
          <div className="nk-profile-grid" aria-label={english ? "Loading profiles" : "A carregar perfis"}>
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
            <h2>{english ? "No profiles yet" : "Ainda não há perfis"}</h2>
            <p>{english ? "New members will appear here after approval." : "Novos membros aparecerão aqui após aprovação."}</p>
            <button type="button" onClick={onReload}>
              {english ? "Refresh profiles" : "Atualizar perfis"}
            </button>
          </div>
        ) : (
          <div className="nk-empty-state">
            <ShieldCheck size={28} />
            <h2>{english ? "No results" : "Nenhum resultado"}</h2>
            <p>
              {hasActiveFilters
                ? (english ? "Change or clear the filters." : "Altere ou limpe os filtros.")
                : (english ? "Refresh to try again." : "Atualize para tentar novamente.")}
            </p>
            <button type="button" onClick={hasActiveFilters ? clearFilters : onReload}>
              {hasActiveFilters ? (english ? "Clear filters" : "Limpar filtros") : (english ? "Refresh profiles" : "Atualizar perfis")}
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
