import { useState } from "react";
import { fetchMemberNkataIdSession } from "../services/api.js";
import NkataIdHandoff from "../components/identity/NkataIdHandoff.jsx";

export default function ChatIdentityPage({ onBack, onRefresh }) {
  const [verification, setVerification] = useState(null);

  const [error, setError] = useState("");

  const refresh = async () => {
    setError("");
    try {
      setVerification(await fetchMemberNkataIdSession());
      await onRefresh();
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return (
    <main className="nk-shell nk-access-workspace">
      <button type="button" className="nk-button" onClick={onBack}>Voltar a explorar</button>
      <h1>Verificação para usar o chat</h1>
      <p>A sua conta já está activa. Verifique a sua identidade para abrir conversas no NKATA.</p>
      <NkataIdHandoff member value={verification} onChange={setVerification} />
      {error && <p role="alert">{error}</p>}
      {verification?.can_submit && (
        <button type="button" className="nk-button" onClick={refresh}>
          Actualizar estado da verificação
        </button>
      )}
    </main>
  );
}
