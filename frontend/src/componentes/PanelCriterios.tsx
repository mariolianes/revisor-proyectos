import { formatearValor } from "../lib/formato"
import type { CriterioDerivado } from "../lib/tipos"

interface Props {
  criterios: CriterioDerivado[]
}

/** Lo que depende de la sección que se está editando. */
export function PanelCriterios({ criterios }: Props) {
  if (criterios.length === 0) {
    return (
      <p className="text-[13px] text-gris">
        Ningún criterio deriva de esta sección. Puedes editarla sin que se
        actualice nada más — y sin que ninguna regla lo advierta.
      </p>
    )
  }

  return (
    <div>
      <h3 className="text-[12px] uppercase tracking-[0.08em] senal mb-4">
        Depende de esta sección
      </h3>
      <ul className="regla-fina">
        {criterios.map((criterio) => (
          <li key={`${criterio.fichero}:${criterio.identificador}`}
              className="border-b border-grisclaro py-3">
            <p className="font-mono text-[11px] text-gris">{criterio.fichero}</p>
            <p className="font-mono text-[12px] mt-1">{criterio.identificador}</p>
            <dl className="mt-2 space-y-1">
              {Object.entries(criterio.valores).map(([clave, valor]) => (
                <div key={clave} className="flex gap-2 font-mono text-[12px]">
                  <dt className="text-gris">{clave}</dt>
                  <dd>{formatearValor(valor)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </div>
  )
}
