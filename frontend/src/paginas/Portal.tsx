import { lazy, Suspense, useState } from "react";
import { api, EVOLUCIONES, fecha, HUESOS, useImagen } from "../api";
import { Cargando, Encabezado, Mensaje, useDatos, Vacio, Ventana } from "../componentes";

const Visor3D = lazy(() => import("../Visor3D"));

const tono: Record<string, string> = { mejoria: "bg-emerald-50 text-emerald-700", estable: "bg-cielo text-marino",
  progresion: "bg-amber-50 text-amber-800", primera: "bg-cielo text-marino" };

function EstudioPaciente({ e }: { e: any }) {
  const [verImagen, setVerImagen] = useState(false);
  const [ver3d, setVer3d] = useState(false);
  const [errPdf, setErrPdf] = useState(false);
  const hay3d = e.hay_lesion && e.zona_3d && e.hueso;
  const url = useImagen(verImagen ? e.id : null, "radiografia");
  return (
    <li className="relative pl-8">
      <span className="absolute left-0 top-6 h-3.5 w-3.5 rounded-full border-2 border-white bg-azul ring-2 ring-celeste/40" aria-hidden="true" />
      <article className="tarjeta">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-semibold text-tinta">{fecha(e.fecha_estudio)}{e.hueso ? ` · ${HUESOS[e.hueso]}${e.lado ? " " + e.lado : ""}` : ""}</h3>
          {e.evolucion && <span className={`chip ${tono[e.evolucion]}`}>{EVOLUCIONES[e.evolucion]}</span>}
        </div>
        {e.mensaje ? <p className="mt-3 leading-relaxed text-suave">{e.mensaje}</p> : <p className="mt-3 text-sm text-suave">Tu médico aún no dejó un mensaje para este estudio.</p>}
        {e.tratamiento && <p className="mt-3 text-sm"><span className="font-medium text-marino">Tratamiento indicado: </span>{e.tratamiento}</p>}
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2">
        {hay3d && <button className="text-sm font-medium text-azul hover:underline" aria-expanded={ver3d} onClick={() => setVer3d(!ver3d)}>{ver3d ? "Ocultar modelo 3D" : "Ver la zona en 3D"}</button>}
        <button className="text-sm font-medium text-azul hover:underline" aria-expanded={verImagen} onClick={() => setVerImagen(!verImagen)}>{verImagen ? "Ocultar radiografía" : "Ver mi radiografía"}</button>
        <button className="text-sm font-medium text-azul hover:underline" onClick={() => api.descargar(`/portal/estudios/${e.id}/informe`, `mi_estudio_${e.fecha_estudio}.pdf`).then(() => setErrPdf(false)).catch(() => setErrPdf(true))}>Descargar resumen (PDF)</button>
        {errPdf && <span className="text-sm text-red-700">No se pudo descargar el resumen. Intenta de nuevo.</span>}
        </div>
        {ver3d && hay3d && (
          <div className="mt-3">
            <Suspense fallback={<p className="p-6 text-sm text-suave">Preparando el modelo…</p>}>
              <Visor3D hueso={e.hueso} lado={e.lado} zona={e.zona_3d} tono="paciente" tipo={e.zona_3d.tipo || "mancha"} alto={340} />
            </Suspense>
            <p className="mt-2 text-xs text-suave">Ilustración para entender en qué parte del hueso está la zona que revisa tu médico. No es una imagen de tu hueso.</p>
          </div>
        )}
        {verImagen && <div className="negatoscopio mt-3 flex justify-center p-3">{url ? <img src={url} alt={`Radiografía del ${fecha(e.fecha_estudio)}`} className="max-h-96 w-auto max-w-full" /> : <p className="p-8 text-sm text-slate-400">Cargando…</p>}</div>}
      </article>
    </li>
  );
}

