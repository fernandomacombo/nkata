import {
  Bell,
  Crown,
  Eye,
  Heart,
  Home,
  Lock,
  MessageCircle,
  Search,
  ShieldCheck,
  Sparkles,
  UserRound,
  UsersRound
} from "lucide-react";

const featuredProfiles = [
  {
    id: 1,
    name: "Ana",
    age: 27,
    city: "Maputo",
    intention: "Relacionamento sério",
    initials: "A",
    tone: "from-rose-950 via-zinc-950 to-black"
  },
  {
    id: 2,
    name: "Mauro",
    age: 32,
    city: "Matola",
    intention: "Conhecer com intenção",
    initials: "M",
    tone: "from-zinc-900 via-black to-red-950"
  },
  {
    id: 3,
    name: "Lina",
    age: 29,
    city: "Beira",
    intention: "Algo sério",
    initials: "L",
    tone: "from-neutral-950 via-zinc-900 to-black"
  }
];

const actions = [
  { label: "Perfis", icon: UsersRound, value: "24" },
  { label: "Matches", icon: Sparkles, value: "6" },
  { label: "Mensagens", icon: MessageCircle, value: "3" },
  { label: "Privacidade", icon: Lock, value: "100%" }
];

function ProfileCard({ profile, active }) {
  return (
    <article
      className={`premium-card group overflow-hidden rounded-[2rem] border border-white/10 bg-white shadow-soft transition duration-300 ${
        active ? "md:scale-[1.02]" : "opacity-95"
      }`}
    >
      <div className={`relative h-72 bg-gradient-to-br ${profile.tone}`}>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(200,16,46,0.30),transparent_34%)]" />
        <div className="absolute left-5 top-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-xs font-bold text-white backdrop-blur-xl">
          <ShieldCheck size={15} /> Verificado
        </div>
        <div className="absolute inset-0 grid place-items-center">
          <div className="grid h-28 w-28 place-items-center rounded-[2rem] bg-red-700 text-5xl font-black text-white shadow-premium">
            {profile.initials}
          </div>
        </div>
        <div className="absolute bottom-5 left-5 right-5 flex items-end justify-between text-white">
          <div>
            <h3 className="text-3xl font-black tracking-tight">
              {profile.name}, {profile.age}
            </h3>
            <p className="text-sm font-semibold text-white/68">{profile.city}</p>
          </div>
          <button className="grid h-12 w-12 place-items-center rounded-full bg-white text-black shadow-premium transition group-hover:scale-105">
            <Heart size={20} />
          </button>
        </div>
      </div>

      <div className="space-y-4 p-5">
        <span className="inline-flex rounded-full bg-red-50 px-3 py-1 text-xs font-black text-red-700">
          {profile.intention}
        </span>
        <p className="text-sm leading-6 text-zinc-600">
          Perfil analisado pela comunidade NKATA. Conversas protegidas e intenção clara antes de qualquer aproximação.
        </p>
        <div className="grid grid-cols-3 gap-2">
          <button className="rounded-2xl bg-zinc-100 py-3 text-sm font-black text-zinc-900">♡</button>
          <button className="rounded-2xl bg-black py-3 text-sm font-black text-white">✦</button>
          <button className="rounded-2xl bg-red-700 py-3 text-sm font-black text-white">Ver</button>
        </div>
      </div>
    </article>
  );
}

