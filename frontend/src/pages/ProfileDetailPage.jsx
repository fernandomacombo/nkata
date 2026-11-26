import Presence from "../components/profiles/Presence.jsx";
import { ProfilePreferences } from "../components/MatchPreferences";
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
  MessageCircle,
  MoreHorizontal,
  Maximize2,
  ChevronLeft,
  ChevronRight,
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
  { type: "OLA", label: "Olá", icon: "hand", message: "Olá, gostei do seu perfil e gostaria de conhecer melhor." },
  { type: "FLOR", label: "Flor", icon: "flower", message: "Uma flor para mostrar que este perfil chamou a sua atenção." },
  { type: "BEIJINHO", label: "Beijinho", icon: "heart", message: "Um gesto carinhoso, sem abrir uma conversa privada." },
];

const SIGNAL_ICONS = {
  FLOR: Flower2,
  BEIJINHO: Heart,
  OLA: Hand,
};

const PROFILE_THEMES = new Set(["classico", "areia", "noite"]);

function normalizeProfileTheme(value) {
  const theme = String(value || "classico").trim().toLowerCase();
  return PROFILE_THEMES.has(theme) ? theme : "classico";
}

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

function ProfileMoments({ items = [], english }) {
  const [now, setNow] = useState(Date.now);
  const [selectedId, setSelectedId] = useState(null);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const current = items.filter(item => Date.parse(item.expiresAt) > now);
  const selected = current.find(item => item.id === selectedId);
  useEffect(() => {
    if (!selected) return undefined;
    const close = event => { if (event.key === "Escape") setSelectedId(null); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [selected]);
  if (!current.length) return null;
  function remaining(item) {
    const minutes = Math.max(1, Math.ceil((Date.parse(item.expiresAt) - now) / 60000));
    return minutes >= 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${minutes} min`;
  }
  return <section className="nk-profile-moments" aria-label={english ? "Moments" : "Momentos"}>
    <header><h2>{english ? "Moments" : "Momentos"}</h2><span>{english ? "Available for 24 hours" : "Disponíveis durante 24 horas"}</span></header>
    <div className="nk-profile-moments__strip">
      {current.map((item,index) => <button key={item.id} type="button" className="nk-profile-moment" onClick={() => setSelectedId(item.id)} aria-label={english ? `Open moment ${index+1}` : `Abrir momento ${index+1}`}>
        {item.mediaType === "VIDEO" && item.mediaUrl ? <><video src={item.mediaUrl} muted playsInline preload="metadata"/><span className="nk-profile-moment__play"><Play size={20}/></span></> : item.mediaUrl ? <img src={item.mediaUrl} alt="" loading="lazy"/> : <strong>{item.text}</strong>}
        <small>{remaining(item)}</small>
      </button>)}
    </div>
    {selected && <div className="nk-profile-gallery__viewer" onMouseDown={event => {if(event.target === event.currentTarget) setSelectedId(null);}}>
      <section role="dialog" aria-modal="true" aria-label={english ? "Moment" : "Momento"}>
        <button type="button" autoFocus onClick={() => setSelectedId(null)} aria-label={english ? "Close moment" : "Fechar momento"}><X size={21}/></button>
        {selected.mediaType === "VIDEO" && selected.mediaUrl ? <video src={selected.mediaUrl} controls autoPlay playsInline/> : selected.mediaUrl ? <img src={selected.mediaUrl} alt=""/> : <div className="nk-profile-moment__text">{selected.text}</div>}
        {selected.mediaUrl && selected.text && <p className="nk-profile-moment__caption">{selected.text}</p>}
      </section>
    </div>}
  </section>;
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
  onAskChat,
  onToggleInterest,
  onRequireLogin,
  onBack,
}) {
  const [chatError, setChatError] = useState("");
  const [askingChat, setAskingChat] = useState(false);
  async function askChat() {
    setAskingChat(true);
    setChatError("");
    try { await onAskChat(); }
    catch (error) { setChatError(error.message); }
    finally { setAskingChat(false); }
  }
  const english = useInterfaceLanguage() === "EN";
  const [imageFailed, setImageFailed] = useState(false);
  const [photoIndex, setPhotoIndex] = useState(0);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [bioExpanded, setBioExpanded] = useState(false);
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

  const portraits = useMemo(() => [...new Set([
    profile?.foto_url,
    ...(profile?.gallery || []).filter(item => String(item.id).startsWith("registo-") && item.mediaType === "IMAGEM").map(item => item.mediaUrl),
  ].filter(Boolean))], [profile?.foto_url, profile?.gallery]);
  const activePortrait = portraits[photoIndex] || portraits[0];
  const hasImage = Boolean(activePortrait) && !imageFailed;
  const publications = (profile?.gallery || []).filter(item => !String(item.id).startsWith("registo-") && item.mediaUrl && item.mediaUrl !== profile.cover_url);
  function changePhoto(index) {
    setPhotoIndex((index + portraits.length) % portraits.length);
    setImageFailed(false);
  }
  useEffect(() => {
    setPhotoIndex(0); setImageFailed(false); setPhotoOpen(false); setMoreOpen(false); setBioExpanded(false);
    setChatError(""); setSignalData(null); setSignalStatus(""); setSignalError("");
  }, [profile?.id]);
  useEffect(() => {
    if (!photoOpen && !moreOpen) return undefined;
    function key(event) {
      if (event.key === "Escape") { setPhotoOpen(false); setMoreOpen(false); }
      if (photoOpen && portraits.length > 1 && event.key === "ArrowRight") changePhoto(photoIndex + 1);
      if (photoOpen && portraits.length > 1 && event.key === "ArrowLeft") changePhoto(photoIndex - 1);
    }
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [photoOpen, moreOpen, photoIndex, portraits.length]);
  const profileTheme = normalizeProfileTheme(profile?.tema_perfil);
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

    const offer = signalData?.signals?.find(item => item.type === type);
    if (signalData?.quota?.credit_mode && !offer?.available) return;
    if (offer?.cost > 0 && !window.confirm(english ? `Send this signal for ${offer.cost} credits?` : `Enviar ${offer.label} por ${offer.cost} créditos?`)) return;
    setSignalSending(type);
    setSignalError("");
    setSignalStatus("");

    try {
      const result = await sendProfileSignal(profile.id, type, offer?.cost);
      setSignalData({ quota: result.quota, signals: result.signals, identity_blocked: result.identity_blocked });
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
  const bio = (profile.sobre_si || "").trim();
  const bioLong = bio.length > 190 || bio.split(/\r?\n/).filter(Boolean).length > 3;
  const bioLines = bio.split(/\r?\n/).filter(line => line.trim());
  const bioPreview = bioLong && !bioExpanded ? (bioLines.length > 3 ? bioLines.slice(0,3).join("\n") : bio).slice(0,190).trimEnd() : bio;
  const ages = profile.preferencias?.ages;
  const ageRange = Array.isArray(ages) && ages.length === 2 && ages[0] >= 18 && ages[1] >= ages[0];
  const personalPreferences = { ...(profile.preferencias || {}), ages: undefined };
  const hasPersonalPreferences = ["height","smoking","drinking","education","occupation"].some(key => personalPreferences[key]) || personalPreferences.pets?.length > 0;

  return (
    <main className={`nk-profile-detail nk-profile-redesign nk-profile-detail--theme-${profileTheme}`}>
      <div className="nk-shell">
        <button type="button" className="nk-profile-detail__back" onClick={onBack}>
          <ArrowLeft size={18} /> {english ? "Back" : "Voltar"}
        </button>

        {profile.cover_url && (
          <div className="nk-profile-detail__cover" aria-hidden="true">
            <img
              src={profile.cover_url}
              alt=""
              decoding="async"
              onError={(event) => { event.currentTarget.hidden = true; }}
            />
            <div />
          </div>
        )}

        <div className={`nk-profile-detail__layout ${profile.cover_url ? "has-cover" : ""}`}>
          <aside className="nk-profile-portrait">
            <div className="nk-profile-detail__media">
              {hasImage ? <img src={activePortrait} alt={english ? "Profile photograph" : "Fotografia de perfil"} decoding="async" onError={() => setImageFailed(true)} /> :
                <div className="nk-profile-detail__fallback"><UserRound size={64} strokeWidth={1.15}/><span>{english ? "No photo" : "Sem fotografia"}</span></div>}
              <Presence profile={profile} english={english} />
              {hasImage && <button type="button" className="nk-profile-portrait__expand" aria-label={english ? "Enlarge photo" : "Ampliar fotografia"} onClick={() => setPhotoOpen(true)}><Maximize2 size={18}/></button>}
              {portraits.length > 1 && <div className="nk-profile-portrait__controls">
                <button type="button" aria-label={english ? "Previous photo" : "Fotografia anterior"} onClick={() => changePhoto(photoIndex - 1)}><ChevronLeft size={20}/></button>
                <span>{photoIndex + 1} / {portraits.length}</span>
                <button type="button" aria-label={english ? "Next photo" : "Fotografia seguinte"} onClick={() => changePhoto(photoIndex + 1)}><ChevronRight size={20}/></button>
              </div>}
            </div>
            {portraits.length > 1 && <div className="nk-profile-portrait__thumbs">{portraits.map((url, index) => <button type="button" key={url} aria-label={english ? `Photo ${index+1}` : `Fotografia ${index+1}`} aria-pressed={index === photoIndex} onClick={() => changePhoto(index)}><img src={url} alt="" loading="lazy"/></button>)}</div>}
          </aside>

          <section className="nk-profile-detail__content">
            <div className="nk-profile-detail__heading">
              <div className="nk-profile-intro">
                <h1 className="nk-profile-intro__name">
                  <span className="nk-profile-intro__name-text">{profile.nome_publico}</span>
                  {profile.verificado === true && !String(profile.id).startsWith("demo-") && (
                    <span className="nk-profile-intro__verified" title={english ? "Identity verified by NKATA" : "Identidade verificada pelo NKATA"}>
                      <BadgeCheck size={27} strokeWidth={1.8} aria-hidden="true" />
                      <span className="nk-profile-intro__sr-only">{english ? "Identity verified" : "Identidade verificada"}</span>
                    </span>
                  )}
                  {profile.idade ? <span className="nk-profile-intro__age">{profile.idade} {english ? "years old" : "anos"}</span> : null}
                </h1>
                {profile.verificado === true && !String(profile.id).startsWith("demo-") && (
                  <p className="nk-profile-intro__verified-label">{english ? "Identity verified by NKATA" : "Identidade verificada pelo NKATA"}</p>
                )}
                <div className="nk-profile-intro__meta">
                  {profile.cidade && <span><MapPin size={17}/>{profile.cidade}</span>}
                </div>
                {(profile.objetivo_display || ageRange) && (
                  <div className="nk-profile-intro__looking nk-profile-intro__intention">
                    <Heart size={22} strokeWidth={1.7} aria-hidden="true"/>
                    <div>
                      {profile.objetivo_display && <strong>{objectiveLabel(profile.objetivo_display, english)}</strong>}
                      {ageRange && <small>{english ? "Would like to meet someone aged" : "Gostaria de conhecer alguém entre"} {ages[0]}–{ages[1]} {english ? "years old" : "anos"}</small>}
                    </div>
                  </div>
                )}
                <div className="nk-profile-intro__primary">
                  {onAskChat && !String(profile.id).startsWith("demo-") && <button type="button" className="nk-button nk-button--wine" disabled={askingChat} onClick={askChat}><MessageCircle size={18}/> {askingChat ? (english ? "Sending…" : "A enviar…") : (english ? "Request a chat" : "Pedir para conversar")}</button>}
              <button
                type="button"
                className={`nk-button nk-button--quiet ${interestActive ? "is-active" : ""}`}
                aria-pressed={Boolean(interestActive)}
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

                </div>
                {chatError && <p role="alert">{chatError}</p>}
                {interestMessage && <div className={`nk-interest-message ${interestActive ? "is-active" : ""}`} role="status">{interestMessage}</div>}
                <div className="nk-profile-detail__quick-actions">
                  <button type="button" className={`nk-profile-detail__save ${saved ? "is-saved" : ""}`} onClick={() => onToggleSaved?.(profile)} aria-pressed={saved}><Heart size={18} fill={saved ? "currentColor" : "none"}/>{saved ? (english ? "Saved" : "Guardado") : (english ? "Save" : "Guardar")}</button>
                  <div className="nk-profile-more">
                    <button type="button" className="nk-profile-detail__share" aria-expanded={moreOpen} onClick={() => setMoreOpen(value => !value)}><MoreHorizontal size={19}/>{english ? "More" : "Mais"}</button>
                    {moreOpen && <div className="nk-profile-more__menu">
                      <button type="button" onClick={handleShare}><Share2 size={16}/>{shareStatus || (english ? "Share" : "Partilhar")}</button>
                      <button type="button" onClick={() => {setMoreOpen(false);openSafetyAction("report");}}><Flag size={16}/>{english ? "Report" : "Denunciar"}</button>
                      <button type="button" onClick={() => {setMoreOpen(false);openSafetyAction("block");}}><Ban size={16}/>{english ? "Block" : "Bloquear"}</button>
                    </div>}
                  </div>
                </div>
              </div>
            </div>

            {error && <div className="nk-profile-detail__notice">{english ? "Some profile details could not be refreshed." : "Alguns dados deste perfil não foram atualizados."}</div>}
            {safetyStatus && <div className="nk-interest-message is-active" role="status">{safetyStatus}</div>}

            <section className={`nk-profile-signals ${limitReached ? "is-locked" : ""}`}>
              <div className="nk-profile-signals__heading">
                <div>
                  <h2>{english ? "Send a signal" : "Enviar um sinal"}</h2>
                  <p>
                    {authenticated && signalData?.identity_blocked ? (english ? "Verify your identity to send signals." : "Verifique a sua identidade para enviar sinais.") : authenticated && quota
                      ? (quota.credit_mode ? (english ? "Confirm the cost before sending." : "Confirme o custo antes de enviar.") : (english ? `${quota.daily_limit} daily signals on your ${quota.plan_label} plan.` : `${quota.daily_limit} sinais diários no plano ${quota.plan_label}.`))
                      : (english ? "Show interest without starting a conversation." : "Mostre interesse sem iniciar uma conversa.")}
                  </p>
                </div>
                {authenticated && quota && (
                  <strong className="nk-profile-signals__quota">
                    {quota.credit_mode ? `${quota.credit_balance} ${english ? "credits" : "créditos"}` : `${quota.used_today} ${english ? "of" : "de"} ${quota.daily_limit} ${english ? "used" : "no plano"}`}
                    {!quota.credit_mode && quota.recharge_balance > 0 ? ` · +${quota.recharge_balance} ${english ? "top-up" : "recarga"}` : ""}
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
                    || !signalData
                    || signalData?.identity_blocked
                    || sent
                    || limitReached
                    || signal.available === false
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
                                : signalData?.identity_blocked
                                  ? (english ? "Unavailable" : "Indisponível")
                                : quota?.credit_mode
                                  ? (signal.cost ? `${signal.cost} ${english ? (signal.cost === 1 ? "credit" : "credits") : (signal.cost === 1 ? "crédito" : "créditos")}` : (english ? "Included" : "Incluído"))
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
                  {english ? "Sign in to use your plan's signals" : "Entrar para enviar sinais"}
                </button>
              )}

              {signalLoading && authenticated && (
                <small className="nk-profile-signals__loading">{english ? "Checking available signals…" : "A confirmar os sinais disponíveis…"}</small>
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
          </section>
        </div>

        <section className="nk-profile-essentials nk-profile-essentials--wide">
          <h2>{english ? "Get to know me" : "Conheça-me melhor"}</h2>
          <div className="nk-profile-essentials__grid">
            <section className="nk-profile-detail__block nk-profile-essentials__bio">
              <span>{english ? "About me" : "Sobre mim"}</span>
              <p className="nk-profile-intro__bio" id="nk-profile-bio">{bioPreview || (english ? "No introduction yet." : "Ainda sem apresentação.")}{bioLong && !bioExpanded ? "…" : ""}</p>
              {bioLong && <button type="button" className="nk-profile-bio-toggle" aria-expanded={bioExpanded} aria-controls="nk-profile-bio" onClick={() => setBioExpanded(value => !value)}>{bioExpanded ? (english ? "Read less" : "Ver menos") : (english ? "Read more" : "Ler mais")}</button>}
            </section>
            {(profile.o_que_valoriza || profile.o_que_nao_aceita) && <div className="nk-profile-essentials__values">
              {profile.o_que_valoriza && <DetailBlock title={english ? "What I value" : "O que valorizo"}>{profile.o_que_valoriza}</DetailBlock>}
              {profile.o_que_nao_aceita && <DetailBlock title={english ? "What I don’t accept" : "O que não aceito"}>{profile.o_que_nao_aceita}</DetailBlock>}
            </div>}
            {hasPersonalPreferences && <section className="nk-profile-detail__block nk-profile-essentials__facts"><span>{english ? "Lifestyle" : "Estilo de vida"}</span><ProfilePreferences values={personalPreferences} english={english}/></section>}
          </div>
        </section>

        <ProfileMoments key={profile.id} items={profile.moments || []} english={english}/>
        <ProfileGallery items={publications} personName={profile.nome_publico} english={english}/>
        <div className="nk-profile-privacy"><LockKeyhole size={15}/>{english ? "Phone, email and documents are kept private." : "Telefone, email e documentos permanecem privados."}</div>
        {loading && <span className="nk-profile-detail__updating">{english ? "Refreshing profile…" : "A atualizar o perfil…"}</span>}
      </div>

      {photoOpen && hasImage && <div className="nk-profile-gallery__viewer" onMouseDown={event => {if(event.target === event.currentTarget) setPhotoOpen(false);}}>
        <section role="dialog" aria-modal="true" aria-label={english ? "Profile photo" : "Fotografia de perfil"}>
          <button type="button" autoFocus onClick={() => setPhotoOpen(false)} aria-label={english ? "Close photo" : "Fechar fotografia"}><X size={21}/></button>
          <img src={activePortrait} alt={english ? "Profile photograph" : "Fotografia de perfil"}/>
          {portraits.length > 1 && <div className="nk-profile-portrait__controls"><button type="button" onClick={() => changePhoto(photoIndex-1)} aria-label={english ? "Previous photo" : "Fotografia anterior"}><ChevronLeft size={20}/></button><span>{photoIndex+1} / {portraits.length}</span><button type="button" onClick={() => changePhoto(photoIndex+1)} aria-label={english ? "Next photo" : "Fotografia seguinte"}><ChevronRight size={20}/></button></div>}
        </section>
      </div>}

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
