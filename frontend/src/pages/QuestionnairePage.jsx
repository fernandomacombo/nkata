import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Check,
  Eye,
  EyeOff,
  HeartHandshake,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import {
  createQuestionnairePassword,
  fetchQuestionnaire,
  submitQuestionnaire,
} from "../services/questionnaireApi.js";
import NkataLogo from "../components/brand/NkataLogo.jsx";

const emptyValues = {
  disponibilidade: "",
  tem_filhos: "",
  aceita_pessoa_com_filhos: "",
  cidade_preferida: "",
  faixa_etaria_preferida: "",
  sobre_si: "",
  o_que_valoriza: "",
  o_que_nao_aceita: "",
  aceita_regras: false,
};

function firstError(errors, name) {
  const value = errors?.[name];
  return Array.isArray(value) ? value[0] : value || "";
}

function FieldError({ errors, name }) {
  const message = firstError(errors, name);
  return message ? <small className="nk-questionnaire-error">{message}</small> : null;
}

function SelectField({ label, name, value, choices = [], errors, onChange }) {
  return (
    <label className="nk-questionnaire-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(name, event.target.value)}>
        <option value="">Selecione uma opção</option>
        {choices.map((choice) => (
          <option key={choice.value} value={choice.value}>{choice.label}</option>
        ))}
      </select>
      <FieldError errors={errors} name={name} />
    </label>
  );
}

