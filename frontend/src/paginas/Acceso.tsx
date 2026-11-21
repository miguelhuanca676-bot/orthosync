import React, { FormEvent, useState } from "react";
import { api } from "../api";
import { BotonTema, Encabezado, Mensaje, PieLegal, useSesion } from "../componentes";

export function Ingreso() {
  const { entrar } = useSesion();
  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [mostrarClave, setMostrarClave] = useState(false);
  const enviar = async (e: FormEvent) => {
    e.preventDefault(); setError(""); setEnviando(true);
    try { await entrar(correo, clave); }
    catch (err: any) { setError(err.message); }
    finally { setEnviando(false); }
  };
  return (
    <div className="osh-login osh-login-v4">
      <section className="osh-login-hero osh-login-left relative isolate hidden text-white lg:flex" aria-label="ORTHOSYNC · Radiología por rayos X">
        <div className="osh-login-stars pointer-events-none absolute inset-0 -z-10"/>
        <a href="/" className="osh-login-left-brand">
          <img src="/img/asset-husky.webp" alt="" width="48" height="48"
            onError={(ev) => { ev.currentTarget.onerror = null; ev.currentTarget.src="/img/husky-guardian.svg"; }}/>
          <span><strong>ORTHO<span>SYNC</span></strong><small>RADIOLOGÍA POR RAYOS X</small></span>
        </a>
        <div className="osh-login-editorial">
          <span className="osh-login-eyebrow"><span className="osh-live-dot" /> TECNOLOGÍA CLÍNICA · IA</span>
          <h1>La precisión comienza <span>con una imagen.</span></h1>
          <p>Detección asistida de lesiones tumorales en huesos largos mediante radiografías e inteligencia artificial.</p>
          <div className="osh-login-xray" aria-label="Ilustración de radiografía de fémur con lesión resaltada">
            <img src="/img/asset-login.webp" alt="Ilustración de un hueso largo en rayos X con una región señalada para revisión" />
            <div className="osh-login-xray-caption"><span className="osh-live-dot"/> IMAGEN ILUSTRATIVA · REVISIÓN PROFESIONAL</div>
          </div>
        </div>
        <p className="osh-login-left-foot">ORTHOSYNC · Sistema académico de apoyo al diagnóstico</p>
      </section>
      <main className="osh-login-right osh-login-form-area">
        <BotonTema className="osh-login-theme-switch" />
        <div className="osh-login-card osh-login-form-card">
          <a href="/" className="osh-login-form-brand">
            <img src="/img/asset-husky.webp" alt="" width="52" height="52"
              onError={(ev) => { ev.currentTarget.onerror = null; ev.currentTarget.src="/img/husky-guardian.svg"; }}/>
            <span><strong>ORTHO<span>SYNC</span></strong><small>ACCESO CLÍNICO SEGURO</small></span>
          </a>
          <div className="osh-login-form-heading">
            <span className="osh-login-label">BIENVENIDO DE NUEVO</span>
            <h2>Inicia sesión</h2>
            <p>Accede a tus pacientes, estudios y herramientas de análisis.</p>
          </div>
          <form onSubmit={enviar} className="osh-login-fields">
            {error && <Mensaje>{error}</Mensaje>}
            <div>
              <label className="etiqueta" htmlFor="correo">Correo electrónico</label>
              <input id="correo" type="email" autoComplete="username" required className="campo osh-login-input"
                placeholder="correo@clinica.com" value={correo} onChange={(e) => setCorreo(e.target.value)} />
            </div>
            <div>
              <label className="etiqueta" htmlFor="clave">Contraseña</label>
              <div className="osh-login-password-wrap">
                <input id="clave" type={mostrarClave ? "text" : "password"} autoComplete="current-password" required
                  className="campo osh-login-input" placeholder="Tu contraseña" value={clave} onChange={(e) => setClave(e.target.value)} />
                <button type="button" className="osh-login-password-toggle" onClick={() => setMostrarClave((v) => !v)}
                  aria-label={mostrarClave ? "Ocultar contraseña" : "Mostrar contraseña"}>{mostrarClave ? "Ocultar" : "Ver"}</button>
              </div>
            </div>
            <button type="submit" className="boton osh-login-submit w-full" disabled={enviando}>
              {enviando ? "Verificando acceso…" : "Entrar a ORTHOSYNC"}
            </button>
          </form>
          <p className="osh-login-clinical-note">Herramienta de apoyo: toda interpretación requiere validación profesional.</p>
          <a className="osh-login-home-link" href="/">← Volver a la página principal</a>
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
