let registrationPromise;

export function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return Promise.resolve(null);
  if (!window.isSecureContext) return Promise.resolve(null);

  if (!registrationPromise) {
    registrationPromise = navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch((error) => {
      console.warn("NKATA service worker indisponível:", error);
      return null;
    });
  }
  return registrationPromise;
}

export async function getReadyServiceWorker() {
  const registration = await registerServiceWorker();
  if (!registration) return null;
  return navigator.serviceWorker.ready;
}

export function urlBase64ToUint8Array(value) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  return Uint8Array.from([...raw].map((character) => character.charCodeAt(0)));
}
