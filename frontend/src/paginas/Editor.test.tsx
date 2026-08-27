import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { Editor } from "./Editor"
import { api } from "../lib/api"
import type { CriterioDerivado, Propuesta, Seccion } from "../lib/tipos"

vi.mock("../lib/api", () => ({
  api: {
    seccion: vi.fn(),
    propuesta: vi.fn(),
    guardar: vi.fn(),
  },
}))

const seccion: Seccion = {
  ancla: "maestro#8-dimensiones",
  titulo: "8. Dimensiones",
  texto: "Texto original de la sección.",
  hash: "hash-1",
  criterios_que_la_citan: 0,
}

const criterios: CriterioDerivado[] = []

const propuestas: Propuesta[] = [
  {
    fichero: "criteria/v2026-2027/formato.yaml",
    identificador: "extension",
    clave: "minimo_paginas_contenido",
    valor_actual: "20",
    valor_propuesto: "25",
    motivo: "El texto lo sube a 25.",
  },
]

describe("Editor", () => {
  beforeEach(() => {
    vi.mocked(api.seccion).mockResolvedValue({ seccion, criterios })
  })

  it("si falla el guardado, no pierde el texto editado ni el enlace de volver", async () => {
    vi.mocked(api.propuesta).mockResolvedValue(propuestas)
    vi.mocked(api.guardar).mockRejectedValue(
      new Error("No se ha podido contactar con el servidor."),
    )

    render(<Editor ancla="maestro#8-dimensiones" alVolver={vi.fn()} />)

    await screen.findByText("8. Dimensiones")

    const textarea = screen.getByDisplayValue("Texto original de la sección.")
    fireEvent.change(textarea, {
      target: { value: "Texto editado por el profesor, sin guardar todavía." },
    })

    fireEvent.click(screen.getByRole("button", { name: /guardar cambio/i }))

    await screen.findByLabelText(/por qué/i)
    fireEvent.change(screen.getByLabelText(/por qué/i), { target: { value: "motivo" } })
    fireEvent.change(screen.getByLabelText(/fuente/i), { target: { value: "fuente" } })
    fireEvent.click(screen.getByRole("button", { name: /^guardar$/i }))

    await screen.findByText(/no se ha podido contactar con el servidor/i)

    // El texto que el profesor llevaba escrito sigue ahí, sin recargarse ni perderse.
    expect(
      screen.getByDisplayValue("Texto editado por el profesor, sin guardar todavía."),
    ).toBeInTheDocument()
    // El camino de vuelta sigue disponible: no se ha quedado atrapado.
    expect(screen.getByRole("button", { name: /documentos/i })).toBeInTheDocument()
  })
})
