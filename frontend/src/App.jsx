import {
  ArrowRight,
  BadgeCheck,
  Bell,
  CheckCircle2,
  Clock3,
  Crown,
  Fingerprint,
  Heart,
  Home,
  Lock,
  MapPin,
  MessageCircle,
  Search,
  ShieldCheck,
  SlidersHorizontal,
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
    status: "Verificado",
    phrase: "Procuro algo maduro, com respeito, intenção clara e calma.",
    tone: "from-red-950 via-zinc-950 to-black"
  },
  {
    id: 2,
    name: "Mauro",
    age: 32,
    city: "Matola",
    intention: "Conhecer com intenção",
    initials: "M",
    status: "Analisado",
    phrase: "Valorizo família, estabilidade emocional e conversa honesta.",
    tone: "from-zinc-950 via-black to-red-950"
  },
  {
    id: 3,
    name: "Lina",
    age: 29,
    city: "Beira",
    intention: "Algo sério",
    initials: "L",
    status: "Seguro",
    phrase: "Quero conhecer alguém com propósito, respeito e visão de futuro.",
    tone: "from-neutral-950 via-zinc-900 to-black"
  }
];

const trustMetrics = [
  { label: "Perfis analisados", value: "24", icon: UsersRound },
  { label: "Interações sérias", value: "6", icon: Sparkles },
  { label: "Conversas protegidas", value: "3", icon: MessageCircle },
  { label: "Privacidade ativa", value: "100%", icon: Lock }
];

const securityPoints = [
  {
    title: "Entrada controlada",
    text: "Cada pedido passa por análise antes de ganhar visibilidade dentro da comunidade.",
    icon: Fingerprint
  },
  {
    title: "Perfis com intenção",
    text: "A plataforma destaca objetivo, cidade e contexto — não incentiva exposição desnecessária.",
    icon: BadgeCheck
  },
  {
    title: "Privacidade primeiro",
    text: "Documentos e dados sensíveis permanecem fora da área pública do produto.",
    icon: ShieldCheck
  }
];

function TrustBadge({ icon: Icon, children }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-3 py-2 text-[0.68rem] font-black uppercase tracking-[0.16em] text-white/72 backdrop-blur-xl">
      <Icon size={14} className="text-[#d7b46a]" />
      {children}
    </span>
  );
}

function ProfileCard({ profile, featured = false }) {
  return (
    <article
      className={`group overflow-hidden rounded-[2rem] border border-black/[0.06] bg-white shadow-[0_24px_80px_rgba(10,10,10,0.10)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_30px_100px_rgba(10,10,10,0.16)] ${
        featured ? "lg:scale-[1.02]" : ""
      }`}
    >
      <div className={`relative h-[19rem] overflow-hidden bg-gradient-to-br ${profile.tone}`}>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_26%_18%,rgba(200,16,46,0.38),transparent_34%),radial-gradient(circle_at_78%_12%,rgba(215,180,106,0.18),transparent_28%)]" />
        <div className="absolute inset-x-5 top-5 flex items-center justify-between">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-xs font-black text-white backdrop-blur-xl">
            <ShieldCheck size={15} /> {profile.status}
          </span>
          <span className="rounded-full border border-white/10 bg-black/24 px-3 py-2 text-xs font-bold text-white/72 backdrop-blur-xl">
            Premium
          </span>
        </div>

        <div className="absolute inset-0 grid place-items-center">
          <div className="relative grid h-28 w-28 place-items-center rounded-[2rem] border border-white/15 bg-white/10 text-5xl font-black text-white shadow-[0_28px_70px_rgba(0,0,0,0.38)] backdrop-blur-xl">
            <span className="absolute inset-2 rounded-[1.55rem] bg-[#c8102e]" />
            <span className="relative">{profile.initials}</span>
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black via-black/60 to-transparent p-5 pt-20 text-white">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h3 className="text-3xl font-black tracking-[-0.04em]">
                {profile.name}, {profile.age}
              </h3>
              <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-white/68">
                <MapPin size={15} /> {profile.city}
              </p>
            </div>
            <button className="grid h-12 w-12 place-items-center rounded-full bg-white text-black shadow-[0_18px_50px_rgba(255,255,255,0.18)] transition group-hover:scale-105">
              <Heart size={20} />
            </button>
          </div>
        </div>
      </div>

      <div className="space-y-4 p-5">
        <span className="inline-flex rounded-full bg-[#c8102e]/10 px-3 py-1.5 text-xs font-black text-[#9f0d24]">
          {profile.intention}
        </span>
        <p className="min-h-[3rem] text-sm leading-6 text-zinc-600">{profile.phrase}</p>

        <div className="grid grid-cols-[0.86fr_0.86fr_1.2fr] gap-2">
          <button className="rounded-2xl bg-zinc-100 py-3 text-sm font-black text-zinc-900 transition hover:bg-zinc-200">
            Guardar
          </button>
          <button className="rounded-2xl bg-black py-3 text-sm font-black text-white transition hover:bg-zinc-800">
            Interesse
          </button>
          <button className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#c8102e] py-3 text-sm font-black text-white shadow-[0_16px_45px_rgba(200,16,46,0.30)] transition hover:bg-[#9f0d24]">
            Ver <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </article>
  );
}

