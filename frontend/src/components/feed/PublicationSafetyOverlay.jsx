import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import {
  BadgeAlert,
  Ban,
  CheckCircle2,
  Ellipsis,
  EyeOff,
  Flag,
  LoaderCircle,
  Megaphone,
  ShieldAlert,
  UserX,
  X,
} from "lucide-react";
import { hidePublication, reportPublication } from "../../services/feedSafetyApi.js";
import useInterfaceLanguage from "../../hooks/useInterfaceLanguage.js";

const REPORT_REASONS = [
  { value: "NUDEZ_SEXUAL", pt: "Nudez ou conteúdo sexual", en: "Nudity or sexual content", icon: ShieldAlert },
  { value: "SERVICOS_SEXUAIS", pt: "Serviços sexuais ou prostituição", en: "Sexual services or prostitution", icon: Ban },
  { value: "CONTACTOS_PUBLICIDADE", pt: "Contactos, publicidade ou venda", en: "Contact details, advertising or sales", icon: Megaphone },
  { value: "ASSEDIO", pt: "Assédio, ameaça ou discurso ofensivo", en: "Harassment, threats or offensive speech", icon: UserX },
  { value: "FRAUDE", pt: "Fraude, perfil falso ou conteúdo enganoso", en: "Fraud, fake profile or misleading content", icon: BadgeAlert },
  { value: "PRIVACIDADE_TERCEIROS", pt: "Exposição de terceiros sem consentimento", en: "Sharing another person's information without consent", icon: EyeOff },
];

function publicationIdFromCard(card) {
  const media = card.querySelector(".nk-feed-card__media");
  const source = media?.getAttribute("src") || media?.src || "";
  const match = source.match(/\/api\/publicacoes\/(\d+)\/media\//);
  return match?.[1] || "";
}

function discoverTargets() {
  return [...document.querySelectorAll(".nk-feed-card")]
    .filter((card) => !card.querySelector(".nk-feed-card__delete"))
    .map((card) => ({
      id: publicationIdFromCard(card),
      card,
      header: card.querySelector(".nk-feed-card__header"),
    }))
    .filter((item) => item.id && item.header);
}

export default function PublicationSafetyOverlay() {
  const english = useInterfaceLanguage() === "EN";
  const [targets, setTargets] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [mode, setMode] = useState("menu");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const refreshTargets = useCallback(() => {
    const next = discoverTargets();
    setTargets((current) => {
      const same = current.length === next.length && next.every((item, index) => (
        item.id === current[index]?.id
        && item.card === current[index]?.card
        && item.header === current[index]?.header
      ));
      return same ? current : next;
    });
  }, []);

  useEffect(() => {
    refreshTargets();
    const observer = new MutationObserver(refreshTargets);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [refreshTargets]);

  useEffect(() => {
    if (!selectedId) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [selectedId]);

  const selectedTarget = useMemo(
    () => targets.find((item) => item.id === selectedId) || null,
    [selectedId, targets],
  );

  useEffect(() => {
    if (selectedId && !selectedTarget) {
      setSelectedId("");
      setMode("menu");
    }
  }, [selectedId, selectedTarget]);

  const open = (id) => {
    setSelectedId(id);
    setMode("menu");
    setError("");
  };

  const close = () => {
    if (busy) return;
    setSelectedId("");
    setMode("menu");
    setError("");
  };

  const hideCard = () => {
    selectedTarget?.card?.classList.add("nk-feed-card--hidden-by-user");
  };

  const handleHide = async () => {
    if (!selectedId || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await hidePublication(selectedId);
      hideCard();
      setSelectedId("");
      setStatus(result.message || (english ? "Post hidden." : "Publicação ocultada."));
      window.setTimeout(() => setStatus(""), 3200);
    } catch (requestError) {
      setError(requestError.message || (english ? "Unable to hide this post." : "Não foi possível ocultar esta publicação."));
    } finally {
      setBusy(false);
    }
  };

  const handleReport = async (reason) => {
    if (!selectedId || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await reportPublication(selectedId, reason);
      hideCard();
      setSelectedId("");
      setMode("menu");
      setStatus(result.message || (english ? "Report received for review." : "Denúncia recebida para análise."));
      window.setTimeout(() => setStatus(""), 4200);
    } catch (requestError) {
      setError(requestError.message || (english ? "Unable to send the report." : "Não foi possível enviar a denúncia."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {targets.map((target) => createPortal(
        <button
          key={`safety-${target.id}`}
          type="button"
          className="nk-feed-safety-trigger"
          onClick={() => open(target.id)}
          aria-label={english ? "Post safety options" : "Opções de segurança da publicação"}
          title={english ? "Options" : "Opções"}
        >
          <Ellipsis size={19} />
        </button>,
        target.header,
      ))}

      {selectedId && createPortal(
        <div className="nk-feed-safety-layer" role="presentation">
          <button
            type="button"
            className="nk-feed-safety-backdrop"
            onClick={close}
            aria-label={english ? "Close post options" : "Fechar opções da publicação"}
          />

          <section
            className="nk-feed-safety-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby="nk-feed-safety-title"
          >
            <header>
              <div>
                <span>{mode === "report" ? (english ? "Community safety" : "Segurança da comunidade") : (english ? "Post" : "Publicação")}</span>
                <h2 id="nk-feed-safety-title">
                  {mode === "report" ? (english ? "Why are you reporting this?" : "Por que está a denunciar?") : (english ? "What would you like to do?" : "O que deseja fazer?")}
                </h2>
              </div>
              <button type="button" onClick={close} disabled={busy} aria-label={english ? "Close" : "Fechar"}>
                <X size={20} />
              </button>
            </header>

            {mode === "menu" ? (
              <div className="nk-feed-safety-actions">
                <button type="button" onClick={handleHide} disabled={busy}>
                  <span><EyeOff size={20} /></span>
                  <div>
                    <strong>{english ? "Hide this post" : "Ocultar esta publicação"}</strong>
                    <small>{english ? "It will only disappear for you." : "Deixa de aparecer apenas para si."}</small>
                  </div>
                  {busy && <LoaderCircle size={18} className="is-spinning" />}
                </button>

                <button type="button" className="is-danger" onClick={() => setMode("report")} disabled={busy}>
                  <span><Flag size={20} /></span>
                  <div>
                    <strong>{english ? "Report post" : "Denunciar publicação"}</strong>
                    <small>{english ? "The NKATA team will review it." : "A equipa NKATA fará uma análise."}</small>
                  </div>
                </button>
              </div>
            ) : (
              <div className="nk-feed-report-reasons">
                {REPORT_REASONS.map((reason) => {
                  const Icon = reason.icon;
                  return (
                    <button
                      key={reason.value}
                      type="button"
                      onClick={() => handleReport(reason.value)}
                      disabled={busy}
                    >
                      <Icon size={19} />
                      <span>{english ? reason.en : reason.pt}</span>
                      {busy && <LoaderCircle size={17} className="is-spinning" />}
                    </button>
                  );
                })}
                <button type="button" className="nk-feed-report-back" onClick={() => setMode("menu")} disabled={busy}>
                  {english ? "Back" : "Voltar"}
                </button>
              </div>
            )}

            {error && <div className="nk-feed-safety-error" role="alert">{error}</div>}
          </section>
        </div>,
        document.body,
      )}

      {status && createPortal(
        <div className="nk-feed-safety-toast" role="status">
          <CheckCircle2 size={18} />
          <span>{status}</span>
        </div>,
        document.body,
      )}
    </>
  );
}
