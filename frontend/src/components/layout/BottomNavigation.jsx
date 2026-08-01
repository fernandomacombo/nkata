import { Bookmark, HeartHandshake, Home, Search, UserRound } from "lucide-react";

const items = [
  { id: "home", label: "Início", icon: Home },
  { id: "discover", label: "Perfis", icon: Search },
  { id: "saved", label: "Guardados", icon: Bookmark },
  { id: "matches", label: "Matches", icon: HeartHandshake },
  { id: "account", label: "Conta", icon: UserRound },
];

export default function BottomNavigation({
  activePage,
  onNavigate,
  savedCount = 0,
  unreadMatches = 0,
}) {
  return (
    <nav className="nk-bottom-nav" aria-label="Navegação da aplicação">
      {items.map((item) => {
        const Icon = item.icon;
        const active = activePage === item.id;
        const badgeCount = item.id === "saved"
          ? savedCount
          : item.id === "matches"
            ? unreadMatches
            : 0;

        return (
          <button
            key={item.id}
            type="button"
            className={active ? "is-active" : ""}
            onClick={() => onNavigate(item.id)}
            aria-current={active ? "page" : undefined}
          >
            <span className="nk-bottom-nav__icon">
              <Icon size={19} strokeWidth={active ? 2.3 : 1.8} />
              {badgeCount > 0 && (
                <em>{badgeCount > 9 ? "9+" : badgeCount}</em>
              )}
            </span>
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
