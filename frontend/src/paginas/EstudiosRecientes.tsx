import { useEffect, useMemo, useState } from "react";
import { api, fecha, HUESOS, useImagen } from "../api";
import { Cargando, Enlace, Icono, IconoMarca, Mensaje, useDatos } from "../componentes";

type Item = { id: string; paciente: string; codigo: string; fecha_estudio?: string; hueso?: string; estado_analisis?: string; opinion?: string; sospechoso?: boolean; };
function MiniaturaEstudio({ item }: { item: Item }) {
  const url = useImagen(item.id, item.estado_analisis === "listo" ? "cajas" : "radiografia");
  return <span className="osh-studies-preview">{url ? <img src={url} alt="" loading="lazy"/> : <Icono n="estudios" className="h-6 w-6"/>}</span>;
}
export function EstudiosRecientes() {
  const { datos: pacientes, error } = useDatos<any[]>("/pacientes?buscar=");
  const [estudios, setEstudios] = useState<Item[]>([]);
  const [errorEstudios, setErrorEstudios] = useState("");
  const [cargando, setCargando] = useState(true);
  const [consulta, setConsulta] = useState("");
  const [filtro, setFiltro] = useState<"todos" | "listo" | "pendiente">("todos");
  useEffect(() => {
    if (!pacientes) return;
    let vigente = true;
    const opciones = pacientes.filter(p => (Number(p.n_estudios)||0) > 0)
      .sort((a,b)=>String(b.ultimo_estudio||"").localeCompare(String(a.ultimo_estudio||""))).slice(0, 12);
    setCargando(true); setErrorEstudios("");
    Promise.allSettled(opciones.map(async p => {
      const res = await api.get(`/pacientes/${p.id}/estudios`);
      return (Array.isArray(res) ? res : []).slice(0, 4).map((e: any) => ({
        id: e.id, paciente: `${p.nombres} ${p.apellidos}`, codigo: p.codigo,
        fecha_estudio: e.fecha_estudio, hueso: e.hueso, estado_analisis: e.estado_analisis,
        opinion: e.opinion, sospechoso: e.sospechoso
      } satisfies Item));
    })).then(result => {
      if (!vigente) return;
      const errores = result.filter(x=>x.status==="rejected").length;
      const visibles = result.flatMap(x=>x.status==="fulfilled" ? x.value : [])
        .sort((a,b)=>String(b.fecha_estudio||"").localeCompare(String(a.fecha_estudio||""))).slice(0, 20);
      setEstudios(visibles);
      if (errores) setErrorEstudios("No se pudieron consultar todos los expedientes; se muestran únicamente los estudios disponibles.");
    }).finally(()=>{ if(vigente) setCargando(false); });
    return ()=>{ vigente=false; };
  },[pacientes]);
  const filtrados = useMemo(()=>estudios.filter(e=>{
    if(filtro==="listo" && e.estado_analisis!=="listo") return false;
    if(filtro==="pendiente" && e.estado_analisis==="listo") return false;
    const texto=`${e.codigo} ${e.paciente} ${HUESOS[e.hueso||""]||""}`.toLocaleLowerCase("es");
    return texto.includes(consulta.toLocaleLowerCase("es"));
  }),[estudios,consulta,filtro]);
  return <div className="osh-studies-page space-y-5">
    <section className="osh-clinical-banner"><div className="osh-clinical-banner-content">
      <p className="osh-clinical-kicker"><span className="osh-live-dot"/> ESTUDIOS RADIOLÓGICOS</p>
      <div className="flex items-center gap-4"><img src="/img/asset-radiografias.webp" alt="" className="osh-banner-module-icon" onError={(ev)=>{ev.currentTarget.onerror=null;ev.currentTarget.src="/img/orthosync-radiografias.svg";}}/><h1>Explorador de <span>estudios clínicos</span></h1></div>
      <p>Revisa radiografías, análisis asistidos y valoraciones médicas de tus expedientes autorizados.</p>
      <p className="osh-clinical-disclaimer">Listado rápido de los estudios más recientes, hasta 12 expedientes y 20 estudios.</p>
    </div><img src="/img/radiology-bg.svg" alt="" className="osh-clinical-banner-art"/></section>
    {error && <Mensaje>{error}</Mensaje>}
    {errorEstudios && <Mensaje tipo="alerta">{errorEstudios}</Mensaje>}
    <section className="osh-console-card">
      <div className="osh-console-cardhead"><div><span className="osh-console-eyebrow">EXPLORADOR AUTORIZADO</span><h2><IconoMarca n="estudios"/> Últimos estudios</h2></div>
        <Enlace a="/pacientes" className="osh-console-textlink">Todos los pacientes →</Enlace></div>
      <div className="osh-studies-toolbar">
        <div className="osh-studies-search"><Icono n="buscar" className="h-4 w-4"/><input type="search" aria-label="Buscar por paciente, expediente o hueso" placeholder="Paciente, código o hueso..." value={consulta} onChange={(e)=>setConsulta(e.target.value)}/></div>
        <div className="osh-studies-filters" aria-label="Filtrar estudios">
          {([["todos","Todos"],["listo","Analizados"],["pendiente","Pendientes"]] as const).map(([key,label])=>
            <button key={key} type="button" aria-pressed={filtro===key} className={filtro===key?"is-active":""} onClick={()=>setFiltro(key)}>{label}</button>
          )}
        </div>
      </div>
      {cargando?<div className="p-8"><Cargando/></div>:filtrados.length===0?
        <p className="osh-empty-study">No hay estudios que coincidan con estos criterios. Consulta los expedientes para ver otros registros.</p>:
        <ul className="osh-studies-grid">
          {filtrados.map(e=><li key={e.id}><Enlace a={`/estudios/${e.id}`} className="osh-studies-card">
            <MiniaturaEstudio item={e}/>
            <span className="min-w-0 flex-1"><span className="block truncate text-sm font-bold text-white">{HUESOS[e.hueso||""]||"Estudio radiológico"}</span>
              <span className="mt-1 block truncate text-xs text-sky-100/75">{e.paciente}</span>
              <span className="mt-1 block truncate text-[11px] text-sky-100/55">{e.codigo} · {fecha(e.fecha_estudio)}</span>
            </span>
            <span className={`osh-study-status ${e.estado_analisis==="listo"?"is-ready":"is-pending"}`}>{e.estado_analisis==="listo"?(e.opinion?"Valorado":"Analizado"):"Pendiente"}</span>
          </Enlace></li>)}
        </ul>}
    </section>
  </div>;
}
