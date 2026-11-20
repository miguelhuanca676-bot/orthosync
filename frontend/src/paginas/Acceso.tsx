import React, { FormEvent, lazy, Suspense, useState } from "react";
const Visor3D = lazy(() => import("../Visor3D"));
import { api } from "../api";
import { BotonTema, Encabezado, Mensaje, PieLegal, useSesion } from "../componentes";

export function Ingreso() {
  const { entrar } = useSesion();
  const [correo, setCorreo] = useState(""); const [clave, setClave] = useState("");
  const [error, setError] = useState(""); const [enviando, setEnviando] = useState(false);
  const enviar = async (e: FormEvent) => {
    e.preventDefault(); setError(""); setEnviando(true);
    try { await entrar(correo, clave); } catch (err: any) { setError(err.message); } finally { setEnviando(false); }
  };
  return (
    <div className="osh-login min-h-screen lg:grid lg:grid-cols-[1.12fr_.88fr]">
      <section className="osh-login-hero relative isolate hidden min-h-screen flex-col overflow-hidden px-8 pb-8 pt-9 text-white lg:flex xl:px-14">
        <div className="osh-login-stars pointer-events-none absolute inset-0 -z-10"/>
        <a href="/" className="relative z-10 inline-flex w-fit items-center gap-3">
          <img src="/img/logo-blanco.svg" alt="" className="h-14 w-14 rounded-2xl border border-celeste/30 bg-white/10 p-1"/>
          <span><span className="block text-2xl font-extrabold uppercase tracking-[.09em]">Ortho<span className="text-celeste">sync</span></span><span className="mt-1 block text-[11px] uppercase tracking-[.2em] text-celeste/80">Medical Intelligence</span></span>
        </a>
        <div className="relative z-10 mx-auto flex w-full max-w-[760px] flex-1 flex-col justify-center py-12">
          <span className="osh-kicker w-fit"><span className="osh-live-dot" /> RADIOLOGÍA · VISIÓN INTELIGENTE</span>
          <h1 className="mt-6 max-w-[660px] text-[clamp(2.2rem,4vw,4.3rem)] font-extrabold leading-[1.06] tracking-[-.055em]">
            Una nueva dimensión<br/>del <span className="text-celeste">análisis óseo.</span>
          </h1>
          <p className="mt-4 max-w-[580px] text-sm leading-7 text-sky-100/75 xl:text-base">Análisis asistido por inteligencia artificial, gestión clínica y visualización anatómica 3D en un solo lugar.</p>
          <div className="osh-login-visual relative mt-7 overflow-hidden rounded-[26px] border border-celeste/30">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
              <span className="inline-flex items-center gap-2 text-xs font-bold text-white"><span className="osh-live-dot"/> VISUALIZACIÓN ANATÓMICA</span>
              <span className="text-[10px] font-semibold tracking-[.12em] text-celeste">3D · REFERENCIA</span>
            </div>
            <Suspense fallback={<div className="grid h-[320px] place-items-center text-sm text-sky-100/70">Preparando visor anatómico…</div>}>
              <Visor3D hueso="femur" zona={null} alto={320}/>
            </Suspense>
          </div>
          <div className="mt-5 grid grid-cols-3 gap-3">
            <div className="osh-login-feature"><span className="text-celeste">01</span><strong>Detección asistida</strong></div>
            <div className="osh-login-feature"><span className="text-celeste">02</span><strong>Revisión médica</strong></div>
            <div className="osh-login-feature"><span className="text-celeste">03</span><strong>Anatomía 3D</strong></div>
          </div>
        </div>
        <p className="relative z-10 text-[11px] text-sky-100/50">ORTHOSYNC · SpineBolivia · Prototipo académico de apoyo al diagnóstico</p>
      </section>
      <main className="osh-login-right relative flex min-h-screen items-center justify-center px-5 py-14 sm:px-10">
        <BotonTema className="absolute right-5 top-5 border border-linea bg-panel text-suave hover:text-fuerte" />
        <div className="osh-login-card relative w-full max-w-[480px] overflow-hidden rounded-[30px] p-7 sm:p-10">
          <a href="/" className="mb-8 flex items-center gap-3">
            <img src="/img/logo.svg" alt="ORTHOSYNC" className="h-14 w-14 rounded-2xl border border-celeste/25 bg-noche/15 p-1"/>
            <span><span className="block text-[23px] font-extrabold uppercase tracking-[.06em] text-fuerte">ORTHO<span className="text-celeste">SYNC</span></span><span className="text-[11px] font-semibold uppercase tracking-[.13em] text-suave">Acceso clínico seguro</span></span>
          </a>
          <span className="osh-login-label">BIENVENIDO DE NUEVO</span>
          <h2 className="mt-3 text-[clamp(1.65rem,3vw,2.25rem)] font-extrabold tracking-[-.045em] text-fuerte">Ingresa a tu cuenta</h2>
          <p className="mt-2 text-sm leading-relaxed text-suave">Accede a tu espacio de trabajo, pacientes y estudios radiológicos.</p>
          <form onSubmit={enviar} className="mt-8 space-y-5">
            {error && <Mensaje>{error}</Mensaje>}
            <div>
              <label className="etiqueta" htmlFor="correo">Correo electrónico</label>
              <input id="correo" type="email" autoComplete="username" required className="campo osh-login-input" placeholder="tu-correo@clinica.com" value={correo} onChange={(e) => setCorreo(e.target.value)}/>
            </div>
            <div>
              <label className="etiqueta" htmlFor="clave">Contraseña</label>
              <input id="clave" type="password" autoComplete="current-password" required className="campo osh-login-input" placeholder="Ingresa tu contraseña" value={clave} onChange={(e) => setClave(e.target.value)}/>
            </div>
            <button className="boton osh-login-submit w-full" disabled={enviando}>{enviando ? "Ingresando…" : "Ingresar al sistema"}</button>
          </form>
          <div className="mt-7 flex items-start gap-3 rounded-xl border border-celeste/15 bg-celeste/5 p-3 text-xs leading-relaxed text-suave"><span className="text-lg text-celeste" aria-hidden="true">✦</span><span>Entorno de apoyo clínico. Los resultados de IA deben ser revisados por un profesional médico.</span></div>
          <div className="mt-6 -mx-4"><PieLegal /></div>
        </div>
      </main>
    </div>
  );
}

