import { fireEvent, render, screen, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { Revision } from "./Revision"
import { api } from "../lib/api"
import type { Decision, ResultadoAnalisis } from "../lib/tipos"

vi.mock("../lib/api")

const ENTREGA = {
  id: "id-1", codigo_alumno: "AF023", ciclo: "DAM", fase: "E2", version: 1,
  nombre_archivo: "AF023_DAM_E2_20260115_v1.pdf", huella: "a".repeat(64),
  recibida_en: "2026-08-27T10:00:00", estado: "ANALIZADO",
  motivo_bloqueo: null, version_criterios: "v2026-2027",
}

const CITA_1 = "El presupuesto inicial asciende a 4.500 euros"
const CITA_2 = "La arquitectura se apoya en tres capas"
const CITA_3 = "El plan de pruebas cubre los casos principales"

/** Cuatro dimensiones: dos prioridades, una fuera del límite, una sin prioridad. */
const RESULTADO: ResultadoAnalisis = {
  entrega: ENTREGA,
  informe: {
    identificacion: {
      alumno: "AF023", ciclo: "DAM", fase: "E2", version: "1",
      archivo: ENTREGA.nombre_archivo, criterios: "v2026-2027",
    },
    control_administrativo: [],
    resumen: "El trabajo cubre la mayoría de los apartados exigidos.",
    valoraciones: [
      {
        dimension: "D01", nivel: "INSUFICIENTE", prioridad: "P1",
        evidencia: { cita: CITA_1, apartado: "5. Viabilidad económica" },
        observacion: "Faltan fuentes que respalden las cifras del presupuesto.",
        evidencia_localizada: true,
      },
      {
        dimension: "D02", nivel: "EN_DESARROLLO", prioridad: "P2",
        evidencia: { cita: CITA_2, apartado: "3. Arquitectura" },
        observacion: "La arquitectura no justifica la elección de capas.",
        evidencia_localizada: true,
      },
      {
        dimension: "D03", nivel: "EN_DESARROLLO", prioridad: "P2",
        evidencia: { cita: CITA_3, apartado: "6. Pruebas" },
        observacion: "El plan de pruebas no cubre los casos límite.",
        evidencia_localizada: true,
      },
      {
        dimension: "D04", nivel: "SOLIDO", prioridad: null,
        evidencia: { cita: "La memoria sigue el índice normativo", apartado: "1. Introducción" },
        observacion: "La estructura documental es correcta.",
        evidencia_localizada: true,
      },
    ],
    fortalezas: [
      {
        descripcion: "El repositorio mantiene un histórico de commits ordenado.",
        evidencia: { cita: "git log", apartado: "Anexo" },
        evidencia_localizada: true,
      },
    ],
    prioridades: [
      {
        dimension: "D01", nivel: "INSUFICIENTE", prioridad: "P1",
        evidencia: { cita: CITA_1, apartado: "5. Viabilidad económica" },
        observacion: "Faltan fuentes que respalden las cifras del presupuesto.",
        evidencia_localizada: true,
      },
      {
        dimension: "D02", nivel: "EN_DESARROLLO", prioridad: "P2",
        evidencia: { cita: CITA_2, apartado: "3. Arquitectura" },
        observacion: "La arquitectura no justifica la elección de capas.",
        evidencia_localizada: true,
      },
    ],
    prioridades_descartadas: [
      {
        dimension: "D03", nivel: "EN_DESARROLLO", prioridad: "P2",
        evidencia: { cita: CITA_3, apartado: "6. Pruebas" },
        observacion: "El plan de pruebas no cubre los casos límite.",
        evidencia_localizada: true,
      },
    ],
    dudas: ["No queda claro si el anexo B es del alumno o de un tercero citado."],
    indicios: [],
    reparos: [],
    dimensiones_ausentes: [],
    semaforo: "AMBAR",
    recomendacion: "Aplicar cambios antes de cerrar la siguiente fase",
    motor: "gpt-ejemplo",
  },
  devolucion: {
    apertura: "Has avanzado bien en esta fase.",
    fortalezas: ["El repositorio mantiene un histórico de commits ordenado."],
    acciones: ["Justifica las cifras del presupuesto con fuentes."],
    cierre: "Sigue así en la próxima entrega.",
  },
  motor: "gpt-ejemplo",
  aviso: null,
}

describe("Revision", () => {
  beforeEach(() => {
    // Sin esto, `mock.calls` se acumula de un test al siguiente y
    // `mock.calls[0]` deja de ser la llamada de este test.
    vi.clearAllMocks()
    vi.mocked(api.revisar).mockResolvedValue(RESULTADO)
  })

  it("muestra las dos salidas: el informe y el borrador", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    expect(screen.getByText(/cubre la mayoría de los apartados/i)).toBeInTheDocument()
    expect(screen.getByText(/has avanzado bien en esta fase/i)).toBeInTheDocument()
  })

  it("el aviso del motor simulado se ve antes que nada", () => {
    const { container } = render(
      <Revision
        id="id-1"
        inicial={{ ...RESULTADO, motor: "simulado" }}
        alVolver={vi.fn()}
      />,
    )

    expect(screen.getByText(/motor simulado/i)).toBeInTheDocument()
    // Literalmente lo primero que se pinta: antes que el propio botón de
    // volver. `container.firstElementChild.textContent` no sirve para esto
    // -junta el texto de todo el árbol, no solo el del primer hijo-, así
    // que se compara la posición de cada nodo de primer nivel.
    const raiz = container.querySelector(".max-w-3xl")!
    const hijos = Array.from(raiz.children)
    const indiceAviso = hijos.findIndex((h) => /motor simulado/i.test(h.textContent ?? ""))
    const indiceVolver = hijos.findIndex((h) => /volver/i.test(h.textContent ?? ""))
    expect(indiceAviso).toBeGreaterThanOrEqual(0)
    expect(indiceVolver).toBeGreaterThanOrEqual(0)
    expect(indiceAviso).toBeLessThan(indiceVolver)
  })

  it("con un motor real no aparece ningún aviso de motor simulado", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    expect(screen.queryByText(/motor simulado/i)).not.toBeInTheDocument()
  })

  it("al descartar una observación desaparece de las prioridades", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    const seccionPrioridades = screen.getByRole("heading", {
      name: /prioridades para la devolución/i,
    }).closest("section")!
    expect(within(seccionPrioridades).getByText(/D01 · P1/)).toBeInTheDocument()

    // La primera tarjeta de "Observaciones" es la de D01 (la primera prioridad).
    const tarjetaD01 = screen.getByText("D01").closest("li")!
    fireEvent.click(within(tarjetaD01).getByRole("button", { name: /^descartar$/i }))

    expect(within(seccionPrioridades).queryByText(/D01 · P1/)).not.toBeInTheDocument()
    expect(within(seccionPrioridades).getByText(/D02 · P2/)).toBeInTheDocument()
    // La tarjeta sigue existiendo: descartar no es lo mismo que borrar del
    // informe, es una decisión que se puede deshacer.
    expect(screen.getByText("D01")).toBeInTheDocument()
  })

  it("al guardar se envían todas las decisiones, incluidas las no tocadas", async () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    fireEvent.click(screen.getByRole("button", { name: /guardar la revisión/i }))

    await screen.findByText(/guardado/i)

    expect(api.revisar).toHaveBeenCalledWith("id-1", {
      decisiones: [
        { dimension: "D01", decision: "ACEPTADA", texto: null },
        { dimension: "D02", decision: "ACEPTADA", texto: null },
        { dimension: "D03", decision: "ACEPTADA", texto: null },
        { dimension: "D04", decision: "ACEPTADA", texto: null },
      ] satisfies Decision[],
    })
  })

  it("envía la decisión que se ha tomado en cada observación", async () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    const tarjetaD01 = screen.getByText("D01").closest("li")!
    fireEvent.click(within(tarjetaD01).getByRole("button", { name: /^descartar$/i }))

    const tarjetaD02 = screen.getByText("D02").closest("li")!
    fireEvent.click(within(tarjetaD02).getByRole("button", { name: /^editar$/i }))
    fireEvent.change(within(tarjetaD02).getByLabelText(/texto editado de d02/i), {
      target: { value: "La arquitectura necesita justificar cada capa." },
    })

    fireEvent.click(screen.getByRole("button", { name: /guardar la revisión/i }))
    await screen.findByText(/guardado/i)

    const cuerpo = vi.mocked(api.revisar).mock.calls[0][1]
    expect(cuerpo.decisiones).toContainEqual({
      dimension: "D01", decision: "DESCARTADA", texto: null,
    })
    expect(cuerpo.decisiones).toContainEqual({
      dimension: "D02", decision: "EDITADA",
      texto: "La arquitectura necesita justificar cada capa.",
    })
  })

  it("un error del servidor al guardar se enseña con su mensaje", async () => {
    vi.mocked(api.revisar).mockRejectedValueOnce(
      new Error("No se ha podido contactar con el servidor."),
    )
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    fireEvent.click(screen.getByRole("button", { name: /guardar la revisión/i }))

    expect(
      await screen.findByText(/no se ha podido contactar con el servidor/i),
    ).toBeInTheDocument()
    expect(screen.queryByText(/^guardado\.$/i)).not.toBeInTheDocument()
  })

  it("no hay ningún control de nota, semáforo editable ni botón de aprobar", () => {
    const { container } = render(
      <Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />,
    )

    expect(screen.queryByRole("button", { name: /aprobar/i })).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/nota/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^nota$/i)).not.toBeInTheDocument()
    // El semáforo se lee, no se elige: ni un <select> ni un <input> a su
    // alrededor.
    const seccionSemaforo = screen.getByRole("heading", {
      name: /semáforo propuesto/i,
    }).closest("section")!
    expect(seccionSemaforo.querySelector("select")).toBeNull()
    expect(seccionSemaforo.querySelector("input")).toBeNull()
    expect(container.querySelector("select")).toBeNull()
  })

  it("un análisis con el informe válido y el borrador fallido no se presenta como un error", () => {
    const AVISO =
      "El análisis se ha completado: el informe es válido y ya se puede usar para decidir. " +
      "El borrador de devolución para el alumno no se ha podido generar."
    render(
      <Revision
        id="id-1"
        inicial={{ ...RESULTADO, devolucion: null, aviso: AVISO }}
        alVolver={vi.fn()}
      />,
    )

    expect(screen.getByText(AVISO, { exact: false })).toBeInTheDocument()
    // El informe se sigue pudiendo revisar entero.
    expect(screen.getByText(/cubre la mayoría de los apartados/i)).toBeInTheDocument()
    expect(screen.getByText("D01")).toBeInTheDocument()
    // Y no hay ninguna sección de borrador que enseñar (el aviso de arriba
    // sí menciona la palabra «borrador», así que se busca el titular, no
    // cualquier texto que la contenga).
    expect(
      screen.queryByRole("heading", { name: /borrador de devolución/i }),
    ).not.toBeInTheDocument()
  })

  it("vuelve con el botón de volver", () => {
    const alVolver = vi.fn()
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={alVolver} />)

    fireEvent.click(screen.getByRole("button", { name: /volver/i }))

    expect(alVolver).toHaveBeenCalled()
  })
})
