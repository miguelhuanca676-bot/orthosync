// Service worker de Orthosync: permite instalar la app y abrirla más rápido.
// Solo guarda archivos públicos (código, estilos, imágenes de la interfaz). NUNCA guarda respuestas de /api/,
// así que ningún dato de pacientes queda en el dispositivo.
const VERSION = "orthosync-v4-responsive-20261120";
const BASICOS = ["/app", "/manifest.webmanifest", "/img/asset-husky.webp", "/img/asset-dashboard.webp", "/img/asset-login.webp", "/img/icono-192.png"];

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
  // Recursos de marca: consultar la red primero para no mostrar logos antiguos tras actualizar.
  // Fuera de línea, usar únicamente las copias públicas de interfaz ya guardadas.
  if (url.pathname.startsWith("/img/")) {
    e.respondWith(fetch(e.request).then((resp) => {
      if (resp.ok) { const copia = resp.clone(); caches.open(VERSION).then((c) => c.put(e.request, copia)); }
      return resp;
    }).catch(() => caches.match(e.request)));
    return;
  }
  // Los recursos /assets/ tienen huella de contenido y pueden almacenarse sin quedar obsoletos.
  if (url.pathname.startsWith("/assets/") || url.pathname.endsWith(".woff2")) {
    e.respondWith(caches.match(e.request).then((g) => g || fetch(e.request).then((resp) => {
      if (resp.ok) { const copia = resp.clone(); caches.open(VERSION).then((c) => c.put(e.request, copia)); }
      return resp;
    })));
  }
});
