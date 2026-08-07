import { useEffect, useMemo, useRef, useState } from "react";
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
import { createMoment, deleteMoment, fetchMoments } from "../services/momentsApi.js";

function remainingLabel(moment) {
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
      if (event.key === "ArrowRight") setIndex((current) => Math.min(moments.length - 1, current + 1));
      if (event.key === "ArrowLeft") setIndex((current) => Math.max(0, current - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [moments.length, onClose]);

  if (!moment) return null;

  return (
    <div className="nk-moment-viewer" role="dialog" aria-modal="true" aria-label={`Momento de ${moment.profile.nome_publico}`}>
      <div className="nk-moment-viewer__frame">
        <div className="nk-moment-viewer__progress" aria-hidden="true">
          {moments.map((item, itemIndex) => (
            <span key={item.id} className={itemIndex <= index ? "is-active" : ""} />
          ))}
        </div>

        <header className="nk-moment-viewer__header">
          <button type="button" className="nk-moment-viewer__person" onClick={() => onOpenProfile?.(moment.profile)}>
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
    </div>
  );
}

export default function MomentsPage({ onOpenProfile }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [text, setText] = useState("");
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
  const groups = useMemo(() => groupByProfile(moments), [moments]);
  const capabilities = data?.capabilities || null;
  const mediaEnabled = Boolean(capabilities?.media_enabled);

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
    if (publishing || (!text.trim() && !media)) return;

    setPublishing(true);
    setError("");
    setStatus("");
    try {
      const result = await createMoment({ text: text.trim(), visibility, media });
      setData((current) => ({
        ...(current || {}),
        results: [result.moment, ...(current?.results || [])],
        mine: [result.moment, ...(current?.mine || [])],
        capabilities: result.capabilities || current?.capabilities,
      }));
      setText("");
      clearMedia();
      setStatus(result.message || "Momento publicado.");
      window.setTimeout(() => setStatus(""), 3200);
    } catch (requestError) {
      setError(requestError.message || "Não foi possível publicar o Momento.");
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
            <span className="nk-eyebrow nk-eyebrow--dark"><Play size={15} /> Momentos</span>
            <h1>Partilhe um pouco do seu dia.</h1>
            <p>Os Momentos desaparecem automaticamente após 24 horas e nunca ficam públicos na internet.</p>
          </div>
          <span className="nk-moments-page__private"><ShieldCheck size={17} /> Apenas membros NKATA</span>
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

          <textarea
            value={text}
            onChange={(event) => setText(event.target.value.slice(0, 500))}
            placeholder="O que gostaria de partilhar hoje?"
            maxLength={500}
            rows={3}
          />

          {mediaPreview && (
            <div className="nk-moment-composer__preview">
              {media?.type?.startsWith("video/")
                ? <video src={mediaPreview} controls playsInline />
                : <img src={mediaPreview} alt="Pré-visualização" />}
              <button type="button" onClick={clearMedia} aria-label="Remover ficheiro"><X size={17} /></button>
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
                onClick={() => mediaEnabled ? fileRef.current?.click() : setError("Fotografias e vídeos exigem NKATA Essencial ou Premium.")}
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

            <button type="submit" className="nk-button nk-button--wine" disabled={publishing || (!text.trim() && !media)}>
              <Send size={17} /> {publishing ? "A publicar…" : "Publicar"}
            </button>
          </div>
          <small className="nk-moment-composer__counter">{text.length}/500 · desaparece em 24h</small>
        </form>

        {error && <div className="nk-moments-page__message is-error">{error}</div>}
        {status && <div className="nk-moments-page__message is-success">{status}</div>}

        <div className="nk-moments-page__heading">
          <div>
            <h2>Momentos recentes</h2>
            <p>Sem comentários públicos. Veja apenas o que cada pessoa decidiu partilhar.</p>
          </div>
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
                    {group.moments.some((item) => item.media_type === "VIDEO") && <em><Play size={10} fill="currentColor" /></em>}
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
            <h2>Ainda não há Momentos ativos</h2>
            <p>Seja a primeira pessoa a partilhar algo simples do seu dia.</p>
          </div>
        )}
      </section>

      {viewerGroup && (
        <MomentViewer
          moments={viewerGroup.moments}
          initialIndex={0}
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
