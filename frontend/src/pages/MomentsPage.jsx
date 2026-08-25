import { useEffect, useMemo, useRef, useState } from "react";
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
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";
import useInterfaceLanguage from "../hooks/useInterfaceLanguage.js";
import { createMoment, deleteMoment, fetchMoments } from "../services/momentsApi.js";

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

function groupByProfile(moments) {
  const groups = [];
  const map = new Map();

  moments.forEach((moment) => {
    const key = String(moment.profile.id);
    if (!map.has(key)) {
      const group = { profile: moment.profile, moments: [], mine: moment.mine };
      map.set(key, group);
      groups.push(group);
    }
    map.get(key).moments.push(moment);
    if (moment.mine) map.get(key).mine = true;
  });

  groups.sort((a, b) => Number(b.mine) - Number(a.mine));
  return groups;
}

function MomentMedia({ moment }) {
  if (moment.media_type === "IMAGEM" && moment.media_url) {
    return <img className="nk-moment-viewer__media" src={moment.media_url} alt="" />;
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
                ? <img src={moment.profile.foto_url} alt="" />
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
          <img src={moment.media_url} alt={english ? "Content submitted for review" : "Conteúdo enviado para revisão"} />
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

export default function MomentsPage({ onOpenProfile }) {
  const english = useInterfaceLanguage() === "EN";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [caption, setCaption] = useState("SEM_LEGENDA");
  const [media, setMedia] = useState(null);
  const [mediaPreview, setMediaPreview] = useState("");
  const [composerOpen, setComposerOpen] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [status, setStatus] = useState("");
  const [viewerGroup, setViewerGroup] = useState(null);
  const fileRef = useRef(null);

  const load = async ({ signal } = {}) => {
    setLoading(true);
    setError("");
    try {
      const result = await fetchMoments({ signal });
      setData(result);
    } catch (requestError) {
      if (requestError.name !== "AbortError") {
        setError(requestError.message || (english ? "Unable to load Moments." : "Não foi possível carregar os Momentos."));
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    load({ signal: controller.signal });
    return () => controller.abort();
  }, []);

  useEffect(() => () => {
    if (mediaPreview) URL.revokeObjectURL(mediaPreview);
  }, [mediaPreview]);

  const moments = data?.results || [];
  const reviewItems = data?.review_items || [];
  const groups = useMemo(() => groupByProfile(moments), [moments]);
  const capabilities = data?.capabilities || null;
  const mediaEnabled = Boolean(capabilities?.media_enabled);
  const captionOptions = capabilities?.caption_options || FALLBACK_CAPTIONS;
  const canPublish = Boolean(media || caption !== "SEM_LEGENDA");
  const viewerGroupIndex = viewerGroup
    ? groups.findIndex((group) => String(group.profile.id) === String(viewerGroup.profile.id))
    : -1;

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
      setError(english ? "Photos and videos in Moments require NKATA Essential or Premium." : "Fotografias e vídeos nos Momentos exigem NKATA Essencial ou Premium.");
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

    setPublishing(true);
    setError("");
    setStatus("");

    try {
      const result = await createMoment({ caption, visibility: "TODOS", media });
      setData((current) => {
        const base = current || {};
        if (result.pending_review) {
          return {
            ...base,
            review_items: [result.moment, ...(base.review_items || [])],
            capabilities: result.capabilities || base.capabilities,
          };
        }
        return {
          ...base,
          results: [result.moment, ...(base.results || [])],
          mine: [result.moment, ...(base.mine || [])],
          capabilities: result.capabilities || base.capabilities,
        };
      });
      setCaption("SEM_LEGENDA");
      clearMedia();
      setComposerOpen(false);
      setStatus(result.message || (english ? "Moment posted." : "Momento enviado."));
      window.setTimeout(() => setStatus(""), 4200);
    } catch (requestError) {
      setError(requestError.message || (english ? "Unable to post the Moment." : "Não foi possível enviar o Momento."));
    } finally {
      setPublishing(false);
    }
  };

  const handleDelete = async (moment) => {
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
    }
  };

  return (
    <main className="nk-moments-page">
      <CompactPageHeader title={english ? "Moments" : "Momentos"} />

      <section className="nk-shell nk-moments-page__content">
        <form
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
              <label className="nk-moment-composer__caption">
                <span className="sr-only">{english ? "Caption" : "Frase"}</span>
                <select
                  value={caption}
                  onChange={(event) => setCaption(event.target.value)}
                  aria-label={english ? "Moment caption" : "Frase do Momento"}
                >
                  {captionOptions.map((option) => (
                    <option key={option.value} value={option.value}>{english ? (EN_CAPTIONS[option.value] || option.label) : option.label}</option>
                  ))}
                </select>
              </label>

              {mediaPreview && (
                <div className="nk-moment-composer__preview">
                  {media?.type?.startsWith("video/")
                    ? <video src={mediaPreview} controls playsInline />
                    : <img src={mediaPreview} alt={english ? "Preview" : "Pré-visualização"} />}
                  <button type="button" onClick={clearMedia} aria-label={english ? "Remove file" : "Remover ficheiro"}><X size={17} /></button>
                </div>
              )}

              <div className="nk-moment-composer__controls">
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime"
                  onChange={handleFile}
                  hidden
                />
                <button
                  type="button"
                  className="nk-moment-composer__media"
                  onClick={() => mediaEnabled
                    ? fileRef.current?.click()
                    : setError(english ? "Photos and videos require NKATA Essential or Premium." : "Fotografias e vídeos exigem NKATA Essencial ou Premium.")}
                >
                  {mediaEnabled ? <ImagePlus size={18} /> : <LockKeyhole size={17} />}
                  {english ? "Photo or video" : "Foto ou vídeo"}
                </button>

                <button type="submit" className="nk-button nk-button--wine" disabled={publishing || !canPublish}>
                  <Send size={17} /> {publishing ? (english ? "Posting…" : "A publicar…") : (english ? "Post" : "Publicar")}
                </button>
              </div>
            </div>
          )}
        </form>

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

        <div className="nk-moments-page__heading">
          <h2>{english ? "Recent" : "Recentes"}</h2>
          <button type="button" onClick={() => load()} disabled={loading}>
            <RefreshCw size={16} className={loading ? "is-spinning" : ""} /> {english ? "Refresh" : "Atualizar"}
          </button>
        </div>

        {loading && !data ? (
          <div className="nk-moment-rail nk-moment-rail--loading"><span /><span /><span /><span /></div>
        ) : groups.length ? (
          <div className="nk-moment-rail" aria-label={english ? "People with Moments" : "Pessoas com Momentos"}>
            {groups.map((group) => (
              <button type="button" key={group.profile.id} onClick={() => setViewerGroup(group)}>
                <span className="nk-moment-rail__ring">
                  <span>
                    {group.profile.foto_url
                      ? <img src={group.profile.foto_url} alt="" />
                      : <UserRound size={28} />}
                    {group.moments.some((item) => item.media_type === "VIDEO") && (
                      <em><Play size={10} fill="currentColor" /></em>
                    )}
                  </span>
                </span>
                <strong>{group.mine ? (english ? "Yours" : "O seu") : group.profile.nome_publico}</strong>
                <small>{group.moments.length} {english ? (group.moments.length === 1 ? "Moment" : "Moments") : (group.moments.length === 1 ? "Momento" : "Momentos")}</small>
              </button>
            ))}
          </div>
        ) : (
          <div className="nk-moments-page__empty">
            <Clock3 size={27} />
            <h2>{english ? "No active Moments" : "Nenhum Momento ativo"}</h2>
            <p>{english ? "Post the first one." : "Publique o primeiro."}</p>
          </div>
        )}
      </section>

      {viewerGroup && viewerGroupIndex >= 0 && (
        <AutoplayMomentViewer
          groups={groups}
          initialGroupIndex={viewerGroupIndex}
          onClose={() => setViewerGroup(null)}
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
