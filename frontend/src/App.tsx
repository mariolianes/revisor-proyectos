import { useState } from "react"

import { Documentos } from "./paginas/Documentos"
import { Editor } from "./paginas/Editor"
import { Entregas } from "./paginas/Entregas"
import { Estado } from "./paginas/Estado"
import { Pendientes } from "./paginas/Pendientes"

type Vista = "entregas" | "documentos" | "estado" | "pendientes"

export default function App() {
  const [vista, setVista] = useState<Vista>("entregas")
  const [anclaEditando, setAnclaEditando] = useState<string | null>(null)
  // La ficha de una entrega confirmada es de la Task 14 (componente Ficha,
  // todavía sin escribir). Aquí se guarda igualmente qué entrega se acaba
  // de confirmar, para que esa tarea solo tenga que añadir la rama que la
  // muestra; hasta entonces la bandeja de Entregas sigue visible tras
  // confirmar, y la pestaña funciona sin la ficha.
  const [fichaAbierta, setFichaAbierta] = useState<string | null>(null)

  const pestanas: { clave: Vista; texto: string }[] = [
    { clave: "entregas", texto: "Entregas" },
    { clave: "documentos", texto: "Documentos" },
    { clave: "estado", texto: "Estado" },
    { clave: "pendientes", texto: "Pendientes" },
  ]

  return (
    <div className="min-h-screen px-8 py-10 md:px-16">
      <header className="mb-12">
        <h1 className="text-[13px] font-semibold uppercase tracking-[0.12em] mb-6">
          Revisor de proyectos
        </h1>
        <nav className="flex gap-6 regla-fina pt-4">
          {pestanas.map((pestana) => (
            <button
              key={pestana.clave}
              onClick={() => {
                setVista(pestana.clave)
                setAnclaEditando(null)
                setFichaAbierta(null)
              }}
              className={
                vista === pestana.clave && !anclaEditando && !fichaAbierta
                  ? "text-[13px] border-b-2 border-tinta pb-1"
                  : "text-[13px] text-gris pb-1"
              }
            >
              {pestana.texto}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {anclaEditando ? (
          <Editor ancla={anclaEditando} alVolver={() => setAnclaEditando(null)} />
        ) : vista === "entregas" ? (
          <Entregas alAbrirFicha={setFichaAbierta} />
        ) : vista === "documentos" ? (
          <Documentos alElegirSeccion={setAnclaEditando} />
        ) : vista === "estado" ? (
          <Estado />
        ) : (
          <Pendientes />
        )}
      </main>
    </div>
  )
}
