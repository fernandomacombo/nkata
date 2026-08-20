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
import PreferencesPanel from "../components/account/PreferencesPanel.jsx";
import CompactPageHeader from "../components/layout/CompactPageHeader.jsx";
import {
  API_BASE_URL,
  fetchMyProfileGallery,
  updateMyProfileCover,
  uploadMyProfilePhoto,
} from "../services/api.js";

const objectiveOptions = [
  { value: "RELACIONAMENTO_SERIO", pt: "Relacionamento sério", en: "Serious relationship" },
  { value: "CONHECER_COM_INTENCAO", pt: "Conhecer pessoas com intenção", en: "Meet people with intention" },
  { value: "AMIZADE_EVOLUIR", pt: "Amizade que pode evoluir", en: "Friendship that may grow" },
  { value: "CASAMENTO_FUTURO", pt: "Casamento no futuro", en: "Marriage in the future" },
];

const emptyForm = {
  nome_publico: "",
  cidade: "",
  objetivo: "",
  sobre_si: "",
  o_que_valoriza: "",
  o_que_nao_aceita: "",
};

function formatMemberDate(value, language) {
  if (!value) return "";

  return new Intl.DateTimeFormat(language === "EN" ? "en-GB" : "pt-MZ", {
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

function objectiveLabel(value, language) {
  const option = objectiveOptions.find((item) => item.value === value);
  return language === "EN" ? (option?.en || "Serious relationship") : (option?.pt || "Relação séria");
}

function InterestItem({ profile, onOpen, language }) {
  return (
    <button type="button" className="nk-account-interest" onClick={() => onOpen(profile)}>
      <span className="nk-account-interest__photo">
        {profile.foto_url ? (
          <img src={profile.foto_url} alt={`${language === "EN" ? "Photo of" : "Foto de"} ${profile.nome_publico}`} />
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

function ProfilePreview({ account, form, imageUrl, language, onClose }) {
  const english = language === "EN";
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
            <span>{english ? "Preview" : "Pré-visualização"}</span>
            <h2 id="profile-preview-title">{english ? "How your profile appears" : "Como o seu perfil aparece"}</h2>
          </div>
          <button type="button" onClick={onClose} aria-label={english ? "Close preview" : "Fechar pré-visualização"}>
            <X size={20} />
          </button>
        </header>

        <div className="nk-profile-preview__layout">
          <div className="nk-profile-preview__photo">
            {imageUrl ? (
              <img src={imageUrl} alt={`${english ? "Preview of" : "Pré-visualização de"} ${form.nome_publico}`} />
            ) : (
              <UserRound size={70} strokeWidth={1.1} />
            )}
            <div />
            <span><ShieldCheck size={15} /> {english ? "Verified profile" : "Perfil verificado"}</span>
            <section>
              <small>{objectiveLabel(form.objetivo, language)}</small>
              <strong>
                {form.nome_publico || account.nome_publico}
                {account.idade ? `, ${account.idade}` : ""}
              </strong>
              <em><MapPin size={13} /> {form.cidade || account.cidade}</em>
            </section>
          </div>

          <div className="nk-profile-preview__content">
            <span className="nk-eyebrow nk-eyebrow--dark">
              <ShieldCheck size={15} /> {english ? "Confirmed profile" : "Perfil confirmado"}
            </span>
            <h3>{form.nome_publico || account.nome_publico}</h3>
            <p>{objectiveLabel(form.objetivo, language)}</p>

            <article>
              <strong>{english ? "About me" : "Sobre mim"}</strong>
              <p>{form.sobre_si || (english ? "Your introduction will appear here." : "A sua apresentação aparecerá aqui.")}</p>
            </article>
            <article>
              <strong>{english ? "What I value" : "O que valorizo"}</strong>
              <p>{form.o_que_valoriza || (english ? "This information has not been added yet." : "Esta informação ainda não foi preenchida.")}</p>
            </article>
            <article>
              <strong>{english ? "What I do not accept" : "O que não aceito"}</strong>
              <p>{form.o_que_nao_aceita || (english ? "This information has not been added yet." : "Esta informação ainda não foi preenchida.")}</p>
            </article>
          </div>
        </div>
      </section>
    </div>
  );
}

function ProfileGalleryManager({ language }) {
  const english = language === "EN";
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
          setError(requestError.message || (english ? "Could not open the gallery." : "Não foi possível abrir a galeria."));
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
      setError(requestError.message || (english ? "Could not update the cover." : "Não foi possível atualizar a capa."));
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
            <h2>{english ? "Cover and gallery" : "Capa e galeria"}</h2>
            <p>{english ? "Approved content appears automatically." : "Conteúdo aprovado aparece automaticamente."}</p>
          </div>
        </div>
        {gallery?.coverPublicationId && (
          <button
            type="button"
            onClick={() => changeCover(null)}
            disabled={Boolean(savingId)}
          >
            {english ? "Remove cover" : "Remover capa"}
          </button>
        )}
      </header>

      {loading ? (
        <div className="nk-account-gallery__loading" aria-label={english ? "Loading gallery" : "A carregar galeria"}>
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
                <img src={item.mediaUrl} alt={english ? "Approved publication" : "Publicação aprovada"} loading="lazy" />
              )}

              {item.isCover ? (
                <strong>{english ? "Cover" : "Capa"}</strong>
              ) : item.canBeCover ? (
                <button
                  type="button"
                  onClick={() => changeCover(item.id)}
                  disabled={Boolean(savingId)}
                >
                  {savingId === item.id
                    ? (english ? "Saving…" : "A guardar…")
                    : (english ? "Use as cover" : "Usar como capa")}
                </button>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <div className="nk-account-gallery__empty">
          <Images size={22} />
          <span>{english ? "Your approved publications will appear here." : "As suas publicações aprovadas aparecerão aqui."}</span>
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
  preferences,
  preferencesLoading,
  preferencesSaving,
  preferencesError,
  onPreviewPreferences,
  onSavePreferences,
}) {
  const language = preferences?.idioma === "EN" ? "EN" : "PT";
  const english = language === "EN";
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
      setPhotoError(english ? "Choose a JPG, PNG or WEBP photo." : "Escolha uma fotografia em JPG, PNG ou WEBP.");
      event.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setPhotoError(english ? "The photo must be no larger than 5 MB." : "A fotografia deve ter no máximo 5 MB.");
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
      setPhotoError(uploadError.message || (english ? "Could not update the photo." : "Não foi possível atualizar a fotografia."));
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
          <h1>{english ? "Could not open your account" : "Não foi possível abrir a sua conta"}</h1>
          <p>{error || (english ? "Try again in a few moments." : "Tente novamente dentro de alguns instantes.")}</p>
          <button type="button" className="nk-button nk-button--wine" onClick={onReload}>
            {english ? "Try again" : "Tentar novamente"}
          </button>
        </div>
      </main>
    );
  }

  const displayedPhoto = pendingPhotoUrl || account.foto_url;

  return (
    <main className="nk-account">
      <CompactPageHeader title={english ? "Account" : "Conta"}>
        <button type="button" className="nk-account__preview-button" onClick={() => setPreviewOpen(true)}>
          <Eye size={17} /> {english ? "Preview" : "Pré-visualizar"}
        </button>
        <button type="button" className="nk-account__reload" onClick={onReload} disabled={loading}>
          <RefreshCw size={17} className={loading ? "is-spinning" : ""} />
          {english ? "Refresh" : "Atualizar"}
        </button>
      </CompactPageHeader>

      <section className="nk-shell nk-account__layout">
        <aside className="nk-account__sidebar">
          <article className="nk-account-card">
            <div className="nk-account-card__photo">
              {displayedPhoto ? (
                <img src={displayedPhoto} alt={`${english ? "Photo of" : "Foto de"} ${account.nome_publico}`} />
              ) : (
                <UserRound size={52} strokeWidth={1.25} />
              )}
              <span><ShieldCheck size={15} /></span>
              <button
                type="button"
                className="nk-account-card__camera"
                onClick={() => photoInputRef.current?.click()}
                aria-label={english ? "Change photo" : "Alterar fotografia"}
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
              <ImageUp size={16} /> {english ? "Change photo" : "Alterar fotografia"}
            </button>

            {pendingPhoto && (
              <div className="nk-account-card__photo-confirm">
                <span>{english ? "New photo selected" : "Nova fotografia selecionada"}</span>
                <div>
                  <button type="button" onClick={clearPendingPhoto} disabled={photoUploading}>
                    {english ? "Cancel" : "Cancelar"}
                  </button>
                  <button type="button" onClick={handlePhotoUpload} disabled={photoUploading}>
                    {photoUploading
                      ? (english ? "Uploading…" : "A enviar…")
                      : (english ? "Use this photo" : "Usar esta foto")}
                  </button>
                </div>
              </div>
            )}

            {photoError && <div className="nk-account-card__photo-message is-error">{photoError}</div>}
            {photoSuccess && <div className="nk-account-card__photo-message is-success">{photoSuccess}</div>}

            <h2>{account.nome_publico}</h2>
            <p><MapPin size={14} /> {account.cidade}</p>
            <div className="nk-account-card__facts">
              <span>{account.idade} {english ? "years" : "anos"}</span>
              <span>{objectiveLabel(account.objetivo, language)}</span>
            </div>
            <small className="nk-account-card__private-email">
              <LockKeyhole size={12} /> {account.email} · {english ? "private" : "privado"}
            </small>

            <div className={`nk-account-card__visibility ${account.visivel ? "is-visible" : ""}`}>
              {account.visivel ? <Eye size={16} /> : <EyeOff size={16} />}
              <div>
                <strong>{account.visivel
                  ? (english ? "Visible profile" : "Perfil visível")
                  : (english ? "Hidden profile" : "Perfil oculto")}</strong>
                <span>
                  {account.visivel
                    ? (english ? "It can appear in the profiles area." : "Pode aparecer na área de perfis.")
                    : (english ? "It is not shown to other members." : "Não aparece para outros membros.")}
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
              {account.visivel
                ? (english ? "Hide profile" : "Ocultar perfil")
                : (english ? "Show profile" : "Mostrar perfil")}
            </button>

            <div className={`nk-account-card__public-preview ${account.destaque_publico ? "is-active" : ""}`}>
              <div className="nk-account-card__public-preview-heading">
                <span><Globe2 size={17} /></span>
                <div>
                  <strong>{english ? "Public introduction" : "Apresentação pública"}</strong>
                  <small>
                    {account.destaque_publico
                      ? (english ? "Your card can appear before sign-in." : "O seu cartão pode aparecer antes do login.")
                      : account.destaque_publico_elegivel
                        ? (english ? "Allow your card on the public page." : "Autorize o seu cartão na página pública.")
                        : account.visivel
                          ? (english ? "The photo is awaiting approval." : "A fotografia aguarda aprovação.")
                          : (english ? "First make the profile visible." : "Primeiro torne o perfil visível.")}
                  </small>
                </div>
              </div>

              <div className="nk-account-card__public-preview-meta">
                <span>{account.destaque_publico_exibicoes} {english ? "appearances" : "aparições"}</span>
                <em>{account.destaque_publico
                  ? (english ? "Active" : "Ativo")
                  : (english ? "Off" : "Desligado")}</em>
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
                {account.destaque_publico
                  ? (english ? "Remove from public page" : "Retirar da página pública")
                  : (english ? "Allow public introduction" : "Permitir apresentação pública")}
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
              <span>{english ? "Interests sent" : "Interesses enviados"}</span>
            </article>
          </div>

          {account.membro_desde && (
            <div className="nk-account__member-since">
              <CalendarDays size={17} />
              <span>{english ? "Member since" : "Membro desde"} {formatMemberDate(account.membro_desde, language)}</span>
            </div>
          )}
        </aside>

        <div className="nk-account__main">
          <nav className="nk-account-tabs" aria-label={english ? "Account areas" : "Áreas da conta"}>
            {[
              ["summary", english ? "Summary" : "Resumo"],
              ["profile", english ? "Profile" : "Perfil"],
              ["plan", english ? "Plan" : "Plano"],
              ["interests", english ? "Interests" : "Interesses"],
              ["preferences", english ? "Appearance" : "Aparência"],
              ["security", english ? "Security" : "Segurança"],
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
            <AccountSummaryPanel language={language} onOpenSection={setAccountSection} />
          )}

          {accountSection === "profile" && (
            <>
            <form className="nk-account-form" onSubmit={handleSubmit}>
            <div className="nk-account-form__heading">
              <div>
                <h2>{english ? "Edit profile" : "Editar perfil"}</h2>
                <p>{english ? "This information appears on your profile." : "Estas informações aparecem no seu perfil."}</p>
              </div>
              <button type="submit" className="nk-button nk-button--wine" disabled={saving}>
                <Save size={17} />
                {saving
                  ? (english ? "Saving…" : "A guardar…")
                  : (english ? "Save changes" : "Guardar alterações")}
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
                <span>{english ? "Display name" : "Nome apresentado"}</span>
                <input
                  type="text"
                  value={form.nome_publico}
                  onChange={(event) => updateField("nome_publico", event.target.value)}
                  maxLength={120}
                  required
                />
              </label>

              <label>
                <span>{english ? "City" : "Cidade"}</span>
                <input
                  type="text"
                  value={form.cidade}
                  onChange={(event) => updateField("cidade", event.target.value)}
                  maxLength={100}
                  required
                />
              </label>

              <label className="nk-account-form__wide">
                <span>{english ? "What you are looking for" : "O que procura"}</span>
                <select
                  value={form.objetivo}
                  onChange={(event) => updateField("objetivo", event.target.value)}
                  required
                >
                  {objectiveOptions.map((option) => (
                    <option key={option.value} value={option.value}>{english ? option.en : option.pt}</option>
                  ))}
                </select>
              </label>

              <label className="nk-account-form__wide">
                <span>{english ? "About you" : "Sobre si"}</span>
                <textarea
                  value={form.sobre_si}
                  onChange={(event) => updateField("sobre_si", event.target.value)}
                  maxLength={1800}
                  minLength={30}
                  rows={5}
                  required
                />
                <small>{english ? "Minimum 30 characters" : "Mínimo 30 caracteres"} · {form.sobre_si.length}/1800</small>
              </label>

              <label className="nk-account-form__wide">
                <span>{english ? "What you value in a relationship" : "O que valoriza numa relação"}</span>
                <textarea
                  value={form.o_que_valoriza}
                  onChange={(event) => updateField("o_que_valoriza", event.target.value)}
                  maxLength={1800}
                  minLength={18}
                  rows={4}
                  required
                />
                <small>{english ? "Minimum 18 characters" : "Mínimo 18 caracteres"} · {form.o_que_valoriza.length}/1800</small>
              </label>

              <label className="nk-account-form__wide">
                <span>{english ? "What you do not accept" : "O que não aceita"}</span>
                <textarea
                  value={form.o_que_nao_aceita}
                  onChange={(event) => updateField("o_que_nao_aceita", event.target.value)}
                  maxLength={1800}
                  minLength={12}
                  rows={4}
                  required
                />
                <small>{english ? "Minimum 12 characters" : "Mínimo 12 caracteres"} · {form.o_que_nao_aceita.length}/1800</small>
              </label>
            </div>
            </form>
            <ProfileGalleryManager language={language} />
            </>
          )}

          {accountSection === "plan" && <PlanPanel language={language} />}

          {accountSection === "interests" && (
            <section className="nk-account-interests">
              <div className="nk-account-interests__heading">
                <div>
                  <h2>{english ? "Interests sent" : "Interesses enviados"}</h2>
                </div>
                <span>{interests.length}</span>
              </div>

              {interests.length ? (
                <div className="nk-account-interests__list">
                  {interests.map((profile) => (
                    <InterestItem key={profile.id} profile={profile} language={language} onOpen={onOpenProfile} />
                  ))}
                </div>
              ) : (
                <div className="nk-account-interests__empty">
                  <Heart size={22} />
                  <span>{english ? "No interests sent." : "Nenhum interesse enviado."}</span>
                </div>
              )}
            </section>
          )}

          {accountSection === "preferences" && (
            <PreferencesPanel
              preferences={preferences}
              loading={preferencesLoading}
              saving={preferencesSaving}
              error={preferencesError}
              onPreview={onPreviewPreferences}
              onSave={onSavePreferences}
            />
          )}

          {accountSection === "security" && (
            <section className="nk-account-security">
              <div>
                <span><LockKeyhole size={19} /></span>
                <div>
                  <h2>{english ? "Security" : "Segurança"}</h2>
                  <p>{english ? "Your password and documents are private." : "Palavra-passe e documentos são privados."}</p>
                </div>
              </div>

              <div className="nk-account-security__actions">
                <button
                  type="button"
                  onClick={() => window.location.assign(
                    new URL("/minha-conta/alterar-senha/", API_BASE_URL).toString(),
                  )}
                >
                  {english ? "Change password" : "Alterar palavra-passe"}
                </button>
                <button type="button" className="is-danger" onClick={onSignOut}>
                  <LogOut size={16} /> {english ? "Sign out" : "Terminar sessão"}
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
          language={language}
          onClose={() => setPreviewOpen(false)}
        />
      )}
    </main>
  );
}
