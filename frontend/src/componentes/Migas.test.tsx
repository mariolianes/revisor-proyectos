import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { Migas } from "./Migas"

describe("Migas", () => {
  it("la última no es un botón: es donde estás", () => {
    render(
      <Migas migas={[
        { texto: "Entregas", alPulsar: vi.fn() },
        { texto: "Entrega", alPulsar: vi.fn() },
        { texto: "Revisión" },
      ]} />
    )

    expect(screen.getAllByRole("button")).toHaveLength(2)
    expect(screen.getByText("Revisión")).toHaveAttribute("aria-current", "page")
  })

  it("se puede saltar a cualquier nivel anterior, no solo al inmediato", () => {
    // Con dos niveles anidados, tener que salir de uno en uno es justo lo
    // que hacía perderse.
    const aLaBandeja = vi.fn()
    render(
      <Migas migas={[
        { texto: "Entregas", alPulsar: aLaBandeja },
        { texto: "Entrega", alPulsar: vi.fn() },
        { texto: "Revisión" },
      ]} />
    )

    return userEvent.click(screen.getByRole("button", { name: "Entregas" }))
      .then(() => expect(aLaBandeja).toHaveBeenCalledOnce())
  })

  it("una miga sin acción no es pulsable aunque no sea la última", () => {
    render(
      <Migas migas={[
        { texto: "Entregas", alPulsar: vi.fn() },
        { texto: "Entrega" },
        { texto: "Revisión" },
      ]} />
    )

    expect(screen.getAllByRole("button")).toHaveLength(1)
  })
})
