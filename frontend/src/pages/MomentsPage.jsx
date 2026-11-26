import HeartLoader from "../components/HeartLoader.jsx";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock3,
  ImagePlus,
  LockKeyhole,
  Play,
  Plus,
  RefreshCw,
  Send,
  ShieldCheck,
  Trash2,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import AutoplayMomentViewer from "../components/moments/AutoplayMomentViewer.jsx";
import MomentWindows, { activeMomentGroups } from "../components/moments/MomentWindows.jsx";
import MomentStudio from "../components/moments/MomentStudio.jsx";
import useSeenMoments from "../hooks/useSeenMoments.js";
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";
import useInterfaceLanguage from "../hooks/useInterfaceLanguage.js";
import { createMoment, deleteMoment, fetchMoments, groupMomentsByProfile, MOMENTS_REFRESH_MS } from "../services/momentsApi.js";

const FALLBACK_CAPTIONS = [
  { value: "SEM_LEGENDA", label: "Sem legenda" },
  { value: "DIA_TRANQUILO", label: "Um dia tranquilo por aqui." },
  { value: "BOAS_ENERGIAS", label: "Boas energias para o dia." },
  { value: "APROVEITAR_MOMENTO", label: "A aproveitar um bom momento." },
  { value: "CONHECER_COM_CALMA", label: "Aberto(a) a conhecer alguém com calma." },
  { value: "FIM_DE_DIA", label: "A terminar o dia com tranquilidade." },
];

const EN_CAPTIONS = {
  SEM_LEGENDA: "No caption",
  DIA_TRANQUILO: "A peaceful day.",
  BOAS_ENERGIAS: "Good energy for the day.",
  APROVEITAR_MOMENTO: "Enjoying a good moment.",
  CONHECER_COM_CALMA: "Open to meeting someone at a calm pace.",
  FIM_DE_DIA: "Ending the day peacefully.",
};

function remainingLabel(moment, english) {
  if (moment.moderation_status === "PENDENTE") return english ? "Under review" : "Em análise";
  if (moment.moderation_status === "REJEITADO") return english ? "Not approved" : "Não aprovado";
  if (!moment.expires_at) return "";

  const expires = new Date(moment.expires_at);
  const milliseconds = Math.max(0, expires.getTime() - Date.now());
  const minutes = Math.ceil(milliseconds / 60000);
  if (minutes <= 1) return english ? "Ends in under 1 min" : "Termina em menos de 1 min";
  if (minutes < 60) return english ? `Ends in ${minutes} min` : `Termina em ${minutes} min`;
  const hours = Math.ceil(minutes / 60);
  return english ? `Ends in ${hours} h` : `Termina em ${hours} h`;
}



function MomentMedia({ moment }) {
  if (moment.media_type === "IMAGEM" && moment.media_url) {
    return <img className="nk-moment-viewer__media" src={moment.media_url} alt="" decoding="async" />;
  }
  if (moment.media_type === "VIDEO" && moment.media_url) {
    return (
      <video
        className="nk-moment-viewer__media"
        src={moment.media_url}
        controls
        playsInline
        preload="metadata"
      />
    );
  }
  return <div className="nk-moment-viewer__text-only" aria-hidden="true" />;
}