function MisDatos({ solicitud, alCambiar }: { solicitud: any; alCambiar: () => void }) {
  const [pedir, setPedir] = useState(false); const [motivo, setMotivo] = useState("");
  const [msg, setMsg] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const descargar = async () => {
    setMsg(null);
    try { await api.descargar("/portal/mis-datos", "mis_datos.json"); } catch (x: any) { setMsg({ tipo: "error", texto: x.message }); }
  };
  const enviar = async () => {
    try { await api.post("/portal/solicitar-eliminacion", { motivo: motivo || null }); setPedir(false); alCambiar(); }
    catch (x: any) { setMsg({ tipo: "error", texto: x.message }); setPedir(false); }
  };
  const estado: Record<string, string> = { pendiente: "en revisión por la clínica", completada: "completada", rechazada: "no aprobada" };
  return (
    <section className="tarjeta" aria-labelledby="t-datos">
      <h2 id="t-datos" className="subtitulo">Mis datos y privacidad</h2>
      <p className="mt-1 text-sm text-suave">Puedes descargar una copia de tus datos personales o pedir que se eliminen. Más detalles en la <a className="text-marino underline" href="/privacidad.html" target="_blank" rel="noopener">política de privacidad</a>.</p>
      {msg && <div className="mt-3"><Mensaje tipo={msg.tipo}>{msg.texto}</Mensaje></div>}
      {solicitud && (
        <div className="mt-3"><Mensaje tipo={solicitud.estado === "rechazada" ? "alerta" : "info"}>
          Tu solicitud de eliminación del {fecha(solicitud.fecha)} está {estado[solicitud.estado]}.{solicitud.respuesta && solicitud.estado === "rechazada" ? ` Motivo: ${solicitud.respuesta}` : ""}
        </Mensaje></div>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="boton-claro" onClick={descargar}>Descargar mis datos</button>
        {solicitud?.estado !== "pendiente" && <button className="boton-peligro" onClick={() => setPedir(true)}>Solicitar eliminación de mis datos</button>}
      </div>
      {pedir && (
        <Ventana titulo="Solicitar eliminación de datos" alCerrar={() => setPedir(false)}>
          <p className="text-sm text-suave">La clínica revisará tu pedido. Si se aprueba, se borrarán tus datos, tus radiografías y tu acceso al portal. La clínica puede tener la obligación legal de conservar tu historia clínica por un tiempo; si es así, te lo explicará.</p>
          <label className="etiqueta mt-4" htmlFor="mot">Motivo (opcional)</label>
          <textarea id="mot" rows={3} maxLength={1000} className="campo" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          <div className="mt-5 flex justify-end gap-2">
            <button className="boton-claro" onClick={() => setPedir(false)}>Cancelar</button>
            <button className="boton-peligro" onClick={enviar}>Enviar solicitud</button>
          </div>
        </Ventana>
      )}
    </section>
  );
}

export function Portal() {
  const { datos, error, recargar } = useDatos("/portal/resumen");
  if (error) return <Mensaje>{error}</Mensaje>;
  if (!datos) return <Cargando />;
  const estudios = [...datos.estudios].reverse();
  return (
    <>
      <Encabezado titulo={`Hola, ${datos.paciente.nombres}`} detalle={`Expediente ${datos.paciente.codigo}, SpineBolivia`} />
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,760px)_340px]">
        <section aria-labelledby="t-evo" className="min-w-0">
          <h2 id="t-evo" className="subtitulo mb-4">Mi evolución</h2>
          {estudios.length === 0 ? (
            <div className="tarjeta"><Vacio titulo="Aún no hay estudios publicados">Cuando tu médico revise tus radiografías, aparecerán aquí.</Vacio></div>
          ) : (
            <ol className="relative space-y-5 before:absolute before:bottom-2 before:left-[6px] before:top-6 before:w-0.5 before:bg-linea">
              {estudios.map((e: any) => <EstudioPaciente key={e.id} e={e} />)}
            </ol>
          )}
        </section>
        <aside className="space-y-6 xl:sticky xl:top-20">
          {datos.proximo_control && (
            <div className="tarjeta flex items-center gap-4">
              <span className="flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-xl bg-azul text-white">
                <span className="text-lg font-semibold leading-none">{datos.proximo_control.slice(8, 10)}</span>
                <span className="text-[10px]">{new Date(datos.proximo_control + "T12:00:00").toLocaleDateString("es-BO", { month: "short" }).replace(".", "")}</span>
              </span>
              <div><p className="text-[13px] text-suave">Tu próximo control</p><p className="font-semibold text-fuerte">{new Date(datos.proximo_control + "T12:00:00").toLocaleDateString("es-BO", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</p>
                <p className="text-xs text-suave">Confirma la hora con la clínica.</p></div>
            </div>
          )}
          <div className="negatoscopio p-5 text-sm leading-relaxed text-sky-100/85"><p className="mb-2 font-semibold text-white">Antes de leer</p>{datos.aviso}</div>
          <MisDatos solicitud={datos.solicitud_eliminacion} alCambiar={recargar} />
        </aside>
      </div>
    </>
  );
}
