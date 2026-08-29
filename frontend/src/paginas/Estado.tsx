import { useEffect, useState } from "react"

import { api } from "../lib/api"
import type { EstadoGobernanza } from "../lib/tipos"

export function Estado() {
  const [estado, setEstado] = useState<EstadoGobernanza | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.estado().then(setEstado).catch((e: Error) => setError(e.message))
  }, [])

  if (error) return <p className="text-tinta">{error}</p>
  if (!estado) return <p className="text-gris">Cargando…</p>

  const pendientes = estado.reglas.filter((regla) => regla.estado === "pendiente")
  const parciales = estado.reglas.filter((regla) => regla.estado === "parcial")

  return (
    <div className="max-w-lectura">
      {/* La conformidad se afirma solo de las reglas que existen. Decir «el
          repositorio está conforme» a secas incluiría a las que todavía no
          vigilan nada, que es prometer más de lo que se cumple. */}
      <p className="text-[15px] mb-2">
        {estado.conforme
          ? "Ninguna de las reglas que ya funcionan encuentra nada."
          : "Hay infracciones sin resolver."}
      </p>
      {pendientes.length > 0 && (
        <p className="text-[13px] text-gris mb-2">
          {pendientes.map((regla) => regla.codigo).join(", ")} está escrita en
          GOVERNANCE.md pero todavía no comprueba nada, así que lo que protege
          no lo vigila nadie por ahora.
        </p>
      )}
      {parciales.length > 0 && (
        <p className="text-[13px] text-gris mb-8">
          {parciales.map((regla) => regla.codigo).join(", ")} protege una
          parte real de lo que promete; su ficha dice qué cubre ya y qué no
          cubre todavía.
        </p>
      )}

      <ul className="regla-fina">
        {estado.reglas.map((regla) => (
          <li key={regla.codigo} className="border-b border-grisclaro py-5">
            <div className="flex items-baseline gap-3">
              <span className="font-mono text-[12px] text-gris">{regla.codigo}</span>
              <h3 className="text-[15px]">{regla.nombre}</h3>
              {regla.estado !== "verificada" && (
                <span className="text-[12px] text-gris uppercase tracking-[0.08em]">
                  {regla.estado}
                </span>
              )}
              {regla.infracciones > 0 && (
                // El recuento de infracciones no es la relación sección↔criterios:
                // la única tinta de color (senal) no se usa aquí.
                <span className="text-tinta text-[12px]">{regla.infracciones}</span>
              )}
            </div>
            <p className="text-[13px] mt-2">
              {regla.estado === "pendiente" ? "Protegerá: " : ""}
              {regla.vigila}
            </p>

            {/* El número solo dice que hay algo mal en alguna parte. Lo que
                se puede arreglar es el fichero y el detalle, que es el mismo
                texto que imprime el verificador. */}
            {regla.detalles.length > 0 && (
              <ul className="mt-3 space-y-2">
                {regla.detalles.map((infraccion, indice) => (
                  <li key={indice} className="text-[12px]">
                    <span className="font-mono text-gris">{infraccion.fichero}</span>
                    <p className="text-gris mt-1">{infraccion.detalle}</p>
                  </li>
                ))}
              </ul>
            )}

            <p className="text-[13px] mt-2 pt-2 border-t border-grisclaro">
              No cubre: {regla.limite}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}
