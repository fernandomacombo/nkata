import { BadgeCheck, EyeOff, Fingerprint, ShieldCheck } from "lucide-react";
import useInterfaceLanguage from "../../hooks/useInterfaceLanguage.js";

const items = [
  {
    icon: Fingerprint,
    pt: ["Pedido revisto pela equipa", "O perfil só aparece depois da análise dos dados enviados."],
    en: ["Application reviewed by our team", "A profile only appears after the submitted information is reviewed."],
  },
  {
    icon: EyeOff,
    pt: ["Contactos ocultos", "Telefone, email e documentos não aparecem no perfil."],
    en: ["Private contact details", "Phone, email and documents are not shown on the profile."],
  },
  {
    icon: BadgeCheck,
    pt: ["Informação essencial", "A pessoa mostra o que procura, a cidade e uma apresentação curta."],
    en: ["Essential information", "Members share what they seek, their city and a short introduction."],
  },
];

export default function SecurityPanel() {
  const english = useInterfaceLanguage() === "EN";
  return (
    <section className="nk-security" id="seguranca">
      <div className="nk-shell nk-security__grid">
        <div className="nk-security__intro">
          <span className="nk-eyebrow nk-eyebrow--light">
            <ShieldCheck size={15} />
            {english ? "Safety" : "Segurança"}
          </span>
          <h2>{english ? "Meet people without exposing your personal data." : "Conheça pessoas sem expor os seus dados."}</h2>
          <p>
            {english ? "Our team reviews applications, profiles and reports made on the platform." : "A equipa acompanha os pedidos, os perfis e as denúncias feitas dentro da plataforma."}
          </p>
        </div>

        <div className="nk-security__items">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.pt[0]}>
                <span className="nk-security__icon"><Icon size={20} /></span>
                <div>
                  <h3>{(english ? item.en : item.pt)[0]}</h3>
                  <p>{(english ? item.en : item.pt)[1]}</p>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
