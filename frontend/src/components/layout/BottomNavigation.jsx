import {
  CirclePlay,
  HeartHandshake,
  Home,
  Search,
  UserRound,
} from "lucide-react";

const items = [
  { id: "home", label: { PT: "Início", EN: "Home" }, icon: Home },
  { id: "discover", label: { PT: "Perfis", EN: "Profiles" }, icon: Search },
  { id: "moments", label: { PT: "Momentos", EN: "Moments" }, icon: CirclePlay },
  { id: "matches", label: { PT: "Matches", EN: "Matches" }, icon: HeartHandshake },
  { id: "account", label: { PT: "Conta", EN: "Account" }, icon: UserRound },
];

export default function BottomNavigation({
  activePage,
  onNavigate,
  unreadMatches = 0,
  language = "PT",
}) {
  return (
    <nav className="nk-bottom-nav" aria-label="Navegação da aplicação">
      {items.map((item) => {
        const Icon = item.icon;
        const active = activePage === item.id;
        const badgeCount = item.id === "matches" ? unreadMatches : 0;

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
            <span>{item.label[language] || item.label.PT}</span>
          </button>
        );
      })}
    </nav>
  );
}
