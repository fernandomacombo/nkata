import { useEffect, useState } from "react";
import {
  ArrowLeft,
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
import NkataLogo from "../brand/NkataLogo.jsx";

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
  showMobileBack = false,
  onMobileBack,
  language = "PT",
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const authenticated = Boolean(session?.authenticated);
  const operator = Boolean(authenticated && session?.user?.is_staff);
  const member = Boolean(authenticated && !operator);
  const english = language === "EN";
  const tr = (portuguese, englishText) => (english ? englishText : portuguese);
  const memberName = session?.profile?.name || session?.user?.name || tr("Conta", "Account");

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
        {showMobileBack && (
          <button
            type="button"
            className="nk-header__mobile-back"
            onClick={onMobileBack}
            aria-label={tr("Voltar", "Back")}
          >
            <ArrowLeft size={19} />
            <span>{tr("Voltar", "Back")}</span>
          </button>
        )}

        <button
          type="button"
          className="nk-brand"
          onClick={() => navigate(operator ? "admin" : "home")}
          aria-label={tr("Ir para o início", "Go to home")}
        >
          <NkataLogo className="nk-brand__logo" />
          <span className="nk-brand__word">NKATA</span>
        </button>

        <nav className="nk-desktop-nav" aria-label={tr("Navegação principal", "Main navigation")}>
          {!operator && <button
            type="button"
            className={activePage === "home" ? "is-active" : ""}
            onClick={() => navigate("home")}
          >
            {tr("Início", "Home")}
          </button>}
          {!operator && <button
            type="button"
            className={activePage === "discover" ? "is-active" : ""}
            onClick={() => navigate("discover")}
          >
            {tr("Perfis", "Profiles")}
          </button>}
          {member && (
            <button
              type="button"
              className={activePage === "moments" ? "is-active" : ""}
              onClick={() => navigate("moments")}
            >
              {tr("Momentos", "Moments")}
            </button>
          )}
          {session?.user?.is_staff && (
            <button
              type="button"
              className={activePage === "admin" ? "is-active" : ""}
              onClick={() => navigate("admin")}
            >
              {tr("Painel", "Admin")}
            </button>
          )}
          {member && (
            <button
              type="button"
              className={activePage === "saved" ? "is-active" : ""}
              onClick={() => navigate("saved")}
            >
              {tr("Guardados", "Saved")} {savedCount > 0 ? `(${savedCount})` : ""}
            </button>
          )}
          {member && (
            <button
              type="button"
              className={activePage === "matches" ? "is-active" : ""}
              onClick={() => navigate("matches")}
            >
              Matches {unreadMatches > 0 ? `(${unreadMatches})` : ""}
            </button>
          )}
          {!operator && <button
            type="button"
            className={activePage === "security" ? "is-active" : ""}
            onClick={() => navigate("security")}
          >
            {tr("Segurança", "Safety")}
          </button>}
          {!authenticated && (
            <button type="button" onClick={() => goTo("/acompanhar-pedido/")}>
              {tr("Acompanhar pedido", "Track request")}
            </button>
          )}
        </nav>

        <div className="nk-header__actions">
          <span className="nk-private-status">
            <LockKeyhole size={14} />
            {authenticated ? tr("Sessão iniciada", "Signed in") : tr("Ligação protegida", "Secure connection")}
          </span>

          {authenticated ? (
            <>
              {member && <button
                type="button"
                className={`nk-header__notifications ${activePage === "notifications" ? "is-active" : ""}`}
                onClick={() => navigate("notifications")}
                aria-label={
                  unreadNotifications
                    ? `${unreadNotifications} ${tr("notificações por ler", "unread notifications")}`
                    : tr("Abrir notificações", "Open notifications")
                }
              >
                <Bell size={18} />
                {unreadNotifications > 0 && (
                  <span className="nk-header__notifications-count">
                    {unreadNotifications > 99 ? "99+" : unreadNotifications}
                  </span>
                )}
              </button>}
              {member && <button
                type="button"
                className="nk-header__member"
                onClick={() => navigate("account")}
                title={memberName}
              >
                <UserRound size={16} />
                <span>{memberName}</span>
              </button>}
              <button
                type="button"
                className="nk-header__logout"
                onClick={signOut}
                aria-label={tr("Terminar sessão", "Sign out")}
                title={tr("Sair", "Sign out")}
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
              aria-label={tr("Entrar", "Sign in")}
              title={tr("Entrar", "Sign in")}
            >
              <LogIn size={17} />
              <span>{tr("Entrar", "Sign in")}</span>
            </button>
          )}

          {!authenticated && (
            <button
              type="button"
              className="nk-button nk-button--dark nk-header__request"
              onClick={() => goTo("/pedir-acesso/")}
            >
              <ShieldCheck size={17} />
              {tr("Pedir acesso", "Request access")}
            </button>
          )}

          <button
            type="button"
            className={`nk-icon-button nk-header__menu ${mobileMenuOpen ? "is-open" : ""}`}
            aria-label={mobileMenuOpen ? tr("Fechar menu", "Close menu") : tr("Abrir menu", "Open menu")}
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
            aria-label={tr("Fechar menu", "Close menu")}
          />

          <aside
            id="nk-mobile-menu"
            className="nk-mobile-menu"
            aria-label={tr("Menu principal", "Main menu")}
          >
            <header className="nk-mobile-menu__header">
              <div className="nk-mobile-menu__brand">
                <NkataLogo className="nk-brand__logo" />
                <div>
                  <strong>NKATA</strong>
                  <small>{operator ? tr("Área administrativa", "Admin area") : authenticated ? tr("Área de membros", "Members area") : tr("Relações com intenção", "Intentional relationships")}</small>
                </div>
              </div>
              {!operator && <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                aria-label={tr("Fechar menu", "Close menu")}
              >
                <X size={20} />
              </button>}
            </header>

            {authenticated && (
              <div className="nk-mobile-menu__member">
                <span><UserRound size={20} /></span>
                <div>
                  <small>{tr("Sessão iniciada", "Signed in")}</small>
                  <strong>{memberName}</strong>
                </div>
                <LockKeyhole size={17} />
              </div>
            )}

            <nav className="nk-mobile-menu__nav" aria-label={tr("Opções do menu", "Menu options")}>
              {!operator && <button
                type="button"
                className={activePage === "home" ? "is-active" : ""}
                onClick={() => navigate("home")}
              >
                <span><Home size={19} /></span>
                <div><strong>{tr("Início", "Home")}</strong><small>{tr("Voltar à página principal", "Return to the home page")}</small></div>
              </button>}

              <button
                type="button"
                className={activePage === "discover" ? "is-active" : ""}
                onClick={() => navigate("discover")}
              >
                <span><Search size={19} /></span>
                <div><strong>{tr("Perfis", "Profiles")}</strong><small>{tr("Conhecer pessoas da comunidade", "Meet people in the community")}</small></div>
              </button>

              {member && (
                <button
                  type="button"
                  className={activePage === "moments" ? "is-active" : ""}
                  onClick={() => navigate("moments")}
                >
                  <span><CirclePlay size={19} /></span>
                  <div><strong>{tr("Momentos", "Moments")}</strong><small>{tr("Histórias que desaparecem em 24 horas", "Stories available for 24 hours")}</small></div>
                </button>
              )}

              {session?.user?.is_staff && (
                <button
                  type="button"
                  className={activePage === "admin" ? "is-active" : ""}
                  onClick={() => navigate("admin")}
                >
                  <span><PanelsTopLeft size={19} /></span>
                  <div><strong>{tr("Painel NKATA", "NKATA Admin")}</strong><small>{tr("Administração e moderação", "Administration and moderation")}</small></div>
                </button>
              )}

              {member && (
                <button
                  type="button"
                  className={activePage === "saved" ? "is-active" : ""}
                  onClick={() => navigate("saved")}
                >
                  <span><Bookmark size={19} /></span>
                  <div><strong>{tr("Guardados", "Saved")}</strong><small>{tr("A sua seleção pessoal", "Your personal selection")}</small></div>
                  {savedCount > 0 && <em>{savedCount > 99 ? "99+" : savedCount}</em>}
                </button>
              )}

              {member && (
                <button
                  type="button"
                  className={activePage === "matches" ? "is-active" : ""}
                  onClick={() => navigate("matches")}
                >
                  <span><HeartHandshake size={19} /></span>
                  <div><strong>Matches</strong><small>{tr("Conversas e ligações", "Chats and calls")}</small></div>
                  {unreadMatches > 0 && <em>{unreadMatches > 99 ? "99+" : unreadMatches}</em>}
                </button>
              )}

              {member && (
                <button
                  type="button"
                  className={activePage === "notifications" ? "is-active" : ""}
                  onClick={() => navigate("notifications")}
                >
                  <span><Bell size={19} /></span>
                  <div><strong>{tr("Notificações", "Notifications")}</strong><small>{tr("Novidades importantes", "Important updates")}</small></div>
                  {unreadNotifications > 0 && (
                    <em>{unreadNotifications > 99 ? "99+" : unreadNotifications}</em>
                  )}
                </button>
              )}

              {member && (
                <button
                  type="button"
                  className={activePage === "account" ? "is-active" : ""}
                  onClick={() => navigate("account")}
                >
                  <span><UserRound size={19} /></span>
                  <div><strong>{tr("Minha conta", "My account")}</strong><small>{tr("Perfil, fotografia e privacidade", "Profile, photo and privacy")}</small></div>
                </button>
              )}

              {!operator && <button
                type="button"
                className={activePage === "security" ? "is-active" : ""}
                onClick={() => navigate("security")}
              >
                <span><ShieldCheck size={19} /></span>
                <div><strong>{tr("Segurança", "Safety")}</strong><small>{tr("Como protegemos a comunidade", "How we protect the community")}</small></div>
              </button>}

              {!authenticated && (
                <button type="button" onClick={() => goTo("/acompanhar-pedido/")}>
                  <span><FileSearch size={19} /></span>
                  <div><strong>{tr("Acompanhar pedido", "Track request")}</strong><small>{tr("Consultar o estado da análise", "Check the review status")}</small></div>
                </button>
              )}
            </nav>

            <footer className="nk-mobile-menu__footer">
              {authenticated ? (
                <button type="button" className="nk-mobile-menu__logout" onClick={signOut}>
                  <LogOut size={18} /> {tr("Terminar sessão", "Sign out")}
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    className="nk-button nk-button--wine"
                    onClick={() => goTo("/pedir-acesso/")}
                  >
                    <UserPlus size={18} /> {tr("Pedir acesso", "Request access")}
                  </button>
                  <button
                    type="button"
                    className="nk-button nk-button--quiet"
                    onClick={() => navigate("login")}
                    disabled={sessionLoading}
                  >
                    <LogIn size={18} /> {tr("Entrar", "Sign in")}
                  </button>
                </>
              )}
              <small><LockKeyhole size={13} /> {tr("Ligação protegida", "Secure connection")}</small>
            </footer>
          </aside>
        </div>
      )}
    </header>
  );
}
