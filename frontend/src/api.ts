// Comunicación con el servidor de Orthosync.
// La sesión vive en una cookie httpOnly que el navegador envía sola: este código (y la consola F12)
// no puede leerla ni modificarla. El rol del usuario lo decide siempre el servidor.
import { useEffect, useState } from "react";

export class ErrorApi extends Error {
  constructor(public estado: number, mensaje: string) { super(mensaje); }
}

async function pedir(ruta: string, opciones: RequestInit = {}) {
  const cab: Record<string, string> = { "X-Orthosync": "1", ...(opciones.headers as any) };
  if (opciones.body && !(opciones.body instanceof FormData)) cab["Content-Type"] = "application/json";
  let r: Response;
  try { r = await fetch("/api" + ruta, { ...opciones, headers: cab, credentials: "same-origin", cache: "no-store" }); }
  catch { throw new ErrorApi(0, "No se pudo conectar con el servidor"); }
  if (r.status === 401 && ruta !== "/auth/login" && ruta !== "/auth/yo") window.dispatchEvent(new Event("sesion-vencida"));
  if (!r.ok) {
    let m = "Ocurrió un error";
    try {
      const d = await r.json();
      m = typeof d.detail === "string" ? d.detail : "Revisa los datos del formulario";
    } catch { /* sin detalle */ }
    throw new ErrorApi(r.status, m);
  }
  return r;
}

export const api = {
  get: (ruta: string) => pedir(ruta).then((r) => r.json()),
  post: (ruta: string, datos?: any) => pedir(ruta, { method: "POST", body: datos ? JSON.stringify(datos) : undefined }).then((r) => r.json()),
  patch: (ruta: string, datos: any) => pedir(ruta, { method: "PATCH", body: JSON.stringify(datos) }).then((r) => r.json()),
  borrar: (ruta: string) => pedir(ruta, { method: "DELETE" }),
  /** Descarga un archivo protegido por la sesión. */
  descargar: async (ruta: string, nombre: string, cuerpo?: any) => {
    const r = await pedir(ruta, cuerpo === undefined ? {} : { method: "POST", body: JSON.stringify(cuerpo) });
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a"); a.href = url; a.download = nombre; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  },
  subir: (ruta: string, formulario: FormData) => pedir(ruta, { method: "POST", body: formulario }).then((r) => r.json()),
};

/** Las imágenes están protegidas: se piden con la sesión y se muestran desde memoria. */
export function useImagen(estudioId: string | null, tipo: string, version = 0) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!estudioId) return;
    let vigente = true, creada: string | null = null;
    setUrl(null);
    pedir(`/estudios/${encodeURIComponent(estudioId)}/imagen/${tipo}`).then((r) => r.blob()).then((b) => {
      if (!vigente) return;
      creada = URL.createObjectURL(b); setUrl(creada);
    }).catch(() => vigente && setUrl(null));
    return () => { vigente = false; if (creada) URL.revokeObjectURL(creada); };
  }, [estudioId, tipo, version]);
  return url;
}

export const fecha = (f?: string | null) => {
  if (!f) return "—";
  if (f.length > 10) {    // fecha con hora: el servidor la guarda en UTC; se muestra en la hora local
    const d = new Date(f.endsWith("Z") ? f : f + "Z");
    if (!isNaN(d.getTime())) return d.toLocaleDateString("es-BO", { day: "2-digit", month: "2-digit", year: "numeric" });
  }
  return f.slice(0, 10).split("-").reverse().join("/");
};
export const pct = (v?: number | null, d = 0) => (v == null ? "—" : (v * 100).toFixed(d).replace(".", ",") + " %");
export const HUESOS: Record<string, string> = { femur: "Fémur", tibia: "Tibia", perone: "Peroné", humero: "Húmero",
  radio: "Radio", cubito: "Cúbito", mano: "Mano", pie: "Pie", cadera: "Cadera" };
export const OPINIONES: Record<string, string> = { normal: "Normal", benigno: "Lesión de aspecto benigno",
  maligno: "Lesión de aspecto maligno", no_concluyente: "No concluyente" };
export const EVOLUCIONES: Record<string, string> = { primera: "Primer estudio", mejoria: "Mejoría", estable: "Estable",
  progresion: "Progresión" };
export const ROLES: Record<string, string> = { administrador: "Administrador", traumatologo: "Traumatólogo",
  recepcion: "Recepción", paciente: "Paciente" };
export const edad = (nac?: string | null) => {
  if (!nac) return null;
  const n = new Date(nac + "T00:00:00"), h = new Date();
  return h.getFullYear() - n.getFullYear() - (h < new Date(h.getFullYear(), n.getMonth(), n.getDate()) ? 1 : 0);
};

/** Fecha local (no UTC) en formato AAAA-MM-DD, sumando días si se pide. */
export const fechaLocal = (masDias = 0) => {
  const d = new Date(); d.setDate(d.getDate() + masDias);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
