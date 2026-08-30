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
  modalidad: "PROFESIONAL",
}

const CITA_1 = "El presupuesto inicial asciende a 4.500 euros"
const CITA_2 = "La arquitectura se apoya en tres capas"
const CITA_3 = "El plan de pruebas cubre los casos principales"
// Distinta de la descripción a propósito: descripción y cita coincidiendo
// palabra por palabra habría hecho que `getByText` encontrara el mismo
// texto en dos nodos del DOM (el `<li>` y el `<span>` de la cita) y
// reventara con «se ha encontrado más de un elemento», que es justo lo
// que no puede pasar en la vida real -la cita es un fragmento literal del
// trabajo, la descripción es la lectura del motor sobre ese fragmento-.
const CITA_INDICIO =
  "adopta un enfoque de arquitectura hexagonal desacoplada mediante inversión de dependencias"

/** Cuatro dimensiones: dos prioridades, una fuera del límite, una sin prioridad. */
const RESULTADO: ResultadoAnalisis = {
  entrega: ENTREGA,
  informe: {
    identificacion: {
      alumno: "AF023", ciclo: "DAM", modalidad: "PROFESIONAL", fase: "E2",
      version: "1", archivo: ENTREGA.nombre_archivo, criterios: "v2026-2027",
      fecha: "2026-08-27",
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
    indicios: [
      {
        descripcion:
          "El vocabulario técnico de este párrafo no aparece en ningún otro apartado del trabajo.",
        evidencia: { cita: CITA_INDICIO, apartado: "4. Desarrollo" },
        evidencia_localizada: true,
      },
    ],
    reparos: [
      {
        regla: "dimension_repetida",
        detalle: "La dimensión D09 venía valorada dos veces; se ha conservado la primera.",
      },
      {
        regla: "autoria_formulada_categoricamente",
        detalle:
          "Además, el indicio está redactado en términos categóricos, como un veredicto y " +
          "no como una observación.",
      },
    ],
    dimensiones_ausentes: ["D07"],
    continuidad: [
      {
        dimension: "D06", prioridad: "P2",
        observacion_anterior: "Falta justificar el presupuesto con fuentes externas.",
        estado: "PENDIENTE",
        motivo: "El fragmento que motivó esta observación sigue apareciendo "
          + "igual, literal, en la entrega nueva: no se ha tocado.",
      },
      {
        dimension: "D08", prioridad: "P1",
        observacion_anterior: "El anexo de riesgos no identifica ninguna mitigación.",
        estado: "NO_VERIFICABLE",
        motivo: "El fragmento que motivó esta observación ya no aparece "
          + "igual en la entrega nueva. Algo ha cambiado en ese punto, pero "
          + "el sistema no puede saber si el cambio corrige lo señalado, lo "
          + "corrige solo en parte, o simplemente lo desplaza sin "
          + "resolverlo: esa lectura le corresponde al docente.",
      },
    ],
    continuidad_nota: null,
    semaforo: "AMBAR",
    recomendacion: "Aplicar cambios antes de cerrar la siguiente fase",
    motor: "gpt-ejemplo",
  },
  // Dos acciones, en el mismo orden que `informe.prioridades`: así
  // `Revision` puede emparejar `devolucion.acciones[i]` con la prioridad de
  // la que salió, tal como lo arma `componer()` en
  // `backend/salidas/borrador.py`.
  devolucion: {
    apertura: "Has avanzado bien en esta fase.",
    fortalezas: ["El repositorio mantiene un histórico de commits ordenado."],
    acciones: [
      "Justifica las cifras del presupuesto con fuentes.",
      "Explica por qué se han elegido esas tres capas.",
    ],
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

  it("muestra las dudas del motor con la tinta de señal", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    const duda = screen.getByText(/anexo b es del alumno o de un tercero/i)
    expect(duda).toBeInTheDocument()
    // No es la única `.senal` de la pantalla, así que se comprueba la
    // clase del propio elemento, no un recuento global del contenedor.
    expect(duda).toHaveClass("senal")
  })

  it("muestra el indicio de autoría, con su cita, y con la tinta de señal", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    const indicio = screen.getByText(/el vocabulario técnico de este párrafo/i)
    expect(indicio).toBeInTheDocument()
    expect(indicio).toHaveClass("senal")
    expect(screen.getByText(/arquitectura hexagonal desacoplada/i)).toBeInTheDocument()
    // El aviso del §13 -que es un indicio, no un veredicto, y la decisión
    // es del docente- tiene que estar junto al indicio, no solo en algún
    // sitio de la pantalla.
    expect(screen.getByText(/no es un veredicto/i)).toBeInTheDocument()
  })

  it("muestra la cita de una fortaleza, igual que un indicio", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    // La misma descripción aparece también en el borrador de devolución
    // (`devolucion.fortalezas`), así que hace falta acotar la búsqueda a la
    // sección "Fortalezas" del informe interno.
    const seccion = screen.getByRole("heading", { name: /^fortalezas$/i }).closest("section")!
    const fortaleza = within(seccion).getByText(/histórico de commits ordenado/i)
    expect(fortaleza).toBeInTheDocument()
    expect(within(seccion).getByText("«git log»")).toBeInTheDocument()
    // Localizada: sin la tinta de señal.
    expect(fortaleza).not.toHaveClass("senal")
  })

  it("una fortaleza sin la cita localizada lleva la tinta de señal", () => {
    const SIN_LOCALIZAR = {
      descripcion: "El diseño sigue un patrón de capas bien definido.",
      evidencia: { cita: "cita que no se ha encontrado en el documento", apartado: "3" },
      evidencia_localizada: false,
    }
    render(
      <Revision
        id="id-1"
        inicial={{
          ...RESULTADO,
          informe: { ...RESULTADO.informe, fortalezas: [SIN_LOCALIZAR] },
        }}
        alVolver={vi.fn()}
      />,
    )

    const fortaleza = screen.getByText(/patrón de capas bien definido/i)
    expect(fortaleza).toHaveClass("senal")
    expect(
      screen.getByText(/la cita no se ha localizado en el documento/i),
    ).toBeInTheDocument()
  })

  it("sin indicios de autoría, no se enseña la sección entera", () => {
    render(
      <Revision
        id="id-1"
        inicial={{ ...RESULTADO, informe: { ...RESULTADO.informe, indicios: [] } }}
        alVolver={vi.fn()}
      />,
    )

    expect(
      screen.queryByRole("heading", { name: /indicios de autoría/i }),
    ).not.toBeInTheDocument()
  })

  it("muestra los reparos de verificación, con su regla y su detalle", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    expect(screen.getByText(/reparos de verificación \(2\)/i)).toBeInTheDocument()
    expect(screen.getByText("dimension_repetida")).toBeInTheDocument()
    expect(screen.getByText(/D09 venía valorada dos veces/i)).toBeInTheDocument()
    expect(screen.getByText("autoria_formulada_categoricamente")).toBeInTheDocument()
    expect(screen.getByText(/redactado en términos categóricos/i)).toBeInTheDocument()
  })

  it("sin reparos, no se enseña la sección entera", () => {
    render(
      <Revision
        id="id-1"
        inicial={{ ...RESULTADO, informe: { ...RESULTADO.informe, reparos: [] } }}
        alVolver={vi.fn()}
      />,
    )

    expect(screen.queryByText(/reparos de verificación/i)).not.toBeInTheDocument()
  })

  it("muestra las dimensiones sin valorar, con la explicación de por qué importa", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    expect(screen.getByText(/dimensiones sin valorar \(1\)/i)).toBeInTheDocument()
    expect(screen.getByText("D07")).toBeInTheDocument()
    expect(screen.getByText(/el motor no llegó a valorarlas/i)).toBeInTheDocument()
  })

  it("sin dimensiones ausentes, no se enseña la sección entera", () => {
    render(
      <Revision
        id="id-1"
        inicial={{
          ...RESULTADO,
          informe: { ...RESULTADO.informe, dimensiones_ausentes: [] },
        }}
        alVolver={vi.fn()}
      />,
    )

    expect(screen.queryByText(/dimensiones sin valorar/i)).not.toBeInTheDocument()
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

  it("el borrador avisa de que refleja el análisis original, no las decisiones tomadas", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    expect(
      screen.getByText(/no se ha vuelto a redactar con ellas/i),
    ).toBeInTheDocument()
  })

  it("sin ninguna prioridad descartada, el borrador no lleva el aviso de discrepancia", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    expect(
      screen.queryByText(/ya no correspond(e|en) a ninguna prioridad viva/i),
    ).not.toBeInTheDocument()
  })

  it("antes de guardar: al descartar una prioridad cuya acción sigue en el borrador, aparece el aviso, sin nombrar la dimensión, con la tinta de señal", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    // D02 es la segunda prioridad, con evidencia localizada: `componer()`
    // no escribe más de una acción por prioridad-con-evidencia, así que
    // descartar una de las dos deja sobrando una acción del borrador -sin
    // que esta pantalla pueda decir, con certeza, cuál de las dos es-.
    const tarjetaD02 = screen.getByText("D02").closest("li")!
    fireEvent.click(within(tarjetaD02).getByRole("button", { name: /^descartar$/i }))

    const aviso = screen.getByText(
      /el borrador incluye una acción que ya no corresponde a ninguna prioridad viva/i,
    )
    expect(aviso).toBeInTheDocument()
    expect(aviso).toHaveClass("senal")
    // No nombra D02: el emparejamiento por posición no está comprobado, y
    // el aviso no puede afirmar más de lo que sabe.
    expect(aviso.textContent).not.toMatch(/D02/)
    // El texto del borrador sigue ahí, sin tocar: el aviso no lo recorta.
    expect(
      screen.getByText(/explica por qué se han elegido esas tres capas/i),
    ).toBeInTheDocument()
  })

  it("descartar una observación que no tiene acción en el borrador no dispara el aviso", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    // D04 no es una prioridad -no tiene acción en `devolucion.acciones`-,
    // así que descartarla no puede dejar sobrando ninguna acción del
    // borrador: ya sobraban cero, y descartar D04 no cambia ese recuento.
    const tarjetaD04 = screen.getByText("D04").closest("li")!
    fireEvent.click(within(tarjetaD04).getByRole("button", { name: /^descartar$/i }))

    expect(
      screen.queryByText(/ya no correspond(e|en) a ninguna prioridad viva/i),
    ).not.toBeInTheDocument()
  })

  it("después de guardar: la revisión que vuelve del servidor ya no trae la prioridad descartada, y el aviso sigue apareciendo, con recuento y sin nombrar la dimensión", async () => {
    // Lo que de verdad devuelve `revisar()` en `backend/api/analisis.py`
    // cuando el docente descarta D02: la quita para siempre de
    // `informe.prioridades` -no la deja ahí marcada-, y no toca
    // `devolucion`, que sigue con sus dos acciones originales, palabra por
    // palabra. Es justo la situación en la que el aviso desaparecía antes
    // de este arreglo: ya no queda ninguna prioridad descartada que
    // comparar, porque la propia lista de prioridades ya viene sin ella.
    const TRAS_GUARDAR: ResultadoAnalisis = {
      ...RESULTADO,
      informe: {
        ...RESULTADO.informe,
        valoraciones: RESULTADO.informe.valoraciones.filter((v) => v.dimension !== "D02"),
        prioridades: RESULTADO.informe.prioridades.filter((v) => v.dimension !== "D02"),
      },
    }
    vi.mocked(api.revisar).mockResolvedValue(TRAS_GUARDAR)

    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    const tarjetaD02 = screen.getByText("D02").closest("li")!
    fireEvent.click(within(tarjetaD02).getByRole("button", { name: /^descartar$/i }))
    fireEvent.click(screen.getByRole("button", { name: /guardar la revisión/i }))

    await screen.findByText(/guardado/i)

    const aviso = await screen.findByText(
      /el borrador incluye una acción que ya no corresponde a ninguna prioridad viva/i,
    )
    expect(aviso).toBeInTheDocument()
    expect(aviso).toHaveClass("senal")
    expect(aviso.textContent).not.toMatch(/D02/)
    // El texto de la acción de D02 sigue en el borrador, sin regenerar.
    expect(
      screen.getByText(/explica por qué se han elegido esas tres capas/i),
    ).toBeInTheDocument()
  })

  it("al reabrir una revisión ya guardada, el aviso aparece sin que el docente toque nada", () => {
    // Una entrega en la que ya se guardó una revisión que descartó D02 en
    // el pasado: `GET /entregas/{id}/analisis` la devuelve tal cual quedó,
    // sin D02 en `informe.prioridades`, y con el mismo borrador de
    // siempre, que nunca se regenera. No hay ningún clic en este test -es
    // justo lo que pasa "al volver al día siguiente"-.
    const YA_GUARDADA: ResultadoAnalisis = {
      ...RESULTADO,
      informe: {
        ...RESULTADO.informe,
        valoraciones: RESULTADO.informe.valoraciones.filter((v) => v.dimension !== "D02"),
        prioridades: RESULTADO.informe.prioridades.filter((v) => v.dimension !== "D02"),
      },
    }

    render(<Revision id="id-1" inicial={YA_GUARDADA} alVolver={vi.fn()} />)

    const aviso = screen.getByText(
      /el borrador incluye una acción que ya no corresponde a ninguna prioridad viva/i,
    )
    expect(aviso).toBeInTheDocument()
    expect(aviso).toHaveClass("senal")
    expect(aviso.textContent).not.toMatch(/D02/)
  })

  it("la cabecera enseña ciclo, modalidad, fecha y versión de criterios", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    expect(
      screen.getByText(/DAM · PROFESIONAL · 2026-08-27 · criterios v2026-2027/),
    ).toBeInTheDocument()
  })

  it("cuando la modalidad no está registrada, la cabecera lo dice en vez de dejar un hueco", () => {
    render(
      <Revision
        id="id-1"
        inicial={{
          ...RESULTADO,
          informe: {
            ...RESULTADO.informe,
            identificacion: { ...RESULTADO.informe.identificacion, modalidad: "No registrada" },
          },
        }}
        alVolver={vi.fn()}
      />,
    )

    expect(screen.getByText(/No registrada/)).toBeInTheDocument()
  })

  it("muestra la continuidad, con lo pendiente en tinta normal y lo no verificable con la señal", () => {
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={vi.fn()} />)

    const pendiente = screen.getByText(/falta justificar el presupuesto con fuentes/i)
    expect(pendiente).toBeInTheDocument()
    expect(pendiente).not.toHaveClass("senal")
    expect(screen.getByText(/D06 · Pendiente/)).toBeInTheDocument()

    const noVerificable = screen.getByText(/el anexo de riesgos no identifica ninguna mitigación/i)
    expect(noVerificable).toBeInTheDocument()
    expect(noVerificable).toHaveClass("senal")
    expect(screen.getByText(/D08 · No verificable/)).toBeInTheDocument()
  })

  it("sin nada que clasificar, la continuidad enseña la nota en vez de una lista vacía", () => {
    render(
      <Revision
        id="id-1"
        inicial={{
          ...RESULTADO,
          informe: {
            ...RESULTADO.informe,
            continuidad: [],
            continuidad_nota:
              "Primera entrega de este alumno en esta fase: no hay antecedente con el que comparar.",
          },
        }}
        alVolver={vi.fn()}
      />,
    )

    expect(screen.getByText(/no hay antecedente con el que comparar/i)).toBeInTheDocument()
    expect(screen.queryByText(/D06/)).not.toBeInTheDocument()
  })

  it("sin continuidad y sin nota, no se enseña la sección entera", () => {
    render(
      <Revision
        id="id-1"
        inicial={{
          ...RESULTADO,
          informe: { ...RESULTADO.informe, continuidad: [], continuidad_nota: null },
        }}
        alVolver={vi.fn()}
      />,
    )

    expect(
      screen.queryByRole("heading", { name: /^continuidad$/i }),
    ).not.toBeInTheDocument()
  })

  it("vuelve con el botón de volver", () => {
    const alVolver = vi.fn()
    render(<Revision id="id-1" inicial={RESULTADO} alVolver={alVolver} />)

    fireEvent.click(screen.getByRole("button", { name: /volver/i }))

    expect(alVolver).toHaveBeenCalled()
  })
})
