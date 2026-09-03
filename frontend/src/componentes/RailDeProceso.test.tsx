import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { PELDANOS, RailDeProceso } from "./RailDeProceso"

describe("RailDeProceso", () => {
  it("enseña los peldaños del recorrido, en orden", () => {
    render(<RailDeProceso estado="RECIBIDO" />)

    const textos = screen
      .getAllByRole("listitem")
      .map((li) => li.textContent?.trim())

    expect(textos).toEqual([
      "Recibida (está aquí)", "Analizada", "Con borrador", "En revisión",
      "Aprobada",
    ])
  })

  it("marca dónde está la entrega", () => {
    render(<RailDeProceso estado="ANALIZADO" />)

    expect(screen.getByText(/está aquí/)).toBeInTheDocument()
    expect(screen.getByText("Analizada").textContent).toContain("está aquí")
  })

  it("una entrega bloqueada no ocupa ningún peldaño", () => {
    render(<RailDeProceso estado="BLOQUEADO" />)

    // Ni «Bloqueada» entre dos peldaños -daría a entender que toda entrega
    // pasa por ahí- ni un «está aquí» en ninguno de los cinco.
    expect(screen.queryByText(/está aquí/)).not.toBeInTheDocument()
    expect(screen.getByText(/Fuera del recorrido/)).toBeInTheDocument()
  })

  it("no repite el motivo del bloqueo", () => {
    // La ficha ya lo dice entero. Verlo dos veces en la misma pantalla hace
    // dudar de si son dos problemas distintos.
    render(<RailDeProceso estado="BLOQUEADO" />)

    expect(screen.getByText(/Fuera del recorrido/).textContent).toBe(
      "Fuera del recorrido: bloqueada."
    )
  })

  it("un estado que no está en el recorrido no marca nada", () => {
    // COMUNICADO existe en el §16.1 pero D-004 lo deja abierto y el raíl
    // termina en APROBADO. Que llegue no debe pintar un peldaño equivocado.
    render(<RailDeProceso estado="COMUNICADO" />)

    expect(screen.queryByText(/está aquí/)).not.toBeInTheDocument()
  })

  it("el recorrido no incluye BLOQUEADO como peldaño", () => {
    expect(PELDANOS.map((p) => p.estado)).not.toContain("BLOQUEADO")
  })
})
