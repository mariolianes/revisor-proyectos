import { useState } from "react"

import { Observacion } from "../componentes/Observacion"
import type { EstadoDeLaDecision } from "../componentes/Observacion"
import { api } from "../lib/api"
import { CODIGOS_SEMAFORO } from "../lib/tipos"
import type { Decision, ResultadoAnalisis, ValoracionVerificada } from "../lib/tipos"

// La misma severidad que `SEVERIDAD_SEMAFORO` en
// `backend/salidas/informe.py`: GRIS por debajo de VERDE a propósito, para
// que la comprobación de aquí -de anticipo, no la que de verdad decide- dé
// el mismo resultado que dará el servidor al guardar. Ver D-016 en
// `docs/decisions.md`.
const SEVERIDAD_SEMAFORO: Record<string, number> = { GRIS: -1, VERDE: 0, AMBAR: 1, ROJO: 2 }

/**
 * El color mínimo que sostienen las valoraciones fiables que siguen
 * aprobadas -mismo cálculo que `semaforo_por_valoraciones`
 * (`backend/salidas/informe.py`)-, para poder avisar en pantalla antes de
 * que el docente intente guardar un semáforo final que el servidor va a
 * rechazar. No sustituye esa comprobación: es un anticipo, calculado con la
 * misma regla, sobre las decisiones que esta pantalla tiene delante ahora
 * mismo.
 */
function colorMinimo(
  valoraciones: ValoracionVerificada[],
  estadoDe: (v: ValoracionVerificada) => EstadoDeLaDecision,
): string {
  const fiables = valoraciones.filter(
    (v) => v.evidencia_localizada && estadoDe(v).decision !== "DESCARTADA",
  )
  if (fiables.length === 0) return "GRIS"
  for (const prioridad of ["P1", "P2", "P3"]) {
    if (fiables.some((v) => v.prioridad === prioridad)) {
      return prioridad === "P1" ? "ROJO" : "AMBAR"
    }
  }
  return "VERDE"
}

interface Props {
  id: string
  /**
   * Lo que devolvió `POST /entregas/{id}/analisis`, ya en la máquina: esta
   * pantalla no vuelve a pedirlo. Un segundo análisis cuesta dinero otra
   * vez y puede dar un juicio distinto del que el docente lleva un rato
   * revisando -el mismo motivo por el que `Ficha` no repite `GET ficha`
   * cuando ya trae los datos de confirmar.
   */
  inicial: ResultadoAnalisis
  alVolver: () => void
}

const estadoDeSalida = (v: ValoracionVerificada): EstadoDeLaDecision => (
  { decision: "ACEPTADA", texto: v.observacion }
)

