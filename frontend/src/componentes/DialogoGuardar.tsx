import { useState } from "react"

import { formatearValor } from "../lib/formato"
import type { CambioDeValor, Propuesta, Resultado } from "../lib/tipos"

interface Props {
  propuestas: Propuesta[]
  /** Hay una petición de guardado en vuelo. */
  enviando?: boolean
  /** El resultado de un guardado que no salió: se enseña aquí dentro. */
  resultado?: Resultado | null
  /** Un fallo que no llegó ni a ser resultado, como quedarse sin servidor. */
  error?: string | null
  alConfirmar: (datos: { cambios: CambioDeValor[]; motivo: string; fuente: string }) => void
  alCancelar: () => void
}

/** La decisión del docente sobre un criterio, mientras la está tomando. */
interface Decision {
  /** Lo que ha escrito como valor nuevo. Vacío: no ha escrito nada. */
  valor: string
  /** Ha declarado que ese criterio sigue siendo correcto tal como está. */
  sigueIgual: boolean
}

const llaveDe = (propuesta: Propuesta) => `${propuesta.identificador}.${propuesta.clave}`

/**
 * El paso que convierte una edición en un cambio registrado.
 *
 * Motivo y fuente son obligatorios porque es lo que R5 exige y lo que
 * permitirá entender la decisión dentro de un año. No hay forma de
 * saltárselos: sin ellos el botón no se activa.
 *
 * Y cada criterio que deriva de la sección se decide aquí, uno por uno:
 * escribiendo lo que pasa a valer, o declarando que sigue siendo correcto.
 * Antes solo se podía aceptar o descartar lo que el editor había sabido
 * inferir, y para todo lo demás -reescribir una dimensión, cambiar la
 * tipografía, un peso que la prosa no deletrea- la única salida era editar
 * el YAML a mano, que es el procedimiento de consola que esta pantalla vino
 * a sustituir. Un criterio que se quede sin decidir deja su sección sin
 * sellar y el guardado se rechaza, diciendo cuáles faltan.
 *
 * Lo que el editor ha comprobado que sigue apareciendo igual en el texto
 * nuevo llega ya marcado -no hay nada que decidir ahí-, y el resto se puede
 * dar por revisado de una vez cuando el docente ya los ha mirado. Ninguna de
 * las dos cosas salta ninguna regla: el guardado sigue exigiendo motivo,
 * fuente y su gesto, y cada criterio queda escrito en el documento de
 * cambio. Lo que evitan es que seguir el procedimiento cueste tanto como
 * para que compense rodearlo.
 */
