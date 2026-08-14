import { Search, SlidersHorizontal } from "lucide-react";

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
  return (
    <section className="nk-filters" aria-label="Filtros de perfis">
      <label className="nk-search-field">
        <Search size={18} />
        <input
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Nome, cidade ou intenção"
        />
      </label>

      <button
        type="button"
        className={`nk-filter-button ${showAdvanced ? "is-active" : ""}`}
        onClick={onToggleAdvanced}
        aria-expanded={showAdvanced}
      >
        <SlidersHorizontal size={17} />
        Filtros
      </button>

      {showAdvanced && (
        <div className="nk-filters__advanced">
          <label>
            <span>Cidade</span>
            <select value={city} onChange={(event) => onCityChange(event.target.value)}>
              <option value="">Todas as cidades</option>
              <option value="Maputo">Maputo</option>
              <option value="Matola">Matola</option>
              <option value="Beira">Beira</option>
              <option value="Vilankulo">Vilankulo</option>
            </select>
          </label>

          <label>
            <span>O que procura</span>
            <select value={objective} onChange={(event) => onObjectiveChange(event.target.value)}>
              <option value="">Qualquer intenção</option>
              <option value="Relacionamento sério">Relacionamento sério</option>
              <option value="Conhecer com intenção">Conhecer com intenção</option>
              <option value="Casamento no futuro">Casamento no futuro</option>
              <option value="Amizade que pode evoluir">Amizade que pode evoluir</option>
            </select>
          </label>

          <label>
            <span>Idade mínima</span>
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
            <span>Idade máxima</span>
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
            Limpar filtros
          </button>
        </div>
      )}
    </section>
  );
}
