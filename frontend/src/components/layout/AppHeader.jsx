import { LockKeyhole, Menu, ShieldCheck } from "lucide-react";

export default function AppHeader({ activePage, onNavigate }) {
  return (
    <header className="nk-header">
      <div className="nk-shell nk-header__inner">
        <button
          type="button"
          className="nk-brand"
          onClick={() => onNavigate("home")}
          aria-label="Ir para o início"
        >
          <span className="nk-brand__mark">N</span>
          <span className="nk-brand__word">NKATA</span>
        </button>

        <nav className="nk-desktop-nav" aria-label="Navegação principal">
          <button
            type="button"
            className={activePage === "home" ? "is-active" : ""}
            onClick={() => onNavigate("home")}
          >
            Início
          </button>
          <button
            type="button"
            className={activePage === "discover" ? "is-active" : ""}
            onClick={() => onNavigate("discover")}
          >
            Descobrir
          </button>
          <button type="button" onClick={() => onNavigate("security")}>Segurança</button>
        </nav>

        <div className="nk-header__actions">
          <span className="nk-private-status">
            <LockKeyhole size={14} />
            Ambiente privado
          </span>
          <button type="button" className="nk-header__login">Entrar</button>
          <button type="button" className="nk-button nk-button--dark nk-header__request">
            <ShieldCheck size={17} />
            Solicitar entrada
          </button>
          <button type="button" className="nk-icon-button nk-header__menu" aria-label="Abrir menu">
            <Menu size={20} />
          </button>
        </div>
      </div>
    </header>
  );
}
