import type { CodigoDeDecision, ValoracionVerificada } from "../lib/tipos"

/** La decisión del docente sobre una observación, mientras la está tomando. */
export interface EstadoDeLaDecision {
  decision: CodigoDeDecision
  /** Lo que queda de la observación tras editarla. Se ignora si no es EDITADA. */
  texto: string
}

interface Props {
  valoracion: ValoracionVerificada
  estado: EstadoDeLaDecision
  alCambiar: (estado: EstadoDeLaDecision) => void
}

/**
 * Una observación del informe, con las tres formas de decidir sobre ella.
 *
 * La tinta `senal` marca aquí solo la cita no localizada: es lo único de
 * esta tarjeta que espera una decisión que no sea aceptar o no. El nivel
 * `NO_VERIFICABLE` no la lleva -no es una alarma, es una escala del §8.1
 * igual que las demás-, y tampoco la lleva la prioridad por sí sola: una
 * P1 no es más urgente de pintar que una P3, es al docente a quien le toca
 * juzgar cuál lo es.
 */
export function Observacion({ valoracion, estado, alCambiar }: Props) {
  const editando = estado.decision === "EDITADA"
  const descartada = estado.decision === "DESCARTADA"

  const aceptar = () =>
    alCambiar({ decision: "ACEPTADA", texto: valoracion.observacion })
  const empezarAEditar = () =>
    alCambiar({ decision: "EDITADA", texto: estado.texto || valoracion.observacion })
  const descartar = () =>
    alCambiar({ decision: "DESCARTADA", texto: valoracion.observacion })

  return (
    <li className={`border-b border-grisclaro py-4 ${descartada ? "opacity-40" : ""}`}>
      <div className="flex flex-wrap items-baseline gap-x-3 text-[11px] uppercase tracking-[0.08em] text-gris">
        <span>{valoracion.dimension}</span>
        <span>{valoracion.nivel.replace(/_/g, " ").toLowerCase()}</span>
        {valoracion.prioridad && <span>{valoracion.prioridad}</span>}
      </div>

      {!valoracion.evidencia_localizada && (
        <p className="mt-2 max-w-lectura text-[13px] senal">
          La cita no se ha localizado en el documento: tal como está, esta
          observación no llegará al alumno. Puedes aceptarla igualmente si
          la reconoces.
        </p>
      )}

      <blockquote className="mt-2 max-w-lectura border-l-2 border-grisclaro pl-3 font-mono text-[12px] text-gris">
        «{valoracion.evidencia.cita}»
        <span className="block mt-1">{valoracion.evidencia.apartado}</span>
      </blockquote>

      <p className="mt-2 max-w-lectura text-[14px]">{valoracion.observacion}</p>

      {editando && (
        <div className="mt-3 max-w-lectura">
          <textarea
            value={estado.texto}
            onChange={(e) => alCambiar({ decision: "EDITADA", texto: e.target.value })}
            aria-label={`Texto editado de ${valoracion.dimension}`}
            rows={3}
            className="w-full border border-grisclaro bg-white p-2 text-[13px]"
          />
          <button type="button" onClick={aceptar} className="mt-1 text-[12px] text-gris">
            Descartar la edición
          </button>
        </div>
      )}

      <div className="mt-3 flex gap-4">
        <button
          type="button"
          onClick={aceptar}
          aria-pressed={estado.decision === "ACEPTADA"}
          className={
            estado.decision === "ACEPTADA"
              ? "text-[12px] border-b-2 border-tinta pb-1"
              : "text-[12px] text-gris pb-1"
          }
        >
          Aceptar
        </button>
        <button
          type="button"
          onClick={empezarAEditar}
          aria-pressed={editando}
          className={
            editando
              ? "text-[12px] border-b-2 border-tinta pb-1"
              : "text-[12px] text-gris pb-1"
          }
        >
          Editar
        </button>
        <button
          type="button"
          onClick={descartar}
          aria-pressed={descartada}
          className={
            descartada
              ? "text-[12px] border-b-2 border-tinta pb-1"
              : "text-[12px] text-gris pb-1"
          }
        >
          Descartar
        </button>
      </div>
    </li>
  )
}
