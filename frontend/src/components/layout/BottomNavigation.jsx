import { HeartHandshake, Home, MessageCircle, Search, UserRound } from "lucide-react";

const items = [
  { id: "home", label: "Início", icon: Home },
  { id: "discover", label: "Descobrir", icon: Search },
  { id: "matches", label: "Matches", icon: HeartHandshake },
  { id: "messages", label: "Mensagens", icon: MessageCircle },
  { id: "account", label: "Conta", icon: UserRound },
];

export default function BottomNavigation({ activePage, onNavigate }) {
  return (
    <nav className="nk-bottom-nav" aria-label="Navegação da aplicação">
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
            <Icon size={19} strokeWidth={active ? 2.3 : 1.8} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
