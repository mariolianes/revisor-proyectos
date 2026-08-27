import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { DialogoGuardar } from "./DialogoGuardar"
import type { Propuesta } from "../lib/tipos"

const propuestas: Propuesta[] = [
  {
    fichero: "criteria/v2026-2027/formato.yaml",
    identificador: "extension",
    clave: "minimo_paginas_contenido",
    valor_actual: "20",
    valor_propuesto: "25",
    motivo: "El texto decía «20» y ahora dice «25» en el mismo sitio.",
  },
  {
    fichero: "criteria/v2026-2027/formato.yaml",
    identificador: "tipografia",
    clave: "familia",
    valor_actual: "Arial",
    valor_propuesto: null,
    motivo: "Este valor no es un número, revísalo a mano.",
  },
]

describe("DialogoGuardar", () => {
  it("no deja guardar sin motivo ni fuente", () => {
    render(<DialogoGuardar propuestas={propuestas} alConfirmar={vi.fn()} alCancelar={vi.fn()} />)
    expect(screen.getByRole("button", { name: /guardar/i })).toBeDisabled()
  })

  it("deja guardar cuando estan los dos", () => {
    render(<DialogoGuardar propuestas={propuestas} alConfirmar={vi.fn()} alCancelar={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/por qué/i), { target: { value: "La programación lo sube" } })
    fireEvent.change(screen.getByLabelText(/fuente/i), { target: { value: "Programación 2026-27" } })
    expect(screen.getByRole("button", { name: /guardar/i })).toBeEnabled()
  })

  it("envia solo las propuestas aceptadas", () => {
    const alConfirmar = vi.fn()
    render(<DialogoGuardar propuestas={propuestas} alConfirmar={alConfirmar} alCancelar={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/por qué/i), { target: { value: "motivo" } })
    fireEvent.change(screen.getByLabelText(/fuente/i), { target: { value: "fuente" } })
    fireEvent.click(screen.getByRole("button", { name: /guardar/i }))

    expect(alConfirmar).toHaveBeenCalledWith({
      cambios: [{
        fichero: "criteria/v2026-2027/formato.yaml",
        identificador: "extension",
        clave: "minimo_paginas_contenido",
        valor_nuevo: "25",
      }],
      motivo: "motivo",
      fuente: "fuente",
    })
  })

  it("muestra el motivo de lo que hay que revisar a mano", () => {
    render(<DialogoGuardar propuestas={propuestas} alConfirmar={vi.fn()} alCancelar={vi.fn()} />)
    expect(screen.getByText(/revísalo a mano/i)).toBeInTheDocument()
  })

  it("envia el valor que el profesor escribe en un criterio de revision manual", () => {
    const alConfirmar = vi.fn()
    render(<DialogoGuardar propuestas={propuestas} alConfirmar={alConfirmar} alCancelar={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/valor nuevo de tipografia\.familia/i), {
      target: { value: "Times New Roman" },
    })
    fireEvent.change(screen.getByLabelText(/por qué/i), { target: { value: "motivo" } })
    fireEvent.change(screen.getByLabelText(/fuente/i), { target: { value: "fuente" } })
    fireEvent.click(screen.getByRole("button", { name: /^guardar$/i }))

    expect(alConfirmar).toHaveBeenCalledWith({
      cambios: [
        {
          fichero: "criteria/v2026-2027/formato.yaml",
          identificador: "extension",
          clave: "minimo_paginas_contenido",
          valor_nuevo: "25",
        },
        {
          fichero: "criteria/v2026-2027/formato.yaml",
          identificador: "tipografia",
          clave: "familia",
          valor_nuevo: "Times New Roman",
        },
      ],
      motivo: "motivo",
      fuente: "fuente",
    })
  })

  it("marcar «lo he revisado y no cambia» tambien es una decision", () => {
    const alConfirmar = vi.fn()
    render(<DialogoGuardar propuestas={propuestas} alConfirmar={alConfirmar} alCancelar={vi.fn()} />)

    fireEvent.click(screen.getByLabelText(/sin cambio en tipografia\.familia/i))
    fireEvent.change(screen.getByLabelText(/por qué/i), { target: { value: "motivo" } })
    fireEvent.change(screen.getByLabelText(/fuente/i), { target: { value: "fuente" } })
    fireEvent.click(screen.getByRole("button", { name: /^guardar$/i }))

    const { cambios } = alConfirmar.mock.calls[0][0]
    expect(cambios).toContainEqual({
      fichero: "criteria/v2026-2027/formato.yaml",
      identificador: "tipografia",
      clave: "familia",
      valor_nuevo: null,
    })
  })

  it("mientras se guarda, el boton no admite un segundo clic", () => {
    const alConfirmar = vi.fn()
    render(
      <DialogoGuardar propuestas={propuestas} enviando alConfirmar={alConfirmar}
                      alCancelar={vi.fn()} />,
    )
    fireEvent.change(screen.getByLabelText(/por qué/i), { target: { value: "motivo" } })
    fireEvent.change(screen.getByLabelText(/fuente/i), { target: { value: "fuente" } })

    expect(screen.getByRole("button", { name: /guardando/i })).toBeDisabled()
    expect(alConfirmar).not.toHaveBeenCalled()
  })
})
