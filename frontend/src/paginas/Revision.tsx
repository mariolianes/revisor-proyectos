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
 * Tres cosas de fondo, no de estilo:
 *
 * 1. Qué está verificado y qué no. `Observacion` marca con `senal` la que
 *    tiene la cita sin localizar; aquí se hace lo mismo con las dudas del
 *    motor y los indicios de autoría (§13: son un indicio, no un veredicto,
 *    la decisión es del docente).
 * 2. El borrador es texto libre. Se ha comprobado que no viola ninguna
 *    regla dura -nada de notas, nada de autoría, nada sin evidencia-, pero
 *    no que cada frase corresponda exactamente a una prioridad: quien lo
 *    firma es él, y tiene que saberlo antes de aceptarlo. Por eso ese aviso
 *    NO lleva `senal` -no es algo que localizar y decidir, es una condición
 *    de todo el bloque- y va justo encima del borrador, no escondido.
 * 3. Informe válido, borrador fallido no es un error. Cuando
 *    `resultado.devolucion` es `null`, `resultado.aviso` ya trae la
 *    explicación completa compuesta por el backend; esta pantalla no la
 *    repite ni la presenta como un fallo, y el informe se sigue pudiendo
 *    revisar entero.
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

      {informe.fortalezas.length > 0 && (
        <section className="mb-10">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-3">
            Fortalezas
          </h3>
          <ul className="space-y-2">
            {informe.fortalezas.map((f, i) => (
              <li key={i} className="max-w-lectura text-[13px]">
                {f.descripcion}
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
          <p className="max-w-lectura text-[12px] text-gris mb-4">
            Se ha comprobado que este texto no incumple ninguna regla que no
            se negocia -nada de notas, nada de indicios de autoría, nada sin
            evidencia-, pero no que cada frase corresponda exactamente a una
            prioridad. Es texto libre del motor, y lo firmas tú: léelo
            entero antes de usarlo.
          </p>
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
