import { useMemo, useState } from "react";
import {
  ArrowLeft,
  BadgeCheck,
  Heart,
  LockKeyhole,
  MapPin,
  Share2,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import { API_BASE_URL } from "../services/api.js";

function DetailBlock({ title, children }) {
  return (
    <section className="nk-profile-detail__block">
      <span>{title}</span>
      <p>{children}</p>
    </section>
  );
}

export default function ProfileDetailPage({
  profile,
  loading,
  error,
  saved,
  onToggleSaved,
  onBack,
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const [shareStatus, setShareStatus] = useState("");

  const hasImage = Boolean(profile?.foto_url) && !imageFailed;
  const profileUrl = useMemo(() => {
    if (!profile?.id || String(profile.id).startsWith("demo-")) return null;
    return new URL(`/perfis/${profile.id}/`, API_BASE_URL).toString();
  }, [profile?.id]);

  const handleShare = async () => {
    if (!profile) return;

    const shareUrl = profileUrl || window.location.href;
    const shareData = {
      title: `${profile.nome_publico} no NKATA`,
      text: `Veja o perfil de ${profile.nome_publico} no NKATA.`,
      url: shareUrl,
    };

    try {
      if (navigator.share) {
        await navigator.share(shareData);
        setShareStatus("Partilhado");
      } else {
        await navigator.clipboard.writeText(shareUrl);
        setShareStatus("Link copiado");
      }
    } catch (shareError) {
      if (shareError.name !== "AbortError") setShareStatus("Não foi possível partilhar");
    }

    window.setTimeout(() => setShareStatus(""), 2200);
  };

  if (!profile && loading) {
    return (
      <main className="nk-profile-detail nk-profile-detail--loading">
        <div className="nk-shell nk-profile-detail__skeleton">
          <div />
          <section>
            <span />
            <span />
            <span />
          </section>
        </div>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="nk-profile-detail nk-profile-detail--empty">
        <div className="nk-shell nk-profile-detail__empty-card">
          <ShieldCheck size={30} />
          <h1>Perfil não disponível</h1>
          <p>{error || "Não foi possível abrir este perfil agora."}</p>
          <button type="button" className="nk-button nk-button--wine" onClick={onBack}>
            Voltar aos perfis
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="nk-profile-detail">
      <div className="nk-shell">
        <button type="button" className="nk-profile-detail__back" onClick={onBack}>
          <ArrowLeft size={18} />
          Voltar
        </button>

        <div className="nk-profile-detail__layout">
          <aside className="nk-profile-detail__media">
            {hasImage ? (
              <img
                src={profile.foto_url}
                alt={`Foto de ${profile.nome_publico}`}
                onError={() => setImageFailed(true)}
              />
            ) : (
              <div className="nk-profile-detail__fallback">
                <UserRound size={64} strokeWidth={1.15} />
                <span>Sem fotografia</span>
              </div>
            )}

            <div className="nk-profile-detail__media-shade" />

            <span className="nk-profile-detail__verified">
              <BadgeCheck size={16} />
              {profile.verificado ? "Perfil verificado" : "Em análise"}
            </span>

            <div className="nk-profile-detail__media-copy">
              <span>{profile.objetivo_display}</span>
              <strong>{profile.nome_publico}</strong>
              <small><MapPin size={14} /> {profile.cidade}</small>
            </div>
          </aside>

          <section className="nk-profile-detail__content">
            <div className="nk-profile-detail__heading">
              <div>
                <span className="nk-eyebrow nk-eyebrow--dark">
                  <ShieldCheck size={15} /> Perfil verificado
                </span>
                <h1>
                  {profile.nome_publico}
                  {profile.idade ? `, ${profile.idade}` : ""}
                </h1>
                <p>{profile.objetivo_display}</p>
              </div>

              <div className="nk-profile-detail__quick-actions">
                <button
                  type="button"
                  className={`nk-profile-detail__save ${saved ? "is-saved" : ""}`}
                  onClick={() => onToggleSaved?.(profile)}
                  aria-pressed={saved}
                >
                  <Heart size={19} fill={saved ? "currentColor" : "none"} />
                  {saved ? "Guardado" : "Guardar"}
                </button>
                <button type="button" className="nk-profile-detail__share" onClick={handleShare}>
                  <Share2 size={18} />
                  {shareStatus || "Partilhar"}
                </button>
              </div>
            </div>

            {error && (
              <div className="nk-profile-detail__notice">
                Alguns dados deste perfil não foram atualizados.
              </div>
            )}

            <div className="nk-profile-detail__blocks">
              <DetailBlock title="Sobre mim">
                {profile.sobre_si || "Esta pessoa ainda não acrescentou uma apresentação."}
              </DetailBlock>

              <DetailBlock title="O que valorizo">
                {profile.o_que_valoriza || "Ainda não foi preenchido."}
              </DetailBlock>

              <DetailBlock title="O que não aceito">
                {profile.o_que_nao_aceita || "Ainda não foi preenchido."}
              </DetailBlock>
            </div>

            <div className="nk-profile-detail__assurance">
              <span><LockKeyhole size={18} /></span>
              <div>
                <strong>Telefone, email e documentos não são mostrados</strong>
                <p>Os contactos só são partilhados quando existir autorização e interesse dos dois lados.</p>
              </div>
            </div>

            <div className="nk-profile-detail__actions">
              <button
                type="button"
                className="nk-button nk-button--wine"
                onClick={() => profileUrl && window.location.assign(profileUrl)}
                disabled={!profileUrl}
              >
                <Sparkles size={18} />
                {profileUrl ? "Tenho interesse" : "Disponível depois da aprovação"}
              </button>
              <button type="button" className="nk-button nk-button--quiet" onClick={onBack}>
                Ver outros perfis
              </button>
            </div>

            {loading && (
              <span className="nk-profile-detail__updating">A atualizar o perfil…</span>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
