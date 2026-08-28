import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { ArchivoPendiente } from "./ArchivoPendiente"
import type { ArchivoVisto } from "../lib/tipos"

const DEDUCIDO: ArchivoVisto = {
  nombre: "AF023_DAM_E2_20260115_v1.pdf",
  ruta: "/entregas/AF023_DAM_E2_20260115_v1.pdf",
  modificado_en: "2026-08-27T10:00:00",
  propuesta: {
    codigo_alumno: "AF023", ciclo: "DAM", fase: "E2",
    fecha: "2026-01-15", version: 1, motivo: "", completa: true,
  },
  problema: "",
}

const SIN_DEDUCIR: ArchivoVisto = {
  nombre: "trabajo de clase.pdf",
  ruta: "/entregas/trabajo de clase.pdf",
  modificado_en: "2026-08-27T10:00:00",
  propuesta: {
    codigo_alumno: null, ciclo: null, fase: null, fecha: null, version: null,
    motivo: "El nombre no sigue la convención.", completa: false,
  },
  problema: "",
}

const CON_PROBLEMA: ArchivoVisto = {
  ...DEDUCIDO,
  modificado_en: null,
  problema: "No se ha podido leer «AF023_DAM_E2_20260115_v1.pdf»: permiso denegado.",
}

describe("ArchivoPendiente", () => {
  it("enseña lo deducido cuando la propuesta está completa", () => {
    render(<ArchivoPendiente archivo={DEDUCIDO} alConfirmar={vi.fn()} />)

    expect(screen.getByText("AF023_DAM_E2_20260115_v1.pdf")).toBeInTheDocument()
    // No /AF023/ ni /E2/ sueltos: los dos aparecen también dentro del
    // nombre del archivo ("AF023_DAM_E2_..."), y una búsqueda tan amplia
    // encuentra dos coincidencias y falla por ambigua.
    expect(screen.getByText(/AF023 · DAM · E2 · versión 1/)).toBeInTheDocument()
  })

  it("confirma con lo deducido de un solo clic", async () => {
    const alConfirmar = vi.fn()
    render(<ArchivoPendiente archivo={DEDUCIDO} alConfirmar={alConfirmar} />)

    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }))

    expect(alConfirmar).toHaveBeenCalledWith({
      nombre_archivo: "AF023_DAM_E2_20260115_v1.pdf",
      codigo_alumno: "AF023", ciclo: "DAM", fase: "E2", version: 1,
    })
  })

  it("enseña el motivo cuando no se ha podido deducir", () => {
    render(<ArchivoPendiente archivo={SIN_DEDUCIR} alConfirmar={vi.fn()} />)

    expect(screen.getByText(/no sigue la convención/)).toBeInTheDocument()
  })

  it("no ofrece confirmar sin rellenar cuando falta información", () => {
    render(<ArchivoPendiente archivo={SIN_DEDUCIR} alConfirmar={vi.fn()} />)

    expect(screen.getByRole("button", { name: /confirmar/i })).toBeDisabled()
  })

  it("permite escribir lo que falta y entonces confirma", async () => {
    const alConfirmar = vi.fn()
    render(<ArchivoPendiente archivo={SIN_DEDUCIR} alConfirmar={alConfirmar} />)

    await userEvent.type(screen.getByLabelText(/código/i), "AF031")
    await userEvent.type(screen.getByLabelText(/ciclo/i), "DAW")
    await userEvent.selectOptions(screen.getByLabelText(/fase/i), "E1")
    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }))

    expect(alConfirmar).toHaveBeenCalledWith({
      nombre_archivo: "trabajo de clase.pdf",
      codigo_alumno: "AF031", ciclo: "DAW", fase: "E1", version: 1,
    })
  })

  it("deja corregir una propuesta que se dedujo mal", async () => {
    const alConfirmar = vi.fn()
    render(<ArchivoPendiente archivo={DEDUCIDO} alConfirmar={alConfirmar} />)

    await userEvent.click(screen.getByRole("button", { name: /corregir/i }))
    await userEvent.selectOptions(screen.getByLabelText(/fase/i), "E3")
    await userEvent.click(screen.getByRole("button", { name: /confirmar/i }))

    expect(alConfirmar).toHaveBeenCalledWith(
      expect.objectContaining({ fase: "E3", codigo_alumno: "AF023" }),
    )
  })

  it("enseña el problema cuando el archivo no se ha podido leer bien", () => {
    render(<ArchivoPendiente archivo={CON_PROBLEMA} alConfirmar={vi.fn()} />)

    expect(screen.getByText(/permiso denegado/)).toBeInTheDocument()
  })
})
