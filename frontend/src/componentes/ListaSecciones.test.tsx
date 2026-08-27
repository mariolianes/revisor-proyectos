import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { ListaSecciones } from "./ListaSecciones"
import type { Documento } from "../lib/tipos"

const documento: Documento = {
  clave: "maestro",
  titulo: "Documento Maestro",
  fichero: "docs/maestro/01-documento-maestro.md",
  secciones: [
    { ancla: "maestro#8-dimensiones", titulo: "8. Dimensiones", texto: "", hash: "a", criterios_que_la_citan: 12 },
    { ancla: "maestro#19-privacidad", titulo: "19. Privacidad", texto: "", hash: "b", criterios_que_la_citan: 0 },
  ],
}

describe("ListaSecciones", () => {
  it("muestra cuantos criterios cita cada seccion", () => {
    render(<ListaSecciones documento={documento} alElegir={vi.fn()} />)
    expect(screen.getByText("12 criterios")).toBeInTheDocument()
  })

  it("dice explicitamente cuando una seccion no la cita nadie", () => {
    render(<ListaSecciones documento={documento} alElegir={vi.fn()} />)
    expect(screen.getByText("ningún criterio")).toBeInTheDocument()
  })

  it("avisa al elegir una seccion", async () => {
    const alElegir = vi.fn()
    render(<ListaSecciones documento={documento} alElegir={alElegir} />)
    screen.getByText("8. Dimensiones").click()
    expect(alElegir).toHaveBeenCalledWith("maestro#8-dimensiones")
  })
})
