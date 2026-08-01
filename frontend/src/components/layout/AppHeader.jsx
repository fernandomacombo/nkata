import { Bookmark, LockKeyhole, Menu, ShieldCheck } from "lucide-react";

export default function AppHeader({ activePage, onNavigate, savedCount = 0 }) {
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
            Perfis
          </button>
          <button
            type="button"
            className={activePage === "saved" ? "is-active" : ""}
            onClick={() => onNavigate("saved")}
          >
            Guardados {savedCount > 0 ? `(${savedCount})` : ""}
          </button>
          <button type="button" onClick={() => onNavigate("security")}>Segurança</button>
        </nav>

        <div className="nk-header__actions">
          <span className="nk-private-status">
            <LockKeyhole size={14} />
            Conta protegida
          </span>
          <button type="button" className="nk-header__login" onClick={() => window.location.assign("/entrar/")}>Entrar</button>
          <button type="button" className="nk-button nk-button--dark nk-header__request" onClick={() => window.location.assign("/solicitar-entrada/") }>
            <ShieldCheck size={17} />
            Pedir acesso
          </button>
          <button
            type="button"
            className="nk-icon-button nk-header__menu"
            aria-label="Abrir perfis guardados"
            onClick={() => onNavigate("saved")}
          >
            {savedCount > 0 ? <Bookmark size={20} fill="currentColor" /> : <Menu size={20} />}
          </button>
        </div>
      </div>
    </header>
  );
}
