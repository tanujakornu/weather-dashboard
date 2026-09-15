// Minimal service worker: makes the app installable and keeps the visual
// shell (CSS/JS/icons) available even on a flaky connection. Weather data
// itself is always fetched fresh -- this never caches API responses or the
// dynamic HTML pages, so you never see stale weather.
const CACHE_NAME = "weather-dashboard-shell-v1";
const SHELL_ASSETS = [
  "/static/css/style.css",
  "/static/js/main.js",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  const isShellAsset = url.origin === self.location.origin && SHELL_ASSETS.includes(url.pathname);

  if (isShellAsset) {
    // Cache-first for the static shell -- instant load, refreshed in the background.
    event.respondWith(
      caches.match(req).then((cached) => {
        const network = fetch(req)
          .then((res) => {
            caches.open(CACHE_NAME).then((cache) => cache.put(req, res.clone()));
            return res;
          })
          .catch(() => cached);
        return cached || network;
      })
    );
  }
  // Everything else (weather pages, API-backed HTML, map tiles) goes to the
  // network untouched, so data is always live.
});
