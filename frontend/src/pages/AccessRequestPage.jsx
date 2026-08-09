import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Camera,
  Check,
  FileCheck2,
  ImagePlus,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { submitAccessRequest } from "../services/api.js";

const steps = [
  { id: "details", label: "Sobre si", icon: UserRound },
  { id: "photos", label: "Fotografias", icon: Camera },
  { id: "identity", label: "Identidade", icon: ShieldCheck },
  { id: "review", label: "Confirmar", icon: FileCheck2 },
];

const initialValues = {
  nome_completo: "",
  email: "",
  telefone: "",
  idade: "",
  cidade: "",
  genero: "",
  objetivo: "",
  aceita_verificacao: false,
};

const initialFiles = {
  foto_perfil: null,
  foto_extra_1: null,
  foto_extra_2: null,
  foto_extra_3: null,
  bi_frente: null,
  bi_verso: null,
  selfie_com_bi: null,
};

const photoFields = [
  { name: "foto_perfil", title: "Foto principal", text: "Uma fotografia recente, com o rosto bem visível." },
  { name: "foto_extra_1", title: "Fotografia 2", text: "Escolha uma fotografia diferente da principal." },
  { name: "foto_extra_2", title: "Fotografia 3", text: "Pode ser uma fotografia de corpo inteiro ou num ambiente natural." },
  { name: "foto_extra_3", title: "Fotografia 4", text: "Evite filtros fortes, óculos escuros e imagens desfocadas." },
];

const identityFields = [
  { name: "bi_frente", title: "BI — frente", text: "A informação deve estar legível." },
  { name: "bi_verso", title: "BI — verso", text: "Fotografe o documento inteiro." },
  { name: "selfie_com_bi", title: "Selfie com o BI", text: "Segure o documento junto ao rosto, com boa iluminação." },
];

function fieldError(errors, name) {
  const value = errors?.[name];
  return Array.isArray(value) ? value[0] : value || "";
}

function FileCard({ field, file, error, onChange, privateFile = false }) {
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : ""), [file]);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview);
  }, [preview]);

  return (
    <label className={`nk-access-upload ${file ? "has-file" : ""} ${error ? "has-error" : ""}`}>
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={(event) => onChange(field.name, event.target.files?.[0] || null)}
      />

      <span className="nk-access-upload__preview">
        {preview ? (
          <img src={preview} alt="Pré-visualização" />
        ) : privateFile ? (
          <LockKeyhole size={25} />
        ) : (
          <ImagePlus size={25} />
        )}
      </span>

      <span className="nk-access-upload__copy">
        <strong>{field.title}</strong>
        <small>{file ? file.name : field.text}</small>
        {error && <em>{error}</em>}
      </span>

      <span className="nk-access-upload__action">
        {file ? <Check size={17} /> : "Escolher"}
      </span>
    </label>
  );
}

function Progress({ current }) {
  return (
    <div className="nk-access-progress" aria-label={`Passo ${current + 1} de ${steps.length}`}>
      {steps.map((step, index) => {
        const Icon = step.icon;
        const active = index === current;
        const complete = index < current;
        return (
          <div
            key={step.id}
            className={`${active ? "is-active" : ""} ${complete ? "is-complete" : ""}`}
          >
            <span>{complete ? <Check size={16} /> : <Icon size={16} />}</span>
            <small>{step.label}</small>
          </div>
        );
      })}
    </div>
  );
}

