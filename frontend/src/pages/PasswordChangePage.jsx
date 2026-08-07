import { useEffect, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import { fetchSession } from "../services/api.js";
import { changeAccountPassword } from "../services/accountSecurityApi.js";

function firstError(errors, name) {
  const value = errors?.[name];
  return Array.isArray(value) ? value[0] : value || "";
}

function PasswordField({
  label,
  name,
  value,
  show,
  placeholder,
  error,
  onChange,
  onToggle,
  autoComplete,
}) {
  return (
    <label className="nk-password-change-field">
      <span>{label}</span>
      <div className={error ? "has-error" : ""}>
        <LockKeyhole size={18} />
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(event) => onChange(name, event.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required
        />
        <button
          type="button"
          onClick={onToggle}
          aria-label={show ? `Ocultar ${label.toLowerCase()}` : `Mostrar ${label.toLowerCase()}`}
        >
          {show ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
      {error && <small>{error}</small>}
    </label>
  );
}

export default function PasswordChangePage({ onBack, onLogin }) {
  const [checkingSession, setCheckingSession] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [errors, setErrors] = useState({});
  const [requestError, setRequestError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchSession({ signal: controller.signal })
      .then((session) => setAuthenticated(Boolean(session?.authenticated)))
      .catch((error) => {
        if (error.name !== "AbortError") setRequestError("Não foi possível confirmar a sua sessão.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setCheckingSession(false);
      });
    return () => controller.abort();
  }, []);

  const updateField = (name, value) => {
    if (name === "current_password") setCurrentPassword(value);
    if (name === "new_password") setNewPassword(value);
    if (name === "confirmation") setConfirmation(value);
    setErrors((current) => ({ ...current, [name]: undefined }));
    setRequestError("");
  };

  const validate = () => {
    const next = {};
    if (!currentPassword) next.current_password = "Escreva a sua palavra-passe atual.";
    if (newPassword.length < 8) next.new_password = "Use pelo menos 8 caracteres.";
    if (newPassword && newPassword === currentPassword) {
      next.new_password = "Escolha uma palavra-passe diferente da atual.";
    }
    if (newPassword !== confirmation) next.confirmation = "As palavras-passe não coincidem.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    setRequestError("");
    setErrors({});
    try {
      await changeAccountPassword({ currentPassword, newPassword, confirmation });
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        setAuthenticated(false);
      }
      setRequestError(error.message);
      setErrors(error.payload?.errors || {});
    } finally {
      setSubmitting(false);
    }
  };

  if (checkingSession) {
    return (
      <main className="nk-password-change nk-password-change--center">
        <LoaderCircle size={30} className="is-spinning" />
        <strong>A confirmar a sua sessão…</strong>
      </main>
    );
  }

  if (!authenticated) {
    return (
      <main className="nk-password-change nk-password-change--center">
        <span className="nk-password-change__status-icon"><LockKeyhole size={28} /></span>
        <h1>Entre para alterar a palavra-passe.</h1>
        <p>Esta área é reservada aos membros com sessão iniciada.</p>
        {requestError && <div className="nk-password-change-alert">{requestError}</div>}
        <button type="button" className="nk-button nk-button--wine" onClick={onLogin}>Entrar</button>
      </main>
    );
  }

  if (success) {
    return (
      <main className="nk-password-change">
        <header className="nk-password-change-topbar">
          <button type="button" onClick={onBack} className="nk-password-change-brand">
            <span>N</span><strong>NKATA</strong>
          </button>
          <span><ShieldCheck size={14} /> Conta protegida</span>
        </header>

        <section className="nk-password-change-success">
          <span><CheckCircle2 size={31} /></span>
          <small>Segurança atualizada</small>
          <h1>A sua palavra-passe foi alterada.</h1>
          <p>A sessão continua ativa. Pode voltar à sua conta e continuar normalmente.</p>
          <button type="button" className="nk-button nk-button--wine" onClick={onBack}>
            Voltar à minha conta
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="nk-password-change">
      <header className="nk-password-change-topbar">
        <button type="button" onClick={onBack} className="nk-password-change-brand">
          <span>N</span><strong>NKATA</strong>
        </button>
        <span><ShieldCheck size={14} /> Conta protegida</span>
      </header>

      <section className="nk-password-change-layout">
        <aside className="nk-password-change-intro">
          <button type="button" className="nk-password-change-back" onClick={onBack}>
            <ArrowLeft size={17} /> Voltar à conta
          </button>
          <span className="nk-eyebrow nk-eyebrow--dark"><ShieldCheck size={15} /> Segurança</span>
          <h1>Uma palavra-passe só sua.</h1>
          <p>Confirme a palavra-passe atual e escolha uma nova. O NKATA não envia nem guarda a sua palavra-passe em texto legível.</p>

          <div className="nk-password-change-note">
            <KeyRound size={21} />
            <div>
              <strong>A sua sessão não será terminada</strong>
              <span>Depois da alteração, continuará ligado neste dispositivo.</span>
            </div>
          </div>
        </aside>

        <section className="nk-password-change-card">
          <div className="nk-password-change-card__heading">
            <span>Alterar palavra-passe</span>
            <h2>Proteja o seu acesso</h2>
            <p>Use uma palavra-passe diferente das que utiliza noutros serviços.</p>
          </div>

          <form onSubmit={handleSubmit}>
            <PasswordField
              label="Palavra-passe atual"
              name="current_password"
              value={currentPassword}
              show={showCurrent}
              placeholder="A palavra-passe que usa agora"
              error={firstError(errors, "current_password")}
              onChange={updateField}
              onToggle={() => setShowCurrent((current) => !current)}
              autoComplete="current-password"
            />

            <PasswordField
              label="Nova palavra-passe"
              name="new_password"
              value={newPassword}
              show={showNew}
              placeholder="Pelo menos 8 caracteres"
              error={firstError(errors, "new_password")}
              onChange={updateField}
              onToggle={() => setShowNew((current) => !current)}
              autoComplete="new-password"
            />

            <PasswordField
              label="Confirmar nova palavra-passe"
              name="confirmation"
              value={confirmation}
              show={showConfirmation}
              placeholder="Repita a nova palavra-passe"
              error={firstError(errors, "confirmation")}
              onChange={updateField}
              onToggle={() => setShowConfirmation((current) => !current)}
              autoComplete="new-password"
            />

            <div className="nk-password-change-guidance">
              <ShieldCheck size={18} />
              <span>Evite nomes, datas fáceis, sequências numéricas e palavras-passe muito comuns.</span>
            </div>

            {requestError && <div className="nk-password-change-alert">{requestError}</div>}

            <button
              type="submit"
              className="nk-button nk-button--wine nk-password-change-submit"
              disabled={submitting || !currentPassword || !newPassword || !confirmation}
            >
              {submitting ? <LoaderCircle size={18} className="is-spinning" /> : <LockKeyhole size={18} />}
              {submitting ? "A atualizar…" : "Atualizar palavra-passe"}
            </button>
          </form>
        </section>
      </section>
    </main>
  );
}
