import { useEffect, useRef, useState } from "react";
import {
  CalendarDays,
  Camera,
  CheckCircle2,
  Eye,
  EyeOff,
  Globe2,
  Heart,
  ImageUp,
  Images,
  LockKeyhole,
  LogOut,
  MapPin,
  RefreshCw,
  Save,
  ShieldCheck,
  Play,
  UserRound,
  X,
} from "lucide-react";
import PlanPanel from "../components/account/PlanPanel.jsx";
import AccountSummaryPanel from "../components/account/AccountSummaryPanel.jsx";
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";
import {
  API_BASE_URL,
  fetchMyProfileGallery,
  updateMyProfileCover,
  uploadMyProfilePhoto,
} from "../services/api.js";

const objectiveOptions = [
  { value: "RELACIONAMENTO_SERIO", label: "Relacionamento sério" },
  { value: "CONHECER_COM_INTENCAO", label: "Conhecer pessoas com intenção" },
  { value: "AMIZADE_EVOLUIR", label: "Amizade que pode evoluir" },
  { value: "CASAMENTO_FUTURO", label: "Casamento no futuro" },
];

const emptyForm = {
  nome_publico: "",
  cidade: "",
  objetivo: "",
  sobre_si: "",
  o_que_valoriza: "",
  o_que_nao_aceita: "",
};

