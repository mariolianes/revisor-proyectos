import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { Ficha } from "./Ficha"
import { api } from "../lib/api"
import type { FichaDeLectura } from "../lib/tipos"

vi.mock("../lib/api")

// Las formas siguen a `frontend/src/lib/tipos.ts` (que a su vez sigue al
// backend), no al brief de la Task 14: `Evolucion` no tiene
// `parrafos_eliminados` ni `parrafos_nuevos` -eso llevaba a inventar un
// dato que el sistema no mide-, sino `parrafos_antes` y `parrafos_despues`
// (el tamaño de cada lado). `MedidasDeEntrega` tampoco deja ningún campo
// opcional: hay que rellenarlos todos para que el fixture sea del tipo que
// dice ser.
const COMPLETA: FichaDeLectura = {
  entrega: {
    id: "id-1", codigo_alumno: "AF023", ciclo: "DAM", fase: "E2", version: 1,
    nombre_archivo: "AF023_DAM_E2_20260115_v1.pdf", huella: "a".repeat(64),
    recibida_en: "2026-08-27T10:00:00", estado: "RECIBIDO",
    motivo_bloqueo: null, version_criterios: "v2026-2027",
  },
  medidas: {
    nombre_archivo: "AF023_DAM_E2_20260115_v1.pdf",
    huella: "a".repeat(64),
    paginas: [],
    total_paginas: 24, paginas_en_blanco: [7], escaneado: false,
    texto: {
      familia_dominante: "Arial", cuerpo_dominante: 11,
      proporcion_cuerpo_dominante: 0.92,
      ratio_interlineado: 1.73,
      margen_izquierdo_cm: 2.5, margen_derecho_cm: 2.5,
      margen_superior_cm: 2.5, margen_inferior_cm: 2.5,
      proporcion_lineas_al_margen_derecho: 0.81,
    },
    estructura: {
      pagina_del_indice: 2, primera_pagina_de_contenido: 3,
      primera_pagina_de_anexos: null, paginas_de_contenido: 20,
      entradas_de_indice: [], titulos_no_encontrados: [],
      paginas_declaradas_incorrectas: [],
    },
    imagenes: [
      { pagina: 9, ancho_px: 900, alto_px: 600, dpi_efectivo: 42.1, proporcion_de_pagina: 0.22 },
    ],
  },
  comprobaciones: [{
    criterio: "extension", veredicto: "CUMPLE",
    esperado: "20 páginas", medido: "20 páginas",
    fuente: "maestro#6-estandar-academico", nota: "",
  }],
  evolucion: {
    proporcion_conservada: 0.9, proporcion_nueva: 0.3,
    parrafos_antes: 18, parrafos_despues: 30,
    avisos: ["Han desaparecido 2 párrafos."],
  },
  comparada_con: "AF023_DAM_E1_20251201_v1.pdf",
  aviso: "",
}

// El mismo aviso que compone `AVISO_PROTECCION_DATOS` en
// `backend/api/analisis.py`, y el mismo error que produce `pedir()`
// (`frontend/src/lib/api.ts`) para una respuesta 428: un `Error` con
// `estado` puesto, no solo un mensaje.
const AVISO_PROTECCION_DATOS =
  "Analizar esta entrega envía el texto íntegro del documento a un " +
  "proveedor de análisis externo. Las condiciones de protección de datos " +
  "para tratar documentos reales de alumnos con esa herramienta todavía " +
  "no están cerradas."

function errorConEstado(mensaje: string, estado: number): Error {
  const error = new Error(mensaje) as Error & { estado: number }
  error.estado = estado
  return error
}

