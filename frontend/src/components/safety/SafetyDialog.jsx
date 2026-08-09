import { AlertTriangle, Ban, Flag, Link2Off, ShieldCheck, X } from "lucide-react";
import { useEffect, useState } from "react";

const reportReasons = [
  { value: "PERFIL_FALSO", label: "Suspeito que o perfil seja falso" },
  { value: "FOTO_SUSPEITA", label: "A fotografia parece suspeita" },
  { value: "COMPORTAMENTO_INADEQUADO", label: "Comportamento inadequado" },
  { value: "DADOS_FALSOS", label: "As informações parecem falsas" },
  { value: "OUTRO", label: "Outro motivo" },
];

const modeContent = {
  report: {
    icon: Flag,
    eyebrow: "Enviar denúncia",
    title: "Conte-nos o que aconteceu.",
    description: "A outra pessoa não será informada de que foi denunciada.",
    action: "Enviar denúncia",
  },
  block: {
    icon: Ban,
    eyebrow: "Bloquear perfil",
    title: "Bloquear esta pessoa?",
    description:
      "O perfil deixará de aparecer para si. Interesses, match e conversa existentes serão removidos.",
    action: "Bloquear perfil",
  },
  close: {
    icon: Link2Off,
    eyebrow: "Encerrar ligação",
    title: "Encerrar esta ligação?",
    description:
      "A conversa ficará indisponível para os dois. Esta ação não envia uma denúncia.",
    action: "Encerrar ligação",
  },
};

export default function SafetyDialog({
  open,
  mode,
  personName,
  loading = false,
  error = "",
  onClose,
  onConfirm,
}) {
  const [reason, setReason] = useState("COMPORTAMENTO_INADEQUADO");
  const [details, setDetails] = useState("");
  const content = modeContent[mode] || modeContent.report;
  const Icon = content.icon;

  useEffect(() => {
    if (!open) return;
    setReason("COMPORTAMENTO_INADEQUADO");
    setDetails("");
  }, [open, mode]);

  useEffect(() => {
    if (!open) return undefined;

    const handleKeyDown = (event) => {
      if (event.key === "Escape" && !loading) onClose?.();
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [loading, onClose, open]);

  if (!open) return null;

  const handleSubmit = async (event) => {
    event.preventDefault();

    await onConfirm?.(
      mode === "report"
        ? { reason, details: details.trim() }
        : {},
    );
  };

  return (
    <div
      className="nk-safety-dialog"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !loading) onClose?.();
      }}
    >
      <section
        className="nk-safety-dialog__card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="nk-safety-dialog-title"
      >
        <button
          type="button"
          className="nk-safety-dialog__close"
          onClick={onClose}
          disabled={loading}
          aria-label="Fechar"
        >
          <X size={19} />
        </button>

        <span className={`nk-safety-dialog__icon is-${mode}`}>
          <Icon size={24} />
        </span>
        <span className="nk-safety-dialog__eyebrow">{content.eyebrow}</span>
        <h2 id="nk-safety-dialog-title">{content.title}</h2>
        <p>
          {personName ? `${personName}: ` : ""}
          {content.description}
        </p>

        <form onSubmit={handleSubmit}>
          {mode === "report" && (
            <div className="nk-safety-dialog__fields">
              <label>
                <span>Motivo</span>
                <select
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  disabled={loading}
                >
                  {reportReasons.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </label>

              <label>
                <span>Detalhes {reason === "OUTRO" ? "(obrigatório)" : "(opcional)"}</span>
                <textarea
                  value={details}
                  onChange={(event) => setDetails(event.target.value.slice(0, 1000))}
                  placeholder="Explique apenas o necessário para a equipa compreender a situação."
                  rows={4}
                  disabled={loading}
                />
                <small>{details.length}/1000</small>
              </label>
            </div>
          )}

          {mode !== "report" && (
            <div className="nk-safety-dialog__notice">
              <AlertTriangle size={18} />
              <span>Confirme apenas quando tiver certeza.</span>
            </div>
          )}

          {error && <div className="nk-safety-dialog__error">{error}</div>}

          <div className="nk-safety-dialog__actions">
            <button type="button" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button
              type="submit"
              className={`is-${mode}`}
              disabled={
                loading
                || (mode === "report" && reason === "OUTRO" && details.trim().length < 10)
              }
            >
              {loading ? "A processar…" : content.action}
            </button>
          </div>
        </form>

        <footer>
          <ShieldCheck size={15} />
          <span>Estas ações são tratadas de forma privada pela equipa NKATA.</span>
        </footer>
      </section>
    </div>
  );
}
