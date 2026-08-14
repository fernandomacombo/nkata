import { useState } from "react";
import { Heart, MapPin, ShieldCheck, UserRound } from "lucide-react";

export default function ProfileCard({
  profile,
  compact = false,
  onOpen,
  saved = false,
  onToggleSaved,
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const hasImage = Boolean(profile.foto_url) && !imageFailed;
  const displayName = `${profile.nome_publico}${profile.idade ? `, ${profile.idade}` : ""}`;

  const handleSave = (event) => {
    event.stopPropagation();
    onToggleSaved?.(profile);
  };

  return (
    <article className={`nk-profile-card ${compact ? "nk-profile-card--compact" : ""}`}>
      <button
        type="button"
        className="nk-profile-card__open"
        onClick={() => onOpen?.(profile)}
        aria-label={`Abrir perfil de ${displayName}`}
      >
        <div className="nk-profile-card__media">
          {hasImage ? (
            <img
              src={profile.foto_url}
              alt={`Foto de ${profile.nome_publico}`}
              loading="lazy"
              onError={() => setImageFailed(true)}
            />
          ) : (
            <div className="nk-profile-card__fallback" aria-label="Foto não disponível">
              <UserRound size={52} strokeWidth={1.2} />
              <span>Fotografia indisponível</span>
            </div>
          )}

          <div className="nk-profile-card__shade" aria-hidden="true" />

          <div className="nk-profile-card__story">
            <div className="nk-profile-card__identity">
              <h3>
                <span>{displayName}</span>
                {profile.verificado && (
                  <span
                    className="nk-profile-card__verified"
                    aria-label="Perfil verificado"
                    title="Perfil verificado"
                  >
                    <ShieldCheck size={16} strokeWidth={2.1} />
                  </span>
                )}
              </h3>
              <p>
                <MapPin size={15} strokeWidth={1.9} />
                <span>{profile.cidade || "Moçambique"}</span>
              </p>
            </div>

            <span className="nk-profile-card__intention">
              {profile.objetivo_display || "Conhecer com intenção"}
            </span>
          </div>
        </div>
      </button>

      <button
        type="button"
        className={`nk-profile-card__save ${saved ? "is-saved" : ""}`}
        aria-label={saved ? "Remover dos guardados" : "Guardar perfil"}
        aria-pressed={saved}
        onClick={handleSave}
      >
        <Heart size={20} strokeWidth={1.9} fill={saved ? "currentColor" : "none"} />
      </button>
    </article>
  );
}
