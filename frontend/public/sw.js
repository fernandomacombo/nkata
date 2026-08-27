const CACHE_VERSION = "nkata-shell-v4";
const DEVELOPMENT_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);
const APP_SHELL = [
  "/",
  "/manifest.webmanifest",
  "/images/nkata-logo-original.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  // O service worker continua registado no localhost para testar instalação e
  // Push, mas deixa o Vite servir sempre a versão mais recente dos ficheiros.
  if (DEVELOPMENT_HOSTS.has(self.location.hostname)) return;
  if (request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put("/", clone));
          return response;
        })
        .catch(() => caches.match("/"))
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok && ["style", "script", "image", "font"].includes(request.destination)) {
          const clone = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = { body: event.data?.text() || "Tem uma novidade no NKATA." };
  }

  const title = payload.title || "NKATA";
  const options = {
    body: payload.body || "Tem uma novidade no NKATA.",
    icon: payload.icon || "/images/nkata-logo-original.png",
    badge: "/icons/nkata-badge-96.png",
    image: payload.image || undefined,
    tag: payload.tag || "nkata-notification",
    renotify: Boolean(payload.renotify),
    data: { url: payload.url || "/notificacoes/" },
    actions: [{ action: "open", title: "Abrir NKATA" }]
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const destination = new URL(event.notification.data?.url || "/notificacoes/", self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((client) => client.url.startsWith(self.location.origin));
      if (existing) {
        existing.navigate(destination);
        return existing.focus();
      }
      return self.clients.openWindow(destination);
    })
  );
});
