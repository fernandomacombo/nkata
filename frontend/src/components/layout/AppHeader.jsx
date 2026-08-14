import { useEffect, useState } from "react";
import {
  Bell,
  Bookmark,
  CirclePlay,
  FileSearch,
  HeartHandshake,
  Home,
  LockKeyhole,
  LogIn,
  LogOut,
  Menu,
  PanelsTopLeft,
  Search,
  ShieldCheck,
  UserPlus,
  UserRound,
  X,
} from "lucide-react";

export default function AppHeader({
  activePage,
  onNavigate,
  savedCount = 0,
  unreadMatches = 0,
  unreadNotifications = 0,
  session,
  sessionLoading = false,
  onSignOut,
  heroMode = false,
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const authenticated = Boolean(session?.authenticated);
  const memberName = session?.profile?.name || session?.user?.name || "Conta";

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [activePage, authenticated]);

  useEffect(() => {
    if (!mobileMenuOpen) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleEscape = (event) => {
      if (event.key === "Escape") setMobileMenuOpen(false);
    };

    window.addEventListener("keydown", handleEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleEscape);
    };
  }, [mobileMenuOpen]);

  const navigate = (page) => {
    setMobileMenuOpen(false);
    onNavigate(page);
  };

  const goTo = (path) => {
    setMobileMenuOpen(false);
    window.location.assign(path);
  };

  const signOut = () => {
    setMobileMenuOpen(false);
    onSignOut?.();
  };

  return (
    <header className={`nk-header ${heroMode ? "nk-header--hero" : ""}`}>
      <div className="nk-shell nk-header__inner">
        <button
          type="button"
          className="nk-brand"
          onClick={() => navigate("home")}
          aria-label="Ir para o início"
        >
          <span className="nk-brand__mark">N</span>
          <span className="nk-brand__word">NKATA</span>
        </button>

        <nav className="nk-desktop-nav" aria-label="Navegação principal">
          <button
            type="button"
            className={activePage === "home" ? "is-active" : ""}
            onClick={() => navigate("home")}
          >
            Início
          </button>
          <button
            type="button"
            className={activePage === "discover" ? "is-active" : ""}
            onClick={() => navigate("discover")}
          >
            Perfis
          </button>
          {authenticated && (
            <button
              type="button"
              className={activePage === "moments" ? "is-active" : ""}
              onClick={() => navigate("moments")}
            >
              Momentos
            </button>
          )}
          {session?.user?.is_staff && (
            <button
              type="button"
              className={activePage === "admin" ? "is-active" : ""}
              onClick={() => navigate("admin")}
            >
              Painel
            </button>
          )}
          {authenticated && (
            <button
              type="button"
              className={activePage === "saved" ? "is-active" : ""}
              onClick={() => navigate("saved")}
            >
              Guardados {savedCount > 0 ? `(${savedCount})` : ""}
            </button>
          )}
          {authenticated && (
            <button
              type="button"
              className={activePage === "matches" ? "is-active" : ""}
              onClick={() => navigate("matches")}
            >
              Matches {unreadMatches > 0 ? `(${unreadMatches})` : ""}
            </button>
          )}
          <button type="button" onClick={() => navigate("security")}>Segurança</button>
          {!authenticated && (
            <button type="button" onClick={() => goTo("/acompanhar-pedido/")}>
              Acompanhar pedido
            </button>
          )}
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
                className={`nk-header__notifications ${activePage === "notifications" ? "is-active" : ""}`}
                onClick={() => navigate("notifications")}
                aria-label={
                  unreadNotifications
                    ? `${unreadNotifications} notificações por ler`
                    : "Abrir notificações"
                }
              >
                <Bell size={18} />
                {unreadNotifications > 0 && (
                  <span className="nk-header__notifications-count">
                    {unreadNotifications > 99 ? "99+" : unreadNotifications}
                  </span>
                )}
              </button>
              <button
                type="button"
                className="nk-header__member"
                onClick={() => navigate("account")}
                title={memberName}
              >
                <UserRound size={16} />
                <span>{memberName}</span>
              </button>
              <button
                type="button"
                className="nk-header__logout"
                onClick={signOut}
                aria-label="Terminar sessão"
                title="Sair"
              >
                <LogOut size={17} />
              </button>
            </>
          ) : (
            <button
              type="button"
              className="nk-header__login"
              onClick={() => navigate("login")}
              disabled={sessionLoading}
              aria-label="Entrar"
              title="Entrar"
            >
              <LogIn size={17} />
              <span>Entrar</span>
            </button>
          )}

          {!authenticated && (
            <button
              type="button"
              className="nk-button nk-button--dark nk-header__request"
              onClick={() => goTo("/pedir-acesso/")}
            >
              <ShieldCheck size={17} />
              Pedir acesso
            </button>
          )}

          <button
            type="button"
            className={`nk-icon-button nk-header__menu ${mobileMenuOpen ? "is-open" : ""}`}
            aria-label={mobileMenuOpen ? "Fechar menu" : "Abrir menu"}
            aria-expanded={mobileMenuOpen}
            aria-controls="nk-mobile-menu"
            onClick={() => setMobileMenuOpen((current) => !current)}
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="nk-mobile-menu-layer">
          <button
            type="button"
            className="nk-mobile-menu__backdrop"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Fechar menu"
          />

          <aside
            id="nk-mobile-menu"
            className="nk-mobile-menu"
            aria-label="Menu principal"
          >
            <header className="nk-mobile-menu__header">
              <div className="nk-mobile-menu__brand">
                <span className="nk-brand__mark">N</span>
                <div>
                  <strong>NKATA</strong>
                  <small>{authenticated ? "Área de membros" : "Relações com intenção"}</small>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Fechar menu"
              >
                <X size={20} />
              </button>
            </header>

            {authenticated && (
              <div className="nk-mobile-menu__member">
                <span><UserRound size={20} /></span>
                <div>
                  <small>Sessão iniciada</small>
                  <strong>{memberName}</strong>
                </div>
                <LockKeyhole size={17} />
              </div>
            )}

            <nav className="nk-mobile-menu__nav" aria-label="Opções do menu">
              <button
                type="button"
                className={activePage === "home" ? "is-active" : ""}
                onClick={() => navigate("home")}
              >
                <span><Home size={19} /></span>
                <div><strong>Início</strong><small>Voltar à página principal</small></div>
              </button>

              <button
                type="button"
                className={activePage === "discover" ? "is-active" : ""}
                onClick={() => navigate("discover")}
              >
                <span><Search size={19} /></span>
                <div><strong>Perfis</strong><small>Conhecer pessoas da comunidade</small></div>
              </button>

              {authenticated && (
                <button
                  type="button"
                  className={activePage === "moments" ? "is-active" : ""}
                  onClick={() => navigate("moments")}
                >
                  <span><CirclePlay size={19} /></span>
                  <div><strong>Momentos</strong><small>Histórias que desaparecem em 24 horas</small></div>
                </button>
              )}

              {session?.user?.is_staff && (
                <button
                  type="button"
                  className={activePage === "admin" ? "is-active" : ""}
                  onClick={() => navigate("admin")}
                >
                  <span><PanelsTopLeft size={19} /></span>
                  <div><strong>Painel NKATA</strong><small>Administração e moderação</small></div>
                </button>
              )}

              {authenticated && (
                <button
                  type="button"
                  className={activePage === "saved" ? "is-active" : ""}
                  onClick={() => navigate("saved")}
                >
                  <span><Bookmark size={19} /></span>
                  <div><strong>Guardados</strong><small>A sua seleção pessoal</small></div>
                  {savedCount > 0 && <em>{savedCount > 99 ? "99+" : savedCount}</em>}
                </button>
              )}

              {authenticated && (
                <button
                  type="button"
                  className={activePage === "matches" ? "is-active" : ""}
                  onClick={() => navigate("matches")}
                >
                  <span><HeartHandshake size={19} /></span>
                  <div><strong>Matches</strong><small>Conversas e ligações</small></div>
                  {unreadMatches > 0 && <em>{unreadMatches > 99 ? "99+" : unreadMatches}</em>}
                </button>
              )}

              {authenticated && (
                <button
                  type="button"
                  className={activePage === "notifications" ? "is-active" : ""}
                  onClick={() => navigate("notifications")}
                >
                  <span><Bell size={19} /></span>
                  <div><strong>Notificações</strong><small>Novidades importantes</small></div>
                  {unreadNotifications > 0 && (
                    <em>{unreadNotifications > 99 ? "99+" : unreadNotifications}</em>
                  )}
                </button>
              )}

              {authenticated && (
                <button
                  type="button"
                  className={activePage === "account" ? "is-active" : ""}
                  onClick={() => navigate("account")}
                >
                  <span><UserRound size={19} /></span>
                  <div><strong>Minha conta</strong><small>Perfil, fotografia e privacidade</small></div>
                </button>
              )}

              <button type="button" onClick={() => navigate("security")}>
                <span><ShieldCheck size={19} /></span>
                <div><strong>Segurança</strong><small>Como protegemos a comunidade</small></div>
              </button>

              {!authenticated && (
                <button type="button" onClick={() => goTo("/acompanhar-pedido/")}>
                  <span><FileSearch size={19} /></span>
                  <div><strong>Acompanhar pedido</strong><small>Consultar o estado da análise</small></div>
                </button>
              )}
            </nav>

            <footer className="nk-mobile-menu__footer">
              {authenticated ? (
                <button type="button" className="nk-mobile-menu__logout" onClick={signOut}>
                  <LogOut size={18} /> Terminar sessão
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    className="nk-button nk-button--wine"
                    onClick={() => goTo("/pedir-acesso/")}
                  >
                    <UserPlus size={18} /> Pedir acesso
                  </button>
                  <button
                    type="button"
                    className="nk-button nk-button--quiet"
                    onClick={() => navigate("login")}
                    disabled={sessionLoading}
                  >
                    <LogIn size={18} /> Entrar
                  </button>
                </>
              )}
              <small><LockKeyhole size={13} /> Ligação protegida</small>
            </footer>
          </aside>
        </div>
      )}
    </header>
  );
}
