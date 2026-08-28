import { useEffect, useState } from "react";
import {
  ArrowLeft,
  BadgeCheck,
  Check,
  ClipboardCopy,
  Clock3,
  FileSearch,
  LoaderCircle,
  LockKeyhole,
  Mail,
  MailCheck,
  RefreshCw,
  SearchCheck,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { fetchAccessRequestStatus, requestAccessCodeRecovery } from "../services/api.js";

const LOOKUP_KEY = "nkata_access_request_lookup";

const stages = [
  { number: 1, title: "Recebido", text: "O pedido chegou à equipa." },
  { number: 2, title: "Em análise", text: "Os dados estão a ser confirmados." },
  { number: 3, title: "Decisão", text: "A equipa conclui a avaliação." },
  { number: 4, title: "Acesso", text: "A conta aprovada fica disponível." },
];

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-MZ", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function ResultIcon({ tone }) {
  if (tone === "success") return <BadgeCheck size={31} />;
  if (tone === "attention" || tone === "closed") return <TriangleAlert size={29} />;
  if (tone === "review") return <SearchCheck size={29} />;
  return <Clock3 size={29} />;
}

export default function AccessStatusPage({ onBack, onRequest, onLogin }) {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [recovering, setRecovering] = useState(false);
  const [recoveryMessage, setRecoveryMessage] = useState("");

  const lookup = async (values = { email, code }) => {
    const normalizedEmail = String(values.email || "").trim().toLowerCase();
    const normalizedCode = String(values.code || "").trim();

    if (!/^\S+@\S+\.\S+$/.test(normalizedEmail)) {
      setError("Informe o mesmo email usado no pedido.");
      return;
    }

    if (normalizedCode.length < 30) {
      setError("Informe o código privado completo.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const payload = await fetchAccessRequestStatus({
        email: normalizedEmail,
        code: normalizedCode,
      });
      setEmail(normalizedEmail);
      setCode(normalizedCode);
      setResult(payload);
      window.sessionStorage.setItem(
        LOOKUP_KEY,
        JSON.stringify({ email: normalizedEmail, code: normalizedCode }),
      );
    } catch (requestError) {
      setResult(null);
      setError(requestError.message || "Não foi possível consultar o pedido agora.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    try {
      const saved = JSON.parse(window.sessionStorage.getItem(LOOKUP_KEY) || "null");
      if (saved?.email && saved?.code) {
        setEmail(saved.email);
        setCode(saved.code);
        lookup(saved);
      }
    } catch {
      window.sessionStorage.removeItem(LOOKUP_KEY);
    }
    // Executa apenas ao abrir a página.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = (event) => {
    event.preventDefault();
    lookup();
  };

  const recoverCode = async () => {
    const normalizedEmail = String(email || "").trim().toLowerCase();
    if (!/^\S+@\S+\.\S+$/.test(normalizedEmail)) {
      setError("Informe primeiro o email usado no pedido.");
      return;
    }
    setRecovering(true);
    setError("");
    setRecoveryMessage("");
    try {
      const payload = await requestAccessCodeRecovery(normalizedEmail);
      setEmail(normalizedEmail);
      setRecoveryMessage(payload?.message || "Se existir um pedido, o código será enviado por email.");
    } catch (requestError) {
      setError(requestError.message || "Não foi possível enviar o código agora.");
    } finally {
      setRecovering(false);
    }
  };

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(result?.codigo || code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  const resetLookup = () => {
    setResult(null);
    setError("");
    setCopied(false);
    setEmail("");
    setCode("");
    window.sessionStorage.removeItem(LOOKUP_KEY);
  };

  return (
    <main className="nk-request-status">
      <section className="nk-request-status__hero">
        <div className="nk-shell nk-request-status__hero-inner">
          <button type="button" className="nk-access-back" onClick={onBack}>
            <ArrowLeft size={18} /> Voltar
          </button>

          <div className="nk-request-status__intro">
            <span className="nk-eyebrow nk-eyebrow--dark">
              <FileSearch size={15} /> Acompanhamento privado
            </span>
            <h1>Acompanhe o seu pedido.</h1>
            <p>
              Use o email informado e o código privado recebido no final do pedido.
            </p>
          </div>

          <aside>
            <LockKeyhole size={19} />
            <span>
              <strong>A consulta é confidencial.</strong>
              <small>Nenhuma fotografia ou documento será apresentado aqui.</small>
            </span>
          </aside>
        </div>
      </section>

      <section className="nk-shell nk-request-status__workspace">
        {!result ? (
          <div className="nk-request-status__layout">
            <form className="nk-request-status__form" onSubmit={handleSubmit}>
              <header>
                <span><SearchCheck size={23} /></span>
                <div>
                  <small>Consultar pedido</small>
                  <h2>Veja em que ponto está a análise.</h2>
                  <p>Os dois dados devem corresponder ao mesmo pedido.</p>
                </div>
              </header>

              <label>
                <span>Email usado no pedido</span>
                <div className="nk-request-status__input">
                  <Mail size={18} />
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => {
                      setEmail(event.target.value);
                      setError("");
                      setRecoveryMessage("");
                    }}
                    autoComplete="email"
                    placeholder="nome@exemplo.com"
                  />
                </div>
              </label>

              <button
                type="button"
                className="nk-request-status__recover"
                onClick={recoverCode}
                disabled={recovering}
              >
                {recovering ? <LoaderCircle size={17} className="is-spinning" /> : <MailCheck size={17} />}
                {recovering ? "A enviar…" : "Perdeu o código? Reenviar por email"}
              </button>

              {recoveryMessage && (
                <div className="nk-request-status__recovery-message" role="status">
                  {recoveryMessage}
                </div>
              )}

              <label>
                <span>Código privado</span>
                <div className="nk-request-status__input">
                  <ShieldCheck size={18} />
                  <input
                    value={code}
                    onChange={(event) => {
                      setCode(event.target.value);
                      setError("");
                    }}
                    autoComplete="off"
                    spellCheck="false"
                    placeholder="00000000-0000-0000-0000-000000000000"
                  />
                </div>
              </label>

              {error && <div className="nk-request-status__error" role="alert">{error}</div>}

              <button type="submit" className="nk-button nk-button--wine" disabled={loading}>
                {loading ? <LoaderCircle size={18} className="is-spinning" /> : <SearchCheck size={18} />}
                {loading ? "A consultar…" : "Consultar pedido"}
              </button>

              <button type="button" className="nk-request-status__new" onClick={onRequest}>
                Ainda não enviou um pedido? Pedir acesso
              </button>
            </form>

            <aside className="nk-request-status__help">
              <span><ShieldCheck size={24} /></span>
              <h3>Onde encontro o código?</h3>
              <p>
                O código aparece no ecrã e é enviado ao email depois do pedido. Se fechar
                a página, pode reenviá-lo usando o mesmo endereço.
              </p>
              <div>
                <Check size={16} />
                <span>O código não dá acesso à sua conta</span>
              </div>
              <div>
                <Check size={16} />
                <span>Documentos e fotografias continuam ocultos</span>
              </div>
              <div>
                <Check size={16} />
                <span>A equipa nunca pedirá a sua palavra-passe</span>
              </div>
            </aside>
          </div>
        ) : (
          <section className={`nk-request-status__result is-${result.tone || "waiting"}`}>
            <header>
              <span className="nk-request-status__result-icon">
                <ResultIcon tone={result.tone} />
              </span>
              <div>
                <small>{result.status_label}</small>
                <h2>{result.title}</h2>
                <p>{result.message}</p>
              </div>
              <button
                type="button"
                className="nk-request-status__refresh"
                onClick={() => lookup()}
                disabled={loading}
              >
                <RefreshCw size={17} className={loading ? "is-spinning" : ""} />
                {loading ? "A atualizar…" : "Atualizar"}
              </button>
            </header>

            {error && <div className="nk-request-status__error" role="alert">{error}</div>}

            <div className="nk-request-status__timeline" aria-label="Progresso do pedido">
              {stages.map((stage) => {
                const complete = stage.number < Number(result.stage || 1);
                const active = stage.number === Number(result.stage || 1);
                return (
                  <article
                    key={stage.number}
                    className={`${complete ? "is-complete" : ""} ${active ? "is-active" : ""}`}
                  >
                    <span>{complete ? <Check size={17} /> : stage.number}</span>
                    <div>
                      <strong>{stage.title}</strong>
                      <small>{stage.text}</small>
                    </div>
                  </article>
                );
              })}
            </div>

            <div className="nk-request-status__details">
              <article>
                <span>Pedido enviado</span>
                <strong>{formatDate(result.created_at)}</strong>
              </article>
              <article>
                <span>Última atualização</span>
                <strong>{formatDate(result.updated_at)}</strong>
              </article>
              <article className="is-code">
                <span>Código privado</span>
                <strong>{result.codigo}</strong>
                <button type="button" onClick={copyCode}>
                  <ClipboardCopy size={15} /> {copied ? "Copiado" : "Copiar"}
                </button>
              </article>
            </div>

            <div className="nk-request-status__assurance">
              <LockKeyhole size={18} />
              <p>
                Esta página apresenta apenas o andamento. Os seus documentos,
                fotografias, telefone e dados internos da análise permanecem protegidos.
              </p>
            </div>

            <footer>
              {result.next_action === "IDENTITY_RECAPTURE" && result.next_path && (
                <button
                  type="button"
                  className="nk-button nk-button--wine"
                  onClick={() => window.location.assign(result.next_path)}
                >
                  <RefreshCw size={18} /> Repetir verificação
                </button>
              )}
              {result.can_login && (
                <button type="button" className="nk-button nk-button--wine" onClick={onLogin}>
                  <BadgeCheck size={18} /> Entrar na conta
                </button>
              )}
              <button type="button" className="nk-button nk-button--quiet" onClick={resetLookup}>
                Consultar outro pedido
              </button>
            </footer>
          </section>
        )}
      </section>
    </main>
  );
}
