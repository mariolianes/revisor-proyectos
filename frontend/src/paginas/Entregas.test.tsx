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
 modalidad: null,
}

const ENTORNO = {
  hay_carpeta: true, carpeta: "C:/01_ALUMNOS", persistencia_duradera: true,
  version_criterios: "v2026-2027", motor: "simulado", avisos: [],
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
    const FICHA_CONFIRMADA = {
      entrega: { ...REGISTRADA, id: "id-nueva" },
      medidas: null, comprobaciones: [], evolucion: null,
      comparada_con: null,
      aviso: "Este archivo ya estaba registrado como entrega.",
    }
    vi.mocked(api.confirmar).mockResolvedValue(FICHA_CONFIRMADA)
    render(<Entregas alAbrirFicha={alAbrirFicha} />)

    await userEvent.click(await screen.findByRole("button", { name: /confirmar/i }))

    // Con la ficha entera, no solo con el identificador: es la unica que
    // trae los avisos que compone confirmar, y pedirla otra vez por su
    // identificador los borra (ver App.test.tsx).
    await waitFor(() =>
      expect(alAbrirFicha).toHaveBeenCalledWith("id-nueva", FICHA_CONFIRMADA),
    )
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

describe("la bandeja agrupada por lo que espera del docente", () => {
  function entrega(id: string, estado: string) {
    return { ...REGISTRADA, id, estado }
  }

  it("agrupa por lo que le toca a él, no por si está registrada", async () => {
    vi.mocked(api.entorno).mockResolvedValue(ENTORNO)
    vi.mocked(api.archivosPendientes).mockResolvedValue([])
    vi.mocked(api.entregas).mockResolvedValue([
      entrega("a", "RECIBIDO"),
      entrega("b", "ANALIZADO"),
      entrega("c", "APROBADO"),
    ])

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText("Listas para analizar")).toBeInTheDocument()
    expect(screen.getByText("Esperan tu revisión")).toBeInTheDocument()
    expect(screen.getByText("Cerradas")).toBeInTheDocument()
  })

  it("no pinta un grupo vacío, salvo el de cerradas", async () => {
    // Cinco encabezados con nada debajo son justo el ruido que esta
    // agrupación quiere quitar. El de cerradas se queda porque su recuento
    // a cero sí dice algo: todavía no has cerrado ninguna.
    vi.mocked(api.entorno).mockResolvedValue(ENTORNO)
    vi.mocked(api.archivosPendientes).mockResolvedValue([])
    vi.mocked(api.entregas).mockResolvedValue([entrega("a", "RECIBIDO")])

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText("Listas para analizar")).toBeInTheDocument()
    expect(screen.queryByText("Esperan tu revisión")).not.toBeInTheDocument()
    expect(screen.queryByText("Bloqueadas")).not.toBeInTheDocument()
    expect(screen.getByText("Cerradas")).toBeInTheDocument()
  })

  it("una entrega bloqueada aparece en su propio grupo", async () => {
    vi.mocked(api.entorno).mockResolvedValue(ENTORNO)
    vi.mocked(api.archivosPendientes).mockResolvedValue([])
    vi.mocked(api.entregas).mockResolvedValue([entrega("a", "BLOQUEADO")])

    render(<Entregas alAbrirFicha={vi.fn()} />)

    expect(await screen.findByText("Bloqueadas")).toBeInTheDocument()
    expect(screen.getByText("bloqueada")).toBeInTheDocument()
  })

  it("cada grupo dice cuántas hay", async () => {
    vi.mocked(api.entorno).mockResolvedValue(ENTORNO)
    vi.mocked(api.archivosPendientes).mockResolvedValue([])
    vi.mocked(api.entregas).mockResolvedValue([
      entrega("a", "ANALIZADO"),
      entrega("b", "EN_REVISION_DOCENTE"),
      entrega("c", "BORRADORES_GENERADOS"),
    ])

    render(<Entregas alAbrirFicha={vi.fn()} />)

    const titulo = await screen.findByText("Esperan tu revisión")
    expect(titulo.parentElement?.textContent).toContain("3")
  })
})
