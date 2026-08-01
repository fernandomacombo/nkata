import { MapPin, Search, SlidersHorizontal } from "lucide-react";

export default function ProfileFilters({ query, city, onQueryChange, onCityChange }) {
  return (
    <section className="nk-filters" aria-label="Filtros de perfis">
      <label className="nk-search-field">
        <Search size={18} />
        <input
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Pesquisar por nome, cidade ou intenção"
        />
      </label>

      <label className="nk-select-field">
        <MapPin size={17} />
        <select value={city} onChange={(event) => onCityChange(event.target.value)}>
          <option value="">Todas as cidades</option>
          <option value="Maputo">Maputo</option>
          <option value="Matola">Matola</option>
          <option value="Beira">Beira</option>
          <option value="Vilankulo">Vilankulo</option>
        </select>
      </label>

      <button type="button" className="nk-filter-button">
        <SlidersHorizontal size={17} />
        Mais filtros
      </button>
    </section>
  );
}
