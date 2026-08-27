import { useEffect, useState } from "react"

import { api } from "../lib/api"
import type { EstadoGobernanza } from "../lib/tipos"

export function Estado() {
  const [estado, setEstado] = useState<EstadoGobernanza | null>(null)

  useEffect(() => { api.estado().then(setEstado) }, [])

  if (!estado) return <p className="text-gris">Cargando…</p>

  return (
    <div className="max-w-lectura">
      <p className="text-[15px] mb-8">
        {estado.conforme
          ? "El repositorio está conforme: ninguna regla encuentra nada."
          : "Hay infracciones sin resolver."}
      </p>

      <ul className="regla-fina">
        {estado.reglas.map((regla) => (
          <li key={regla.codigo} className="border-b border-grisclaro py-5">
            <div className="flex items-baseline gap-3">
              <span className="font-mono text-[12px] text-gris">{regla.codigo}</span>
              <h3 className="text-[15px]">{regla.nombre}</h3>
              {regla.infracciones > 0 && (
                // El recuento de infracciones no es la relación sección↔criterios:
                // la única tinta de color (senal) no se usa aquí.
                <span className="text-tinta text-[12px]">{regla.infracciones}</span>
              )}
            </div>
            <p className="text-[13px] mt-2">{regla.vigila}</p>
            <p className="text-[13px] text-gris mt-1">
              <span className="uppercase tracking-[0.08em] text-[11px]">
                No cubre:{" "}
              </span>
              {regla.limite}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}
