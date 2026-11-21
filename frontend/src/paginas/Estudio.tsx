import React, { FormEvent, lazy, Suspense, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, EVOLUCIONES, fecha, fechaLocal, HUESOS, OPINIONES, pct, useImagen } from "../api";
import { Cargando, Encabezado, Enlace, EscaneoCNN, Icono, Mensaje, useDatos, Ventana } from "../componentes";

const Visor3D = lazy(() => import("../Visor3D"));

const CARAS = ["frente", "lado derecho de la imagen", "atrás", "lado izquierdo de la imagen"];
const VISTAS: [string, string][] = [["cajas", "Zona detectada"], ["calor", "Mapa de calor"], ["radiografia", "Radiografía"]];

function Barra({ nombre, valor, umbral, color }: { nombre: string; valor: number; umbral?: number | null; color: string }) {
  return (
    <div>
      <div className="flex items-baseline justify-between text-sm"><span className="text-suave">{nombre}</span><span className="text-2xl font-semibold tracking-tight text-fuerte">{pct(valor, 1)}</span></div>
      <div className="relative mt-2 h-2 rounded-full bg-superficie" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(valor * 100)} aria-label={nombre}>
        <div className={`h-full rounded-full ${color}`} style={{ width: `${valor * 100}%` }} />
        {umbral != null && <div className="absolute -top-1 h-4.5 w-0.5 bg-noche" style={{ left: `${umbral * 100}%` }} title={`Umbral de alerta ${pct(umbral)}`} />}
      </div>
    </div>
  );
}

const ASPECTOS: Record<string, string> = { litica: "Lítica (destruye hueso)", crecimiento: "Crece hacia afuera del hueso", mixta: "Mixta (destruye hueso y forma masa)" };
const TIPO_DE_ASPECTO: Record<string, string> = { litica: "cavidad", crecimiento: "crecimiento", mixta: "cavidad" };
const PLAZOS: [string, number][] = [["4 semanas", 28], ["8 semanas", 56], ["3 meses", 91], ["6 meses", 182], ["1 año", 365]];
const masDias = (d: number) => fechaLocal(d);

type Caja = [number, number, number, number];
/** Imagen con los recuadros del médico encima. En modo corrección, se dibujan arrastrando. */
function ImagenConZonas({ url, alt, cajas, editando, alCambiar }: { url: string; alt: string; cajas: Caja[]; editando: boolean; alCambiar: (c: Caja[]) => void }) {
  const caja = useRef<HTMLDivElement>(null);
  const [inicio, setInicio] = useState<[number, number] | null>(null);
  const [actual, setActual] = useState<Caja | null>(null);
  const punto = (ev: React.PointerEvent): [number, number] => {
    const r = caja.current!.getBoundingClientRect();
    return [Math.min(Math.max((ev.clientX - r.left) / r.width, 0), 1), Math.min(Math.max((ev.clientY - r.top) / r.height, 0), 1)];
  };
  const dibujadas = actual ? [...cajas, actual] : cajas;
  return (
    <div ref={caja} className={`relative inline-block select-none ${editando ? "cursor-crosshair" : ""}`} style={{ touchAction: editando ? "none" : "auto" }}
      onPointerDown={(ev) => { if (!editando) return; (ev.target as Element).setPointerCapture?.(ev.pointerId); const p = punto(ev); setInicio(p); setActual([p[0], p[1], p[0], p[1]]); }}
      onPointerMove={(ev) => { if (!editando || !inicio) return; const p = punto(ev); setActual([Math.min(inicio[0], p[0]), Math.min(inicio[1], p[1]), Math.max(inicio[0], p[0]), Math.max(inicio[1], p[1])]); }}
      onPointerUp={() => { if (actual && actual[2] - actual[0] > 0.01 && actual[3] - actual[1] > 0.01) alCambiar([...cajas, actual].slice(-5)); setInicio(null); setActual(null); }}>
      <img src={url} alt={alt} draggable={false} className="block max-h-[calc(100vh-15rem)] w-auto max-w-full rounded" />
      <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden="true">
        {dibujadas.map((c, i) => (
          <rect key={i} x={c[0]} y={c[1]} width={c[2] - c[0]} height={c[3] - c[1]} fill="rgba(52,211,153,.12)" stroke="#34d399" strokeWidth={2.5} strokeDasharray="6 4" vectorEffect="non-scaling-stroke" />
        ))}
      </svg>
      {cajas.length > 0 && !editando && <span className="absolute left-2 top-2 rounded bg-emerald-400 px-1.5 py-0.5 text-[11px] font-semibold text-[#0a1a3a]">Zona marcada por el médico</span>}
    </div>
  );
}

