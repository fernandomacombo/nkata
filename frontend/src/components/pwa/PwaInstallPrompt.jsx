import { useEffect, useState } from "react";
import { Download, Share2, X } from "lucide-react";
import useInterfaceLanguage from "../../hooks/useInterfaceLanguage.js";
import usePwaInstall from "../../hooks/usePwaInstall.js";

const DISMISSED_KEY = "nkata:pwa-install-dismissed";

export default function PwaInstallPrompt() {
  const english = useInterfaceLanguage() === "EN";
  const pwa = usePwaInstall();
  const [showIosHint, setShowIosHint] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (pwa.installed) {
      setVisible(false);
      return undefined;
    }
    if (sessionStorage.getItem(DISMISSED_KEY)) return undefined;

    if (pwa.canInstall) {
      setVisible(true);
      return undefined;
    }

    if (pwa.ios) {
      const timer = window.setTimeout(() => {
        setShowIosHint(true);
        setVisible(true);
      }, 1800);
      return () => window.clearTimeout(timer);
    }

    return undefined;
  }, [pwa.canInstall, pwa.installed, pwa.ios]);

  if (!visible || (!pwa.canInstall && !showIosHint)) return null;

  const dismiss = () => {
    sessionStorage.setItem(DISMISSED_KEY, "1");
    setVisible(false);
  };

  const install = async () => {
    const choice = await pwa.install();
    if (choice.outcome === "accepted") setVisible(false);
  };

  return (
    <aside className="nk-pwa-prompt" aria-live="polite">
      <span className="nk-pwa-prompt__icon">
        {showIosHint && !pwa.canInstall ? <Share2 size={20} /> : <Download size={20} />}
      </span>
      <div>
        <strong>{english ? "Install NKATA" : "Instalar NKATA"}</strong>
        <small>
          {showIosHint && !pwa.canInstall
            ? (english ? "Tap Share and then Add to Home Screen." : "Toque em Partilhar e depois em Adicionar ao ecrã principal.")
            : (english ? "Use NKATA like an app on this device." : "Use o NKATA como uma aplicação neste dispositivo.")}
        </small>
      </div>
      {pwa.canInstall && (
        <button type="button" className="nk-pwa-prompt__install" onClick={install}>
          {english ? "Install" : "Instalar"}
        </button>
      )}
      <button type="button" className="nk-pwa-prompt__close" onClick={dismiss} aria-label={english ? "Close" : "Fechar"}>
        <X size={17} />
      </button>
    </aside>
  );
}
