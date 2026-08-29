import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { DialogoGuardar } from "./DialogoGuardar"
import type { CambioDeValor, Propuesta } from "../lib/tipos"

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

/** El mismo caso, pero con la tipografía ya comprobada por el editor. */
const conUnoYaRevisado: Propuesta[] = [
  propuestas[0],
  {
    ...propuestas[1],
    motivo: "El valor sigue apareciendo igual en el texto nuevo.",
    revisado_sin_cambio: true,
  },
  {
    fichero: "criteria/v2026-2027/formato.yaml",
    identificador: "tipografia",
    clave: "cuerpo",
    valor_actual: "11",
    valor_propuesto: null,
    motivo: "El valor ha desaparecido del texto.",
  },
]

/** Tres criterios que hay que decidir, ninguno inferido ni comprobado. */
const tresSinDecidir: Propuesta[] = [
  { ...propuestas[0], valor_propuesto: null, motivo: "Revísalo a mano." },
  propuestas[1],
  {
    fichero: "criteria/v2026-2027/formato.yaml",
    identificador: "tipografia",
    clave: "cuerpo",
    valor_actual: "11",
    valor_propuesto: null,
    motivo: "El valor ha desaparecido del texto.",
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

  it("envia el valor que el profesor escribe en un criterio de revisión manual", () => {
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

  it("marcar «lo he revisado y no cambia» también es una decisión", () => {
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

  it("un criterio que sigue igual en el texto nuevo llega ya marcado", () => {
    const alConfirmar = vi.fn()
    render(
      <DialogoGuardar propuestas={conUnoYaRevisado} alConfirmar={alConfirmar}
                      alCancelar={vi.fn()} />,
    )

    expect(screen.getByLabelText(/sin cambio en tipografia\.familia/i)).toBeChecked()
    // Y sale ya decidido: el aviso solo cuenta el que de verdad falta.
    expect(screen.getByText(/queda 1 criterio sin decidir/i)).toBeInTheDocument()

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

  it("el que llega marcado se puede desmarcar", () => {
    render(
      <DialogoGuardar propuestas={conUnoYaRevisado} alConfirmar={vi.fn()}
                      alCancelar={vi.fn()} />,
    )
    fireEvent.click(screen.getByLabelText(/sin cambio en tipografia\.familia/i))
    expect(screen.getByText(/quedan 2 criterios sin decidir/i)).toBeInTheDocument()
  })

  it("el boton de marcar el resto dice cuantos son y los marca todos", () => {
    const alConfirmar = vi.fn()
    render(<DialogoGuardar propuestas={tresSinDecidir} alConfirmar={alConfirmar}
                           alCancelar={vi.fn()} />)

    // Dice cuántos va a marcar antes de marcarlos.
    const boton = screen.getByRole("button", { name: /he revisado los 3 que quedan/i })
    fireEvent.click(boton)

    expect(screen.queryByText(/sin decidir/i)).not.toBeInTheDocument()
    expect(screen.getByLabelText(/sin cambio en extension\./i)).toBeChecked()
    expect(screen.getByLabelText(/sin cambio en tipografia\.familia/i)).toBeChecked()
    expect(screen.getByLabelText(/sin cambio en tipografia\.cuerpo/i)).toBeChecked()

    fireEvent.change(screen.getByLabelText(/por qué/i), { target: { value: "motivo" } })
    fireEvent.change(screen.getByLabelText(/fuente/i), { target: { value: "fuente" } })
    fireEvent.click(screen.getByRole("button", { name: /^guardar$/i }))

    const { cambios } = alConfirmar.mock.calls[0][0]
    expect(cambios).toHaveLength(3)
    expect(cambios.every((c: CambioDeValor) => c.valor_nuevo === null)).toBe(true)
  })

  it("marcar el resto no pisa lo que el profesor ya habia decidido", () => {
    const alConfirmar = vi.fn()
    render(<DialogoGuardar propuestas={tresSinDecidir} alConfirmar={alConfirmar}
                           alCancelar={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/valor nuevo de tipografia\.cuerpo/i), {
      target: { value: "12" },
    })
    fireEvent.click(screen.getByRole("button", { name: /he revisado los 2 que quedan/i }))

    fireEvent.change(screen.getByLabelText(/por qué/i), { target: { value: "motivo" } })
    fireEvent.change(screen.getByLabelText(/fuente/i), { target: { value: "fuente" } })
    fireEvent.click(screen.getByRole("button", { name: /^guardar$/i }))

    const { cambios } = alConfirmar.mock.calls[0][0]
    expect(cambios).toContainEqual({
      fichero: "criteria/v2026-2027/formato.yaml",
      identificador: "tipografia",
      clave: "cuerpo",
      valor_nuevo: "12",
    })
    expect(cambios.filter((c: CambioDeValor) => c.valor_nuevo === null)).toHaveLength(2)
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