export function DialogoGuardar({
  propuestas,
  enviando = false,
  resultado = null,
  error = null,
  alConfirmar,
  alCancelar,
}: Props) {
  const automaticas = propuestas.filter((p) => p.valor_propuesto !== null)
  // Los que el editor ha comprobado que siguen apareciendo igual en el texto
  // nuevo van aparte, ya marcados: no hay nada que decidir sobre ellos y
  // mezclarlos con los que sí lo piden era lo que convertía una errata del
  // §8 en treinta y seis decisiones.
  const sinCambio = propuestas.filter(
    (p) => p.valor_propuesto === null && p.revisado_sin_cambio === true,
  )
  const aMano = propuestas.filter(
    (p) => p.valor_propuesto === null && p.revisado_sin_cambio !== true,
  )

  const [decisiones, setDecisiones] = useState<Record<string, Decision>>(() => {
    const inicial: Record<string, Decision> = {}
    for (const propuesta of propuestas) {
      inicial[llaveDe(propuesta)] = {
        // Lo que el editor ha sabido inferir viene escrito, para que aceptarlo
        // sea no tocar nada. Sigue siendo suyo: puede corregirlo o borrarlo.
        valor: propuesta.valor_propuesto ?? "",
        // Lo que el editor ha comprobado que sigue igual llega ya marcado.
        // Sigue siendo una decisión suya: puede desmarcarlo, y se registra
        // en el documento de cambio exactamente igual que si lo hubiera
        // marcado él.
        sigueIgual: propuesta.revisado_sin_cambio === true,
      }
    }
    return inicial
  })
  const [motivo, setMotivo] = useState("")
  const [fuente, setFuente] = useState("")

  const decisionDe = (propuesta: Propuesta): Decision =>
    decisiones[llaveDe(propuesta)] ?? { valor: "", sigueIgual: false }

  const cambiar = (propuesta: Propuesta, parte: Partial<Decision>) => {
    const llave = llaveDe(propuesta)
    setDecisiones({ ...decisiones, [llave]: { ...decisionDe(propuesta), ...parte } })
  }

  const sinDecidir = propuestas.filter((p) => {
    const decision = decisionDe(p)
    return !decision.sigueIgual && decision.valor.trim().length === 0
  })

  /** Marca como revisados sin cambio todos los que sigan sin decidir. */
  const marcarElRestoRevisado = () => {
    const siguientes = { ...decisiones }
    for (const propuesta of sinDecidir) {
      const llave = llaveDe(propuesta)
      siguientes[llave] = { ...decisionDe(propuesta), sigueIgual: true }
    }
    setDecisiones(siguientes)
  }

  const puedeGuardar =
    motivo.trim().length > 0 && fuente.trim().length > 0 && !enviando

  const confirmar = () => {
    const cambios: CambioDeValor[] = []
    for (const propuesta of propuestas) {
      const decision = decisionDe(propuesta)
      if (decision.sigueIgual) {
        cambios.push({
          fichero: propuesta.fichero,
          identificador: propuesta.identificador,
          clave: propuesta.clave,
          // Sin valor nuevo: el criterio no se toca, pero queda revisado.
          valor_nuevo: null,
        })
      } else if (decision.valor.trim().length > 0) {
        cambios.push({
          fichero: propuesta.fichero,
          identificador: propuesta.identificador,
          clave: propuesta.clave,
          valor_nuevo: decision.valor.trim(),
        })
      }
    }
    alConfirmar({ cambios, motivo: motivo.trim(), fuente: fuente.trim() })
  }

  const filaDeCriterio = (propuesta: Propuesta) => {
    const llave = llaveDe(propuesta)
    const decision = decisionDe(propuesta)
    return (
      <li key={llave} className="border-b border-grisclaro py-4">
        <p className="font-mono text-[12px]">
          {llave}{" "}
          <span className="text-gris">
            ahora {formatearValor(propuesta.valor_actual)}
          </span>
        </p>
        <p className="text-[12px] text-gris mt-1">{propuesta.motivo}</p>

        <label className="block mt-3">
          <span className="block text-[11px] uppercase tracking-[0.08em] text-gris mb-1">
            Pasa a decir
          </span>
          <input
            value={decision.valor}
            disabled={decision.sigueIgual || enviando}
            onChange={(e) => cambiar(propuesta, { valor: e.target.value })}
            aria-label={`Valor nuevo de ${llave}`}
            className="w-full border border-grisclaro bg-white p-2 font-mono
                       text-[13px] disabled:bg-papel disabled:text-gris"
          />
        </label>

        <label className="flex gap-2 items-center mt-2 text-[12px] text-gris">
          <input
            type="checkbox"
            checked={decision.sigueIgual}
            disabled={enviando}
            onChange={(e) => cambiar(propuesta, { sigueIgual: e.target.checked })}
            aria-label={`Sin cambio en ${llave}`}
          />
          Lo he revisado y no cambia
        </label>
      </li>
    )
  }

  return (
    <div className="fixed inset-0 bg-tinta/20 flex items-center justify-center p-8">
      <div className="bg-papel border border-tinta max-w-2xl w-full p-8 max-h-full overflow-y-auto">
        <h2 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-gris mb-6">
          Registrar el cambio
        </h2>

        {automaticas.length > 0 && (
          <section className="mb-6">
            <p className="text-[13px] mb-3">
              Esto lo he sabido leer del texto. Compruébalo y corrígelo si me he
              equivocado:
            </p>
            <ul className="regla-fina">{automaticas.map(filaDeCriterio)}</ul>
          </section>
        )}

        {sinCambio.length > 0 && (
          <section className="mb-6">
            <p className="text-[13px] mb-3">
              Esto sigue apareciendo igual en el texto nuevo, así que lo doy
              por revisado sin cambio. Desmárcalo si no estás de acuerdo:
            </p>
            <ul className="regla-fina">{sinCambio.map(filaDeCriterio)}</ul>
          </section>
        )}

        {aMano.length > 0 && (
          <section className="mb-6">
            <p className="text-[13px] mb-3">
              Esto no lo puedo decidir yo. Dime tú qué dice ahora cada criterio,
              o marca que sigue igual:
            </p>
            <ul className="regla-fina">{aMano.map(filaDeCriterio)}</ul>
          </section>
        )}

        {sinDecidir.length > 0 && (
          <div className="mb-6">
            <p className="text-[12px] text-gris">
              {sinDecidir.length === 1
                ? "Queda 1 criterio sin decidir."
                : `Quedan ${sinDecidir.length} criterios sin decidir.`}{" "}
              Mientras haya alguno, esta sección no se sella y R2 seguirá pidiendo
              que se mire.
            </p>
            {/* No es un atajo a las reglas: sigue siendo él quien declara que
                los ha revisado, y cada uno queda escrito en el documento de
                cambio igual que si los hubiera marcado de uno en uno. Lo que
                evita es que revisarlos y decirlo cuesten lo mismo. Por eso el
                botón dice cuántos va a marcar antes de marcarlos. */}
            <button
              type="button"
              onClick={marcarElRestoRevisado}
              disabled={enviando}
              className="mt-2 px-3 py-1 text-[12px] border border-grisclaro
                         disabled:opacity-30"
            >
              {sinDecidir.length === 1
                ? "He revisado el que queda y no cambia"
                : `He revisado los ${sinDecidir.length} que quedan y no cambian`}
            </button>
          </div>
        )}

        <label className="block mb-4">
          <span className="block text-[12px] uppercase tracking-[0.08em] text-gris mb-2">
            ¿Por qué cambias esto?
          </span>
          <textarea
            value={motivo}
            disabled={enviando}
            onChange={(e) => setMotivo(e.target.value)}
            rows={3}
            className="w-full border border-grisclaro bg-white p-3 text-[14px]"
          />
        </label>

        <label className="block mb-6">
          <span className="block text-[12px] uppercase tracking-[0.08em] text-gris mb-2">
            ¿Qué fuente lo respalda?
          </span>
          <input
            value={fuente}
            disabled={enviando}
            onChange={(e) => setFuente(e.target.value)}
            className="w-full border border-grisclaro bg-white p-3 text-[14px]"
          />
          <span className="block text-[12px] text-gris mt-2">
            La programación didáctica, una instrucción del centro, un acuerdo
            documentado. Si no hay ninguna, este cambio no debería hacerse.
          </span>
        </label>

        {/* Un guardado rechazado por las reglas es el fallo esperado, no una
            excepción: se enseña aquí dentro, con el motivo y la fuente
            intactos, para que corregir sea seguir escribiendo. */}
        {error && (
          <p className="mb-6 text-[13px] text-tinta border-t border-grisclaro pt-4">
            {error}
          </p>
        )}

        {resultado && (
          <div className="mb-6 border-t border-grisclaro pt-4">
            <p className="text-[13px]">{resultado.mensaje}</p>
            {resultado.infracciones.length > 0 && (
              <ul className="mt-3 space-y-2">
                {resultado.infracciones.map((infraccion, indice) => (
                  <li key={indice} className="text-[12px]">
                    <span className="font-mono text-tinta">[{infraccion.regla}]</span>{" "}
                    <span className="font-mono text-gris">{infraccion.fichero}</span>
                    <p className="text-gris mt-1">{infraccion.detalle}</p>
                  </li>
                ))}
              </ul>
            )}
            {resultado.detalle_tecnico && (
              <p className="mt-3 font-mono text-[11px] text-gris">
                {resultado.detalle_tecnico}
              </p>
            )}
          </div>
        )}

        <div className="flex gap-3 justify-end items-center">
          {enviando && (
            <span className="text-[12px] text-gris mr-auto">
              Guardando. No cierres esta ventana ni vuelvas a pulsar.
            </span>
          )}
          <button onClick={alCancelar} disabled={enviando}
                  className="px-4 py-2 text-[13px] border border-grisclaro
                             disabled:opacity-30">
            Cancelar
          </button>
          <button onClick={confirmar} disabled={!puedeGuardar}
                  className="px-4 py-2 text-[13px] bg-tinta text-papel disabled:opacity-30">
            {enviando ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </div>
    </div>
  )
}
