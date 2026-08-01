import {
  ArrowRight,
  CheckCircle2,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  UserCheck,
} from "lucide-react";
import ProfileCard from "../components/profiles/ProfileCard.jsx";
import SecurityPanel from "../components/security/SecurityPanel.jsx";

const processSteps = [
  {
    number: "01",
    title: "Envie o pedido",
    text: "Preencha os dados e envie as fotografias pedidas.",
    icon: UserCheck,
  },
  {
    number: "02",
    title: "Aguarde a análise",
    text: "A equipa confirma os dados antes de ativar o perfil.",
    icon: ShieldCheck,
  },
  {
    number: "03",
    title: "Comece a conhecer pessoas",
    text: "Depois da aprovação, pode ver perfis e demonstrar interesse.",
    icon: Sparkles,
  },
];

const trustPoints = [
  "Perfis confirmados",
  "Contactos protegidos",
  "Entrada analisada pela equipa",
];

const platformCommitments = [
  {
    title: "Contactos protegidos",
    text: "Só são partilhados com consentimento.",
  },
  {
    title: "Perfis analisados",
    text: "Cada entrada passa por uma revisão.",
  },
  {
    title: "Denúncias acompanhadas",
    text: "A equipa pode intervir quando necessário.",
  },
  {
    title: "Feito para Moçambique",
    text: "Uma comunidade próxima da nossa realidade.",
  },
];

export default function HomePage({
  profiles,
  onNavigate,
  onOpenProfile,
  isSaved,
  onToggleSaved,
}) {
  const featured = profiles.slice(0, 3);
  const heroProfile = featured[0];

  return (
    <>
      <main>
        <section className="nk-hero nk-hero--refined">
          <div className="nk-shell nk-hero__grid">
            <div className="nk-hero__copy">
              <span className="nk-eyebrow">
                <LockKeyhole size={15} />
                Entrada mediante aprovação
              </span>

              <h1>
                Conheça alguém que procura <em>o mesmo que você.</em>
              </h1>

              <p>
                Um espaço para pessoas que querem conhecer alguém com respeito,
                clareza e intenção de construir algo sério.
              </p>

              <div className="nk-hero__actions">
                <button
                  type="button"
                  className="nk-button nk-button--wine"
                  onClick={() => onNavigate("discover")}
                >
                  Ver perfis
                  <ArrowRight size={18} />
                </button>
                <button
                  type="button"
                  className="nk-button nk-button--quiet"
                  onClick={() => window.location.assign("/solicitar-entrada/")}
                >
                  Pedir acesso
                </button>
              </div>

              <div className="nk-hero__trust" aria-label="Compromissos do NKATA">
                {trustPoints.map((point) => (
                  <span key={point}>
                    <CheckCircle2 size={16} />
                    {point}
                  </span>
                ))}
              </div>
            </div>

            <button
              type="button"
              className="nk-hero__visual"
              aria-label={heroProfile ? `Abrir perfil de ${heroProfile.nome_publico}` : "Sem perfis disponíveis"}
              onClick={() => heroProfile && onOpenProfile(heroProfile)}
              disabled={!heroProfile}
            >
              {heroProfile ? (
                <>
                  <img src={heroProfile.foto_url} alt={`Perfil de ${heroProfile.nome_publico}`} />
                  <div className="nk-hero__visual-shade" />
                  <div className="nk-hero__visual-badge">
                    <ShieldCheck size={15} />
                    Perfil verificado
                  </div>
                  <div className="nk-hero__visual-caption">
                    <span>{heroProfile.objetivo_display}</span>
                    <strong>
                      {heroProfile.nome_publico}
                      {heroProfile.idade ? `, ${heroProfile.idade}` : ""}
                    </strong>
                    <small>{heroProfile.cidade}</small>
                    <em>Ver perfil <ArrowRight size={14} /></em>
                  </div>
                </>
              ) : (
                <div className="nk-hero__empty">Ainda não há perfis disponíveis</div>
              )}
            </button>
          </div>
        </section>

        <section className="nk-trust-strip nk-trust-strip--detailed" aria-label="Como o NKATA funciona">
          <div className="nk-shell nk-trust-strip__inner">
            {platformCommitments.map((item) => (
              <span key={item.title}>
                <strong>{item.title}</strong>
                <small>{item.text}</small>
              </span>
            ))}
          </div>
        </section>

        <section className="nk-section nk-featured">
          <div className="nk-shell">
            <div className="nk-section-heading">
              <div>
                <span className="nk-eyebrow nk-eyebrow--dark">Alguns perfis</span>
                <h2>Veja quem está disponível.</h2>
                <p>Abra um perfil para conhecer melhor a pessoa antes de demonstrar interesse.</p>
              </div>
              <button type="button" className="nk-text-action" onClick={() => onNavigate("discover")}>Ver todos <ArrowRight size={17} /></button>
            </div>

            <div className="nk-profile-grid">
              {featured.map((profile) => (
                <ProfileCard
                  key={profile.id}
                  profile={profile}
                  onOpen={onOpenProfile}
                  saved={isSaved(profile)}
                  onToggleSaved={onToggleSaved}
                />
              ))}
            </div>
          </div>
        </section>

        <section className="nk-section nk-process" id="processo">
          <div className="nk-shell">
            <div className="nk-section-heading nk-section-heading--center">
              <div>
                <span className="nk-eyebrow nk-eyebrow--dark">Como entrar</span>
                <h2>Três passos para começar.</h2>
              </div>
            </div>

            <div className="nk-process__grid">
              {processSteps.map((step) => {
                const Icon = step.icon;
                return (
                  <article key={step.number}>
                    <span className="nk-process__number">{step.number}</span>
                    <span className="nk-process__icon"><Icon size={22} /></span>
                    <h3>{step.title}</h3>
                    <p>{step.text}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <SecurityPanel />
      </main>

      <footer className="nk-footer">
        <div className="nk-shell nk-footer__inner">
          <div>
            <strong>NKATA</strong>
            <p>Para quem procura uma relação séria.</p>
          </div>
          <span>© 2026 NKATA · Moçambique</span>
        </div>
      </footer>
    </>
  );
}
