import { MatchPreferences, legacyAges } from "../components/MatchPreferences";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Eye,
  EyeOff,
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
  return message ? <small className="nk-questionnaire-error" role="alert">{message}</small> : null;
}

const questions = [
  { field: "disponibilidade", group: "Sobre si", title: "Está disponível para uma relação?" },
  { field: "tem_filhos", group: "Sobre si", title: "Tem filhos?" },
  { field: "sobre_si", group: "Sobre si", title: "Como se apresentaria?", multiline: true, hint: "Pode falar de algo que gosta de fazer ou de como costuma passar o seu tempo." },
  { field: "aceita_pessoa_com_filhos", group: "Quem quer conhecer", title: "Aceita conhecer alguém com filhos?" },
  { field: "cidade_preferida", group: "Quem quer conhecer", title: "Onde gostaria de conhecer pessoas?", hint: "Ex.: Maputo, Matola, Vilankulo" },
  { field: "ages", group: "Quem quer conhecer", title: "Que idades prefere?" },
  { field: "o_que_valoriza", group: "Valores e limites", title: "O que mais valoriza numa relação?", multiline: true, hint: "Ex.: respeito, honestidade, comunicação" },
  { field: "o_que_nao_aceita", group: "Valores e limites", title: "Que limites são importantes para si?", multiline: true, hint: "Pense no que precisa para se sentir respeitado numa relação." },
];
const lastQuestion = questions.length - 1;

function ChoiceField({ name, value, choices = [], errors, onChange }) {
  return (
    <fieldset className="nk-questionnaire-choice" aria-labelledby="nk-question-title">
      <div>
        {choices.map((choice) => (
          <label key={choice.value}>
            <input type="radio" name={name} checked={value === choice.value} onChange={() => onChange(name, choice.value)} />
            <span>{choice.label}</span>
          </label>
        ))}
      </div>
      <FieldError errors={errors} name={name} />
    </fieldset>
  );
}

function SafetyNotice({ onAccept, onBack }) {
  const dialogRef = useRef(null);
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);

  return (
    <dialog
      ref={dialogRef}
      className="nk-questionnaire-safety"
      aria-labelledby="nk-questionnaire-safety-title"
      onCancel={(event) => event.preventDefault()}
    >
      <form onSubmit={(event) => {
        event.preventDefault();
        if (accepted) onAccept();
      }}>
        <div className="nk-questionnaire-safety__body">
          <span className="nk-questionnaire-safety__icon"><ShieldCheck size={24} aria-hidden="true" /></span>
          <h2 id="nk-questionnaire-safety-title">A sua segurança no NKATA</h2>
          <ul>
            <li>Escolha fotos que se sinta confortável em mostrar. Evite imagens íntimas ou comprometedoras e respeite a privacidade de outras pessoas.</li>
            <li>Proteja os seus dados. Evite partilhar números de telefone, emails, documentos, palavras-passe ou dados bancários em conversas, fotos ou publicações.</li>
            <li>Se alguém pedir dinheiro, dados pessoais ou imagens íntimas, pode bloquear e denunciar o perfil no NKATA.</li>
          </ul>
          <p className="nk-questionnaire-safety__privacy">
            <LockKeyhole size={19} aria-hidden="true" />
            <span><strong>O NKATA protege os seus dados sensíveis.</strong> Os documentos enviados para verificação são confidenciais e ficam fora do seu perfil público. Pedimos que proteja também os seus dados e os de outras pessoas.</span>
          </p>
        </div>
        <footer>
          <label>
            <input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} />
            <span>Li e aceito estas orientações de segurança e as regras da comunidade NKATA.</span>
          </label>
          <div className="nk-questionnaire-safety__actions">
            <button type="button" className="nk-button nk-button--quiet" onClick={onBack}>Voltar</button>
            <button type="submit" className="nk-button nk-button--wine" disabled={!accepted}>Aceitar e abrir o questionário</button>
          </div>
        </footer>
      </form>
    </dialog>
  );
}

