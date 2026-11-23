import { createContext, useContext, useEffect, useState } from "react";
import { request } from "../../services/api.js";

const PresenceContext = createContext({});

export function PresenceProvider({ children, member, identity, page }) {
  const [snapshot, setSnapshot] = useState({});
  useEffect(() => {
    const controller = new AbortController();
    let busy = false;
    setSnapshot({});
    async function refresh() {
      if (busy || document.hidden) return;
      const ids = [...new Set(Array.from(document.querySelectorAll("[data-presence-id]"),
        node => Number(node.dataset.presenceId)).filter(id => Number.isSafeInteger(id) && id > 0))];
      if (!member && !ids.length) return;
      busy = true;
      try {
        const next = {};
        for (let index = 0; index < Math.max(1, ids.length); index += 100) {
          const response = await request("/api/presenca/", { method: "POST",
            body: { perfis: ids.slice(index, index + 100) }, signal: controller.signal });
          Object.assign(next, response.perfis);
        }
        if (!controller.signal.aborted) setSnapshot(next);
      } catch {
        if (!controller.signal.aborted) setSnapshot({});
      } finally { busy = false; }
    }
    refresh();
    const timer = window.setInterval(refresh, 10000);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      controller.abort();
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [member, identity, page]);
  return <PresenceContext.Provider value={snapshot}>{children}</PresenceContext.Provider>;
}

export default function Presence({ profile, english }) {
  const age = useContext(PresenceContext)[profile?.id];
  if (!profile?.id) return null;
  let label = "";
  const online = typeof age === "number" && age < 35;
  if (online) label = "Online";
  else if (age === null) label = english ? "Last activity unknown" : "Sem registo de atividade";
  else if (typeof age === "number") {
    const unit = age < 3600 ? "minute" : age < 86400 ? "hour" : "day";
    const divisor = { minute: 60, hour: 3600, day: 86400 }[unit];
    const ago = new Intl.RelativeTimeFormat(english ? "en" : "pt", {numeric:"always"})
      .format(-Math.max(1, Math.floor(age / divisor)), unit);
    label = "Offline · " + ago;
  }
  return <span data-presence-id={profile.id} role={label ? "img" : undefined}
    aria-label={label || undefined} title={label || undefined}
    className={online ? "nk-presence is-online" : "nk-presence"} />;
}
