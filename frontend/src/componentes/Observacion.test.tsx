import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { Observacion } from "./Observacion"
import type { EstadoDeLaDecision } from "./Observacion"
import type { ValoracionVerificada } from "../lib/tipos"

const VALORACION: ValoracionVerificada = {
  dimension: "D05",
  nivel: "EN_DESARROLLO",
  prioridad: "P2",
  evidencia: {
    cita: "El presupuesto inicial asciende a 4.500 euros",
    apartado: "5. Viabilidad económica",
  },
  observacion: "Faltan fuentes que respalden las cifras del presupuesto.",
  evidencia_localizada: true,
}

const ACEPTADA: EstadoDeLaDecision = {
  decision: "ACEPTADA",
  texto: VALORACION.observacion,
}

describe("Observacion", () => {
  it("enseña dimensión, nivel, prioridad, cita y observación", () => {
    render(<Observacion valoracion={VALORACION} estado={ACEPTADA} alCambiar={vi.fn()} />)

    expect(screen.getByText("D05")).toBeInTheDocument()
    expect(screen.getByText("P2")).toBeInTheDocument()
    expect(screen.getByText(/en desarrollo/i)).toBeInTheDocument()
    expect(screen.getByText(/4\.500 euros/)).toBeInTheDocument()
    expect(screen.getByText(/faltan fuentes/i)).toBeInTheDocument()
  })

  it("tiene los tres botones", () => {
    render(<Observacion valoracion={VALORACION} estado={ACEPTADA} alCambiar={vi.fn()} />)

    expect(screen.getByRole("button", { name: /aceptar/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^editar$/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /descartar/i })).toBeInTheDocument()
  })

  it("aceptar avisa con la decisión ACEPTADA", () => {
    const alCambiar = vi.fn()
    render(<Observacion valoracion={VALORACION} estado={ACEPTADA} alCambiar={alCambiar} />)

    fireEvent.click(screen.getByRole("button", { name: /aceptar/i }))

    expect(alCambiar).toHaveBeenCalledWith({
      decision: "ACEPTADA", texto: VALORACION.observacion,
    })
  })

  it("descartar avisa con la decisión DESCARTADA", () => {
    const alCambiar = vi.fn()
    render(<Observacion valoracion={VALORACION} estado={ACEPTADA} alCambiar={alCambiar} />)

    fireEvent.click(screen.getByRole("button", { name: /^descartar$/i }))

    expect(alCambiar).toHaveBeenCalledWith({
      decision: "DESCARTADA", texto: VALORACION.observacion,
    })
  })

  it("una observación descartada se ve apagada", () => {
    const { container } = render(
      <Observacion
        valoracion={VALORACION}
        estado={{ decision: "DESCARTADA", texto: VALORACION.observacion }}
        alCambiar={vi.fn()}
      />,
    )

    expect(container.querySelector("li")).toHaveClass("opacity-40")
  })

  it("pulsar editar pide pasar a EDITADA con el texto original", () => {
    // Observacion es un componente controlado: quien decide si se
    // repinta en modo edición es quien lo usa, guardando el estado que
    // este callback pide. Aquí solo se comprueba la petición.
    const alCambiar = vi.fn()
    render(<Observacion valoracion={VALORACION} estado={ACEPTADA} alCambiar={alCambiar} />)

    fireEvent.click(screen.getByRole("button", { name: /^editar$/i }))

    expect(alCambiar).toHaveBeenCalledWith({
      decision: "EDITADA", texto: VALORACION.observacion,
    })
  })

  it("en modo edición, el área de texto lleva el texto original", () => {
    render(
      <Observacion
        valoracion={VALORACION}
        estado={{ decision: "EDITADA", texto: VALORACION.observacion }}
        alCambiar={vi.fn()}
      />,
    )

    expect(screen.getByLabelText(/texto editado de d05/i)).toHaveValue(VALORACION.observacion)
  })

  it("escribir en el área de edición avisa con el texto nuevo", () => {
    const alCambiar = vi.fn()
    render(
      <Observacion
        valoracion={VALORACION}
        estado={{ decision: "EDITADA", texto: VALORACION.observacion }}
        alCambiar={alCambiar}
      />,
    )

    fireEvent.change(screen.getByLabelText(/texto editado de d05/i), {
      target: { value: "Falta justificar el presupuesto con al menos dos fuentes." },
    })

    expect(alCambiar).toHaveBeenCalledWith({
      decision: "EDITADA",
      texto: "Falta justificar el presupuesto con al menos dos fuentes.",
    })
  })

  it("hay forma de descartar la edición y volver a aceptada", () => {
    const alCambiar = vi.fn()
    render(
      <Observacion
        valoracion={VALORACION}
        estado={{ decision: "EDITADA", texto: "Un texto a medio escribir" }}
        alCambiar={alCambiar}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: /descartar la edición/i }))

    expect(alCambiar).toHaveBeenCalledWith({
      decision: "ACEPTADA", texto: VALORACION.observacion,
    })
  })

  it("una cita no localizada se marca y avisa de que no llegará al alumno", () => {
    const { container } = render(
      <Observacion
        valoracion={{ ...VALORACION, evidencia_localizada: false }}
        estado={ACEPTADA}
        alCambiar={vi.fn()}
      />,
    )

    expect(screen.getByText(/no llegará al alumno/i)).toBeInTheDocument()
    expect(container.querySelectorAll(".senal")).toHaveLength(1)
  })

  it("una cita localizada no lleva ningún aviso ni tinta de señal", () => {
    const { container } = render(
      <Observacion valoracion={VALORACION} estado={ACEPTADA} alCambiar={vi.fn()} />,
    )

    expect(screen.queryByText(/no llegará al alumno/i)).not.toBeInTheDocument()
    expect(container.querySelectorAll(".senal")).toHaveLength(0)
  })

  it("un nivel NO_VERIFICABLE no lleva la tinta de señal", () => {
    // La escala del §8.1 incluye NO_VERIFICABLE como un nivel más, no como
    // una alarma: solo la cita no localizada justifica la tinta de señal.
    const { container } = render(
      <Observacion
        valoracion={{ ...VALORACION, nivel: "NO_VERIFICABLE" }}
        estado={ACEPTADA}
        alCambiar={vi.fn()}
      />,
    )

    expect(container.querySelectorAll(".senal")).toHaveLength(0)
  })
})
