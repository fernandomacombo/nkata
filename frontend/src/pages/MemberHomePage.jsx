import { useEffect, useMemo, useRef, useState } from "react";
import {
  BadgeCheck,
  ChevronDown,
  CirclePlay,
  Flower2,
  Heart,
  HeartHandshake,
  ImagePlus,
  LoaderCircle,
  LockKeyhole,
  MapPin,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserCheck,
  UserPlus,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
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

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  const now = new Date();
  const minutes = Math.max(0, Math.floor((now - date) / 60000));
  if (minutes < 1) return "Agora";
  if (minutes < 60) return `Há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Há ${hours} h`;
  return new Intl.DateTimeFormat("pt-MZ", { day: "2-digit", month: "short" }).format(date);
}

function PublicationMedia({ publication }) {
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
      alt={`Publicação de ${publication.profile.nome_publico}`}
      loading="lazy"
    />
  );
}

function PublicationCard({ publication, onOpenProfile, onChanged, onDeleted }) {
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
      setInterestMessage(error.message || "Não foi possível atualizar o interesse.");
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
              <img src={publication.profile.foto_url} alt="" />
            ) : (
              <UserRound size={24} />
            )}
          </span>
          <span>
            <strong>
              {publication.mine ? "A sua publicação" : publication.profile.nome_publico}
              {publication.profile.verificado && <BadgeCheck size={15} />}
            </strong>
            <small>
              <MapPin size={12} /> {publication.profile.cidade}
              <span>·</span>
              {formatDate(publication.created_at)}
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
            {following ? "A seguir" : "Seguir"}
          </button>
        ) : (
          <button
            type="button"
            className="nk-feed-card__delete"
            onClick={remove}
            disabled={deleting}
            aria-label="Remover publicação"
          >
            {deleting ? <LoaderCircle size={17} className="is-spinning" /> : <Trash2 size={17} />}
          </button>
        )}
      </header>

      <div className="nk-feed-card__media-wrap">
        <PublicationMedia publication={publication} />
        <span className="nk-feed-card__privacy">
          {publication.visibility === "MATCHES" ? <LockKeyhole size={13} /> : <UsersRound size={13} />}
          {publication.visibility_label}
        </span>
      </div>

      <div className="nk-feed-card__body">
        {publication.caption && <p className="nk-feed-card__caption">{publication.caption}</p>}

        <div className="nk-feed-card__reactions" aria-label="Reações à publicação">
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
              {interestActive ? "Interesse enviado" : "Tenho interesse"}
            </button>
            <button type="button" onClick={() => onOpenProfile?.(publication.profile)}>
              <UserRound size={17} /> Ver perfil
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

function ReviewPublication({ publication, onDeleted }) {
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
          <img src={publication.media_url} alt="" />
        )}
      </span>
      <span>
        <strong>{pending ? "Em análise" : "Não aprovada"}</strong>
        <small>
          {pending
            ? "Só você e a equipa NKATA conseguem ver este conteúdo."
            : (publication.moderation_note || "Esta publicação não foi aprovada.")}
        </small>
      </span>
      <button type="button" onClick={remove} disabled={deleting} aria-label="Remover envio">
        {deleting ? <LoaderCircle size={16} className="is-spinning" /> : <X size={17} />}
      </button>
    </article>
  );
}