export default function AccessRequestPage({ onBack, onLogin, onFinish }) {
  const [step, setStep] = useState(0);
  const [values, setValues] = useState(initialValues);
  const [files, setFiles] = useState(initialFiles);
  const [errors, setErrors] = useState({});
  const [requestError, setRequestError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState("");

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [step]);

  const updateValue = (name, value) => {
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
    setRequestError("");
  };

  const updateFile = (name, file) => {
    setFiles((current) => ({ ...current, [name]: file }));
    setErrors((current) => ({ ...current, [name]: undefined }));
    setRequestError("");
  };

  const validateStep = () => {
    const nextErrors = {};

    if (step === 0) {
      if (values.nome_completo.trim().length < 3) nextErrors.nome_completo = "Escreva o seu nome completo.";
      if (!/^\S+@\S+\.\S+$/.test(values.email)) nextErrors.email = "Informe um email válido.";
      if (values.telefone.replace(/\D/g, "").length < 8) nextErrors.telefone = "Informe um número de telefone válido.";
      if (!values.idade || Number(values.idade) < 18) nextErrors.idade = "O NKATA é apenas para maiores de 18 anos.";
      if (values.cidade.trim().length < 2) nextErrors.cidade = "Informe a sua cidade.";
      if (!values.genero) nextErrors.genero = "Escolha uma opção.";
      if (!values.objetivo) nextErrors.objetivo = "Escolha o que procura.";
    }

    const fieldsToCheck = step === 1 ? photoFields : step === 2 ? identityFields : [];
    fieldsToCheck.forEach(({ name }) => {
      const file = files[name];
      if (!file) {
        nextErrors[name] = "Escolha esta imagem.";
      } else if (file.size > 6 * 1024 * 1024) {
        nextErrors[name] = "A imagem deve ter no máximo 6 MB.";
      } else if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
        nextErrors[name] = "Use JPG, PNG ou WEBP.";
      }
    });

    if (step === 3 && !values.aceita_verificacao) {
      nextErrors.aceita_verificacao = "Confirme que aceita a verificação para enviar o pedido.";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const goNext = () => {
    if (!validateStep()) return;
    setStep((current) => Math.min(current + 1, steps.length - 1));
  };

  const goBack = () => {
    if (step === 0) {
      onBack?.();
      return;
    }
    setErrors({});
    setRequestError("");
    setStep((current) => current - 1);
  };

  const handleSubmit = async () => {
    if (!validateStep() || submitting) return;

    setSubmitting(true);
    setRequestError("");

    try {
      const result = await submitAccessRequest(values, files);
      setSuccess(result?.message || "Recebemos o seu pedido.");
    } catch (error) {
      const payloadErrors = error.payload?.errors || {};
      setErrors(payloadErrors);
      setRequestError(error.message || "Não foi possível enviar o pedido agora.");

      const detailFields = Object.keys(payloadErrors);
      if (detailFields.some((name) => Object.hasOwn(initialValues, name))) setStep(0);
      else if (detailFields.some((name) => photoFields.some((field) => field.name === name))) setStep(1);
      else if (detailFields.some((name) => identityFields.some((field) => field.name === name))) setStep(2);
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <main className="nk-access-success">
        <section>
          <span><BadgeCheck size={34} /></span>
          <small>Pedido recebido</small>
          <h1>Agora é com a equipa NKATA.</h1>
          <p>{success}</p>
          <div>
            <button type="button" className="nk-button nk-button--wine" onClick={onFinish}>
              Voltar ao início
            </button>
            <button type="button" className="nk-button nk-button--quiet" onClick={onLogin}>
              Já tenho conta
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="nk-access-page">
      <section className="nk-access-intro">
        <div className="nk-shell nk-access-intro__inner">
          <button type="button" onClick={goBack} className="nk-access-back">
            <ArrowLeft size={18} /> Voltar
          </button>
          <div>
            <span className="nk-eyebrow nk-eyebrow--dark">
              <ShieldCheck size={15} /> Entrada mediante aprovação
            </span>
            <h1>Peça acesso com calma.</h1>
            <p>Precisamos de alguns dados para confirmar que cada pessoa é real e adulta.</p>
          </div>
          <aside>
            <LockKeyhole size={19} />
            <span>
              <strong>Os documentos são privados.</strong>
              <small>Não aparecem no perfil e são usados apenas na análise.</small>
            </span>
          </aside>
        </div>
      </section>

      <section className="nk-shell nk-access-workspace">
        <Progress current={step} />

        <div className="nk-access-layout">
          <section className="nk-access-card">
            {step === 0 && (
              <div className="nk-access-step nk-soft-enter">
                <header>
                  <small>Passo 1 de 4</small>
                  <h2>Conte-nos quem é.</h2>
                  <p>Use os seus dados reais. Eles serão confirmados antes da aprovação.</p>
                </header>

                <div className="nk-access-fields">
                  <label className="is-wide">
                    <span>Nome completo</span>
                    <input value={values.nome_completo} onChange={(event) => updateValue("nome_completo", event.target.value)} autoComplete="name" placeholder="O seu nome completo" />
                    {fieldError(errors, "nome_completo") && <em>{fieldError(errors, "nome_completo")}</em>}
                  </label>
                  <label>
                    <span>Email</span>
                    <input type="email" value={values.email} onChange={(event) => updateValue("email", event.target.value)} autoComplete="email" placeholder="nome@exemplo.com" />
                    {fieldError(errors, "email") && <em>{fieldError(errors, "email")}</em>}
                  </label>
                  <label>
                    <span>Telefone</span>
                    <input value={values.telefone} onChange={(event) => updateValue("telefone", event.target.value)} autoComplete="tel" placeholder="+258 84 000 0000" />
                    {fieldError(errors, "telefone") && <em>{fieldError(errors, "telefone")}</em>}
                  </label>
                  <label>
                    <span>Idade</span>
                    <input type="number" min="18" max="100" value={values.idade} onChange={(event) => updateValue("idade", event.target.value)} placeholder="Ex.: 32" />
                    {fieldError(errors, "idade") && <em>{fieldError(errors, "idade")}</em>}
                  </label>
                  <label>
                    <span>Cidade</span>
                    <input value={values.cidade} onChange={(event) => updateValue("cidade", event.target.value)} autoComplete="address-level2" placeholder="Ex.: Maputo" />
                    {fieldError(errors, "cidade") && <em>{fieldError(errors, "cidade")}</em>}
                  </label>
                  <label>
                    <span>Género</span>
                    <select value={values.genero} onChange={(event) => updateValue("genero", event.target.value)}>
                      <option value="">Escolha uma opção</option>
                      <option value="MASCULINO">Masculino</option>
                      <option value="FEMININO">Feminino</option>
                      <option value="OUTRO">Prefiro não dizer</option>
                    </select>
                    {fieldError(errors, "genero") && <em>{fieldError(errors, "genero")}</em>}
                  </label>
                  <label>
                    <span>O que procura?</span>
                    <select value={values.objetivo} onChange={(event) => updateValue("objetivo", event.target.value)}>
                      <option value="">Escolha uma opção</option>
                      <option value="RELACIONAMENTO_SERIO">Relacionamento sério</option>
                      <option value="CONHECER_COM_INTENCAO">Conhecer com intenção</option>
                      <option value="AMIZADE_EVOLUIR">Amizade que pode evoluir</option>
                      <option value="CASAMENTO_FUTURO">Casamento no futuro</option>
                    </select>
                    {fieldError(errors, "objetivo") && <em>{fieldError(errors, "objetivo")}</em>}
                  </label>
                </div>
              </div>
            )}

            {step === 1 && (
              <div className="nk-access-step nk-soft-enter">
                <header>
                  <small>Passo 2 de 4</small>
                  <h2>Escolha fotografias naturais.</h2>
                  <p>Quatro imagens ajudam a equipa a confirmar o pedido e tornam o futuro perfil mais completo.</p>
                </header>
                <div className="nk-access-uploads">
                  {photoFields.map((field) => (
                    <FileCard key={field.name} field={field} file={files[field.name]} error={fieldError(errors, field.name)} onChange={updateFile} />
                  ))}
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="nk-access-step nk-soft-enter">
                <header>
                  <small>Passo 3 de 4</small>
                  <h2>Confirme a sua identidade.</h2>
                  <p>Estas imagens ficam restritas à equipa responsável pela análise.</p>
                </header>
                <div className="nk-access-uploads nk-access-uploads--identity">
                  {identityFields.map((field) => (
                    <FileCard key={field.name} field={field} file={files[field.name]} error={fieldError(errors, field.name)} onChange={updateFile} privateFile />
                  ))}
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="nk-access-step nk-soft-enter">
                <header>
                  <small>Passo 4 de 4</small>
                  <h2>Confirme antes de enviar.</h2>
                  <p>Revise os dados principais. Ainda pode voltar e corrigir alguma informação.</p>
                </header>

                <div className="nk-access-review">
                  <article><span>Nome</span><strong>{values.nome_completo}</strong></article>
                  <article><span>Email</span><strong>{values.email}</strong></article>
                  <article><span>Telefone</span><strong>{values.telefone}</strong></article>
                  <article><span>Cidade</span><strong>{values.cidade}</strong></article>
                  <article><span>Idade</span><strong>{values.idade} anos</strong></article>
                  <article><span>Imagens</span><strong>7 selecionadas</strong></article>
                </div>

                <label className={`nk-access-consent ${fieldError(errors, "aceita_verificacao") ? "has-error" : ""}`}>
                  <input type="checkbox" checked={values.aceita_verificacao} onChange={(event) => updateValue("aceita_verificacao", event.target.checked)} />
                  <span>
                    <strong>Aceito passar pela verificação do NKATA.</strong>
                    <small>Compreendo que o pedido pode ser aprovado, recusado ou devolvido para correção.</small>
                    {fieldError(errors, "aceita_verificacao") && <em>{fieldError(errors, "aceita_verificacao")}</em>}
                  </span>
                </label>
              </div>
            )}

            {requestError && <div className="nk-access-error" role="alert">{requestError}</div>}

            <footer className="nk-access-actions">
              <button type="button" className="nk-button nk-button--quiet" onClick={goBack} disabled={submitting}>
                <ArrowLeft size={17} /> {step === 0 ? "Cancelar" : "Anterior"}
              </button>

              {step < steps.length - 1 ? (
                <button type="button" className="nk-button nk-button--wine" onClick={goNext}>
                  Continuar <ArrowRight size={17} />
                </button>
              ) : (
                <button type="button" className="nk-button nk-button--wine" onClick={handleSubmit} disabled={submitting}>
                  {submitting ? <LoaderCircle size={18} className="is-spinning" /> : <ShieldCheck size={18} />}
                  {submitting ? "A enviar…" : "Enviar pedido"}
                </button>
              )}
            </footer>
          </section>

          <aside className="nk-access-help">
            <span><ShieldCheck size={22} /></span>
            <h3>Por que pedimos estes dados?</h3>
            <p>O NKATA não é uma plataforma de entrada automática. Cada pedido é analisado antes de o perfil ficar disponível.</p>
            <ul>
              <li><Check size={15} /> Confirmar que é uma pessoa adulta e real</li>
              <li><Check size={15} /> Reduzir perfis falsos e fotografias enganosas</li>
              <li><Check size={15} /> Proteger os contactos e documentos enviados</li>
            </ul>
            <small>JPG, PNG ou WEBP · máximo de 6 MB por imagem</small>
          </aside>
        </div>
      </section>
    </main>
  );
}
