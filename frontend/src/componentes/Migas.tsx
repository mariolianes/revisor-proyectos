/**
 * Dónde estás, y cómo volver.
 *
 * Antes, abrir una ficha o una revisión apagaba las cuatro pestañas: el
 * docente no veía de dónde venía ni tenía más salida que un «← Volver» que
 * aparecía dentro de la pantalla. Con dos niveles anidados -bandeja, ficha,
 * revisión- eso se pierde enseguida.
 *
 * Cada miga menos la última es un botón: se puede saltar a cualquier nivel
 * anterior, no solo al inmediato.
 */

export interface Miga {
  texto: string
  /** `undefined` en la última: es donde estás, no un sitio al que ir. */
  alPulsar?: () => void
}

interface Props {
  migas: Miga[]
}

export function Migas({ migas }: Props) {
  return (
    <nav aria-label="Dónde estás" className="mb-8 flex flex-wrap items-center">
      {migas.map((miga, i) => {
        const ultima = i === migas.length - 1
        return (
          <span key={miga.texto} className="flex items-center">
            {i > 0 && (
              <span aria-hidden="true" className="mx-2 text-[12px] text-grisclaro">
                ›
              </span>
            )}
            {ultima || !miga.alPulsar ? (
              <span
                aria-current={ultima ? "page" : undefined}
                className="text-[12px] uppercase tracking-[0.08em]"
              >
                {miga.texto}
              </span>
            ) : (
              <button
                onClick={miga.alPulsar}
                className="text-[12px] uppercase tracking-[0.08em] text-gris hover:text-tinta transition-colors"
              >
                {miga.texto}
              </button>
            )}
          </span>
        )
      })}
    </nav>
  )
}
