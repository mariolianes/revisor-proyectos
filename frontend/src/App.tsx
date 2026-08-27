import { useState } from "react"

import { Documentos } from "./paginas/Documentos"

function App() {
  const [seccionElegida, setSeccionElegida] = useState<string | null>(null)

  return (
    <main className="min-h-screen bg-papel px-8 py-12">
      <header className="regla-fina pb-4 mb-8">
        <h1 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-gris">
          Editor de criterios
        </h1>
      </header>
      <Documentos alElegirSeccion={setSeccionElegida} />
      {seccionElegida && (
        <p className="mt-8 font-mono text-[11px] text-gris">
          Sección elegida: {seccionElegida}
        </p>
      )}
    </main>
  )
}

export default App
