import { useEffect, useState } from "react";

let deferredInstallEvent = null;
let installed = (
  window.matchMedia("(display-mode: standalone)").matches
  || Boolean(window.navigator.standalone)
);
const listeners = new Set();

function isIosDevice() {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
}

function currentState() {
  return {
    canInstall: Boolean(deferredInstallEvent),
    installed,
    ios: isIosDevice(),
    secure: window.isSecureContext,
  };
}

function notify() {
  const state = currentState();
  listeners.forEach((listener) => listener(state));
}

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstallEvent = event;
  notify();
});

window.addEventListener("appinstalled", () => {
  deferredInstallEvent = null;
  installed = true;
  notify();
});

export async function requestPwaInstall() {
  if (!deferredInstallEvent) return { outcome: "unavailable" };

  const installEvent = deferredInstallEvent;
  deferredInstallEvent = null;
  notify();

  await installEvent.prompt();
  const choice = await installEvent.userChoice;
  if (choice.outcome === "accepted") installed = true;
  notify();
  return choice;
}

export default function usePwaInstall() {
  const [state, setState] = useState(currentState);

  useEffect(() => {
    const update = (nextState) => setState(nextState);
    listeners.add(update);
    setState(currentState());
    return () => listeners.delete(update);
  }, []);

  return { ...state, install: requestPwaInstall };
}
