import { useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  LoaderCircle,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { requestPasswordReset } from "../services/passwordResetApi.js";
import NkataLogo from "../components/brand/NkataLogo.jsx";

export default function PasswordResetPage({ onBack, onLogin }) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!email.trim()) return;

    setLoading(true);
    setError("");
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (requestError) {
      setError(requestError.message || "Não foi possível enviar o pedido agora.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="nk-password-page">
      <header className="nk-password-topbar">
        <button type="button" className="nk-password-brand" onClick={onBack}>
          <NkataLogo /><strong>NKATA</strong>
        </button>
        <span><LockKeyhole size={14} /> Ligação protegida</span>
      </header>

      <section className="nk-password-layout">
        <div className="nk-password-intro">
          <button type="button" className="nk-password-back" onClick={onLogin}>
            <ArrowLeft size={16} /> Voltar a entrar
          </button>
          <span className="nk-eyebrow nk-eyebrow--dark"><ShieldCheck size={15} /> Recuperar acesso</span>
          <h1>Volte à sua conta com segurança.</h1>
          <p>
            Indique o email usado no NKATA. Se existir uma conta associada, enviaremos um link temporário para criar uma nova palavra-passe.
          </p>
        </div>

        <section className="nk-password-card">
          {sent ? (
            <div className="nk-password-success">
              <span><CheckCircle2 size={27} /></span>
              <small>Pedido recebido</small>
              <h2>Consulte o seu email.</h2>
              <p>
                Se existir uma conta associada a <strong>{email.trim()}</strong>, receberá as instruções para criar uma nova palavra-passe.
              </p>
              <button type="button" className="nk-button nk-button--wine" onClick={onLogin}>
                Voltar a entrar
              </button>
              <button type="button" className="nk-password-link" onClick={() => setSent(false)}>
                Usar outro email
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="nk-password-card__heading">
                <span>Palavra-passe</span>
                <h2>Recupere o acesso</h2>
                <p>Enviaremos apenas instruções de recuperação. Nunca pedimos a sua palavra-passe por email.</p>
              </div>

              <label className="nk-password-field">
                <span>Email</span>
                <div>
                  <Mail size={18} />
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => { setEmail(event.target.value); setError(""); }}
                    placeholder="seuemail@exemplo.com"
                    autoComplete="email"
                    required
                  />
                </div>
              </label>

              {error && <div className="nk-password-alert">{error}</div>}

              <button
                type="submit"
                className="nk-button nk-button--wine nk-password-submit"
                disabled={loading || !email.trim()}
              >
                {loading ? <LoaderCircle size={18} className="is-spinning" /> : <Mail size={18} />}
                {loading ? "A enviar…" : "Enviar instruções"}
              </button>
            </form>
          )}
        </section>
      </section>
    </main>
  );
}
