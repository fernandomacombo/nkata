import {
  CirclePlay,
  MessageCircle,
  Home,
  Search,
  UserRound,
} from "lucide-react";

const items = [
  { id: "home", label: { PT: "Início", EN: "Home" }, icon: Home },
  { id: "discover", label: { PT: "Perfis", EN: "Profiles" }, icon: Search },
  { id: "moments", label: { PT: "Momentos", EN: "Moments" }, icon: CirclePlay },
  { id: "chats", label: { PT: "Chats", EN: "Chats" }, icon: MessageCircle },
  { id: "account", label: { PT: "Conta", EN: "Account" }, icon: UserRound },
];

export default function BottomNavigation({
  activePage,
  onNavigate,
  language = "PT",
}) {
  const english = language === "EN";
  return (
    <nav className="nk-bottom-nav" aria-label={english ? "App navigation" : "Navegação da aplicação"}>
      {items.map((item) => {
        const Icon = item.icon;
        const active = activePage === item.id;

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
            </span>
            <span>{item.label[language] || item.label.PT}</span>
          </button>
        );
      })}
    </nav>
  );
}
