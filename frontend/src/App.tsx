import { useState } from "react"

import { Documentos } from "./paginas/Documentos"
import { Editor } from "./paginas/Editor"
import { Estado } from "./paginas/Estado"
import { Pendientes } from "./paginas/Pendientes"

type Vista = "documentos" | "estado" | "pendientes"

export default function App() {
  const [vista, setVista] = useState<Vista>("documentos")
  const [anclaEditando, setAnclaEditando] = useState<string | null>(null)

  const pestanas: { clave: Vista; texto: string }[] = [
    { clave: "documentos", texto: "Documentos" },
    { clave: "estado", texto: "Estado" },
    { clave: "pendientes", texto: "Pendientes" },
  ]

  return (
    <div className="min-h-screen px-8 py-10 md:px-16">
      <header className="mb-12">
        <h1 className="text-[13px] font-semibold uppercase tracking-[0.12em] mb-6">
          Editor de criterios
        </h1>
        <nav className="flex gap-6 regla-fina pt-4">
          {pestanas.map((pestana) => (
            <button
              key={pestana.clave}
              onClick={() => { setVista(pestana.clave); setAnclaEditando(null) }}
              className={
                vista === pestana.clave && !anclaEditando
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
