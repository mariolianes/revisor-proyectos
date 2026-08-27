import type { Documento } from "../lib/tipos"

interface Props {
  documento: Documento
  alElegir: (ancla: string) => void
}

/**
 * Las secciones de un documento, cada una con cuántos criterios dependen de
 * ella. Ese número es lo que el docente no puede deducir mirando el texto,
 * y por eso es lo único que lleva color.
 */
export function ListaSecciones({ documento, alElegir }: Props) {
  return (
    <ol className="regla-fina">
      {documento.secciones.map((seccion) => (
        <li key={seccion.ancla} className="border-b border-grisclaro">
          <button
            onClick={() => alElegir(seccion.ancla)}
            className="w-full text-left py-4 px-1 hover:bg-white transition-colors"
          >
            <span className="block text-[15px]">{seccion.titulo}</span>
            <span className="block mt-1 text-[12px] uppercase tracking-[0.08em]">
              {seccion.criterios_que_la_citan > 0 ? (
                <span className="senal">
                  {seccion.criterios_que_la_citan} criterios
                </span>
              ) : (
                <span className="text-gris">ningún criterio</span>
              )}
            </span>
          </button>
        </li>
      ))}
    </ol>
  )
}
