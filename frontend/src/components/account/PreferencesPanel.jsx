import { Check, Languages, LoaderCircle, MessageCircle, Palette } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const profileThemes = [
  { value: "CLASSICO", pt: "Clássico", en: "Classic", className: "is-classic" },
  { value: "AREIA", pt: "Areia", en: "Sand", className: "is-sand" },
  { value: "NOITE", pt: "Noite", en: "Night", className: "is-night" },
];

const chatBackgrounds = [
  { value: "SERENO", pt: "Sereno", en: "Serene", className: "is-serene" },
  { value: "BOTANICO", pt: "Botânico", en: "Botanical", className: "is-botanical" },
  { value: "NOTURNO", pt: "Noturno", en: "Dark", className: "is-dark" },
];

function Choice({ selected, label, previewClass, onSelect, disabled }) {
  return (
    <button
      type="button"
      className={`nk-preference-choice ${previewClass} ${selected ? "is-selected" : ""}`}
      onClick={onSelect}
      aria-pressed={selected}
      disabled={disabled}
    >
      <span aria-hidden="true"><i /><i /><i /></span>
      <strong>{label}</strong>
      {selected && <em><Check size={13} /></em>}
    </button>
  );
}

export default function PreferencesPanel({ preferences, loading, saving, error, onPreview, onSave }) {
  const [form, setForm] = useState(preferences);
  const [message, setMessage] = useState("");
  const messageTimer = useRef(null);

  useEffect(() => setForm(preferences), [preferences]);

  useEffect(() => () => window.clearTimeout(messageTimer.current), []);

  const update = async (field, value) => {
    if (saving || form[field] === value) return;

    const previous = form;
    setMessage("");
    const next = { ...form, [field]: value };
    setForm(next);
    onPreview?.(next);

    try {
      const saved = await onSave({ [field]: value });
      setForm(saved);
      setMessage(saved.idioma === "EN" ? "Saved automatically." : "Guardado automaticamente.");
      window.clearTimeout(messageTimer.current);
      messageTimer.current = window.setTimeout(() => setMessage(""), 2200);
    } catch {
      setForm(previous);
      onPreview?.(previous);
    }
  };

  if (loading && !preferences) {
    return <section className="nk-preferences-panel is-loading" aria-label="A carregar preferências"><span /><span /><span /></section>;
  }

  const english = form?.idioma === "EN";

  return (
    <section className="nk-preferences-panel">
      <header>
        <div>
          <span>{english ? "Personalisation" : "Personalização"}</span>
          <h2>{english ? "Make NKATA yours" : "Deixe o NKATA com o seu estilo"}</h2>
        </div>
        <span className={`nk-preferences-panel__autosave ${saving ? "is-saving" : ""}`} role="status">
          {saving ? <LoaderCircle size={15} /> : <Check size={15} />}
          {saving ? (english ? "Saving…" : "A guardar…") : (english ? "Auto-save" : "Automático")}
        </span>
      </header>

      {(error || message) && (
        <div className={`nk-preferences-panel__message ${error ? "is-error" : "is-success"}`} role="status">
          {error || message}
        </div>
      )}

      <section className="nk-preference-section nk-preference-section--language">
        <div><Languages size={18} /><strong>{english ? "Interface language" : "Idioma da interface"}</strong></div>
        <div className="nk-language-switch">
          <button type="button" disabled={saving} className={form.idioma === "PT" ? "is-selected" : ""} onClick={() => update("idioma", "PT")}>Português</button>
          <button type="button" disabled={saving} className={form.idioma === "EN" ? "is-selected" : ""} onClick={() => update("idioma", "EN")}>English</button>
        </div>
      </section>

      <section className="nk-preference-section">
        <div><Palette size={18} /><strong>{english ? "App theme" : "Tema da aplicação"}</strong></div>
        <div className="nk-preference-grid">
          {profileThemes.map((theme) => (
            <Choice
              key={theme.value}
              selected={form.tema_perfil === theme.value}
              label={english ? theme.en : theme.pt}
              previewClass={theme.className}
              onSelect={() => update("tema_perfil", theme.value)}
              disabled={saving}
            />
          ))}
        </div>
      </section>

      <section className="nk-preference-section">
        <div><MessageCircle size={18} /><strong>{english ? "Chat background" : "Fundo das conversas"}</strong></div>
        <div className="nk-preference-grid">
          {chatBackgrounds.map((background) => (
            <Choice
              key={background.value}
              selected={form.fundo_conversa === background.value}
              label={english ? background.en : background.pt}
              previewClass={background.className}
              onSelect={() => update("fundo_conversa", background.value)}
              disabled={saving}
            />
          ))}
        </div>
      </section>
    </section>
  );
}
