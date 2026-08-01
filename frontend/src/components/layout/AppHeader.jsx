import {
  Bookmark,
  LockKeyhole,
  LogOut,
  Menu,
  ShieldCheck,
  UserRound,
} from "lucide-react";

export default function AppHeader({
  activePage,
  onNavigate,
  savedCount = 0,
  session,
  sessionLoading = false,
  onSignOut,
}) {
  const authenticated = Boolean(session?.authenticated);
  const memberName = session?.profile?.name || session?.user?.name || "Conta";

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
            {authenticated ? "Sessão iniciada" : "Ligação protegida"}
          </span>

          {authenticated ? (
            <>
              <button
                type="button"
                className="nk-header__member"
                onClick={() => onNavigate("account")}
                title={memberName}
              >
                <UserRound size={16} />
                <span>{memberName}</span>
              </button>
              <button
                type="button"
                className="nk-header__logout"
                onClick={onSignOut}
                aria-label="Terminar sessão"
              >
                <LogOut size={17} />
              </button>
            </>
          ) : (
            <button
              type="button"
              className="nk-header__login"
              onClick={() => onNavigate("login")}
              disabled={sessionLoading}
            >
              Entrar
            </button>
          )}

          {!authenticated && (
            <button
              type="button"
              className="nk-button nk-button--dark nk-header__request"
              onClick={() => window.location.assign("/solicitar-entrada/")}
            >
              <ShieldCheck size={17} />
              Pedir acesso
            </button>
          )}

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
