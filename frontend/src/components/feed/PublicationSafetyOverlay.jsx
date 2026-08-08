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

const REPORT_REASONS = [
  { value: "NUDEZ_SEXUAL", label: "Nudez ou conteúdo sexual", icon: ShieldAlert },
  { value: "SERVICOS_SEXUAIS", label: "Serviços sexuais ou prostituição", icon: Ban },
  { value: "CONTACTOS_PUBLICIDADE", label: "Contactos, publicidade ou venda", icon: Megaphone },
  { value: "ASSEDIO", label: "Assédio, ameaça ou discurso ofensivo", icon: UserX },
  { value: "FRAUDE", label: "Fraude, perfil falso ou conteúdo enganoso", icon: BadgeAlert },
  { value: "PRIVACIDADE_TERCEIROS", label: "Exposição de terceiros sem consentimento", icon: EyeOff },
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
      setStatus(result.message || "Publicação ocultada.");
      window.setTimeout(() => setStatus(""), 3200);
    } catch (requestError) {
      setError(requestError.message || "Não foi possível ocultar esta publicação.");
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
      setStatus(result.message || "Denúncia recebida para análise.");
      window.setTimeout(() => setStatus(""), 4200);
    } catch (requestError) {
      setError(requestError.message || "Não foi possível enviar a denúncia.");
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
          aria-label="Opções de segurança da publicação"
          title="Opções"
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
            aria-label="Fechar opções da publicação"
          />

          <section
            className="nk-feed-safety-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby="nk-feed-safety-title"
          >
            <header>
              <div>
                <span>{mode === "report" ? "Segurança da comunidade" : "Publicação"}</span>
                <h2 id="nk-feed-safety-title">
                  {mode === "report" ? "Por que está a denunciar?" : "O que deseja fazer?"}
                </h2>
              </div>
              <button type="button" onClick={close} disabled={busy} aria-label="Fechar">
                <X size={20} />
              </button>
            </header>

            {mode === "menu" ? (
              <div className="nk-feed-safety-actions">
                <button type="button" onClick={handleHide} disabled={busy}>
                  <span><EyeOff size={20} /></span>
                  <div>
                    <strong>Ocultar esta publicação</strong>
                    <small>Deixa de aparecer apenas para si.</small>
                  </div>
                  {busy && <LoaderCircle size={18} className="is-spinning" />}
                </button>

                <button type="button" className="is-danger" onClick={() => setMode("report")} disabled={busy}>
                  <span><Flag size={20} /></span>
                  <div>
                    <strong>Denunciar publicação</strong>
                    <small>A equipa NKATA fará uma análise.</small>
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
                      <span>{reason.label}</span>
                      {busy && <LoaderCircle size={17} className="is-spinning" />}
                    </button>
                  );
                })}
                <button type="button" className="nk-feed-report-back" onClick={() => setMode("menu")} disabled={busy}>
                  Voltar
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
