import { useState } from "react"

import { formatearValor } from "../lib/formato"
import type { CambioDeValor, Propuesta } from "../lib/tipos"

interface Props {
  propuestas: Propuesta[]
  alConfirmar: (datos: { cambios: CambioDeValor[]; motivo: string; fuente: string }) => void
  alCancelar: () => void
}

/**
 * El paso que convierte una edición en un cambio registrado.
 *
 * Motivo y fuente son obligatorios porque es lo que R5 exige y lo que
 * permitirá entender la decisión dentro de un año. No hay forma de
 * saltárselos: sin ellos el botón no se activa.
 */
export function DialogoGuardar({ propuestas, alConfirmar, alCancelar }: Props) {
  const automaticas = propuestas.filter((p) => p.valor_propuesto !== null)
  const aMano = propuestas.filter((p) => p.valor_propuesto === null)

  const [aceptadas, setAceptadas] = useState<Set<string>>(
    new Set(automaticas.map((p) => `${p.identificador}.${p.clave}`)),
  )
  const [motivo, setMotivo] = useState("")
  const [fuente, setFuente] = useState("")

  const puedeGuardar = motivo.trim().length > 0 && fuente.trim().length > 0

  const alternar = (llave: string) => {
    const siguiente = new Set(aceptadas)
    siguiente.has(llave) ? siguiente.delete(llave) : siguiente.add(llave)
    setAceptadas(siguiente)
  }

  const confirmar = () => {
    const cambios: CambioDeValor[] = automaticas
      .filter((p) => aceptadas.has(`${p.identificador}.${p.clave}`))
      .map((p) => ({
        fichero: p.fichero,
        identificador: p.identificador,
        clave: p.clave,
        valor_nuevo: p.valor_propuesto as string,
      }))
    alConfirmar({ cambios, motivo: motivo.trim(), fuente: fuente.trim() })
  }

  return (
    <div className="fixed inset-0 bg-tinta/20 flex items-center justify-center p-8">
      <div className="bg-papel border border-tinta max-w-2xl w-full p-8 max-h-full overflow-y-auto">
        <h2 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-gris mb-6">
          Registrar el cambio
        </h2>

        {automaticas.length > 0 && (
          <section className="mb-6">
            <p className="text-[13px] mb-3">Criterios que se actualizarán:</p>
            <ul className="regla-fina">
              {automaticas.map((p) => {
                const llave = `${p.identificador}.${p.clave}`
                return (
                  <li key={llave} className="border-b border-grisclaro py-3 flex gap-3">
                    <input
                      type="checkbox"
                      checked={aceptadas.has(llave)}
                      onChange={() => alternar(llave)}
                      className="mt-1"
                      aria-label={llave}
                    />
                    <div>
                      <p className="font-mono text-[12px]">
                        {p.identificador}.{p.clave}{" "}
                        <span className="text-gris">{formatearValor(p.valor_actual)}</span>
                        {" → "}
                        <span className="senal">{formatearValor(p.valor_propuesto as string)}</span>
                      </p>
                      <p className="text-[12px] text-gris mt-1">{p.motivo}</p>
                    </div>
                  </li>
                )
              })}
            </ul>
          </section>
        )}

        {aMano.length > 0 && (
          <section className="mb-6">
            <p className="text-[13px] mb-3">
              Esto no lo puedo decidir yo. Revísalo cuando termines:
            </p>
            <ul className="regla-fina">
              {aMano.map((p) => (
                <li key={`${p.identificador}.${p.clave}`}
                    className="border-b border-grisclaro py-3">
                  <p className="font-mono text-[12px]">
                    {p.identificador}.{p.clave} = {formatearValor(p.valor_actual)}
                  </p>
                  <p className="text-[12px] text-gris mt-1">{p.motivo}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        <label className="block mb-4">
          <span className="block text-[12px] uppercase tracking-[0.08em] text-gris mb-2">
            ¿Por qué cambias esto?
          </span>
          <textarea
            value={motivo}
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
            onChange={(e) => setFuente(e.target.value)}
            className="w-full border border-grisclaro bg-white p-3 text-[14px]"
          />
          <span className="block text-[12px] text-gris mt-2">
            La programación didáctica, una instrucción del centro, un acuerdo
            documentado. Si no hay ninguna, este cambio no debería hacerse.
          </span>
        </label>

        <div className="flex gap-3 justify-end">
          <button onClick={alCancelar}
                  className="px-4 py-2 text-[13px] border border-grisclaro">
            Cancelar
          </button>
          <button onClick={confirmar} disabled={!puedeGuardar}
                  className="px-4 py-2 text-[13px] bg-tinta text-papel disabled:opacity-30">
            Guardar
          </button>
        </div>
      </div>
    </div>
  )
}