export default function QuestionnairePage({ token, onBack, onLogin }) {
  const [data, setData] = useState(null);
  const [values, setValues] = useState(emptyValues);
  const [step, setStep] = useState("questionnaire");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [requestError, setRequestError] = useState("");
  const [errors, setErrors] = useState({});
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetchQuestionnaire(token, { signal: controller.signal })
      .then((payload) => {
        setData(payload);
        setValues({ ...emptyValues, ...(payload.values || {}) });
        if (payload.account_ready) setStep("success");
        else if (payload.questionnaire_complete) setStep("password");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setRequestError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [token]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [step]);

  const firstName = useMemo(() => {
    const name = data?.pedido?.nome || "";
    return name.trim().split(/\s+/)[0] || "";
  }, [data]);

  const updateValue = (name, value) => {
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
    setRequestError("");
  };

  const validateQuestionnaire = () => {
    const next = {};
    ["disponibilidade", "tem_filhos", "aceita_pessoa_com_filhos"].forEach((field) => {
      if (!values[field]) next[field] = "Escolha uma opção.";
    });
    if (values.cidade_preferida.trim().length < 2) next.cidade_preferida = "Informe a cidade ou região.";
    if (values.faixa_etaria_preferida.trim().length < 3) next.faixa_etaria_preferida = "Informe a faixa etária que procura.";
    if (values.sobre_si.trim().length < 20) next.sobre_si = "Conte um pouco mais sobre si.";
    if (values.o_que_valoriza.trim().length < 10) next.o_que_valoriza = "Diga o que considera importante numa relação.";
    if (values.o_que_nao_aceita.trim().length < 10) next.o_que_nao_aceita = "Explique os limites importantes para si.";
    if (!values.aceita_regras) next.aceita_regras = "Confirme que aceita as regras da comunidade.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleQuestionnaireSubmit = async (event) => {
    event.preventDefault();
    if (!validateQuestionnaire()) return;

    setSubmitting(true);
    setRequestError("");
    setErrors({});
    try {
      await submitQuestionnaire(token, values);
      setStep("password");
    } catch (error) {
      setRequestError(error.message);
      setErrors(error.payload?.errors || {});
    } finally {
      setSubmitting(false);
    }
  };

  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    const next = {};
    if (password.length < 8) next.password = "Use pelo menos 8 caracteres.";
    if (password !== confirmation) next.confirmation = "As palavras-passe não coincidem.";
    if (Object.keys(next).length) {
      setErrors(next);
      return;
    }

    setSubmitting(true);
    setRequestError("");
    setErrors({});
    try {
      await createQuestionnairePassword(token, { password, confirmation });
      setStep("success");
    } catch (error) {
      setRequestError(error.message);
      setErrors(error.payload?.errors || {});
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="nk-questionnaire-shell nk-questionnaire-center">
        <LoaderCircle className="is-spinning" size={30} />
        <strong>A preparar o seu questionário…</strong>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="nk-questionnaire-shell nk-questionnaire-center">
        <ShieldCheck size={34} />
        <h1>Este questionário não está disponível.</h1>
        <p>{requestError || "Confirme se o pedido já foi aprovado."}</p>
        <button type="button" className="nk-button nk-button--quiet" onClick={onBack}>Voltar ao NKATA</button>
      </main>
    );
  }

  return (
    <main className="nk-questionnaire-shell">
      <header className="nk-questionnaire-topbar">
        <button type="button" className="nk-questionnaire-brand" onClick={onBack}>
          <NkataLogo /><strong>NKATA</strong>
        </button>
        <span className="nk-questionnaire-secure"><LockKeyhole size={14} /> Ligação protegida</span>
      </header>

      <section className="nk-questionnaire-layout">
        <aside className="nk-questionnaire-intro">
          <button type="button" className="nk-questionnaire-back" onClick={onBack}>
            <ArrowLeft size={16} /> Voltar
          </button>
          <span className="nk-eyebrow nk-eyebrow--dark"><BadgeCheck size={15} /> Pedido aprovado</span>
          <h1>{firstName ? `${firstName}, ` : ""}vamos conhecer melhor as suas intenções.</h1>
          <p>
            As respostas ajudam a apresentar o seu perfil com mais clareza e a manter a comunidade focada em relações sérias.
          </p>

          <div className="nk-questionnaire-person">
            <span><UserRound size={20} /></span>
            <div>
              <small>Pedido aprovado para</small>
              <strong>{data.pedido.nome}</strong>
              <em>{data.pedido.cidade} · {data.pedido.objetivo}</em>
            </div>
          </div>

          <div className="nk-questionnaire-steps" aria-label="Progresso">
            <div className={step === "questionnaire" ? "is-active" : "is-complete"}>
              <span>{step === "questionnaire" ? "1" : <Check size={15} />}</span>
              <div><strong>Questionário</strong><small>Preferências e apresentação</small></div>
            </div>
            <div className={step === "password" ? "is-active" : step === "success" ? "is-complete" : ""}>
              <span>{step === "success" ? <Check size={15} /> : "2"}</span>
              <div><strong>Palavra-passe</strong><small>Proteja a sua conta</small></div>
            </div>
            <div className={step === "success" ? "is-active" : ""}>
              <span>3</span>
              <div><strong>Conta pronta</strong><small>Comece a usar o NKATA</small></div>
            </div>
          </div>
        </aside>

        <section className="nk-questionnaire-card">
          {step === "questionnaire" && (
            <form onSubmit={handleQuestionnaireSubmit}>
              <div className="nk-questionnaire-card__heading">
                <span>1 de 2</span>
                <h2>Sobre si e o que procura</h2>
                <p>Responda com naturalidade. Pode rever tudo antes de continuar.</p>
              </div>

              <div className="nk-questionnaire-grid">
                <SelectField
                  label="Está disponível para uma relação?"
                  name="disponibilidade"
                  value={values.disponibilidade}
                  choices={data.choices?.disponibilidade}
                  errors={errors}
                  onChange={updateValue}
                />
                <SelectField
                  label="Tem filhos?"
                  name="tem_filhos"
                  value={values.tem_filhos}
                  choices={data.choices?.tem_filhos}
                  errors={errors}
                  onChange={updateValue}
                />
                <SelectField
                  label="Aceita conhecer alguém com filhos?"
                  name="aceita_pessoa_com_filhos"
                  value={values.aceita_pessoa_com_filhos}
                  choices={data.choices?.aceita_pessoa_com_filhos}
                  errors={errors}
                  onChange={updateValue}
                />

                <label className="nk-questionnaire-field">
                  <span>Onde gostaria de conhecer pessoas?</span>
                  <input value={values.cidade_preferida} onChange={(event) => updateValue("cidade_preferida", event.target.value)} placeholder="Ex.: Maputo, Matola, Vilankulo" />
                  <FieldError errors={errors} name="cidade_preferida" />
                </label>

                <label className="nk-questionnaire-field nk-questionnaire-field--full">
                  <span>Faixa etária que procura</span>
                  <input value={values.faixa_etaria_preferida} onChange={(event) => updateValue("faixa_etaria_preferida", event.target.value)} placeholder="Ex.: 25 a 35 anos" />
                  <FieldError errors={errors} name="faixa_etaria_preferida" />
                </label>

                <label className="nk-questionnaire-field nk-questionnaire-field--full">
                  <span>Fale um pouco sobre si</span>
                  <textarea rows="4" value={values.sobre_si} onChange={(event) => updateValue("sobre_si", event.target.value)} placeholder="Conte o que considera importante sobre si, com as suas próprias palavras." />
                  <FieldError errors={errors} name="sobre_si" />
                </label>

                <label className="nk-questionnaire-field nk-questionnaire-field--full">
                  <span>O que mais valoriza numa relação?</span>
                  <textarea rows="4" value={values.o_que_valoriza} onChange={(event) => updateValue("o_que_valoriza", event.target.value)} placeholder="Ex.: respeito, honestidade, presença, comunicação…" />
                  <FieldError errors={errors} name="o_que_valoriza" />
                </label>

                <label className="nk-questionnaire-field nk-questionnaire-field--full">
                  <span>O que não aceita numa relação?</span>
                  <textarea rows="4" value={values.o_que_nao_aceita} onChange={(event) => updateValue("o_que_nao_aceita", event.target.value)} placeholder="Fale dos limites que considera importantes." />
                  <FieldError errors={errors} name="o_que_nao_aceita" />
                </label>
              </div>

              <label className={`nk-questionnaire-consent ${errors.aceita_regras ? "has-error" : ""}`}>
                <input type="checkbox" checked={values.aceita_regras} onChange={(event) => updateValue("aceita_regras", event.target.checked)} />
                <span><Check size={14} /></span>
                <div>
                  <strong>Aceito as regras da comunidade NKATA</strong>
                  <small>Comprometo-me a agir com respeito, honestidade e intenção clara.</small>
                </div>
              </label>
              <FieldError errors={errors} name="aceita_regras" />

              {requestError && <div className="nk-questionnaire-alert">{requestError}</div>}

              <button type="submit" className="nk-button nk-button--wine nk-questionnaire-primary" disabled={submitting}>
                {submitting ? <LoaderCircle size={18} className="is-spinning" /> : <HeartHandshake size={18} />}
                Guardar e continuar <ArrowRight size={17} />
              </button>
            </form>
          )}

          {step === "password" && (
            <form onSubmit={handlePasswordSubmit}>
              <div className="nk-questionnaire-card__heading">
                <span>2 de 2</span>
                <h2>Crie a sua palavra-passe</h2>
                <p>Esta palavra-passe será usada para entrar na sua conta. A equipa NKATA não precisa de a conhecer.</p>
              </div>

              <div className="nk-questionnaire-password-note">
                <LockKeyhole size={21} />
                <div><strong>A sua conta continua privada nesta etapa</strong><small>O perfil só é ativado depois de concluir a palavra-passe.</small></div>
              </div>

              <label className="nk-questionnaire-field nk-questionnaire-field--full">
                <span>Nova palavra-passe</span>
                <div className="nk-questionnaire-password">
                  <input type={showPassword ? "text" : "password"} value={password} onChange={(event) => { setPassword(event.target.value); setErrors((current) => ({ ...current, password: undefined })); }} autoComplete="new-password" placeholder="Pelo menos 8 caracteres" />
                  <button type="button" onClick={() => setShowPassword((current) => !current)} aria-label={showPassword ? "Ocultar palavra-passe" : "Mostrar palavra-passe"}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button>
                </div>
                <FieldError errors={errors} name="password" />
              </label>

              <label className="nk-questionnaire-field nk-questionnaire-field--full">
                <span>Confirmar palavra-passe</span>
                <div className="nk-questionnaire-password">
                  <input type={showConfirmation ? "text" : "password"} value={confirmation} onChange={(event) => { setConfirmation(event.target.value); setErrors((current) => ({ ...current, confirmation: undefined })); }} autoComplete="new-password" placeholder="Repita a palavra-passe" />
                  <button type="button" onClick={() => setShowConfirmation((current) => !current)} aria-label={showConfirmation ? "Ocultar confirmação" : "Mostrar confirmação"}>{showConfirmation ? <EyeOff size={18} /> : <Eye size={18} />}</button>
                </div>
                <FieldError errors={errors} name="confirmation" />
              </label>

              {requestError && <div className="nk-questionnaire-alert">{requestError}</div>}

              <div className="nk-questionnaire-actions">
                <button type="button" className="nk-button nk-button--quiet" onClick={() => setStep("questionnaire")}>Rever respostas</button>
                <button type="submit" className="nk-button nk-button--wine" disabled={submitting}>
                  {submitting ? <LoaderCircle size={18} className="is-spinning" /> : <LockKeyhole size={18} />}
                  Criar a minha conta
                </button>
              </div>
            </form>
          )}

          {step === "success" && (
            <div className="nk-questionnaire-success">
              <span><BadgeCheck size={34} /></span>
              <small>Conta preparada</small>
              <h2>Bem-vindo ao NKATA{firstName ? `, ${firstName}` : ""}.</h2>
              <p>O seu questionário foi concluído e a conta está pronta. Agora já pode entrar e gerir o seu perfil.</p>
              <div className="nk-questionnaire-success__actions">
                <button type="button" className="nk-button nk-button--wine" onClick={onLogin}>Entrar na minha conta <ArrowRight size={17} /></button>
                <button type="button" className="nk-button nk-button--quiet" onClick={onBack}>Voltar ao início</button>
              </div>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