function MomentViewer({ moments, initialIndex, onClose, onDelete, onOpenProfile, english }) {
  const [index, setIndex] = useState(initialIndex);
  const moment = moments[index] || moments[0];

  useEffect(() => {
    setIndex(initialIndex);
  }, [initialIndex, moments]);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKey = (event) => {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowRight") {
        setIndex((current) => Math.min(moments.length - 1, current + 1));
      }
      if (event.key === "ArrowLeft") {
        setIndex((current) => Math.max(0, current - 1));
      }
    };

    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [moments.length, onClose]);

  if (!moment) return null;

  return createPortal(
    <div className="nk-moment-viewer" role="dialog" aria-modal="true" aria-label={`${english ? "Moment by" : "Momento de"} ${moment.profile.nome_publico}`}>
      <div className="nk-moment-viewer__frame">
        <div className="nk-moment-viewer__progress" aria-hidden="true">
          {moments.map((item, itemIndex) => (
            <span key={item.id} className={itemIndex <= index ? "is-active" : ""} />
          ))}
        </div>

        <header className="nk-moment-viewer__header">
          <button
            type="button"
            className="nk-moment-viewer__person"
            onClick={() => !moment.mine && onOpenProfile?.(moment.profile)}
            disabled={moment.mine}
            title={moment.mine ? (english ? "Manage your profile in Account" : "O seu perfil é gerido em Minha conta") : (english ? "Open profile" : "Abrir perfil")}
          >
            <span>
              {moment.profile.foto_url
                ? <img src={moment.profile.foto_url} alt="" loading="lazy" decoding="async" />
                : <UserRound size={22} />}
            </span>
            <div>
              <strong>{moment.mine ? (english ? "Your Moment" : "O seu Momento") : moment.profile.nome_publico}</strong>
              <small><Clock3 size={12} /> {remainingLabel(moment, english)}</small>
            </div>
          </button>

          <div className="nk-moment-viewer__header-actions">
            {moment.mine && (
              <button type="button" onClick={() => onDelete(moment)} aria-label={english ? "Delete Moment" : "Remover Momento"}>
                <Trash2 size={18} />
              </button>
            )}
            <button type="button" onClick={onClose} aria-label={english ? "Close Moment" : "Fechar Momento"}>
              <X size={20} />
            </button>
          </div>
        </header>

        <div className={`nk-moment-viewer__content is-${moment.media_type.toLowerCase()}`}>
          <MomentMedia moment={moment} />
          <div className="nk-moment-viewer__shade" />
          {moment.text && <p>{moment.text}</p>}
          <span className="nk-moment-viewer__privacy">
            {moment.visibility === "MATCHES" ? <LockKeyhole size={14} /> : <UsersRound size={14} />}
            {english ? (moment.visibility === "MATCHES" ? "Matches only" : "All members") : moment.visibility_label}
          </span>
        </div>

        {index > 0 && (
          <button
            type="button"
            className="nk-moment-viewer__nav is-prev"
            onClick={() => setIndex((current) => current - 1)}
            aria-label={english ? "Previous Moment" : "Momento anterior"}
          >
            <ChevronLeft size={24} />
          </button>
        )}
        {index < moments.length - 1 && (
          <button
            type="button"
            className="nk-moment-viewer__nav is-next"
            onClick={() => setIndex((current) => current + 1)}
            aria-label={english ? "Next Moment" : "Próximo Momento"}
          >
            <ChevronRight size={24} />
          </button>
        )}
      </div>
    </div>,
    document.body,
  );
}

function ReviewItem({ moment, onDelete, english }) {
  const pending = moment.moderation_status === "PENDENTE";
  return (
    <article className={`nk-moment-review-item ${pending ? "is-pending" : "is-rejected"}`}>
      <div className="nk-moment-review-item__media">
        {moment.media_type === "IMAGEM" && moment.media_url ? (
          <img src={moment.media_url} alt={english ? "Content submitted for review" : "Conteúdo enviado para revisão"} loading="lazy" decoding="async" />
        ) : moment.media_type === "VIDEO" && moment.media_url ? (
          <video src={moment.media_url} muted playsInline preload="metadata" />
        ) : (
          <ShieldCheck size={25} />
        )}
      </div>
      <div>
        <strong>{pending ? (english ? "Under review" : "Em análise") : (english ? "Not approved" : "Não aprovado")}</strong>
        <p>
          {pending
            ? (english ? "Visible only to you. The 24 hours begin after approval." : "Visível apenas para si. As 24 horas começam após aprovação.")
            : (moment.moderation_note || (english ? "This content was not approved." : "Este conteúdo não foi aprovado para publicação."))}
        </p>
      </div>
      <button type="button" onClick={() => onDelete(moment)} aria-label={english ? "Delete submission" : "Remover envio"}>
        <Trash2 size={17} />
      </button>
    </article>
  );
}