function formatMemberDate(value) {
  if (!value) return "";

  return new Intl.DateTimeFormat("pt-MZ", {
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

function objectiveLabel(value) {
  return objectiveOptions.find((option) => option.value === value)?.label || "Relação séria";
}

function InterestItem({ profile, onOpen }) {
  return (
    <button type="button" className="nk-account-interest" onClick={() => onOpen(profile)}>
      <span className="nk-account-interest__photo">
        {profile.foto_url ? (
          <img src={profile.foto_url} alt={`Foto de ${profile.nome_publico}`} />
        ) : (
          <UserRound size={28} />
        )}
      </span>
      <span>
        <strong>
          {profile.nome_publico}
          {profile.idade ? `, ${profile.idade}` : ""}
        </strong>
        <small><MapPin size={12} /> {profile.cidade}</small>
      </span>
      <Heart size={17} fill="currentColor" />
    </button>
  );
}

function ProfilePreview({ account, form, imageUrl, onClose }) {
  return (
    <div
      className="nk-profile-preview"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="nk-profile-preview__dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="profile-preview-title"
      >
        <header>
          <div>
            <span>Pré-visualização</span>
            <h2 id="profile-preview-title">Como o seu perfil aparece</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Fechar pré-visualização">
            <X size={20} />
          </button>
        </header>

        <div className="nk-profile-preview__layout">
          <div className="nk-profile-preview__photo">
            {imageUrl ? (
              <img src={imageUrl} alt={`Pré-visualização de ${form.nome_publico}`} />
            ) : (
              <UserRound size={70} strokeWidth={1.1} />
            )}
            <div />
            <span><ShieldCheck size={15} /> Perfil verificado</span>
            <section>
              <small>{objectiveLabel(form.objetivo)}</small>
              <strong>
                {form.nome_publico || account.nome_publico}
                {account.idade ? `, ${account.idade}` : ""}
              </strong>
              <em><MapPin size={13} /> {form.cidade || account.cidade}</em>
            </section>
          </div>

          <div className="nk-profile-preview__content">
            <span className="nk-eyebrow nk-eyebrow--dark">
              <ShieldCheck size={15} /> Perfil confirmado
            </span>
            <h3>{form.nome_publico || account.nome_publico}</h3>
            <p>{objectiveLabel(form.objetivo)}</p>

            <article>
              <strong>Sobre mim</strong>
              <p>{form.sobre_si || "A sua apresentação aparecerá aqui."}</p>
            </article>
            <article>
              <strong>O que valorizo</strong>
              <p>{form.o_que_valoriza || "Esta informação ainda não foi preenchida."}</p>
            </article>
            <article>
              <strong>O que não aceito</strong>
              <p>{form.o_que_nao_aceita || "Esta informação ainda não foi preenchida."}</p>
            </article>
          </div>
        </div>
      </section>
    </div>
  );
}

function ProfileGalleryManager() {
  const [gallery, setGallery] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetchMyProfileGallery({ signal: controller.signal })
      .then(setGallery)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          setError(requestError.message || "Não foi possível abrir a galeria.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const changeCover = async (publicationId) => {
    setSavingId(publicationId || "remove");
    setError("");
    setMessage("");
    try {
      const result = await updateMyProfileCover(publicationId);
      setGallery(result.gallery);
      setMessage(result.message);
      window.setTimeout(() => setMessage(""), 2600);
    } catch (requestError) {
      setError(requestError.message || "Não foi possível atualizar a capa.");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <section className="nk-account-gallery">
      <header>
        <div>
          <span><Images size={18} /></span>
          <div>
            <h2>Capa e galeria</h2>
            <p>Conteúdo aprovado aparece automaticamente.</p>
          </div>
        </div>
        {gallery?.coverPublicationId && (
          <button
            type="button"
            onClick={() => changeCover(null)}
            disabled={Boolean(savingId)}
          >
            Remover capa
          </button>
        )}
      </header>

      {loading ? (
        <div className="nk-account-gallery__loading" aria-label="A carregar galeria">
          <span /><span /><span />
        </div>
      ) : gallery?.results?.length ? (
        <div className="nk-account-gallery__grid">
          {gallery.results.map((item) => (
            <article key={item.id} className={item.isCover ? "is-cover" : ""}>
              {item.mediaType === "VIDEO" ? (
                <>
                  <video src={item.mediaUrl} muted playsInline preload="metadata" />
                  <span className="nk-account-gallery__video"><Play size={17} fill="currentColor" /></span>
                </>
              ) : (
                <img src={item.mediaUrl} alt="Publicação aprovada" loading="lazy" />
              )}

              {item.isCover ? (
                <strong>Capa</strong>
              ) : item.canBeCover ? (
                <button
                  type="button"
                  onClick={() => changeCover(item.id)}
                  disabled={Boolean(savingId)}
                >
                  {savingId === item.id ? "A guardar…" : "Usar como capa"}
                </button>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <div className="nk-account-gallery__empty">
          <Images size={22} />
          <span>As suas publicações aprovadas aparecerão aqui.</span>
        </div>
      )}

      {message && <div className="nk-account-gallery__message is-success">{message}</div>}
      {error && <div className="nk-account-gallery__message is-error">{error}</div>}
    </section>
  );
}

export default function AccountPage({
  account,
  interests,
  loading,
  saving,
  error,
  success,
  onReload,
  onSave,
  onToggleVisibility,
  onTogglePublicPreview,
  onOpenProfile,
  onSignOut,
}) {
  const [form, setForm] = useState(emptyForm);
  const [accountSection, setAccountSection] = useState("summary");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [pendingPhoto, setPendingPhoto] = useState(null);
  const [pendingPhotoUrl, setPendingPhotoUrl] = useState("");
  const [photoUploading, setPhotoUploading] = useState(false);
  const [photoError, setPhotoError] = useState("");
  const [photoSuccess, setPhotoSuccess] = useState("");
  const photoInputRef = useRef(null);

  useEffect(() => {
    if (!account) return;

    setForm({
      nome_publico: account.nome_publico || "",
      cidade: account.cidade || "",
      objetivo: account.objetivo || "",
      sobre_si: account.sobre_si || "",
      o_que_valoriza: account.o_que_valoriza || "",
      o_que_nao_aceita: account.o_que_nao_aceita || "",
    });
  }, [account]);

  useEffect(() => () => {
    if (pendingPhotoUrl) URL.revokeObjectURL(pendingPhotoUrl);
  }, [pendingPhotoUrl]);

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSave(form);
  };

  const clearPendingPhoto = () => {
    if (pendingPhotoUrl) URL.revokeObjectURL(pendingPhotoUrl);
    setPendingPhoto(null);
    setPendingPhotoUrl("");
    if (photoInputRef.current) photoInputRef.current.value = "";
  };

  const handlePhotoSelected = (event) => {
    const file = event.target.files?.[0];
    setPhotoError("");
    setPhotoSuccess("");

    if (!file) return;

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setPhotoError("Escolha uma fotografia em JPG, PNG ou WEBP.");
      event.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setPhotoError("A fotografia deve ter no máximo 5 MB.");
      event.target.value = "";
      return;
    }

    if (pendingPhotoUrl) URL.revokeObjectURL(pendingPhotoUrl);
    setPendingPhoto(file);
    setPendingPhotoUrl(URL.createObjectURL(file));
  };

  const handlePhotoUpload = async () => {
    if (!pendingPhoto || photoUploading) return;

    setPhotoUploading(true);
    setPhotoError("");
    setPhotoSuccess("");

    try {
      const result = await uploadMyProfilePhoto(pendingPhoto);
      setPhotoSuccess(result.message);
      clearPendingPhoto();
      await onReload();
      window.setTimeout(() => setPhotoSuccess(""), 2600);
    } catch (uploadError) {
      setPhotoError(uploadError.message || "Não foi possível atualizar a fotografia.");
    } finally {
      setPhotoUploading(false);
    }
  };

  if (loading && !account) {
    return (
      <main className="nk-account">
        <div className="nk-shell nk-account__loading">
          <span />
          <div><em /><em /><em /></div>
        </div>
      </main>
    );
  }

  if (!account) {
    return (
      <main className="nk-account">
        <div className="nk-shell nk-account__empty">
          <UserRound size={32} />
          <h1>Não foi possível abrir a sua conta</h1>
          <p>{error || "Tente novamente dentro de alguns instantes."}</p>
          <button type="button" className="nk-button nk-button--wine" onClick={onReload}>
            Tentar novamente
          </button>
        </div>
      </main>
    );
  }

  const displayedPhoto = pendingPhotoUrl || account.foto_url;

  return (
    <main className="nk-account">
      <CompactPageHeader title="Conta">
        <button type="button" className="nk-account__preview-button" onClick={() => setPreviewOpen(true)}>
          <Eye size={17} /> Pré-visualizar
        </button>
        <button type="button" className="nk-account__reload" onClick={onReload} disabled={loading}>
          <RefreshCw size={17} className={loading ? "is-spinning" : ""} />
          Atualizar
        </button>
      </CompactPageHeader>

      <section className="nk-shell nk-account__layout">
        <aside className="nk-account__sidebar">
          <article className="nk-account-card">
            <div className="nk-account-card__photo">
              {displayedPhoto ? (
                <img src={displayedPhoto} alt={`Foto de ${account.nome_publico}`} />
              ) : (
                <UserRound size={52} strokeWidth={1.25} />
              )}
              <span><ShieldCheck size={15} /></span>
              <button
                type="button"
                className="nk-account-card__camera"
                onClick={() => photoInputRef.current?.click()}
                aria-label="Alterar fotografia"
              >
                <Camera size={16} />
              </button>
            </div>

            <input
              ref={photoInputRef}
              className="nk-account-card__file-input"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handlePhotoSelected}
            />

            <button
              type="button"
              className="nk-account-card__photo-button"
              onClick={() => photoInputRef.current?.click()}
              disabled={photoUploading}
            >
              <ImageUp size={16} /> Alterar fotografia
            </button>

            {pendingPhoto && (
              <div className="nk-account-card__photo-confirm">
                <span>Nova fotografia selecionada</span>
                <div>
                  <button type="button" onClick={clearPendingPhoto} disabled={photoUploading}>
                    Cancelar
                  </button>
                  <button type="button" onClick={handlePhotoUpload} disabled={photoUploading}>
                    {photoUploading ? "A enviar…" : "Usar esta foto"}
                  </button>
                </div>
              </div>
            )}

            {photoError && <div className="nk-account-card__photo-message is-error">{photoError}</div>}
            {photoSuccess && <div className="nk-account-card__photo-message is-success">{photoSuccess}</div>}

            <h2>{account.nome_publico}</h2>
            <p><MapPin size={14} /> {account.cidade}</p>
            <div className="nk-account-card__facts">
              <span>{account.idade} anos</span>
              <span>{account.objetivo_display}</span>
            </div>
            <small className="nk-account-card__private-email">
              <LockKeyhole size={12} /> {account.email} · privado
            </small>

            <div className={`nk-account-card__visibility ${account.visivel ? "is-visible" : ""}`}>
              {account.visivel ? <Eye size={16} /> : <EyeOff size={16} />}
              <div>
                <strong>{account.visivel ? "Perfil visível" : "Perfil oculto"}</strong>
                <span>
                  {account.visivel
                    ? "Pode aparecer na área de perfis."
                    : "Não aparece para outros membros."}
                </span>
              </div>
            </div>

            <button
              type="button"
              className="nk-account-card__visibility-button"
              onClick={() => onToggleVisibility(!account.visivel)}
              disabled={saving}
            >
              {account.visivel ? <EyeOff size={17} /> : <Eye size={17} />}
              {account.visivel ? "Ocultar perfil" : "Mostrar perfil"}
            </button>

            <div className={`nk-account-card__public-preview ${account.destaque_publico ? "is-active" : ""}`}>
              <div className="nk-account-card__public-preview-heading">
                <span><Globe2 size={17} /></span>
                <div>
                  <strong>Apresentação pública</strong>
                  <small>
                    {account.destaque_publico
                      ? "O seu cartão pode aparecer antes do login."
                      : account.destaque_publico_elegivel
                        ? "Autorize o seu cartão na página pública."
                        : account.visivel
                          ? "A fotografia aguarda aprovação."
                          : "Primeiro torne o perfil visível."}
                  </small>
                </div>
              </div>

              <div className="nk-account-card__public-preview-meta">
                <span>{account.destaque_publico_exibicoes} aparições</span>
                <em>{account.destaque_publico ? "Ativo" : "Desligado"}</em>
              </div>

              <button
                type="button"
                onClick={() => onTogglePublicPreview(!account.destaque_publico)}
                disabled={
                  saving
                  || (!account.destaque_publico && !account.destaque_publico_elegivel)
                }
                aria-pressed={account.destaque_publico}
              >
                {account.destaque_publico ? "Retirar da página pública" : "Permitir apresentação pública"}
              </button>

              {error && <small className="nk-account-card__public-preview-message is-error">{error}</small>}
              {success && <small className="nk-account-card__public-preview-message is-success">{success}</small>}
            </div>
          </article>

          <div className="nk-account__stats">
            <article>
              <strong>{account.total_matches}</strong>
              <span>Matches</span>
            </article>
            <article>
              <strong>{account.total_interesses_enviados}</strong>
              <span>Interesses enviados</span>
            </article>
          </div>

          {account.membro_desde && (
            <div className="nk-account__member-since">
              <CalendarDays size={17} />
              <span>Membro desde {formatMemberDate(account.membro_desde)}</span>
            </div>
          )}
        </aside>

        <div className="nk-account__main">
          <nav className="nk-account-tabs" aria-label="Áreas da conta">
            {[
              ["summary", "Resumo"],
              ["profile", "Perfil"],
              ["plan", "Plano"],
              ["interests", "Interesses"],
              ["security", "Segurança"],
            ].map(([section, label]) => (
              <button
                type="button"
                key={section}
                className={accountSection === section ? "is-active" : ""}
                onClick={() => setAccountSection(section)}
                aria-current={accountSection === section ? "page" : undefined}
              >
                {label}
              </button>
            ))}
          </nav>

          {accountSection === "summary" && (
            <AccountSummaryPanel onOpenSection={setAccountSection} />
          )}

          {accountSection === "profile" && (
            <>
            <form className="nk-account-form" onSubmit={handleSubmit}>
            <div className="nk-account-form__heading">
              <div>
                <h2>Editar perfil</h2>
                <p>Estas informações aparecem no seu perfil.</p>
              </div>
              <button type="submit" className="nk-button nk-button--wine" disabled={saving}>
                <Save size={17} />
                {saving ? "A guardar…" : "Guardar alterações"}
              </button>
            </div>

            {error && <div className="nk-account-form__message is-error">{error}</div>}
            {success && (
              <div className="nk-account-form__message is-success">
                <CheckCircle2 size={17} /> {success}
              </div>
            )}

            <div className="nk-account-form__grid">
              <label>
                <span>Nome apresentado</span>
                <input
                  type="text"
                  value={form.nome_publico}
                  onChange={(event) => updateField("nome_publico", event.target.value)}
                  maxLength={120}
                  required
                />
              </label>

              <label>
                <span>Cidade</span>
                <input
                  type="text"
                  value={form.cidade}
                  onChange={(event) => updateField("cidade", event.target.value)}
                  maxLength={100}
                  required
                />
              </label>

              <label className="nk-account-form__wide">
                <span>O que procura</span>
                <select
                  value={form.objetivo}
                  onChange={(event) => updateField("objetivo", event.target.value)}
                  required
                >
                  {objectiveOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>

              <label className="nk-account-form__wide">
                <span>Sobre si</span>
                <textarea
                  value={form.sobre_si}
                  onChange={(event) => updateField("sobre_si", event.target.value)}
                  maxLength={1800}
                  minLength={30}
                  rows={5}
                  required
                />
                <small>Mínimo 30 caracteres · {form.sobre_si.length}/1800</small>
              </label>

              <label className="nk-account-form__wide">
                <span>O que valoriza numa relação</span>
                <textarea
                  value={form.o_que_valoriza}
                  onChange={(event) => updateField("o_que_valoriza", event.target.value)}
                  maxLength={1800}
                  minLength={18}
                  rows={4}
                  required
                />
                <small>Mínimo 18 caracteres · {form.o_que_valoriza.length}/1800</small>
              </label>

              <label className="nk-account-form__wide">
                <span>O que não aceita</span>
                <textarea
                  value={form.o_que_nao_aceita}
                  onChange={(event) => updateField("o_que_nao_aceita", event.target.value)}
                  maxLength={1800}
                  minLength={12}
                  rows={4}
                  required
                />
                <small>Mínimo 12 caracteres · {form.o_que_nao_aceita.length}/1800</small>
              </label>
            </div>
            </form>
            <ProfileGalleryManager />
            </>
          )}

          {accountSection === "plan" && <PlanPanel />}

          {accountSection === "interests" && (
            <section className="nk-account-interests">
              <div className="nk-account-interests__heading">
                <div>
                  <h2>Interesses enviados</h2>
                </div>
                <span>{interests.length}</span>
              </div>

              {interests.length ? (
                <div className="nk-account-interests__list">
                  {interests.map((profile) => (
                    <InterestItem key={profile.id} profile={profile} onOpen={onOpenProfile} />
                  ))}
                </div>
              ) : (
                <div className="nk-account-interests__empty">
                  <Heart size={22} />
                  <span>Nenhum interesse enviado.</span>
                </div>
              )}
            </section>
          )}

          {accountSection === "security" && (
            <section className="nk-account-security">
              <div>
                <span><LockKeyhole size={19} /></span>
                <div>
                  <h2>Segurança</h2>
                  <p>Palavra-passe e documentos são privados.</p>
                </div>
              </div>

              <div className="nk-account-security__actions">
                <button
                  type="button"
                  onClick={() => window.location.assign(
                    new URL("/minha-conta/alterar-senha/", API_BASE_URL).toString(),
                  )}
                >
                  Alterar palavra-passe
                </button>
                <button type="button" className="is-danger" onClick={onSignOut}>
                  <LogOut size={16} /> Terminar sessão
                </button>
              </div>
            </section>
          )}
        </div>
      </section>

      {previewOpen && (
        <ProfilePreview
          account={account}
          form={form}
          imageUrl={displayedPhoto}
          onClose={() => setPreviewOpen(false)}
        />
      )}
    </main>
  );
}
