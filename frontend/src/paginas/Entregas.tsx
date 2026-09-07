import { useCallback, useEffect, useState } from "react"

import { ArchivoPendiente } from "../componentes/ArchivoPendiente"
import { api } from "../lib/api"
import type {
  ArchivoVisto, Confirmacion, EntregaRegistrada, Entorno, FichaDeLectura,
} from "../lib/tipos"

/**
 * La bandeja, agrupada por lo que espera del docente y no por si una entrega
 * está registrada o no.
 *
 * El orden de los grupos es el del recorrido del §16.1, y el criterio para
 * agruparlos es una sola pregunta: **¿le toca a él?** Antes había dos listas
 * -pendientes y registradas- y toda la información sobre en qué punto estaba
 * cada trabajo se resumía en una palabra en minúscula al pie de cada fila.
 * Con doscientas entregas eso no se lee.
 *
 * BLOQUEADO va con las que esperan al docente, no aparte: una entrega
 * bloqueada es exactamente algo que él tiene que mirar.
 */
const GRUPOS: { clave: string; titulo: string; estados: string[] }[] = [
  { clave: "analizar", titulo: "Listas para analizar", estados: ["RECIBIDO"] },
  {
    clave: "revisar",
    titulo: "Esperan tu revisión",
    estados: ["ANALIZADO", "BORRADORES_GENERADOS", "EN_REVISION_DOCENTE"],
  },
  { clave: "bloqueadas", titulo: "Bloqueadas", estados: ["BLOQUEADO"] },
  { clave: "cerradas", titulo: "Cerradas", estados: ["APROBADO", "COMUNICADO"] },
]

interface Props {
  /**
   * `leida` es la ficha que devuelve confirmar, y se pasa entera a
   * propósito: lleva los avisos que solo existen al confirmar -que el
   * archivo ya estaba registrado, que el ciclo declarado no es el del
   * alumno- y que no están en `GET /api/entregas/{id}`. Al abrir una
   * entrega de la lista de registradas no hay ficha que pasar, y entonces
   * la pantalla la pide.
   */
  alAbrirFicha: (id: string, leida?: FichaDeLectura) => void
}

/**
 * La bandeja: lo que ha llegado a la carpeta y lo que ya está registrado.
 *
 * `error` recoge un fallo técnico -sin servidor, sin red, un dato que el
 * backend ha rechazado-, no una decisión que le toque al docente, así que
 * no lleva la tinta `senal`: se pinta igual que en Documentos, Estado y
 * Pendientes. `senal` aquí se reserva a los avisos del entorno, al motivo
 * de una propuesta que no se ha podido deducir, al problema de un archivo
 * que no se ha podido leer y a una entrega bloqueada -las cuatro cosas que
 * sí esperan que el docente mire y decida.
 */
export function Entregas({ alAbrirFicha }: Props) {
  const [entorno, setEntorno] = useState<Entorno | null>(null)
  const [pendientes, setPendientes] = useState<ArchivoVisto[]>([])
  const [registradas, setRegistradas] = useState<EntregaRegistrada[]>([])
  const [error, setError] = useState("")
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback(async () => {
    setCargando(true)
    try {
      const [elEntorno, losPendientes, lasRegistradas] = await Promise.all([
        api.entorno(), api.archivosPendientes(), api.entregas(),
      ])
      setEntorno(elEntorno)
      setPendientes(losPendientes)
      setRegistradas(lasRegistradas)
      setError("")
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo))
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { void cargar() }, [cargar])

  async function confirmar(datos: Confirmacion) {
    try {
      const ficha = await api.confirmar(datos)
      alAbrirFicha(ficha.entrega.id, ficha)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo))
    }
  }

  return (
    <div className="max-w-3xl">
      {entorno?.avisos.map((aviso) => (
        <p key={aviso} className="mb-4 max-w-lectura text-[13px] senal">
          {aviso}
        </p>
      ))}

      {error && (
        <p className="mb-6 max-w-lectura text-[13px] text-tinta">{error}</p>
      )}

      <section className="mb-12">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-[12px] uppercase tracking-[0.12em] text-gris">
            Esperan tu confirmación
          </h2>
          {!cargando && (
            <span className="font-mono text-[12px] text-gris">
              {pendientes.length}
            </span>
          )}
        </div>
        {cargando ? (
          <p className="text-[13px] text-gris">Mirando la carpeta…</p>
        ) : pendientes.length === 0 ? (
          <p className="text-[13px] text-gris">
            No hay nada nuevo en la carpeta.
          </p>
        ) : (
          <ul className="regla-fina">
            {pendientes.map((archivo) => (
              <ArchivoPendiente
                key={archivo.nombre}
                archivo={archivo}
                alConfirmar={confirmar}
              />
            ))}
          </ul>
        )}
      </section>

      {GRUPOS.map((grupo) => {
        const suyas = registradas.filter((e) => grupo.estados.includes(e.estado))
        // Un grupo vacío no se pinta salvo que sea el de las cerradas, que
        // sirve de recuento aunque esté a cero. Pintarlos todos llenaría la
        // pantalla de encabezados sin nada debajo, que es justo el ruido que
        // esta agrupación quiere quitar.
        if (suyas.length === 0 && grupo.clave !== "cerradas") return null
        return (
          <section key={grupo.clave} className="mb-12">
            <div className="mb-4 flex items-baseline justify-between">
              <h2 className="text-[12px] uppercase tracking-[0.12em] text-gris">
                {grupo.titulo}
              </h2>
              <span className="font-mono text-[12px] text-gris">
                {suyas.length}
              </span>
            </div>
            {suyas.length === 0 ? (
              <p className="text-[13px] text-gris">Todavía no hay ninguna.</p>
            ) : (
              <ol className="regla-fina">
                {suyas.map((entrega) => (
                  <li key={entrega.id} className="border-b border-grisclaro">
                    <button
                      onClick={() => alAbrirFicha(entrega.id)}
                      className="w-full text-left py-4 px-1 hover:bg-papel transition-colors"
                    >
                      <span className="block text-[15px]">
                        {entrega.codigo_alumno} · {entrega.fase} · versión{" "}
                        {entrega.version}
                      </span>
                      <span className="block mt-1 font-mono text-[12px] text-gris">
                        {entrega.nombre_archivo}
                      </span>
                      <span className="block mt-1 text-[12px] uppercase tracking-[0.08em]">
                        {entrega.estado === "BLOQUEADO" ? (
                          <span className="senal">bloqueada</span>
                        ) : (
                          <span className="text-gris">
                            {entrega.estado.toLowerCase().replace(/_/g, " ")}
                          </span>
                        )}
                      </span>
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </section>
        )
      })}
    </div>
  )
}
