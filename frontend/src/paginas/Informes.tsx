import { useState } from "react"

import { api } from "../lib/api"
import { CICLOS, COMUNIDADES, FASES } from "../lib/tipos"
import type { InformeCentro } from "../lib/tipos"

/**
 * El informe por centro: cobertura, estado del proceso, semáforos y coste.
 *
 * El módulo que lo compone existía desde el punto 7 del orden de implantación
 * y no tenía pantalla: el docente no podía llegar a él.
 *
 * **Ningún nombre aparece aquí, y no por cuidado nuestro: no puede.** El
 * módulo que compone el informe no recibe el listado local en absoluto, así
 * que quien no ha entregado se identifica por su identificador. Si el docente
 * quiere nombres, los resuelve en su equipo.
 *
 * El aviso de grupo pequeño se pinta con la tinta `senal` porque es
 * exactamente lo que esa tinta señala: algo que espera que él lo lea y
 * decida, no una decoración.
 */
export function Informes() {
  const [ccaa, setCcaa] = useState("")
  const [centro, setCentro] = useState("")
  const [ciclo, setCiclo] = useState("")
  const [fase, setFase] = useState("")
  const [curso, setCurso] = useState("2026-2027")
  const [informe, setInforme] = useState<InformeCentro | null>(null)
  const [error, setError] = useState("")
  const [pidiendo, setPidiendo] = useState(false)

  async function pedir() {
    if (pidiendo) return
    setPidiendo(true)
    setError("")
    try {
      setInforme(await api.informeDeCentro({ ccaa, centro, ciclo, fase, curso }))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : String(fallo))
      setInforme(null)
    } finally {
      setPidiendo(false)
    }
  }

  const euros = (valor: number | null) =>
    valor === null ? "—" : `$${valor.toFixed(4)}`

  return (
    <div className="max-w-3xl">
      <p className="prosa mb-8">
        Sin ningún filtro, es el informe del curso entero. Cada filtro que
        pongas lo acota.
      </p>

      <section className="mb-12">
        <div className="flex flex-wrap items-end gap-5">
          <Filtro etiqueta="Comunidad" valor={ccaa} alCambiar={setCcaa}
                  opciones={[...COMUNIDADES]} />
          <Filtro etiqueta="Ciclo" valor={ciclo} alCambiar={setCiclo}
                  opciones={[...CICLOS]} />
          <Filtro etiqueta="Fase" valor={fase} alCambiar={setFase}
                  opciones={[...FASES]} />
          <label className="block">
            <span className="block text-[11px] uppercase tracking-[0.08em] text-gris mb-1">
              Centro
            </span>
            <input
              value={centro}
              onChange={(e) => setCentro(e.target.value)}
              placeholder="AND-MAL-01"
              className="w-32 border border-grisclaro bg-papel px-2 py-1 text-[13px]"
            />
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
            onClick={() => void pedir()}
            disabled={pidiendo}
            className="px-4 py-2 text-[13px] bg-tinta text-papel disabled:opacity-30"
          >
            {pidiendo ? "Componiendo…" : "Ver informe"}
          </button>
        </div>
        {error && (
          <p className="mt-4 max-w-lectura text-[13px] text-tinta">{error}</p>
        )}
      </section>

      {informe && (
        <>
          <Bloque titulo="Cobertura">
            <p className="mb-4 text-[15px]">
              {informe.cobertura.matriculados} matriculado
              {informe.cobertura.matriculados === 1 ? "" : "s"}
              {informe.cobertura.bajas_o_traslados > 0 &&
                ` · ${informe.cobertura.bajas_o_traslados} de baja o trasladado`}
            </p>

            {informe.cobertura.aviso_grupo_pequeno && (
              <p className="mb-4 max-w-lectura text-[13px] senal">
                {informe.cobertura.aviso_grupo_pequeno}
              </p>
            )}

            {informe.cobertura.por_fase.length === 0 ? (
              <p className="text-[13px] text-gris">
                Todavía no hay ninguna entrega registrada con estos filtros.
              </p>
            ) : (
              <ul className="regla-fina">
                {informe.cobertura.por_fase.map((f) => (
                  <li key={f.fase} className="border-b border-grisclaro py-3 px-1">
                    <span className="text-[15px]">
                      {f.fase} · {f.entregados} entregada
                      {f.entregados === 1 ? "" : "s"} · {f.sin_entregar} sin
                      entregar
                    </span>
                    {f.sin_entregar_codigos && f.sin_entregar_codigos.length > 0 && (
                      <span className="mt-1 block font-mono text-[12px] text-gris">
                        {f.sin_entregar_codigos.join(" · ")}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Bloque>

          <Bloque titulo="Estado del proceso">
            <Recuentos datos={informe.proceso.por_estado} />
          </Bloque>

          <Bloque titulo="Semáforos">
            <p className="mb-2 text-[11px] uppercase tracking-[0.08em] text-gris">
              Propuestos por el sistema
            </p>
            <Recuentos datos={informe.semaforos.propuestos} />
            <p className="mt-6 mb-2 text-[11px] uppercase tracking-[0.08em] text-gris">
              Confirmados por ti
            </p>
            <Recuentos datos={informe.semaforos.confirmados_por_docente} />
            {informe.semaforos.pendientes_de_confirmar > 0 && (
              <p className="mt-4 text-[13px] senal">
                {informe.semaforos.pendientes_de_confirmar} esperan que
                confirmes su color.
              </p>
            )}
          </Bloque>

          <Bloque titulo="Coste">
            <table className="w-full text-[13px]">
              <tbody>
                <Fila etiqueta="Total" valor={euros(informe.coste.coste_total_usd)} />
                <Fila etiqueta="Por análisis principal"
                      valor={euros(informe.coste.coste_medio_analisis_principal_usd)} />
                <Fila etiqueta="Por verificación"
                      valor={euros(informe.coste.coste_medio_verificacion_usd)} />
                <Fila etiqueta="Por reanálisis"
                      valor={euros(informe.coste.coste_medio_reanalisis_usd)} />
                <Fila etiqueta="Proyección mensual"
                      valor={euros(informe.coste.proyeccion_mensual_usd)} />
                <Fila etiqueta="Proyección anual"
                      valor={euros(informe.coste.proyeccion_anual_usd)} />
                <Fila etiqueta="Tokens"
                      valor={`${informe.coste.tokens_entrada.toLocaleString("es")} entrada · ${informe.coste.tokens_salida.toLocaleString("es")} salida`} />
                <Fila etiqueta="Motor"
                      valor={Object.entries(informe.coste.modelos)
                        .map(([m, n]) => `${m} (${n})`).join(", ") || "—"} />
              </tbody>
            </table>

            {informe.coste.ejecuciones_sin_coste_calculable > 0 && (
              <p className="mt-4 max-w-lectura text-[13px] senal">
                {informe.coste.ejecuciones_sin_coste_calculable} análisis sin
                coste calculable: su modelo no está en la tabla de tarifas. El
                sistema no inventa un precio.
              </p>
            )}
            {informe.coste.notas.map((nota) => (
              <p key={nota} className="mt-3 max-w-lectura text-[13px] text-gris">
                {nota}
              </p>
            ))}
          </Bloque>
        </>
      )}
    </div>
  )
}

function Filtro({ etiqueta, valor, alCambiar, opciones }: {
  etiqueta: string
  valor: string
  alCambiar: (v: string) => void
  opciones: string[]
}) {
  return (
    <label className="block">
      <span className="block text-[11px] uppercase tracking-[0.08em] text-gris mb-1">
        {etiqueta}
      </span>
      <select
        value={valor}
        onChange={(e) => alCambiar(e.target.value)}
        className="border border-grisclaro bg-papel px-2 py-1 text-[13px]"
      >
        <option value="">Todas</option>
        {opciones.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  )
}

function Bloque({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="mb-12">
      <h2 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
        {titulo}
      </h2>
      {children}
    </section>
  )
}

function Recuentos({ datos }: { datos: Record<string, number> }) {
  const entradas = Object.entries(datos).filter(([, n]) => n > 0)
  if (entradas.length === 0) {
    return <p className="text-[13px] text-gris">Ninguno todavía.</p>
  }
  return (
    <ul className="flex flex-wrap gap-x-8 gap-y-2">
      {entradas.map(([clave, n]) => (
        <li key={clave} className="text-[15px]">
          <span className="font-mono">{n}</span>{" "}
          <span className="text-[12px] uppercase tracking-[0.08em] text-gris">
            {clave.toLowerCase().replace(/_/g, " ")}
          </span>
        </li>
      ))}
    </ul>
  )
}

function Fila({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <tr className="border-b border-grisclaro">
      <td className="py-2 text-gris">{etiqueta}</td>
      <td className="py-2 text-right font-mono">{valor}</td>
    </tr>
  )
}