export default function MemberHomePage({ onNavigate, onOpenProfile }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [media, setMedia] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [caption, setCaption] = useState("SEM_LEGENDA");
  const [visibility, setVisibility] = useState("TODOS");
  const [publishing, setPublishing] = useState(false);
  const [composerOpen, setComposerOpen] = useState(
    () => !window.matchMedia("(max-width: 820px)").matches,
  );
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
        setError(requestError.message || "Não foi possível carregar o feed.");
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
      setError("Publicar fotografias e vídeos exige NKATA Essencial ou Premium.");
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
      const result = await createPublication({ media, caption, visibility });
      setData((current) => ({
        ...(current || {}),
        review_items: [result.publication, ...(current?.review_items || [])],
        capabilities: result.capabilities || current?.capabilities,
      }));
      clearMedia();
      setCaption("SEM_LEGENDA");
      setStatus(result.message || "Publicação enviada para análise.");
      window.setTimeout(() => setStatus(""), 4200);
    } catch (requestError) {
      setError(requestError.message || "Não foi possível enviar a publicação.");
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

  const feedHeading = useMemo(() => (
    publications.length
      ? "Pessoas e momentos que podem fazer sentido para si."
      : "O feed começa quando a comunidade publica."
  ), [publications.length]);

  return (
    <main className="nk-member-home">
      <section className="nk-member-home__topbar">
        <div className="nk-shell nk-member-home__topbar-inner">
          <div>
            <span><ShieldCheck size={15} /> Comunidade privada</span>
            <h1>Início</h1>
          </div>
          <div>
            <button type="button" onClick={() => onNavigate("moments")}>
              <CirclePlay size={19} />
              <span>Momentos</span>
            </button>
            <button type="button" onClick={() => load()} disabled={loading} aria-label="Atualizar feed">
              <RefreshCw size={19} className={loading ? "is-spinning" : ""} />
            </button>
          </div>
        </div>
      </section>

      <section className="nk-shell nk-member-home__layout">
        <div className="nk-member-home__feed-column">
          <form
            className={`nk-feed-composer ${canPublish ? "" : "is-locked"} ${composerOpen ? "is-open" : "is-collapsed"}`}
            onSubmit={publish}
          >
            <header>
              <span><ImagePlus size={20} /></span>
              <div>
                <strong>Nova publicação</strong>
                <small>{capabilities?.plan_label || "A confirmar o seu plano"}</small>
              </div>
              {!canPublish && <LockKeyhole size={18} />}
              {canPublish && (
                <button
                  type="button"
                  className="nk-feed-composer__toggle"
                  onClick={() => setComposerOpen((current) => !current)}
                  aria-expanded={composerOpen}
                  aria-label={composerOpen ? "Fechar criação de publicação" : "Criar publicação"}
                >
                  <ChevronDown size={18} />
                </button>
              )}
            </header>

            {canPublish ? (
              <div className="nk-feed-composer__body">
                <div className="nk-feed-composer__policy">
                  <ShieldCheck size={17} />
                  <span>Sem texto livre. Fotos e vídeos passam por moderação antes de aparecer no feed.</span>
                </div>

                {previewUrl ? (
                  <div className="nk-feed-composer__preview">
                    {media?.type?.startsWith("video/") ? (
                      <video src={previewUrl} controls playsInline />
                    ) : (
                      <img src={previewUrl} alt="Pré-visualização" />
                    )}
                    <button type="button" onClick={clearMedia} aria-label="Remover ficheiro">
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
                      <strong>Escolher fotografia ou vídeo</strong>
                      <small>Imagem até 10 MB · vídeo até 60 MB</small>
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
                    <span>Frase NKATA</span>
                    <select value={caption} onChange={(event) => setCaption(event.target.value)}>
                      {captionOptions.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Quem pode ver</span>
                    <select value={visibility} onChange={(event) => setVisibility(event.target.value)}>
                      <option value="TODOS">Todos os membros</option>
                      <option value="MATCHES">Apenas matches</option>
                    </select>
                  </label>
                </div>

                <button
                  type="submit"
                  className="nk-feed-composer__submit"
                  disabled={!media || publishing}
                >
                  {publishing ? <LoaderCircle size={18} className="is-spinning" /> : <Send size={18} />}
                  {publishing ? "A enviar" : "Enviar para análise"}
                </button>
              </div>
            ) : (
              <div className="nk-feed-composer__locked-copy">
                <LockKeyhole size={22} />
                <div>
                  <strong>Publicações com media fazem parte dos planos pagos.</strong>
                  <p>Pode ver, reagir, seguir e demonstrar interesse no plano Livre. Para publicar fotografia ou vídeo, use Essencial ou Premium.</p>
                </div>
                <button type="button" onClick={() => onNavigate("account")}>Ver planos</button>
              </div>
            )}
          </form>

          {status && <div className="nk-member-home__status" role="status">{status}</div>}
          {error && <div className="nk-member-home__error" role="alert">{error}</div>}

          {reviewItems.length > 0 && (
            <section className="nk-feed-review-list">
              <header>
                <strong>As suas publicações em revisão</strong>
                <small>Conteúdo pendente não aparece para outros membros.</small>
              </header>
              <div>
                {reviewItems.map((publication) => (
                  <ReviewPublication
                    key={publication.id}
                    publication={publication}
                    onDeleted={removeFromState}
                  />
                ))}
              </div>
            </section>
          )}

          <div className="nk-member-home__feed-heading">
            <div>
              <span>Para si</span>
              <h2>{feedHeading}</h2>
            </div>
          </div>

          {loading && !publications.length ? (
            <div className="nk-feed-loading" aria-label="A carregar feed">
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
                />
              ))}
            </div>
          ) : (
            <div className="nk-feed-empty">
              <span><ImagePlus size={28} /></span>
              <h2>Ainda não há publicações aprovadas.</h2>
              <p>O NKATA não preenche o feed com conteúdo fictício. As publicações aparecem depois da moderação.</p>
              <button type="button" onClick={() => onNavigate("discover")}>
                <UserRound size={17} /> Explorar perfis
              </button>
            </div>
          )}
        </div>

        <aside className="nk-member-home__aside">
          <article>
            <ShieldCheck size={19} />
            <div>
              <strong>Feed sem comentários</strong>
              <p>As interações públicas ficam limitadas a reações, seguir e interesse.</p>
            </div>
          </article>
          <article>
            <UsersRound size={19} />
            <div>
              <strong>Prioridade às suas ligações</strong>
              <p>Pessoas que segue aparecem antes no feed, sem alterar as regras de privacidade.</p>
            </div>
          </article>
        </aside>
      </section>
    </main>
  );
}