export default function MomentsPage({ onOpenProfile, userId }) {
  const english = useInterfaceLanguage() === "EN";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [caption, setCaption] = useState("DIA_TRANQUILO");
  const [theme, setTheme] = useState("wine");
  const [font, setFont] = useState("serif");
  const [visibility, setVisibility] = useState("TODOS");
  const composerRef = useRef(null);
  const [media, setMedia] = useState(null);
  const [mediaPreview, setMediaPreview] = useState("");
  const [composerOpen, setComposerOpen] = useState(false);
  useEffect(() => {
    if (composerOpen) composerRef.current?.scrollIntoView({block:"start",behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth"});
  }, [composerOpen]);
  const [publishing, setPublishing] = useState(false);
  const [status, setStatus] = useState("");
  const [viewerGroup, setViewerGroup] = useState(null);
  const {seen:seenMoments,markSeen}=useSeenMoments(userId);
  const closeViewer = useCallback(() => setViewerGroup(null), []);
  const fileRef = useRef(null);
  const activeRequest = useRef(null);
  const changingMoment = useRef(false);

  const load = useCallback(async ({ silent = false } = {}) => {
    if (changingMoment.current || (silent && activeRequest.current)) return;
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    if (!silent) {
      setLoading(true);
      setError("");
    }
    try {
      const result = await fetchMoments({ signal: controller.signal });
      if (!controller.signal.aborted) setData(result);
    } catch (requestError) {
      if (!silent && !controller.signal.aborted) {
        setError(requestError.message || (english ? "Unable to load Moments." : "Não foi possível carregar os Momentos."));
      }
    } finally {
      if (activeRequest.current === controller) {
        activeRequest.current = null;
        setLoading(false);
      }
    }
  }, [english]);

  useEffect(() => {
    load();
    const refresh = () => {
      if (!document.hidden) load({ silent: true });
    };
    const timer = window.setInterval(refresh, MOMENTS_REFRESH_MS);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refresh);
      activeRequest.current?.abort();
      activeRequest.current = null;
    };
  }, [load]);

  useEffect(() => () => {
    if (mediaPreview) URL.revokeObjectURL(mediaPreview);
  }, [mediaPreview]);

  const moments = data?.results || [];
  const reviewItems = data?.review_items || [];
  const groups = useMemo(() => groupMomentsByProfile(moments), [moments]);
  const capabilities = data?.capabilities || null;
  const mediaEnabled = Boolean(capabilities?.media_enabled);
  const captionOptions = capabilities?.caption_options || FALLBACK_CAPTIONS;
  const visibilityOptions = (capabilities?.visibility_options || [{value:"TODOS",label:"Todos os membros"},{value:"MATCHES",label:"Apenas matches"}]).filter(option => ["TODOS","MATCHES"].includes(option.value));
  const captionLabel = option => option ? (english ? EN_CAPTIONS[option.value] || option.label : option.label) : "";
  const canPublish = Boolean(media || caption !== "SEM_LEGENDA");
  const clearMedia = () => {
    if (mediaPreview) URL.revokeObjectURL(mediaPreview);
    setMedia(null);
    setMediaPreview("");
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleFile = (event) => {
    const file = event.target.files?.[0] || null;
    setError("");
    if (!file) return;

    if (!mediaEnabled) {
      setError(english ? "Photos and videos in Moments require NKATA Fortnightly, Essential or Premium." : "Fotografias e vídeos nos Momentos exigem NKATA Quinzenal, Essencial ou Premium.");
      event.target.value = "";
      return;
    }

    if (mediaPreview) URL.revokeObjectURL(mediaPreview);
    setMedia(file);
    setMediaPreview(URL.createObjectURL(file));
  };

  const handlePublish = async (event) => {
    event.preventDefault();
    if (publishing || !canPublish) return;

    changingMoment.current = true;
    activeRequest.current?.abort();
    setPublishing(true);
    setError("");
    setStatus("");

    try {
      const result = await createMoment({ caption, visibility, media, theme, font });
      const publishedMoment = result.moment || result;
      setData((current) => {
        const base = current || {};
        if (publishedMoment.moderation_status === "PENDENTE") {
          return {
            ...base,
            review_items: [publishedMoment, ...(base.review_items || [])],
            capabilities: result.capabilities || base.capabilities,
          };
        }
        return {
          ...base,
          results: [publishedMoment, ...(base.results || [])],
          mine: [publishedMoment, ...(base.mine || [])],
          capabilities: result.capabilities || base.capabilities,
        };
      });
      setCaption("DIA_TRANQUILO");
      clearMedia();
      setComposerOpen(false);
      setStatus(result.message || (english ? "Moment posted." : "Momento enviado."));
      window.setTimeout(() => setStatus(""), 4200);
    } catch (requestError) {
      setError(requestError.message || (english ? "Unable to post the Moment." : "Não foi possível enviar o Momento."));
    } finally {
      changingMoment.current = false;
      setPublishing(false);
    }
  };

  const handleDelete = async (moment) => {
    if (changingMoment.current) return;
    changingMoment.current = true;
    activeRequest.current?.abort();
    try {
      await deleteMoment(moment.id);
      setData((current) => ({
        ...(current || {}),
        results: (current?.results || []).filter((item) => item.id !== moment.id),
        mine: (current?.mine || []).filter((item) => item.id !== moment.id),
        review_items: (current?.review_items || []).filter((item) => item.id !== moment.id),
      }));
      setViewerGroup(null);
      setStatus(english ? "Moment deleted." : "Momento removido.");
      window.setTimeout(() => setStatus(""), 2400);
    } catch (requestError) {
      setError(requestError.message || (english ? "Unable to delete the Moment." : "Não foi possível remover o Momento."));
    } finally {
      changingMoment.current = false;
    }
  };

  return (
    <main className="nk-moments-page">
      <CompactPageHeader title={english ? "Moments" : "Momentos"}>
        <button type="button" onClick={() => load()} disabled={loading} aria-label={english ? "Refresh Moments" : "Atualizar Momentos"}>
          <RefreshCw size={17} className={loading ? "is-spinning" : ""} />
          {english ? "Refresh" : "Atualizar"}
        </button>
      </CompactPageHeader>

      <section className="nk-shell nk-moments-page__content">
        {loading && !data ? <HeartLoader page="moments"/> : <MomentWindows
          groups={groups}
          english={english}
          seen={seenMoments}
          composerOpen={composerOpen}
          onCreate={() => setComposerOpen((value) => !value)}
          onOpen={(group, momentId) => {
            const active = activeMomentGroups(groups);
            const index = active.findIndex(item => item.profile.id === group.profile.id);
            if (index >= 0) setViewerGroup({ groups: active, index, momentIndex: Math.max(0, active[index].moments.findIndex(item => item.id === momentId)) });
          }}
        />}
        {composerOpen && <form id="nk-moment-composer" ref={composerRef}
          className={`nk-moment-composer ${composerOpen ? "is-open" : "is-collapsed"}`}
          onSubmit={handlePublish}
        >
          <button
            type="button"
            className="nk-moment-composer__heading"
            onClick={() => setComposerOpen((current) => !current)}
            aria-expanded={composerOpen}
          >
            <span className="nk-moment-composer__plus"><Plus size={20} /></span>
            <span className="nk-moment-composer__label">{english ? "New Moment" : "Novo Momento"}</span>
            <span className="nk-moment-composer__expand">
              <ChevronDown size={18} />
            </span>
          </button>

          {composerOpen && (
            <div className="nk-moment-composer__body">
              <p className="nk-janelas-composer-intro"><Clock3 size={17}/>{english ? "Your Moment lasts 24 hours after approval." : "O teu momento vive 24 horas após aprovação."}</p>
              <MomentStudio english={english} captionOptions={captionOptions} captionLabel={captionLabel} caption={caption} theme={theme} font={font}
                visibility={visibility} visibilityOptions={visibilityOptions} mediaEnabled={mediaEnabled} mediaPreview={mediaPreview}
                isVideo={Boolean(media?.type?.startsWith("video/") || /\.(mp4|webm|mov)$/i.test(media?.name || ""))}
                publishing={publishing} onCaption={setCaption} onTheme={setTheme} onFont={setFont} onVisibility={setVisibility}
                onPreset={preset=>{setTheme(preset.theme);setFont(preset.font);setCaption(preset.caption);}}
                onPickMedia={()=>fileRef.current?.click()} onRemoveMedia={clearMedia}/>
              <div className="nk-moment-composer__controls nk-janelas-studio__submit">
                <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime" onChange={handleFile} hidden disabled={publishing || !mediaEnabled}/>
                <button type="submit" className="nk-button nk-button--wine" disabled={publishing || !canPublish}>
                  <Send size={17} /> {publishing ? (english ? "Posting…" : "A publicar…") : (english ? "Post" : "Publicar")}
                </button>
              </div>
            </div>
          )}
        </form>}

        {error && <div className="nk-moments-page__message is-error">{error}</div>}
        {status && <div className="nk-moments-page__message is-success">{status}</div>}

        {reviewItems.length > 0 && (
          <section className="nk-moment-review">
            <div className="nk-moment-review__heading">
              <h2>{english ? "Under review" : "Em análise"}</h2>
              <span>{reviewItems.length}</span>
            </div>
            <div className="nk-moment-review__list">
              {reviewItems.map((moment) => (
                <ReviewItem key={moment.id} moment={moment} onDelete={handleDelete} english={english} />
              ))}
            </div>
          </section>
        )}

      </section>

      {viewerGroup && (
        <AutoplayMomentViewer
          groups={viewerGroup.groups}
          initialGroupIndex={viewerGroup.index}
          initialMomentIndex={viewerGroup.momentIndex}
          windowsMode
          onViewed={markSeen}
          onClose={closeViewer}
          onDelete={handleDelete}
          onOpenProfile={(profile) => {
            setViewerGroup(null);
            onOpenProfile?.(profile);
          }}
        />
      )}
    </main>
  );
}
