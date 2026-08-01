import { useState } from "react";
import { ArrowUpRight, Heart, MapPin, ShieldCheck, UserRound } from "lucide-react";

export default function ProfileCard({ profile, compact = false, onOpen }) {
  const [imageFailed, setImageFailed] = useState(false);
  const hasImage = Boolean(profile.foto_url) && !imageFailed;

  return (
    <article className={`nk-profile-card ${compact ? "nk-profile-card--compact" : ""}`}>
      <div className="nk-profile-card__media">
        {hasImage ? (
          <img
            src={profile.foto_url}
            alt={`Foto de ${profile.nome_publico}`}
            loading="lazy"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="nk-profile-card__fallback" aria-label="Foto protegida">
            <UserRound size={46} strokeWidth={1.25} />
            <span>Foto protegida</span>
          </div>
        )}

        <div className="nk-profile-card__shade" />

        <div className="nk-profile-card__verified">
          <ShieldCheck size={14} />
          {profile.verificado ? "Verificado" : "Em análise"}
        </div>

        <button type="button" className="nk-profile-card__save" aria-label="Guardar perfil">
          <Heart size={19} />
        </button>

        <div className="nk-profile-card__identity">
          <h3>
            {profile.nome_publico}
            {profile.idade ? `, ${profile.idade}` : ""}
          </h3>
          <p>
            <MapPin size={14} />
            {profile.cidade}
          </p>
        </div>
      </div>

      <div className="nk-profile-card__content">
        <span className="nk-intention">{profile.objetivo_display}</span>
        <p className="nk-profile-card__about">{profile.sobre_si}</p>

        <div className="nk-profile-card__footer">
          <span>Dados pessoais protegidos</span>
          <button type="button" onClick={() => onOpen?.(profile)}>
            Ver perfil
            <ArrowUpRight size={16} />
          </button>
        </div>
      </div>
    </article>
  );
}
