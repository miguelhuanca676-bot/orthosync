import React, { FormEvent, useState } from "react";
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
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-noche lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="absolute inset-0 bg-[radial-gradient(60%_50%_at_70%_40%,rgba(31,95,214,0.35),transparent_65%),radial-gradient(50%_50%_at_0%_100%,rgba(124,77,219,0.35),transparent_60%)]" />
        <div className="absolute inset-0 opacity-[0.07] [background-image:linear-gradient(rgba(255,255,255,.6)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.6)_1px,transparent_1px)] [background-size:56px_56px] [mask-image:radial-gradient(70%_70%_at_60%_45%,#000,transparent)]" />
        <a href="/" className="relative flex items-center gap-3 text-white"><img src="/img/logo-blanco.svg" alt="" className="h-9 w-9" /><span className="text-lg font-semibold">Orthosync</span></a>
        <div className="relative mx-auto flex w-full max-w-xl items-center gap-10">
          <img src="/img/3d-hueso.webp" alt="" className="h-[48vh] max-h-[480px] w-auto drop-shadow-[0_24px_60px_rgba(92,200,245,0.25)]" />
          <ul className="space-y-5 text-sm text-sky-100/80">
            <li><p className="font-semibold text-white">Detecta</p>Normal o con lesión, y qué tan seguro está el modelo.</li>
            <li><p className="font-semibold text-white">Localiza</p>Recuadro y mapa de calor sobre la placa.</li>
            <li><p className="font-semibold text-white">Explica</p>El hueso en 3D con la lesión en su lugar.</li>
          </ul>
        </div>
        <div className="relative text-white">
          <p className="text-3xl font-semibold leading-tight tracking-[-0.02em]">Una segunda mirada para cada radiografía de hueso</p>
          <p className="mt-3 max-w-md text-sky-100/75">Apoyo al traumatólogo en la detección de tumores óseos.</p>
        </div>
      </div>
      <main className="relative flex items-center justify-center px-5 py-10">
        <BotonTema className="absolute right-4 top-4 border border-linea bg-panel text-suave hover:text-fuerte" />
        <div className="w-full max-w-sm">
          <a href="/" className="mb-8 flex items-center gap-2.5">
            <img src="/img/logo.svg" alt="" className="h-11 w-11" />
            <span><span className="block text-2xl font-bold leading-tight text-fuerte">Orthosync</span>
              <span className="block text-xs text-suave">SpineBolivia</span></span>
          </a>
          <h1 className="text-xl font-bold text-tinta">Ingresa a tu cuenta</h1>
          <p className="mt-1 text-sm text-suave">Personal de la clínica y pacientes.</p>
          <form onSubmit={enviar} className="mt-6 space-y-4">
            {error && <Mensaje>{error}</Mensaje>}
            <div><label className="etiqueta" htmlFor="correo">Correo</label>
              <input id="correo" type="email" autoComplete="username" required className="campo" value={correo} onChange={(e) => setCorreo(e.target.value)} /></div>
            <div><label className="etiqueta" htmlFor="clave">Contraseña</label>
              <input id="clave" type="password" autoComplete="current-password" required className="campo" value={clave} onChange={(e) => setClave(e.target.value)} /></div>
            <button className="boton w-full" disabled={enviando}>{enviando ? "Ingresando…" : "Ingresar"}</button>
          </form>
          <div className="mt-8 -mx-4"><PieLegal /></div>
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
