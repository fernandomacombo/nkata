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
    title: "Solicite a entrada",
    text: "Partilhe apenas os dados necessários para iniciar a análise.",
    icon: UserCheck,
  },
  {
    number: "02",
    title: "Passe pela verificação",
    text: "A equipa avalia o pedido e protege os dados enviados.",
    icon: ShieldCheck,
  },
  {
    number: "03",
    title: "Conheça com intenção",
    text: "Depois da aprovação, descubra pessoas com objetivos claros.",
    icon: Sparkles,
  },
];

export default function HomePage({ profiles, onNavigate, onOpenProfile }) {
  const featured = profiles.slice(0, 3);
  const heroProfile = featured[0];

  return (
    <>
      <main>
        <section className="nk-hero">
          <div className="nk-shell nk-hero__grid">
            <div className="nk-hero__copy">
              <span className="nk-eyebrow">
                <LockKeyhole size={15} />
                Comunidade privada
              </span>

              <h1>
                Conheça alguém com <em>intenção real.</em>
              </h1>

              <p>
                Uma experiência reservada para adultos que valorizam respeito, clareza e relações construídas com calma.
              </p>

              <div className="nk-hero__actions">
                <button
                  type="button"
                  className="nk-button nk-button--wine"
                  onClick={() => onNavigate("discover")}
                >
                  Descobrir perfis
                  <ArrowRight size={18} />
                </button>
                <button
                  type="button"
                  className="nk-button nk-button--quiet"
                  onClick={() => window.location.assign("/solicitar-entrada/")}
                >
                  Solicitar entrada
                </button>
              </div>

              <div className="nk-hero__trust">
                <span><CheckCircle2 size={16} /> Perfis analisados</span>
                <span><CheckCircle2 size={16} /> Dados protegidos</span>
                <span><CheckCircle2 size={16} /> Acesso controlado</span>
              </div>
            </div>

            <button
              type="button"
              className="nk-hero__visual"
              aria-label={heroProfile ? `Abrir perfil de ${heroProfile.nome_publico}` : "Perfis em preparação"}
              onClick={() => heroProfile && onOpenProfile(heroProfile)}
              disabled={!heroProfile}
            >
              {heroProfile ? (
                <>
                  <img src={heroProfile.foto_url} alt={`Perfil de ${heroProfile.nome_publico}`} />
                  <div className="nk-hero__visual-shade" />
                  <div className="nk-hero__visual-badge">
                    <ShieldCheck size={16} />
                    Perfil aprovado
                  </div>
                  <div className="nk-hero__visual-caption">
                    <span>Conhecer com propósito</span>
                    <strong>{heroProfile.nome_publico}, {heroProfile.idade}</strong>
                    <small>{heroProfile.cidade}</small>
                  </div>
                </>
              ) : (
                <div className="nk-hero__empty">Perfis em preparação</div>
              )}
            </button>
          </div>
        </section>

        <section className="nk-trust-strip" aria-label="Compromissos NKATA">
          <div className="nk-shell nk-trust-strip__inner">
            <span>Privacidade por defeito</span>
            <span>Moderação humana</span>
            <span>Interações com intenção</span>
            <span>Comunidade moçambicana</span>
          </div>
        </section>

        <section className="nk-section nk-featured">
          <div className="nk-shell">
            <div className="nk-section-heading">
              <div>
                <span className="nk-eyebrow nk-eyebrow--dark">Perfis selecionados</span>
                <h2>Pessoas, não catálogos.</h2>
                <p>
                  Informação essencial, fotografias controladas e intenção apresentada com clareza.
                </p>
              </div>
              <button type="button" className="nk-text-action" onClick={() => onNavigate("discover")}>Ver todos <ArrowRight size={17} /></button>
            </div>

            <div className="nk-profile-grid">
              {featured.map((profile) => (
                <ProfileCard
                  key={profile.id}
                  profile={profile}
                  onOpen={() => onOpenProfile(profile)}
                />
              ))}
            </div>
          </div>
        </section>

        <section className="nk-section nk-process" id="processo">
          <div className="nk-shell">
            <div className="nk-section-heading nk-section-heading--center">
              <div>
                <span className="nk-eyebrow nk-eyebrow--dark">Como funciona</span>
                <h2>Um processo simples. Um padrão elevado.</h2>
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
            <p>Relações sérias, com privacidade e intenção.</p>
          </div>
          <span>© 2026 NKATA · Moçambique</span>
        </div>
      </footer>
    </>
  );
}
