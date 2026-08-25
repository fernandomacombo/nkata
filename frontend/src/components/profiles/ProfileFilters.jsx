import { Search, SlidersHorizontal } from "lucide-react";
import useInterfaceLanguage from "../../hooks/useInterfaceLanguage.js";

export default function ProfileFilters({
  query,
  city,
  objective,
  minAge,
  maxAge,
  showAdvanced,
  onQueryChange,
  onCityChange,
  onObjectiveChange,
  onMinAgeChange,
  onMaxAgeChange,
  onToggleAdvanced,
  onClear,
}) {
  const english = useInterfaceLanguage() === "EN";
  return (
    <section className="nk-filters" aria-label={english ? "Profile filters" : "Filtros de perfis"}>
      <label className="nk-search-field">
        <Search size={18} />
        <input
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={english ? "Name, city or intention" : "Nome, cidade ou intenção"}
        />
      </label>

      <button
        type="button"
        className={`nk-filter-button ${showAdvanced ? "is-active" : ""}`}
        onClick={onToggleAdvanced}
        aria-expanded={showAdvanced}
      >
        <SlidersHorizontal size={17} />
        {english ? "Filters" : "Filtros"}
      </button>

      {showAdvanced && (
        <div className="nk-filters__advanced">
          <label>
            <span>{english ? "City" : "Cidade"}</span>
            <select value={city} onChange={(event) => onCityChange(event.target.value)}>
              <option value="">{english ? "All cities" : "Todas as cidades"}</option>
              <option value="Maputo">Maputo</option>
              <option value="Matola">Matola</option>
              <option value="Beira">Beira</option>
              <option value="Vilankulo">Vilankulo</option>
            </select>
          </label>

          <label>
            <span>{english ? "Looking for" : "O que procura"}</span>
            <select value={objective} onChange={(event) => onObjectiveChange(event.target.value)}>
              <option value="">{english ? "Any intention" : "Qualquer intenção"}</option>
              <option value="Relacionamento sério">{english ? "Serious relationship" : "Relacionamento sério"}</option>
              <option value="Conhecer com intenção">{english ? "Meet with intention" : "Conhecer com intenção"}</option>
              <option value="Casamento no futuro">{english ? "Marriage in the future" : "Casamento no futuro"}</option>
              <option value="Amizade que pode evoluir">{english ? "Friendship that may grow" : "Amizade que pode evoluir"}</option>
            </select>
          </label>

          <label>
            <span>{english ? "Minimum age" : "Idade mínima"}</span>
            <input
              type="number"
              min="18"
              max="99"
              value={minAge}
              onChange={(event) => onMinAgeChange(event.target.value)}
              placeholder="18"
            />
          </label>

          <label>
            <span>{english ? "Maximum age" : "Idade máxima"}</span>
            <input
              type="number"
              min="18"
              max="99"
              value={maxAge}
              onChange={(event) => onMaxAgeChange(event.target.value)}
              placeholder="60"
            />
          </label>

          <button type="button" className="nk-filters__clear" onClick={onClear}>
            {english ? "Clear filters" : "Limpar filtros"}
          </button>
        </div>
      )}
    </section>
  );
}
