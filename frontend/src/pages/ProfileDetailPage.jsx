import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  BadgeCheck,
  Ban,
  Flag,
  Flower2,
  Hand,
  Heart,
  LockKeyhole,
  MapPin,
  Share2,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import SafetyDialog from "../components/safety/SafetyDialog.jsx";
import { blockProfile, reportProfile } from "../services/api.js";
import { fetchProfileSignals, sendProfileSignal } from "../services/signalApi.js";

const DEFAULT_SIGNALS = [
  { type: "FLOR", label: "Flor", icon: "flower", message: "Uma flor para mostrar que este perfil chamou a sua atenção." },
  { type: "BEIJINHO", label: "Beijinho", icon: "heart", message: "Um gesto carinhoso, sem abrir uma conversa privada." },
  { type: "OLA", label: "Olá", icon: "hand", message: "Olá, gostei do seu perfil e gostaria de conhecer melhor." },
];

const SIGNAL_ICONS = {
  FLOR: Flower2,
  BEIJINHO: Heart,
  OLA: Hand,
};

function DetailBlock({ title, children }) {
  return (
    <section className="nk-profile-detail__block">
      <span>{title}</span>
      <p>{children}</p>
    </section>
  );
}

export default function ProfileDetailPage({
  profile,
  loading,
  error,
  saved,
  authenticated,
  interestActive,
  interestLoading,
  interestMessage,
  onToggleSaved,
  onToggleInterest,
  onRequireLogin,
  onBack,
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const [shareStatus, setShareStatus] = useState("");
  const [safetyMode, setSafetyMode] = useState("");
  const [safetyLoading, setSafetyLoading] = useState(false);
  const [safetyError, setSafetyError] = useState("");
  const [safetyStatus, setSafetyStatus] = useState("");
  const [signalData, setSignalData] = useState(null);
  const [signalLoading, setSignalLoading] = useState(false);
  const [signalSending, setSignalSending] = useState("");
  const [signalError, setSignalError] = useState("");
  const [signalStatus, setSignalStatus] = useState("");

  const hasImage = Boolean(profile?.foto_url) && !imageFailed;
  const profileUrl = useMemo(() => {
    if (!profile?.id || String(profile.id).startsWith("demo-")) return null;
    return new URL(`/perfis/${profile.id}/`, window.location.origin).toString();
  }, [profile?.id]);

  useEffect(() => {
    if (!authenticated || !profile?.id || String(profile.id).startsWith("demo-")) {
      setSignalData(null);
      setSignalLoading(false);
      return undefined;
    }

    const controller = new AbortController();
    setSignalLoading(true);
    setSignalError("");

    fetchProfileSignals(profile.id, { signal: controller.signal })
      .then((payload) => setSignalData(payload))
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          setSignalError(requestError.message || "Não foi possível consultar os sinais disponíveis.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setSignalLoading(false);
      });

    return () => controller.abort();
  }, [authenticated, profile?.id]);

  const handleShare = async () => {
    if (!profile) return;

    const shareUrl = profileUrl || window.location.href;
    const shareData = {
      title: `${profile.nome_publico} no NKATA`,
      text: `Veja o perfil de ${profile.nome_publico} no NKATA.`,
      url: shareUrl,
    };

    try {
      if (navigator.share) {
        await navigator.share(shareData);
        setShareStatus("Partilhado");
      } else {
        await navigator.clipboard.writeText(shareUrl);
        setShareStatus("Link copiado");
      }
    } catch (shareError) {
      if (shareError.name !== "AbortError") setShareStatus("Não foi possível partilhar");
    }

    window.setTimeout(() => setShareStatus(""), 2200);
  };

  const openSafetyAction = (mode) => {
    if (!authenticated) {
      onRequireLogin?.();
      return;
    }

    if (!profile?.id || String(profile.id).startsWith("demo-")) return;
    setSafetyError("");
    setSafetyMode(mode);
  };

  const handleSafetyConfirm = async ({ reason, details } = {}) => {
    if (!profile?.id || !safetyMode) return;

    const currentMode = safetyMode;
    setSafetyLoading(true);
    setSafetyError("");

    try {
      const result = currentMode === "report"
        ? await reportProfile(profile.id, { reason, details })
        : await blockProfile(profile.id);

      setSafetyMode("");
      setSafetyStatus(result?.message || "A ação foi concluída.");

      if (currentMode === "block") {
        window.setTimeout(() => window.location.assign("/perfis/"), 1000);
      } else {
        window.setTimeout(() => setSafetyStatus(""), 3200);
      }
    } catch (requestError) {
      setSafetyError(requestError.message || "Não foi possível concluir esta ação.");
    } finally {
      setSafetyLoading(false);
    }
  };

  const handleSignal = async (type) => {
    if (!authenticated) {
      onRequireLogin?.();
      return;
    }
    if (!profile?.id || String(profile.id).startsWith("demo-")) return;

    setSignalSending(type);
    setSignalError("");
    setSignalStatus("");

    try {
      const result = await sendProfileSignal(profile.id, type);
      setSignalData({ quota: result.quota, signals: result.signals });
      setSignalStatus(result.message || "Sinal enviado.");
      window.setTimeout(() => setSignalStatus(""), 3200);
    } catch (requestError) {
      if (requestError.payload?.quota) {
        setSignalData((current) => ({
          ...(current || {}),
          quota: requestError.payload.quota,
          signals: requestError.payload.signals || current?.signals || DEFAULT_SIGNALS,
        }));
      }
      setSignalError(requestError.message || "Não foi possível enviar este sinal.");
    } finally {
      setSignalSending("");
    }
  };

  if (!profile && loading) {
    return (
      <main className="nk-profile-detail nk-profile-detail--loading">
        <div className="nk-shell nk-profile-detail__skeleton">
          <div />
          <section><span /><span /><span /></section>
        </div>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="nk-profile-detail nk-profile-detail--empty">
        <div className="nk-shell nk-profile-detail__empty-card">
          <ShieldCheck size={30} />
          <h1>Perfil não disponível</h1>
          <p>{error || "Não foi possível abrir este perfil agora."}</p>
          <button type="button" className="nk-button nk-button--wine" onClick={onBack}>
            Voltar aos perfis
          </button>
        </div>
      </main>
    );
  }

  const handleInterest = () => {
    if (!authenticated) {
      onRequireLogin?.();
      return;
    }
    onToggleInterest?.(profile);
  };

  const quota = signalData?.quota || null;
  const signals = signalData?.signals?.length ? signalData.signals : DEFAULT_SIGNALS;
  const limitReached = Boolean(quota?.limit_reached);

  return (
    <main className="nk-profile-detail">
      <div className="nk-shell">
        <button type="button" className="nk-profile-detail__back" onClick={onBack}>
          <ArrowLeft size={18} /> Voltar
        </button>

        <div className="nk-profile-detail__layout">
          <aside className="nk-profile-detail__media">
            {hasImage ? (
              <img
                src={profile.foto_url}
                alt={`Foto de ${profile.nome_publico}`}
                onError={() => setImageFailed(true)}
              />
            ) : (
              <div className="nk-profile-detail__fallback">
                <UserRound size={64} strokeWidth={1.15} />
                <span>Sem fotografia</span>
              </div>
            )}

            <div className="nk-profile-detail__media-shade" />
            <span className="nk-profile-detail__verified">
              <BadgeCheck size={16} />
              {profile.verificado ? "Perfil verificado" : "Em análise"}
            </span>
            <div className="nk-profile-detail__media-copy">
              <span>{profile.objetivo_display}</span>
              <strong>{profile.nome_publico}{profile.idade ? `, ${profile.idade}` : ""}</strong>
              <small><MapPin size={14} /> {profile.cidade}</small>
            </div>
          </aside>

          <section className="nk-profile-detail__content">
            <div className="nk-profile-detail__heading">
              <div>
                <span className="nk-eyebrow nk-eyebrow--dark">
                  <ShieldCheck size={15} /> Perfil verificado
                </span>
                <h1>{profile.nome_publico}{profile.idade ? `, ${profile.idade}` : ""}</h1>
                <p>{profile.objetivo_display}</p>
              </div>

              <div className="nk-profile-detail__quick-actions">
                <button
                  type="button"
                  className={`nk-profile-detail__save ${saved ? "is-saved" : ""}`}
                  onClick={() => onToggleSaved?.(profile)}
                  aria-pressed={saved}
                >
                  <Heart size={19} fill={saved ? "currentColor" : "none"} />
                  {saved ? "Guardado" : "Guardar"}
                </button>
                <button type="button" className="nk-profile-detail__share" onClick={handleShare}>
                  <Share2 size={18} /> {shareStatus || "Partilhar"}
                </button>
              </div>
            </div>

            {error && <div className="nk-profile-detail__notice">Alguns dados deste perfil não foram atualizados.</div>}
            {safetyStatus && <div className="nk-interest-message is-active" role="status">{safetyStatus}</div>}

            <div className="nk-profile-detail__blocks">
              <DetailBlock title="Sobre mim">
                {profile.sobre_si || "Esta pessoa ainda não acrescentou uma apresentação."}
              </DetailBlock>
              <DetailBlock title="O que valorizo">
                {profile.o_que_valoriza || "Ainda não foi preenchido."}
              </DetailBlock>
              <DetailBlock title="O que não aceito">
                {profile.o_que_nao_aceita || "Ainda não foi preenchido."}
              </DetailBlock>
            </div>

            <div className="nk-profile-detail__assurance">
              <span><LockKeyhole size={18} /></span>
              <div>
                <strong>Telefone, email e documentos não são mostrados</strong>
                <p>Os contactos só são partilhados quando existir autorização dos dois lados.</p>
              </div>
            </div>

            <section className={`nk-profile-signals ${limitReached ? "is-locked" : ""}`}>
              <div className="nk-profile-signals__heading">
                <div>
                  <span>Sinais NKATA</span>
                  <h2>Um gesto simples, antes da conversa.</h2>
                  <p>
                    {authenticated && quota
                      ? `${quota.plan_label}: ${quota.daily_limit} sinais por dia. A recarga só é usada depois desse limite.`
                      : "Envie uma flor, um beijinho ou um olá sem abrir o chat."}
                  </p>
                </div>
                {authenticated && quota && (
                  <strong className="nk-profile-signals__quota">
                    {quota.used_today} de {quota.daily_limit} no plano
                    {quota.recharge_balance > 0 ? ` · +${quota.recharge_balance} recarga` : ""}
                  </strong>
                )}
              </div>

              <div className="nk-profile-signals__grid">
                {signals.map((signal) => {
                  const sent = Boolean(signal.sent_to_profile_today);
                  const busy = signalSending === signal.type;
                  const SignalIcon = SIGNAL_ICONS[signal.type] || Sparkles;
                  const disabled = (
                    signalLoading
                    || Boolean(signalSending)
                    || sent
                    || limitReached
                    || String(profile.id).startsWith("demo-")
                  );

                  return (
                    <button
                      type="button"
                      key={signal.type}
                      className={sent ? "is-sent" : ""}
                      onClick={() => handleSignal(signal.type)}
                      disabled={authenticated ? disabled : false}
                      title={signal.message}
                    >
                      <span className="nk-profile-signals__icon" aria-hidden="true">
                        <SignalIcon size={27} strokeWidth={1.55} />
                      </span>
                      <strong>{signal.label}</strong>
                      <small>
                        {!authenticated
                          ? "Entrar para enviar"
                          : busy
                            ? "A enviar…"
                            : sent
                              ? "Enviado hoje"
                              : limitReached
                                ? "Limite atingido"
                                : quota?.next_source === "RECHARGE"
                                  ? "Usar recarga"
                                  : "Enviar sinal"}
                      </small>
                    </button>
                  );
                })}
              </div>

              {!authenticated && (
                <button type="button" className="nk-profile-signals__login" onClick={onRequireLogin}>
                  Entrar para usar os sinais do seu plano
                </button>
              )}

              {signalLoading && authenticated && (
                <small className="nk-profile-signals__loading">A confirmar o seu plano e os sinais de hoje…</small>
              )}
              {signalStatus && <div className="nk-profile-signals__message is-success">{signalStatus}</div>}
              {signalError && <div className="nk-profile-signals__message is-error">{signalError}</div>}

              {limitReached && quota && (
                <div className="nk-profile-signals__limit">
                  <LockKeyhole size={18} />
                  <div>
                    <strong>O limite do {quota.plan_label} foi usado hoje.</strong>
                    <span>Não existe saldo de recarga. Novos sinais ficam disponíveis no próximo dia ou com uma futura recarga.</span>
                  </div>
                </div>
              )}
            </section>

            <div className="nk-profile-safety">
              <span>Algo não parece certo? A equipa pode ajudar.</span>
              <div className="nk-profile-safety__actions">
                <button type="button" onClick={() => openSafetyAction("report")}>
                  <Flag size={15} /> Denunciar
                </button>
                <button
                  type="button"
                  className="is-danger"
                  onClick={() => openSafetyAction("block")}
                >
                  <Ban size={15} /> Bloquear
                </button>
              </div>
            </div>

            {interestMessage && (
              <div className={`nk-interest-message ${interestActive ? "is-active" : ""}`} role="status">
                {interestMessage}
              </div>
            )}

            <div className="nk-profile-detail__actions">
              <button
                type="button"
                className={`nk-button nk-button--wine ${interestActive ? "is-active" : ""}`}
                onClick={handleInterest}
                disabled={interestLoading || String(profile.id).startsWith("demo-")}
              >
                <Sparkles size={18} />
                {interestLoading
                  ? "A guardar…"
                  : !authenticated
                    ? "Entrar para demonstrar interesse"
                    : interestActive
                      ? "Interesse enviado"
                      : "Tenho interesse"}
              </button>
              <button type="button" className="nk-button nk-button--quiet" onClick={onBack}>
                Ver outros perfis
              </button>
            </div>

            {loading && <span className="nk-profile-detail__updating">A atualizar o perfil…</span>}
          </section>
        </div>
      </div>

      <SafetyDialog
        open={Boolean(safetyMode)}
        mode={safetyMode}
        personName={profile.nome_publico}
        loading={safetyLoading}
        error={safetyError}
        onClose={() => !safetyLoading && setSafetyMode("")}
        onConfirm={handleSafetyConfirm}
      />
    </main>
  );
}
