import { useState } from "react"

import { Migas } from "./componentes/Migas"
import type { Miga } from "./componentes/Migas"
import { Alumnos } from "./paginas/Alumnos"
import { Documentos } from "./paginas/Documentos"
import { Editor } from "./paginas/Editor"
import { Entregas } from "./paginas/Entregas"
import { Estado } from "./paginas/Estado"
import { Ficha } from "./paginas/Ficha"
import { Pendientes } from "./paginas/Pendientes"
import { Revision } from "./paginas/Revision"
import type { FichaDeLectura, ResultadoAnalisis } from "./lib/tipos"

type Vista = "entregas" | "alumnos" | "documentos" | "estado" | "pendientes"

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
  // La revisión abierta, con el resultado que trajo el análisis. Se cierra
  // igual que la ficha -al cambiar de pestaña o al volver-, y volver de la
  // revisión deja la ficha detrás sin volver a pedirla: es la misma que
  // estaba abierta antes de analizar.
  const [revisionAbierta, setRevisionAbierta] = useState<
    { id: string; resultado: ResultadoAnalisis } | null
  >(null)

  const nombreDeVista: Record<Vista, string> = {
    entregas: "Entregas",
    alumnos: "Alumnos",
    documentos: "Documentos",
    estado: "Estado",
    pendientes: "Pendientes",
  }

  // Se componen del estado que ya existe -qué pestaña, qué ficha, qué
  // revisión-, no de una fuente nueva: así no puede haber una miga que diga
  // una cosa y una pantalla que enseñe otra.
  const migas: Miga[] = [
    {
      texto: nombreDeVista[vista],
      alPulsar: () => {
        setAnclaEditando(null)
        setFichaAbierta(null)
        setRevisionAbierta(null)
      },
    },
  ]
  if (fichaAbierta || revisionAbierta) {
    migas.push({
      texto: "Entrega",
      alPulsar: revisionAbierta ? () => setRevisionAbierta(null) : undefined,
    })
  }
  if (revisionAbierta) {
    migas.push({ texto: "Revisión" })
  }
  if (anclaEditando) {
    migas.push({ texto: "Editor" })
  }

  const pestanas: { clave: Vista; texto: string }[] = [
    { clave: "entregas", texto: "Entregas" },
    { clave: "alumnos", texto: "Alumnos" },
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
                setRevisionAbierta(null)
              }}
              className={
                vista === pestana.clave
                  ? "text-[13px] border-b-2 border-tinta pb-1"
                  : "text-[13px] text-gris pb-1"
              }
            >
              {pestana.texto}
            </button>
          ))}
        </nav>
      </header>

      {migas.length > 1 && <Migas migas={migas} />}

      <main>
        {revisionAbierta ? (
          <Revision
            id={revisionAbierta.id}
            inicial={revisionAbierta.resultado}
            alVolver={() => setRevisionAbierta(null)}
          />
        ) : fichaAbierta ? (
          <Ficha
            id={fichaAbierta.id}
            inicial={fichaAbierta.leida}
            alVolver={() => setFichaAbierta(null)}
            alAbrirRevision={(id, resultado) => setRevisionAbierta({ id, resultado })}
          />
        ) : anclaEditando ? (
          <Editor ancla={anclaEditando} alVolver={() => setAnclaEditando(null)} />
        ) : vista === "entregas" ? (
          <Entregas
            alAbrirFicha={(id, leida) => setFichaAbierta({ id, leida: leida ?? null })}
          />
        ) : vista === "alumnos" ? (
          <Alumnos />
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
