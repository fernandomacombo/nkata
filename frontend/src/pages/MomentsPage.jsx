import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
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
import { createMoment, deleteMoment, fetchMoments } from "../services/momentsApi.js";

const FALLBACK_CAPTIONS = [
  { value: "SEM_LEGENDA", label: "Sem legenda" },
  { value: "DIA_TRANQUILO", label: "Um dia tranquilo por aqui." },
  { value: "BOAS_ENERGIAS", label: "Boas energias para o dia." },
  { value: "APROVEITAR_MOMENTO", label: "A aproveitar um bom momento." },
  { value: "CONHECER_COM_CALMA", label: "Aberto(a) a conhecer alguém com calma." },
  { value: "FIM_DE_DIA", label: "A terminar o dia com tranquilidade." },
];

function remainingLabel(moment) {
  if (moment.moderation_status === "PENDENTE") return "Em análise";
  if (moment.moderation_status === "REJEITADO") return "Não aprovado";
  if (!moment.expires_at) return "";

  const expires = new Date(moment.expires_at);
  const milliseconds = Math.max(0, expires.getTime() - Date.now());
  const minutes = Math.ceil(milliseconds / 60000);
  if (minutes <= 1) return "Termina em menos de 1 min";
  if (minutes < 60) return `Termina em ${minutes} min`;
  const hours = Math.ceil(minutes / 60);
  return `Termina em ${hours} h`;
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

function MomentViewer({ moments, initialIndex, onClose, onDelete, onOpenProfile }) {
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
    <div className="nk-moment-viewer" role="dialog" aria-modal="true" aria-label={`Momento de ${moment.profile.nome_publico}`}>
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
            title={moment.mine ? "O seu perfil é gerido em Minha conta" : "Abrir perfil"}
          >
            <span>
              {moment.profile.foto_url
                ? <img src={moment.profile.foto_url} alt="" />
                : <UserRound size={22} />}
            </span>
            <div>
              <strong>{moment.mine ? "O seu Momento" : moment.profile.nome_publico}</strong>
              <small><Clock3 size={12} /> {remainingLabel(moment)}</small>
            </div>
          </button>

          <div className="nk-moment-viewer__header-actions">
            {moment.mine && (
              <button type="button" onClick={() => onDelete(moment)} aria-label="Remover Momento">
                <Trash2 size={18} />
              </button>
            )}
            <button type="button" onClick={onClose} aria-label="Fechar Momento">
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
            {moment.visibility_label}
          </span>
        </div>

        {index > 0 && (
          <button
            type="button"
            className="nk-moment-viewer__nav is-prev"
            onClick={() => setIndex((current) => current - 1)}
            aria-label="Momento anterior"
          >
            <ChevronLeft size={24} />
          </button>
        )}
        {index < moments.length - 1 && (
          <button
            type="button"
            className="nk-moment-viewer__nav is-next"
            onClick={() => setIndex((current) => current + 1)}
            aria-label="Próximo Momento"
          >
            <ChevronRight size={24} />
          </button>
        )}
      </div>
    </div>,
    document.body,
  );
}

function ReviewItem({ moment, onDelete }) {
  const pending = moment.moderation_status === "PENDENTE";
  return (
    <article className={`nk-moment-review-item ${pending ? "is-pending" : "is-rejected"}`}>
      <div className="nk-moment-review-item__media">
        {moment.media_type === "IMAGEM" && moment.media_url ? (
          <img src={moment.media_url} alt="Conteúdo enviado para revisão" />
        ) : moment.media_type === "VIDEO" && moment.media_url ? (
          <video src={moment.media_url} muted playsInline preload="metadata" />
        ) : (
          <ShieldCheck size={25} />
        )}
      </div>
      <div>
        <strong>{pending ? "Em análise" : "Não aprovado"}</strong>
        <p>
          {pending
            ? "Visível apenas para si. As 24 horas começam após aprovação."
            : (moment.moderation_note || "Este conteúdo não foi aprovado para publicação.")}
        </p>
      </div>
      <button type="button" onClick={() => onDelete(moment)} aria-label="Remover envio">
        <Trash2 size={17} />
      </button>
    </article>
  );
}

