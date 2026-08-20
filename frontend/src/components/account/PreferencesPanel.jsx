import { Check, Languages, MessageCircle, Palette, Save } from "lucide-react";
import { useEffect, useState } from "react";

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

function Choice({ selected, label, previewClass, onSelect }) {
  return (
    <button
      type="button"
      className={`nk-preference-choice ${previewClass} ${selected ? "is-selected" : ""}`}
      onClick={onSelect}
      aria-pressed={selected}
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

  useEffect(() => setForm(preferences), [preferences]);

  const update = (field, value) => {
    setMessage("");
    const next = { ...form, [field]: value };
    setForm(next);
    onPreview?.(next);
  };

  const submit = async (event) => {
    event.preventDefault();
    try {
      await onSave({
        idioma: form.idioma,
        tema_perfil: form.tema_perfil,
        fundo_conversa: form.fundo_conversa,
      });
      setMessage(form.idioma === "EN" ? "Preferences saved." : "Preferências guardadas.");
      window.setTimeout(() => setMessage(""), 2600);
    } catch {
      // O erro detalhado é apresentado pelo estado partilhado da aplicação.
    }
  };

  if (loading && !preferences) {
    return <section className="nk-preferences-panel is-loading" aria-label="A carregar preferências"><span /><span /><span /></section>;
  }

  const english = form?.idioma === "EN";

  return (
    <form className="nk-preferences-panel" onSubmit={submit}>
      <header>
        <div>
          <span>{english ? "Personalisation" : "Personalização"}</span>
          <h2>{english ? "Make NKATA yours" : "Deixe o NKATA com o seu estilo"}</h2>
        </div>
        <button type="submit" disabled={saving}>
          <Save size={16} /> {saving ? (english ? "Saving…" : "A guardar…") : (english ? "Save" : "Guardar")}
        </button>
      </header>

      {(error || message) && (
        <div className={`nk-preferences-panel__message ${error ? "is-error" : "is-success"}`} role="status">
          {error || message}
        </div>
      )}

      <section className="nk-preference-section nk-preference-section--language">
        <div><Languages size={18} /><strong>{english ? "Interface language" : "Idioma da interface"}</strong></div>
        <div className="nk-language-switch">
          <button type="button" className={form.idioma === "PT" ? "is-selected" : ""} onClick={() => update("idioma", "PT")}>Português</button>
          <button type="button" className={form.idioma === "EN" ? "is-selected" : ""} onClick={() => update("idioma", "EN")}>English</button>
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
            />
          ))}
        </div>
      </section>
    </form>
  );
}
