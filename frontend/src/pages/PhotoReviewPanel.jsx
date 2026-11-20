import { useCallback, useEffect, useState } from "react";
import { Check, RefreshCw, ShieldCheck, X } from "lucide-react";
import { request, API_BASE_URL } from "../services/api.js";
import "../profile-photos.css";

export default function PhotoReviewPanel() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("PENDENTE");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await request(`/api/painel/fotografias/?status=${filter}`);
      setItems(data.results || []);
    } catch (e) {
      setError(e.message || "Não foi possível abrir a fila de fotografias.");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  async function review(item, action) {
    const key = `${item.profile_id}-${item.slot}`;
    if (!window.confirm(action === "approve" ? "Aprovar esta fotografia para apresentação?" : "Rejeitar esta fotografia?")) return;
    setBusy(key);
    setError("");
    setNotice("");
    try {
      await request(`/api/painel/fotografias/${item.profile_id}/${item.slot}/rever/`, {
        method: "POST", body: { action, version: item.version },
      });
      setNotice(action === "approve" ? "Fotografia aprovada." : "Fotografia rejeitada.");
      await load();
    } catch (e) {
      setError(e.message || "Falha ao guardar a revisão.");
    } finally { setBusy(""); }
  }

  return <section className="nk-photo-review">
    <header className="nk-admin-section-header">
      <div><small>Moderação de fotografias</small><h2><ShieldCheck size={23} /> Fotografias de perfil</h2><p>Reveja fotografias antes de permitir a sua divulgação. Documentos de identidade não aparecem nesta área.</p></div>
      <button type="button" onClick={load} disabled={loading} title="Atualizar lista"><RefreshCw size={18}/></button>
    </header>
    <div className="nk-photo-review__filters">
      <label htmlFor="nk-photo-review-state">Estado</label>
      <select id="nk-photo-review-state" value={filter} onChange={(e) => setFilter(e.target.value)}>
        <option value="PENDENTE">Pendentes</option><option value="APROVADO">Aprovadas</option><option value="REJEITADO">Rejeitadas</option>
      </select>
    </div>
    {error && <p role="alert" className="nk-photo__error">{error}</p>}
    {notice && <p role="status" className="nk-photo__success">{notice}</p>}
    {loading && <p>A carregar fotografias...</p>}
    {!loading && !items.length && <p>Não existem fotografias neste estado.</p>}
    <div className="nk-photo__grid">
      {items.map((item) => {
        const key = `${item.profile_id}-${item.slot}`;
        return <article className="nk-photo__card" key={key}>
          <img src={`${API_BASE_URL}${item.image_url}`} alt={`Fotografia para revisão de ${item.name}`} loading="lazy"/>
          <div><strong>{item.name}</strong><small>{item.label}</small><span>{item.status === "PENDENTE" ? "Aguarda revisão" : item.status === "APROVADO" ? "Aprovada" : "Rejeitada"}</span></div>
          <div className="nk-photo__actions">
            {item.status !== "APROVADO" && <button type="button" disabled={Boolean(busy)} onClick={() => review(item, "approve")}><Check size={15}/> Aprovar</button>}
            {item.status !== "REJEITADO" && <button type="button" disabled={Boolean(busy)} onClick={() => review(item, "reject")}><X size={15}/> Rejeitar</button>}
          </div>
        </article>;
      })}
    </div>
  </section>;
}
