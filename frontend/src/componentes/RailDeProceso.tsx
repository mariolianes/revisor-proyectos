/**
 * Dónde está una entrega dentro del recorrido del §16.1.
 *
 * El recorrido tiene siete estados y solo seis son una línea: BLOQUEADO no
 * viene después de RECIBIDO, es una salida de la vía. Por eso no ocupa un
 * peldaño -pintarlo entre dos daría a entender que toda entrega pasa por
 * ahí- y se dice aparte, con la tinta `senal`, que es lo que se reserva a lo
 * que espera una decisión del docente.
 *
 * COMUNICADO tampoco se pinta como alcanzable todavía: D-004 lo deja abierto
 * -no está decidido por qué canal llega el feedback al alumno-, así que el
 * raíl termina en APROBADO.
 *
 * El motivo del bloqueo NO se repite aquí: la ficha ya lo dice con todas sus
 * letras, y verlo dos veces en la misma pantalla hace dudar de si son dos
 * problemas distintos.
 */

// Los peldaños, en el orden del §16.1 y con el nombre que lee el docente,
// no el de la columna de la base de datos.
export const PELDANOS: { estado: string; texto: string }[] = [
  { estado: "RECIBIDO", texto: "Recibida" },
  { estado: "ANALIZADO", texto: "Analizada" },
  { estado: "BORRADORES_GENERADOS", texto: "Con borrador" },
  { estado: "EN_REVISION_DOCENTE", texto: "En revisión" },
  { estado: "APROBADO", texto: "Aprobada" },
]

interface Props {
  estado: string
}

export function RailDeProceso({ estado }: Props) {
  const bloqueada = estado === "BLOQUEADO"
  // Una entrega bloqueada llegó a estar recibida: se pinta el primer peldaño
  // como alcanzado y el resto sin alcanzar, con el motivo debajo.
  const alcanzado = bloqueada
    ? 0
    : PELDANOS.findIndex((p) => p.estado === estado)

  return (
    <div className="mb-8">
      <ol className="flex items-start" aria-label="Recorrido de la entrega">
        {PELDANOS.map((peldano, i) => {
          const hecho = alcanzado >= 0 && i <= alcanzado
          const actual = i === alcanzado && !bloqueada
          return (
            <li key={peldano.estado} className="flex-1 min-w-0">
              <div className="flex items-center" aria-hidden="true">
                <span
                  className={
                    "h-[7px] w-[7px] shrink-0 rounded-full " +
                    (hecho ? "bg-tinta" : "border border-grisclaro bg-papel")
                  }
                />
                {i < PELDANOS.length - 1 && (
                  <span
                    className={
                      "h-px flex-1 " +
                      (alcanzado > i ? "bg-tinta" : "bg-grisclaro")
                    }
                  />
                )}
              </div>
              <span
                className={
                  "mt-2 block pr-3 text-[11px] uppercase tracking-[0.08em] " +
                  (actual
                    ? "text-tinta"
                    : hecho
                      ? "text-gris"
                      : "text-grisclaro")
                }
              >
                {peldano.texto}
                {actual && <span className="sr-only"> (está aquí)</span>}
              </span>
            </li>
          )
        })}
      </ol>

      {bloqueada && (
        <p className="mt-4 max-w-lectura text-[13px] senal">
          Fuera del recorrido: bloqueada.
        </p>
      )}
    </div>
  )
}
