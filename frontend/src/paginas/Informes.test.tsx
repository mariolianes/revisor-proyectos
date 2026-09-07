import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { api } from "../lib/api"
import type { InformeCentro } from "../lib/tipos"
import { Informes } from "./Informes"

vi.mock("../lib/api")

const INFORME: InformeCentro = {
  filtro: { ccaa: "AND", centro: null, ciclo: null, curso: "2026-2027", fase: null },
  cobertura: {
    matriculados: 42,
    bajas_o_traslados: 2,
    por_fase: [
      { fase: "E2", entregados: 30, sin_entregar: 12,
        sin_entregar_codigos: ["ALU-260007", "ALU-260011"] },
    ],
    aviso_grupo_pequeno: null,
  },
  proceso: { por_estado: { RECIBIDO: 5, ANALIZADO: 25, BLOQUEADO: 0 } },
  semaforos: {
    propuestos: { VERDE: 4, AMBAR: 18, ROJO: 3, GRIS: 0 },
    confirmados_por_docente: { VERDE: 1, AMBAR: 2, ROJO: 0, GRIS: 0 },
    pendientes_de_confirmar: 22,
  },
  coste: {
    modelos: { "openai:gpt-5.6-luna": 25 },
    tokens_entrada: 361_000, tokens_salida: 254_000,
    tokens_entrada_cacheados: 0,
    coste_total_usd: 0.3778,
    coste_medio_analisis_principal_usd: 0.0151,
    coste_medio_verificacion_usd: null,
    coste_medio_reanalisis_usd: null,
    promedio_por_fase_usd: { E2: 0.0151 },
    proyeccion_mensual_usd: 1.2, proyeccion_anual_usd: 14.4,
    ejecuciones_sin_coste_calculable: 0,
    periodo_observado_dias: 9, notas: [],
  },
}

describe("Informes", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.informeDeCentro).mockResolvedValue(INFORME)
  })

  it("pide el informe con los filtros que se hayan puesto", async () => {
    render(<Informes />)
    await userEvent.click(screen.getByRole("button", { name: "Ver informe" }))

    expect(api.informeDeCentro).toHaveBeenCalledWith({
      ccaa: "", centro: "", ciclo: "", fase: "", curso: "2026-2027",
    })
  })

  it("enseña la cobertura y quién no ha entregado", async () => {
    render(<Informes />)
    await userEvent.click(screen.getByRole("button", { name: "Ver informe" }))

    expect(await screen.findByText(/42 matriculados/)).toBeInTheDocument()
    expect(screen.getByText(/12 sin entregar/)).toBeInTheDocument()
    expect(screen.getByText(/ALU-260007/)).toBeInTheDocument()
  })

  it("con un grupo pequeño enseña el aviso y ningún identificador", async () => {
    // La lista de códigos permite deducir de quién se habla a cualquiera que
    // reciba el informe; un recuento suelto, no. Ver D-032.
    vi.mocked(api.informeDeCentro).mockResolvedValue({
      ...INFORME,
      cobertura: {
        ...INFORME.cobertura,
        matriculados: 3,
        aviso_grupo_pequeno: "Grupo pequeño: no se enumera quién no ha entregado.",
        por_fase: [{ fase: "E2", entregados: 1, sin_entregar: 2,
                     sin_entregar_codigos: null }],
      },
    })

    render(<Informes />)
    await userEvent.click(screen.getByRole("button", { name: "Ver informe" }))

    expect(await screen.findByText(/Grupo pequeño/)).toBeInTheDocument()
    expect(screen.queryByText(/ALU-/)).not.toBeInTheDocument()
  })

  it("separa lo que propuso el sistema de lo que confirmó el docente", async () => {
    // Es la distinción del §16: la propuesta del sistema no es una decisión.
    render(<Informes />)
    await userEvent.click(screen.getByRole("button", { name: "Ver informe" }))

    expect(await screen.findByText(/Propuestos por el sistema/)).toBeInTheDocument()
    expect(screen.getByText(/Confirmados por ti/)).toBeInTheDocument()
    expect(screen.getByText(/22 esperan que confirmes/)).toBeInTheDocument()
  })

  it("enseña el coste con el detalle que pidió el docente", async () => {
    render(<Informes />)
    await userEvent.click(screen.getByRole("button", { name: "Ver informe" }))

    expect(await screen.findByText("Por análisis principal")).toBeInTheDocument()
    expect(screen.getByText("Proyección anual")).toBeInTheDocument()
    expect(screen.getByText(/openai:gpt-5.6-luna/)).toBeInTheDocument()
  })

  it("dice cuántos análisis no tienen coste calculable, sin inventarlo", async () => {
    vi.mocked(api.informeDeCentro).mockResolvedValue({
      ...INFORME,
      coste: { ...INFORME.coste, ejecuciones_sin_coste_calculable: 4 },
    })

    render(<Informes />)
    await userEvent.click(screen.getByRole("button", { name: "Ver informe" }))

    expect(
      await screen.findByText(/El sistema no inventa un precio/)
    ).toBeInTheDocument()
  })

  it("un fallo se enseña con su mensaje", async () => {
    vi.mocked(api.informeDeCentro).mockRejectedValue(
      new Error("«ZZZ» no es una comunidad autónoma reconocida.")
    )

    render(<Informes />)
    await userEvent.click(screen.getByRole("button", { name: "Ver informe" }))

    expect(await screen.findByText(/no es una comunidad/)).toBeInTheDocument()
  })
})
