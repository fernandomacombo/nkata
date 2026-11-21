import "../questionnaire.css";

const habits = {
  smoking: [["never", "Não fumo", "I don't smoke"], ["occasionally", "Fumo ocasionalmente", "I smoke occasionally"], ["regularly", "Fumo", "I smoke"]],
  drinking: [["never", "Não bebo", "I don't drink"], ["occasionally", "Bebo ocasionalmente", "I drink occasionally"], ["regularly", "Bebo regularmente", "I drink regularly"]],
  education: [["primary", "Ensino primário", "Primary education"], ["secondary", "Ensino secundário", "Secondary education"], ["technical", "Formação técnico-profissional", "Technical or vocational training"], ["higher", "Ensino superior", "Higher education"], ["other", "Outro", "Other"]],
  occupation: [["working", "Trabalho", "Working"], ["studying", "Estudo", "Studying"], ["both", "Trabalho e estudo", "Working and studying"], ["looking", "Procuro trabalho", "Looking for work"], ["other", "Outra situação", "Other"]],
};

export function legacyAges(value = "") {
  const match = value.match(/^\s*(\d{2,3})\s*(?:a|[-–—])\s*(\d{2,3})(?:\s+anos)?\s*$/i);
  if (!match) return /^sem preferência$/i.test(value.trim()) ? null : undefined;
  const [, minimum, maximum] = match.map(Number);
  return 18 <= minimum && minimum <= maximum && maximum <= 120 ? [minimum, maximum] : undefined;
}

