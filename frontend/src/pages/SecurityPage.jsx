import { ArrowRight, LockKeyhole, ShieldCheck } from "lucide-react";
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";
import SecurityPanel from "../components/security/SecurityPanel.jsx";
import useInterfaceLanguage from "../hooks/useInterfaceLanguage.js";

export default function SecurityPage({ authenticated, onNavigate }) {
  const english = useInterfaceLanguage() === "EN";

  return (
    <main className="nk-security-page">
      <CompactPageHeader title={english ? "Safety" : "Segurança"}>
        <button
          type="button"
          onClick={() => onNavigate(authenticated ? "account" : "login")}
        >
          {authenticated ? <ShieldCheck size={17} /> : <LockKeyhole size={17} />}
          {authenticated
            ? (english ? "Privacy settings" : "Definições de privacidade")
            : (english ? "Sign in" : "Entrar")}
          <ArrowRight size={16} />
        </button>
      </CompactPageHeader>

      <div className="nk-security-page__content">
        <SecurityPanel />
      </div>
    </main>
  );
}
