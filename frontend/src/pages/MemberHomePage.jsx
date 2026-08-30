import { useEffect, useRef, useState } from "react";
import {
  BadgeCheck,
  ChevronDown,
  Flower2,
  Heart,
  HeartHandshake,
  ImagePlus,
  LoaderCircle,
  LockKeyhole,
  MapPin,
  RefreshCw,
  Send,
  Sparkles,
  Trash2,
  UserCheck,
  UserPlus,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";
import useInterfaceLanguage from "../hooks/useInterfaceLanguage.js";
import {
  createPublication,
  deletePublication,
  fetchPublications,
  togglePublicationReaction,
} from "../services/feedApi.js";
import { toggleProfileInterest } from "../services/api.js";
import { toggleFollowProfile } from "../services/followApi.js";

const FALLBACK_CAPTIONS = [
  { value: "SEM_LEGENDA", label: "Sem legenda" },
  { value: "UM_POUCO_DE_MIM", label: "Um pouco de mim." },
  { value: "BOM_MOMENTO", label: "Um bom momento para guardar." },
  { value: "DIA_ESPECIAL", label: "Um dia especial por aqui." },
  { value: "VIDA_COM_CALMA", label: "A viver com calma e intenção." },
  { value: "CONHECER_COM_RESPEITO", label: "Aberto(a) a conhecer alguém com respeito." },
];

const REACTION_ICONS = {
  GOSTEI: Heart,
  FLOR: Flower2,
  APRECIAR: Sparkles,
};

const EN_CAPTIONS = {
  SEM_LEGENDA: "No caption",
  UM_POUCO_DE_MIM: "A little about me.",
  BOM_MOMENTO: "A good moment to remember.",
  DIA_ESPECIAL: "A special day.",
  VIDA_COM_CALMA: "Living with calm and intention.",
  CONHECER_COM_RESPEITO: "Open to meeting someone with respect.",
};

const visibilityLabel = (publication, english) => english
  ? (publication.visibility === "MATCHES" ? "Matches only" : "All members")
  : publication.visibility_label;

function formatDate(value, english) {
  if (!value) return "";
  const date = new Date(value);
  const now = new Date();
  const minutes = Math.max(0, Math.floor((now - date) / 60000));
  if (minutes < 1) return english ? "Now" : "Agora";
  if (minutes < 60) return english ? `${minutes} min ago` : `Há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return english ? `${hours} h ago` : `Há ${hours} h`;
  return new Intl.DateTimeFormat(english ? "en-GB" : "pt-MZ", { day: "2-digit", month: "short" }).format(date);
}

function PublicationMedia({ publication, english }) {
  if (publication.media_type === "VIDEO") {
    return (
      <video
        className="nk-feed-card__media"
        src={publication.media_url}
        controls
        playsInline
        preload="metadata"
      />
    );
  }
  return (
    <img
      className="nk-feed-card__media"
      src={publication.media_url}
      alt={`${english ? "Post by" : "Publicação de"} ${publication.profile.nome_publico}`}
      loading="lazy"
      decoding="async"
    />
  );
}

function PublicationCard({ publication, onOpenProfile, onChanged, onDeleted, english }) {
  const [following, setFollowing] = useState(Boolean(publication.following));
  const [followBusy, setFollowBusy] = useState(false);
  const [interestActive, setInterestActive] = useState(Boolean(publication.interest_active));
  const [interestBusy, setInterestBusy] = useState(false);
  const [interestMessage, setInterestMessage] = useState("");
  const [reactions, setReactions] = useState(publication.reactions || null);
  const [reactionBusy, setReactionBusy] = useState("");
  const [deleting, setDeleting] = useState(false);

  const toggleFollow = async () => {
    if (publication.mine || followBusy) return;
    setFollowBusy(true);
    try {
      const result = await toggleFollowProfile(publication.profile.id);
      setFollowing(Boolean(result.active));
      onChanged?.();
    } finally {
      setFollowBusy(false);
    }
  };

  const toggleInterest = async () => {
    if (publication.mine || interestBusy) return;
    setInterestBusy(true);
    setInterestMessage("");
    try {
      const result = await toggleProfileInterest(publication.profile.id);
      setInterestActive(Boolean(result.active));
      setInterestMessage(result.message || "");
      window.setTimeout(() => setInterestMessage(""), 3200);
    } catch (error) {
      setInterestMessage(error.message || (english ? "Unable to update your interest." : "Não foi possível atualizar o interesse."));
    } finally {
      setInterestBusy(false);
    }
  };

  const react = async (type) => {
    if (publication.mine || reactionBusy) return;
    setReactionBusy(type);
    try {
      const result = await togglePublicationReaction(publication.id, type);
      setReactions(result);
    } finally {
      setReactionBusy("");
    }
  };

  const remove = async () => {
    if (!publication.mine || deleting) return;
    setDeleting(true);
    try {
      await deletePublication(publication.id);
      onDeleted?.(publication.id);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <article className="nk-feed-card">
      <header className="nk-feed-card__header">
        <button
          type="button"
          className="nk-feed-card__person"
          disabled={publication.mine}
          onClick={() => !publication.mine && onOpenProfile?.(publication.profile)}
        >
          <span className="nk-feed-card__avatar">
            {publication.profile.foto_url ? (
              <img src={publication.profile.foto_url} alt="" loading="lazy" decoding="async" />
            ) : (
              <UserRound size={24} />
            )}
          </span>
          <span>
            <strong>
              {publication.mine ? (english ? "Your post" : "A sua publicação") : publication.profile.nome_publico}
              {publication.profile.verificado && <BadgeCheck size={15} />}
            </strong>
            <small>
              <MapPin size={12} /> {publication.profile.cidade}
              <span>·</span>
              {formatDate(publication.created_at, english)}
            </small>
          </span>
        </button>

        {!publication.mine ? (
          <button
            type="button"
            className={`nk-feed-card__follow ${following ? "is-active" : ""}`}
            onClick={toggleFollow}
            disabled={followBusy}
          >
            {followBusy ? (
              <LoaderCircle size={16} className="is-spinning" />
            ) : following ? (
              <UserCheck size={16} />
            ) : (
              <UserPlus size={16} />
            )}
            {following ? (english ? "Following" : "A seguir") : (english ? "Follow" : "Seguir")}
          </button>
        ) : (
          <button
            type="button"
            className="nk-feed-card__delete"
            onClick={remove}
            disabled={deleting}
            aria-label={english ? "Delete post" : "Remover publicação"}
          >
            {deleting ? <LoaderCircle size={17} className="is-spinning" /> : <Trash2 size={17} />}
          </button>
        )}
      </header>

      <div className="nk-feed-card__media-wrap">
        <PublicationMedia publication={publication} english={english} />
        <span className="nk-feed-card__privacy">
          {publication.visibility === "MATCHES" ? <LockKeyhole size={13} /> : <UsersRound size={13} />}
          {visibilityLabel(publication, english)}
        </span>
      </div>

      <div className="nk-feed-card__body">
        {publication.caption && <p className="nk-feed-card__caption">{publication.caption}</p>}

        <div className="nk-feed-card__reactions" aria-label={english ? "Post reactions" : "Reações à publicação"}>
          {(reactions?.options || []).map((option) => {
            const Icon = REACTION_ICONS[option.value] || Sparkles;
            const active = reactions?.mine === option.value;
            const count = Number(reactions?.counts?.[option.value] || 0);
            return (
              <button
                key={option.value}
                type="button"
                className={active ? "is-active" : ""}
                onClick={() => react(option.value)}
                disabled={publication.mine || Boolean(reactionBusy)}
                aria-pressed={active}
                title={option.label}
              >
                {reactionBusy === option.value
                  ? <LoaderCircle size={19} className="is-spinning" />
                  : <Icon size={19} />}
                {count > 0 && <span>{count}</span>}
              </button>
            );
          })}
        </div>

        {!publication.mine && (
          <div className="nk-feed-card__relationship">
            <button
              type="button"
              className={interestActive ? "is-active" : ""}
              onClick={toggleInterest}
              disabled={interestBusy}
            >
              {interestBusy ? (
                <LoaderCircle size={17} className="is-spinning" />
              ) : (
                <HeartHandshake size={17} />
              )}
              {interestActive ? (english ? "Interest sent" : "Interesse enviado") : (english ? "I'm interested" : "Tenho interesse")}
            </button>
            <button type="button" onClick={() => onOpenProfile?.(publication.profile)}>
              <UserRound size={17} /> {english ? "View profile" : "Ver perfil"}
            </button>
          </div>
        )}

        {interestMessage && (
          <small className="nk-feed-card__message" role="status">{interestMessage}</small>
        )}
      </div>
    </article>
  );
}

function ReviewPublication({ publication, onDeleted, english }) {
  const [deleting, setDeleting] = useState(false);
  const pending = publication.moderation_status === "PENDENTE";

  const remove = async () => {
    if (deleting) return;
    setDeleting(true);
    try {
      await deletePublication(publication.id);
      onDeleted?.(publication.id);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <article className={`nk-feed-review ${pending ? "is-pending" : "is-rejected"}`}>
      <span className="nk-feed-review__media">
        {publication.media_type === "VIDEO" ? (
          <video src={publication.media_url} muted playsInline preload="metadata" />
        ) : (
          <img src={publication.media_url} alt="" loading="lazy" decoding="async" />
        )}
      </span>
      <span>
        <strong>{pending ? (english ? "Under review" : "Em análise") : (english ? "Not approved" : "Não aprovada")}</strong>
        <small>
          {pending
            ? (english ? "Only you and the NKATA team can see this content." : "Só você e a equipa NKATA conseguem ver este conteúdo.")
            : (publication.moderation_note || (english ? "This post was not approved." : "Esta publicação não foi aprovada."))}
        </small>
      </span>
      <button type="button" onClick={remove} disabled={deleting} aria-label={english ? "Delete submission" : "Remover envio"}>
        {deleting ? <LoaderCircle size={16} className="is-spinning" /> : <X size={17} />}
      </button>
    </article>
  );
}

export default function MemberHomePage({ onNavigate, onOpenProfile }) {
  const english = useInterfaceLanguage() === "EN";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [media, setMedia] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [caption, setCaption] = useState("SEM_LEGENDA");
  const [publishing, setPublishing] = useState(false);
  const [composerOpen, setComposerOpen] = useState(false);
  const fileRef = useRef(null);

  const capabilities = data?.capabilities || null;
  const publications = data?.results || [];
  const reviewItems = data?.review_items || [];
  const captionOptions = capabilities?.caption_options || FALLBACK_CAPTIONS;
  const canPublish = Boolean(capabilities?.publish_media_enabled);

  const load = async ({ signal, silent = false } = {}) => {
    if (!silent) setLoading(true);
    setError("");
    try {
      const result = await fetchPublications({ signal });
      setData(result);
    } catch (requestError) {
      if (requestError.name !== "AbortError") {
        setError(requestError.message || (english ? "Unable to load the feed." : "Não foi possível carregar o feed."));
      }
    } finally {
      if (!signal?.aborted && !silent) setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    load({ signal: controller.signal });
    return () => controller.abort();
  }, []);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const clearMedia = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl("");
    setMedia(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const selectMedia = (event) => {
    const file = event.target.files?.[0] || null;
    setError("");
    if (!file) return;
    if (!canPublish) {
      setError(english ? "Posting photos and videos requires NKATA Essential or Premium." : "Publicar fotografias e vídeos exige NKATA Essencial ou Premium.");
      event.target.value = "";
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setMedia(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const publish = async (event) => {
    event.preventDefault();
    if (!media || publishing || !canPublish) return;

    setPublishing(true);
    setError("");
    setStatus("");
    try {
      const result = await createPublication({ media, caption, visibility: "TODOS" });
      setData((current) => ({
        ...(current || {}),
        review_items: [result.publication, ...(current?.review_items || [])],
        capabilities: result.capabilities || current?.capabilities,
      }));
      clearMedia();
      setCaption("SEM_LEGENDA");
      setComposerOpen(false);
      setStatus(result.message || (english ? "Post submitted for review." : "Publicação enviada para análise."));
      window.setTimeout(() => setStatus(""), 4200);
    } catch (requestError) {
      setError(requestError.message || (english ? "Unable to submit the post." : "Não foi possível enviar a publicação."));
    } finally {
      setPublishing(false);
    }
  };

  const removeFromState = (id) => {
    setData((current) => ({
      ...(current || {}),
      results: (current?.results || []).filter((item) => item.id !== id),
      review_items: (current?.review_items || []).filter((item) => item.id !== id),
    }));
  };

  return (
    <main className="nk-member-home">
      <CompactPageHeader title={english ? "Home" : "Início"}>
        <button type="button" onClick={() => load()} disabled={loading} aria-label={english ? "Refresh feed" : "Atualizar feed"}>
          <RefreshCw size={19} className={loading ? "is-spinning" : ""} />
          {english ? "Refresh" : "Atualizar"}
        </button>
      </CompactPageHeader>

      <section className="nk-shell nk-member-home__layout">
        <div className="nk-member-home__feed-column">
          <form
            className={`nk-feed-composer ${canPublish ? "" : "is-locked"} ${composerOpen ? "is-open" : "is-collapsed"}`}
            onSubmit={publish}
          >
            <header>
              <span><ImagePlus size={20} /></span>
              <div>
                <strong>{english ? "New post" : "Nova publicação"}</strong>
              </div>
              {!canPublish && <LockKeyhole size={18} />}
              {canPublish && (
                <button
                  type="button"
                  className="nk-feed-composer__toggle"
                  onClick={() => setComposerOpen((current) => !current)}
                  aria-expanded={composerOpen}
                  aria-label={composerOpen ? (english ? "Close post composer" : "Fechar criação de publicação") : (english ? "Create post" : "Criar publicação")}
                >
                  <ChevronDown size={18} />
                </button>
              )}
            </header>

            {canPublish ? (
              <div className="nk-feed-composer__body">
                {previewUrl ? (
                  <div className="nk-feed-composer__preview">
                    {media?.type?.startsWith("video/") ? (
                      <video src={previewUrl} controls playsInline />
                    ) : (
                      <img src={previewUrl} alt={english ? "Preview" : "Pré-visualização"} />
                    )}
                    <button type="button" onClick={clearMedia} aria-label={english ? "Remove file" : "Remover ficheiro"}>
                      <X size={18} />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="nk-feed-composer__pick"
                    onClick={() => fileRef.current?.click()}
                  >
                    <ImagePlus size={22} />
                    <span>
                      <strong>{english ? "Photo or video" : "Foto ou vídeo"}</strong>
                    </span>
                  </button>
                )}

                <input
                  ref={fileRef}
                  type="file"
                  className="nk-feed-composer__file"
                  accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime"
                  onChange={selectMedia}
                />

                <div className="nk-feed-composer__options">
                  <label>
                    <span className="sr-only">{english ? "Caption" : "Frase"}</span>
                    <select value={caption} onChange={(event) => setCaption(event.target.value)}>
                      {captionOptions.map((option) => (
                        <option key={option.value} value={option.value}>{english ? (EN_CAPTIONS[option.value] || option.label) : option.label}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <button
                  type="submit"
                  className="nk-feed-composer__submit"
                  disabled={!media || publishing}
                >
                  {publishing ? <LoaderCircle size={18} className="is-spinning" /> : <Send size={18} />}
                  {publishing ? (english ? "Posting" : "A publicar") : (english ? "Post" : "Publicar")}
                </button>
              </div>
            ) : (
              <div className="nk-feed-composer__locked-copy">
                <LockKeyhole size={22} />
                <div>
                  <strong>{english ? "Posting requires a paid plan." : "Publicar exige um plano pago."}</strong>
                  <p>{english ? "Essential and Premium include photos and videos." : "Essencial e Premium permitem fotos e vídeos."}</p>
                </div>
                <button type="button" onClick={() => onNavigate("account")}>{english ? "View plans" : "Ver planos"}</button>
              </div>
            )}
          </form>

          {status && <div className="nk-member-home__status" role="status">{status}</div>}
          {error && <div className="nk-member-home__error" role="alert">{error}</div>}

          {reviewItems.length > 0 && (
            <section className="nk-feed-review-list">
              <header>
                <strong>{english ? "Under review" : "Em análise"}</strong>
              </header>
              <div>
                {reviewItems.map((publication) => (
                  <ReviewPublication
                    key={publication.id}
                    publication={publication}
                    onDeleted={removeFromState}
                    english={english}
                  />
                ))}
              </div>
            </section>
          )}

          <div className="nk-member-home__feed-heading">
            <div>
              <h2>{english ? "Posts" : "Publicações"}</h2>
            </div>
          </div>

          {loading && !publications.length ? (
            <div className="nk-feed-loading" aria-label={english ? "Loading feed" : "A carregar feed"}>
              <span />
              <span />
              <span />
            </div>
          ) : publications.length ? (
            <div className="nk-feed-list">
              {publications.map((publication) => (
                <PublicationCard
                  key={publication.id}
                  publication={publication}
                  onOpenProfile={onOpenProfile}
                  onChanged={() => load({ silent: true })}
                  onDeleted={removeFromState}
                  english={english}
                />
              ))}
            </div>
          ) : (
            <div className="nk-feed-empty">
              <span><ImagePlus size={28} /></span>
              <h2>{english ? "No posts" : "Nenhuma publicação"}</h2>
              <p>{english ? "New posts will appear here after approval." : "Novas publicações aparecerão aqui após aprovação."}</p>
              <button type="button" onClick={() => onNavigate("discover")}>
                <UserRound size={17} /> {english ? "Explore profiles" : "Explorar perfis"}
              </button>
            </div>
          )}
        </div>

      </section>
    </main>
  );
}
