// Cloudflare Pages Function: todo lo que llega a /api/* se reenvía al servidor de Oracle (la API).
// Así el navegador solo habla con un dominio (Cloudflare): las cookies de sesión siguen siendo "del mismo sitio",
// no hace falta CORS y la IP del servidor queda escondida detrás de Cloudflare.
//
// Variables que se configuran en Cloudflare (Settings → Variables and Secrets):
//   ORIGEN_API     https://163-176-34-234.sslip.io      (dirección del servidor, sin barra final)
//   PROXY_SECRETO  la misma clave que ORTHOSYNC_PROXY_SECRETO en el servidor (tipo "Secret")

const QUITAR = ["host", "cf-connecting-ip", "x-forwarded-for", "x-real-ip", "x-proxy-secreto", "x-cliente-ip"];

export async function onRequest({ request, env }) {
  if (!env.ORIGEN_API || !env.PROXY_SECRETO) {
    return Response.json({ detail: "Falta configurar ORIGEN_API y PROXY_SECRETO en Cloudflare" }, { status: 500 });
  }
  const url = new URL(request.url);
  const destino = env.ORIGEN_API.replace(/\/$/, "") + url.pathname + url.search;

  const cabeceras = new Headers(request.headers);
  for (const h of QUITAR) cabeceras.delete(h);
  cabeceras.set("X-Proxy-Secreto", env.PROXY_SECRETO);
  cabeceras.set("X-Cliente-IP", request.headers.get("cf-connecting-ip") || "");
  cabeceras.set("X-Sitio-Original", url.origin);

  const conCuerpo = !["GET", "HEAD"].includes(request.method);
  try {
    const respuesta = await fetch(destino, {
      method: request.method,
      headers: cabeceras,
      body: conCuerpo ? request.body : undefined,   // se reenvía en flujo (no se carga entero en memoria)
      duplex: "half",
      redirect: "manual",
    });
    return new Response(respuesta.body, respuesta);   // copia estado, cabeceras y cookies tal cual
  } catch (e) {
    return Response.json({ detail: "El servidor no responde. Intenta de nuevo en unos minutos." }, { status: 502 });
  }
}
