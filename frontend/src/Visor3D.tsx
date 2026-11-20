// Visor 3D: hueso ilustrativo con la lesión dibujada en su sitio. Se carga solo cuando se usa.
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { ALTO, aplicarLesion, cargarHueso, HUESOS_3D, preparar, TipoLesion, Zona } from "./hueso3d";

export const COLORES = { maligno: "#e5484d", benigno: "#f5a524", neutro: "#ff7a45", paciente: "#ff8a3d" };
type Tono = keyof typeof COLORES;
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
const NOMBRE_TIPO: Record<TipoLesion, string> = { cavidad: "Lesión lítica (hueco)", crecimiento: "Lesión que crece hacia afuera", mancha: "Zona afectada" };

export default function Visor3D({ hueso, lado, zona, tono = "neutro", tipo = "mancha", alto = 440, alListo }:
  { hueso: string; lado?: string | null; zona: Zona | null; tono?: Tono; tipo?: TipoLesion; alto?: number;
    alListo?: (capturar: (() => string) | null) => void }) {
  const caja = useRef<HTMLDivElement>(null);
  const r = useRef<any>({});
  const [girando, setGirando] = useState(false);
  const [falla, setFalla] = useState(false);
  const [estado, setEstado] = useState<"cargando" | "anatomico" | "simple" | "error">("cargando");
  const [reintentos, setReintentos] = useState(0);
  const [version, setVersion] = useState(0);   // avisa al efecto de la lesión que la escena ya está lista
  const avisar = useRef(alListo); avisar.current = alListo;

  // Escena: se arma de nuevo solo si cambia el hueso o el lado
  useEffect(() => {
    let vivo = true, limpiar: (() => void) | null = null;
    setEstado("cargando");
    cargarHueso(hueso).then((res) => {
      if (!vivo) { res?.geos.forEach((g) => g.dispose()); return; }
      if (!res) { setEstado("error"); return; }
      limpiar = armar(res.geos);
      if (limpiar) { setEstado(res.anatomico ? "anatomico" : "simple"); setVersion((v) => v + 1); }
    }).catch(() => { if (vivo) setEstado("error"); });
    return () => { vivo = false; limpiar?.(); };
  }, [hueso, lado, alto, reintentos]);

  function armar(crudas: THREE.BufferGeometry[]): (() => void) | null {
    const el = caja.current; if (!el) return null;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); }
    catch { setFalla(true); return null; }
    const geos = preparar(crudas);
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.08;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.setSize(el.clientWidth, alto);
    renderer.domElement.setAttribute("aria-hidden", "true");
    el.appendChild(renderer.domElement);

    const escena = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(renderer);
    const entorno = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;   // reflejos suaves de estudio
    escena.environment = entorno; escena.environmentIntensity = 0.55;
    const camara = new THREE.PerspectiveCamera(35, el.clientWidth / alto, 0.05, 200);
    escena.add(new THREE.HemisphereLight("#eaf5ff", "#1b2940", 1.4));
    const luz = new THREE.DirectionalLight("#fff9ed", 2.1); luz.position.set(6, 12, 10); escena.add(luz);
    const contra = new THREE.DirectionalLight("#7fb2ff", 1.15); contra.position.set(-8, 4, -10); escena.add(contra);
    camara.add(new THREE.PointLight("#ffffff", 0.6, 0, 0)); escena.add(camara);   // luz que acompaña a la cámara (ilumina el interior del hueco)

    const grupo = new THREE.Group();
    const material = new THREE.MeshPhysicalMaterial({ vertexColors: true, roughness: 0.76, metalness: 0, side: THREE.DoubleSide,
      clearcoat: 0.06, clearcoatRoughness: 0.85, sheen: 0.16, sheenRoughness: 0.9, sheenColor: new THREE.Color("#fff3dc") });
    geos.forEach((g) => grupo.add(new THREE.Mesh(g, material)));
    if (lado === "izquierdo") grupo.scale.x = -1;          // espejo para el lado izquierdo
    escena.add(grupo);

    const controles = new OrbitControls(camara, renderer.domElement);
    controles.enableDamping = true; controles.minDistance = 1.2; controles.maxDistance = 65; controles.autoRotateSpeed = 1.6;
    // Encuadre adaptativo: cadera, mano y huesos largos se ajustan a su geometría real.
    const limites = new THREE.Box3().setFromObject(grupo);
    const centro = limites.getCenter(new THREE.Vector3());
    const dimensiones = limites.getSize(new THREE.Vector3());
    const fov = THREE.MathUtils.degToRad(camara.fov);
    const distancia = Math.max(
      dimensiones.y / (2 * Math.tan(fov / 2) * 0.78),
      dimensiones.x / (2 * camara.aspect * Math.tan(fov / 2) * 0.78),
      dimensiones.z * 2.2, 9
    );
    const completo = { pos: centro.clone().add(V(0, dimensiones.y * 0.06, distancia)), mira: centro.clone() };
    camara.position.copy(completo.pos); controles.target.copy(completo.mira); controles.update();

    let anim: null | { t0: number; dur: number; p0: THREE.Vector3; p1: THREE.Vector3; m0: THREE.Vector3; m1: THREE.Vector3 } = null;
    const irA = (pos: THREE.Vector3, mira: THREE.Vector3, dur = 1500) =>
      (anim = { t0: performance.now(), dur, p0: camara.position.clone(), p1: pos, m0: controles.target.clone(), m1: mira });

    let lesion: ReturnType<typeof aplicarLesion> = null, extension = 0.15;
    const acercar = () => {
      if (!lesion) return;
      const p = lesion.punto.clone(), dir = lesion.dir.clone();
      if (lado === "izquierdo") { p.x *= -1; dir.x *= -1; }
      const d = Math.max(extension * ALTO * 0.9, 1.2) + 2.2;
      const lateral = V(dir.z, 0, -dir.x).multiplyScalar(d * 0.35);       // un poco de costado para ver la profundidad
      irA(p.clone().add(dir.multiplyScalar(d)).add(lateral).add(V(0, d * 0.3, 0)), p);
    };

    const zoom = (factor: number) => {
      const origen = controles.target;
      const offset = camara.position.clone().sub(origen);
      const destino = THREE.MathUtils.clamp(offset.length() * factor, controles.minDistance, controles.maxDistance);
      irA(origen.clone().add(offset.setLength(destino)), origen.clone(), 300);
    };
    r.current = {
      zoom, dibujar: (zona: Zona | null, color: string, tipo: TipoLesion) => {
        lesion = aplicarLesion(geos, zona, color, tipo);
        extension = zona?.extension ?? 0.15;
      },
      acercar, completo: () => irA(completo.pos.clone(), completo.mira.clone()), controles, primera: true,
    };

    // captura de la vista actual (para incluirla en el informe PDF)
    avisar.current?.(() => {
      renderer.setClearColor("#1a2470", 1); renderer.render(escena, camara);        // fondo azul (el PDF no tiene transparencia)
      const png = renderer.domElement.toDataURL("image/png");
      renderer.setClearColor("#000000", 0); renderer.render(escena, camara);
      return png;
    });

    let vivo = true, visible = true;
    const observar = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; });
    observar.observe(el);
    const cuadro = (ahora: number) => {
      if (!vivo) return;
      if (anim) {
        const t = Math.min(1, (ahora - anim.t0) / anim.dur), e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        camara.position.lerpVectors(anim.p0, anim.p1, e); controles.target.lerpVectors(anim.m0, anim.m1, e);
        if (t >= 1) anim = null;
      }
      if (visible && !document.hidden) { controles.update(); renderer.render(escena, camara); }
      requestAnimationFrame(cuadro);
    };
    requestAnimationFrame(cuadro);

    const ajustar = new ResizeObserver(() => {
      camara.aspect = el.clientWidth / alto; camara.updateProjectionMatrix(); renderer.setSize(el.clientWidth, alto);
    });
    ajustar.observe(el);
    return () => {
      vivo = false; avisar.current?.(null); observar.disconnect(); ajustar.disconnect(); controles.dispose();
      geos.forEach((g) => g.dispose()); material.dispose(); entorno.dispose(); pmrem.dispose();
      renderer.dispose(); renderer.domElement.remove(); r.current = {};
    };
  }

  // Lesión: se redibuja sin rearmar la escena
  useEffect(() => {
    if (!r.current.dibujar) return;
    r.current.dibujar(zona, COLORES[tono], tipo);
    if (r.current.primera && zona) { r.current.primera = false; setTimeout(() => r.current.acercar?.(), 600); }
  }, [version, zona?.posicion, zona?.extension, zona?.angulo, tono, tipo]);

  useEffect(() => { if (r.current.controles) r.current.controles.autoRotate = girando; }, [girando, version]);

  if (!HUESOS_3D.includes(hueso)) return <p className="rounded-xl bg-cielo p-4 text-sm text-marino">El modelo 3D no está disponible para este hueso.</p>;
  if (falla) return <p className="rounded-xl bg-cielo p-4 text-sm text-marino">Este navegador no permite mostrar gráficos 3D.</p>;
  const boton = "rounded-lg bg-white/15 px-3 py-1.5 text-xs font-semibold text-white ring-1 ring-white/25 backdrop-blur hover:bg-white/25";
  return (
    <div className="negatoscopio">
      <div ref={caja} role="img" aria-label={`Modelo 3D ilustrativo del hueso. ${zona ? NOMBRE_TIPO[tipo] : "Sin lesión marcada"}.`} style={{ height: alto }} />
      {estado === "cargando" && <p className="pointer-events-none absolute inset-0 grid place-items-center text-sm text-blue-100">Cargando modelo anatómico…</p>}
      {estado === "error" && <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-noche/90 p-6 text-center text-sm text-sky-100"><p>No fue posible cargar el modelo anatómico.</p><button className="rounded-xl bg-celeste px-4 py-2 font-semibold text-noche" onClick={() => setReintentos((n) => n + 1)}>Reintentar</button></div>}
      <div className="absolute left-3 top-3 max-w-[40%] rounded-lg border border-celeste/20 bg-noche/65 px-3 py-2 text-[11px] font-medium text-sky-100 backdrop-blur-md">{estado === "anatomico" ? "Modelo anatómico de referencia" : estado === "simple" ? "Vista ilustrativa de respaldo" : estado === "error" ? "Modelo no disponible" : "Preparando visualización 3D"}</div>
      <div className="absolute right-3 top-14 flex max-w-[calc(100%-1.5rem)] flex-wrap justify-end gap-2 sm:top-3 sm:max-w-[65%]">
        {zona && <button className={boton} onClick={() => r.current.acercar?.()}>Acercar a la lesión</button>}
        <button className={boton} onClick={() => r.current.completo?.()}>Hueso completo</button>
        <button className={boton} aria-label="Acercar vista" onClick={() => r.current.zoom?.(0.78)}>+</button>
        <button className={boton} aria-label="Alejar vista" onClick={() => r.current.zoom?.(1.28)}>−</button>
        <button className={boton} aria-pressed={girando} onClick={() => setGirando(!girando)}>{girando ? "Detener giro" : "Girar"}</button>
      </div>
      {estado === "simple" && <button className="absolute bottom-11 left-3 rounded-lg border border-amber-300/40 bg-noche/85 px-3 py-2 text-xs text-amber-100 hover:bg-noche" onClick={() => setReintentos((n) => n + 1)}>Reintentar modelo anatómico</button>}
      <div className="pointer-events-none absolute inset-x-3 bottom-3 flex flex-wrap items-center justify-between gap-2 text-xs text-blue-100">
        {zona ? <span className="flex items-center gap-2"><span className="h-3 w-3 rounded-full" style={{ background: COLORES[tono] }} />{NOMBRE_TIPO[tipo]} · ubicación aproximada</span> : <span>Sin lesión marcada</span>}
        <span className="hidden text-right sm:inline">Arrastra para girar · rueda o pellizco para acercar
          {estado === "anatomico" && <><br /><span className="opacity-70">Modelo: BodyParts3D © DBCLS (CC BY-SA 2.1 JP)</span></>}</span>
      </div>
    </div>
  );
}