/**
 * Donde el docente revisa el análisis observación por observación y decide
 * qué pasa a la devolución. La última pantalla del flujo: todo lo demás en
 * este sistema propone y se detiene aquí.
 *
 * Cinco cosas de fondo, no de estilo:
 *
 * 1. Qué está verificado y qué no. `Observacion` marca con `senal` la que
 *    tiene la cita sin localizar; aquí se hace lo mismo con las dudas del
 *    motor y los indicios de autoría (§13: son un indicio, no un veredicto,
 *    la decisión es del docente). Las fortalezas siguen la misma regla que
 *    las observaciones: llevan su cita y, si no se localizó, la señal -al
 *    alumno no le llega ninguna fortaleza sin localizar (`componer()` la
 *    filtra en `backend/salidas/borrador.py`), pero aquí el docente ve el
 *    análisis entero, y es él quien tiene que poder distinguirlas.
 * 2. Los reparos y las dimensiones ausentes son consulta, no acción: nadie
 *    decide nada sobre ellos desde esta pantalla, así que van en secciones
 *    plegables, igual que el resto de dimensiones evaluadas. Un reparo
 *    (`Informe.reparos`) es la constancia de lo que el motor devolvió y el
 *    sistema no dio por bueno -dimensión repetida, dimensión inactiva en
 *    la fase, evidencia no localizada, un indicio redactado como
 *    veredicto-; sin ellos el docente no puede distinguir lo que dijo el
 *    motor de lo que este sistema le está dando por bueno. Una dimensión
 *    ausente (`Informe.dimensiones_ausentes`) es una dimensión activa en
 *    la fase que el motor no llegó a valorar -no es que esté correcta, es
 *    que nadie la ha mirado todavía, y eso le toca a él.
 * 3. El borrador es texto libre y, además, es viejo. Se ha comprobado que
 *    no viola ninguna regla dura -nada de notas, nada de autoría, nada sin
 *    evidencia-, pero no que cada frase corresponda exactamente a una
 *    prioridad, y tampoco refleja las decisiones que se toman en esta
 *    misma pantalla: lo compuso el motor a partir del análisis original,
 *    antes de que el docente aceptara, editara o descartara nada. Volver a
 *    pedirlo cuesta dinero y reenvía el trabajo del alumno, así que este
 *    aviso no regenera el texto: dice la verdad sobre él. Lo que sí puede
 *    afirmar con certeza es un recuento, no una identidad: `componer()`
 *    (`backend/salidas/borrador.py`) no escribe más de una acción por
 *    prioridad con evidencia localizada, así que si el borrador trae más
 *    acciones que prioridades siguen vivas ahora mismo -contando
 *    `informe.prioridades` tal como llega a esta pantalla, ya sea de un
 *    análisis recién hecho o de una revisión ya guardada, más lo que el
 *    docente acaba de descartar aquí sin guardar todavía- sobra, con toda
 *    certeza, al menos esa diferencia. Qué acción concreta sobra y de qué
 *    prioridad era es una pregunta distinta, y esta pantalla no la
 *    contesta: contestarla se apoyaría en que el motor haya devuelto las
 *    acciones en el mismo orden en que se le pidieron, una por prioridad,
 *    y eso no lo comprueba nadie -es texto libre del mismo motor del que
 *    este sistema desconfía en todo lo demás-. Nombrar una dimensión
 *    concreta sería afirmar más de lo que se sabe; contar cuántas sobran
 *    no lo es, y por eso el aviso solo hace lo segundo, con `senal`: es lo
 *    único de este bloque que de verdad espera que el docente revise el
 *    borrador entero antes de usarlo.
 * 4. Informe válido, borrador fallido no es un error. Cuando
 *    `resultado.devolucion` es `null`, `resultado.aviso` ya trae la
 *    explicación completa compuesta por el backend; esta pantalla no la
 *    repite ni la presenta como un fallo, y el informe se sigue pudiendo
 *    revisar entero.
 * 5. La tinta de señal se reserva. Solo marca lo que de verdad espera una
 *    decisión del docente -cita sin localizar, indicio de autoría, duda
 *    del motor, la discrepancia real del borrador-; los bloques plegables
 *    del punto 2 son consulta y van sin ella, para que no se convierta en
 *    decoración que deja de leerse.
 *
 * Desde la decisión del docente del 2026-08-30 (D-015, D-016, D-017 en
 * `docs/decisions.md`) hay tres controles nuevos, y los tres siguen la
 * misma frontera de siempre: lo que aquí se decide es interno, nunca llega
 * al alumno, y ninguno lo propone el motor.
 *
 * - El semáforo propuesto se sigue leyendo, no editando -no hay `<select>`
 *   a su lado-: es la prueba de auditoría de lo que el sistema propuso.
 *   Aparte, y solo aparte, hay un semáforo final que el docente sí elige:
 *   ninguno de los dos puede confundirse con el otro con solo mirar.
 * - La nota interna solo enseña un control cuando hay algo que decidir
 *   -`estado_nota` en `propuesta`, `modificada` o `aprobada`-; mientras siga
 *   `pendiente_de_rubrica` o `no_aplicable`, la pantalla lo dice con texto,
 *   sin ningún campo que invite a escribir un número que no existe.
 * - La síntesis provisional es la única prosa larga de esta pantalla que el
 *   docente edita directamente, y por eso lleva su propio rótulo -«síntesis
 *   provisional para revisión docente»- en vez de darse por cerrada.
 */