export function EstudioDetalle() {
  const { id } = useParams();
  const { datos: e, error, setDatos } = useDatos(`/estudios/${id}`);
  const [vista, setVista] = useState("cajas");
  const [corrigiendo, setCorrigiendo] = useState(false);
  const [cajasMedico, setCajasMedico] = useState<Caja[]>([]);
  const [msgZona, setMsgZona] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [ver, setVer] = useState(0);
  const [f, setF] = useState<any>(null);
  const [estado, setEstado] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [recorte, setRecorte] = useState(false); const [borrar, setBorrar] = useState(false);
  const [editando, setEditando] = useState<boolean | null>(null); const [guardando, setGuardando] = useState(false);
  const ir = useNavigate();
  const listo = e?.estado_analisis === "listo";
  const vistaReal = corrigiendo ? "radiografia" : listo ? vista : "radiografia";
  const url = useImagen(e ? e.id : null, vistaReal, ver);
  useEffect(() => { if (e && !corrigiendo) setCajasMedico(e.cajas_medico ?? []); }, [e, corrigiendo]);

  const [ver3d, setVer3d] = useState(false);
  const [zona, setZona] = useState<{ posicion: number; extension: number; angulo?: number; tipo?: string | null } | null>(null);
  const [msg3d, setMsg3d] = useState("");
  const capturar3d = useRef<(() => string) | null>(null);
  const [generando, setGenerando] = useState(false);
  const [reanalizando, setReanalizando] = useState(false);
  useEffect(() => { if (e && !zona) setZona(e.zona_3d ?? { posicion: 0.5, extension: 0.15 }); }, [e, zona]);
  useEffect(() => {
    if (e && !f) setF({ hueso: e.hueso ?? Object.keys(e.hueso_sugerido ?? {})[0] ?? "", lado: e.lado ?? "", opinion: e.opinion ?? "", proximo_control: e.proximo_control ?? "",
      evolucion: e.evolucion ?? "", tratamiento: e.tratamiento ?? "", comentario: e.comentario ?? "", mensaje_paciente: e.mensaje_paciente ?? "" });
  }, [e, f]);

  useEffect(() => { if (e && editando === null) setEditando(!e.opinion); }, [e, editando]);
  if (error) return <Mensaje>{error}</Mensaje>;
  if (!e || !f || editando === null) return <Cargando />;
  const actualizar = (d: any) => { setDatos(d); setVer((v) => v + 1); };
  const guardar = async (ev: FormEvent) => {
    ev.preventDefault(); setEstado(null); setGuardando(true);
    try {
      const cuerpo = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : v]));
      setDatos(await api.patch(`/estudios/${id}/valoracion`, { ...cuerpo, publicar: true }));
      setEditando(false); setEstado({ tipo: "ok", texto: "Valoración guardada y publicada para el paciente." });
      setTimeout(() => document.getElementById("t-val")?.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
    } catch (x: any) { setEstado({ tipo: "error", texto: x.message }); }
    finally { setGuardando(false); }
  };
  const alternarVisible = async () => {
    setEstado(null);
    try { setDatos(await api.post(`/estudios/${id}/publicar`, { publicado: !e.publicado })); }
    catch (x: any) { setEstado({ tipo: "error", texto: x.message }); }
  };
  const c = (k: string) => ({ value: f[k], onChange: (x: any) => setF({ ...f, [k]: x.target.value }) });
  const guardarZona = async () => {
    setMsg3d("");
    try { setDatos(await api.patch(`/estudios/${id}/valoracion`, { zona_3d: { ...zona, angulo: zona?.angulo ?? 0, tipo: tipo3d } })); setMsg3d("Ubicación guardada."); }
    catch (x: any) { setMsg3d(x.message); }
  };
  const descargarInforme = async () => {
    setEstado(null); setGenerando(true);
    try {
      const imagen_3d = ver3d && capturar3d.current ? capturar3d.current() : undefined;
      await api.descargar(`/estudios/${id}/informe`, `informe_estudio_${id}.pdf`, { imagen_3d });
    } catch (x: any) { setEstado({ tipo: "error", texto: x.message }); }
    finally { setGenerando(false); }
  };
  const puede3d = !!f.hueso;
  const tono3d = f.opinion === "maligno" ? "maligno" : f.opinion === "benigno" ? "benigno" : "neutro";
  const aspecto = Object.entries(e.aspecto_sugerido ?? {})[0] as [string, number] | undefined;
  const tipo3d = (zona?.tipo || (aspecto ? TIPO_DE_ASPECTO[aspecto[0]] : null) || (f.opinion === "maligno" ? "cavidad" : f.opinion === "benigno" ? "crecimiento" : "mancha")) as any;
  const guardarZonas = async () => {
    setMsgZona(null);
    try { setDatos(await api.patch(`/estudios/${id}/valoracion`, { cajas_medico: cajasMedico })); setCorrigiendo(false); setMsgZona({ tipo: "ok", texto: cajasMedico.length ? "Zona guardada. Este caso se usará para mejorar el modelo." : "Se quitó la zona marcada." }); }
    catch (x: any) { setMsgZona({ tipo: "error", texto: x.message }); }
  };
  const sugerido = Object.entries(e.hueso_sugerido ?? {}).slice(0, 2) as [string, number][];

  return (
    <>
      {reanalizando && <EscaneoCNN mensaje="La CNN está revisando nuevamente la radiografía. El resultado se actualizará al finalizar." />}
      <p className="mb-3 text-sm"><Enlace a={`/pacientes/${e.paciente_id}`} className="inline-flex items-center gap-1 text-azul hover:underline"><Icono n="volver" className="h-4 w-4" />Expediente del paciente</Enlace></p>
      <section className="osh-clinical-banner mb-6" aria-label="Panel del estudio radiológico"><div className="osh-clinical-banner-content"><p className="osh-clinical-kicker"><span className="osh-live-dot"/> ORTHOSYNC · RADIOLOGÍA DIGITAL</p><h1>Evaluación <span>radiológica inteligente</span></h1><p>Estudio del {fecha(e.fecha_estudio)} · {HUESOS[f.hueso] || "Hueso por determinar"}</p><p className="osh-clinical-disclaimer">La interpretación de la IA requiere confirmación del especialista.</p></div><img src="/img/radiology-bg.svg" alt="" className="osh-clinical-banner-art"/></section>
      <Encabezado titulo={`Estudio del ${fecha(e.fecha_estudio)}`} detalle={<span className="flex flex-wrap items-center gap-x-3 gap-y-1"><span>Archivo {e.archivo_original}</span>
        {f.hueso && <span className="chip bg-cielo text-marino">{HUESOS[f.hueso]}{f.lado ? ` ${f.lado}` : ""}</span>}
        {e.opinion ? <span className="chip bg-panel text-fuerte ring-1 ring-linea">{OPINIONES[e.opinion]}</span> : listo && <span className="chip bg-amber-50 text-amber-800">Por valorar</span>}
        {e.publicado && <span className="chip bg-lavanda text-violeta">Visible para el paciente</span>}</span>}>
        <button className="boton" disabled={generando} onClick={descargarInforme} title="Incluye la vista 3D si está abierta">{generando ? "Generando…" : "Descargar informe PDF"}</button>
        <button className="boton-claro" onClick={() => setRecorte(true)}>Ajustar recorte</button>
        {!listo && <button className="boton-claro" disabled={reanalizando} onClick={async () => {
          setReanalizando(true); setEstado(null);
          try { actualizar(await api.post(`/estudios/${id}/analizar`)); }
          catch (x: any) { setEstado({ tipo: "error", texto: x.message || "No se pudo volver a analizar la radiografía." }); }
          finally { setReanalizando(false); }
        }}>{reanalizando ? "Escaneando…" : "Analizar de nuevo"}</button>}
        <button className="boton-peligro" onClick={() => setBorrar(true)}>Eliminar</button>
      </Encabezado>

      <div className="osh-study-layout grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <section className="osh-study-imaging negatoscopio xl:sticky xl:top-20" aria-label="Imágenes del estudio">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-4 py-3"><span className="inline-flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.1em] text-celeste"><Icono n="estudios" className="h-4 w-4"/> Visor radiológico</span>
            {listo ? (
              <div role="tablist" aria-label="Vista de la imagen" className="inline-flex rounded-lg bg-white/5 p-1 ring-1 ring-white/10">
                {VISTAS.map(([k, n]) => (
                  <button key={k} role="tab" aria-selected={vista === k} onClick={() => setVista(k)}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${vista === k ? "bg-[#fff] text-[#0a1a3a]" : "text-sky-100/80 hover:text-white"}`}>{n}</button>
                ))}
              </div>
            ) : <p className="text-sm text-sky-100/80">Radiografía</p>}
            {!corrigiendo ? (
              <button className="rounded-lg px-3 py-1.5 text-sm font-medium text-sky-100 ring-1 ring-white/20 hover:bg-white/10" onClick={() => { setMsgZona(null); setCorrigiendo(true); }}>
                {(e.cajas_medico ?? []).length ? "Editar zona del médico" : "Corregir la zona"}</button>
            ) : (
              <div className="flex flex-wrap gap-2">
                <button className="rounded-lg px-3 py-1.5 text-sm font-medium text-sky-100 ring-1 ring-white/20 hover:bg-white/10 disabled:opacity-40" disabled={!cajasMedico.length} onClick={() => setCajasMedico(cajasMedico.slice(0, -1))}>Deshacer</button>
                <button className="rounded-lg px-3 py-1.5 text-sm font-medium text-sky-100 ring-1 ring-white/20 hover:bg-white/10" onClick={() => setCorrigiendo(false)}>Cancelar</button>
                <button className="rounded-lg bg-emerald-400 px-3 py-1.5 text-sm font-semibold text-[#0a1a3a] hover:bg-emerald-300" onClick={guardarZonas}>Guardar zona</button>
              </div>
            )}
          </div>
          {corrigiendo && <p className="border-b border-white/10 bg-emerald-400/10 px-4 py-2 text-[13px] text-emerald-100">Arrastra sobre la radiografía para encerrar la lesión. Puedes marcar hasta 5 zonas. Si la placa es normal, guarda sin marcar nada.</p>}
          {msgZona && <p className={`border-b border-white/10 px-4 py-2 text-[13px] ${msgZona.tipo === "ok" ? "text-emerald-200" : "text-red-200"}`}>{msgZona.texto}</p>}
          <div className="flex min-h-80 items-center justify-center p-4">
            {url ? (vistaReal === "calor" ? <img src={url} alt="Radiografía del estudio, vista: mapa de calor" className="max-h-[calc(100vh-15rem)] w-auto max-w-full rounded" />
              : <ImagenConZonas url={url} alt={`Radiografía del estudio, vista: ${corrigiendo ? "corrección" : VISTAS.find((v) => v[0] === vista)?.[1]}`} cajas={cajasMedico} editando={corrigiendo} alCambiar={setCajasMedico} />)
              : <p className="py-16 text-sm text-sky-200/60">Cargando imagen…</p>}
          </div>
          {!corrigiendo && listo && vista === "calor" && <p className="border-t border-white/10 px-4 py-3 text-xs text-sky-100/75">El mapa de calor es orientativo: muestra la región que más influyó en la clasificación, no delimita la lesión.</p>}
          {!corrigiendo && listo && vista === "cajas" && <p className="border-t border-white/10 px-4 py-3 text-xs text-sky-100/75">{!e.cajas?.length ? "El detector no marcó ninguna zona en esta imagen." : e.cajas.some((c: number[]) => c[4] === 0) ? "El detector no marcó ninguna zona; el recuadro ámbar es una ubicación aproximada tomada del mapa de calor." : `${e.cajas.length} zona(s) marcada(s) por el detector, con su confianza.`}</p>}
        </section>

        <div className="space-y-6">
          <section className="tarjeta" aria-labelledby="t-res">
            <h2 id="t-res" className="subtitulo">Resultado del sistema</h2>
            {!listo ? (
              <div className="mt-3"><Mensaje tipo="alerta">{e.estado_analisis === "sin_modelos" ? "Los modelos aún no están instalados en el servidor. La radiografía quedó guardada; usa «Analizar de nuevo» cuando estén." : "No se pudo analizar esta imagen."}</Mensaje></div>
            ) : (
              <div className="mt-3 space-y-4">
                <p className={`rounded-lg border-l-4 px-3 py-2 text-sm font-medium ${e.sospechoso ? "border-red-500 bg-red-50 text-red-900" : "border-emerald-500 bg-emerald-50 text-emerald-900"}`}>{e.conclusion_sistema}</p>
                <Barra nombre="Confianza de lesión tumoral" valor={e.p_tumor} color={e.sospechoso ? "bg-red-500" : "bg-emerald-500"} />
                {e.p_maligno != null && <Barra nombre="Confianza de malignidad" valor={e.p_maligno} color="bg-amber-500" />}
                {sugerido.length > 0 && <p className="text-sm text-suave">Hueso sugerido: {sugerido.map(([h, p]) => `${HUESOS[h] ?? h} (${pct(p)})`).join(", ")}</p>}
                {aspecto && <p className="text-sm text-suave">Aspecto sugerido: <span className="font-medium text-tinta">{ASPECTOS[aspecto[0]] ?? aspecto[0]}</span> ({pct(aspecto[1])})</p>}
                <p className="text-xs leading-relaxed text-suave">Los porcentajes expresan la confianza del modelo, no una probabilidad clínica.</p>
              </div>
            )}
          </section>

          {!editando ? (
            <section className="tarjeta" aria-labelledby="t-val">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 id="t-val" className="subtitulo">Valoración del médico</h2>
                  <p className="mt-0.5 text-[13px] text-suave">{e.valorado_en ? `Registrada el ${fecha(e.valorado_en)}` : ""}</p>
                </div>
                <button className="boton-claro px-3 py-1.5" onClick={() => { setEstado(null); setEditando(true); }}>Editar</button>
              </div>
              {estado && <div className="mt-3"><Mensaje tipo={estado.tipo}>{estado.texto}</Mensaje></div>}
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex flex-wrap gap-2">
                  <span className={`chip ${e.opinion === "maligno" ? "bg-red-50 text-red-700" : e.opinion === "benigno" ? "bg-amber-50 text-amber-800" : e.opinion === "normal" ? "bg-emerald-50 text-emerald-700" : "bg-cielo text-marino"}`}>{OPINIONES[e.opinion] ?? "Sin opinión"}</span>
                  {e.evolucion && <span className="chip bg-cielo text-marino">{EVOLUCIONES[e.evolucion]}</span>}
                  {e.hueso && <span className="chip bg-cielo text-marino">{HUESOS[e.hueso]}{e.lado ? ` ${e.lado}` : ""}</span>}
                </div>
                {e.tratamiento && <div><dt className="text-[13px] text-suave">Tratamiento</dt><dd className="mt-0.5">{e.tratamiento}</dd></div>}
                {e.proximo_control && <div><dt className="text-[13px] text-suave">Próximo control</dt><dd className="mt-0.5 font-medium">{fecha(e.proximo_control)}</dd></div>}
                {e.mensaje_paciente && <div><dt className="text-[13px] text-suave">Mensaje para el paciente</dt><dd className="mt-0.5">{e.mensaje_paciente}</dd></div>}
                {e.comentario && <div><dt className="text-[13px] text-suave">Notas clínicas (privadas)</dt><dd className="mt-0.5">{e.comentario}</dd></div>}
              </dl>
              <div className={`mt-4 flex flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2 text-[13px] ${e.publicado ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}>
                <span>{e.publicado ? "El paciente ya puede verlo en su portal, sin porcentajes." : "Oculto: el paciente no ve este estudio."}</span>
                <button className="font-semibold underline-offset-2 hover:underline" onClick={alternarVisible}>{e.publicado ? "Ocultar al paciente" : "Volver a mostrar"}</button>
              </div>
            </section>
          ) : (
          <form onSubmit={guardar} className="tarjeta space-y-4" aria-labelledby="t-val">
            <h2 id="t-val" className="subtitulo">Valoración del médico</h2>
            {estado && <Mensaje tipo={estado.tipo}>{estado.texto}</Mensaje>}
            <div className="grid grid-cols-2 gap-3">
              <div><label className="etiqueta" htmlFor="vh">Hueso</label>
                <select id="vh" className="campo" {...c("hueso")}><option value="">Sin indicar</option>{Object.entries(HUESOS).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className="etiqueta" htmlFor="vl">Lado</label>
                <select id="vl" className="campo" {...c("lado")}><option value="">Sin indicar</option><option value="izquierdo">Izquierdo</option><option value="derecho">Derecho</option></select></div>
              <div><label className="etiqueta" htmlFor="vo">Su opinión</label>
                <select id="vo" required className="campo" {...c("opinion")}><option value="">Elige una opción</option>{Object.entries(OPINIONES).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
              <div><label className="etiqueta" htmlFor="ve">Evolución</label>
                <select id="ve" className="campo" {...c("evolucion")}><option value="">Sin indicar</option>{Object.entries(EVOLUCIONES).map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select></div>
            </div>
            <div><label className="etiqueta" htmlFor="vt">Tratamiento indicado</label><textarea id="vt" rows={2} className="campo" {...c("tratamiento")} /></div>
            <fieldset>
              <legend className="etiqueta">Próximo control</legend>
              <div className="flex flex-wrap gap-1.5">
                {PLAZOS.map(([n, d]) => (
                  <button key={n} type="button" onClick={() => setF({ ...f, proximo_control: masDias(d) })}
                    className={`rounded-full border px-2.5 py-1 text-xs font-medium transition ${f.proximo_control === masDias(d) ? "border-azul bg-azul text-white" : "border-linea text-suave hover:border-azul/50"}`}>{n}</button>
                ))}
                <button type="button" onClick={() => setF({ ...f, proximo_control: "" })} className={`rounded-full border px-2.5 py-1 text-xs font-medium ${!f.proximo_control ? "border-azul bg-azul text-white" : "border-linea text-suave"}`}>Sin control</button>
              </div>
              <input type="date" aria-label="Fecha del próximo control" className="campo mt-2" min={e.fecha_estudio} value={f.proximo_control} onChange={(x) => setF({ ...f, proximo_control: x.target.value })} />
            </fieldset>
            <div><label className="etiqueta" htmlFor="vm">Mensaje para el paciente</label><textarea id="vm" rows={3} className="campo" placeholder="Explicación en lenguaje sencillo" {...c("mensaje_paciente")} /></div>
            <div><label className="etiqueta" htmlFor="vc">Notas clínicas (no las ve el paciente)</label><textarea id="vc" rows={2} className="campo" {...c("comentario")} /></div>
            <div className="flex flex-wrap gap-2">
              <button className="boton flex-1" disabled={guardando}>{guardando ? "Guardando…" : "Guardar y publicar al paciente"}</button>
              {e.opinion && <button type="button" className="boton-claro" onClick={() => { setEditando(false); setEstado(null); }}>Cancelar</button>}
            </div>
            <p className="text-xs text-suave">Al guardar, el paciente verá en su portal tu mensaje, el tratamiento y la radiografía, sin porcentajes. Las notas clínicas quedan privadas.</p>
          </form>
          )}
        </div>
      </div>

      <section className="tarjeta mt-6" aria-labelledby="t-3d">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="t-3d" className="subtitulo">Modelo 3D de la zona afectada</h2>
            <p className="mt-1 text-sm text-suave">Ilustración del hueso para explicar el hallazgo al paciente. No es una reconstrucción del hueso real.</p>
          </div>
          {!ver3d && <button className="boton" disabled={!puede3d} onClick={() => setVer3d(true)}>Generar 3D</button>}
        </div>
        {!f.hueso && <p className="mt-3 text-sm text-amber-800">Elige el hueso en la valoración para generar el modelo.</p>}
        {f.hueso === "cadera" && <p className="mt-3 text-sm text-amber-800">El modelo 3D no está disponible para la cadera.</p>}
        {ver3d && puede3d && zona && (
          <div className="mt-4 grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
            <div>
              <Suspense fallback={<div className="negatoscopio flex h-[440px] items-center justify-center text-sm text-sky-200/60">Preparando el modelo…</div>}>
                <Visor3D hueso={f.hueso} lado={f.lado || null} zona={zona as any} tono={tono3d} tipo={tipo3d} alListo={(c) => (capturar3d.current = c)} />
              </Suspense>
            </div>
            <div className="space-y-4">
              <div>
                <label className="etiqueta" htmlFor="z-tipo">Aspecto de la lesión</label>
                <select id="z-tipo" className="campo" value={tipo3d} onChange={(x) => setZona({ ...zona, tipo: x.target.value })}>
                  <option value="cavidad">Lítica: destruye hueso (se ve como un hueco)</option>
                  <option value="crecimiento">Crece hacia afuera del hueso (protuberancia)</option>
                  <option value="mancha">Solo marcar la zona con color</option>
                </select>
              </div>
              <div>
                <label className="etiqueta" htmlFor="z-ang">Cara del hueso: {CARAS[Math.round((zona.angulo ?? 0) / 90) % 4]}</label>
                <input id="z-ang" type="range" min={0} max={359} value={Math.round(zona.angulo ?? 0)} className="w-full accent-azul"
                  onChange={(x) => setZona({ ...zona, angulo: +x.target.value })} />
                <div className="flex justify-between text-xs text-suave"><span>Frente</span><span>Derecha</span><span>Atrás</span><span>Izquierda</span><span>Frente</span></div>
              </div>
              <div>
                <label className="etiqueta" htmlFor="z-pos">Ubicación de la zona: {Math.round(zona.posicion * 100)} %</label>
                <input id="z-pos" type="range" min={0} max={100} value={Math.round(zona.posicion * 100)} className="w-full accent-azul"
                  onChange={(x) => setZona({ ...zona, posicion: +x.target.value / 100 })} />
                <div className="flex justify-between text-xs text-suave"><span>Extremo superior</span><span>Extremo inferior</span></div>
              </div>
              <div>
                <label className="etiqueta" htmlFor="z-ext">Extensión: {Math.round(zona.extension * 100)} % del hueso</label>
                <input id="z-ext" type="range" min={2} max={60} value={Math.round(zona.extension * 100)} className="w-full accent-azul"
                  onChange={(x) => setZona({ ...zona, extension: +x.target.value / 100 })} />
              </div>
              <button className="boton-claro w-full" onClick={guardarZona}>Guardar ubicación</button>
              {msg3d && <Mensaje tipo={msg3d.startsWith("Ubicación") ? "ok" : "error"}>{msg3d}</Mensaje>}
              <p className="text-xs leading-relaxed text-suave">La altura inicial sale de la zona marcada en la radiografía (arriba y abajo, como en la placa); la cara y el aspecto los eliges tú. El color sigue tu opinión: rojo si es de aspecto maligno, ámbar si es benigno.</p>
              <p className="text-xs leading-relaxed text-suave">Si el estudio está publicado, el paciente verá esta misma ilustración en su portal. Al descargar el informe PDF con el modelo abierto, se incluye la vista tal como la ves.</p>
            </div>
          </div>
        )}
      </section>

      {recorte && <Recortar estudioId={e.id} alCerrar={() => setRecorte(false)} alListo={(d) => { actualizar(d); setRecorte(false); }} />}
      {borrar && <Ventana titulo="Eliminar estudio" alCerrar={() => setBorrar(false)}>
        <p className="text-sm text-suave">Se eliminarán la radiografía, el análisis y la valoración. Esta acción no se puede deshacer.</p>
        <div className="mt-5 flex justify-end gap-2">
          <button className="boton-claro" onClick={() => setBorrar(false)}>Cancelar</button>
          <button className="boton-peligro" onClick={async () => { await api.borrar(`/estudios/${id}`); ir(`/pacientes/${e.paciente_id}`); }}>Eliminar definitivamente</button>
        </div>
      </Ventana>}
    </>
  );
}

function Recortar({ estudioId, alCerrar, alListo }: { estudioId: string; alCerrar: () => void; alListo: (d: any) => void }) {
  const url = useImagen(estudioId, "sin_recortar");
  const [r, setR] = useState({ x1: 0, y1: 0, x2: 100, y2: 100 });
  const [err, setErr] = useState(""); const [enviando, setEnviando] = useState(false);
  const aplicar = async () => {
    setErr(""); setEnviando(true);
    try { alListo(await api.post(`/estudios/${estudioId}/recortar`, { x1: r.x1 / 100, y1: r.y1 / 100, x2: r.x2 / 100, y2: r.y2 / 100 })); }
    catch (x: any) { setErr(x.message); setEnviando(false); }
  };
  const control = (k: keyof typeof r, nombre: string) => (
    <div><label className="etiqueta" htmlFor={"r" + k}>{nombre}: {r[k]} %</label>
      <input id={"r" + k} type="range" min={0} max={100} value={r[k]} className="w-full accent-azul" onChange={(e) => setR({ ...r, [k]: +e.target.value })} /></div>
  );
  return (
    <Ventana titulo="Ajustar recorte" alCerrar={alCerrar}>
      {enviando && <EscaneoCNN mensaje="Reprocesando la radiografía con el recorte seleccionado y ejecutando la CNN." />}
      <p className="text-sm text-suave">Deja dentro del recuadro solo la radiografía. Al aplicar, el sistema la analiza de nuevo.</p>
      {err && <div className="mt-3"><Mensaje>{err}</Mensaje></div>}
      <div className="relative mx-auto mt-4 w-fit overflow-hidden rounded-lg bg-noche">
        {url ? <img src={url} alt="Imagen original sin recortar" className="max-h-80 w-auto" /> : <p className="p-10 text-sm text-slate-400">Cargando…</p>}
        <div className="pointer-events-none absolute border-2 border-cyan-300 shadow-[0_0_0_9999px_rgba(15,31,61,0.6)]"
          style={{ left: `${r.x1}%`, top: `${r.y1}%`, width: `${Math.max(r.x2 - r.x1, 0)}%`, height: `${Math.max(r.y2 - r.y1, 0)}%` }} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2">
        {control("x1", "Borde izquierdo")}{control("x2", "Borde derecho")}{control("y1", "Borde superior")}{control("y2", "Borde inferior")}
      </div>
      <button className="boton mt-5 w-full" disabled={enviando} onClick={aplicar}>{enviando ? "Analizando…" : "Aplicar y analizar de nuevo"}</button>
    </Ventana>
  );
}
