import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { Entregas } from "./Entregas"
import { api } from "../lib/api"

vi.mock("../lib/api", () => ({
  api: {
    entorno: vi.fn(),
    archivosPendientes: vi.fn(),
    entregas: vi.fn(),
    confirmar: vi.fn(),
  },
}))

const PENDIENTE = {
  nombre: "AF023_DAM_E2_20260115_v1.pdf",
  ruta: "/entregas/AF023_DAM_E2_20260115_v1.pdf",
  modificado_en: "2026-08-27T10:00:00",
  propuesta: {
    codigo_alumno: "AF023", ciclo: "DAM", fase: "E2",
    fecha: "2026-01-15", version: 1, motivo: "", completa: true,
  },
  problema: "",
}

const REGISTRADA = {
  id: "id-1", codigo_alumno: "AF023", ciclo: "DAM", fase: "E1", version: 1,
  nombre_archivo: "AF023_DAM_E1_20251201_v1.pdf", huella: "a".repeat(64),
  recibida_en: "2026-08-20T09:00:00", estado: "RECIBIDO",
  motivo_bloqueo: null, version_criterios: "v2026-2027",
}

const ENTORNO = {
  hay_carpeta: true, carpeta: "C:/01_ALUMNOS", persistencia_duradera: true,
  version_criterios: "v2026-2027", avisos: [],
}

describe("Entregas", () => {
  beforeEach(() => {
    vi.mocked(api.entorno).mockResolvedValue(ENTORNO)
    vi.mocked(api.archivosPendientes).mockResolvedValue([PENDIENTE])
    vi.mocked(api.entregas).mockResolvedValue([REGISTRADA])
  })

  it("enseña los archivos pendientes de confirmar", async () => {
    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText("AF023_DAM_E2_20260115_v1.pdf")).toBeInTheDocument()
  })

  it("enseña las entregas ya registradas", async () => {
    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText(/AF023_DAM_E1_20251201_v1.pdf/)).toBeInTheDocument()
  })

  it("avisa cuando no hay carpeta configurada", async () => {
    vi.mocked(api.entorno).mockResolvedValue({
      ...ENTORNO, hay_carpeta: false, carpeta: null,
      avisos: ["No hay carpeta de entregas configurada."],
    })
    vi.mocked(api.archivosPendientes).mockResolvedValue([])

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText(/No hay carpeta de entregas/)).toBeInTheDocument()
  })

  it("avisa cuando lo registrado no se va a guardar", async () => {
    vi.mocked(api.entorno).mockResolvedValue({
      ...ENTORNO, persistencia_duradera: false,
      avisos: ["Lo que registres se pierde al cerrarlo."],
    })

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText(/se pierde al cerrarlo/)).toBeInTheDocument()
  })

  it("al confirmar abre la ficha de la entrega", async () => {
    const alAbrirFicha = vi.fn()
    vi.mocked(api.confirmar).mockResolvedValue({
      entrega: { ...REGISTRADA, id: "id-nueva" },
      medidas: null, comprobaciones: [], evolucion: null,
      comparada_con: null, aviso: "",
    })
    render(<Entregas alAbrirFicha={alAbrirFicha} />)

    await userEvent.click(await screen.findByRole("button", { name: /confirmar/i }))

    await waitFor(() => expect(alAbrirFicha).toHaveBeenCalledWith("id-nueva"))
  })

  it("enseña el error del servidor sin romperse", async () => {
    vi.mocked(api.archivosPendientes).mockRejectedValue(new Error("Servidor apagado."))

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText(/Servidor apagado/)).toBeInTheDocument()
  })

  it("dice claramente cuando no hay nada pendiente", async () => {
    vi.mocked(api.archivosPendientes).mockResolvedValue([])

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText(/nada nuevo/i)).toBeInTheDocument()
  })
})
