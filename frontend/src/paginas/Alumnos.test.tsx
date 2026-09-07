import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { api } from "../lib/api"
import { Alumnos } from "./Alumnos"

vi.mock("../lib/api")

const LISTADOS = [
  { nombre: "andalucia.xlsx", tamano_kb: 42 },
  { nombre: "madrid.xlsx", tamano_kb: 51 },
]

describe("Alumnos", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listados).mockResolvedValue(LISTADOS)
  })

  it("enseña los Excel que esperan en la carpeta", async () => {
    render(<Alumnos />)

    expect(await screen.findByText(/andalucia.xlsx/)).toBeInTheDocument()
    expect(screen.getByText(/madrid.xlsx/)).toBeInTheDocument()
  })

  it("sin ningún Excel dice qué hacer, no solo que no hay", async () => {
    vi.mocked(api.listados).mockResolvedValue([])

    render(<Alumnos />)

    expect(
      await screen.findByText(/Deja ahí los listados de matrícula/)
    ).toBeInTheDocument()
  })

  it("importa el listado elegido y resume lo que ha pasado", async () => {
    vi.mocked(api.importarListado).mockResolvedValue({
      nuevas: 24, actualizadas: 3, pendientes: [],
    })

    render(<Alumnos />)
    await userEvent.click(await screen.findByRole("button", { name: "Importar" }))

    expect(api.importarListado).toHaveBeenCalledWith({
      nombre_archivo: "andalucia.xlsx", ccaa_code: "AND", curso: "2026-2027",
    })
    expect(await screen.findByText(/24 altas · 3 actualizadas/)).toBeInTheDocument()
  })

  it("las filas sin registrar se identifican por su número de fila", async () => {
    vi.mocked(api.importarListado).mockResolvedValue({
      nuevas: 1, actualizadas: 0,
      pendientes: [{
        fila: 7, motivo: "CENTRO_DESCONOCIDO",
        detalle: "Fila 7: el centro «AND-XXX-99» no está en el catálogo.",
      }],
    })

    render(<Alumnos />)
    await userEvent.click(await screen.findByRole("button", { name: "Importar" }))

    // Dos veces a propósito: el encabezado de la fila y el detalle que
    // explica por qué. Se comprueban los dos.
    expect(await screen.findAllByText(/Fila 7/)).toHaveLength(2)
    expect(screen.getByText(/centro desconocido/)).toBeInTheDocument()
  })

  it("dice que ninguna fila dudosa se ha asignado a nadie", async () => {
    // El docente tiene que poder distinguir «no se ha registrado» de «se ha
    // registrado mal». Es la diferencia entre revisar siete filas y revisar
    // el listado entero.
    vi.mocked(api.importarListado).mockResolvedValue({
      nuevas: 0, actualizadas: 0,
      pendientes: [{ fila: 2, motivo: "SIN_CENTRO", detalle: "Fila 2: sin centro." }],
    })

    render(<Alumnos />)
    await userEvent.click(await screen.findByRole("button", { name: "Importar" }))

    expect(
      await screen.findByText(/se detiene antes que dar de alta a la persona equivocada/)
    ).toBeInTheDocument()
  })

  it("un fallo se enseña con su mensaje", async () => {
    vi.mocked(api.importarListado).mockRejectedValue(
      new Error("El Excel «and.xlsx» no tiene filas de datos.")
    )

    render(<Alumnos />)
    await userEvent.click(await screen.findByRole("button", { name: "Importar" }))

    expect(await screen.findByText(/no tiene filas de datos/)).toBeInTheDocument()
  })
})
