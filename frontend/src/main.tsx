import { StrictMode, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Outlet, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import "./estilos.css";
import { Cargando, inicioDe, Marco, NoEncontrado, ProveedorSesion, useSesion } from "./componentes";
import { AceptarTerminos, CambioObligatorio, Ingreso, MiCuenta } from "./paginas/Acceso";
import { Auditoria, Resumen, Solicitudes, Usuarios } from "./paginas/Admin";
import { EstudioDetalle } from "./paginas/Estudio";
import { PacienteDetalle, Pacientes } from "./paginas/Pacientes";
import { Portal } from "./paginas/Portal";
import { Controles, Validacion } from "./paginas/Clinica";

// ---------------------------------------------------------------------------------------------
// Rutas ocultas: la ruta real (por ejemplo /pacientes/abc) vive solo en memoria. En la barra de
// direcciones se muestra un código aleatorio distinto en cada paso, sin ningún significado.
// Los botones Atrás/Adelante y recargar la página siguen funcionando dentro de la misma pestaña.
// ---------------------------------------------------------------------------------------------
const MAPA = "orthosync.rutas";
const leerMapa = (): Record<string, string> => { try { return JSON.parse(sessionStorage.getItem(MAPA) || "{}"); } catch { return {}; } };
const guardarMapa = (m: Record<string, string>) => { try { sessionStorage.setItem(MAPA, JSON.stringify(m)); } catch { /* sin almacenamiento */ } };
const codigoAleatorio = () => Array.from(crypto.getRandomValues(new Uint8Array(12)), (b) => b.toString(36).padStart(2, "0")).join("").slice(0, 18);
const rutaInicial = () => leerMapa()[location.hash.slice(1)] ?? "/";

function RutasOcultas() {
  const loc = useLocation();
  const ir = useNavigate();
  const desdeHistorial = useRef(false);
  useEffect(() => {
    const ruta = loc.pathname;
    if (desdeHistorial.current) { desdeHistorial.current = false; return; }
    const mapa = leerMapa();
    const actual = location.hash.slice(1);
    if (mapa[actual] === ruta) return;
    const codigo = codigoAleatorio();
    mapa[codigo] = ruta;
    const claves = Object.keys(mapa); if (claves.length > 300) delete mapa[claves[0]];
    guardarMapa(mapa);
    if (actual && actual in mapa) history.pushState(null, "", "#" + codigo);
    else history.replaceState(null, "", "#" + codigo);
  }, [loc.pathname]);
  useEffect(() => {
    const alVolver = () => {
      const ruta = leerMapa()[location.hash.slice(1)];
      desdeHistorial.current = true;
      ir(ruta ?? "/", { replace: true });
    };
    window.addEventListener("popstate", alVolver);
    return () => window.removeEventListener("popstate", alVolver);
  }, [ir]);
  return null;
}

/** Solo deja pasar a los roles indicados; a cualquier otro le muestra "Página no encontrada". */
function Protegida({ roles }: { roles?: string[] }) {
  const { usuario, listo } = useSesion();
  if (!listo) return <Cargando />;
  if (!usuario) return <Ingreso />;
  if (usuario.debe_cambiar_clave) return <CambioObligatorio />;
  if (usuario.rol === "paciente" && !usuario.acepto_terminos) return <AceptarTerminos />;
  if (roles && !roles.includes(usuario.rol)) return <Marco><NoEncontrado /></Marco>;
  return <Marco><Outlet /></Marco>;
}

function Inicio() {
  const { usuario, listo } = useSesion();
  const ir = useNavigate();
  useEffect(() => {
    if (usuario && !usuario.debe_cambiar_clave && (usuario.rol !== "paciente" || usuario.acepto_terminos)) ir(inicioDe(usuario.rol), { replace: true });
  }, [usuario, ir]);
  if (!listo) return <Cargando />;
  if (!usuario) return <Ingreso />;
  if (usuario.debe_cambiar_clave) return <CambioObligatorio />;
  if (usuario.rol === "paciente" && !usuario.acepto_terminos) return <AceptarTerminos />;
  return <Cargando />;
}

function SesionVencida() {
  const ir = useNavigate();
  const { actualizar } = useSesion();
  useEffect(() => {
    const f = () => { actualizar(null as any); ir("/", { replace: true }); };
    window.addEventListener("sesion-vencida", f);
    return () => window.removeEventListener("sesion-vencida", f);
  }, [ir, actualizar]);
  return null;
}

const PERSONAL = ["administrador", "traumatologo", "recepcion"];

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <ProveedorSesion>
      <MemoryRouter initialEntries={[rutaInicial()]}>
        <RutasOcultas />
        <SesionVencida />
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route element={<Protegida roles={["administrador"]} />}>
            <Route path="/resumen" element={<Resumen />} />
            <Route path="/usuarios" element={<Usuarios />} />
            <Route path="/solicitudes" element={<Solicitudes />} />
            <Route path="/auditoria" element={<Auditoria />} />
          </Route>
          <Route element={<Protegida roles={PERSONAL} />}>
            <Route path="/pacientes" element={<Pacientes />} />
            <Route path="/pacientes/:id" element={<PacienteDetalle />} />
            <Route path="/controles" element={<Controles />} />
          </Route>
          <Route element={<Protegida roles={["administrador", "traumatologo"]} />}>
            <Route path="/validacion" element={<Validacion />} />
          </Route>
          <Route element={<Protegida roles={["traumatologo"]} />}>
            <Route path="/estudios/:id" element={<EstudioDetalle />} />
          </Route>
          <Route element={<Protegida roles={["paciente"]} />}>
            <Route path="/portal" element={<Portal />} />
          </Route>
          <Route element={<Protegida />}>
            <Route path="/cuenta" element={<MiCuenta />} />
            <Route path="*" element={<NoEncontrado />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </ProveedorSesion>
  </StrictMode>,
);

// App instalable: el service worker solo guarda archivos públicos (nunca datos de pacientes).
if ("serviceWorker" in navigator && location.protocol !== "file:" && !import.meta.env.DEV) {
  window.addEventListener("load", () => { navigator.serviceWorker.register("/sw.js").catch(() => { /* sin modo app */ }); });
}
