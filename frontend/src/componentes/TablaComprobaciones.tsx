import type { Comprobacion } from "../lib/tipos"

const ROTULOS: Record<Comprobacion["veredicto"], string> = {
  CUMPLE: "cumple",
  NO_CUMPLE: "no cumple",
  NO_VERIFICABLE: "no se puede comprobar",
}

/**
 * Cada criterio de formato con lo que se esperaba, lo que se midió y de
 * dónde sale.
 *
 * La tinta de señal marca solo lo que no cumple. Un «no se puede comprobar»
 * no la lleva: no es un fallo del alumno, es un hueco del sistema, y
 * pintarlo igual que un incumplimiento haría que el docente los confundiera.
 */
export function TablaComprobaciones({
  comprobaciones,
}: { comprobaciones: Comprobacion[] }) {
  return (
    <ol className="regla-fina">
      {comprobaciones.map((comprobacion) => (
        <li key={comprobacion.criterio} className="border-b border-grisclaro py-4">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <span className="text-[15px]">
              {comprobacion.criterio.replace(/_/g, " ")}
            </span>
            <span
              className={
                comprobacion.veredicto === "NO_CUMPLE"
                  ? "senal text-[12px] uppercase tracking-[0.08em]"
                  : "text-gris text-[12px] uppercase tracking-[0.08em]"
              }
            >
              {ROTULOS[comprobacion.veredicto]}
            </span>
          </div>
          <dl className="mt-2 max-w-lectura text-[13px]">
            <div className="flex gap-3">
              <dt className="text-gris w-24 shrink-0">Se pide</dt>
              <dd>{comprobacion.esperado}</dd>
            </div>
            <div className="flex gap-3 mt-1">
              <dt className="text-gris w-24 shrink-0">Se ha medido</dt>
              <dd>{comprobacion.medido}</dd>
            </div>
            <div className="flex gap-3 mt-1">
              <dt className="text-gris w-24 shrink-0">Sale de</dt>
              <dd className="font-mono text-[12px] text-gris">
                {comprobacion.fuente}
              </dd>
            </div>
          </dl>
          {comprobacion.nota && (
            <p className="mt-2 max-w-lectura text-[12px] text-gris">
              {comprobacion.nota}
            </p>
          )}
        </li>
      ))}
    </ol>
  )
}