export function MatchPreferences({ values = {}, onChange, section, english = false, errors = {}, requireAge = false }) {
  const t = (pt, en) => english ? en : pt;
  const set = (key, value) => onChange({ ...values, [key]: value });
  const select = (key, label, options, empty = t("Prefiro não responder", "Prefer not to answer")) => (
    <label className="nk-questionnaire-field" key={key}>
      <span>{label}</span>
      <select value={values[key] || ""} onChange={(event) => set(key, event.target.value)}>
        <option value="">{empty}</option>
        {options.map(([value, pt, en]) => <option key={value} value={value}>{t(pt, en)}</option>)}
      </select>
    </label>
  );

  if (section === "details") return (
    <details className="nk-preferences-optional">
      <summary>{t("Mais sobre si · opcional", "More about you · optional")}</summary>
      <div className="nk-questionnaire-grid">
        <label className="nk-questionnaire-field">
          <span>{t("Altura", "Height")}</span>
          <select value={values.height ?? ""} onChange={(event) => set("height", event.target.value ? Number(event.target.value) : null)}>
            <option value="">{t("Prefiro não responder", "Prefer not to answer")}</option>
            {Array.from({ length: 151 }, (_, index) => index + 100).map((height) => <option key={height} value={height}>{height} cm</option>)}
          </select>
        </label>
        {select("smoking", t("Fuma?", "Do you smoke?"), habits.smoking)}
        {select("drinking", t("Consome bebidas alcoólicas?", "Do you drink alcohol?"), habits.drinking)}
        {select("education", t("Escolaridade", "Education"), habits.education)}
        {select("occupation", t("Ocupação", "Occupation"), habits.occupation)}
      </div>
      <label className="nk-preferences-check">
        <input type="checkbox" checked={!!values.show_details} onChange={(event) => set("show_details", event.target.checked)} />
        {t("Mostrar estes dados a outros membros no meu perfil", "Show these details to other members on my profile")}
      </label>
    </details>
  );

  const ages = values.ages;
  const ageMode = Array.isArray(ages) ? "range" : ages === null ? "any" : "";
  const validRange = ages?.[0] && ages?.[1] && ages[0] <= ages[1];
  return (
    <>
      <div className="nk-preferences-age">
        <label className="nk-questionnaire-field">
          <span>{t("Que idades prefere nas pessoas que gostaria de conhecer?", "What age range would you prefer?")}</span>
          <select required={requireAge} value={ageMode} onChange={(event) => {
            const mode = event.target.value;
            onChange({ ...values, ages: mode === "range" ? [0, 0] : mode === "any" ? null : undefined, show_ages: mode === "range" && !!values.show_ages });
          }}>
            <option value="">{t("Selecione uma opção", "Select an option")}</option>
            <option value="range">{t("Escolher idades", "Choose ages")}</option>
            <option value="any">{t("Sem preferência de idade", "No age preference")}</option>
          </select>
        </label>
        {ageMode === "range" && <>
          <div className="nk-preferences-age-grid">
            {[t("Idade mínima", "Minimum age"), t("Idade máxima", "Maximum age")].map((label, index) => (
              <label className="nk-questionnaire-field" key={label}>
                <span>{label}</span>
                <select
                  required
                  value={ages[index] || ""}
                  ref={index === 1 ? (input) => input?.setCustomValidity(
                    ages[1] && ages[1] < ages[0]
                      ? t("A idade máxima deve ser igual ou superior à mínima.", "Maximum age must be at least the minimum age.")
                      : "",
                  ) : undefined} onChange={(event) => {
                  const next = [...ages];
                  next[index] = Number(event.target.value);
                  set("ages", next);
                }}>
                  <option value="">{t("Escolher", "Choose")}</option>
                  {Array.from({ length: 103 }, (_, age) => age + 18).map((age) => <option key={age} value={age}>{age}</option>)}
                </select>
              </label>
            ))}
          </div>
          <small aria-live="polite">{validRange ? (english ? `You prefer to meet people aged ${ages[0]} to ${ages[1]}.` : `Prefere conhecer pessoas dos ${ages[0]} aos ${ages[1]} anos.`) : ages[0] > ages[1] && ages[1] > 0 ? t("A idade máxima deve ser igual ou superior à mínima.", "Maximum age must be at least the minimum age.") : ""}</small>
          <label className="nk-preferences-check">
            <input type="checkbox" checked={!!values.show_ages} onChange={(event) => set("show_ages", event.target.checked)} />
            {t("Mostrar a idade procurada a outros membros no meu perfil", "Show my preferred age range to other members on my profile")}
          </label>
        </>}
        {errors.ages && <small role="alert">{errors.ages}</small>}
      </div>
      <div className="nk-questionnaire-grid">
        {select("preferred_smoking", t("Preferência sobre tabaco", "Smoking preference"), [["never", "Prefiro alguém que não fume", "I prefer a non-smoker"]], t("Sem preferência", "No preference"))}
        {select("preferred_drinking", t("Preferência sobre álcool", "Drinking preference"), [["never", "Prefiro alguém que não beba", "I prefer someone who doesn't drink"], ["occasionally", "Aceito que beba ocasionalmente", "Occasional drinking is fine"]], t("Sem preferência", "No preference"))}
      </div>
    </>
  );
}

export function ProfilePreferences({ values = {}, english }) {
  const items = [values.height && `${values.height} cm`];
  for (const [key, options] of Object.entries(habits)) {
    const option = options.find(([value]) => value === values[key]);
    if (!option) continue;
    const profileLabels = {
      smoking: { never: ["Não fuma", "Doesn't smoke"], occasionally: ["Fuma ocasionalmente", "Smokes occasionally"], regularly: ["Fuma", "Smokes"] },
      drinking: { never: ["Não bebe", "Doesn't drink"], occasionally: ["Bebe ocasionalmente", "Drinks occasionally"], regularly: ["Bebe regularmente", "Drinks regularly"] },
    };
    items.push((profileLabels[key]?.[option[0]] || option.slice(1))[english ? 1 : 0]);
  }
  return (
    <>
      {items.some(Boolean) && <ul className="nk-preferences-profile">{items.filter(Boolean).map((item) => <li key={item}>{item}</li>)}</ul>}
      {values.ages && <section className="nk-preferences-profile-ages">
        <strong>{english ? "Who they would like to meet" : "Quem gostaria de conhecer"}</strong>
        <p>{english ? `Prefers people aged ${values.ages[0]} to ${values.ages[1]}.` : `Prefere conhecer pessoas dos ${values.ages[0]} aos ${values.ages[1]} anos.`}</p>
      </section>}
    </>
  );
}
