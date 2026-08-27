import type {
  CambioDeValor, Documento, EstadoGobernanza, Pendiente,
  Propuesta, Resultado, Seccion, CriterioDerivado,
} from "./tipos"

const BASE = "/api"

async function pedir<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  const respuesta = await fetch(`${BASE}${ruta}`, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  })
  if (!respuesta.ok) {
    const detalle = await respuesta.text()
    throw new Error(`${respuesta.status}: ${detalle}`)
  }
  return respuesta.json() as Promise<T>
}

export const api = {
  documentos: () => pedir<Documento[]>("/documentos"),

  seccion: (ancla: string) =>
    pedir<{ seccion: Seccion; criterios: CriterioDerivado[] }>(
      `/secciones/${encodeURIComponent(ancla)}`,
    ),

  propuesta: (ancla: string, textoNuevo: string) =>
    pedir<Propuesta[]>("/propuesta", {
      method: "POST",
      body: JSON.stringify({ ancla, texto_nuevo: textoNuevo }),
    }),

  guardar: (datos: {
    ancla: string
    texto_nuevo: string
    cambios: CambioDeValor[]
    motivo: string
    fuente: string
    hash_esperado: string
  }) => pedir<Resultado>("/guardar", {
    method: "POST",
    body: JSON.stringify(datos),
  }),

  estado: () => pedir<EstadoGobernanza>("/estado"),
  pendientes: () => pedir<Pendiente[]>("/pendientes"),
}
