import { FormEvent, useState } from "react";
import { api, fecha, pct, ROLES } from "../api";
import { Cargando, Dato, Encabezado, Enlace, Mensaje, useDatos, useSesion, Ventana } from "../componentes";
import { InicioClinico } from "./InicioClinico";

export function Resumen() {
  const { datos: e, error } = useDatos("/admin/estadisticas");
  if (error) return <Mensaje>{error}</Mensaje>;
  if (!e) return <Cargando />;
  const sinModelos = !e.modelos.tumor;
  return (
    <>
      <InicioClinico />
      <div className="osh-admin-section-title mt-8 mb-5"><div><p className="osh-console-eyebrow">ADMINISTRACIÓN DE LA PLATAFORMA</p><h2>Resumen operativo</h2></div><Enlace a="/auditoria" className="osh-console-textlink">Auditoría del sistema →</Enlace></div>
      {e.solicitudes_pendientes > 0 && <div className="mb-5"><Mensaje tipo="alerta">Hay {e.solicitudes_pendientes} solicitud(es) de eliminación de datos pendientes. <Enlace a="/solicitudes" className="font-semibold underline">Revisarlas</Enlace></Mensaje></div>}
      {sinModelos && <div className="mb-5"><Mensaje tipo="alerta">Los modelos de análisis todavía no están instalados en el servidor. Los estudios se guardan y se analizarán cuando se copien.</Mensaje></div>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Dato tono={0} nombre="Pacientes" valor={e.pacientes} />
        <Dato tono={1} nombre="Estudios" valor={e.estudios} nota={`${e.estudios_sospechosos} con hallazgo sospechoso`} />
        <Dato tono={2} nombre="Estudios valorados" valor={e.estudios_valorados} />
        <Dato tono={3} nombre="Acuerdo sistema–médico" valor={pct(e.acuerdo_sistema_medico)} nota={`Normal vs. lesión, sobre ${e.casos_para_acuerdo} casos`} />
      </div>
      <div className="mt-6 grid items-start gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <section className="tarjeta" aria-labelledby="t-roles">
          <h2 id="t-roles" className="subtitulo">Usuarios activos</h2>
          <ul className="mt-3 divide-y divide-linea text-sm">
            {Object.entries(e.usuarios_por_rol).map(([rol, n]) => (
              <li key={rol} className="flex items-center justify-between py-2.5"><span className="text-suave">{ROLES[rol]}</span><span className="text-lg font-semibold text-fuerte">{n as number}</span></li>
            ))}
          </ul>
          <Enlace a="/usuarios" className="boton-claro mt-4 w-full">Administrar usuarios</Enlace>
        </section>
        <ActividadReciente />
      </div>
    </>
  );
}

function ActividadReciente() {
  const { datos } = useDatos<any[]>("/admin/auditoria?limite=8");
  return (
    <section className="tarjeta p-0" aria-labelledby="t-act">
      <div className="flex items-center justify-between px-5 pt-5"><h2 id="t-act" className="subtitulo">Actividad reciente</h2><Enlace a="/auditoria" className="text-sm font-medium text-azul hover:underline">Ver toda la auditoría</Enlace></div>
      {!datos ? <Cargando /> : (
        <ul className="mt-2 divide-y divide-linea text-sm">
          {datos.map((a, i) => (
            <li key={i} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 px-5 py-2.5">
              <span><span className="font-medium text-fuerte">{a.usuario ?? "Sistema"}</span> <span className="text-suave">{(ACCIONES[a.accion] ?? a.accion).toLowerCase()}</span>{a.detalle && <span className="text-suave"> · {a.detalle}</span>}</span>
              <span className="text-xs text-suave">{fecha(a.fecha)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function Usuarios() {
  const { usuario: yo } = useSesion();
  const { datos, error, recargar } = useDatos<any[]>("/usuarios");
  const [nuevo, setNuevo] = useState(false);
  const [f, setF] = useState({ nombre: "", correo: "", rol: "traumatologo", clave: "" });
  const [err, setErr] = useState("");
  const crear = async (e: FormEvent) => {
    e.preventDefault(); setErr("");
    try { await api.post("/usuarios", f); setNuevo(false); setF({ nombre: "", correo: "", rol: "traumatologo", clave: "" }); recargar(); }
    catch (x: any) { setErr(x.message); }
  };
  const alternar = async (u: any) => { try { await api.patch(`/usuarios/${u.id}`, { activo: !u.activo }); recargar(); } catch (x: any) { alertar(x.message); } };
  const [aviso, alertar] = useState("");
  if (error) return <Mensaje>{error}</Mensaje>;
  if (!datos) return <Cargando />;
  return (
    <>
      <Encabezado titulo="Usuarios" detalle="Personal de la clínica y cuentas de pacientes">
        <button className="boton" onClick={() => setNuevo(true)}>Nuevo usuario</button>
      </Encabezado>
      {aviso && <div className="mb-4"><Mensaje>{aviso}</Mensaje></div>}
      <div className="tarjeta overflow-x-auto p-0">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="border-b border-linea bg-superficie/60 text-[13px] text-suave">
            <tr><th className="px-4 py-2.5 font-medium">Nombre</th><th className="px-4 py-2.5 font-medium">Correo</th><th className="px-4 py-2.5 font-medium">Rol</th><th className="px-4 py-2.5 font-medium">Estado</th><th className="px-4 py-2.5 font-medium"><span className="sr-only">Acciones</span></th></tr>
          </thead>
          <tbody className="divide-y divide-linea">
            {datos.map((u) => (
              <tr key={u.id}>
                <td className="px-4 py-3 font-medium">{u.nombre}</td>
                <td className="px-4 py-3 text-suave">{u.correo}</td>
                <td className="px-4 py-3">{ROLES[u.rol]}</td>
                <td className="px-4 py-3"><span className={`chip ${u.activo ? "bg-emerald-50 text-emerald-700" : "bg-superficie text-suave"}`}>{u.activo ? "Activo" : "Inactivo"}</span></td>
                <td className="px-4 py-3 text-right">{u.id !== yo?.id && <button className="text-sm font-medium text-azul hover:underline" onClick={() => alternar(u)}>{u.activo ? "Desactivar" : "Activar"}</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {nuevo && (
        <Ventana titulo="Nuevo usuario" alCerrar={() => setNuevo(false)}>
          <form onSubmit={crear} className="space-y-4">
            {err && <Mensaje>{err}</Mensaje>}
            <div><label className="etiqueta" htmlFor="un">Nombre completo</label><input id="un" required className="campo" value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} /></div>
            <div><label className="etiqueta" htmlFor="uc">Correo</label><input id="uc" type="email" required className="campo" value={f.correo} onChange={(e) => setF({ ...f, correo: e.target.value })} /></div>
            <div><label className="etiqueta" htmlFor="ur">Rol</label>
              <select id="ur" className="campo" value={f.rol} onChange={(e) => setF({ ...f, rol: e.target.value })}>
                <option value="traumatologo">Traumatólogo</option><option value="recepcion">Recepción</option><option value="administrador">Administrador</option>
              </select></div>
            <p className="text-xs text-suave">La persona deberá cambiar esta contraseña la primera vez que entre.</p>
            <div><label className="etiqueta" htmlFor="up">Contraseña inicial (mínimo 8 caracteres, con letras y números)</label><input id="up" type="text" required minLength={8} className="campo" value={f.clave} onChange={(e) => setF({ ...f, clave: e.target.value })} /></div>
            <button className="boton w-full">Crear usuario</button>
          </form>
        </Ventana>
      )}
    </>
  );
}

const ACCIONES: Record<string, string> = { login: "Inició sesión", login_fallido: "Intento de ingreso fallido", crear_usuario: "Creó un usuario",
  cambiar_usuario: "Modificó un usuario", crear_paciente: "Registró un paciente", ver_paciente: "Abrió un expediente", cambiar_paciente: "Modificó datos de un paciente",
  crear_cuenta_paciente: "Creó el acceso de un paciente", ver_estudios: "Vio los estudios de un paciente", subir_estudio: "Subió una radiografía",
  ver_estudio: "Abrió un estudio", reanalizar_estudio: "Volvió a analizar un estudio", recortar_estudio: "Ajustó el recorte de un estudio",
  valorar_estudio: "Registró una valoración", publicar_estudio: "Publicó un estudio al paciente", ocultar_estudio: "Ocultó un estudio al paciente",
  borrar_estudio: "Eliminó un estudio", portal_paciente: "Consultó su portal", cambio_clave: "Cambió su contraseña",
  logout: "Cerró sesión", cuenta_bloqueada: "Cuenta bloqueada por intentos fallidos", aceptar_terminos: "Aceptó los términos",
  exportar_datos: "Descargó sus datos", solicitar_eliminacion: "Solicitó eliminar sus datos", eliminar_datos_paciente: "Eliminó los datos de un paciente",
  rechazar_eliminacion: "Rechazó una solicitud de eliminación", informe_estudio: "Descargó un informe", informe_portal: "Descargó su resumen" };

export function Auditoria() {
  const { datos, error } = useDatos<any[]>("/admin/auditoria?limite=300");
  if (error) return <Mensaje>{error}</Mensaje>;
  if (!datos) return <Cargando />;
  return (
    <>
      <Encabezado titulo="Auditoría" detalle="Últimos 300 movimientos: quién hizo qué y cuándo" />
      <div className="tarjeta overflow-x-auto p-0">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="border-b border-linea bg-superficie/60 text-[13px] text-suave">
            <tr><th className="px-4 py-2.5 font-medium">Fecha y hora</th><th className="px-4 py-2.5 font-medium">Usuario</th><th className="px-4 py-2.5 font-medium">Acción</th><th className="px-4 py-2.5 font-medium">Detalle</th><th className="px-4 py-2.5 font-medium">IP</th></tr>
          </thead>
          <tbody className="divide-y divide-linea">
            {datos.map((a, i) => (
              <tr key={i}>
                <td className="whitespace-nowrap px-4 py-2.5 text-suave">{new Date(a.fecha + "Z").toLocaleString("es-BO", { dateStyle: "short", timeStyle: "short" })}</td>
                <td className="px-4 py-2.5">{a.usuario ?? "—"}</td>
                <td className="px-4 py-2.5">{ACCIONES[a.accion] ?? a.accion}</td>
                <td className="px-4 py-2.5 text-suave">{a.detalle}</td>
                <td className="px-4 py-2.5 text-suave">{a.ip ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}


export function Solicitudes() {
  const { datos, error, recargar } = useDatos<any[]>("/admin/solicitudes");
  const [accion, setAccion] = useState<null | { s: any; tipo: "ejecutar" | "rechazar" }>(null);
  const [respuesta, setRespuesta] = useState(""); const [err, setErr] = useState("");
  const confirmar = async () => {
    setErr("");
    try {
      if (accion!.tipo === "ejecutar") await api.post(`/admin/solicitudes/${accion!.s.id}/ejecutar`);
      else await api.post(`/admin/solicitudes/${accion!.s.id}/rechazar`, { respuesta });
      setAccion(null); setRespuesta(""); recargar();
    } catch (x: any) { setErr(x.message); }
  };
  if (error) return <Mensaje>{error}</Mensaje>;
  if (!datos) return <Cargando />;
  const tono: Record<string, string> = { pendiente: "bg-amber-50 text-amber-800", completada: "bg-emerald-50 text-emerald-700", rechazada: "bg-superficie text-suave" };
  return (
    <>
      <Encabezado titulo="Solicitudes de datos" detalle="Pedidos de pacientes para eliminar sus datos personales" />
      <div className="mb-4"><Mensaje tipo="info">Antes de eliminar, verifica si la clínica debe conservar la historia clínica por obligación legal. Si es así, rechaza la solicitud explicando el motivo.</Mensaje></div>
      {datos.length === 0 ? <div className="tarjeta"><p className="py-6 text-center text-sm text-suave">No hay solicitudes.</p></div> : (
        <ul className="space-y-3">
          {datos.map((s) => (
            <li key={s.id} className="tarjeta flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-semibold">Paciente {s.codigo_paciente} · {fecha(s.fecha)}</p>
                <p className="mt-1 text-sm text-suave">{s.motivo || "Sin motivo indicado"}</p>
                {s.respuesta && <p className="mt-1 text-sm text-suave">Respuesta: {s.respuesta}</p>}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`chip ${tono[s.estado]}`}>{s.estado}</span>
                {s.estado === "pendiente" && <>
                  <button className="boton-claro" onClick={() => setAccion({ s, tipo: "rechazar" })}>Rechazar</button>
                  <button className="boton-peligro" onClick={() => setAccion({ s, tipo: "ejecutar" })}>Eliminar datos</button>
                </>}
              </div>
            </li>
          ))}
        </ul>
      )}
      {accion && (
        <Ventana titulo={accion.tipo === "ejecutar" ? "Eliminar datos del paciente" : "Rechazar solicitud"} alCerrar={() => setAccion(null)}>
          {err && <div className="mb-3"><Mensaje>{err}</Mensaje></div>}
          {accion.tipo === "ejecutar" ? (
            <p className="text-sm text-suave">Se eliminarán de forma <strong>definitiva</strong> los datos del paciente {accion.s.codigo_paciente}, todos sus estudios y radiografías y su acceso al portal. Esta acción no se puede deshacer.</p>
          ) : (
            <><label className="etiqueta" htmlFor="resp">Motivo del rechazo (lo verá el paciente)</label>
              <textarea id="resp" rows={3} className="campo" value={respuesta} onChange={(e) => setRespuesta(e.target.value)} /></>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <button className="boton-claro" onClick={() => setAccion(null)}>Cancelar</button>
            <button className={accion.tipo === "ejecutar" ? "boton-peligro" : "boton"} disabled={accion.tipo === "rechazar" && respuesta.trim().length < 3} onClick={confirmar}>
              {accion.tipo === "ejecutar" ? "Eliminar definitivamente" : "Rechazar solicitud"}</button>
          </div>
        </Ventana>
      )}
    </>
  );
}
