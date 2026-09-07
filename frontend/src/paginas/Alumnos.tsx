import { useCallback, useEffect, useState } from "react"

import { api } from "../lib/api"
import { COMUNIDADES } from "../lib/tipos"
import type { ListadoDisponible, ResultadoDeImportacion } from "../lib/tipos"

/**
 * El alta de alumnos desde los Excel del docente.
 *
 * Hasta que esta pantalla existió, dar de alta a los alumnos era una orden de
 * consola que no viajaba dentro del programa: el docente no podía hacerlo
 * solo. Y sin alumnos dados de alta no hay a quién asignar un trabajo, ni
 * nombre que tachar antes de mandar el texto al motor.
 *
 * Los Excel no se suben: se eligen de `00_LISTADOS_ALUMNOS`, que es una
 * carpeta suya. Mismo trato que ya reciben los trabajos.
 *
 * **Ningún nombre aparece en esta pantalla.** Las filas que quedan pendientes
 * de revisión se identifican por su número de fila del Excel -el que él ve al
 * abrirlo- porque la correspondencia nombre-identificador no sale de su
 * equipo. La tinta `senal` se reserva, como en el resto del sistema, a lo que
 * espera una decisión suya: aquí, las filas pendientes.
 */
export function Alumnos() {
  const [listados, setListados] = useState<ListadoDisponible[]>([])
  const [elegido, setElegido] = useState("")
  const [comunidad, setComunidad] = useState<string>(COMUNIDADES[0])
  const [curso, setCurso] = useState("2026-2027")
  const [resultado, setResultado] = useState<ResultadoDeImportacion | null>(null)
  const [error, setError] = useState("")
  const [importando, setImportando] = useState(false)
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback(async () => {
    setCargando(true)
    try {
      const hay = await api.listados()
      setListados(hay)
      setElegido((antes) => antes || hay[0]?.nombre || "")
      setError("")
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo))
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { void cargar() }, [cargar])

  async function importar() {
    if (!elegido || importando) return
    setImportando(true)
    setResultado(null)
    setError("")
    try {
      setResultado(await api.importarListado({
        nombre_archivo: elegido, ccaa_code: comunidad, curso,
      }))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo))
    } finally {
      setImportando(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <p className="prosa mb-8">
        Los listados de matrícula van en la carpeta <code>00_LISTADOS_ALUMNOS</code>,
        un Excel por comunidad. Da igual cómo se llamen las columnas y en qué
        orden vengan.
      </p>

      {error && (
        <p className="mb-6 max-w-lectura text-[13px] text-tinta">{error}</p>
      )}

      <section className="mb-12">
        <h2 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
          Listado que se importa
        </h2>

        {cargando ? (
          <p className="text-[13px] text-gris">Mirando la carpeta…</p>
        ) : listados.length === 0 ? (
          <p className="max-w-lectura text-[13px] text-gris">
            No hay ningún Excel en <code>00_LISTADOS_ALUMNOS</code>. Deja ahí
            los listados de matrícula y vuelve a esta pantalla.
          </p>
        ) : (
          <div className="flex flex-wrap items-end gap-6">
            <label className="block">
              <span className="block text-[11px] uppercase tracking-[0.08em] text-gris mb-1">
                Fichero
              </span>
              <select
                value={elegido}
                onChange={(e) => setElegido(e.target.value)}
                className="border border-grisclaro bg-papel px-2 py-1 text-[13px]"
              >
                {listados.map((l) => (
                  <option key={l.nombre} value={l.nombre}>
                    {l.nombre} · {l.tamano_kb} KB
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="block text-[11px] uppercase tracking-[0.08em] text-gris mb-1">
                Comunidad
              </span>
              <select
                value={comunidad}
                onChange={(e) => setComunidad(e.target.value)}
                className="border border-grisclaro bg-papel px-2 py-1 text-[13px]"
              >
                {COMUNIDADES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="block text-[11px] uppercase tracking-[0.08em] text-gris mb-1">
                Curso
              </span>
              <input
                value={curso}
                onChange={(e) => setCurso(e.target.value)}
                className="w-28 border border-grisclaro bg-papel px-2 py-1 text-[13px]"
              />
            </label>

            <button
              onClick={() => void importar()}
              disabled={importando || !elegido}
              className="px-4 py-2 text-[13px] bg-tinta text-papel disabled:opacity-30"
            >
              {importando ? "Importando…" : "Importar"}
            </button>
          </div>
        )}
      </section>

      {resultado && (
        <section>
          <h2 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
            Resultado
          </h2>
          <p className="mb-6 text-[15px]">
            {resultado.nuevas} alta{resultado.nuevas === 1 ? "" : "s"} ·{" "}
            {resultado.actualizadas} actualizada
            {resultado.actualizadas === 1 ? "" : "s"} ·{" "}
            {resultado.pendientes.length} sin registrar
          </p>

          {resultado.pendientes.length > 0 && (
            <>
              <p className="mb-4 max-w-lectura text-[13px] senal">
                Estas filas no se han registrado. Ninguna se ha asignado a
                nadie: el sistema se detiene antes que dar de alta a la persona
                equivocada. Ábrelas en tu Excel por el número de fila.
              </p>
              <ol className="regla-fina">
                {resultado.pendientes.map((p) => (
                  <li
                    key={`${p.fila}-${p.motivo}`}
                    className="border-b border-grisclaro py-4 px-1"
                  >
                    <span className="block text-[15px]">
                      Fila {p.fila} ·{" "}
                      <span className="text-[12px] uppercase tracking-[0.08em] text-gris">
                        {p.motivo.toLowerCase().replace(/_/g, " ")}
                      </span>
                    </span>
                    <span className="block mt-1 max-w-lectura text-[13px] text-gris">
                      {p.detalle}
                    </span>
                  </li>
                ))}
              </ol>
            </>
          )}
        </section>
      )}
    </div>
  )
}
