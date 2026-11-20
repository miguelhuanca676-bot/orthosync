// Piezas comunes de la interfaz: sesión, marco con menú, avisos, ventanas, etc.
import { createContext, MouseEvent, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, ROLES } from "./api";

// ---------------------------------------------------------------- sesión
export type Usuario = { id: number; nombre: string; correo: string; rol: string; debe_cambiar_clave: boolean; acepto_terminos: boolean };
const Contexto = createContext<{ usuario: Usuario | null; listo: boolean; entrar: (c: string, p: string) => Promise<void>;
  salir: () => Promise<void>; actualizar: (u: Usuario) => void }>(null as any);
export const useSesion = () => useContext(Contexto);

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [listo, setListo] = useState(false);
  const salir = useCallback(async () => {
    try { await api.post("/auth/salir"); } catch { /* aunque falle, se cierra en esta pantalla */ }
    setUsuario(null);
  }, []);
  useEffect(() => {   // ¿hay una sesión abierta? (la cookie es invisible para este código; se pregunta al servidor)
    api.get("/auth/yo").then(setUsuario).catch(() => setUsuario(null)).finally(() => setListo(true));
  }, []);
  useEffect(() => {
    const f = () => setUsuario(null);
    window.addEventListener("sesion-vencida", f);
    return () => window.removeEventListener("sesion-vencida", f);
  }, []);
  const entrar = async (correo: string, clave: string) => setUsuario(await api.post("/auth/login", { correo, clave }));
  return <Contexto.Provider value={{ usuario, listo, entrar, salir, actualizar: setUsuario }}>{children}</Contexto.Provider>;
}

// ---------------------------------------------------------------- enlaces internos
/** Enlace interno: navega sin escribir la ruta en ningún lado (ni en la barra de direcciones ni al pasar el mouse). */
export function Enlace({ a, className, children, alHacer }: { a: string; className?: string; children: ReactNode; alHacer?: () => void }) {
  const ir = useNavigate();
  return (
    <a href="#" className={className} onClick={(e: MouseEvent) => { e.preventDefault(); alHacer?.(); ir(a); }}>{children}</a>
  );
}

// ---------------------------------------------------------------- iconos (trazos simples, 24×24)
const TRAZOS: Record<string, string> = {
  resumen: "M4 13h6V4H4zM14 20h6v-9h-6zM4 20h6v-4H4zM14 7h6V4h-6z",
  panel: "M3 10l9-7 9 7M5 9v11h14V9M9 20v-7h6v7",
  estudios: "M3 4h18v16H3zM7 16l3-4 3 3 3-6 2 3",
  modelo3d: "M12 2 21 7v10l-9 5-9-5V7zM3 7l9 5 9-5M12 12v10",
  usuarios: "M16 19v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1M9 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6M22 19v-1a4 4 0 0 0-3-3.9M16 4.1a3 3 0 0 1 0 5.8",
  pacientes: "M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v0a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2M9 13h6M9 17h4",
  solicitudes: "M4 4h16v16H4zM4 9h16M9 14h6",
  auditoria: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4",
  portal: "M3 17l5-5 4 4 8-8M15 8h5v5",
  cuenta: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8M4 21a8 8 0 0 1 16 0",
  salir: "M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 16l4-4-4-4M14 12H4",
  buscar: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14M20 20l-4-4",
  subir: "M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3",
  volver: "M15 18l-6-6 6-6",
  mas: "M12 5v14M5 12h14",
  controles: "M7 3v3M17 3v3M4 8h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1M9 14l2 2 4-4",
  validacion: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  sol: "M12 3v1.5M12 19.5V21M3 12h1.5M19.5 12H21M5.6 5.6l1.1 1.1M17.3 17.3l1.1 1.1M5.6 18.4l1.1-1.1M17.3 6.7l1.1-1.1M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8",
  luna: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z",
};
export const Icono = ({ n, className = "h-[18px] w-[18px]" }: { n: string; className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className}><path d={TRAZOS[n]} /></svg>
);

