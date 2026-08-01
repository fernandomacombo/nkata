import { BadgeCheck, EyeOff, Fingerprint, ShieldCheck } from "lucide-react";

const items = [
  {
    icon: Fingerprint,
    title: "Entrada analisada",
    text: "O acesso começa com um pedido e uma avaliação antes da publicação do perfil.",
  },
  {
    icon: EyeOff,
    title: "Dados fora da área pública",
    text: "Telefone, email e documentos não aparecem nos perfis apresentados à comunidade.",
  },
  {
    icon: BadgeCheck,
    title: "Intenção clara",
    text: "Cada perfil apresenta objetivo, contexto e informação essencial sem exposição excessiva.",
  },
];

export default function SecurityPanel() {
  return (
    <section className="nk-security" id="seguranca">
      <div className="nk-shell nk-security__grid">
        <div className="nk-security__intro">
          <span className="nk-eyebrow nk-eyebrow--light">
            <ShieldCheck size={15} />
            Proteção por princípio
          </span>
          <h2>Confiança não é um detalhe. É a base.</h2>
          <p>
            O NKATA foi pensado para relações sérias, com menos exposição, mais contexto e controlo em cada etapa.
          </p>
        </div>

        <div className="nk-security__items">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.title}>
                <span className="nk-security__icon"><Icon size={20} /></span>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