export function Revision({ id, inicial, alVolver }: Props) {
  const [resultado, setResultado] = useState(inicial)
  const [estados, setEstados] = useState<Record<string, EstadoDeLaDecision>>(() => {
    const estadoInicial: Record<string, EstadoDeLaDecision> = {}
    for (const v of resultado.informe.valoraciones) {
      estadoInicial[v.dimension] = estadoDeSalida(v)
    }
    return estadoInicial
  })
  const [guardando, setGuardando] = useState(false)
  const [guardado, setGuardado] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Los tres controles nuevos de D-015, D-016 y D-017: cada uno empieza con
  // lo último que guardó el servidor -o lo que compuso el análisis, la
  // primera vez-, y viaja entero en cada `guardar()`, tal como ya viaja
  // `decisiones`.
  const [semaforoFinal, setSemaforoFinal] = useState<string | null>(
    inicial.informe.semaforo_final_docente,
  )
  const [notaFinal, setNotaFinal] = useState<string>(
    inicial.informe.nota_final_docente != null ? String(inicial.informe.nota_final_docente) : "",
  )
  const [motivoNota, setMotivoNota] = useState<string>(
    inicial.informe.motivo_modificacion_nota ?? "",
  )
  const [sintesis, setSintesis] = useState<string>(inicial.informe.sintesis_provisional)

  const { informe, devolucion } = resultado
  const motorSimulado = resultado.motor === "simulado"

  const estadoDe = (v: ValoracionVerificada) => estados[v.dimension] ?? estadoDeSalida(v)

  const cambiar = (v: ValoracionVerificada, estado: EstadoDeLaDecision) => {
    setEstados({ ...estados, [v.dimension]: estado })
    // El resultado guardado del envío anterior deja de ser cierto en
    // cuanto se toca una decisión: si se queda, la pantalla diría
    // "guardado" sobre unas decisiones que ya no son las guardadas.
    setGuardado(false)
  }

  // El color mínimo que sostienen, ahora mismo, las observaciones fiables
  // que siguen aprobadas -recalculado en cada render, con las mismas
  // decisiones que ya gobiernan `prioridadesVivas` más abajo-. Sirve solo
  // para avisar antes de guardar: la comprobación real, la que de verdad
  // decide, la hace `revisar()` en el servidor.
  const colorMinimoActual = colorMinimo(informe.valoraciones, estadoDe)
  const semaforoFinalIncompatible = (
    semaforoFinal !== null
    && SEVERIDAD_SEMAFORO[semaforoFinal] < SEVERIDAD_SEMAFORO[colorMinimoActual]
  )
  const semaforoFinalDesactualizado = (
    semaforoFinal !== null
    && semaforoFinal !== colorMinimoActual
    && !semaforoFinalIncompatible
  )

  const estadosConNota = new Set(["propuesta", "modificada", "aprobada"])
  const hayNotaQueDecidir = estadosConNota.has(informe.estado_nota)
  const notaFinalNumero = notaFinal.trim() === "" ? null : Number(notaFinal)

  const dimsPrioridad = new Set(informe.prioridades.map((v) => v.dimension))
  const dimsFueraDelLimite = new Set(informe.prioridades_descartadas.map((v) => v.dimension))
  const resto = informe.valoraciones.filter(
    (v) => !dimsPrioridad.has(v.dimension) && !dimsFueraDelLimite.has(v.dimension),
  )

  // La vista previa de qué llega al alumno con las decisiones actuales,
  // antes de guardar nada: descartar una prioridad la quita de aquí al
  // momento, aunque su tarjeta -más abajo, con el resto de observaciones-
  // se quede donde estaba para poder volver a aceptarla.
  const prioridadesVivas = informe.prioridades.filter(
    (v) => estadoDe(v).decision !== "DESCARTADA",
  )

  // Cuántas prioridades con evidencia localizada siguen vivas AHORA MISMO,
  // en el informe que esta pantalla tiene delante -da igual si viene de un
  // análisis recién hecho o de una revisión ya guardada-. `prioridadesVivas`
  // ya cubre las dos fuentes de descarte: lo que el docente descartó en una
  // revisión anterior y ya se guardó -`revisar()` en
  // `backend/api/analisis.py` quita esas dimensiones de
  // `informe.prioridades` para siempre, no las deja ahí marcadas- y lo que
  // acaba de descartar aquí mismo, sin guardar todavía (`estadoDe`).
  const prioridadesVivasConEvidencia = prioridadesVivas.filter(
    (v) => v.evidencia_localizada,
  )
  // No se compara identidad, se compara recuento: `componer()`
  // (`backend/salidas/borrador.py`) pide como mucho una acción por
  // prioridad con evidencia localizada, así que `devolucion.acciones.length`
  // nunca puede superar el número de prioridades-con-evidencia que había en
  // el momento de componer el texto. Si ese número, hoy, con las
  // prioridades vivas que quedan, es menor que `devolucion.acciones.length`,
  // sobra al menos esa diferencia de acciones -con toda certeza, sin
  // suponer en qué orden las escribió el motor ni a cuál de ellas
  // corresponde cada una-. Emparejar cada acción con su prioridad exigiría
  // fiarse de que el motor las devolvió una por prioridad y en el mismo
  // orden en que se le pidieron, y eso no lo comprueba nadie: por eso el
  // aviso cuenta, no nombra.
  const accionesSobrantes = devolucion
    ? Math.max(0, devolucion.acciones.length - prioridadesVivasConEvidencia.length)
    : 0

  const guardar = async () => {
    if (guardando) return
    setError(null)

    // Un número mal escrito no llega a pedirse al servidor: `Number("")` da
    // `0`, no `NaN`, así que la comprobación real es la del `trim()` de
    // arriba, pero un texto que no es un número sí puede colarse aquí -por
    // ejemplo, si se pega texto en el campo-, y `NaN` no dice nada útil.
    if (notaFinal.trim() !== "" && Number.isNaN(notaFinalNumero)) {
      setError("La nota final tiene que ser un número entre 0 y 10.")
      return
    }

    setGuardando(true)
    try {
      const decisiones: Decision[] = informe.valoraciones.map((v) => {
        const estado = estadoDe(v)
        return {
          dimension: v.dimension,
          decision: estado.decision,
          texto: estado.decision === "EDITADA" ? estado.texto : null,
        }
      })
      const revisado = await api.revisar(id, {
        decisiones,
        semaforo_final_docente: semaforoFinal,
        nota_final_docente: notaFinalNumero,
        motivo_modificacion_nota: motivoNota.trim() === "" ? null : motivoNota,
        sintesis_provisional: sintesis,
      })
      setResultado(revisado)
      // Lo que de verdad quedó guardado puede no ser exactamente lo que se
      // mandó -una nota igual a la propuesta vuelve sin motivo, aunque se
      // hubiera escrito uno (ver `backend/api/analisis.py`)-, así que estos
      // tres controles se resincronizan con la respuesta, no se dan por
      // buenos con lo que ya tenían.
      setSemaforoFinal(revisado.informe.semaforo_final_docente)
      setNotaFinal(
        revisado.informe.nota_final_docente != null
          ? String(revisado.informe.nota_final_docente) : "",
      )
      setMotivoNota(revisado.informe.motivo_modificacion_nota ?? "")
      setSintesis(revisado.informe.sintesis_provisional)
      setGuardado(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setGuardando(false)
    }
  }

  const listaDeObservaciones = (valoraciones: ValoracionVerificada[]) => (
    <ul className="regla-fina">
      {valoraciones.map((v) => (
        <Observacion
          key={v.dimension}
          valoracion={v}
          estado={estadoDe(v)}
          alCambiar={(estado) => cambiar(v, estado)}
        />
      ))}
    </ul>
  )

  return (
    <div className="max-w-3xl">
      {/* Antes que nada: si lo que sigue son respuestas de un motor
          simulado, el docente tiene que saberlo antes de leer un solo
          juicio, no después. */}
      {motorSimulado && (
        <p className="mb-8 max-w-lectura text-[13px] senal">
          Este análisis lo ha hecho el motor simulado, no un modelo real.
          Lo que sigue son respuestas de prueba fijas, no un juicio sobre
          este trabajo: no lo uses para decidir nada.
        </p>
      )}

      <button onClick={alVolver} className="text-[13px] text-gris mb-8">
        ← Volver
      </button>

      <h2 className="text-[19px] mb-1">
        {informe.identificacion.alumno} · {informe.identificacion.fase} · versión{" "}
        {informe.identificacion.version}
      </h2>
      <p className="text-[13px] text-gris mb-10">Revisión del análisis</p>

      {resultado.aviso && (
        // El caso especial: el informe salió bien, solo falló el borrador.
        // No es un fallo -el texto ya lo dice así, compuesto en el
        // backend- y el informe entero se sigue pudiendo revisar debajo.
        <p className="mb-10 max-w-lectura text-[13px] senal">{resultado.aviso}</p>
      )}

      <section className="mb-10">
        <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
          Semáforo propuesto
        </h3>
        <p className="text-[15px]">{informe.semaforo_propuesto}</p>
        {informe.recomendacion && (
          <p className="mt-1 text-[13px] text-gris">{informe.recomendacion}</p>
        )}
        <p className="mt-2 max-w-lectura text-[12px] text-gris">
          Lo propone el sistema a partir de lo verificado, y no cambia
          después: es la prueba de lo que se propuso antes de que revisaras
          ninguna observación. No es una nota.
        </p>
      </section>

      <section className="mb-10">
        <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
          Semáforo final
        </h3>
        <select
          aria-label="Semáforo final"
          className="border border-grisclaro px-2 py-1 text-[13px]"
          value={semaforoFinal ?? ""}
          onChange={(e) => {
            setSemaforoFinal(e.target.value === "" ? null : e.target.value)
            setGuardado(false)
          }}
        >
          <option value="">— sin confirmar —</option>
          {CODIGOS_SEMAFORO.map((codigo) => (
            <option key={codigo} value={codigo}>{codigo}</option>
          ))}
        </select>
        <p className="mt-2 max-w-lectura text-[12px] text-gris">
          El que confirmas tú al cerrar la revisión. No puede quedar por
          debajo de lo que sostienen las observaciones que sigan aprobadas:
          si lo intentas, guardar lo rechaza y te dice cuál es el mínimo.
        </p>
        {semaforoFinalIncompatible && (
          <p className="mt-2 max-w-lectura text-[13px] senal">
            Con las observaciones que siguen aprobadas ahora mismo, el color
            mínimo es «{colorMinimoActual}». Guardar con «{semaforoFinal}»
            lo va a rechazar el servidor.
          </p>
        )}
        {semaforoFinalDesactualizado && (
          <p className="mt-2 max-w-lectura text-[13px] senal">
            El color mínimo que sostienen las observaciones que siguen
            aprobadas ha cambiado a «{colorMinimoActual}» -probablemente al
            aceptar, editar o descartar alguna-. «{semaforoFinal}» se puede
            seguir guardando, pero conviene que lo revises antes de cerrar.
          </p>
        )}
      </section>

      <section className="mb-10">
        <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
          Nota interna
        </h3>
        {!hayNotaQueDecidir ? (
          <p className="max-w-lectura text-[13px] text-gris">
            {informe.estado_nota === "no_aplicable"
              ? "Esta fase no lleva una nota calculada por el sistema."
              : "Pendiente de rúbrica oficial: el sistema no calcula una " +
                "nota hasta que exista una rúbrica cargada y versionada."}
          </p>
        ) : (
          <>
            <p className="text-[13px]">
              Propuesta del sistema:{" "}
              {informe.nota_propuesta_sistema != null
                ? informe.nota_propuesta_sistema.toFixed(2) : "—"}
              {informe.version_rubrica && (
                <span className="text-gris"> (rúbrica {informe.version_rubrica})</span>
              )}
            </p>
            <label className="mt-3 block text-[12px] uppercase tracking-[0.08em] text-gris">
              Nota final
              <input
                type="number" min={0} max={10} step={0.25}
                className="mt-1 block border border-grisclaro px-2 py-1 text-[13px] normal-case tracking-normal"
                value={notaFinal}
                onChange={(e) => {
                  setNotaFinal(e.target.value)
                  setGuardado(false)
                }}
              />
            </label>
            <p className="mt-2 max-w-lectura text-[12px] text-gris">
              No visible para el alumno, y no se convierte en calificación
              definitiva por guardarla aquí: es una estimación interna que
              apruebas o modificas tú (§13).
            </p>
            {notaFinalNumero !== null && informe.nota_propuesta_sistema !== null
              && notaFinalNumero !== informe.nota_propuesta_sistema && (
              <label className="mt-3 block text-[12px] uppercase tracking-[0.08em] text-gris">
                Motivo del cambio (opcional)
                <textarea
                  className="mt-1 block w-full max-w-lectura border border-grisclaro px-2 py-1 text-[13px] normal-case tracking-normal"
                  rows={2}
                  value={motivoNota}
                  onChange={(e) => {
                    setMotivoNota(e.target.value)
                    setGuardado(false)
                  }}
                />
                <span className="mt-1 block max-w-lectura text-[12px] text-gris normal-case tracking-normal">
                  Qué criterio de corrección pesó en el cambio, no
                  circunstancias del alumno: aquí no tiene sitio ningún dato
                  personal (§19).
                </span>
              </label>
            )}
          </>
        )}
      </section>

      {informe.resumen && (
        <section className="mb-10">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
            Resumen
          </h3>
          <p className="max-w-lectura text-[14px]">{informe.resumen}</p>
        </section>
      )}

      <section className="mb-10">
        <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
          Síntesis provisional para revisión docente
        </h3>
        <p className="max-w-lectura text-[12px] text-gris mb-2">
          La compone el sistema a partir de lo ya verificado en este mismo
          informe. Nunca se cierra sola: reescríbela antes de darla por
          buena.
        </p>
        <textarea
          aria-label="Síntesis provisional para revisión docente"
          className="block w-full max-w-lectura border border-grisclaro px-2 py-2 text-[13px]"
          rows={6}
          value={sintesis}
          onChange={(e) => {
            setSintesis(e.target.value)
            setGuardado(false)
          }}
        />
      </section>

      {informe.dudas.length > 0 && (
        <section className="mb-10">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
            Dudas del motor
          </h3>
          <ul className="space-y-2">
            {informe.dudas.map((duda) => (
              <li key={duda} className="max-w-lectura text-[13px] senal">{duda}</li>
            ))}
          </ul>
        </section>
      )}

      {informe.indicios.length > 0 && (
        <section className="mb-10">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
            Indicios de autoría
          </h3>
          <p className="max-w-lectura text-[12px] text-gris mb-3">
            Un indicio no es un veredicto: la decisión sobre la autoría es
            tuya (§13).
          </p>
          <ul className="space-y-3">
            {informe.indicios.map((indicio, i) => (
              <li key={i} className="max-w-lectura text-[13px] senal">
                {indicio.descripcion}
                <span className="block mt-1 font-mono text-[12px] text-gris">
                  «{indicio.evidencia.cita}»
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {informe.reparos.length > 0 && (
        <details className="mb-10">
          <summary className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3 cursor-pointer">
            Reparos de verificación ({informe.reparos.length})
          </summary>
          <p className="max-w-lectura text-[12px] text-gris mt-3 mb-3">
            Lo que el motor devolvió y el sistema no ha dado por bueno: la
            diferencia entre lo que dijo y lo que aquí se está aceptando.
          </p>
          <ul className="space-y-3">
            {informe.reparos.map((r, i) => (
              <li key={i} className="max-w-lectura text-[13px]">
                <span className="block text-[11px] uppercase tracking-[0.08em] text-gris">
                  {r.regla}
                </span>
                {r.detalle}
              </li>
            ))}
          </ul>
        </details>
      )}

      <section className="mb-10">
        <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
          Prioridades para la devolución
        </h3>
        {prioridadesVivas.length === 0 ? (
          <p className="text-[13px] text-gris">
            Ninguna, con las decisiones actuales.
          </p>
        ) : (
          <ul className="text-[13px] space-y-1">
            {prioridadesVivas.map((v) => (
              <li key={v.dimension}>
                {v.dimension} · {v.prioridad}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mb-10">
        <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
          Observaciones
        </h3>
        {listaDeObservaciones(informe.prioridades)}
      </section>

      {informe.prioridades_descartadas.length > 0 && (
        <section className="mb-10">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
            Con prioridad, fuera del límite de la devolución
          </h3>
          <p className="max-w-lectura text-[12px] text-gris mb-3">
            Tenían evidencia y prioridad, pero no cupieron en el máximo de
            observaciones que llegan al alumno.
          </p>
          {listaDeObservaciones(informe.prioridades_descartadas)}
        </section>
      )}

      {resto.length > 0 && (
        <details className="mb-10">
          <summary className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3 cursor-pointer">
            Resto de dimensiones evaluadas ({resto.length})
          </summary>
          <div className="mt-3">{listaDeObservaciones(resto)}</div>
        </details>
      )}

      {informe.dimensiones_ausentes.length > 0 && (
        <details className="mb-10">
          <summary className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3 cursor-pointer">
            Dimensiones sin valorar ({informe.dimensiones_ausentes.length})
          </summary>
          <p className="max-w-lectura text-[12px] text-gris mt-3 mb-3">
            Activas en esta fase, pero el motor no llegó a valorarlas: no
            significa que estén correctas, significa que nadie las ha
            revisado todavía. Eso te toca a ti.
          </p>
          <ul className="text-[13px] space-y-1">
            {informe.dimensiones_ausentes.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </details>
      )}

      {informe.fortalezas.length > 0 && (
        <section className="mb-10">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
            Fortalezas
          </h3>
          <ul className="space-y-3">
            {informe.fortalezas.map((f, i) => (
              <li
                key={i}
                className={`max-w-lectura text-[13px] ${f.evidencia_localizada ? "" : "senal"}`}
              >
                {f.descripcion}
                <span className="block mt-1 font-mono text-[12px] text-gris">
                  «{f.evidencia.cita}»
                </span>
                {!f.evidencia_localizada && (
                  <span className="block mt-1 text-[12px]">
                    La cita no se ha localizado en el documento: al alumno no
                    le llegará.
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {devolucion && (
        <section className="mb-10">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
            Borrador de devolución
          </h3>
          <p className="max-w-lectura text-[12px] text-gris mb-2">
            Se ha comprobado que este texto no incumple ninguna regla que no
            se negocia -nada de notas, nada de indicios de autoría, nada sin
            evidencia-, pero no que cada frase corresponda exactamente a una
            prioridad. Es texto libre del motor, y lo firmas tú: léelo
            entero antes de usarlo.
          </p>
          <p className="max-w-lectura text-[12px] text-gris mb-4">
            Además, refleja el análisis original, no las decisiones que
            acabas de tomar en esta pantalla: no se ha vuelto a redactar con
            ellas. Revísalo por si alguna ya no aplica.
          </p>
          {accionesSobrantes > 0 && (
            <p className="max-w-lectura text-[13px] senal mb-4">
              {accionesSobrantes === 1 ? (
                <>
                  El borrador incluye una acción que ya no corresponde a
                  ninguna prioridad viva de esta revisión. No se puede
                  señalar con certeza cuál -el orden en que el motor
                  redacta el texto no está garantizado-, así que revisa el
                  borrador entero antes de usarlo.
                </>
              ) : (
                <>
                  El borrador incluye {accionesSobrantes} acciones que ya
                  no corresponden a ninguna prioridad viva de esta
                  revisión. No se puede señalar con certeza cuáles -el
                  orden en que el motor redacta el texto no está
                  garantizado-, así que revisa el borrador entero antes de
                  usarlo.
                </>
              )}
            </p>
          )}
          <div className="max-w-lectura text-[14px] space-y-3">
            <p>{devolucion.apertura}</p>
            {devolucion.fortalezas.length > 0 && (
              <ul className="list-disc pl-5 space-y-1">
                {devolucion.fortalezas.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            )}
            {devolucion.acciones.length > 0 && (
              <ul className="list-disc pl-5 space-y-1">
                {devolucion.acciones.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            )}
            <p>{devolucion.cierre}</p>
          </div>
        </section>
      )}

      {error && (
        <p className="mb-6 max-w-lectura text-[13px] text-tinta border-t border-grisclaro pt-4">
          {error}
        </p>
      )}

      <div className="flex items-center gap-4 border-t border-grisclaro pt-6">
        <button
          onClick={guardar}
          disabled={guardando}
          className="px-4 py-2 text-[13px] bg-tinta text-papel disabled:opacity-30"
        >
          {guardando ? "Guardando…" : "Guardar la revisión"}
        </button>
        {guardado && (
          <span className="text-[12px] text-gris">Guardado.</span>
        )}
      </div>
    </div>
  )
}
