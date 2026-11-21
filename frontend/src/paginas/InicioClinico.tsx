import { lazy, Suspense, useEffect, useState } from "react";
import { api, fecha, HUESOS } from "../api";
import { Cargando, Enlace, Icono, IconoMarca, Mensaje, useDatos, useSesion } from "../componentes";

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
  const medico = usuario?.rol === "traumatologo";
  const puedeValidar = medico || usuario?.rol === "administrador";
  const inicial = usuario?.nombre?.replace(/^(Dra?\.|Lic\.)\s*/, "").split(" ")[0] || "equipo";
  const indicadores = [
    {label:"Pacientes registrados",valor:pacientes.length,sub:"Expedientes autorizados",icon:"usuarios"},
    {label:"Estudios radiológicos",valor:estudios,sub:"Total registrado",icon:"estudios"},
    {label:"Pendientes de revisión",valor:pendientes,sub:medico ? "Para valoración médica":"En expedientes disponibles",icon:"validacion"},
  ];
  return <div className="osh-console osh-console-v4" aria-label="Dashboard clínico ORTHOSYNC">
    <section className="osh-console-hero" aria-labelledby="osh-hero-title">
      <div className="osh-console-copy">
        <span className="osh-system-status"><span className="osh-live-dot"/> INICIO · ÁREA CLÍNICA</span>
        <h1 id="osh-hero-title">Bienvenido, {inicial}. <span>Tu espacio de radiología.</span></h1>
        <p>Estudios por rayos X, expedientes y herramientas para la detección asistida de tumores en huesos largos.</p>
        <div className="osh-console-actions">
          <Enlace a="/pacientes" className="osh-console-cta"><Icono n="pacientes"/> Consultar expedientes</Enlace>
          {medico && <Enlace a="/estudios" className="osh-console-cta secondary"><Icono n="estudios"/> Ver estudios</Enlace>}
        </div>
      </div>
      <div className="osh-console-illustration" aria-hidden="true">
        <img src="/img/asset-dashboard.webp" alt="" onError={(ev) => { ev.currentTarget.onerror = null; ev.currentTarget.src="/img/radiology-bg.svg"; }}/>
      </div>
    </section>
    {error && <Mensaje>{error}</Mensaje>}
    <section className="osh-console-metrics" aria-label="Resumen de los expedientes autorizados">
      {indicadores.map((k)=><div key={k.label} className="osh-console-metric">
        <span className="osh-console-metric-icon"><IconoMarca n={k.icon} className="osh-img-icon"/></span>
        <div className="min-w-0 flex-1"><p>{k.label}</p><small>{k.sub}</small></div>
        <strong>{datos ? k.valor.toLocaleString("es-BO") : "—"}</strong>
      </div>)}
    </section>
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
              <img src="/img/asset-dashboard.webp" alt="" className="osh-console-model-bg" onError={(ev) => { ev.currentTarget.onerror = null; ev.currentTarget.src = "/img/radiology-bg.svg"; }}/>
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
        <section className="osh-console-card" aria-labelledby="osh-title-studies">
          <div className="osh-console-cardhead">
            <div><span className="osh-console-eyebrow">ACTIVIDAD RECIENTE</span>
              <h2 id="osh-title-studies"><IconoMarca n="estudios"/> Últimos estudios</h2></div>
            <Enlace a={medico ? "/estudios" : "/pacientes"} className="osh-console-textlink">
              {medico ? "Ver todos" : "Ver pacientes"} <span aria-hidden="true">→</span>
            </Enlace>
          </div>
          {!datos ? <div className="p-5"><Cargando/></div> : <EstudiosClinicos pacientes={pacientes} medico={medico}/>}
        </section>
        <section className="osh-console-card osh-console-guidance" aria-label="Flujo de análisis">
          <div className="osh-console-cardhead">
            <div><span className="osh-console-eyebrow">FLUJO DE TRABAJO</span>
              <h2><Icono n="validacion" /> Análisis con criterio clínico</h2></div>
          </div>
          <div className="osh-console-guidance-copy">
            <p>{medico ? "Estudios pendientes de revisión profesional: " + pendientes :
              "Las radiografías y valoraciones se gestionan según los permisos de tu perfil."}</p>
            <p>Los hallazgos de la CNN son orientativos y deben ser revisados por el especialista.</p>
            {puedeValidar && <Enlace a="/validacion" className="osh-console-textlink">Consultar validación CNN <span aria-hidden="true">→</span></Enlace>}
          </div>
        </section>
      </div>
    </div>
  </div>;
}
