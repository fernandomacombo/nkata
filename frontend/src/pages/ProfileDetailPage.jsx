import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  BadgeCheck,
  Ban,
  Flag,
  Flower2,
  Hand,
  Heart,
  Images,
  LockKeyhole,
  MapPin,
  Play,
  Share2,
  ShieldCheck,
  Sparkles,
  UserRound,
  X,
} from "lucide-react";
import SafetyDialog from "../components/safety/SafetyDialog.jsx";
import useInterfaceLanguage from "../hooks/useInterfaceLanguage.js";
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

const objectiveLabel = (value, english) => english ? ({
  "Relacionamento sério": "Serious relationship",
  "Conhecer com intenção": "Meet with intention",
  "Casamento no futuro": "Marriage in the future",
  "Amizade que pode evoluir": "Friendship that may grow",
})[value] || value : value;

const signalLabels = {
  FLOR: ["Flower", "A flower to show that this profile caught your attention."],
  BEIJINHO: ["Kiss", "A warm gesture without opening a private conversation."],
  OLA: ["Hello", "Hello, I liked your profile and would like to know you better."],
};

function DetailBlock({ title, children }) {
  return (
    <section className="nk-profile-detail__block">
      <span>{title}</span>
      <p>{children}</p>
    </section>
  );
}

