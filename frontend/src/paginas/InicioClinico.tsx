// Panel clínico: usa exclusivamente los expedientes autorizados para el rol actual.
// Las cifras proceden de /pacientes; no son métricas inventadas ni cambian la CNN.
import { lazy, Suspense } from "react";
import { fecha } from "../api";
import { Cargando, Enlace, Icono, Mensaje, useDatos, useSesion } from "../componentes";

const Visor3D = lazy(() => import("../Visor3D"));

export function InicioClinico() {
  const { usuario } = useSesion();
  const { datos, error } = useDatos<any[]>("/pacientes?buscar=");
  const pacientes = Array.isArray(datos) ? datos : [];
  const cantidadEstudios = pacientes.reduce((n, p) => n + (Number(p.n_estudios) || 0), 0);
  const pendientes = pacientes.reduce((n, p) => n + (Number(p.por_valorar) || 0), 0);
  const conEstudios = pacientes.filter((p) => (Number(p.n_estudios) || 0) > 0).length;
  const recientes = [...pacientes].filter((p) => p.ultimo_estudio).sort((a, b) =>
    String(b.ultimo_estudio).localeCompare(String(a.ultimo_estudio))).slice(0, 5);
  const nombre = usuario?.nombre?.replace(/^(Dra?\.|Lic\.)\s*/, "").split(" ")[0] || "equipo clínico";
  const medico = usuario?.rol === "traumatologo";
  const kpis = [
    { etiqueta: "Pacientes registrados", valor: pacientes.length, icono: "usuarios", nota: "Expedientes accesibles" },
    { etiqueta: "Estudios radiológicos", valor: cantidadEstudios, icono: "pacientes", nota: "En expedientes consultados" },
    { etiqueta: "Estudios por valorar", valor: pendientes, icono: "validacion", nota: medico ? "Pendientes de revisión" : "Registrados en el sistema" },
    { etiqueta: "Pacientes con estudios", valor: conEstudios, icono: "controles", nota: "Con al menos un estudio" },
  ];
  return (
    <div className="osh-dashboard space-y-6">
      <section className="osh-dashboard-hero relative isolate overflow-hidden rounded-[28px] border border-celeste/25 p-6 sm:p-9 lg:p-10">
        <div className="relative z-10 max-w-[720px]">
          <span className="osh-kicker"><span className="osh-live-dot" /> ORTHOSYNC · WORKSPACE CLÍNICO</span>
          <h1 className="mt-5 text-[clamp(1.9rem,3.3vw,3.3rem)] font-extrabold leading-[1.08] tracking-[-.055em] text-white">
            Hola, {nombre}.<br/><span className="text-celeste">Tu centro de radiología inteligente.</span>
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-7 text-sky-100/80 sm:text-base">
            Gestiona expedientes, revisa estudios y explora modelos óseos anatómicos.
            Los resultados de inteligencia artificial requieren siempre valoración médica.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Enlace a="/pacientes" className="osh-primary-link"><Icono n="pacientes" /> Abrir expedientes</Enlace>
            <Enlace a="/controles" className="osh-outline-link"><Icono n="controles" /> Ver controles</Enlace>
          </div>
        </div>
        <div className="osh-hero-emblem" aria-hidden="true">
          <span className="osh-hero-ring" /><img src="/img/logo-blanco.svg" alt="" />
        </div>
        <span aria-hidden="true" className="osh-hero-grid"/>
      </section>

      {error && <Mensaje>{error}</Mensaje>}

      <section aria-label="Indicadores reales de expedientes" className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-4">
        {kpis.map((k) => (
          <div key={k.etiqueta} className="osh-kpi relative overflow-hidden rounded-[20px] p-5">
            <div className="flex items-start justify-between gap-3">
              <span className="osh-kpi-icon"><Icono n={k.icono} className="h-6 w-6"/></span>
              <span className="text-[10px] font-bold uppercase tracking-[.15em] text-celeste/80">Datos del sistema</span>
            </div>
            <p className="mt-5 text-[13px] font-medium text-suave">{k.etiqueta}</p>
            <p className="mt-1 text-[35px] font-extrabold tracking-[-.06em] text-fuerte">{datos ? k.valor.toLocaleString("es-BO") : "—"}</p>
            <p className="mt-2 text-[12px] text-suave">{k.nota}</p>
          </div>
        ))}
      </section>

      <div className="grid items-start gap-5 2xl:grid-cols-[minmax(0,1.3fr)_minmax(330px,.7fr)]">
        <section className="osh-feature-panel overflow-hidden rounded-[24px] border border-celeste/25" aria-labelledby="osh-modelo">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4 sm:px-6">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[.16em] text-celeste">Explorador anatómico</p>
              <h2 id="osh-modelo" className="mt-1 text-lg font-bold text-white">Visor óseo 3D interactivo</h2>
            </div>
            <span className="rounded-full border border-celeste/35 bg-celeste/10 px-3 py-1 text-[11px] font-semibold text-sky-100">Modelo de referencia</span>
          </div>
          <div className="osh-model-viewport px-4 py-5 sm:px-6">
            <Suspense fallback={<div className="grid h-[370px] place-items-center text-sm text-sky-100"><Cargando /></div>}>
              <Visor3D hueso="femur" zona={null} alto={370} />
            </Suspense>
          </div>
          <p className="px-6 pb-5 text-[12px] leading-5 text-sky-100/65">Modelo anatómico ilustrativo. No representa una reconstrucción 3D de ningún paciente ni modifica los análisis de la CNN.</p>
        </section>

        <div className="space-y-5">
          <section className="osh-feature-panel overflow-hidden rounded-[24px] border border-celeste/25" aria-labelledby="osh-recientes">
            <div className="flex items-center justify-between gap-3 border-b border-white/10 px-5 py-4">
              <div><p className="text-[10px] font-bold uppercase tracking-[.15em] text-celeste">Actividad clínica</p><h2 id="osh-recientes" className="mt-1 text-lg font-bold text-white">Expedientes recientes</h2></div>
              <Enlace a="/pacientes" className="text-xs font-semibold text-celeste hover:underline">Ver todos</Enlace>
            </div>
            {!datos ? <div className="p-6 text-sm text-sky-100"><Cargando /></div> :
              recientes.length === 0 ? <p className="p-6 text-sm text-sky-100/75">Todavía no hay estudios registrados.</p> :
              <ul className="divide-y divide-white/10">
                {recientes.map((p) => (
                  <li key={p.id}>
                    <Enlace a={`/pacientes/${p.id}`} className="flex items-center gap-3 px-5 py-3.5 transition hover:bg-celeste/10">
                      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-celeste/25 bg-celeste/10 text-celeste"><Icono n="pacientes"/></span>
                      <span className="min-w-0 flex-1"><span className="block truncate text-[13px] font-semibold text-white">{p.nombres} {p.apellidos}</span>
                        <span className="mt-0.5 block text-[11px] text-sky-100/65">Estudio: {fecha(p.ultimo_estudio)}</span></span>
                      <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${p.por_valorar > 0 ? "bg-amber-400/15 text-amber-200" : "bg-emerald-400/15 text-emerald-200"}`}>{p.por_valorar > 0 ? "Por valorar" : "Al día"}</span>
                    </Enlace>
                  </li>
                ))}
              </ul>}
          </section>
          <section className="osh-feature-panel rounded-[24px] border border-celeste/25 p-5">
            <p className="text-[10px] font-bold uppercase tracking-[.15em] text-celeste">Herramientas</p>
            <h2 className="mt-1 text-lg font-bold text-white">Acceso rápido</h2>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {([["/pacientes", "Expedientes", "pacientes"], ["/controles", "Controles", "controles"], ["/cuenta", "Mi cuenta", "cuenta"], ...(usuario?.rol !== "recepcion" ? [["/validacion", "Validación CNN", "validacion"]] : [])] as [string,string,string][]).map(([ruta, titulo, icono]) => (
                <Enlace key={ruta} a={ruta} className="osh-action-tile"><Icono n={icono} className="h-6 w-6"/><span>{titulo}</span></Enlace>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
