import { lazy, Suspense, useEffect, useState } from "react";
import { api, fecha, HUESOS } from "../api";
import { Cargando, Enlace, Icono, Mensaje, useDatos, useSesion } from "../componentes";

const Visor3D = lazy(() => import("../Visor3D"));
const SIN_PACIENTES: any[] = [];
const OPCIONES = [
  { id: "femur", label: "Fémur", sigla: "FEM" },
  { id: "tibia", label: "Tibia", sigla: "TIB" },
  { id: "humero", label: "Húmero", sigla: "HUM" },
  { id: "cadera", label: "Cadera", sigla: "CAD" },
  { id: "mano", label: "Mano", sigla: "MAN" },
  { id: "pie", label: "Pie", sigla: "PIE" },
] as const;
type EstudioVista = { id: string; paciente?: string; fecha_estudio?: string; hueso?: string; estado_analisis?: string; conclusion_sistema?: string; opinion?: string; p_tumor?: number | null; sospechoso?: boolean; };
function EstudiosClinicos({ pacientes, medico }: { pacientes: any[]; medico: boolean }) {
  const [estudios, setEstudios] = useState<EstudioVista[]>([]);
  const [cargando, setCargando] = useState(false);
  useEffect(() => {
    if (!medico || pacientes.length === 0) { setEstudios([]); return; }
    let vigente = true;
    const ids = [...pacientes].filter((p) => p.n_estudios > 0)
      .sort((a, b) => String(b.ultimo_estudio || "").localeCompare(String(a.ultimo_estudio || "")))
      .slice(0, 4);
    if (!ids.length) { setEstudios([]); return; }
    setCargando(true);
    Promise.allSettled(ids.map(async (p) => {
      const lista = await api.get(`/pacientes/${p.id}/estudios`);
      return (Array.isArray(lista) ? lista : []).slice(0, 3).map((e: any) =>
        ({ ...e, paciente: `${p.nombres} ${p.apellidos}` }));
    })).then((res) => {
      if (!vigente) return;
      const result = res.flatMap((x) => x.status === "fulfilled" ? x.value : []);
      setEstudios(result.sort((a, b) => String(b.fecha_estudio || "").localeCompare(String(a.fecha_estudio || ""))).slice(0, 4));
    }).finally(() => { if (vigente) setCargando(false); });
    return () => { vigente = false; };
  }, [pacientes, medico]);
  if (!medico) return <p className="osh-empty-study">La información clínica de los estudios es exclusiva del traumatólogo. Accede a los expedientes desde Pacientes.</p>;
  if (cargando) return <div className="p-5"><Cargando/></div>;
  if (!estudios.length) return <p className="osh-empty-study">Aún no hay estudios recientes disponibles para esta cuenta.</p>;
  return <ul className="osh-study-list">{estudios.map((e) =>
    <li key={e.id}><Enlace a={`/estudios/${e.id}`} className="osh-study-item">
      <span className="osh-study-icon"><Icono n="estudios" className="h-5 w-5"/></span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13px] font-bold text-white">{HUESOS[e.hueso || ""] || "Estudio radiológico"}</span>
        <span className="mt-1 block truncate text-[11px] text-sky-100/65">{fecha(e.fecha_estudio)} · {e.paciente}</span>
      </span>
      <span className={`osh-study-status ${e.estado_analisis === "listo" ? "is-ready" : "is-pending"}`}>{e.estado_analisis === "listo" ? "Analizado" : "Pendiente"}</span>
      <span aria-hidden="true" className="text-celeste">›</span>
    </Enlace></li>
  )}</ul>;
}
export function InicioClinico() {
  const { usuario } = useSesion();
  const { datos, error } = useDatos<any[]>("/pacientes?buscar=");
  const [hueso, setHueso] = useState("femur");
  
  const [mostrar3d, setMostrar3d] = useState(() => window.matchMedia("(min-width: 1024px)").matches);
  const pacientes = Array.isArray(datos) ? datos : SIN_PACIENTES;
  const estudios = pacientes.reduce((sum, p) => sum + (Number(p.n_estudios) || 0), 0);
  const pendientes = pacientes.reduce((sum, p) => sum + (Number(p.por_valorar) || 0), 0);
  const conEstudios = pacientes.filter((p) => Number(p.n_estudios) > 0).length;
  const medico = usuario?.rol === "traumatologo";
  const inicial = usuario?.nombre?.replace(/^(Dra?\.|Lic\.)\s*/, "").split(" ")[0] || "equipo";
  const indicadores = [
    {label:"Pacientes registrados",valor:pacientes.length,sub:"Expedientes autorizados",icon:"usuarios"},
    {label:"Estudios radiológicos",valor:estudios,sub:"Total registrado",icon:"estudios"},
    {label:"Pendientes de revisión",valor:pendientes,sub:medico ? "Para valoración médica":"En expedientes disponibles",icon:"validacion"},
  ];
  return <div className="osh-console space-y-4" aria-label="Dashboard clínico ORTHOSYNC">
    <section className="osh-console-hero" aria-labelledby="osh-hero-title">
      <div className="osh-console-copy">
        <span className="osh-system-status"><span className="osh-live-dot"/> PLATAFORMA DE RADIOLOGÍA · ORTHOSYNC</span>
        <div className="osh-console-brand"><img src="/img/husky-guardian.svg" alt="" className="osh-console-mascot"/>
          <div><p className="osh-console-wordmark">ORTHO<span>SYNC</span></p>
            <p className="osh-console-tagline">PRECISIÓN · INNOVACIÓN · SALUD</p></div>
        </div>
        <h1 id="osh-hero-title">Bienvenido, {inicial}. <span>Radiología inteligente en un solo lugar.</span></h1>
        <p>IA aplicada al apoyo diagnóstico, expedientes y anatomía 3D. Cada hallazgo requiere revisión profesional.</p>
        <div className="osh-console-actions">
          <Enlace a="/pacientes" className="osh-console-cta"><Icono n="pacientes"/> Explorar pacientes</Enlace>
          <Enlace a="/validacion" className="osh-console-cta secondary"><Icono n="validacion"/> Validación de IA</Enlace>
        </div>
      </div>
      <div className="osh-console-illustration" aria-hidden="true"><img src="/img/radiology-bg.svg" alt=""/></div>
    </section>
    {error && <Mensaje>{error}</Mensaje>}
    <div className="osh-console-upper">
      <div className="osh-console-tools" aria-label="Módulos del sistema">
        {([
          ["/pacientes","Pacientes","usuarios"],
          ["/controles","Controles","controles"],
          ["/validacion","Validación CNN","validacion"],
          ["/cuenta","Mi cuenta","cuenta"],
        ] as [string,string,string][]).filter(([ruta]) => ruta !== "/validacion" || medico).map(([ruta,titulo,icono])=>
        <Enlace key={ruta} a={ruta} className="osh-console-tool"><Icono n={icono} className="h-7 w-7"/><span>{titulo}</span></Enlace>)}
      </div>
      <div className="osh-console-metrics">
        {indicadores.map((k)=><div key={k.label} className="osh-console-metric">
          <span className="osh-console-metric-icon"><Icono n={k.icon} className="h-6 w-6"/></span>
          <div className="min-w-0 flex-1"><p>{k.label}</p><small>{k.sub}</small></div>
          <strong>{datos?k.valor.toLocaleString("es-BO"):"—"}</strong>
        </div>)}
      </div>
    </div>
    <div className="osh-console-panels">
      <section className="osh-console-card osh-console-anatomy" aria-labelledby="osh-title-anatomy">
        <div className="osh-console-cardhead"><div><span className="osh-console-eyebrow">VISUALIZACIÓN MÉDICA</span><h2 id="osh-title-anatomy"><Icono n="modelo3d"/> Visor 3D anatómico</h2></div><span className="osh-console-pill">Modelos de referencia</span></div>
        <div className="osh-console-anatomy-body">
          <div className="osh-console-bonelist" role="group" aria-label="Seleccionar hueso">
            {OPCIONES.map((o)=><button key={o.id} type="button" onClick={()=>setHueso(o.id)} aria-pressed={hueso===o.id} className={`osh-console-bone ${hueso===o.id?"is-active":""}`}>
              <Icono n="modelo3d" className="h-5 w-5"/><span>{o.label}</span><small>{o.sigla}</small></button>)}
          </div>
          <div className="osh-console-model">
            {mostrar3d ? <Suspense fallback={<div className="grid h-[420px] place-items-center text-sm text-sky-100/80">Preparando visor…</div>}>
              <Visor3D key={hueso} hueso={hueso} zona={null} alto={420}/>
            </Suspense> : <div className="osh-console-model-placeholder">
              <img src="/img/radiology-bg.svg" alt="" className="osh-console-model-bg"/>
              <p className="text-[11px] font-bold uppercase tracking-[.18em] text-celeste">Anatomía en 3 dimensiones</p>
              <h3>{OPCIONES.find(o=>o.id===hueso)?.label}</h3>
              <p>Visualiza y gira el hueso mediante el visor interactivo.</p>
              <button type="button" onClick={()=>setMostrar3d(true)} className="osh-console-launch"><Icono n="modelo3d"/> Iniciar visor 3D</button>
            </div>}
          </div>
        </div>
        <div className="osh-console-anatomy-footer">
          <span><span className="osh-live-dot"/> {OPCIONES.find(o=>o.id===hueso)?.label} · Hueso anatómico</span>
          <span>Referencia ilustrativa · No reconstrucción del paciente</span>
        </div>
      </section>
      <div className="osh-console-right">
        <section className="osh-console-card" aria-labelledby="osh-title-studies"><div className="osh-console-cardhead">
          <div><span className="osh-console-eyebrow">EXPEDIENTES AUTORIZADOS</span><h2 id="osh-title-studies"><Icono n="estudios"/> Últimos estudios</h2></div>
          <Enlace a="/pacientes" className="osh-console-textlink">Ver pacientes <span aria-hidden="true">→</span></Enlace></div>
          {!datos?<div className="p-5"><Cargando/></div>:<EstudiosClinicos pacientes={pacientes} medico={medico}/>}
        </section>
        <section className="osh-console-card osh-console-analysis" aria-labelledby="osh-title-ai"><div className="osh-console-cardhead">
          <div><span className="osh-console-eyebrow">SEGUIMIENTO CLÍNICO</span><h2 id="osh-title-ai"><Icono n="validacion"/> Análisis con IA</h2></div>
          <span className="osh-console-pill">Soporte a decisiones</span></div>
          <div className="osh-console-analysis-body">
            <div className="osh-console-gauge"><strong>{datos? conEstudios:"—"}</strong><span>Pacientes con estudios</span></div>
            <div className="min-w-0 flex-1"><p className="text-sm font-bold text-white">{medico ? "Valoración del especialista":"Gestión de expedientes"}</p>
              <p className="mt-2 text-xs leading-6 text-sky-100/65">{medico ? `Hay ${pendientes} estudio(s) por valorar de los expedientes autorizados.` : "El análisis de las radiografías corresponde al personal médico."}</p>
              <Enlace a={medico?"/validacion":"/pacientes"} className="osh-console-analysis-link">{medico?"Ver métricas reales del modelo":"Ir a pacientes"} <span aria-hidden="true">↗</span></Enlace>
            </div>
          </div>
          <p className="osh-console-footnote">No se presentan porcentajes de precisión ni diagnósticos sin obtenerlos de una evaluación real.</p>
        </section>
      </div>
    </div>
  </div>;
}
