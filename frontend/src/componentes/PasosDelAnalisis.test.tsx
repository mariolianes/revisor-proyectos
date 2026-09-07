import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { PasosDelAnalisis, pasosEnCurso } from "./PasosDelAnalisis"

describe("pasosEnCurso", () => {
  it("solo da por hecho lo que ya ha ocurrido", () => {
    // Es la regla del componente, y no es una formalidad: si dice «citas
    // comprobadas» antes de comprobarlas, el docente confía en una garantía
    // que quizá no se ha cumplido.
    const pasos = pasosEnCurso(48, "openai:gpt-5.6-luna")

    const hechos = pasos.filter((p) => p.estado === "hecho")
    expect(hechos).toHaveLength(1)
    expect(hechos[0].texto).toContain("48 páginas")
  })

  it("nunca da por hechas la verificación de citas ni el borrador", () => {
    const pasos = pasosEnCurso(48, "openai:gpt-5.6-luna")

    const pendientes = pasos.filter((p) => p.estado === "pendiente")
    expect(pendientes.map((p) => p.texto)).toEqual([
      "Comprobar que cada cita existe en el documento",
      "Redactar el borrador de devolución",
    ])
  })

  it("dice con qué motor está analizando", () => {
    const pasos = pasosEnCurso(48, "openai:gpt-5.6-luna")

    expect(pasos.find((p) => p.estado === "ahora")?.texto).toContain(
      "openai:gpt-5.6-luna"
    )
  })

  it("sin saber el motor, no se lo inventa", () => {
    const pasos = pasosEnCurso(48, null)

    expect(pasos.find((p) => p.estado === "ahora")?.texto).toBe("Analizando…")
  })

  it("sin saber las páginas, no dice un número", () => {
    const pasos = pasosEnCurso(null, "simulado")

    expect(pasos[0].texto).toBe("Documento leído")
  })

  it("una sola página no se dice en plural", () => {
    expect(pasosEnCurso(1, null)[0].texto).toBe("Documento leído: 1 página")
  })
})

describe("PasosDelAnalisis", () => {
  it("enseña los pasos en orden", () => {
    render(<PasosDelAnalisis pasos={pasosEnCurso(48, "simulado")} />)

    expect(screen.getByText(/48 páginas/)).toBeInTheDocument()
    expect(screen.getByText(/Analizando con simulado/)).toBeInTheDocument()
    expect(screen.getByText(/cada cita existe/)).toBeInTheDocument()
  })

  it("se anuncia a un lector de pantalla mientras cambia", () => {
    // Sin esto, quien no ve la pantalla no se entera de que algo avanza
    // durante el minuto que tarda el análisis.
    const { container } = render(
      <PasosDelAnalisis pasos={pasosEnCurso(48, "simulado")} />
    )

    expect(container.querySelector("[aria-live='polite']")).not.toBeNull()
  })
})
