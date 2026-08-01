import { useState } from "react";
import {
  ArrowLeft,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";

export default function LoginPage({ onBack, onSubmit, loading, error }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSubmit({ email: email.trim(), password });
  };

  return (
    <main className="nk-login-page">
      <div className="nk-shell nk-login-page__layout">
        <section className="nk-login-page__intro">
          <button type="button" className="nk-profile-detail__back" onClick={onBack}>
            <ArrowLeft size={18} />
            Voltar
          </button>

          <span className="nk-eyebrow nk-eyebrow--dark">
            <ShieldCheck size={15} />
            Área de membros
          </span>

          <h1>Bem-vindo de volta.</h1>
          <p>
            Entre para consultar os seus interesses, matches e mensagens.
          </p>

          <div className="nk-login-page__note">
            <LockKeyhole size={20} />
            <div>
              <strong>Os seus dados ficam protegidos</strong>
              <span>O NKATA não mostra o seu email nem o seu telefone nos perfis.</span>
            </div>
          </div>
        </section>

        <section className="nk-login-card">
          <div className="nk-login-card__heading">
            <span>Entrar</span>
            <h2>Aceda à sua conta</h2>
          </div>

          <form onSubmit={handleSubmit} className="nk-login-form">
            <label>
              <span>Email</span>
              <div className="nk-login-field">
                <Mail size={18} />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="seuemail@exemplo.com"
                  autoComplete="email"
                  required
                />
              </div>
            </label>

            <label>
              <span>Palavra-passe</span>
              <div className="nk-login-field">
                <LockKeyhole size={18} />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="A sua palavra-passe"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? "Ocultar palavra-passe" : "Mostrar palavra-passe"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>

            {error && <div className="nk-login-form__error">{error}</div>}

            <button
              type="submit"
              className="nk-button nk-button--wine nk-login-form__submit"
              disabled={loading || !email.trim() || !password}
            >
              {loading ? "A entrar…" : "Entrar"}
            </button>

            <a href="/recuperar-senha/" className="nk-login-form__forgot">
              Esqueci a palavra-passe
            </a>
          </form>

          <div className="nk-login-card__footer">
            <span>Ainda não faz parte?</span>
            <a href="/solicitar-entrada/">Solicitar entrada</a>
          </div>
        </section>
      </div>
    </main>
  );
}
