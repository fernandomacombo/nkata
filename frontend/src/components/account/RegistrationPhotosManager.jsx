import { useCallback, useEffect, useState } from "react";
import { Eye, ImagePlus, RefreshCw, Trash2 } from "lucide-react";
import { API_BASE_URL, request } from "../../services/api.js";
import "../../profile-photos.css";

const statusLabel = { PENDENTE: "A aguardar aprovação", APROVADO: "Aprovada", REJEITADO: "Rejeitada" };

export default function RegistrationPhotosManager({ language = "PT" }) {
  const english = language === "EN";
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await request("/api/minha-conta/fotografias/");
      setItems(result.results || []);
      setError("");
    } catch (e) {
      setError(e.message || "Não foi possível carregar as fotografias.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!loading && /^#fotografia-[0-3]$/.test(window.location.hash)) {
      document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ block: "center" });
    }
  }, [loading]);

  async function upload(slot, file) {
    if (!file) return;
    setBusy(String(slot)); setError(""); setNotice("");
    try {
      const form = new FormData();
      form.append("foto", file);
      form.append("publicar_fotos_perfil", "on");
      const result = await request(`/api/minha-conta/fotografias/${slot}/`, { method: "POST", body: form });
      setItems(result.results || []);
      setNotice(english ? "New photo submitted for approval." : "Nova fotografia enviada para aprovação.");
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  }

  async function setVisibility(item) {
    setBusy(String(item.slot)); setError(""); setNotice("");
    try {
      const result = await request(`/api/minha-conta/fotografias/${item.slot}/`, {
        method: "PATCH", body: { visible: true },
      });
      setItems(result.results || []);
      setNotice(english ? "Photo added to your profile." : "Fotografia adicionada ao seu perfil.");
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  }

  async function remove(item) {
    if (!window.confirm(english ? "Permanently delete this extra photo?" : "Eliminar definitivamente esta fotografia adicional?")) return;
    setBusy(String(item.slot)); setError(""); setNotice("");
    try {
      const result = await request(`/api/minha-conta/fotografias/${item.slot}/`, { method: "DELETE" });
      setItems(result.results || []);
      setNotice("Fotografia eliminada.");
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  }

  return <section className="nk-registration-photos">
    <header className="nk-registration-photos__heading">
      <div><h2>{english ? "Registration photos" : "Fotografias do perfil"}</h2><p>{english ? "Photos added here appear on your profile after approval." : "As fotografias que adicionar aqui serão apresentadas no seu perfil após aprovação."}</p></div>
      <button type="button" onClick={load} disabled={loading} title="Atualizar"><RefreshCw size={17}/></button>
    </header>
    {error && <p role="alert" className="nk-photo__error">{error}</p>}
    {notice && <p role="status" className="nk-photo__success">{notice}</p>}
    {loading && <p>A carregar...</p>}
    <div className="nk-photo__grid">
      {items.map(item => <article id={`fotografia-${item.slot}`} className="nk-photo__card" key={item.slot}>
        <div className="nk-photo__image">
          {item.exists ? <img src={`${API_BASE_URL}${item.media_url}?v=${item.version || 0}`} alt={`Fotografia ${item.slot + 1}`} loading="lazy" /> : <ImagePlus size={32}/>}
        </div>
        <div><strong>Fotografia {item.slot + 1}</strong><small>{item.exists ? (english ? item.review_status : statusLabel[item.review_status] || "A aguardar revisão") : "Sem fotografia"}</small><span>{item.visible ? (english ? "On your profile" : "No seu perfil") : item.exists && item.review_status === "APROVADO" ? (english ? "Not yet on your profile" : "Ainda não publicada") : ""}</span></div>
        {item.review_status === "REJEITADO" && <p role="status">{item.rejection_reason} {english ? "Choose Replace to submit another photo." : "Escolha Substituir para enviar outra fotografia."}</p>}
        <div className="nk-photo__actions">
          <label className="nk-photo__upload"><ImagePlus size={15}/> {item.exists ? (english ? "Replace" : "Substituir") : (english ? "Add" : "Adicionar")}<input type="file" accept="image/jpeg,image/png,image/webp" disabled={Boolean(busy)} onChange={e => {const file=e.target.files?.[0];upload(item.slot,file);e.target.value="";}}/></label>
          {item.exists && item.review_status === "APROVADO" && !item.publication_authorized && <button type="button" onClick={() => setVisibility(item)} disabled={Boolean(busy)}><Eye size={15}/>{english ? "Add to profile" : "Adicionar ao perfil"}</button>}
          {item.exists && <button type="button" onClick={() => remove(item)} disabled={Boolean(busy)}><Trash2 size={15}/> Eliminar</button>}
        </div>
      </article>)}
    </div>
  </section>;
}
