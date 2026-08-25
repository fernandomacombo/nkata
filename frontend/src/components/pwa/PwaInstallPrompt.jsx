import { useEffect, useState } from "react";
import { Download, Share2, X } from "lucide-react";
import useInterfaceLanguage from "../../hooks/useInterfaceLanguage.js";

const DISMISSED_KEY = "nkata:pwa-install-dismissed";

function isIos() {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

function isStandalone() {
  return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone;
}

export default function PwaInstallPrompt() {
  const english = useInterfaceLanguage() === "EN";
  const [installEvent, setInstallEvent] = useState(null);
  const [showIosHint, setShowIosHint] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isStandalone() || sessionStorage.getItem(DISMISSED_KEY)) return undefined;

    const handleInstallable = (event) => {
      event.preventDefault();
      setInstallEvent(event);
      setVisible(true);
    };
    const handleInstalled = () => {
      setVisible(false);
      setInstallEvent(null);
    };

    window.addEventListener("beforeinstallprompt", handleInstallable);
    window.addEventListener("appinstalled", handleInstalled);

    if (isIos()) {
      const timer = window.setTimeout(() => {
        setShowIosHint(true);
        setVisible(true);
      }, 1800);
      return () => {
        window.clearTimeout(timer);
        window.removeEventListener("beforeinstallprompt", handleInstallable);
        window.removeEventListener("appinstalled", handleInstalled);
      };
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", handleInstallable);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  if (!visible || (!installEvent && !showIosHint)) return null;

  const dismiss = () => {
    sessionStorage.setItem(DISMISSED_KEY, "1");
    setVisible(false);
  };

  const install = async () => {
    if (!installEvent) return;
    await installEvent.prompt();
    const choice = await installEvent.userChoice;
    if (choice.outcome === "accepted") setVisible(false);
    setInstallEvent(null);
  };

  return (
    <aside className="nk-pwa-prompt" aria-live="polite">
      <span className="nk-pwa-prompt__icon">
        {showIosHint && !installEvent ? <Share2 size={20} /> : <Download size={20} />}
      </span>
      <div>
        <strong>{english ? "Install NKATA" : "Instalar NKATA"}</strong>
        <small>
          {showIosHint && !installEvent
            ? (english ? "Tap Share and then Add to Home Screen." : "Toque em Partilhar e depois em Adicionar ao ecrã principal.")
            : (english ? "Use NKATA like an app on this device." : "Use o NKATA como uma aplicação neste dispositivo.")}
        </small>
      </div>
      {installEvent && (
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
