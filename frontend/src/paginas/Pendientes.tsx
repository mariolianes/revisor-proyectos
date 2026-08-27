import { useEffect, useState } from "react"

import { api } from "../lib/api"
import type { Pendiente } from "../lib/tipos"

export function Pendientes() {
  const [pendientes, setPendientes] = useState<Pendiente[]>([])

  useEffect(() => { api.pendientes().then(setPendientes) }, [])

  return (
    <div className="max-w-lectura">
      <p className="text-[15px] mb-8">
        Lo que el sistema no sabe y no va a inventar. Cuando llegue la
        programación oficial, esta lista dice qué desbloquea.
      </p>

      <ul className="regla-fina">
        {pendientes.map((pendiente) => (
          <li key={pendiente.clave} className="border-b border-grisclaro py-4">
            {/* Ni aviso ni error: es un rótulo. No lleva la tinta de color,
                reservada a la relación sección↔criterios. */}
            <p className="font-mono text-[13px]">{pendiente.clave}</p>
            <p className="text-[13px] text-gris mt-1">{pendiente.explicacion}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
