import { BadgeCheck, EyeOff, Fingerprint, ShieldCheck } from "lucide-react";

const items = [
  {
    icon: Fingerprint,
    title: "Pedido revisto pela equipa",
    text: "O perfil só aparece depois da análise dos dados enviados.",
  },
  {
    icon: EyeOff,
    title: "Contactos ocultos",
    text: "Telefone, email e documentos não aparecem no perfil.",
  },
  {
    icon: BadgeCheck,
    title: "Informação essencial",
    text: "A pessoa mostra o que procura, a cidade e uma apresentação curta.",
  },
];

export default function SecurityPanel() {
  return (
    <section className="nk-security" id="seguranca">
      <div className="nk-shell nk-security__grid">
        <div className="nk-security__intro">
          <span className="nk-eyebrow nk-eyebrow--light">
            <ShieldCheck size={15} />
            Segurança
          </span>
          <h2>Conheça pessoas sem expor os seus dados.</h2>
          <p>
            A equipa acompanha os pedidos, os perfis e as denúncias feitas dentro da plataforma.
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
