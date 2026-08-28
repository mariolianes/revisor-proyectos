import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import App from "./App"
import { api } from "./lib/api"

vi.mock("./lib/api")

// Cabo suelto que dejó la Task 13: tras confirmar una entrega, la bandeja
// llamaba a abrir la ficha pero no recargaba su propia lista. Al enganchar
// la ficha en App.tsx con prioridad sobre la vista (Task 14), Entregas se
// desmonta mientras la ficha está abierta y se vuelve a montar al volver
// -no es el mismo nodo del árbol el que se actualiza, es un componente
// distinto en la misma posición del ternary-, así que su propio
// `useEffect` pide `archivosPendientes()`/`entregas()` frescos sin que
// nadie tenga que acordarse de recargar nada a mano.
//
// Esto se comprobó a mano montando la app entera y funcionaba, pero sin
// este test nada lo protegía: bastaba con dejar `Entregas` montada de
// fondo, o ponerle una `key` estable, para reintroducir el fallo sin que
// nadie se enterara.

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

const ENTORNO = {
  hay_carpeta: true, carpeta: "C:/01_ALUMNOS", persistencia_duradera: true,
  version_criterios: "v2026-2027", avisos: [],
}

const REGISTRADA = {
  id: "id-nueva", codigo_alumno: "AF023", ciclo: "DAM", fase: "E2", version: 1,
  nombre_archivo: "AF023_DAM_E2_20260115_v1.pdf", huella: "a".repeat(64),
  recibida_en: "2026-08-27T10:00:00", estado: "RECIBIDO",
  motivo_bloqueo: null, version_criterios: "v2026-2027",
}

describe("App", () => {
  beforeEach(() => {
    // Sin esto, los `mockResolvedValueOnce` de `archivosPendientes` se
    // acumulan de un test al siguiente: cada `beforeEach` aniade dos a una
    // cola que el test anterior no ha vaciado del todo, y el segundo test
    // empieza recibiendo la respuesta sobrante del primero.
    vi.resetAllMocks()
    vi.mocked(api.entorno).mockResolvedValue(ENTORNO)
    vi.mocked(api.entregas).mockResolvedValue([])
    vi.mocked(api.archivosPendientes)
      .mockResolvedValueOnce([PENDIENTE])
      .mockResolvedValueOnce([]) // tras confirmar, ya no está pendiente
    vi.mocked(api.confirmar).mockResolvedValue({
      entrega: REGISTRADA, medidas: null, comprobaciones: [],
      evolucion: null, comparada_con: null, aviso: "",
    })
    vi.mocked(api.ficha).mockResolvedValue({
      entrega: REGISTRADA, medidas: null, comprobaciones: [],
      evolucion: null, comparada_con: null, aviso: "",
    })
  })

  it("al volver de la ficha, la bandeja recarga y el archivo confirmado ya no aparece pendiente", async () => {
    render(<App />)

    await screen.findByText("AF023_DAM_E2_20260115_v1.pdf")
    await userEvent.click(await screen.findByRole("button", { name: /confirmar/i }))

    // Se abre la ficha con prioridad sobre la bandeja.
    await screen.findByText(/AF023 · DAM · E2/)
    expect(api.archivosPendientes).toHaveBeenCalledTimes(1)

    await userEvent.click(screen.getByRole("button", { name: /volver/i }))

    await waitFor(() => expect(api.archivosPendientes).toHaveBeenCalledTimes(2))
    expect(screen.queryByText("AF023_DAM_E2_20260115_v1.pdf")).not.toBeInTheDocument()
  })

  // El canal entre confirmar y la ficha estaba muerto, y no lo detectaba
  // nada: Entregas hacía `api.confirmar(datos)` y solo se quedaba con
  // `ficha.entrega.id`, tiraba el resto, y Ficha volvía a pedirla con
  // `GET /api/entregas/{id}`. Ese GET pasa por `leer()`, que no compone
  // ninguno de los avisos de confirmar -no puede: nadie ha declarado nada
  // al abrir una ficha-, así que llegaba con `aviso: ""`.
  //
  // Los tres tests de backend que protegían el aviso del ciclo pasaban
  // todos, y el aviso no llegaba a la pantalla. Estos dos cierran el
  // recorrido entero.
  it("el aviso que devuelve confirmar se ve en la ficha", async () => {
    const AVISO =
      "Has declarado el ciclo DAW, pero AF023 está registrado con el ciclo DAM."
    vi.mocked(api.confirmar).mockResolvedValue({
      entrega: REGISTRADA, medidas: null, comprobaciones: [],
      evolucion: null, comparada_con: null, aviso: AVISO,
    })

    render(<App />)

    await screen.findByText("AF023_DAM_E2_20260115_v1.pdf")
    await userEvent.click(await screen.findByRole("button", { name: /confirmar/i }))

    expect(await screen.findByText(AVISO)).toBeInTheDocument()
  })

  it("la ficha de confirmar no se vuelve a pedir, que la borraría", async () => {
    vi.mocked(api.confirmar).mockResolvedValue({
      entrega: REGISTRADA, medidas: null, comprobaciones: [],
      evolucion: null, comparada_con: null,
      aviso: "Este archivo ya estaba registrado como entrega.",
    })

    render(<App />)

    await screen.findByText("AF023_DAM_E2_20260115_v1.pdf")
    await userEvent.click(await screen.findByRole("button", { name: /confirmar/i }))
    await screen.findByText(/ya estaba registrado/)

    expect(api.ficha).not.toHaveBeenCalled()
  })

  it("una entrega abierta desde la lista de registradas sí se pide", async () => {
    vi.mocked(api.entregas).mockResolvedValue([REGISTRADA])

    render(<App />)

    const enLaLista = await screen.findByRole("button", {
      name: /AF023 · E2 · versión 1/,
    })
    await userEvent.click(enLaLista)

    await waitFor(() => expect(api.ficha).toHaveBeenCalledWith("id-nueva"))
  })
})
