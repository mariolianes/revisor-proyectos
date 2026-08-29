import { useState } from "react"

import { Observacion } from "../componentes/Observacion"
import type { EstadoDeLaDecision } from "../componentes/Observacion"
import { api } from "../lib/api"
import type { Decision, ResultadoAnalisis, ValoracionVerificada } from "../lib/tipos"

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
 *    aviso no regenera el texto: dice la verdad sobre él. Cuando una
 *    acción del borrador corresponde a una prioridad que el docente acaba
 *    de descartar -`accionesDescartadas`, por posición: `componer()` arma
 *    `devolucion.acciones` en el mismo orden que las prioridades con
 *    evidencia localizada, ver `backend/salidas/borrador.py`- la pantalla
 *    lo sabe con certeza, no lo insinúa, y ahí sí usa `senal`: es lo único
 *    de este bloque que de verdad espera que el docente lo corrija a mano
 *    o vuelva a aceptar la prioridad antes de usar el texto.
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
 * Ninguna nota, en ninguna forma: ni como campo, ni como control, ni como
 * hueco a rellenar. El semáforo y la recomendación se leen -proponen, no
 * deciden-, no llevan `senal` porque no piden localizar nada, y no hay
 * ningún control para cambiarlos: se muestran, no se editan.
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

  // `componer()` (`backend/salidas/borrador.py`) arma `devolucion.acciones`
  // a partir de `informe.prioridades` filtradas por `evidencia_localizada`,
  // en ese mismo orden, y recorta a como mucho una acción por prioridad. Por
  // eso el emparejamiento por posición es fiel a como se compuso el texto,
  // no una suposición: `accionesEnBorrador[i]` es la prioridad de la que
  // salió `devolucion.acciones[i]`. Si el motor devolvió menos acciones de
  // las que le tocaban, `slice` no inventa una correspondencia para las que
  // faltan.
  const prioridadesConEvidencia = informe.prioridades.filter(
    (v) => v.evidencia_localizada,
  )
  const accionesEnBorrador = devolucion
    ? prioridadesConEvidencia.slice(0, devolucion.acciones.length)
    : []
  // La única discrepancia entre "Prioridades para la devolución" y el
  // borrador que esta pantalla puede afirmar con certeza: una prioridad que
  // el docente acaba de descartar y cuya acción el borrador todavía trae,
  // palabra por palabra, porque no se ha regenerado. No se comprueba nada
  // más -una edición de texto no rompe la correspondencia por posición, y
  // "aceptada" es justo lo que el borrador ya asume-, así que el aviso no
  // se dispara por eso.
  const accionesDescartadas = accionesEnBorrador.filter(
    (v) => estadoDe(v).decision === "DESCARTADA",
  )

  const guardar = async () => {
    if (guardando) return
    setError(null)
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
      const revisado = await api.revisar(id, { decisiones })
      setResultado(revisado)
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
        <p className="text-[15px]">{informe.semaforo}</p>
        {informe.recomendacion && (
          <p className="mt-1 text-[13px] text-gris">{informe.recomendacion}</p>
        )}
        <p className="mt-2 max-w-lectura text-[12px] text-gris">
          Lo propone el sistema a partir de lo verificado. No es una nota ni
          se puede cambiar aquí: la valoración final es tuya.
        </p>
      </section>

      {informe.resumen && (
        <section className="mb-10">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
            Resumen
          </h3>
          <p className="max-w-lectura text-[14px]">{informe.resumen}</p>
        </section>
      )}

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
          {accionesDescartadas.length > 0 && (
            <p className="max-w-lectura text-[13px] senal mb-4">
              {accionesDescartadas.length === 1 ? (
                <>
                  El borrador todavía pide la acción de{" "}
                  {accionesDescartadas[0].dimension}, que acabas de
                  descartar.
                </>
              ) : (
                <>
                  El borrador todavía pide las acciones de{" "}
                  {accionesDescartadas.map((v) => v.dimension).join(", ")},
                  que acabas de descartar.
                </>
              )}{" "}
              Corrígelo a mano o vuelve a aceptarlas antes de usarlo.
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
