// Modelos 3D ilustrativos de los huesos, construidos con geometría (sin archivos externos).
// Cada hueso mide ALTO unidades a lo largo del eje Y: y = ALTO es el extremo superior
// (como aparece en la radiografía) e y = 0 el inferior.
import * as THREE from "three";
import { mergeVertices } from "three/examples/jsm/utils/BufferGeometryUtils.js";

export const ALTO = 10;
type P = [number, number]; // [radio, altura]
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

/** Superficie de revolución suave a partir de un perfil (radio según la altura). */
function torno(perfil: P[], escalaZ = 0.85, segmentos = 56) {
  const curva = new THREE.SplineCurve(perfil.map(([r, y]) => new THREE.Vector2(r, y)));
  const puntos = curva.getPoints(140).map((p) => new THREE.Vector2(Math.max(p.x, 0.001), p.y));
  puntos[0].x = 0; puntos[puntos.length - 1].x = 0;
  const g = new THREE.LatheGeometry(puntos, segmentos);
  g.scale(1, 1, escalaZ);
  return g;
}

/** Abultamiento (elipsoide), para cóndilos, tuberosidades, cabezas, etc. */
function bulto(r: number, pos: [number, number, number], esc: [number, number, number] = [1, 1, 1]) {
  const g = new THREE.SphereGeometry(r, 40, 28);
  g.scale(...esc); g.translate(...pos);
  return g;
}

/** Cilindro que va de un punto a otro (cuellos, apófisis). */
function puente(r1: number, r2: number, desde: THREE.Vector3, hasta: THREE.Vector3) {
  const dir = hasta.clone().sub(desde);
  const g = new THREE.CylinderGeometry(r2, r1, dir.length(), 32, 1, true);
  g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(V(0, 1, 0), dir.normalize()));
  const medio = desde.clone().add(hasta).multiplyScalar(0.5);
  g.translate(medio.x, medio.y, medio.z);
  return g;
}

/** Hueso corto (metacarpiano, falange…) a lo largo de una dirección. */
function segmento(largo: number, r: number, base: [number, number], angulo: number) {
  const g = torno([[0, 0], [r * 1.45, largo * 0.06], [r * 1.25, largo * 0.2], [r, largo * 0.4], [r * 0.95, largo * 0.62],
    [r * 1.15, largo * 0.84], [r * 1.3, largo * 0.95], [0, largo]], 0.8, 28);
  g.rotateZ(-angulo); g.translate(base[0], base[1], 0);
  return g;
}

/** Rayos de la mano o del pie: metacarpianos/metatarsianos y falanges, con los dedos hacia arriba. */
function rayos(cfg: { y0: number; separacion: number; abanico: number; largos: number[][]; radio: number; pulgar: number }) {
  const geos: THREE.BufferGeometry[] = [];
  cfg.largos.forEach((partes, i) => {
    const esPulgar = i === 0;
    const a = esPulgar ? cfg.pulgar : (i - 2.5) * cfg.abanico;
    let x = (i - 2) * cfg.separacion + (esPulgar ? -0.35 : 0);
    let y = cfg.y0 - (esPulgar ? 0.6 : 0);
    partes.forEach((largo, k) => {
      const r = cfg.radio * (k === 0 ? 1 : 0.85 - k * 0.07);
      geos.push(segmento(largo, r, [x, y], a));
      x += Math.sin(a) * (largo + 0.08); y += Math.cos(a) * (largo + 0.08);
    });
  });
  return geos;
}

