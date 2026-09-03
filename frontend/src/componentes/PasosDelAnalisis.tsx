/**
 * Qué está pasando mientras se analiza una entrega.
 *
 * Con el motor real esto tarda entre medio minuto y un minuto largo, y hasta
 * ahora la pantalla solo decía «Analizando…». El docente no sabía si el
 * trabajo se había enviado, si su nombre se había enmascarado antes o si
 * quedaba mucho.
 *
 * **Ningún paso se marca como hecho sin saberlo.** Esa es la regla de este
 * componente, y no es una formalidad: si el sistema dice «nombre enmascarado»
 * sin haberlo comprobado, el docente confía en una garantía que quizá no se
 * ha cumplido, y esa es justo la garantía que no puede fallar. Solo se dan
 * por hechos los pasos que ya han ocurrido de verdad -la lectura del PDF, que
 * viene de la ficha, y lo que confirme el resultado cuando llegue-; los
 * demás se enseñan como lo que son: lo que va a pasar.
 */

type Estado = "hecho" | "ahora" | "pendiente"

export interface Paso {
  texto: string
  estado: Estado
}

interface Props {
  pasos: Paso[]
}

const MARCA: Record<Estado, string> = {
  hecho: "·",
  ahora: "●",
  pendiente: "○",
}

export function PasosDelAnalisis({ pasos }: Props) {
  return (
    <ul className="mt-5 max-w-lectura" aria-live="polite">
      {pasos.map((paso) => (
        <li
          key={paso.texto}
          className={
            "flex gap-3 py-[3px] text-[13px] " +
            (paso.estado === "pendiente" ? "text-grisclaro" : "text-gris")
          }
        >
          <span
            aria-hidden="true"
            className={
              "w-3 shrink-0 text-center " +
              (paso.estado === "ahora" ? "text-tinta" : "")
            }
          >
            {MARCA[paso.estado]}
          </span>
          <span className={paso.estado === "ahora" ? "text-tinta" : ""}>
            {paso.texto}
          </span>
        </li>
      ))}
    </ul>
  )
}

/**
 * Los pasos de un análisis en curso.
 *
 * `paginas` viene de la ficha, que ya se leyó antes de pulsar Analizar: por
 * eso ese paso sí puede darse por hecho y decir cuántas páginas eran. El
 * resto todavía no ha ocurrido.
 */
export function pasosEnCurso(paginas: number | null, motor: string | null): Paso[] {
  return [
    {
      texto: paginas
        ? `Documento leído: ${paginas} ${paginas === 1 ? "página" : "páginas"}`
        : "Documento leído",
      estado: "hecho",
    },
    {
      texto: motor
        ? `Analizando con ${motor}…`
        : "Analizando…",
      estado: "ahora",
    },
    { texto: "Comprobar que cada cita existe en el documento", estado: "pendiente" },
    { texto: "Redactar el borrador de devolución", estado: "pendiente" },
  ]
}