describe("Ficha", () => {
  beforeEach(() => {
    // Sin esto, `mock.calls` se acumula de un test al siguiente y
    // `expect(api.analizar).not.toHaveBeenCalled()` (más abajo) podría
    // fallar por una llamada de OTRO test, no por esta pantalla.
    vi.clearAllMocks()
    vi.mocked(api.ficha).mockResolvedValue(COMPLETA)
  })

  it("enseña de quién es la entrega", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)

    expect(await screen.findByText(/AF023 · DAM · E2/)).toBeInTheDocument()
  })

  it("enseña lo medido", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)

    expect(await screen.findByText("24")).toBeInTheDocument()
    expect(screen.getByText(/Arial/)).toBeInTheDocument()
  })

  it("enseña las comprobaciones", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)

    expect(await screen.findByText(/maestro#6-estandar-academico/)).toBeInTheDocument()
  })

  it("enseña con qué entrega se ha comparado", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)

    expect(await screen.findByText(/AF023_DAM_E1_20251201_v1.pdf/)).toBeInTheDocument()
    expect(screen.getByText(/Han desaparecido 2 párrafos/)).toBeInTheDocument()
  })

  it("no ofrece nota ni aprobar", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
    await screen.findByText(/AF023 · DAM · E2/)

    expect(screen.queryByRole("button", { name: /nota/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /aprobar/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /calificar/i })).not.toBeInTheDocument()
  })

  it("dice por qué no hay nota, para que no parezca un olvido", async () => {
    render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)

    expect(await screen.findByText(/ponderaciones/i)).toBeInTheDocument()
  })

  it("una entrega bloqueada enseña el motivo y nada más", async () => {
    vi.mocked(api.ficha).mockResolvedValue({
      ...COMPLETA,
      entrega: {
        ...COMPLETA.entrega, estado: "BLOQUEADO",
        motivo_bloqueo: "El archivo está protegido con contraseña.",
      },
      medidas: null, comprobaciones: [], evolucion: null, comparada_con: null,
    })

    render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)

    expect(await screen.findByText(/protegido con contraseña/)).toBeInTheDocument()
  })

  it("distingue un fallo técnico de una entrega bloqueada: solo el bloqueo lleva la tinta de señal", async () => {
    // Que el servidor esté apagado no es culpa del alumno ni dice nada de
    // su trabajo: pintarlo igual que un incumplimiento le daría un peso
    // que no tiene, y diluiría el significado de la única tinta que hay.
    // Las dos ramas van en el mismo test porque lo que se protege es la
    // distinción, no cada rama por separado.
    vi.mocked(api.ficha).mockRejectedValueOnce(
      new Error("No se ha podido contactar con el servidor."),
    )
    const fallo = render(<Ficha id="id-error" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
    await screen.findByText(/No se ha podido contactar con el servidor/)
    expect(fallo.container.querySelectorAll(".senal")).toHaveLength(0)
    fallo.unmount()

    vi.mocked(api.ficha).mockResolvedValueOnce({
      ...COMPLETA,
      entrega: {
        ...COMPLETA.entrega, estado: "BLOQUEADO",
        motivo_bloqueo: "El archivo está protegido con contraseña.",
      },
      medidas: null, comprobaciones: [], evolucion: null, comparada_con: null,
    })
    const bloqueada = render(<Ficha id="id-bloqueada" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
    await screen.findByText(/protegido con contraseña/)
    expect(bloqueada.container.querySelectorAll(".senal").length).toBeGreaterThan(0)
  })

  it("un documento sin texto no publica un cuerpo de 0 puntos", async () => {
    // `cuerpo_dominante` es nulo cuando no hay texto del que sacarlo. Un
    // 0 pintado ahí sería un dato inventado con aspecto de medida.
    vi.mocked(api.ficha).mockResolvedValue({
      ...COMPLETA,
      medidas: {
        ...COMPLETA.medidas!,
        escaneado: true,
        texto: {
          ...COMPLETA.medidas!.texto,
          familia_dominante: "", cuerpo_dominante: null,
          proporcion_cuerpo_dominante: 0,
        },
      },
    })

    render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)

    expect(await screen.findByText("sin texto extraíble")).toBeInTheDocument()
    expect(screen.queryByText(/ 0$/)).not.toBeInTheDocument()
  })

  it("enseña el aviso cuando no se ha podido comparar", async () => {
    vi.mocked(api.ficha).mockResolvedValue({
      ...COMPLETA, evolucion: null, comparada_con: null,
      aviso: "El archivo anterior ya no está en la carpeta.",
    })

    render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)

    expect(await screen.findByText(/ya no está en la carpeta/)).toBeInTheDocument()
  })

  it("vuelve a la bandeja", async () => {
    const alVolver = vi.fn()
    const usuario = (await import("@testing-library/user-event")).default
    render(<Ficha id="id-1" alVolver={alVolver} alAbrirRevision={vi.fn()} />)

    await usuario.click(await screen.findByRole("button", { name: /volver/i }))

    expect(alVolver).toHaveBeenCalled()
  })

  describe("el botón de analizar", () => {
    it("aparece cuando la entrega está en RECIBIDO", async () => {
      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)

      expect(await screen.findByRole("button", { name: /^analizar$/i })).toBeInTheDocument()
    })

    it("no aparece con una entrega bloqueada", async () => {
      vi.mocked(api.ficha).mockResolvedValue({
        ...COMPLETA,
        entrega: {
          ...COMPLETA.entrega, estado: "BLOQUEADO",
          motivo_bloqueo: "El archivo está protegido con contraseña.",
        },
        medidas: null, comprobaciones: [], evolucion: null, comparada_con: null,
      })

      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
      await screen.findByText(/protegido con contraseña/)

      expect(screen.queryByRole("button", { name: /^analizar$/i })).not.toBeInTheDocument()
    })

    it("no aparece con una entrega ya analizada", async () => {
      vi.mocked(api.ficha).mockResolvedValue({
        ...COMPLETA,
        entrega: { ...COMPLETA.entrega, estado: "ANALIZADO" },
      })

      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
      await screen.findByText(/AF023 · DAM · E2/)

      expect(screen.queryByRole("button", { name: /^analizar$/i })).not.toBeInTheDocument()
    })

    it("al analizar, abre la revisión con el resultado del análisis", async () => {
      const usuario = (await import("@testing-library/user-event")).default
      const alAnalizar = vi.fn()
      const RESULTADO = {
        entrega: COMPLETA.entrega,
        informe: {
          identificacion: {}, control_administrativo: [], resumen: "",
          valoraciones: [], fortalezas: [], prioridades: [],
          prioridades_descartadas: [], dudas: [], indicios: [], reparos: [],
          dimensiones_ausentes: [], semaforo: "GRIS", recomendacion: null,
          motor: "simulado",
        },
        devolucion: null, motor: "simulado", aviso: null,
      }
      vi.mocked(api.analizar).mockResolvedValue(RESULTADO)

      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={alAnalizar} />)
      await usuario.click(await screen.findByRole("button", { name: /^analizar$/i }))

      await waitFor(() => expect(alAnalizar).toHaveBeenCalledWith("id-1", RESULTADO))
    })

    it("un fallo al analizar se enseña con su mensaje, sin la tinta de señal", async () => {
      const usuario = (await import("@testing-library/user-event")).default
      vi.mocked(api.analizar).mockRejectedValue(
        new Error("El motor no ha podido completar el análisis: sin cuota disponible."),
      )

      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
      await usuario.click(await screen.findByRole("button", { name: /^analizar$/i }))

      const mensaje = await screen.findByText(/sin cuota disponible/i)
      expect(mensaje).toBeInTheDocument()
      expect(mensaje).not.toHaveClass("senal")
    })
  })

  describe("la confirmación de protección de datos (428)", () => {
    // El backend responde 428 -no un error cualquiera- cuando
    // `proteccion_datos` sigue pendiente y todavía no se ha confirmado
    // nada (ver `backend/api/analisis.py`). El primer intento de analizar
    // no puede quedarse en el mismo cajón que un fallo técnico: tiene que
    // enseñar la pregunta entera, con sus propios gestos.
    const RESULTADO = {
      entrega: COMPLETA.entrega,
      informe: {
        identificacion: {}, control_administrativo: [], resumen: "",
        valoraciones: [], fortalezas: [], prioridades: [],
        prioridades_descartadas: [], dudas: [], indicios: [], reparos: [],
        dimensiones_ausentes: [], semaforo: "GRIS", recomendacion: null,
        motor: "simulado",
      },
      devolucion: null, motor: "simulado", aviso: null,
    }

    it("al recibir un 428, enseña la pregunta completa en vez de un error genérico", async () => {
      const usuario = (await import("@testing-library/user-event")).default
      vi.mocked(api.analizar).mockRejectedValue(
        errorConEstado(AVISO_PROTECCION_DATOS, 428),
      )

      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
      await usuario.click(await screen.findByRole("button", { name: /^analizar$/i }))

      expect(
        await screen.findByText(/texto íntegro del documento/i),
      ).toBeInTheDocument()
      expect(
        await screen.findByText(/proveedor de análisis externo/i),
      ).toBeInTheDocument()
      // No es el cajón de los errores técnicos: no lleva la clase que ese
      // cajón usa para separarlos (ver el fallo de motor de arriba, que sí
      // se pinta sin `senal`; aquí se comprueba lo contrario de la
      // ausencia del botón «Analizar» plano, no de la tinta).
      expect(
        screen.queryByRole("button", { name: /^analizar$/i }),
      ).not.toBeInTheDocument()
      expect(
        await screen.findByRole("button", { name: /sí, enviarlo al proveedor/i }),
      ).toBeInTheDocument()
      expect(
        await screen.findByRole("button", { name: /cancelar/i }),
      ).toBeInTheDocument()
    })

    it("al confirmar, reintenta con la confirmación y abre la revisión con el resultado", async () => {
      const usuario = (await import("@testing-library/user-event")).default
      const alAbrirRevision = vi.fn()
      vi.mocked(api.analizar).mockRejectedValueOnce(
        errorConEstado(AVISO_PROTECCION_DATOS, 428),
      )
      vi.mocked(api.analizar).mockResolvedValueOnce(RESULTADO)

      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={alAbrirRevision} />)
      await usuario.click(await screen.findByRole("button", { name: /^analizar$/i }))
      await screen.findByText(/texto íntegro del documento/i)

      await usuario.click(
        await screen.findByRole("button", { name: /sí, enviarlo al proveedor/i }),
      )

      await waitFor(() =>
        expect(alAbrirRevision).toHaveBeenCalledWith("id-1", RESULTADO),
      )
      // La primera llamada no confirma nada; la segunda -la que sigue a
      // pulsar el botón de la pregunta- sí. Si `analizar()` no propagara
      // el `true` hasta `api.analizar`, esta llamada quedaría idéntica a
      // la primera y el backend volvería a responder 428 en producción,
      // aunque este test no lo vería -el mock resuelve pase lo que pase-.
      expect(api.analizar).toHaveBeenNthCalledWith(1, "id-1", false)
      expect(api.analizar).toHaveBeenNthCalledWith(2, "id-1", true)
    })

    it("al cancelar, no reintenta y vuelve a ofrecer el botón analizar", async () => {
      const usuario = (await import("@testing-library/user-event")).default
      vi.mocked(api.analizar).mockRejectedValue(
        errorConEstado(AVISO_PROTECCION_DATOS, 428),
      )

      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
      await usuario.click(await screen.findByRole("button", { name: /^analizar$/i }))
      await screen.findByText(/texto íntegro del documento/i)

      await usuario.click(await screen.findByRole("button", { name: /cancelar/i }))

      expect(
        await screen.findByRole("button", { name: /^analizar$/i }),
      ).toBeInTheDocument()
      expect(screen.queryByText(/texto íntegro del documento/i)).not.toBeInTheDocument()
      expect(api.analizar).toHaveBeenCalledTimes(1)
    })
  })

  describe("el botón de ver revisión", () => {
    // Una entrega interrumpida a media revisión -el timbre, una clase, el
    // portátil cerrado- vuelve a ANALIZADO, no a RECIBIDO. Sin este botón
    // no había ningún camino de vuelta salvo analizar otra vez: pagar de
    // nuevo y volver a mandar el trabajo del alumno al proveedor por algo
    // que ya estaba guardado.
    const RESULTADO_GUARDADO = {
      entrega: { ...COMPLETA.entrega, estado: "ANALIZADO" },
      informe: {
        identificacion: {
          alumno: "AF023", ciclo: "DAM", fase: "E2", version: "1",
          archivo: COMPLETA.entrega.nombre_archivo, criterios: "v2026-2027",
        },
        control_administrativo: [], resumen: "Un resumen que solo existe en la revisión guardada.",
        valoraciones: [], fortalezas: [], prioridades: [],
        prioridades_descartadas: [], dudas: [], indicios: [], reparos: [],
        dimensiones_ausentes: [], semaforo: "GRIS", recomendacion: null,
        motor: "simulado",
      },
      devolucion: null, motor: "simulado", aviso: null,
    }

    it("aparece con una entrega ya analizada", async () => {
      vi.mocked(api.ficha).mockResolvedValue({
        ...COMPLETA,
        entrega: { ...COMPLETA.entrega, estado: "ANALIZADO" },
      })

      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)

      expect(await screen.findByRole("button", { name: /ver revisión/i })).toBeInTheDocument()
    })

    it("no aparece con una entrega RECIBIDO ni con una bloqueada", async () => {
      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
      await screen.findByText(/AF023 · DAM · E2/)
      expect(screen.queryByRole("button", { name: /ver revisión/i })).not.toBeInTheDocument()

      vi.mocked(api.ficha).mockResolvedValue({
        ...COMPLETA,
        entrega: {
          ...COMPLETA.entrega, estado: "BLOQUEADO",
          motivo_bloqueo: "El archivo está protegido con contraseña.",
        },
        medidas: null, comprobaciones: [], evolucion: null, comparada_con: null,
      })
      const bloqueada = render(<Ficha id="id-2" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
      await screen.findByText(/protegido con contraseña/)
      expect(
        bloqueada.queryByRole("button", { name: /ver revisión/i }),
      ).not.toBeInTheDocument()
    })

    it("al pulsarlo, pide lo ya guardado -no vuelve a analizar- y abre la revisión con esos datos", async () => {
      const usuario = (await import("@testing-library/user-event")).default
      const alAbrirRevision = vi.fn()
      vi.mocked(api.ficha).mockResolvedValue({
        ...COMPLETA,
        entrega: { ...COMPLETA.entrega, estado: "ANALIZADO" },
      })
      vi.mocked(api.analisis).mockResolvedValue(RESULTADO_GUARDADO)

      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={alAbrirRevision} />)
      await usuario.click(await screen.findByRole("button", { name: /ver revisión/i }))

      // No es solo que aparezca un botón: se comprueba que de verdad se
      // pidió lo guardado (GET) y que la revisión se abre con ese
      // resultado -y no que se disparó, sin más, algún análisis nuevo.
      await waitFor(() => expect(api.analisis).toHaveBeenCalledWith("id-1"))
      expect(api.analizar).not.toHaveBeenCalled()
      expect(alAbrirRevision).toHaveBeenCalledWith("id-1", RESULTADO_GUARDADO)
    })

    it("un fallo al pedir la revisión guardada se enseña con su mensaje, sin la tinta de señal", async () => {
      const usuario = (await import("@testing-library/user-event")).default
      vi.mocked(api.ficha).mockResolvedValue({
        ...COMPLETA,
        entrega: { ...COMPLETA.entrega, estado: "ANALIZADO" },
      })
      vi.mocked(api.analisis).mockRejectedValue(
        new Error("No se ha podido contactar con el servidor."),
      )

      render(<Ficha id="id-1" alVolver={vi.fn()} alAbrirRevision={vi.fn()} />)
      await usuario.click(await screen.findByRole("button", { name: /ver revisión/i }))

      const mensaje = await screen.findByText(/no se ha podido contactar con el servidor/i)
      expect(mensaje).toBeInTheDocument()
      expect(mensaje).not.toHaveClass("senal")
    })
  })
})
