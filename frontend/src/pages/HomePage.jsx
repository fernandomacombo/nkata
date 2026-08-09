import {
  ArrowDown,
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

const trustItems = [
  { title: "Perfis analisados", text: "A entrada passa por uma verificação antes da publicação." },
  { title: "Contactos protegidos", text: "Telefone, email e documentos não aparecem publicamente." },
  { title: "Interesse dos dois lados", text: "A conversa só começa depois de existir um match." },
  { title: "Feito para Moçambique", text: "Uma experiência pensada para o nosso contexto." },
];

const defaultDesktopHero = "/images/nkata-hero-desktop.webp";
const defaultMobileHero = "/images/nkata-hero-mobile.webp";

export default function HomePage({
  profiles,
  onNavigate,
  onOpenProfile,
  isSaved,
  onToggleSaved,
}) {
  const featured = profiles.slice(0, 3);
  const desktopHero = import.meta.env.VITE_HERO_DESKTOP_IMAGE_URL || defaultDesktopHero;
  const mobileHero = import.meta.env.VITE_HERO_MOBILE_IMAGE_URL || defaultMobileHero;

  return (
    <>
      <main>
        <section className="nk-hero nk-hero--cover">
          <picture className="nk-hero__background" aria-hidden="true">
            <source media="(max-width: 760px)" srcSet={mobileHero} />
            <img
              src={desktopHero}
              alt=""
              fetchPriority="high"
              decoding="async"
            />
          </picture>

          <div className="nk-hero__overlay" />

          <div className="nk-shell nk-hero__cover-content">
            <div className="nk-hero__copy">
              <span className="nk-eyebrow nk-eyebrow--hero">
                <LockKeyhole size={15} />
                Entrada mediante aprovação
              </span>

              <h1>
                Relações sérias começam com <em>intenções claras.</em>
              </h1>

              <p>
                Conheça pessoas adultas que procuram respeito, compromisso e uma relação com futuro.
              </p>

              <div className="nk-hero__actions">
                <button
                  type="button"
                  className="nk-button nk-button--wine nk-button--hero-primary"
                  onClick={() => onNavigate("discover")}
                >
                  Conhecer perfis
                  <ArrowRight size={18} />
                </button>
                <button
                  type="button"
                  className="nk-button nk-button--hero-secondary"
                  onClick={() => window.location.assign("/pedir-acesso/")}
                >
                  Pedir acesso
                </button>
              </div>

              <div className="nk-hero__trust">
                <span><CheckCircle2 size={16} /> Perfis confirmados</span>
                <span><CheckCircle2 size={16} /> Contactos ocultos</span>
                <span><CheckCircle2 size={16} /> Conversas por match</span>
              </div>
            </div>

            <button
              type="button"
              className="nk-hero__scroll"
              onClick={() => document.getElementById("destaques")?.scrollIntoView({ behavior: "smooth" })}
              aria-label="Ver mais conteúdo"
            >
              <span>Descobrir</span>
              <ArrowDown size={18} />
            </button>
          </div>
        </section>

        <section className="nk-trust-strip" aria-label="Como o NKATA protege a comunidade">
          <div className="nk-shell nk-trust-strip__inner">
            {trustItems.map((item) => (
              <article key={item.title}>
                <strong>{item.title}</strong>
                <span>{item.text}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="nk-section nk-featured" id="destaques">
          <div className="nk-shell">
            {featured.length ? (
              <>
                <div className="nk-section-heading">
                  <div>
                    <span className="nk-eyebrow nk-eyebrow--dark">Alguns perfis</span>
                    <h2>Conheça pessoas com intenção.</h2>
                    <p>Leia a apresentação com calma antes de demonstrar interesse.</p>
                  </div>
                  <button type="button" className="nk-text-action" onClick={() => onNavigate("discover")}>
                    Ver todos <ArrowRight size={17} />
                  </button>
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
              </>
            ) : (
              <div className="nk-community-empty">
                <span className="nk-community-empty__icon"><ShieldCheck size={26} /></span>
                <div>
                  <span className="nk-eyebrow nk-eyebrow--dark">Comunidade em preparação</span>
                  <h2>Os perfis aparecem depois da aprovação.</h2>
                  <p>
                    Não mostramos pessoas fictícias para preencher espaço. Assim que existirem
                    perfis aprovados e visíveis, serão apresentados aqui.
                  </p>
                </div>
                <button
                  type="button"
                  className="nk-button nk-button--wine"
                  onClick={() => window.location.assign("/pedir-acesso/")}
                >
                  Pedir acesso <ArrowRight size={17} />
                </button>
              </div>
            )}
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
