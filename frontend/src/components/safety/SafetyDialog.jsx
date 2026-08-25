import { AlertTriangle, Ban, Flag, Link2Off, ShieldCheck, X } from "lucide-react";
import { useEffect, useState } from "react";
import useInterfaceLanguage from "../../hooks/useInterfaceLanguage.js";

const reportReasons = [
  { value: "PERFIL_FALSO", pt: "Suspeito que o perfil seja falso", en: "I suspect this profile is fake" },
  { value: "FOTO_SUSPEITA", pt: "A fotografia parece suspeita", en: "The photo looks suspicious" },
  { value: "COMPORTAMENTO_INADEQUADO", pt: "Comportamento inadequado", en: "Inappropriate behaviour" },
  { value: "DADOS_FALSOS", pt: "As informações parecem falsas", en: "The information appears false" },
  { value: "OUTRO", pt: "Outro motivo", en: "Another reason" },
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
  const english = useInterfaceLanguage() === "EN";
  const [reason, setReason] = useState("COMPORTAMENTO_INADEQUADO");
  const [details, setDetails] = useState("");
  const content = modeContent[mode] || modeContent.report;
  const translatedContent = english ? ({
    report: ["Send report", "Tell us what happened.", "The other person will not be told who reported them.", "Send report"],
    block: ["Block profile", "Block this person?", "This profile will no longer appear to you. Existing interests, match and conversation will be removed.", "Block profile"],
    close: ["End connection", "End this connection?", "The conversation will become unavailable to both people. This does not send a report.", "End connection"],
  })[mode] || [content.eyebrow, content.title, content.description, content.action] : null;
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
          aria-label={english ? "Close" : "Fechar"}
        >
          <X size={19} />
        </button>

        <span className={`nk-safety-dialog__icon is-${mode}`}>
          <Icon size={24} />
        </span>
        <span className="nk-safety-dialog__eyebrow">{english ? translatedContent[0] : content.eyebrow}</span>
        <h2 id="nk-safety-dialog-title">{english ? translatedContent[1] : content.title}</h2>
        <p>
          {personName ? `${personName}: ` : ""}
          {english ? translatedContent[2] : content.description}
        </p>

        <form onSubmit={handleSubmit}>
          {mode === "report" && (
            <div className="nk-safety-dialog__fields">
              <label>
                <span>{english ? "Reason" : "Motivo"}</span>
                <select
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  disabled={loading}
                >
                  {reportReasons.map((item) => (
                    <option key={item.value} value={item.value}>{english ? item.en : item.pt}</option>
                  ))}
                </select>
              </label>

              <label>
                <span>{english ? "Details" : "Detalhes"} {reason === "OUTRO" ? (english ? "(required)" : "(obrigatório)") : (english ? "(optional)" : "(opcional)")}</span>
                <textarea
                  value={details}
                  onChange={(event) => setDetails(event.target.value.slice(0, 1000))}
                  placeholder={english ? "Share only what our team needs to understand the situation." : "Explique apenas o necessário para a equipa compreender a situação."}
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
              <span>{english ? "Confirm only when you are sure." : "Confirme apenas quando tiver certeza."}</span>
            </div>
          )}

          {error && <div className="nk-safety-dialog__error">{error}</div>}

          <div className="nk-safety-dialog__actions">
            <button type="button" onClick={onClose} disabled={loading}>
              {english ? "Cancel" : "Cancelar"}
            </button>
            <button
              type="submit"
              className={`is-${mode}`}
              disabled={
                loading
                || (mode === "report" && reason === "OUTRO" && details.trim().length < 10)
              }
            >
              {loading ? (english ? "Processing…" : "A processar…") : (english ? translatedContent[3] : content.action)}
            </button>
          </div>
        </form>

        <footer>
          <ShieldCheck size={15} />
          <span>{english ? "These actions are handled privately by the NKATA team." : "Estas ações são tratadas de forma privada pela equipa NKATA."}</span>
        </footer>
      </section>
    </div>
  );
}
