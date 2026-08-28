import { useState } from "react"

import { Documentos } from "./paginas/Documentos"
import { Editor } from "./paginas/Editor"
import { Entregas } from "./paginas/Entregas"
import { Estado } from "./paginas/Estado"
import { Ficha } from "./paginas/Ficha"
import { Pendientes } from "./paginas/Pendientes"
import type { FichaDeLectura } from "./lib/tipos"

type Vista = "entregas" | "documentos" | "estado" | "pendientes"

export default function App() {
  const [vista, setVista] = useState<Vista>("entregas")
  const [anclaEditando, setAnclaEditando] = useState<string | null>(null)
  // Qué entrega tiene la ficha abierta (Task 14). Cambiar de pestaña la
  // cierra, igual que ya hacía con `anclaEditando`. Al volver de la ficha,
  // Entregas se vuelve a montar y su propio `useEffect` recarga la bandeja
  // -así el archivo que se acaba de confirmar deja de aparecer como
  // pendiente sin que la ficha tenga que saber nada de esa lista.
  //
  // Lleva el identificador y, cuando se llega desde confirmar, la ficha que
  // devolvió esa llamada: es la única que trae los avisos de confirmar, y
  // volver a pedirla por su identificador los borraba. Sigue siendo un solo
  // trozo de estado, así que ponerla a null cierra la ficha igual que antes.
  const [fichaAbierta, setFichaAbierta] = useState<
    { id: string; leida: FichaDeLectura | null } | null
  >(null)

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
        {fichaAbierta ? (
          <Ficha
            id={fichaAbierta.id}
            inicial={fichaAbierta.leida}
            alVolver={() => setFichaAbierta(null)}
          />
        ) : anclaEditando ? (
          <Editor ancla={anclaEditando} alVolver={() => setAnclaEditando(null)} />
        ) : vista === "entregas" ? (
          <Entregas
            alAbrirFicha={(id, leida) => setFichaAbierta({ id, leida: leida ?? null })}
          />
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
