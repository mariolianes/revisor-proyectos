import { useEffect, useState } from "react"

import { api } from "../lib/api"
import type { Pendiente } from "../lib/tipos"

export function Pendientes() {
  const [pendientes, setPendientes] = useState<Pendiente[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.pendientes().then(setPendientes).catch((e: Error) => setError(e.message))
  }, [])

  // Sin esto, un fallo al pedir la lista pintaba la cabecera -«lo que el
  // sistema no sabe y no va a inventar»- encima de una lista vacía, y eso se
  // lee como «no hay nada pendiente»: una afirmación falsa y confiada sobre
  // lo único que esta pantalla existe para contar.
  if (error) return <p className="text-tinta">{error}</p>
  if (!pendientes) return <p className="text-gris">Cargando…</p>

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