// ---------------------------------------------------------------- tema claro / oscuro
export function BotonTema({ className = "" }: { className?: string }) {
  const [oscuro, setOscuro] = useState(() => document.documentElement.classList.contains("oscuro"));
  const cambiar = () => {
    const nuevo = !oscuro;
    document.documentElement.classList.toggle("oscuro", nuevo);
    try { localStorage.setItem("orthosync.tema", nuevo ? "oscuro" : "claro"); } catch { /* sin almacenamiento: dura hasta recargar */ }
    setOscuro(nuevo);
  };
  return (
    <button type="button" onClick={cambiar} aria-pressed={oscuro} title={oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition ${className}`}>
      <Icono n={oscuro ? "sol" : "luna"} /><span className="sr-only">{oscuro ? "Modo claro" : "Modo oscuro"}</span>
    </button>
  );
}

// ---------------------------------------------------------------- marco
const MENU: Record<string, [string, string, string][]> = {
  administrador: [["/resumen", "Dashboard", "panel"], ["/pacientes", "Pacientes", "pacientes"], ["/anatomia", "Visor 3D", "modelo3d"], ["/usuarios", "Usuarios", "usuarios"], ["/controles", "Controles", "controles"], ["/validacion", "Validación del modelo", "validacion"], ["/solicitudes", "Solicitudes de datos", "solicitudes"], ["/auditoria", "Auditoría", "auditoria"]],
  traumatologo: [["/panel", "Dashboard", "panel"], ["/pacientes", "Pacientes", "pacientes"], ["/estudios", "Estudios", "estudios"], ["/anatomia", "Visor 3D", "modelo3d"], ["/controles", "Controles", "controles"], ["/validacion", "Validación del modelo", "validacion"]],
  recepcion: [["/panel", "Dashboard", "panel"], ["/pacientes", "Pacientes", "pacientes"], ["/anatomia", "Visor 3D", "modelo3d"], ["/controles", "Controles", "controles"]],
  paciente: [["/portal", "Mi evolución", "portal"]],
};
export const inicioDe = (rol: string) => MENU[rol]?.[0][0] ?? "/";

const hoy = () => new Intl.DateTimeFormat("es-BO", { weekday: "long", day: "numeric", month: "long" }).format(new Date());

export function Marco({ children }: { children: ReactNode }) {
  const { usuario, salir } = useSesion();
  const [abierto, setAbierto] = useState(false);
  const [buscar, setBuscar] = useState("");
  const ir = useNavigate();
  const { pathname } = useLocation();
  if (!usuario) return null;
  const enlaces = [...MENU[usuario.rol], ["/cuenta", "Mi cuenta", "cuenta"] as [string, string, string]];
  const personal = usuario.rol !== "paciente";
  const iniciales = usuario.nombre.replace(/^(Dra?\.|Lic\.)\s*/, "").split(/\s+/).slice(0, 2).map((x) => x[0]).join("");
  return (
    <div className="orthosync-app min-h-screen lg:flex">
      <header className="flex items-center justify-between bg-noche px-4 py-3 text-white lg:hidden">
        <span className="flex items-center gap-2 font-semibold"><img src="/img/husky-guardian.svg" alt="" className="h-10 w-10" />ORTHO<span className="text-celeste">SYNC</span></span>
        <div className="flex items-center gap-2"><BotonTema className="text-sky-100 hover:bg-white/10" />
          <button className="rounded-md px-3 py-1.5 text-sm ring-1 ring-white/30" aria-expanded={abierto} onClick={() => setAbierto(!abierto)}>Menú</button></div>
      </header>
      <aside className={`${abierto ? "flex" : "hidden"} orthosync-sidebar flex-col bg-noche text-white lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-[250px] xl:w-[272px] lg:shrink-0`}
        style={{ backgroundImage: "radial-gradient(140% 50% at 0% 0%, rgba(92,200,245,.18), transparent 60%), radial-gradient(120% 45% at 100% 100%, rgba(124,77,219,.28), transparent 60%)" }}>
        <div className="osh-brand-zone hidden flex-col items-center border-b border-celeste/15 px-5 pb-5 pt-6 lg:flex">
          <img src="/img/husky-guardian.svg" alt="Mascota husky blanco de ORTHOSYNC" className="osh-brand-wolf" />
          <p className="osh-brand-wordmark">ORTHO<span>SYNC</span></p>
          <p className="mt-1 text-center text-[11px] leading-5 text-sky-100/70">Sistema inteligente de<br/>radiología ortopédica</p>
        </div>
        <nav aria-label="Secciones" className="flex-1 overflow-y-auto px-3 py-6">
          <p className="mb-4 px-3 text-[10px] font-extrabold uppercase tracking-[.22em] text-celeste/60">Navegación principal</p>
          <ul className="space-y-1.5">
            {enlaces.map(([ruta, nombre, icono]) => {
              const activo = pathname === ruta || pathname.startsWith(ruta + "/") || (ruta === "/pacientes" && pathname.startsWith("/estudios/"));
              return (
                <li key={ruta}>
                  <Enlace a={ruta} alHacer={() => setAbierto(false)}
                    className={`relative flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-medium transition ${activo ? "bg-gradient-to-r from-azul/85 to-celeste/20 text-white shadow-lg shadow-blue-950/40 ring-1 ring-celeste/35" : "text-sky-100/75 hover:bg-white/10 hover:text-white"}`}>
                    {activo && <span aria-hidden="true" className="absolute inset-y-2 left-0 w-[3px] rounded-full bg-celeste" />}
                    <Icono n={icono} />{nombre}
                  </Enlace>
                </li>
              );
            })}
          </ul>
        </nav>
        {personal && <div className="osh-sidebar-wolf hidden lg:block" aria-hidden="true"><img src="/img/husky-guardian.svg" alt="" /></div>}
        <div className="m-3 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-3 shadow-lg shadow-black/10">
          <span aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-celeste to-violeta text-xs font-semibold">{iniciales}</span>
          <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{usuario.nombre}</p><p className="text-xs text-sky-200/70">{ROLES[usuario.rol]}</p></div>
          <button title="Cerrar sesión" aria-label="Cerrar sesión" className="rounded-md p-1.5 text-sky-100/80 hover:bg-white/10 hover:text-white" onClick={async () => { await salir(); ir("/"); }}><Icono n="salir" /></button>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="osh-topbar sticky top-0 z-20 hidden items-center justify-between gap-6 border-b border-linea bg-panel/90 px-10 py-4 shadow-sm backdrop-blur-xl lg:flex">
          <div className="flex items-center gap-3"><span className="osh-topbar-indicator"/><div><p className="text-[11px] font-bold uppercase tracking-[.16em] text-celeste">ORTHOSYNC · SISTEMA CLÍNICO</p><p className="mt-1 text-xs text-suave first-letter:uppercase">{hoy()}</p></div></div>
          <div className="flex w-full max-w-md items-center justify-end gap-2">
          {personal && (
            <form role="search" className="relative w-full max-w-sm" onSubmit={(e) => { e.preventDefault(); ir("/pacientes", { state: { buscar } }); setBuscar(""); }}>
              <label htmlFor="busqueda-global" className="sr-only">Buscar paciente</label>
              <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-slate-400"><Icono n="buscar" className="h-4 w-4" /></span>
              <input id="busqueda-global" type="search" placeholder="Buscar paciente por nombre, código o CI" className="campo pl-9" value={buscar} onChange={(e) => setBuscar(e.target.value)} />
            </form>
          )}
          <BotonTema className="osh-topbar-theme border border-linea bg-panel text-suave hover:text-fuerte" />
          <div className="osh-topbar-user flex shrink-0 items-center gap-2 rounded-xl border border-celeste/15 px-2.5 py-1.5"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-azul to-violeta text-xs font-bold text-white">{iniciales}</span><span className="hidden xl:block"><span className="block max-w-36 truncate text-xs font-bold text-fuerte">{usuario.nombre}</span><span className="block text-[10px] text-suave">{ROLES[usuario.rol]}</span></span></div>
          </div>
        </div>
        <main className="w-full max-w-[1680px] flex-1 px-4 py-7 sm:px-6 lg:px-10 lg:py-10">{children}</main>
        <PieLegal />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- piezas
export const Cargando = () => <p className="py-10 text-center text-sm text-suave" role="status">Cargando…</p>;

export function Mensaje({ tipo = "error", children }: { tipo?: "error" | "ok" | "info" | "alerta"; children: ReactNode }) {
  const c = { error: "border-red-200 bg-red-50 text-red-800", ok: "border-emerald-200 bg-emerald-50 text-emerald-800",
    info: "border-linea bg-cielo text-marino", alerta: "border-amber-200 bg-amber-50 text-amber-900" }[tipo];
  return <div role={tipo === "error" ? "alert" : "status"} className={`rounded-lg border px-4 py-3 text-sm ${c}`}>{children}</div>;
}

export function Vacio({ titulo, children }: { titulo: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-4 py-10 text-center">
      <img src="/img/sin-datos.webp" alt="" className="h-28 w-28 opacity-90" />
      <p className="mt-3 font-semibold text-fuerte">{titulo}</p>
      {children && <div className="mt-1 max-w-sm text-sm text-suave">{children}</div>}
    </div>
  );
}

export function Ventana({ titulo, alCerrar, children }: { titulo: string; alCerrar: () => void; children: ReactNode }) {
  const caja = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null;
    const enfocables = () => Array.from(caja.current?.querySelectorAll<HTMLElement>("button, a[href], input, select, textarea") ?? []).filter((x) => !x.hasAttribute("disabled"));
    (enfocables()[1] ?? enfocables()[0])?.focus();      // el primer campo (el [0] es el botón cerrar)
    const f = (e: KeyboardEvent) => {
      if (e.key === "Escape") alCerrar();
      if (e.key === "Tab") {      // el foco no sale de la ventana mientras está abierta
        const l = enfocables(); if (!l.length) return;
        if (e.shiftKey && document.activeElement === l[0]) { e.preventDefault(); l[l.length - 1].focus(); }
        else if (!e.shiftKey && document.activeElement === l[l.length - 1]) { e.preventDefault(); l[0].focus(); }
      }
    };
    window.addEventListener("keydown", f);
    return () => { window.removeEventListener("keydown", f); anterior?.focus(); };
  }, []);
  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-noche/50 p-0 sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && alCerrar()}>
      <div ref={caja} role="dialog" aria-modal="true" aria-label={titulo} className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-panel p-6 shadow-xl sm:rounded-2xl">
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-lg font-semibold text-fuerte">{titulo}</h2>
          <button aria-label="Cerrar" className="rounded-md px-2 text-xl leading-none text-suave hover:text-tinta" onClick={alCerrar}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Encabezado({ titulo, detalle, children }: { titulo: ReactNode; detalle?: ReactNode; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0"><h1 className="titulo">{titulo}</h1>{detalle && <div className="mt-1 text-sm text-suave">{detalle}</div>}</div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  );
}

const TONOS = ["bg-celeste", "bg-azul", "bg-indigo-600", "bg-violeta"];
export function Dato({ nombre, valor, nota, tono = 0 }: { nombre: string; valor: ReactNode; nota?: string; tono?: number }) {
  return (
    <div className="tarjeta relative overflow-hidden py-4 pl-6">
      <span aria-hidden="true" className={`absolute inset-y-4 left-0 w-1 rounded-r-full ${TONOS[tono % TONOS.length]}`} />
      <p className="text-[13px] text-suave">{nombre}</p>
      <p className="mt-1 text-[30px] font-semibold leading-none tracking-tight text-fuerte">{valor}</p>
      {nota && <p className="mt-2 text-xs text-suave">{nota}</p>}
    </div>
  );
}

/** Carga datos del servidor y permite recargarlos. */
export function useDatos<T = any>(ruta: string | null) {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!ruta) return;
    let vigente = true;
    api.get(ruta).then((d) => vigente && (setDatos(d), setError(""))).catch((e) => vigente && setError(e.message));
    return () => { vigente = false; };
  }, [ruta, n]);
  return { datos, error, recargar: () => setN((x) => x + 1), setDatos };
}


// ---------------------------------------------------------------- pie con enlaces legales
export function PieLegal({ claro = true }: { claro?: boolean }) {
  const c = claro ? "text-suave hover:text-marino" : "text-blue-100 hover:text-white";
  return (
    <footer className={`w-full max-w-[1680px] px-4 pb-6 text-xs sm:px-6 lg:px-10 ${claro ? "text-suave" : "text-blue-100"}`}>
      <p>Sistema de apoyo al diagnóstico. No sustituye el criterio médico ni el estudio histopatológico. Prototipo académico, no es un dispositivo médico certificado.</p>
      <nav aria-label="Información legal" className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
        <a className={`underline-offset-2 hover:underline ${c}`} href="/privacidad.html" target="_blank" rel="noopener">Privacidad</a>
        <a className={`underline-offset-2 hover:underline ${c}`} href="/terminos.html" target="_blank" rel="noopener">Términos de uso</a>
        <a className={`underline-offset-2 hover:underline ${c}`} href="/cookies.html" target="_blank" rel="noopener">Almacenamiento y cookies</a>
        <a className={`underline-offset-2 hover:underline ${c}`} href="/creditos.html" target="_blank" rel="noopener">Créditos y licencias</a>
      </nav>
    </footer>
  );
}

export function NoEncontrado() {
  return (
    <div className="flex flex-col items-center px-4 py-20 text-center">
      <p className="text-6xl font-semibold tracking-tight text-azul">404</p>
      <h1 className="mt-3 text-xl font-bold text-tinta">Página no encontrada</h1>
      <p className="mt-1 text-sm text-suave">La página que buscas no existe o no está disponible.</p>
      <Enlace a="/" className="boton mt-6">Volver al inicio</Enlace>
    </div>
  );
}