export default function QuestionnairePage({ token, onBack, onLogin }) {
  const [data, setData] = useState(null);
  const [values, setValues] = useState(emptyValues);
  const [step, setStep] = useState("questionnaire");
  const [questionIndex, setQuestionIndex] = useState(0);
  const headingRef = useRef(null);
  const [promotionGranted, setPromotionGranted] = useState(false);
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
        const saved = payload.values || {};
        setValues({
          ...emptyValues,
          ...saved,
          preferencias: { ages: legacyAges(saved.faixa_etaria_preferida), ...saved.preferencias },
        });
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
    headingRef.current?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [step, questionIndex]);

  const firstName = useMemo(() => {
    const name = data?.pedido?.nome || "";
    return name.trim().split(/\s+/)[0] || "";
  }, [data]);

  const updateValue = (name, value) => {
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined, ...(name === "preferencias" ? { ages: undefined } : {}) }));
    setRequestError("");
  };

  const validateQuestionnaire = () => {
    const next = {};
    ["disponibilidade", "tem_filhos", "aceita_pessoa_com_filhos"].forEach((field) => {
      if (!values[field]) next[field] = "Escolha uma opção.";
    });
    if (values.cidade_preferida.trim().length < 2) next.cidade_preferida = "Informe a cidade ou região.";
    const ages = values.preferencias?.ages;
    if (ages && (!ages[0] || !ages[1] || ages[0] > ages[1])) next.ages = "Reveja a idade mínima e máxima.";
    if (ages === undefined) next.ages = "Escolha uma opção de idade.";
    if (values.sobre_si.trim().length < 20) next.sobre_si = "Conte um pouco mais sobre si.";
    if (values.o_que_valoriza.trim().length < 10) next.o_que_valoriza = "Diga o que considera importante numa relação.";
    if (values.o_que_nao_aceita.trim().length < 10) next.o_que_nao_aceita = "Explique os limites importantes para si.";
    if (!values.aceita_regras) next.aceita_regras = "Confirme que aceita as regras da comunidade.";
    return next;
  };

  const question = questions[questionIndex];
  const showQuestionWithErrors = (fieldErrors) => {
    const index = questions.findIndex(({ field }) => fieldErrors[field]);
    if (index !== -1) setQuestionIndex(index);
    else if (fieldErrors.preferencias || fieldErrors.faixa_etaria_preferida) {
      setQuestionIndex(questions.findIndex(({ field }) => field === "ages"));
    }
  };

  const handleQuestionnaireSubmit = async (event) => {
    event.preventDefault();
    if (!values.aceita_regras || submitting) return;
    const validation = validateQuestionnaire();
    if (questionIndex < lastQuestion) {
      if (validation[question.field]) setErrors(validation);
      else {
        setErrors({});
        setRequestError("");
        setQuestionIndex(questionIndex + 1);
      }
      return;
    }
    if (Object.keys(validation).length) {
      setErrors(validation);
      showQuestionWithErrors(validation);
      return;
    }

    setSubmitting(true);
    setRequestError("");
    setErrors({});
    try {
      await submitQuestionnaire(token, values);
      setStep("password");
    } catch (error) {
      setRequestError(error.message);
      const fieldErrors = error.payload?.errors || {};
      setErrors(fieldErrors);
      showQuestionWithErrors(fieldErrors);
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
      const result = await createQuestionnairePassword(token, { password, confirmation });
      setPromotionGranted(Boolean(result.promotion_granted));
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

  const showSafetyNotice = step === "questionnaire" && !values.aceita_regras;
  return (
    <main className="nk-questionnaire-shell">
      {showSafetyNotice && (
        <SafetyNotice onAccept={() => updateValue("aceita_regras", true)} onBack={onBack} />
      )}
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
          <h1>{firstName ? `${firstName}, ` : ""}complete o seu perfil.</h1>
          <p>Conte-nos o essencial para prepararmos a sua conta.</p>

          <div className="nk-questionnaire-person">
            <span><UserRound size={20} /></span>
            <div>
              <small>Pedido aprovado para</small>
              <strong>{data.pedido.nome}</strong>
              <em>{data.pedido.cidade} · {data.pedido.objetivo}</em>
            </div>
          </div>

        </aside>

        <section className="nk-questionnaire-card">
          {step === "questionnaire" && !showSafetyNotice && (
            <form onSubmit={handleQuestionnaireSubmit} noValidate>
              <progress className="nk-questionnaire-meter" value={questionIndex + 1} max={questions.length} aria-label={`Pergunta ${questionIndex + 1} de ${questions.length}`} />
              <div className="nk-questionnaire-card__heading nk-questionnaire-chapter">
                <span>{question.group}</span>
                <h2 ref={headingRef} id="nk-question-title" tabIndex={-1}>{question.title}</h2>
                {question.hint && <p id="nk-question-hint">{question.hint}</p>}
              </div>

              <div key={question.field} className="nk-questionnaire-answer">
                {question.field === "ages" ? (
                  <>
                    <MatchPreferences
                      values={values.preferencias}
                      onChange={(preferences) => updateValue("preferencias", preferences)}
                      section="search"
                      requireAge
                      compactSearch
                      errors={{ ...errors, ages: firstError(errors, "ages") || firstError(errors, "faixa_etaria_preferida") }}
                    />
                    <FieldError errors={errors} name="preferencias" />
                  </>
                ) : data.choices?.[question.field] ? (
                  <ChoiceField name={question.field} value={values[question.field]} choices={data.choices[question.field]} errors={errors} onChange={updateValue} />
                ) : (
                  <div className="nk-questionnaire-field">
                    {question.multiline ? (
                      <textarea rows={4} aria-labelledby="nk-question-title" aria-describedby="nk-question-hint"
                        value={values[question.field]} onChange={(event) => updateValue(question.field, event.target.value)} />
                    ) : (
                      <input aria-labelledby="nk-question-title" aria-describedby="nk-question-hint"
                        value={values[question.field]} onChange={(event) => updateValue(question.field, event.target.value)} />
                    )}
                    <FieldError errors={errors} name={question.field} />
                  </div>
                )}
                {question.field === "sobre_si" && (
                  <MatchPreferences values={values.preferencias} onChange={(preferences) => updateValue("preferencias", preferences)} section="details" />
                )}
              </div>

              <FieldError errors={errors} name="aceita_regras" />

              {requestError && <div className="nk-questionnaire-alert" role="alert">{requestError}</div>}

              <div className="nk-questionnaire-actions nk-questionnaire-chapter-actions">
                {questionIndex > 0 && (
                  <button type="button" className="nk-button nk-button--quiet" disabled={submitting} onClick={() => { setQuestionIndex(questionIndex - 1); setRequestError(""); }}>
                    <ArrowLeft size={17} /> Anterior
                  </button>
                )}
                <button type="submit" className="nk-button nk-button--wine" disabled={submitting}>
                  {questionIndex === lastQuestion ? "Guardar e continuar" : "Continuar"}
                  {submitting ? <LoaderCircle size={18} className="is-spinning" /> : <ArrowRight size={17} />}
                </button>
              </div>
            </form>
          )}

          {step === "password" && (
            <form onSubmit={handlePasswordSubmit}>
              <div className="nk-questionnaire-card__heading">
                <span>Último passo</span>
                <h2 ref={headingRef} tabIndex={-1}>Crie a sua palavra-passe</h2>
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

              {requestError && <div className="nk-questionnaire-alert" role="alert">{requestError}</div>}

              <div className="nk-questionnaire-actions">
                <button type="button" className="nk-button nk-button--quiet" disabled={submitting} onClick={() => { setQuestionIndex(0); setErrors({}); setRequestError(""); setStep("questionnaire"); }}>Rever respostas</button>
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
              {promotionGranted && <p><strong>Já tem 15 dias grátis de NKATA Quinzenal.</strong></p>}
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
