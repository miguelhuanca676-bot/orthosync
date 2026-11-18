// Service worker de Orthosync: permite instalar la app y abrirla más rápido.
// Solo guarda archivos públicos (código, estilos, imágenes de la interfaz). NUNCA guarda respuestas de /api/,
// así que ningún dato de pacientes queda en el dispositivo.
const VERSION = "orthosync-v1";
const BASICOS = ["/app", "/manifest.webmanifest", "/img/logo.svg", "/img/logo-blanco.svg", "/img/icono-192.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(BASICOS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  // páginas: primero la red (siempre la versión nueva); sin conexión, la copia guardada
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).then((r) => {
      if (r.ok && url.pathname === "/app") caches.open(VERSION).then((c) => c.put("/app", r.clone()));
      return r;
    }).catch(() => caches.match(url.pathname === "/" ? "/" : "/app").then((r) => r || caches.match("/app"))));
    return;
  }
  // archivos con huella en el nombre (/assets/...) e imágenes de la interfaz: primero la copia guardada
  if (url.pathname.startsWith("/assets/") || url.pathname.startsWith("/img/") || url.pathname.endsWith(".woff2")) {
    e.respondWith(caches.match(e.request).then((g) => g || fetch(e.request).then((r) => {
      if (r.ok) { const copia = r.clone(); caches.open(VERSION).then((c) => c.put(e.request, copia)); }
      return r;
    })));
  }
});
