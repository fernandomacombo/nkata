import { useEffect, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
import {
  confirmPasswordReset,
  validatePasswordReset,
} from "../services/passwordResetApi.js";

function firstError(errors, name) {
  const value = errors?.[name];
  return Array.isArray(value) ? value[0] : value || "";
}

export default function PasswordResetConfirmPage({ uid, token, onBack, onLogin, onRestart }) {
  const [status, setStatus] = useState("loading");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [requestError, setRequestError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    validatePasswordReset(uid, token, { signal: controller.signal })
      .then(() => setStatus("form"))
      .catch((error) => {
        if (error.name !== "AbortError") {
          setRequestError(error.message || "Este link já não é válido.");
          setStatus("invalid");
        }
      });
    return () => controller.abort();
  }, [uid, token]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nextErrors = {};
    if (password.length < 8) nextErrors.password = "Use pelo menos 8 caracteres.";
    if (password !== confirmation) nextErrors.confirmation = "As palavras-passe não coincidem.";
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }

    setSubmitting(true);
    setErrors({});
    setRequestError("");
    try {
      await confirmPasswordReset(uid, token, { password, confirmation });
      setStatus("success");
    } catch (error) {
      setRequestError(error.message || "Não foi possível atualizar a palavra-passe.");
      setErrors(error.payload?.errors || {});
      if (error.status === 400 && !error.payload?.errors) setStatus("invalid");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="nk-password-page">
      <header className="nk-password-topbar">
        <button type="button" className="nk-password-brand" onClick={onBack}>
          <span>N</span><strong>NKATA</strong>
        </button>
        <span><LockKeyhole size={14} /> Ligação protegida</span>
      </header>

      <section className="nk-password-layout">
        <div className="nk-password-intro">
          <button type="button" className="nk-password-back" onClick={onLogin}>
            <ArrowLeft size={16} /> Voltar a entrar
          </button>
          <span className="nk-eyebrow nk-eyebrow--dark"><ShieldCheck size={15} /> Nova palavra-passe</span>
          <h1>Proteja novamente a sua conta.</h1>
          <p>Escolha uma palavra-passe forte e diferente das que usa noutros serviços.</p>
        </div>

        <section className="nk-password-card">
          {status === "loading" && (
            <div className="nk-password-center">
              <LoaderCircle size={30} className="is-spinning" />
              <strong>A verificar o link…</strong>
            </div>
          )}

          {status === "invalid" && (
            <div className="nk-password-success nk-password-success--invalid">
              <span><LockKeyhole size={27} /></span>
              <small>Link indisponível</small>
              <h2>Este link já não pode ser usado.</h2>
              <p>{requestError || "Peça uma nova recuperação para continuar com segurança."}</p>
              <button type="button" className="nk-button nk-button--wine" onClick={onRestart}>
                Pedir novo link
              </button>
            </div>
          )}

          {status === "success" && (
            <div className="nk-password-success">
              <span><CheckCircle2 size={27} /></span>
              <small>Concluído</small>
              <h2>Palavra-passe atualizada.</h2>
              <p>Já pode entrar no NKATA usando a nova palavra-passe.</p>
              <button type="button" className="nk-button nk-button--wine" onClick={onLogin}>
                Entrar na conta
              </button>
            </div>
          )}

          {status === "form" && (
            <form onSubmit={handleSubmit}>
              <div className="nk-password-card__heading">
                <span>Segurança</span>
                <h2>Crie uma nova palavra-passe</h2>
                <p>O link deixa de funcionar depois desta alteração.</p>
              </div>

              <label className="nk-password-field">
                <span>Nova palavra-passe</span>
                <div>
                  <LockKeyhole size={18} />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(event) => {
                      setPassword(event.target.value);
                      setErrors((current) => ({ ...current, password: undefined }));
                    }}
                    placeholder="Pelo menos 8 caracteres"
                    autoComplete="new-password"
                    required
                  />
                  <button type="button" onClick={() => setShowPassword((current) => !current)} aria-label={showPassword ? "Ocultar palavra-passe" : "Mostrar palavra-passe"}>
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {firstError(errors, "password") && <small className="nk-password-error">{firstError(errors, "password")}</small>}
              </label>

              <label className="nk-password-field">
                <span>Confirmar palavra-passe</span>
                <div>
                  <LockKeyhole size={18} />
                  <input
                    type={showConfirmation ? "text" : "password"}
                    value={confirmation}
                    onChange={(event) => {
                      setConfirmation(event.target.value);
                      setErrors((current) => ({ ...current, confirmation: undefined }));
                    }}
                    placeholder="Repita a nova palavra-passe"
                    autoComplete="new-password"
                    required
                  />
                  <button type="button" onClick={() => setShowConfirmation((current) => !current)} aria-label={showConfirmation ? "Ocultar confirmação" : "Mostrar confirmação"}>
                    {showConfirmation ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {firstError(errors, "confirmation") && <small className="nk-password-error">{firstError(errors, "confirmation")}</small>}
              </label>

              {requestError && <div className="nk-password-alert">{requestError}</div>}

              <button type="submit" className="nk-button nk-button--wine nk-password-submit" disabled={submitting}>
                {submitting ? <LoaderCircle size={18} className="is-spinning" /> : <LockKeyhole size={18} />}
                {submitting ? "A guardar…" : "Guardar nova palavra-passe"}
              </button>
            </form>
          )}
        </section>
      </section>
    </main>
  );
}
