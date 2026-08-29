import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { Estado } from "./Estado"
import { api } from "../lib/api"

vi.mock("../lib/api", () => ({
  api: {
    estado: vi.fn(),
  },
}))

function regla(sobreescritura: Partial<{
  codigo: string
  nombre: string
  vigila: string
  limite: string
  estado: string
  infracciones: number
  detalles: { regla: string; fichero: string; detalle: string }[]
}> = {}) {
  return {
    codigo: "R1",
    nombre: "Una regla",
    vigila: "Lo que vigila.",
    limite: "Lo que no cubre.",
    estado: "verificada",
    infracciones: 0,
    detalles: [],
    ...sobreescritura,
  }
}

describe("Estado", () => {
  it("no llama pendiente a una regla parcial", async () => {
    // R7 no está ni completa ni sin hacer: protege una parte real del §13
    // -la nota, el apto/no apto, la autoría- y deja otra sin construir. Antes
    // de esta corrección la pantalla trataba cualquier estado distinto de
    // "verificada" como "pendiente", así que una regla parcial habría salido
    // diciendo que no protege nada, que es tan falso como decir que protege
    // todo.
    vi.mocked(api.estado).mockResolvedValue({
      conforme: true,
      reglas: [
        regla({ codigo: "R7", estado: "parcial", vigila: "Ya bloquea la nota." }),
      ],
    })

    render(<Estado />)

    expect(await screen.findByText("R7")).toBeInTheDocument()
    expect(screen.getByText("parcial")).toBeInTheDocument()
    expect(screen.queryByText("pendiente")).not.toBeInTheDocument()
    expect(screen.getByText("Ya bloquea la nota.")).toBeInTheDocument()
    expect(screen.queryByText(/Protegerá:/)).not.toBeInTheDocument()
  })

  it("antepone «Protegerá:» solo a lo que todavía no vigila nada", async () => {
    vi.mocked(api.estado).mockResolvedValue({
      conforme: true,
      reglas: [
        regla({ codigo: "R9", estado: "pendiente", vigila: "Nada, todavía." }),
      ],
    })

    render(<Estado />)

    expect(await screen.findByText(/Protegerá:/)).toBeInTheDocument()
  })

  it("no dice «protegerá» de una regla ya verificada", async () => {
    vi.mocked(api.estado).mockResolvedValue({
      conforme: true,
      reglas: [regla({ codigo: "R1", estado: "verificada" })],
    })

    render(<Estado />)

    await screen.findByText("R1")
    expect(screen.queryByText(/Protegerá:/)).not.toBeInTheDocument()
  })
})