export default function MomentsPage({ onOpenProfile }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [caption, setCaption] = useState("SEM_LEGENDA");
  const [visibility, setVisibility] = useState("TODOS");
  const [media, setMedia] = useState(null);
  const [mediaPreview, setMediaPreview] = useState("");
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
        setError(requestError.message || "Não foi possível carregar os Momentos.");
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
      setError("Fotografias e vídeos nos Momentos exigem NKATA Essencial ou Premium.");
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
      const result = await createMoment({ caption, visibility, media });
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
      setStatus(result.message || "Momento enviado.");
      window.setTimeout(() => setStatus(""), 4200);
    } catch (requestError) {
      setError(requestError.message || "Não foi possível enviar o Momento.");
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
      setStatus("Momento removido.");
      window.setTimeout(() => setStatus(""), 2400);
    } catch (requestError) {
      setError(requestError.message || "Não foi possível remover o Momento.");
    }
  };

  return (
    <main className="nk-moments-page">
      <section className="nk-moments-page__intro">
        <div className="nk-shell nk-moments-page__intro-inner">
          <div>
            <h1>Momentos</h1>
            <p>Partilhe fotos, vídeos ou frases por 24 horas.</p>
          </div>
        </div>
      </section>

      <section className="nk-shell nk-moments-page__content">
        <form className="nk-moment-composer" onSubmit={handlePublish}>
          <div className="nk-moment-composer__heading">
            <span className="nk-moment-composer__plus"><Plus size={20} /></span>
            <div>
              <strong>Novo Momento</strong>
              <small>{capabilities?.plan_label || "A confirmar o seu plano…"}</small>
            </div>
          </div>

          <div className="nk-moment-composer__safety-note">
            <ShieldCheck size={18} />
            <div>
              <strong>Use uma frase NKATA</strong>
              <span>Sem contactos, links ou anúncios.</span>
            </div>
          </div>

          <label className="nk-moment-composer__caption">
            <span>Frase</span>
            <select value={caption} onChange={(event) => setCaption(event.target.value)}>
              {captionOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>

          {mediaPreview && (
            <div className="nk-moment-composer__preview">
              {media?.type?.startsWith("video/")
                ? <video src={mediaPreview} controls playsInline />
                : <img src={mediaPreview} alt="Pré-visualização" />}
              <button type="button" onClick={clearMedia} aria-label="Remover ficheiro"><X size={17} /></button>
              <span><ShieldCheck size={14} /> Em análise antes de publicar</span>
            </div>
          )}

          <div className="nk-moment-composer__controls">
            <div>
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
                  : setError("Fotografias e vídeos exigem NKATA Essencial ou Premium.")}
              >
                {mediaEnabled ? <ImagePlus size={18} /> : <LockKeyhole size={17} />}
                {mediaEnabled ? "Foto ou vídeo" : "Media no plano pago"}
              </button>

              <label className="nk-moment-composer__visibility">
                <span className="sr-only">Quem pode ver</span>
                <select value={visibility} onChange={(event) => setVisibility(event.target.value)}>
                  {(capabilities?.visibility_options || [
                    { value: "TODOS", label: "Todos os membros" },
                    { value: "MATCHES", label: "Apenas matches" },
                  ]).map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
            </div>

            <button type="submit" className="nk-button nk-button--wine" disabled={publishing || !canPublish}>
              <Send size={17} /> {publishing ? "A enviar…" : media ? "Enviar para análise" : "Publicar"}
            </button>
          </div>

          <small className="nk-moment-composer__counter">
            {media
              ? "Disponível por 24 horas após aprovação."
              : "Disponível por 24 horas."}
          </small>
        </form>

        {error && <div className="nk-moments-page__message is-error">{error}</div>}
        {status && <div className="nk-moments-page__message is-success">{status}</div>}

        {reviewItems.length > 0 && (
          <section className="nk-moment-review">
            <div className="nk-moment-review__heading">
              <h2>Em análise</h2>
              <span>{reviewItems.length}</span>
            </div>
            <div className="nk-moment-review__list">
              {reviewItems.map((moment) => (
                <ReviewItem key={moment.id} moment={moment} onDelete={handleDelete} />
              ))}
            </div>
          </section>
        )}

        <div className="nk-moments-page__heading">
          <h2>Recentes</h2>
          <button type="button" onClick={() => load()} disabled={loading}>
            <RefreshCw size={16} className={loading ? "is-spinning" : ""} /> Atualizar
          </button>
        </div>

        {loading && !data ? (
          <div className="nk-moment-rail nk-moment-rail--loading"><span /><span /><span /><span /></div>
        ) : groups.length ? (
          <div className="nk-moment-rail" aria-label="Pessoas com Momentos">
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
                <strong>{group.mine ? "O seu" : group.profile.nome_publico}</strong>
                <small>{group.moments.length} {group.moments.length === 1 ? "Momento" : "Momentos"}</small>
              </button>
            ))}
          </div>
        ) : (
          <div className="nk-moments-page__empty">
            <Clock3 size={27} />
            <h2>Nenhum Momento ativo</h2>
            <p>Publique o primeiro.</p>
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