export function geometriasHueso(hueso: string): THREE.BufferGeometry[] | null {
  switch (hueso) {
    case "femur":
      return [
        torno([[0, 0], [1.0, 0.12], [1.25, 0.55], [1.15, 1.2], [0.78, 2.0], [0.5, 3.0], [0.43, 5.0], [0.46, 7.0], [0.56, 8.1],
          [0.72, 8.8], [0.78, 9.25], [0.52, 9.6], [0, 9.68]]),
        bulto(0.62, [0.55, 0.55, -0.12], [0.9, 1, 1.3]), bulto(0.62, [-0.55, 0.55, -0.12], [0.9, 1, 1.3]),
        puente(0.42, 0.34, V(0.2, 8.85, 0), V(1.3, 9.55, 0.12)),
        bulto(0.64, [1.45, 9.68, 0.15]),
        bulto(0.48, [-0.5, 9.25, -0.05], [0.8, 1.35, 0.9]),
        bulto(0.2, [0.38, 8.2, -0.22]),
      ];
    case "tibia":
      return [
        torno([[0, 0], [0.58, 0.08], [0.64, 0.45], [0.5, 1.0], [0.42, 2.0], [0.4, 4.0], [0.46, 6.5], [0.62, 8.0], [0.98, 8.9],
          [1.28, 9.5], [1.32, 9.8], [0, 9.9]], 0.8),
        bulto(0.3, [0.42, 0.05, 0.05], [0.8, 1.7, 0.9]),
        bulto(0.32, [0, 8.6, 0.55], [1, 1.3, 0.7]),
        bulto(0.5, [0.55, 9.65, 0], [1.1, 0.45, 1.2]), bulto(0.5, [-0.55, 9.65, 0], [1.1, 0.45, 1.2]),
      ];
    case "perone":
      return [
        torno([[0, 0.2], [0.3, 0.3], [0.34, 0.8], [0.22, 1.6], [0.17, 5.0], [0.19, 8.6], [0.33, 9.2], [0.32, 9.5], [0, 9.6]], 0.85, 40),
        bulto(0.3, [0, 0.45, 0], [0.85, 1.4, 0.9]),
      ];
    case "humero":
      return [
        torno([[0, 0], [0.9, 0.1], [1.05, 0.4], [0.82, 0.9], [0.46, 1.8], [0.38, 3.0], [0.36, 5.5], [0.42, 7.5], [0.56, 8.6],
          [0.8, 9.15], [0.85, 9.45], [0, 9.6]]),
        bulto(0.3, [0.98, 0.55, 0], [1, 1.2, 0.9]), bulto(0.26, [-0.98, 0.55, 0], [1, 1.2, 0.9]),
        bulto(0.42, [0.35, 0.18, 0.12]), bulto(0.4, [-0.35, 0.18, 0.12], [1, 0.95, 1]),
        bulto(0.86, [0.45, 9.4, -0.2]),
        bulto(0.42, [-0.58, 9.3, 0.1], [0.9, 1.2, 0.9]),
      ];
    case "radio":
      return [
        torno([[0, 0], [0.62, 0.1], [0.64, 0.5], [0.46, 1.2], [0.28, 2.5], [0.22, 5.0], [0.2, 8.4], [0.27, 9.1], [0, 9.2]], 0.8, 44),
        puente(0.42, 0.42, V(0, 9.1, 0), V(0, 9.55, 0)), bulto(0.42, [0, 9.55, 0], [1, 0.12, 1]),
        bulto(0.18, [0.62, 0.1, 0], [1, 1.6, 1]),
      ];
    case "cubito":
      return [
        torno([[0, 0.1], [0.32, 0.18], [0.3, 0.7], [0.22, 2.0], [0.25, 6.0], [0.38, 8.6], [0.55, 9.2], [0.58, 9.5], [0, 9.7]], 0.85, 44),
        bulto(0.46, [0, 9.62, -0.35], [0.9, 1.3, 0.9]), bulto(0.26, [0, 8.95, 0.38], [1, 0.8, 1]),
        bulto(0.14, [0.2, 0.05, 0], [1, 1.8, 1]),
      ];
    case "mano":
      return [
        ...rayos({ y0: 3.2, separacion: 0.55, abanico: 0.07, radio: 0.2, pulgar: -0.55,
          largos: [[2.0, 1.5, 1.1], [3.0, 1.8, 1.1, 0.8], [3.1, 2.0, 1.25, 0.85], [2.9, 1.85, 1.15, 0.8], [2.6, 1.45, 0.9, 0.7]] }),
        bulto(0.36, [-0.85, 2.6, 0]), bulto(0.36, [-0.25, 2.7, 0]), bulto(0.36, [0.35, 2.7, 0]), bulto(0.34, [0.9, 2.6, 0]),
        bulto(0.4, [-0.65, 1.85, 0]), bulto(0.4, [0, 1.95, 0]), bulto(0.38, [0.62, 1.85, 0]),
        bulto(0.7, [-0.2, 0.75, 0], [1.4, 0.8, 0.8]),
      ];
    case "pie":
      return [
        ...rayos({ y0: 4.6, separacion: 0.58, abanico: 0.035, radio: 0.21, pulgar: -0.05,
          largos: [[2.7, 1.3, 1.0], [3.0, 1.0, 0.6, 0.5], [2.8, 0.9, 0.55, 0.45], [2.6, 0.85, 0.5, 0.45], [2.4, 0.8, 0.5, 0.4]] }),
        bulto(0.42, [-1.0, 4.1, 0]), bulto(0.42, [-0.35, 4.15, 0]), bulto(0.42, [0.3, 4.1, 0]), bulto(0.5, [1.0, 3.9, 0]),
        bulto(0.75, [-0.2, 3.0, 0.05], [1.3, 0.75, 0.8]),
        bulto(0.8, [0.1, 1.7, 0.2], [1.0, 1.1, 1.0]),
        bulto(0.95, [0.25, 0.6, -0.1], [0.95, 1.05, 1.0]),
      ];
    default:
      return null; // cadera: fuera del alcance del modelo 3D
  }
}

export type TipoLesion = "cavidad" | "crecimiento" | "mancha";
export type Zona = { posicion: number; extension: number; angulo?: number; tipo?: TipoLesion | null };

/** Deja la malla lista: une vértices repetidos (sin costuras al deformar) y guarda la forma original. */
export function preparar(geos: THREE.BufferGeometry[]) {
  return geos.map((g0) => {
    g0.deleteAttribute("uv");
    const g = mergeVertices(g0); g0.dispose();
    g.computeVertexNormals();
    g.userData.original = (g.getAttribute("position").array as Float32Array).slice();
    return g;
  });
}