function App() {
  return (
    <div className="min-h-screen bg-[#f8f6f3] text-zinc-950">
      <header className="sticky top-0 z-40 border-b border-black/5 bg-white/85 backdrop-blur-2xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 md:h-20 md:px-8">
          <a className="text-xl font-black tracking-[0.18em] md:text-2xl" href="#">
            <span className="text-red-700">N</span>KATA
          </a>

          <nav className="hidden items-center gap-8 text-sm font-bold text-zinc-700 md:flex">
            <a href="#descobrir">Descobrir</a>
            <a href="#premium">Premium</a>
            <a href="#seguranca">Segurança</a>
          </nav>

          <div className="flex items-center gap-2">
            <button className="hidden rounded-full border border-black/10 px-5 py-3 text-sm font-black md:inline-flex">
              Entrar
            </button>
            <button className="rounded-full bg-black px-5 py-3 text-sm font-black text-white shadow-soft">
              Solicitar entrada
            </button>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden bg-black text-white">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(200,16,46,0.35),transparent_30%),radial-gradient(circle_at_85%_10%,rgba(215,180,106,0.18),transparent_28%)]" />
          <div className="relative mx-auto grid max-w-7xl gap-10 px-4 py-10 md:grid-cols-[0.92fr_1.08fr] md:px-8 md:py-20">
            <div className="flex flex-col justify-center">
              <span className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-white/12 bg-white/8 px-4 py-2 text-xs font-black uppercase tracking-[0.14em] text-white/80">
                <Crown size={15} className="text-yellow-300" /> Acesso controlado
              </span>

              <h1 className="max-w-3xl text-5xl font-black leading-[0.92] tracking-[-0.06em] md:text-7xl">
                Relações sérias merecem uma experiência premium.
              </h1>

              <p className="mt-6 max-w-xl text-base leading-8 text-white/68 md:text-lg">
                NKATA não é para qualquer um. É uma comunidade organizada, privada e criada para adultos com intenção real.
              </p>

              <div className="mt-8 grid max-w-md grid-cols-1 gap-3 sm:grid-cols-2">
                <button className="rounded-full bg-red-700 px-6 py-4 text-sm font-black text-white shadow-premium">
                  Ver perfis
                </button>
                <button className="rounded-full border border-white/15 bg-white/10 px-6 py-4 text-sm font-black text-white backdrop-blur-xl">
                  Como funciona
                </button>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <ProfileCard profile={featuredProfiles[0]} active />
              <div className="hidden space-y-4 pt-10 md:block">
                <ProfileCard profile={featuredProfiles[1]} />
              </div>
            </div>
          </div>
        </section>

        <section id="premium" className="mx-auto max-w-7xl px-4 py-8 md:px-8 md:py-16">
          <div className="grid gap-4 md:grid-cols-4">
            {actions.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.label} className="rounded-[1.6rem] border border-black/5 bg-white p-5 shadow-soft">
                  <div className="mb-5 grid h-12 w-12 place-items-center rounded-full bg-red-50 text-red-700">
                    <Icon size={21} />
                  </div>
                  <strong className="block text-3xl font-black tracking-tight">{item.value}</strong>
                  <span className="text-sm font-bold text-zinc-500">{item.label}</span>
                </article>
              );
            })}
          </div>
        </section>

        <section id="descobrir" className="mx-auto max-w-7xl px-4 pb-10 md:px-8 md:pb-20">
          <div className="mb-7 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <span className="text-xs font-black uppercase tracking-[0.16em] text-red-700">Descobrir</span>
              <h2 className="mt-2 text-4xl font-black tracking-[-0.05em] md:text-6xl">Perfis organizados.</h2>
              <p className="mt-3 max-w-xl text-sm leading-7 text-zinc-600 md:text-base">
                Interface feita para ir direto ao que interessa: pessoas, intenção, segurança e conversa.
              </p>
            </div>

            <div className="flex items-center gap-2 rounded-full border border-black/8 bg-white p-2 shadow-soft md:min-w-80">
              <Search size={18} className="ml-3 text-zinc-400" />
              <input
                className="min-h-10 flex-1 bg-transparent text-sm font-semibold outline-none"
                placeholder="Pesquisar cidade ou intenção"
              />
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            {featuredProfiles.map((profile) => (
              <ProfileCard key={profile.id} profile={profile} />
            ))}
          </div>
        </section>

        <section id="seguranca" className="bg-black px-4 py-12 text-white md:px-8 md:py-20">
          <div className="mx-auto grid max-w-7xl gap-8 md:grid-cols-[0.9fr_1.1fr]">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/8 px-4 py-2 text-xs font-black uppercase tracking-[0.14em] text-white/70">
                <Lock size={15} /> Privacidade
              </span>
              <h2 className="mt-5 text-4xl font-black leading-[0.95] tracking-[-0.05em] md:text-6xl">
                Acesso sério. Dados protegidos.
              </h2>
            </div>

            <div className="grid gap-3">
              {[
                "Perfis analisados antes de aparecerem publicamente.",
                "Telefone, email e documentos fora da área pública.",
                "Matches e conversas com controlo de acesso.",
                "Design premium para uma comunidade mais seletiva."
              ].map((text) => (
                <div key={text} className="flex items-center gap-4 rounded-[1.4rem] border border-white/10 bg-white/6 p-4">
                  <div className="grid h-10 w-10 place-items-center rounded-full bg-red-700">
                    <ShieldCheck size={18} />
                  </div>
                  <p className="text-sm font-semibold leading-6 text-white/72">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <nav className="fixed bottom-3 left-3 right-3 z-50 grid grid-cols-5 gap-1 rounded-[1.7rem] border border-black/8 bg-white/94 p-2 shadow-premium backdrop-blur-2xl md:hidden">
        {[
          { label: "Início", icon: Home },
          { label: "Perfis", icon: Heart },
          { label: "Matches", icon: Sparkles },
          { label: "Conta", icon: UserRound },
          { label: "Avisos", icon: Bell }
        ].map((item, index) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              className={`grid min-h-14 place-items-center rounded-2xl text-[0.66rem] font-black ${
                index === 1 ? "bg-red-50 text-red-700" : "text-zinc-600"
              }`}
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

export default App;
