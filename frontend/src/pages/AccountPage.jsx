import { useEffect, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  Eye,
  EyeOff,
  Heart,
  LockKeyhole,
  LogOut,
  MapPin,
  RefreshCw,
  Save,
  ShieldCheck,
  UserRound,
} from "lucide-react";

const objectiveOptions = [
  { value: "RELACIONAMENTO_SERIO", label: "Relacionamento sério" },
  { value: "CONHECER_COM_INTENCAO", label: "Conhecer pessoas com intenção" },
  { value: "AMIZADE_EVOLUIR", label: "Amizade que pode evoluir" },
  { value: "CASAMENTO_FUTURO", label: "Casamento no futuro" },
];

const emptyForm = {
  nome_publico: "",
  cidade: "",
  objetivo: "",
  sobre_si: "",
  o_que_valoriza: "",
  o_que_nao_aceita: "",
};

function formatMemberDate(value) {
  if (!value) return "";

  return new Intl.DateTimeFormat("pt-MZ", {
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

function InterestItem({ profile, onOpen }) {
  return (
    <button type="button" className="nk-account-interest" onClick={() => onOpen(profile)}>
      <span className="nk-account-interest__photo">
        {profile.foto_url ? (
          <img src={profile.foto_url} alt={`Foto de ${profile.nome_publico}`} />
        ) : (
          <UserRound size={28} />
        )}
      </span>
      <span>
        <strong>
          {profile.nome_publico}
          {profile.idade ? `, ${profile.idade}` : ""}
        </strong>
        <small><MapPin size={12} /> {profile.cidade}</small>
      </span>
      <Heart size={17} fill="currentColor" />
    </button>
  );
}

export default function AccountPage({
  account,
  interests,
  loading,
  saving,
  error,
  success,
  onReload,
  onSave,
  onToggleVisibility,
  onOpenProfile,
  onSignOut,
}) {
  const [form, setForm] = useState(emptyForm);

  useEffect(() => {
    if (!account) return;

    setForm({
      nome_publico: account.nome_publico || "",
      cidade: account.cidade || "",
      objetivo: account.objetivo || "",
      sobre_si: account.sobre_si || "",
      o_que_valoriza: account.o_que_valoriza || "",
      o_que_nao_aceita: account.o_que_nao_aceita || "",
    });
  }, [account]);

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSave(form);
  };

  if (loading && !account) {
    return (
      <main className="nk-account">
        <div className="nk-shell nk-account__loading">
          <span />
          <div><em /><em /><em /></div>
        </div>
      </main>
    );
  }

  if (!account) {
    return (
      <main className="nk-account">
        <div className="nk-shell nk-account__empty">
          <UserRound size={32} />
          <h1>Não foi possível abrir a sua conta</h1>
          <p>{error || "Tente novamente dentro de alguns instantes."}</p>
          <button type="button" className="nk-button nk-button--wine" onClick={onReload}>
            Tentar novamente
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="nk-account">
      <section className="nk-account__intro">
        <div className="nk-shell nk-account__intro-inner">
          <div>
            <span className="nk-eyebrow nk-eyebrow--dark">
              <UserRound size={15} />
              A sua conta
            </span>
            <h1>O seu espaço no NKATA.</h1>
            <p>Atualize a apresentação, escolha quando o perfil fica visível e acompanhe as suas ligações.</p>
          </div>

          <button type="button" className="nk-account__reload" onClick={onReload} disabled={loading}>
            <RefreshCw size={17} className={loading ? "is-spinning" : ""} />
            Atualizar
          </button>
        </div>
      </section>

      <section className="nk-shell nk-account__layout">
        <aside className="nk-account__sidebar">
          <article className="nk-account-card">
            <div className="nk-account-card__photo">
              {account.foto_url ? (
                <img src={account.foto_url} alt={`Foto de ${account.nome_publico}`} />
              ) : (
                <UserRound size={52} strokeWidth={1.25} />
              )}
              <span><ShieldCheck size={15} /></span>
            </div>

            <h2>{account.nome_publico}</h2>
            <p><MapPin size={14} /> {account.cidade}</p>
            <small>{account.email}</small>

            <div className={`nk-account-card__visibility ${account.visivel ? "is-visible" : ""}`}>
              {account.visivel ? <Eye size={16} /> : <EyeOff size={16} />}
              <div>
                <strong>{account.visivel ? "Perfil visível" : "Perfil oculto"}</strong>
                <span>
                  {account.visivel
                    ? "Pode aparecer na área de perfis."
                    : "Não aparece para outros membros."}
                </span>
              </div>
            </div>

            <button
              type="button"
              className="nk-account-card__visibility-button"
              onClick={() => onToggleVisibility(!account.visivel)}
              disabled={saving}
            >
              {account.visivel ? <EyeOff size={17} /> : <Eye size={17} />}
              {account.visivel ? "Ocultar perfil" : "Mostrar perfil"}
            </button>
          </article>

          <div className="nk-account__stats">
            <article>
              <strong>{account.total_matches}</strong>
              <span>Matches</span>
            </article>
            <article>
              <strong>{account.total_interesses_enviados}</strong>
              <span>Interesses enviados</span>
            </article>
          </div>

          {account.membro_desde && (
            <div className="nk-account__member-since">
              <CalendarDays size={17} />
              <span>Membro desde {formatMemberDate(account.membro_desde)}</span>
            </div>
          )}
        </aside>

        <div className="nk-account__main">
          <form className="nk-account-form" onSubmit={handleSubmit}>
            <div className="nk-account-form__heading">
              <div>
                <h2>Editar perfil</h2>
                <p>Estas informações são apresentadas aos outros membros.</p>
              </div>
              <button type="submit" className="nk-button nk-button--wine" disabled={saving}>
                <Save size={17} />
                {saving ? "A guardar…" : "Guardar alterações"}
              </button>
            </div>

            {error && <div className="nk-account-form__message is-error">{error}</div>}
            {success && (
              <div className="nk-account-form__message is-success">
                <CheckCircle2 size={17} /> {success}
              </div>
            )}

            <div className="nk-account-form__grid">
              <label>
                <span>Nome apresentado</span>
                <input
                  type="text"
                  value={form.nome_publico}
                  onChange={(event) => updateField("nome_publico", event.target.value)}
                  maxLength={120}
                  required
                />
              </label>

              <label>
                <span>Cidade</span>
                <input
                  type="text"
                  value={form.cidade}
                  onChange={(event) => updateField("cidade", event.target.value)}
                  maxLength={100}
                  required
                />
              </label>

              <label className="nk-account-form__wide">
                <span>O que procura</span>
                <select
                  value={form.objetivo}
                  onChange={(event) => updateField("objetivo", event.target.value)}
                  required
                >
                  {objectiveOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>

              <label className="nk-account-form__wide">
                <span>Sobre si</span>
                <textarea
                  value={form.sobre_si}
                  onChange={(event) => updateField("sobre_si", event.target.value)}
                  maxLength={1800}
                  rows={5}
                />
                <small>{form.sobre_si.length}/1800</small>
              </label>

              <label className="nk-account-form__wide">
                <span>O que valoriza numa relação</span>
                <textarea
                  value={form.o_que_valoriza}
                  onChange={(event) => updateField("o_que_valoriza", event.target.value)}
                  maxLength={1800}
                  rows={4}
                />
                <small>{form.o_que_valoriza.length}/1800</small>
              </label>

              <label className="nk-account-form__wide">
                <span>O que não aceita</span>
                <textarea
                  value={form.o_que_nao_aceita}
                  onChange={(event) => updateField("o_que_nao_aceita", event.target.value)}
                  maxLength={1800}
                  rows={4}
                />
                <small>{form.o_que_nao_aceita.length}/1800</small>
              </label>
            </div>
          </form>

          <section className="nk-account-interests">
            <div className="nk-account-interests__heading">
              <div>
                <h2>Interesses enviados</h2>
                <p>Perfis em que demonstrou interesse.</p>
              </div>
              <span>{interests.length}</span>
            </div>

            {interests.length ? (
              <div className="nk-account-interests__list">
                {interests.map((profile) => (
                  <InterestItem key={profile.id} profile={profile} onOpen={onOpenProfile} />
                ))}
              </div>
            ) : (
              <div className="nk-account-interests__empty">
                <Heart size={22} />
                <span>Ainda não enviou nenhum interesse.</span>
              </div>
            )}
          </section>

          <section className="nk-account-security">
            <div>
              <span><LockKeyhole size={19} /></span>
              <div>
                <h2>Segurança da conta</h2>
                <p>A palavra-passe e os documentos de verificação não são apresentados no perfil.</p>
              </div>
            </div>

            <div className="nk-account-security__actions">
              <button
                type="button"
                onClick={() => window.location.assign("/minha-conta/alterar-senha/")}
              >
                Alterar palavra-passe
              </button>
              <button type="button" className="is-danger" onClick={onSignOut}>
                <LogOut size={16} /> Terminar sessão
              </button>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
