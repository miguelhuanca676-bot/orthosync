import { FormEvent, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, fechaLocal, edad as edadDe, EVOLUCIONES, fecha, HUESOS, OPINIONES, pct, useImagen } from "../api";
import { Cargando, Encabezado, Enlace, EscaneoCNN, Icono, Mensaje, useDatos, useSesion, Vacio, Ventana } from "../componentes";

const VACIO = { nombres: "", apellidos: "", documento: "", fecha_nacimiento: "", sexo: "", telefono: "", tutor_nombre: "", tutor_documento: "" };
const limpiar = (f: any) => Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : v]));

function FormularioPaciente({ inicial, alGuardar, nuevo = false }: { inicial: any; alGuardar: (d: any) => Promise<void>; nuevo?: boolean }) {
  const campos = Object.keys(VACIO);
  const [f, setF] = useState<any>({ ...VACIO, ...Object.fromEntries(Object.entries(inicial).filter(([k]) => campos.includes(k)).map(([k, v]) => [k, v ?? ""])) });
  const [consentimiento, setConsentimiento] = useState(false);
  const [err, setErr] = useState("");
  const anios = edadDe(f.fecha_nacimiento);
  const menor = anios != null && anios < 18;
  const enviar = async (e: FormEvent) => {
    e.preventDefault(); setErr("");
    try { await alGuardar({ ...limpiar(f), ...(nuevo ? { consentimiento } : {}) }); } catch (x: any) { setErr(x.message); }
  };
  const c = (k: string) => ({ value: (f as any)[k], onChange: (e: any) => setF({ ...f, [k]: e.target.value }) });
  return (
    <form onSubmit={enviar} className="space-y-4">
      {err && <Mensaje>{err}</Mensaje>}
      <div className="grid gap-4 sm:grid-cols-2">
        <div><label className="etiqueta" htmlFor="pn">Nombres</label><input id="pn" required className="campo" {...c("nombres")} /></div>
        <div><label className="etiqueta" htmlFor="pa">Apellidos</label><input id="pa" required className="campo" {...c("apellidos")} /></div>
        <div><label className="etiqueta" htmlFor="pd">Documento (CI)</label><input id="pd" className="campo" {...c("documento")} /></div>
        <div><label className="etiqueta" htmlFor="pf">Fecha de nacimiento</label><input id="pf" type="date" required max={fechaLocal()} className="campo" {...c("fecha_nacimiento")} /></div>
        <div><label className="etiqueta" htmlFor="ps">Sexo</label>
          <select id="ps" className="campo" {...c("sexo")}><option value="">Sin indicar</option><option value="F">Femenino</option><option value="M">Masculino</option></select></div>
        <div><label className="etiqueta" htmlFor="pt">Teléfono</label><input id="pt" className="campo" {...c("telefono")} /></div>
      </div>
      {menor && (
        <fieldset className="rounded-xl border border-linea bg-cielo p-4">
          <legend className="px-1 text-sm font-semibold text-marino">Paciente menor de edad ({anios} años)</legend>
          <p className="mb-3 text-xs text-suave">El consentimiento lo firma su padre, madre o tutor legal.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className="etiqueta" htmlFor="tn">Nombre del padre, madre o tutor</label><input id="tn" required className="campo" {...c("tutor_nombre")} /></div>
            <div><label className="etiqueta" htmlFor="td">Documento del tutor</label><input id="td" className="campo" {...c("tutor_documento")} /></div>
          </div>
        </fieldset>
      )}
      {nuevo && (
        <label className="flex items-start gap-3 rounded-xl border border-linea p-3 text-sm text-tinta">
          <input type="checkbox" required className="mt-0.5 h-4 w-4 accent-indigo-600" checked={consentimiento} onChange={(e) => setConsentimiento(e.target.checked)} />
          <span>El {menor ? "tutor del paciente" : "paciente"} firmó el <strong>consentimiento informado</strong> para registrar sus datos y analizar sus radiografías con este sistema de apoyo.</span>
        </label>
      )}
      <button className="boton w-full">Guardar</button>
    </form>
  );
}

const Avatar = ({ p, grande = false }: { p: any; grande?: boolean }) => (
  <span aria-hidden="true" className={`flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-celeste via-azul to-violeta font-semibold text-white ${grande ? "h-14 w-14 text-lg" : "h-9 w-9 text-xs"}`}>{p.nombres[0]}{p.apellidos[0]}</span>
);

