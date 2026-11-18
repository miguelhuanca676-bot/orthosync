// Validación del modelo (para la tesis y para el médico) y controles programados (para la agenda de la clínica).
import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, fecha, pct } from "../api";
import { Cargando, Encabezado, Enlace, Mensaje, useDatos, useSesion, Vacio } from "../componentes";

// ---------------------------------------------------------------- piezas
function Cifra({ nombre, valor, nota }: { nombre: string; valor: string; nota?: string }) {
  return (
    <div className="rounded-lg border border-linea bg-superficie/50 px-4 py-3">
      <p className="text-[13px] text-suave">{nombre}</p>
      <p className="mt-0.5 text-2xl font-semibold tracking-tight text-fuerte">{valor}</p>
      {nota && <p className="mt-0.5 text-xs text-suave">{nota}</p>}
    </div>
  );
}

/** Matriz de confusión: filas = referencia, columnas = predicción. */
function Matriz({ filas, columnas, valores, referencia, prediccion }: { filas: string[]; columnas: string[]; valores: number[][]; referencia: string; prediccion: string }) {
  const max = Math.max(1, ...valores.flat());
  return (
    <div className="overflow-x-auto">
      <table className="text-sm">
        <caption className="sr-only">Matriz de confusión: {referencia} contra {prediccion}</caption>
        <thead>
          <tr><th />{columnas.map((c) => <th key={c} scope="col" className="px-2 pb-1.5 text-center text-xs font-medium text-suave">{c}</th>)}</tr>
        </thead>
        <tbody>
          {filas.map((f, i) => (
            <tr key={f}>
              <th scope="row" className="pr-3 text-right text-xs font-medium text-suave">{f}</th>
              {valores[i].map((v, j) => {
                const t = v / max;
                return (
                  <td key={j} className="p-0.5">
                    <div className={`flex h-14 w-20 items-center justify-center rounded-md text-base font-semibold ${i === j ? "ring-1 ring-azul/30" : ""}`}
                      style={{ background: `rgba(31,95,214,${0.08 + t * 0.72})`, color: t > 0.5 ? "#fff" : "var(--color-fuerte)" }}>{v}</div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-suave">Filas: {referencia}. Columnas: {prediccion}. La diagonal son los aciertos.</p>
    </div>
  );
}

const desdeBinaria = (m: any) => [[m.VN, m.FP], [m.FN, m.VP]];

/** Interpretación del kappa de Cohen (Landis y Koch, 1977). */
const leerKappa = (k: number | null) => k == null ? "sin datos" : k < 0 ? "peor que el azar" : k < 0.21 ? "leve" : k < 0.41 ? "aceptable" : k < 0.61 ? "moderado" : k < 0.81 ? "sustancial" : "casi perfecto";

function CurvaRoc({ curvas }: { curvas: Record<string, [number, number][]> }) {
  const colores = ["#1f5fd6", "#7c4ddb", "#5cc8f5"];
  const nombres = Object.keys(curvas);
  return (
    <div>
      <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart margin={{ top: 8, right: 16, bottom: 18, left: 0 }}>
          <CartesianGrid stroke="var(--color-linea)" />
          <XAxis type="number" dataKey="x" domain={[0, 1]} tickCount={6} tick={{ fontSize: 12, fill: "#7a8aa8" }} label={{ value: "1 − especificidad", position: "insideBottom", offset: -10, fontSize: 12, fill: "#7a8aa8" }} />
          <YAxis type="number" dataKey="y" domain={[0, 1]} tickCount={6} tick={{ fontSize: 12, fill: "#7a8aa8" }} width={40} />
          <Tooltip formatter={(v: any) => Number(v).toFixed(2)} labelFormatter={(v: any) => `1 − esp.: ${Number(v).toFixed(2)}`} />
          <Line data={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} dataKey="y" stroke="#94a3b8" strokeDasharray="4 4" dot={false} isAnimationActive={false} name="Azar" />
          {nombres.map((n, i) => (
            <Line key={n} data={curvas[n].map(([x, y]) => ({ x, y }))} dataKey="y" name={n} stroke={colores[i % 3]} strokeWidth={2.5} dot={false} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
      </div>
      <ul className="mt-3 flex flex-wrap gap-4 text-xs text-suave">
        {nombres.map((n, i) => <li key={n} className="flex items-center gap-1.5"><span className="h-0.5 w-5 rounded" style={{ background: colores[i % 3] }} />{n}</li>)}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------- validación
export function Validacion() {
  const { usuario } = useSesion();
  const { datos: v, error } = useDatos("/validacion");
  const [exportando, setExportando] = useState(false); const [msg, setMsg] = useState("");
  if (error) return <Mensaje>{error}</Mensaje>;
  if (!v) return <Cargando />;
  const p = v.prueba ?? {};
  const e1 = p.etapa1_normal_vs_lesion, e3 = p.etapa3_benigno_vs_maligno, s3 = p.sistema_completo_3_clases, det = p.etapa2_detector ?? v.detector;
  const real = v.uso_real;
  const exportar = async () => {
    setMsg(""); setExportando(true);
    try { await api.descargar("/correcciones/exportar", `orthosync_casos_${new Date().toISOString().slice(0, 10)}.zip`); }
    catch (x: any) { setMsg(x.message); } finally { setExportando(false); }
  };
  return (
    <>
      <Encabezado titulo="Validación del modelo" detalle="Qué tan bien funciona el sistema, medido con imágenes que nunca vio y con las valoraciones de los médicos de la clínica" />
      <div className="grid items-start gap-6 2xl:grid-cols-2">
        <section className="tarjeta" aria-labelledby="t-prueba">
          <h2 id="t-prueba" className="subtitulo">En el conjunto de prueba</h2>
          <p className="mt-0.5 text-[13px] text-suave">Radiografías de BTXRD separadas antes de entrenar. El modelo no las vio nunca.</p>
          {!e1 ? (
            <div className="mt-4"><Mensaje tipo="info">Los modelos instalados no traen métricas de prueba. Vuelve a ejecutar el cuaderno de Kaggle y copia la carpeta <strong>modelos/servidor</strong> completa.</Mensaje></div>
          ) : (
            <div className="mt-4 space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-fuerte">Etapa 1: normal o con lesión</h3>
                <div className="mt-2 grid gap-3 sm:grid-cols-4">
                  <Cifra nombre="AUC" valor={e1.auc.toFixed(3).replace(".", ",")} nota={e1.auc_ic95?.[0] != null ? `IC 95 %: ${e1.auc_ic95[0].toFixed(2)}–${e1.auc_ic95[1].toFixed(2)}`.replace(/\./g, ",") : undefined} />
                  <Cifra nombre="Sensibilidad" valor={pct(e1.sensibilidad, 1)} nota="lesiones detectadas" />
                  <Cifra nombre="Especificidad" valor={pct(e1.especificidad, 1)} nota="normales bien descartadas" />
                  <Cifra nombre="Imágenes" valor={String(e1.n)} nota={`${e1.positivos} con lesión`} />
                </div>
                <div className="mt-4"><Matriz filas={["Normal", "Lesión"]} columnas={["Normal", "Lesión"]} valores={desdeBinaria(e1.matriz)} referencia="diagnóstico real" prediccion="lo que dijo el sistema" /></div>
              </div>
              {e3 && (
                <div>
                  <h3 className="text-sm font-semibold text-fuerte">Etapa 3: benigno o maligno</h3>
                  <div className="mt-2 grid gap-3 sm:grid-cols-4">
                    <Cifra nombre="AUC" valor={e3.auc.toFixed(3).replace(".", ",")} />
                    <Cifra nombre="Sensibilidad" valor={pct(e3.sensibilidad, 1)} nota="malignos detectados" />
                    <Cifra nombre="Especificidad" valor={pct(e3.especificidad, 1)} />
                    <Cifra nombre="Lesiones" valor={String(e3.n)} nota={`${e3.positivos} malignas`} />
                  </div>
                  <div className="mt-4"><Matriz filas={["Benigno", "Maligno"]} columnas={["Benigno", "Maligno"]} valores={desdeBinaria(e3.matriz)} referencia="diagnóstico real" prediccion="lo que dijo el sistema" /></div>
                </div>
              )}
              {p.curvas_roc && <div><h3 className="mb-2 text-sm font-semibold text-fuerte">Curvas ROC</h3><CurvaRoc curvas={p.curvas_roc} /></div>}
              {s3 && (
                <div>
                  <h3 className="text-sm font-semibold text-fuerte">Sistema completo (lo que ve el médico)</h3>
                  <p className="mt-0.5 text-[13px] text-suave">Exactitud {pct(s3.exactitud, 1)} en tres clases.</p>
                  <div className="mt-3"><Matriz filas={["Normal", "Benigno", "Maligno"]} columnas={["Normal", "Benigno", "Maligno"]} valores={s3.matriz} referencia="diagnóstico real" prediccion="lo que dijo el sistema" /></div>
                </div>
              )}
              {det && (
                <div>
                  <h3 className="text-sm font-semibold text-fuerte">Etapa 2: ubicación de la lesión (detector)</h3>
                  <div className="mt-2 grid gap-3 sm:grid-cols-4">
                    <Cifra nombre="mAP50" valor={pct(det.mAP50, 1)} nota="recuadros que coinciden" />
                    <Cifra nombre="Precisión" valor={pct(det.precision, 1)} />
                    <Cifra nombre="Sensibilidad" valor={pct(det.sensibilidad, 1)} />
                    <Cifra nombre="mAP50-95" valor={pct(det.mAP50_95, 1)} nota="exigencia alta" />
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="tarjeta" aria-labelledby="t-real">
          <h2 id="t-real" className="subtitulo">En uso real en la clínica</h2>
          <p className="mt-0.5 text-[13px] text-suave">Compara lo que dijo el sistema con la opinión del traumatólogo en los estudios ya valorados.</p>
          {real.lesion.n === 0 ? (
            <div className="mt-4"><Vacio titulo="Aún no hay estudios valorados">Cuando los médicos valoren estudios analizados, aquí verás cuánto coincide el sistema con ellos.</Vacio></div>
          ) : (
            <div className="mt-4 space-y-6">
              <div className="grid gap-3 sm:grid-cols-4">
                <Cifra nombre="Acuerdo" valor={pct(real.lesion.acuerdo, 1)} nota={`${real.lesion.n} estudios`} />
                <Cifra nombre="Kappa de Cohen" valor={real.lesion.kappa == null ? "—" : real.lesion.kappa.toFixed(2).replace(".", ",")} nota={`acuerdo ${leerKappa(real.lesion.kappa)}`} />
                <Cifra nombre="Sensibilidad" valor={pct(real.lesion.sensibilidad, 1)} nota="frente al médico" />
                <Cifra nombre="Especificidad" valor={pct(real.lesion.especificidad, 1)} nota="frente al médico" />
              </div>
              <Matriz filas={["Normal", "Lesión"]} columnas={["Normal", "Lesión"]} valores={desdeBinaria(real.lesion.matriz)} referencia="opinión del médico" prediccion="lo que dijo el sistema" />
              {real.malignidad.n > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-fuerte">Benigno o maligno</h3>
                  <p className="mt-0.5 text-[13px] text-suave">Acuerdo {pct(real.malignidad.acuerdo, 1)} en {real.malignidad.n} lesiones; kappa {real.malignidad.kappa == null ? "—" : real.malignidad.kappa.toFixed(2).replace(".", ",")} ({leerKappa(real.malignidad.kappa)}).</p>
                </div>
              )}
              {real.por_mes.length >= 2 && (
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-fuerte">Acuerdo por mes</h3>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={real.por_mes.map((m: any) => ({ mes: m.mes, acuerdo: +(m.acuerdo * 100).toFixed(1), n: m.n }))} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                        <CartesianGrid stroke="var(--color-linea)" vertical={false} />
                        <XAxis dataKey="mes" tick={{ fontSize: 12, fill: "#7a8aa8" }} axisLine={false} tickLine={false} />
                        <YAxis domain={[0, 100]} unit=" %" tick={{ fontSize: 12, fill: "#7a8aa8" }} width={50} axisLine={false} tickLine={false} />
                        <Tooltip formatter={(v: any, _n: any, x: any) => [`${v} % (${x.payload.n} estudios)`, "Acuerdo"]} />
                        <Line dataKey="acuerdo" stroke="#1f5fd6" strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
              <p className="text-xs leading-relaxed text-suave">Kappa mide el acuerdo descontando el que ocurriría por azar: menos de 0,40 es bajo, entre 0,41 y 0,60 moderado, entre 0,61 y 0,80 sustancial y más de 0,80 casi perfecto (Landis y Koch). La opinión del médico no es la biopsia: es una referencia clínica, no la verdad definitiva.</p>
            </div>
          )}
          <div className="mt-6 rounded-xl border border-linea bg-superficie/50 p-4">
            <h3 className="text-sm font-semibold text-fuerte">Casos para mejorar el modelo</h3>
            <p className="mt-1 text-[13px] leading-relaxed text-suave">
              {real.corregidos} {real.corregidos === 1 ? "estudio tiene" : "estudios tienen"} la zona corregida por el médico.
              {usuario?.rol === "traumatologo" ? " Exporta los estudios valorados (sin nombres ni documentos) y súbelos a Kaggle para reentrenar con ellos." : " Solo el traumatólogo puede exportarlos, porque contienen radiografías."}
            </p>
            {msg && <div className="mt-3"><Mensaje>{msg}</Mensaje></div>}
            {usuario?.rol === "traumatologo" && <button className="boton-claro mt-3" disabled={exportando} onClick={exportar}>{exportando ? "Preparando…" : "Exportar casos valorados (ZIP)"}</button>}
          </div>
        </section>
      </div>
    </>
  );
}

// ---------------------------------------------------------------- controles programados
export function Controles() {
  const { datos, error } = useDatos<any[]>("/controles");
  const [filtro, setFiltro] = useState<"vencidos" | "proximos" | "todos">("proximos");
  if (error) return <Mensaje>{error}</Mensaje>;
  if (!datos) return <Cargando />;
  const vencidos = datos.filter((c) => c.dias < 0), proximos = datos.filter((c) => c.dias >= 0 && c.dias <= 30);
  const lista = filtro === "vencidos" ? vencidos : filtro === "proximos" ? proximos : datos;
  const estado = (d: number) => d < 0 ? <span className="chip bg-red-50 text-red-700">Vencido hace {-d} {d === -1 ? "día" : "días"}</span>
    : d === 0 ? <span className="chip bg-amber-50 text-amber-800">Hoy</span>
    : d <= 7 ? <span className="chip bg-amber-50 text-amber-800">En {d} {d === 1 ? "día" : "días"}</span>
    : <span className="chip bg-cielo text-marino">En {d} días</span>;
  const FILTROS: [typeof filtro, string, number][] = [["proximos", "Próximos 30 días", proximos.length], ["vencidos", "Vencidos", vencidos.length], ["todos", "Todos", datos.length]];
  return (
    <>
      <Encabezado titulo="Controles" detalle="Pacientes con una cita de control indicada por su médico" />
      <div role="group" aria-label="Filtrar" className="mb-4 inline-flex gap-1 rounded-lg border border-linea bg-panel p-1">
        {FILTROS.map(([k, n, c]) => (
          <button key={k} aria-pressed={filtro === k} onClick={() => setFiltro(k)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${filtro === k ? "bg-noche text-white" : "text-suave hover:bg-cielo"}`}>{n} <span className={filtro === k ? "text-sky-200" : "text-slate-400"}>{c}</span></button>
        ))}
      </div>
      {lista.length === 0 ? <div className="tarjeta"><Vacio titulo={filtro === "vencidos" ? "No hay controles vencidos" : "No hay controles en este periodo"}>Los controles aparecen cuando el médico indica la fecha al valorar un estudio.</Vacio></div> : (
        <div className="overflow-hidden rounded-xl border border-linea bg-panel">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-linea bg-superficie/60 text-[13px] text-suave">
              <tr><th className="px-4 py-2.5 font-medium">Paciente</th><th className="px-4 py-2.5 font-medium">Fecha del control</th><th className="px-4 py-2.5 font-medium">Estado</th>
                <th className="hidden px-4 py-2.5 font-medium md:table-cell">Último estudio</th><th className="hidden px-4 py-2.5 font-medium sm:table-cell">Teléfono</th></tr>
            </thead>
            <tbody className="divide-y divide-linea">
              {lista.map((c) => (
                <tr key={c.paciente_id}>
                  <td className="px-4 py-3"><Enlace a={`/pacientes/${c.paciente_id}`} className="font-medium text-fuerte hover:text-azul">{c.nombre}</Enlace><span className="block text-xs text-suave">{c.codigo}</span></td>
                  <td className="px-4 py-3 font-medium">{fecha(c.fecha_control)}</td>
                  <td className="px-4 py-3">{estado(c.dias)}</td>
                  <td className="hidden px-4 py-3 text-suave md:table-cell">{fecha(c.ultimo_estudio)}</td>
                  <td className="hidden px-4 py-3 text-suave sm:table-cell">{c.telefono ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