export function MiCuenta() {
  const { usuario, actualizar } = useSesion();
  const [actual, setActual] = useState(""); const [nueva, setNueva] = useState("");
  const [estado, setEstado] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const enviar = async (e: FormEvent) => {
    e.preventDefault(); setEstado(null);
    try {
      actualizar(await api.post("/auth/cambiar-clave", { clave_actual: actual, clave_nueva: nueva }));
      setEstado({ tipo: "ok", texto: "Contraseña actualizada." }); setActual(""); setNueva("");
    } catch (err: any) { setEstado({ tipo: "error", texto: err.message }); }
  };
  return (
    <>
      <Encabezado titulo="Mi cuenta" detalle={usuario?.correo} />
      <form onSubmit={enviar} className="tarjeta max-w-md space-y-4">
        <h2 className="font-semibold text-marino">Cambiar contraseña</h2>
        {estado && <Mensaje tipo={estado.tipo}>{estado.texto}</Mensaje>}
        <div><label className="etiqueta" htmlFor="ca">Contraseña actual</label>
          <input id="ca" type="password" required autoComplete="current-password" className="campo" value={actual} onChange={(e) => setActual(e.target.value)} /></div>
        <div><label className="etiqueta" htmlFor="cn">Contraseña nueva (mínimo 8 caracteres, con letras y números)</label>
          <input id="cn" type="password" required minLength={8} autoComplete="new-password" className="campo" value={nueva} onChange={(e) => setNueva(e.target.value)} /></div>
        <button className="boton">Guardar</button>
      </form>
    </>
  );
}