export function Pacientes() {
  const { state } = useLocation() as { state?: { buscar?: string } };
  const [buscar, setBuscar] = useState(state?.buscar ?? "");
  useEffect(() => { if (state?.buscar != null) setBuscar(state.buscar); }, [state]);
  const { datos, error } = useDatos<any[]>(`/pacientes?buscar=${encodeURIComponent(buscar)}`);
  const { usuario } = useSesion();
  const medico = usuario?.rol === "traumatologo";
  const [filtro, setFiltro] = useState<"todos" | "valorar" | "sin">("todos");
  const [nuevo, setNuevo] = useState(false);
  const ir = useNavigate();
  const lista = (datos ?? []).filter((p) => filtro === "todos" || (filtro === "valorar" ? p.por_valorar > 0 : p.n_estudios === 0));
  const pendientes = (datos ?? []).filter((p) => p.por_valorar > 0);
  const totalEstudios = (datos ?? []).reduce((a, p) => a + (p.n_estudios ?? 0), 0);
  const FILTROS: [typeof filtro, string, number][] = [["todos", "Todos", datos?.length ?? 0], ...(medico ? [["valorar", "Por valorar", pendientes.length] as [typeof filtro, string, number]] : []), ["sin", "Sin estudios", (datos ?? []).filter((p) => p.n_estudios === 0).length]];
  return (
    <>
      <div className="osh-patient-hero relative mb-6 overflow-hidden rounded-[25px] border border-celeste/25 p-6 sm:p-8"><span className="osh-kicker"><span className="osh-live-dot"/> GESTIÓN CLÍNICA</span><div className="relative z-10 mt-4 flex flex-wrap items-end justify-between gap-5"><div><h1 className="text-3xl font-extrabold tracking-[-.04em] text-white sm:text-4xl">Expedientes de <span className="text-celeste">pacientes</span></h1><p className="mt-3 max-w-lg text-sm leading-relaxed text-sky-100/75">Consulta historiales autorizados, estudios radiológicos y seguimiento médico desde un mismo espacio.</p></div><div className="flex gap-3"><div className="osh-patient-count"><span>{datos ? datos.length : "—"}</span><small>Pacientes</small></div><div className="osh-patient-count"><span>{datos ? totalEstudios : "—"}</span><small>Estudios</small></div></div></div><img src="/img/logo-blanco.svg" alt="" className="pointer-events-none absolute -right-9 -top-14 h-64 w-64 opacity-[.10]"/></div>
      <Encabezado titulo="Directorio clínico" detalle={datos ? `${datos.length} expedientes y ${totalEstudios} estudios${buscar ? ` que coinciden con «${buscar}»` : ""}` : "Cargando expedientes"}>
        <button className="boton" onClick={() => setNuevo(true)}><Icono n="mas" className="h-4 w-4" />Nuevo paciente</button>
      </Encabezado>
      <div className={`grid gap-6 ${medico ? "xl:grid-cols-[minmax(0,1fr)_340px]" : ""}`}>
        <section aria-label="Lista de pacientes" className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <div className="relative w-full max-w-md">
              <label className="sr-only" htmlFor="b">Buscar paciente</label>
              <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-slate-400"><Icono n="buscar" className="h-4 w-4" /></span>
              <input id="b" type="search" placeholder="Nombre, apellido, código o documento" className="campo pl-9" value={buscar} onChange={(e) => setBuscar(e.target.value)} />
            </div>
            <div role="group" aria-label="Filtrar" className="flex gap-1 rounded-lg border border-linea bg-panel p-1">
              {FILTROS.map(([k, n, c]) => (
                <button key={k} aria-pressed={filtro === k} onClick={() => setFiltro(k)}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium ${filtro === k ? "bg-noche text-white" : "text-suave hover:bg-cielo"}`}>{n} <span className={filtro === k ? "text-sky-200" : "text-slate-400"}>{c}</span></button>
              ))}
            </div>
          </div>
          {error && <Mensaje>{error}</Mensaje>}
          {!datos ? <Cargando /> : lista.length === 0 ? (
            <div className="tarjeta"><Vacio titulo={buscar ? "Sin resultados" : filtro !== "todos" ? "Nada en este filtro" : "Aún no hay pacientes"}>{buscar ? "Prueba con otro nombre, código o documento." : filtro !== "todos" ? "Cambia el filtro para ver los demás expedientes." : "Registra el primero con el botón Nuevo paciente."}</Vacio></div>
          ) : (
            <div className="osh-patient-table overflow-hidden rounded-[20px] border border-linea bg-panel shadow-lg shadow-black/5">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-linea bg-superficie/60 text-[13px] text-suave">
                  <tr><th className="px-4 py-2.5 font-medium">Paciente</th><th className="hidden px-4 py-2.5 font-medium md:table-cell">Documento</th>
                    <th className="hidden px-4 py-2.5 font-medium sm:table-cell">Edad</th><th className="px-4 py-2.5 font-medium">Estudios</th>
                    <th className="hidden px-4 py-2.5 font-medium lg:table-cell">Último estudio</th>{medico && <th className="px-4 py-2.5 font-medium">Estado</th>}</tr>
                </thead>
                <tbody className="divide-y divide-linea">
                  {lista.map((p) => (
                    <tr key={p.id} className="cursor-pointer transition hover:bg-cielo/60" onClick={() => ir(`/pacientes/${p.id}`)}>
                      <td className="px-4 py-3">
                        <Enlace a={`/pacientes/${p.id}`} className="flex items-center gap-3 font-medium text-fuerte">
                          <Avatar p={p} /><span className="min-w-0"><span className="block truncate">{p.apellidos}, {p.nombres}</span><span className="block text-xs font-normal text-suave">{p.codigo}</span></span>
                        </Enlace>
                      </td>
                      <td className="hidden px-4 py-3 text-suave md:table-cell">{p.documento ?? "—"}</td>
                      <td className="hidden px-4 py-3 text-suave sm:table-cell">{edadDe(p.fecha_nacimiento) ?? "—"}{p.es_menor && <span className="chip ml-2 bg-lavanda text-violeta">Menor</span>}</td>
                      <td className="px-4 py-3 text-suave">{p.n_estudios}</td>
                      <td className="hidden px-4 py-3 text-suave lg:table-cell">{fecha(p.ultimo_estudio)}</td>
                      {medico && <td className="px-4 py-3">{p.por_valorar > 0 ? <span className="chip bg-amber-50 text-amber-800 ring-1 ring-amber-200">{p.por_valorar} por valorar</span> : p.n_estudios ? <span className="chip bg-emerald-50 text-emerald-700">Al día</span> : <span className="text-xs text-slate-400">—</span>}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        {medico && (
          <aside className="space-y-4" aria-label="Pendientes">
            <section className="tarjeta">
              <h2 className="subtitulo">Para valorar</h2>
              <p className="mt-0.5 text-[13px] text-suave">Estudios analizados que aún no tienen tu opinión.</p>
              {pendientes.length === 0 ? <p className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">No tienes estudios pendientes.</p> : (
                <ul className="mt-3 divide-y divide-linea">
                  {pendientes.map((p) => (
                    <li key={p.id}><Enlace a={`/pacientes/${p.id}`} className="flex items-center gap-3 py-2.5 hover:text-azul">
                      <Avatar p={p} /><span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{p.nombres} {p.apellidos}</span><span className="block text-xs text-suave">Último estudio {fecha(p.ultimo_estudio)}</span></span>
                      <span className="chip bg-amber-50 text-amber-800">{p.por_valorar}</span></Enlace></li>
                  ))}
                </ul>
              )}
            </section>
            <section className="negatoscopio p-5 text-sky-50">
              <h2 className="font-semibold text-white">Cómo leer el análisis</h2>
              <ul className="mt-3 space-y-2.5 text-[13px] leading-relaxed text-sky-100/85">
                <li>El recuadro celeste lo marca el detector; el ámbar es una ubicación aproximada tomada del mapa de calor.</li>
                <li>Los porcentajes son la confianza del modelo, no una probabilidad clínica.</li>
                <li>El paciente solo ve lo que tú publicas, sin porcentajes.</li>
              </ul>
            </section>
          </aside>
        )}
      </div>
      {nuevo && <Ventana titulo="Nuevo paciente" alCerrar={() => setNuevo(false)}>
        <FormularioPaciente nuevo inicial={{}} alGuardar={async (d) => { const p = await api.post("/pacientes", d); ir(`/pacientes/${p.id}`); }} />
      </Ventana>}
    </>
  );
}


export function PacienteDetalle() {
  const { id } = useParams();
  const { usuario } = useSesion();
  const medico = usuario?.rol === "traumatologo";
  const { datos: p, error, recargar } = useDatos(`/pacientes/${id}`);
  const [editar, setEditar] = useState(false);
  const [cuenta, setCuenta] = useState<null | { correo?: string; clave_temporal?: string }>(null);
  const [correo, setCorreo] = useState(""); const [errCuenta, setErrCuenta] = useState("");
  if (error) return <Mensaje>{error}</Mensaje>;
  if (!p) return <Cargando />;
  const crearCuenta = async (e: FormEvent) => {
    e.preventDefault(); setErrCuenta("");
    try { setCuenta(await api.post(`/pacientes/${id}/cuenta`, { correo })); recargar(); } catch (x: any) { setErrCuenta(x.message); }
  };
  const anios = edadDe(p.fecha_nacimiento);
  const sexo = p.sexo === "F" ? "Femenino" : p.sexo === "M" ? "Masculino" : null;
  return (
    <>
      <p className="mb-3 text-sm"><Enlace a="/pacientes" className="inline-flex items-center gap-1 text-azul hover:underline"><Icono n="volver" className="h-4 w-4" />Pacientes</Enlace></p>
      <div className="osh-patient-detail-hero mb-6 flex flex-wrap items-center justify-between gap-4 rounded-[24px] border border-celeste/25 px-5 py-6 sm:px-7">
        <div className="flex items-center gap-4">
          <Avatar p={p} grande />
          <div>
            <h1 className="text-[clamp(1.45rem,3vw,2.3rem)] font-extrabold tracking-tight text-white">{p.nombres} {p.apellidos}</h1>
            <p className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-sky-100/75">
              <span>Expediente {p.codigo}</span>{anios != null && <span>{anios} años</span>}{sexo && <span>{sexo}</span>}
              {p.es_menor && <span className="chip bg-lavanda text-violeta">Menor de edad</span>}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="rounded-xl border border-white/25 bg-white/10 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/20" onClick={() => setEditar(true)}>Editar datos</button>
          {!p.tiene_cuenta && <button className="rounded-xl border border-celeste/40 bg-celeste/10 px-4 py-2.5 text-sm font-semibold text-celeste transition hover:bg-celeste/20" onClick={() => setCuenta({})}>Crear acceso del paciente</button>}
        </div>
      </div>
      <div className="grid items-start gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
        <div className="space-y-6 xl:sticky xl:top-20">
          <section className="tarjeta osh-detail-card" aria-labelledby="t-ficha">
            <h2 id="t-ficha" className="subtitulo">Ficha</h2>
            <dl className="mt-3 divide-y divide-linea text-sm">
              {([["Documento", p.documento ?? "—"], ["Nacimiento", fecha(p.fecha_nacimiento)], ["Teléfono", p.telefono ?? "—"],
                ...(p.es_menor ? [["Tutor", `${p.tutor_nombre ?? "—"}${p.tutor_documento ? ` · CI ${p.tutor_documento}` : ""}`]] : []),
                ["Consentimiento", p.consentimiento_en ? `Firmado el ${fecha(p.consentimiento_en)}` : "Sin registrar"],
                ["Portal del paciente", p.tiene_cuenta ? "Con acceso" : "Sin acceso"]] as [string, string][]).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 py-2"><dt className="text-suave">{k}</dt><dd className="text-right font-medium">{v}</dd></div>
              ))}
            </dl>
          </section>
          {medico && <SubirRadiografia pacienteId={p.id} />}
        </div>
        <div className="min-w-0">
          {medico ? <Estudios pacienteId={p.id} /> : <Mensaje tipo="info">Los estudios y resultados clínicos solo los ve el traumatólogo.</Mensaje>}
        </div>
      </div>

      {editar && <Ventana titulo="Editar datos" alCerrar={() => setEditar(false)}>
        <FormularioPaciente inicial={p} alGuardar={async (d) => { await api.patch(`/pacientes/${id}`, d); setEditar(false); recargar(); }} />
      </Ventana>}
      {cuenta && <Ventana titulo="Acceso del paciente" alCerrar={() => setCuenta(null)}>
        {cuenta.clave_temporal ? (
          <div className="space-y-3 text-sm">
            <Mensaje tipo="ok">Cuenta creada. Entrega estos datos al paciente; la contraseña no se volverá a mostrar.</Mensaje>
            <p>Correo: <strong>{cuenta.correo}</strong></p>
            <p>Contraseña temporal: <strong className="rounded bg-cielo px-2 py-1 font-mono">{cuenta.clave_temporal}</strong></p>
            <p className="text-suave">El paciente puede cambiarla en "Mi cuenta".</p>
          </div>
        ) : (
          <form onSubmit={crearCuenta} className="space-y-4">
            {errCuenta && <Mensaje>{errCuenta}</Mensaje>}
            <p className="text-sm text-suave">El paciente podrá ver solo los estudios que su médico publique. Al entrar por primera vez deberá crear su propia contraseña y aceptar los términos.{p.es_menor && " Como es menor de edad, entrega el acceso a su padre, madre o tutor."}</p>
            <div><label className="etiqueta" htmlFor="cc">Correo del paciente</label><input id="cc" type="email" required className="campo" value={correo} onChange={(e) => setCorreo(e.target.value)} /></div>
            <button className="boton w-full">Crear acceso</button>
          </form>
        )}
      </Ventana>}
    </>
  );
}

const colorOpinion: Record<string, string> = { normal: "bg-emerald-50 text-emerald-700", benigno: "bg-amber-50 text-amber-800", maligno: "bg-red-50 text-red-700", no_concluyente: "bg-superficie text-suave" };

function SubirRadiografia({ pacienteId }: { pacienteId: string }) {
  const [subiendo, setSubiendo] = useState(false); const [err, setErr] = useState(""); const [encima, setEncima] = useState(false);
  const [fechaEst, setFechaEst] = useState(fechaLocal());
  const archivo = useRef<HTMLInputElement>(null);
  const ir = useNavigate();
  const subir = async (f?: File) => {
    if (!f || subiendo) return;
    setErr(""); setSubiendo(true);
    const fd = new FormData(); fd.append("archivo", f); fd.append("fecha_estudio", fechaEst);
    try { const e = await api.subir(`/pacientes/${pacienteId}/estudios`, fd); ir(`/estudios/${e.id}`); }
    catch (x: any) { setErr(x.message); } finally { setSubiendo(false); if (archivo.current) archivo.current.value = ""; }
  };
  return (
    <section className="tarjeta" aria-labelledby="t-subir">
      <h2 id="t-subir" className="subtitulo"><img src="/img/orthosync-radiografias.svg" alt="" className="osh-img-icon mr-2" />Nueva radiografía</h2>
      {subiendo && <EscaneoCNN mensaje="Subiendo la radiografía y ejecutando el análisis CNN. Conserva esta pestaña abierta." />}
      {err && <div className="mt-3"><Mensaje>{err}</Mensaje></div>}
      <div className="mt-3"><label className="etiqueta" htmlFor="fe">Fecha del estudio</label><input id="fe" type="date" className="campo" value={fechaEst} onChange={(e) => setFechaEst(e.target.value)} /></div>
      <input ref={archivo} type="file" accept=".jpg,.jpeg,.png,.dcm,.dicom,.pdf" className="sr-only" id="arch" onChange={(e) => subir(e.target.files?.[0])} />
      <label htmlFor="arch" onDragOver={(e) => { e.preventDefault(); setEncima(true); }} onDragLeave={() => setEncima(false)}
        onDrop={(e) => { e.preventDefault(); setEncima(false); subir(e.dataTransfer.files?.[0]); }}
        className={`mt-3 flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed px-4 py-7 text-center transition ${encima ? "border-azul bg-cielo" : "border-linea hover:border-azul/50 hover:bg-cielo/50"} ${subiendo ? "pointer-events-none opacity-60" : ""}`}>
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-cielo text-azul"><Icono n="subir" /></span>
        <span className="mt-2 text-sm font-semibold text-fuerte">{subiendo ? "Analizando la radiografía…" : "Arrastra el archivo o haz clic para elegirlo"}</span>
        <span className="mt-1 text-xs text-suave">JPG, PNG, DICOM o el PDF del centro de imágenes, hasta 40 MB</span>
      </label>
    </section>
  );
}

function Miniatura({ e }: { e: any }) {
  const url = useImagen(e.id, e.estado_analisis === "listo" ? "cajas" : "radiografia");
  return (
    <div className="negatoscopio flex h-44 items-center justify-center">
      {url ? <img src={url} alt="" className="h-full w-full object-contain" /> : <span className="text-xs text-sky-200/60">Cargando…</span>}
    </div>
  );
}

function Estudios({ pacienteId }: { pacienteId: string }) {
  const { datos, error } = useDatos<any[]>(`/pacientes/${pacienteId}/estudios`);
  const { datos: ev } = useDatos(`/pacientes/${pacienteId}/evolucion`);
  const puntos = (ev?.puntos ?? []).filter((x: any) => x.area_lesion != null).map((x: any) => ({ fecha: fecha(x.fecha), area: +(x.area_lesion * 100).toFixed(2) }));
  return (
    <div className="space-y-6">
      {puntos.length >= 2 && (
        <section className="tarjeta" aria-labelledby="t-ev">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 id="t-ev" className="subtitulo">Evolución de la zona marcada</h2>
              <p className="mt-0.5 text-[13px] text-suave">Medida relativa: depende del encuadre de cada radiografía.</p>
            </div>
            {ev.cambio_area_ultimo != null && <p className={`chip text-sm ${ev.cambio_area_ultimo < 0 ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>{ev.cambio_area_ultimo < 0 ? "Disminuyó" : "Aumentó"} {Math.abs(ev.cambio_area_ultimo * 100).toFixed(0)} % desde el estudio anterior</p>}
          </div>
          <div className="mt-4 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={puntos} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="linea" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#5cc8f5" /><stop offset="50%" stopColor="#1f5fd6" /><stop offset="100%" stopColor="#7c4ddb" /></linearGradient>
                  <linearGradient id="relleno" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#1f5fd6" stopOpacity={0.22} /><stop offset="100%" stopColor="#5cc8f5" stopOpacity={0.02} /></linearGradient>
                </defs>
                <CartesianGrid stroke="#dce3f0" vertical={false} />
                <XAxis dataKey="fecha" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                <YAxis unit=" %" tick={{ fontSize: 12, fill: "#64748b" }} width={56} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v: any) => [`${v} % de la imagen`, "Zona marcada"]} />
                <Area type="monotone" dataKey="area" stroke="url(#linea)" strokeWidth={3} fill="url(#relleno)" dot={{ r: 4, fill: "#1f5fd6", stroke: "#fff", strokeWidth: 2 }} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      <section aria-labelledby="t-est">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 id="t-est" className="subtitulo">Estudios</h2>
          {datos && datos.length > 0 && <p className="text-[13px] text-suave">{datos.length} en total, del más reciente al más antiguo</p>}
        </div>
        {error && <Mensaje>{error}</Mensaje>}
        {!datos ? <Cargando /> : datos.length === 0 ? <div className="tarjeta"><Vacio titulo="Sin estudios todavía">Sube la primera radiografía con el recuadro de la izquierda.</Vacio></div> : (
          <ol className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3">
            {[...datos].reverse().map((e) => (
              <li key={e.id}>
                <Enlace a={`/estudios/${e.id}`} className="group block rounded-xl border border-linea bg-panel p-2 transition hover:border-azul/40 hover:shadow-lg hover:shadow-indigo-900/5">
                  <Miniatura e={e} />
                  <div className="px-2 pb-1.5 pt-3">
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="font-semibold text-fuerte group-hover:text-azul">{fecha(e.fecha_estudio)}</p>
                      {e.estado_analisis === "listo" && <p className={`text-sm font-semibold ${e.sospechoso ? "text-red-600" : "text-emerald-600"}`}>Lesión {pct(e.p_tumor)}</p>}
                    </div>
                    <p className="mt-0.5 truncate text-[13px] text-suave">{e.estado_analisis === "listo" ? (e.hueso ? `${HUESOS[e.hueso] ?? e.hueso}${e.lado ? ` ${e.lado}` : ""}` : "Hueso sin indicar") : e.estado_analisis === "sin_modelos" ? "Pendiente de análisis" : "No se pudo analizar"}</p>
                    <div className="mt-2.5 flex flex-wrap gap-1.5">
                      {e.opinion ? <span className={`chip ${colorOpinion[e.opinion]}`}>{OPINIONES[e.opinion]}</span> : <span className="chip bg-amber-50 text-amber-800">Por valorar</span>}
                      {e.evolucion && <span className="chip bg-cielo text-marino">{EVOLUCIONES[e.evolucion] ?? e.evolucion}</span>}
                      {e.publicado && <span className="chip bg-lavanda text-violeta">Publicado</span>}
                    </div>
                  </div>
                </Enlace>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
