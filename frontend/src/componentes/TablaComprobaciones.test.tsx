import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { TablaComprobaciones } from "./TablaComprobaciones"
import type { Comprobacion } from "../lib/tipos"

const CUMPLE: Comprobacion = {
  criterio: "paginas_en_blanco", veredicto: "CUMPLE",
  esperado: "ninguna página en blanco", medido: "ninguna",
  fuente: "indice#6-formato-y-control", nota: "",
}

const NO_CUMPLE: Comprobacion = {
  criterio: "extension", veredicto: "NO_CUMPLE",
  esperado: "20 páginas de contenido como mínimo",
  medido: "12 páginas de contenido (de 18 en total)",
  fuente: "maestro#6-estandar-academico", nota: "",
}

const NO_VERIFICABLE: Comprobacion = {
  criterio: "interlineado", veredicto: "NO_VERIFICABLE",
  esperado: "1.5 líneas", medido: "ratio medido 1.73 entre líneas base y cuerpo",
  fuente: "maestro#6-estandar-academico",
  nota: "La equivalencia no está fijada en ninguna fuente oficial.",
}

describe("TablaComprobaciones", () => {
  it("enseña lo esperado y lo medido de cada criterio", () => {
    render(<TablaComprobaciones comprobaciones={[NO_CUMPLE]} />)

    expect(screen.getByText(/20 páginas de contenido como mínimo/)).toBeInTheDocument()
    expect(screen.getByText(/12 páginas de contenido/)).toBeInTheDocument()
  })

  it("enseña la fuente de cada criterio", () => {
    render(<TablaComprobaciones comprobaciones={[NO_CUMPLE]} />)

    expect(screen.getByText(/maestro#6-estandar-academico/)).toBeInTheDocument()
  })

  it("enseña la nota cuando la hay", () => {
    render(<TablaComprobaciones comprobaciones={[NO_VERIFICABLE]} />)

    expect(screen.getByText(/no está fijada en ninguna fuente oficial/)).toBeInTheDocument()
  })

  it("distingue un no verificable de un incumplimiento", () => {
    render(<TablaComprobaciones comprobaciones={[NO_CUMPLE, NO_VERIFICABLE]} />)

    expect(screen.getByText(/no cumple/i)).toBeInTheDocument()
    expect(screen.getByText(/no se puede comprobar/i)).toBeInTheDocument()
  })

  it("lo que cumple no lleva la tinta de señal", () => {
    const { container } = render(<TablaComprobaciones comprobaciones={[CUMPLE]} />)

    expect(container.querySelectorAll(".senal")).toHaveLength(0)
  })

  it("lo que no cumple sí la lleva", () => {
    const { container } = render(<TablaComprobaciones comprobaciones={[NO_CUMPLE]} />)

    expect(container.querySelectorAll(".senal").length).toBeGreaterThan(0)
  })

  it("un no verificable tampoco la lleva: no es un fallo del alumno", () => {
    const { container } = render(
      <TablaComprobaciones comprobaciones={[NO_VERIFICABLE]} />,
    )

    expect(container.querySelectorAll(".senal")).toHaveLength(0)
  })
})
