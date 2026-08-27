import { useEffect, useState } from "react"

import { ListaSecciones } from "../componentes/ListaSecciones"
import { api } from "../lib/api"
import type { Documento } from "../lib/tipos"

interface Props {
  alElegirSeccion: (ancla: string) => void
}

export function Documentos({ alElegirSeccion }: Props) {
  const [documentos, setDocumentos] = useState<Documento[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.documentos().then(setDocumentos).catch((e: Error) => setError(e.message))
  }, [])

  if (error) return <p className="text-tinta">{error}</p>

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
      {documentos.map((documento) => (
        <section key={documento.clave}>
          <h2 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-gris mb-1">
            {documento.titulo}
          </h2>
          <p className="font-mono text-[11px] text-gris mb-4">{documento.fichero}</p>
          <ListaSecciones documento={documento} alElegir={alElegirSeccion} />
        </section>
      ))}
    </div>
  )
}