function ProfileGallery({ items, personName, english }) {
  const [selected, setSelected] = useState(null);
  if (!items?.length) return null;

  return (
    <section className="nk-profile-gallery">
      <header>
        <span><Images size={17} /></span>
        <div>
          <h2>{english ? "Gallery" : "Galeria"}</h2>
          <p>{items.length} {english ? (items.length === 1 ? "post" : "posts") : (items.length === 1 ? "publicação" : "publicações")}</p>
        </div>
      </header>

      <div className="nk-profile-gallery__grid">
        {items.map((item) => (
          <button
            type="button"
            key={item.id}
            onClick={() => setSelected(item)}
            aria-label={`${english ? "Open post by" : "Abrir publicação de"} ${personName}`}
          >
            {item.mediaType === "VIDEO" ? (
              <>
                <video src={item.mediaUrl} muted playsInline preload="metadata" />
                <span><Play size={20} fill="currentColor" /></span>
              </>
            ) : (
              <img src={item.mediaUrl} alt="" loading="lazy" />
            )}
          </button>
        ))}
      </div>

      {selected && (
        <div
          className="nk-profile-gallery__viewer"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setSelected(null);
          }}
        >
          <section role="dialog" aria-modal="true" aria-label={`${english ? "Post by" : "Publicação de"} ${personName}`}>
            <button type="button" onClick={() => setSelected(null)} aria-label={english ? "Close post" : "Fechar publicação"}>
              <X size={21} />
            </button>
            {selected.mediaType === "VIDEO" ? (
              <video src={selected.mediaUrl} controls autoPlay playsInline />
            ) : (
              <img src={selected.mediaUrl} alt={`${english ? "Post by" : "Publicação de"} ${personName}`} />
            )}
          </section>
        </div>
      )}
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
  const english = useInterfaceLanguage() === "EN";
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
          setSignalError(requestError.message || (english ? "Unable to load available signals." : "Não foi possível consultar os sinais disponíveis."));
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
      title: `${profile.nome_publico} ${english ? "on" : "no"} NKATA`,
      text: `${english ? "View the profile of" : "Veja o perfil de"} ${profile.nome_publico} ${english ? "on" : "no"} NKATA.`,
      url: shareUrl,
    };

    try {
      if (navigator.share) {
        await navigator.share(shareData);
        setShareStatus(english ? "Shared" : "Partilhado");
      } else {
        await navigator.clipboard.writeText(shareUrl);
        setShareStatus(english ? "Link copied" : "Link copiado");
      }
    } catch (shareError) {
      if (shareError.name !== "AbortError") setShareStatus(english ? "Unable to share" : "Não foi possível partilhar");
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
      setSafetyStatus(result?.message || (english ? "Action completed." : "A ação foi concluída."));

      if (currentMode === "block") {
        window.setTimeout(() => window.location.assign("/perfis/"), 1000);
      } else {
        window.setTimeout(() => setSafetyStatus(""), 3200);
      }
    } catch (requestError) {
      setSafetyError(requestError.message || (english ? "Unable to complete this action." : "Não foi possível concluir esta ação."));
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
      setSignalStatus(result.message || (english ? "Signal sent." : "Sinal enviado."));
      window.setTimeout(() => setSignalStatus(""), 3200);
    } catch (requestError) {
      if (requestError.payload?.quota) {
        setSignalData((current) => ({
          ...(current || {}),
          quota: requestError.payload.quota,
          signals: requestError.payload.signals || current?.signals || DEFAULT_SIGNALS,
        }));
      }
      setSignalError(requestError.message || (english ? "Unable to send this signal." : "Não foi possível enviar este sinal."));
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
          <h1>{english ? "Profile unavailable" : "Perfil não disponível"}</h1>
          <p>{error || (english ? "Unable to open this profile right now." : "Não foi possível abrir este perfil agora.")}</p>
          <button type="button" className="nk-button nk-button--wine" onClick={onBack}>
            {english ? "Back to profiles" : "Voltar aos perfis"}
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
    <main className={`nk-profile-detail nk-profile-detail--theme-${profile.tema_perfil || "classico"}`}>
      <div className="nk-shell">
        <button type="button" className="nk-profile-detail__back" onClick={onBack}>
          <ArrowLeft size={18} /> {english ? "Back" : "Voltar"}
        </button>

        {profile.cover_url && (
          <div className="nk-profile-detail__cover" aria-hidden="true">
            <img
              src={profile.cover_url}
              alt=""
              onError={(event) => { event.currentTarget.hidden = true; }}
            />
            <div />
          </div>
        )}

        <div className={`nk-profile-detail__layout ${profile.cover_url ? "has-cover" : ""}`}>
          <aside className="nk-profile-detail__media">
            {hasImage ? (
              <img
                src={profile.foto_url}
                alt={`${english ? "Photo of" : "Foto de"} ${profile.nome_publico}`}
                onError={() => setImageFailed(true)}
              />
            ) : (
              <div className="nk-profile-detail__fallback">
                <UserRound size={64} strokeWidth={1.15} />
                <span>{english ? "No photo" : "Sem fotografia"}</span>
              </div>
            )}

            <div className="nk-profile-detail__media-shade" />
            <span className="nk-profile-detail__verified">
              <BadgeCheck size={16} />
              {profile.verificado ? (english ? "Verified profile" : "Perfil verificado") : (english ? "Under review" : "Em análise")}
            </span>
            <div className="nk-profile-detail__media-copy">
              <span>{objectiveLabel(profile.objetivo_display, english)}</span>
              <strong>{profile.nome_publico}{profile.idade ? `, ${profile.idade}` : ""}</strong>
              <small><MapPin size={14} /> {profile.cidade}</small>
            </div>
          </aside>

          <section className="nk-profile-detail__content">
            <div className="nk-profile-detail__heading">
              <div>
                <span className="nk-eyebrow nk-eyebrow--dark">
                  <ShieldCheck size={15} /> {english ? "Verified profile" : "Perfil verificado"}
                </span>
                <h1>{profile.nome_publico}{profile.idade ? `, ${profile.idade}` : ""}</h1>
                <p>{objectiveLabel(profile.objetivo_display, english)}</p>
              </div>

              <div className="nk-profile-detail__quick-actions">
                <button
                  type="button"
                  className={`nk-profile-detail__save ${saved ? "is-saved" : ""}`}
                  onClick={() => onToggleSaved?.(profile)}
                  aria-pressed={saved}
                >
                  <Heart size={19} fill={saved ? "currentColor" : "none"} />
                  {saved ? (english ? "Saved" : "Guardado") : (english ? "Save" : "Guardar")}
                </button>
                <button type="button" className="nk-profile-detail__share" onClick={handleShare}>
                  <Share2 size={18} /> {shareStatus || (english ? "Share" : "Partilhar")}
                </button>
              </div>
            </div>

            {error && <div className="nk-profile-detail__notice">{english ? "Some profile details could not be refreshed." : "Alguns dados deste perfil não foram atualizados."}</div>}
            {safetyStatus && <div className="nk-interest-message is-active" role="status">{safetyStatus}</div>}

            <div className="nk-profile-detail__blocks">
              <DetailBlock title={english ? "About me" : "Sobre mim"}>
                {profile.sobre_si || (english ? "This person has not added an introduction yet." : "Esta pessoa ainda não acrescentou uma apresentação.")}
              </DetailBlock>
              <DetailBlock title={english ? "What I value" : "O que valorizo"}>
                {profile.o_que_valoriza || (english ? "Not filled in yet." : "Ainda não foi preenchido.")}
              </DetailBlock>
              <DetailBlock title={english ? "What I don't accept" : "O que não aceito"}>
                {profile.o_que_nao_aceita || (english ? "Not filled in yet." : "Ainda não foi preenchido.")}
              </DetailBlock>
            </div>

            <ProfileGallery items={profile.gallery} personName={profile.nome_publico} english={english} />

            <div className="nk-profile-detail__assurance">
              <span><LockKeyhole size={18} /></span>
              <div>
                <strong>{english ? "Phone, email and documents are not shown" : "Telefone, email e documentos não são mostrados"}</strong>
                <p>{english ? "Contact details require consent from both people." : "Os contactos exigem autorização dos dois lados."}</p>
              </div>
            </div>

            <section className={`nk-profile-signals ${limitReached ? "is-locked" : ""}`}>
              <div className="nk-profile-signals__heading">
                <div>
                  <span>{english ? "NKATA signals" : "Sinais NKATA"}</span>
                  <h2>{english ? "Send a signal" : "Enviar um sinal"}</h2>
                  <p>
                    {authenticated && quota
                      ? (english ? `${quota.daily_limit} daily signals on your ${quota.plan_label} plan.` : `${quota.daily_limit} sinais diários no plano ${quota.plan_label}.`)
                      : (english ? "Show interest without starting a conversation." : "Mostre interesse sem iniciar uma conversa.")}
                  </p>
                </div>
                {authenticated && quota && (
                  <strong className="nk-profile-signals__quota">
                    {quota.used_today} {english ? "of" : "de"} {quota.daily_limit} {english ? "used" : "no plano"}
                    {quota.recharge_balance > 0 ? ` · +${quota.recharge_balance} ${english ? "top-up" : "recarga"}` : ""}
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
                  const translatedSignal = signalLabels[signal.type];

                  return (
                    <button
                      type="button"
                      key={signal.type}
                      className={sent ? "is-sent" : ""}
                      onClick={() => handleSignal(signal.type)}
                      disabled={authenticated ? disabled : false}
                      title={english ? (translatedSignal?.[1] || signal.message) : signal.message}
                    >
                      <span className="nk-profile-signals__icon" aria-hidden="true">
                        <SignalIcon size={27} strokeWidth={1.55} />
                      </span>
                      <strong>{english ? (translatedSignal?.[0] || signal.label) : signal.label}</strong>
                      <small>
                        {!authenticated
                          ? (english ? "Sign in to send" : "Entrar para enviar")
                          : busy
                            ? (english ? "Sending…" : "A enviar…")
                            : sent
                              ? (english ? "Sent today" : "Enviado hoje")
                              : limitReached
                                ? (english ? "Limit reached" : "Limite atingido")
                                : quota?.next_source === "RECHARGE"
                                  ? (english ? "Use top-up" : "Usar recarga")
                                  : (english ? "Send signal" : "Enviar sinal")}
                      </small>
                    </button>
                  );
                })}
              </div>

              {!authenticated && (
                <button type="button" className="nk-profile-signals__login" onClick={onRequireLogin}>
                  {english ? "Sign in to use your plan's signals" : "Entrar para usar os sinais do seu plano"}
                </button>
              )}

              {signalLoading && authenticated && (
                <small className="nk-profile-signals__loading">{english ? "Checking your plan and today's signals…" : "A confirmar o seu plano e os sinais de hoje…"}</small>
              )}
              {signalStatus && <div className="nk-profile-signals__message is-success">{signalStatus}</div>}
              {signalError && <div className="nk-profile-signals__message is-error">{signalError}</div>}

              {limitReached && quota && (
                <div className="nk-profile-signals__limit">
                  <LockKeyhole size={18} />
                  <div>
                    <strong>{english ? `Today's ${quota.plan_label} limit has been used.` : `O limite do ${quota.plan_label} foi usado hoje.`}</strong>
                    <span>{english ? "There is no top-up balance. New signals become available tomorrow or after a future top-up." : "Não existe saldo de recarga. Novos sinais ficam disponíveis no próximo dia ou com uma futura recarga."}</span>
                  </div>
                </div>
              )}
            </section>

            <div className="nk-profile-safety">
              <span>{english ? "Something doesn't feel right? Our team can help." : "Algo não parece certo? A equipa pode ajudar."}</span>
              <div className="nk-profile-safety__actions">
                <button type="button" onClick={() => openSafetyAction("report")}>
                  <Flag size={15} /> {english ? "Report" : "Denunciar"}
                </button>
                <button
                  type="button"
                  className="is-danger"
                  onClick={() => openSafetyAction("block")}
                >
                  <Ban size={15} /> {english ? "Block" : "Bloquear"}
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
                  ? (english ? "Saving…" : "A guardar…")
                  : !authenticated
                    ? (english ? "Sign in to show interest" : "Entrar para demonstrar interesse")
                    : interestActive
                      ? (english ? "Interest sent" : "Interesse enviado")
                      : (english ? "I'm interested" : "Tenho interesse")}
              </button>
              <button type="button" className="nk-button nk-button--quiet" onClick={onBack}>
                {english ? "View other profiles" : "Ver outros perfis"}
              </button>
            </div>

            {loading && <span className="nk-profile-detail__updating">{english ? "Refreshing profile…" : "A atualizar o perfil…"}</span>}
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
