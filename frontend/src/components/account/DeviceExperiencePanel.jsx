import {
  BellOff,
  BellRing,
  CheckCircle2,
  Download,
  ExternalLink,
  MonitorSmartphone,
  ShieldAlert,
} from "lucide-react";
import usePwaInstall from "../../hooks/usePwaInstall.js";
import usePushNotifications from "../../hooks/usePushNotifications.js";

function installDescription(pwa, english) {
  if (pwa.installed) {
    return english
      ? "NKATA is installed on this device."
      : "O NKATA está instalado neste dispositivo.";
  }
  if (!pwa.secure) {
    return english
      ? "Open NKATA over HTTPS to install it on this device."
      : "Abra o NKATA por HTTPS para instalar neste dispositivo.";
  }
  if (pwa.ios) {
    return english
      ? "In Safari, tap Share and then Add to Home Screen."
      : "No Safari, toque em Partilhar e depois em Adicionar ao ecrã principal.";
  }
  if (pwa.canInstall) {
    return english
      ? "Install the complete app without downloading an installer."
      : "Instale a aplicação completa sem baixar um instalador.";
  }
  return english
    ? "Use your browser menu and choose Install NKATA."
    : "Use o menu do navegador e escolha Instalar NKATA.";
}

function pushDescription(push, english) {
  const messages = {
    enabled: english ? "Alerts are active on this device." : "Os alertas estão ativos neste dispositivo.",
    disabled: english ? "Receive matches, messages and calls outside the app." : "Receba matches, mensagens e chamadas fora da aplicação.",
    denied: english ? "Notifications are blocked in the browser settings." : "As notificações estão bloqueadas nas definições do navegador.",
    unsupported: english ? "This browser or connection does not support secure alerts." : "Este navegador ou ligação não suporta alertas seguros.",
    unconfigured: english ? "The app is ready; the server keys still need to be activated." : "A aplicação está pronta; falta ativar as chaves no servidor.",
    error: push.message || (english ? "Notifications could not be checked." : "Não foi possível verificar as notificações."),
    loading: english ? "Checking this device…" : "A verificar este dispositivo…",
  };
  return messages[push.status] || messages.loading;
}

export default function DeviceExperiencePanel({ language = "PT" }) {
  const english = language === "EN";
  const pwa = usePwaInstall();
  const push = usePushNotifications();
  const pushEnabled = push.status === "enabled";
  const canTogglePush = ["enabled", "disabled"].includes(push.status);

  return (
    <section className="nk-device-experience">
      <header>
        <span><MonitorSmartphone size={20} /></span>
        <div>
          <h2>{english ? "App and device" : "Aplicação e dispositivo"}</h2>
          <p>{english ? "Install NKATA and control alerts on this device." : "Instale o NKATA e controle os alertas neste dispositivo."}</p>
        </div>
      </header>

      <div className="nk-device-experience__grid">
        <article>
          <div className="nk-device-experience__title">
            <span><Download size={18} /></span>
            <div>
              <strong>{english ? "Install NKATA" : "Instalar NKATA"}</strong>
              <small>{installDescription(pwa, english)}</small>
            </div>
          </div>

          <div className={`nk-device-experience__status ${pwa.installed ? "is-active" : ""}`}>
            {pwa.installed ? <CheckCircle2 size={15} /> : <ExternalLink size={15} />}
            {pwa.installed
              ? (english ? "Installed" : "Instalado")
              : pwa.canInstall
                ? (english ? "Ready to install" : "Pronto para instalar")
                : (english ? "Browser installation" : "Instalação pelo navegador")}
          </div>

          {pwa.canInstall && !pwa.installed && (
            <button type="button" onClick={pwa.install}>
              <Download size={16} /> {english ? "Install now" : "Instalar agora"}
            </button>
          )}
        </article>

        <article>
          <div className="nk-device-experience__title">
            <span>{pushEnabled ? <BellRing size={18} /> : <BellOff size={18} />}</span>
            <div>
              <strong>{english ? "Device alerts" : "Alertas do dispositivo"}</strong>
              <small>{pushDescription(push, english)}</small>
            </div>
          </div>

          <div className={`nk-device-experience__status ${pushEnabled ? "is-active" : push.status === "denied" ? "is-warning" : ""}`}>
            {push.status === "denied" ? <ShieldAlert size={15} /> : pushEnabled ? <CheckCircle2 size={15} /> : <BellOff size={15} />}
            {pushEnabled
              ? (english ? "Active" : "Ativos")
              : push.status === "unconfigured"
                ? (english ? "Server setup pending" : "Configuração do servidor pendente")
                : push.status === "denied"
                  ? (english ? "Blocked" : "Bloqueados")
                  : (english ? "Inactive" : "Inativos")}
          </div>

          {canTogglePush && (
            <button
              type="button"
              onClick={pushEnabled ? push.disable : push.enable}
              disabled={push.loading}
            >
              {pushEnabled ? <BellOff size={16} /> : <BellRing size={16} />}
              {push.loading
                ? (english ? "Please wait…" : "Aguarde…")
                : pushEnabled
                  ? (english ? "Disable alerts" : "Desativar alertas")
                  : (english ? "Enable alerts" : "Ativar alertas")}
            </button>
          )}
          {push.status === "error" && (
            <button type="button" onClick={() => push.refresh()} disabled={push.loading}>
              <BellRing size={16} /> {english ? "Check again" : "Verificar novamente"}
            </button>
          )}
        </article>
      </div>
    </section>
  );
}