/** Pantalla sencilla centrada, para los pasos obligatorios antes de entrar. */
function PasoPrevio({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  const { salir } = useSesion();
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="tarjeta w-full max-w-lg p-7">
        <div className="mb-5 flex items-center gap-2.5">
          <img src="/img/logo.svg" alt="" className="h-10 w-10" />
          <span className="text-xl font-bold text-fuerte">Orthosync</span>
        </div>
        <h1 className="titulo">{titulo}</h1>
        <div className="mt-4">{children}</div>
        <button className="mt-6 text-sm text-suave underline-offset-2 hover:underline" onClick={salir}>Cerrar sesión</button>
      </div>
    </main>
  );
}

export function CambioObligatorio() {
  const { actualizar } = useSesion();
  const [actual, setActual] = useState(""); const [nueva, setNueva] = useState(""); const [repetir, setRepetir] = useState("");
  const [error, setError] = useState("");
  const enviar = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    if (nueva !== repetir) { setError("Las contraseñas nuevas no coinciden."); return; }
    try { actualizar(await api.post("/auth/cambiar-clave", { clave_actual: actual, clave_nueva: nueva })); }
    catch (x: any) { setError(x.message); }
  };
  return (
    <PasoPrevio titulo="Crea tu contraseña">
      <p className="text-sm text-suave">Por seguridad, la contraseña que te entregaron es temporal. Crea una propia antes de continuar: al menos 8 caracteres, con letras y números.</p>
      <form onSubmit={enviar} className="mt-5 space-y-4">
        {error && <Mensaje>{error}</Mensaje>}
        <div><label className="etiqueta" htmlFor="o-a">Contraseña actual (temporal)</label><input id="o-a" type="password" required autoComplete="current-password" className="campo" value={actual} onChange={(e) => setActual(e.target.value)} /></div>
        <div><label className="etiqueta" htmlFor="o-n">Contraseña nueva</label><input id="o-n" type="password" required minLength={8} autoComplete="new-password" className="campo" value={nueva} onChange={(e) => setNueva(e.target.value)} /></div>
        <div><label className="etiqueta" htmlFor="o-r">Repite la contraseña nueva</label><input id="o-r" type="password" required minLength={8} autoComplete="new-password" className="campo" value={repetir} onChange={(e) => setRepetir(e.target.value)} /></div>
        <button className="boton w-full">Guardar y continuar</button>
      </form>
    </PasoPrevio>
  );
}

export function AceptarTerminos() {
  const { actualizar } = useSesion();
  const [acepto, setAcepto] = useState(false); const [error, setError] = useState("");
  const enviar = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    try { actualizar(await api.post("/portal/aceptar-terminos")); } catch (x: any) { setError(x.message); }
  };
  return (
    <PasoPrevio titulo="Antes de ver tu información">
      <div className="space-y-3 text-sm leading-relaxed text-suave">
        <p>En este portal verás los estudios que tu médico revisó y decidió compartir contigo.</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>La información es de apoyo: ante cualquier duda, consulta a tu médico.</li>
          <li>Tus datos se usan solo para tu atención en la clínica.</li>
          <li>Puedes descargar tus datos o pedir que se eliminen desde el portal.</li>
        </ul>
        <p>Lee la <a className="font-medium text-marino underline" href="/privacidad.html" target="_blank" rel="noopener">política de privacidad</a> y los <a className="font-medium text-marino underline" href="/terminos.html" target="_blank" rel="noopener">términos de uso</a>.</p>
      </div>
      <form onSubmit={enviar} className="mt-5 space-y-4">
        {error && <Mensaje>{error}</Mensaje>}
        <label className="flex items-start gap-3 text-sm text-tinta">
          <input type="checkbox" className="mt-0.5 h-4 w-4 accent-indigo-600" checked={acepto} onChange={(e) => setAcepto(e.target.checked)} />
          <span>Leí y acepto la política de privacidad y los términos de uso. Si soy padre, madre o tutor, acepto en nombre del paciente menor de edad.</span>
        </label>
        <button className="boton w-full" disabled={!acepto}>Aceptar y continuar</button>
      </form>
    </PasoPrevio>
  );
}