// ruido suave y barato, para que los bordes de la lesión sean irregulares
const ruido = (x: number, y: number, z: number) =>
  (Math.sin(x * 4.1 + y * 1.7) + Math.sin(y * 3.3 - z * 2.9 + 1.3) + Math.sin(z * 4.7 + x * 2.3 + 0.7)) / 3;

/** Punto de la superficie donde está la lesión, dirección hacia afuera y grosor local del hueso. */
export function puntoLesion(geos: THREE.BufferGeometry[], zona: Zona) {
  const yc = ALTO * (1 - zona.posicion), th = ((zona.angulo ?? 0) * Math.PI) / 180;
  const dir = V(Math.sin(th), 0, Math.cos(th));
  // centro del hueso a esa altura
  let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity, n = 0;
  for (const g of geos) {
    const o = g.userData.original as Float32Array;
    for (let i = 0; i < o.length; i += 3) if (Math.abs(o[i + 1] - yc) < 0.18) {
      n++; minX = Math.min(minX, o[i]); maxX = Math.max(maxX, o[i]); minZ = Math.min(minZ, o[i + 2]); maxZ = Math.max(maxZ, o[i + 2]);
    }
  }
  const centro = n ? V((minX + maxX) / 2, yc, (minZ + maxZ) / 2) : V(0, yc, 0);
  // el punto más saliente hacia la dirección elegida
  let mejor = -Infinity; const p = centro.clone();
  for (const g of geos) {
    const o = g.userData.original as Float32Array;
    for (let i = 0; i < o.length; i += 3) {
      if (Math.abs(o[i + 1] - yc) > 0.18) continue;
      const proy = (o[i] - centro.x) * dir.x + (o[i + 2] - centro.z) * dir.z;
      if (proy > mejor) { mejor = proy; p.set(o[i], o[i + 1], o[i + 2]); }
    }
  }
  return { punto: p, centro, dir, radio: Math.max(mejor, 0.15) };
}

/**
 * Dibuja la lesión SOLO en su sitio:
 *  - cavidad: hunde la superficie (lesión lítica, el hueso se ve "comido" o hueco)
 *  - crecimiento: levanta la superficie (lesión que crece hacia afuera)
 *  - mancha: solo color
 */
export function aplicarLesion(geos: THREE.BufferGeometry[], zona: Zona | null, color: string, tipo: TipoLesion) {
  const base = new THREE.Color("#ece5d3"), lesion = new THREE.Color(color), oscuro = new THREE.Color("#2a0a0a"), c = new THREE.Color();
  const L = zona ? puntoLesion(geos, zona) : null;
  const rv = zona ? Math.max((zona.extension * ALTO) / 2, 0.18) : 1;
  const rh = L ? Math.min(Math.max(rv * 0.8, 0.18), L.radio * 1.15) : 1;
  for (const g of geos) {
    const o = g.userData.original as Float32Array;
    const pos = g.getAttribute("position") as THREE.BufferAttribute;
    let col = g.getAttribute("color") as THREE.BufferAttribute | undefined;
    if (!col) { col = new THREE.BufferAttribute(new Float32Array(pos.count * 3), 3); g.setAttribute("color", col); }
    (pos.array as Float32Array).set(o);
    for (let i = 0; i < pos.count; i++) {
      const x = o[i * 3], y = o[i * 3 + 1], z = o[i * 3 + 2];
      let w = 0, hx = 0, hz = 0;
      if (L) {
        hx = x - L.centro.x; hz = z - L.centro.z;
        const hl = Math.hypot(hx, hz) || 1; hx /= hl; hz /= hl;
        const cara = Math.min(1, Math.max(0, ((hx * L.dir.x + hz * L.dir.z) - 0.05) / 0.45)); // solo la cara elegida
        const dx = x - L.punto.x, dy = y - L.punto.y, dz = z - L.punto.z;
        const d = Math.sqrt((dx * dx + dz * dz) / (rh * rh) + (dy * dy) / (rv * rv)) * (1 + 0.28 * ruido(x * 2, y * 2, z * 2));
        w = Math.max(0, 1 - d); w = w * w * (3 - 2 * w) * cara;
      }
      if (w > 0 && L && tipo !== "mancha") {
        const r2 = 0.8 + 0.4 * (0.5 + 0.5 * ruido(x * 5 + 3, y * 5, z * 5));
        const desp = tipo === "cavidad" ? -L.radio * 0.78 * w * r2 : L.radio * 0.95 * w * r2;
        pos.setXYZ(i, x + hx * desp, y, z + hz * desp);
      }
      const marca = Math.min(1, w * 3.5);
      c.copy(base).lerp(lesion, marca * 0.95);
      if (tipo === "cavidad") c.lerp(oscuro, Math.pow(w, 1.4) * 0.75);
      col.setXYZ(i, c.r, c.g, c.b);
    }
    pos.needsUpdate = true; col.needsUpdate = true;
    g.computeVertexNormals();
  }
  return L;
}
