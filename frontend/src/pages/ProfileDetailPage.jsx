import { useMemo, useState } from "react";
import {
  ArrowLeft,
  BadgeCheck,
  Heart,
  LockKeyhole,
  MapPin,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";

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
  onBack,
}) {
  const [saved, setSaved] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  const hasImage = Boolean(profile?.foto_url) && !imageFailed;
  const profileUrl = useMemo(() => {
    if (!profile?.id || String(profile.id).startsWith("demo-")) return null;
    return `/perfis/${profile.id}/`;
  }, [profile?.id]);

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
          <h1>Perfil indisponível</h1>
          <p>{error || "Não foi possível apresentar este perfil neste momento."}</p>
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
                <span>Fotografia protegida</span>
              </div>
            )}

            <div className="nk-profile-detail__media-shade" />

            <span className="nk-profile-detail__verified">
              <BadgeCheck size={16} />
              {profile.verificado ? "Perfil aprovado" : "Perfil em análise"}
            </span>

            <div className="nk-profile-detail__media-copy">
              <span>Comunidade privada</span>
              <strong>{profile.nome_publico}</strong>
              <small><MapPin size={14} /> {profile.cidade}</small>
            </div>
          </aside>

          <section className="nk-profile-detail__content">
            <div className="nk-profile-detail__heading">
              <div>
                <span className="nk-eyebrow nk-eyebrow--dark">
                  <ShieldCheck size={15} /> Perfil protegido
                </span>
                <h1>
                  {profile.nome_publico}
                  {profile.idade ? `, ${profile.idade}` : ""}
                </h1>
                <p>{profile.objetivo_display}</p>
              </div>

              <button
                type="button"
                className={`nk-profile-detail__save ${saved ? "is-saved" : ""}`}
                onClick={() => setSaved((current) => !current)}
                aria-pressed={saved}
              >
                <Heart size={19} fill={saved ? "currentColor" : "none"} />
                {saved ? "Guardado" : "Guardar"}
              </button>
            </div>

            {error && (
              <div className="nk-profile-detail__notice">
                A informação principal está disponível, mas alguns detalhes não foram atualizados.
              </div>
            )}

            <div className="nk-profile-detail__blocks">
              <DetailBlock title="Sobre mim">
                {profile.sobre_si || "Este perfil prefere apresentar-se durante uma conversa segura."}
              </DetailBlock>

              <DetailBlock title="O que valorizo">
                {profile.o_que_valoriza || "Respeito, clareza e intenção são prioridades nesta comunidade."}
              </DetailBlock>

              <DetailBlock title="O que não aceito">
                {profile.o_que_nao_aceita || "Limites pessoais são partilhados apenas no contexto apropriado."}
              </DetailBlock>
            </div>

            <div className="nk-profile-detail__assurance">
              <span><LockKeyhole size={18} /></span>
              <div>
                <strong>Contacto e documentos permanecem privados</strong>
                <p>O NKATA mostra apenas informação aprovada para descoberta. A aproximação acontece de forma controlada.</p>
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
                {profileUrl ? "Demonstrar interesse" : "Interação disponível após aprovação"}
              </button>
              <button type="button" className="nk-button nk-button--quiet" onClick={onBack}>
                Continuar a descobrir
              </button>
            </div>

            {loading && (
              <span className="nk-profile-detail__updating">A atualizar detalhes do perfil…</span>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