function MetricCard({ item }) {
  const Icon = item.icon;
  return (
    <article className="rounded-[1.65rem] border border-black/[0.06] bg-white p-5 shadow-[0_18px_55px_rgba(10,10,10,0.08)]">
      <div className="mb-5 grid h-12 w-12 place-items-center rounded-full bg-[#c8102e]/10 text-[#c8102e]">
        <Icon size={21} />
      </div>
      <strong className="block text-3xl font-black tracking-[-0.04em] text-zinc-950">{item.value}</strong>
      <span className="mt-1 block text-sm font-bold text-zinc-500">{item.label}</span>
    </article>
  );
}

function App() {
  return (
    <div className="min-h-screen bg-[#f8f6f3] text-zinc-950">
      <header className="sticky top-0 z-40 border-b border-black/[0.06] bg-[#f8f6f3]/88 backdrop-blur-2xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 md:h-20 md:px-8">
          <a className="inline-flex items-center gap-3 text-xl font-black tracking-[0.18em] md:text-2xl" href="#">
            <span className="grid h-9 w-9 place-items-center rounded-2xl bg-black text-sm tracking-normal text-white">
              N
            </span>
            NKATA
          </a>

          <nav className="hidden items-center gap-8 text-sm font-bold text-zinc-700 md:flex">
            <a className="transition hover:text-[#c8102e]" href="#descobrir">Descobrir</a>
            <a className="transition hover:text-[#c8102e]" href="#seguranca">Segurança</a>
            <a className="transition hover:text-[#c8102e]" href="#processo">Processo</a>
          </nav>

          <div className="flex items-center gap-2">
            <button className="hidden rounded-full border border-black/10 px-5 py-3 text-sm font-black text-zinc-800 transition hover:border-black/20 hover:bg-white md:inline-flex">
              Entrar
            </button>
            <button className="rounded-full bg-black px-5 py-3 text-sm font-black text-white shadow-[0_16px_45px_rgba(0,0,0,0.18)] transition hover:bg-[#c8102e]">
              Solicitar entrada
            </button>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden bg-black text-white">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_14%_18%,rgba(200,16,46,0.38),transparent_30%),radial-gradient(circle_at_86%_10%,rgba(215,180,106,0.18),transparent_26%),linear-gradient(135deg,rgba(255,255,255,0.08)_0,transparent_26%)]" />
          <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-[#f8f6f3] to-transparent" />

          <div className="relative mx-auto grid max-w-7xl gap-10 px-4 py-10 md:grid-cols-[0.9fr_1.1fr] md:px-8 md:py-20">
            <div className="flex flex-col justify-center">
              <div className="mb-5 flex flex-wrap gap-2">
                <TrustBadge icon={Crown}>Acesso controlado</TrustBadge>
                <TrustBadge icon={Lock}>Privacidade ativa</TrustBadge>
              </div>

              <h1 className="max-w-3xl text-5xl font-black leading-[0.92] tracking-[-0.065em] md:text-7xl">
                Relações sérias precisam de um ambiente seguro.
              </h1>

              <p className="mt-6 max-w-xl text-base leading-8 text-white/68 md:text-lg">
                NKATA é uma comunidade privada para adultos com intenção real. Entrada analisada, perfis organizados e conversas com mais confiança.
              </p>

              <div className="mt-8 grid max-w-lg grid-cols-1 gap-3 sm:grid-cols-2">
                <button className="inline-flex items-center justify-center gap-2 rounded-full bg-[#c8102e] px-6 py-4 text-sm font-black text-white shadow-[0_20px_70px_rgba(200,16,46,0.34)] transition hover:bg-[#9f0d24]">
                  Ver perfis seguros <ArrowRight size={17} />
                </button>
                <button className="rounded-full border border-white/15 bg-white/10 px-6 py-4 text-sm font-black text-white backdrop-blur-xl transition hover:bg-white/15">
                  Entender o processo
                </button>
              </div>

              <div className="mt-8 grid max-w-xl grid-cols-1 gap-3 sm:grid-cols-3">
                {["Verificação", "Moderação", "Privacidade"].map((item) => (
                  <div key={item} className="flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.06] px-3 py-3 text-sm font-bold text-white/72">
                    <CheckCircle2 size={17} className="text-[#d7b46a]" /> {item}
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <ProfileCard profile={featuredProfiles[0]} featured />
              <div className="hidden space-y-4 pt-10 lg:block">
                <div className="rounded-[2rem] border border-white/10 bg-white/[0.07] p-5 backdrop-blur-2xl">
                  <div className="mb-4 flex items-center justify-between">
                    <span className="text-xs font-black uppercase tracking-[0.16em] text-white/52">Triagem</span>
                    <span className="rounded-full bg-[#d7b46a]/15 px-3 py-1 text-xs font-black text-[#d7b46a]">Premium</span>
                  </div>
                  <h3 className="text-2xl font-black tracking-[-0.04em]">Comunidade com filtro e propósito.</h3>
                  <p className="mt-3 text-sm leading-6 text-white/58">
                    Menos ruído, mais intenção. O design privilegia confiança, segurança e organização.
                  </p>
                </div>
                <ProfileCard profile={featuredProfiles[1]} />
              </div>
            </div>
          </div>
        </section>

        <section className="relative z-10 mx-auto -mt-6 max-w-7xl px-4 pb-8 md:px-8 md:pb-16">
          <div className="grid gap-4 md:grid-cols-4">
            {trustMetrics.map((item) => (
              <MetricCard key={item.label} item={item} />
            ))}
          </div>
        </section>

        <section id="descobrir" className="mx-auto max-w-7xl px-4 pb-12 md:px-8 md:pb-20">
          <div className="mb-7 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <span className="text-xs font-black uppercase tracking-[0.18em] text-[#c8102e]">Descobrir</span>
              <h2 className="mt-2 text-4xl font-black tracking-[-0.055em] md:text-6xl">Perfis organizados, sem confusão.</h2>
              <p className="mt-3 max-w-xl text-sm leading-7 text-zinc-600 md:text-base">
                A interface mostra o essencial: pessoa, intenção, cidade, segurança e ação. Nada de exposição desnecessária.
              </p>
            </div>

            <div className="flex items-center gap-2 rounded-full border border-black/[0.06] bg-white p-2 shadow-[0_16px_50px_rgba(10,10,10,0.08)] md:min-w-96">
              <Search size={18} className="ml-3 text-zinc-400" />
              <input
                className="min-h-10 flex-1 bg-transparent text-sm font-semibold outline-none placeholder:text-zinc-400"
                placeholder="Pesquisar cidade ou intenção"
              />
              <button className="grid h-10 w-10 place-items-center rounded-full bg-zinc-100 text-zinc-700">
                <SlidersHorizontal size={17} />
              </button>
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            {featuredProfiles.map((profile) => (
              <ProfileCard key={profile.id} profile={profile} />
            ))}
          </div>
        </section>

        <section id="seguranca" className="bg-black px-4 py-12 text-white md:px-8 md:py-20">
          <div className="mx-auto grid max-w-7xl gap-8 md:grid-cols-[0.85fr_1.15fr]">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-xs font-black uppercase tracking-[0.14em] text-white/70">
                <Lock size={15} /> Segurança NKATA
              </span>
              <h2 className="mt-5 text-4xl font-black leading-[0.95] tracking-[-0.055em] md:text-6xl">
                Confiança não é detalhe. É estrutura.
              </h2>
              <p className="mt-5 max-w-lg text-sm leading-7 text-white/58 md:text-base">
                A experiência premium começa no controlo: quem entra, o que aparece, como interage e como a privacidade é preservada.
              </p>
            </div>

            <div className="grid gap-3">
              {securityPoints.map((point) => {
                const Icon = point.icon;
                return (
                  <article key={point.title} className="flex gap-4 rounded-[1.6rem] border border-white/10 bg-white/[0.06] p-5 backdrop-blur-xl">
                    <div className="grid h-12 w-12 flex-none place-items-center rounded-full bg-[#c8102e] shadow-[0_14px_40px_rgba(200,16,46,0.28)]">
                      <Icon size={20} />
                    </div>
                    <div>
                      <h3 className="font-black tracking-[-0.02em]">{point.title}</h3>
                      <p className="mt-1 text-sm font-medium leading-6 text-white/60">{point.text}</p>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section id="processo" className="mx-auto max-w-7xl px-4 py-12 md:px-8 md:py-20">
          <div className="grid gap-5 md:grid-cols-3">
            {[
              { step: "01", title: "Pedido de entrada", text: "A pessoa solicita acesso e fornece informação básica para análise.", icon: Clock3 },
              { step: "02", title: "Validação", text: "A comunidade mantém organização com revisão e controlo de perfis.", icon: ShieldCheck },
              { step: "03", title: "Interação segura", text: "Depois de aprovado, o utilizador descobre perfis e interage com intenção.", icon: MessageCircle }
            ].map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.step} className="rounded-[2rem] border border-black/[0.06] bg-white p-6 shadow-[0_18px_55px_rgba(10,10,10,0.08)]">
                  <div className="mb-8 flex items-center justify-between">
                    <span className="text-xs font-black uppercase tracking-[0.18em] text-zinc-400">{item.step}</span>
                    <div className="grid h-11 w-11 place-items-center rounded-full bg-black text-white">
                      <Icon size={19} />
                    </div>
                  </div>
                  <h3 className="text-2xl font-black tracking-[-0.04em]">{item.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-zinc-600">{item.text}</p>
                </article>
              );
            })}
          </div>
        </section>
      </main>

      <nav className="fixed bottom-3 left-3 right-3 z-50 grid grid-cols-5 gap-1 rounded-[1.7rem] border border-black/[0.08] bg-white/95 p-2 shadow-[0_24px_90px_rgba(0,0,0,0.20)] backdrop-blur-2xl md:hidden">
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
              className={`grid min-h-14 place-items-center rounded-2xl text-[0.66rem] font-black transition ${
                index === 1 ? "bg-[#c8102e]/10 text-[#c8102e]" : "text-zinc-600 hover:bg-zinc-100"
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
