import { lazy, Suspense, useState } from "react";
import { Cargando, Enlace, Icono } from "../componentes";

const Visor3D = lazy(() => import("../Visor3D"));

const MODELOS = [
  { id: "femur", titulo: "Fémur", grupo: "Miembro inferior" },
  { id: "tibia", titulo: "Tibia", grupo: "Miembro inferior" },
  { id: "perone", titulo: "Peroné", grupo: "Miembro inferior" },
  { id: "cadera", titulo: "Cadera", grupo: "Pelvis" },
  { id: "humero", titulo: "Húmero", grupo: "Miembro superior" },
  { id: "radio", titulo: "Radio", grupo: "Miembro superior" },
  { id: "cubito", titulo: "Cúbito", grupo: "Miembro superior" },
  { id: "mano", titulo: "Mano", grupo: "Mano" },
  { id: "pie", titulo: "Pie", grupo: "Pie" },
];

export function Biblioteca3D() {
  const [hueso, setHueso] = useState("femur");
  const seleccionado = MODELOS.find((m) => m.id === hueso) || MODELOS[0];
  return <div className="osh-anatomy-page space-y-5">
    <section className="osh-clinical-banner">
      <div className="osh-clinical-banner-content">
        <p className="osh-clinical-kicker"><span className="osh-live-dot"/> BIBLIOTECA ANATÓMICA 3D</p>
        <h1>Explorador <span>anatómico interactivo</span></h1>
        <p>Modelos óseos de referencia en alta resolución con rotación, zoom y control de cámara.</p>
        <p className="osh-clinical-disclaimer">No se genera una reconstrucción específica de un paciente a partir de una radiografía 2D.</p>
      </div>
      <img src="/img/estudio-husky-rayos-x.webp" alt="" className="osh-clinical-banner-art osh-radiology-husky-art" onError={(ev) => { ev.currentTarget.onerror = null; ev.currentTarget.src = "/img/asset-dashboard.webp"; }}/>
    </section>
    <div className="osh-anatomy-layout">
      <aside className="osh-anatomy-menu osh-console-card" aria-label="Elegir hueso">
        <div className="osh-console-cardhead"><div><span className="osh-console-eyebrow">NAVEGADOR ANATÓMICO</span><h2><Icono n="modelo3d"/> Modelos disponibles</h2></div></div>
        <div className="osh-anatomy-options">
          {MODELOS.map((m)=><button key={m.id} type="button" className={`osh-anatomy-option ${m.id===hueso?"is-active":""}`} onClick={()=>setHueso(m.id)} aria-pressed={m.id===hueso}>
            <Icono n="modelo3d" className="h-6 w-6"/><span><strong>{m.titulo}</strong><small>{m.grupo}</small></span><span aria-hidden="true">›</span>
          </button>)}
        </div>
      </aside>
      <section className="osh-anatomy-stage osh-console-card" aria-labelledby="osh-anatomy-title">
        <div className="osh-console-cardhead"><div><span className="osh-console-eyebrow">MODELO ANATÓMICO DE REFERENCIA</span><h2 id="osh-anatomy-title"><Icono n="modelo3d"/> {seleccionado.titulo} · Vista 3D</h2></div><span className="osh-console-pill">3D interactivo</span></div>
        <div className="osh-anatomy-viewer">
          <Suspense fallback={<div className="grid h-[520px] place-items-center text-sky-100"><Cargando/></div>}>
            <Visor3D hueso={hueso} zona={null} alto={520}/>
          </Suspense>
        </div>
        <div className="osh-anatomy-bottom">
          <p>Arrastra para girar · pellizca o utiliza la rueda para acercar · usa “Hueso completo” para restablecer el encuadre.</p>
          <Enlace a="/pacientes" className="osh-console-textlink">Ver expedientes <span aria-hidden="true">→</span></Enlace>
        </div>
      </section>
    </div>
    <p className="text-xs leading-relaxed text-suave">Modelos anatómicos procesados a partir de BodyParts3D © DBCLS, CC BY-SA 2.1 JP. Su uso es educativo e ilustrativo; no constituye diagnóstico ni modelo individual de un paciente.</p>
  </div>;
}
