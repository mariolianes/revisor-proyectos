import type {
  ArchivoVisto, CambioDeValor, Confirmacion, Documento, EntregaRegistrada,
  Entorno, EstadoGobernanza, FichaDeLectura, Pendiente,
  Propuesta, Resultado, Seccion, CriterioDerivado,
} from "./tipos"

const BASE = "/api"

async function pedir<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  let respuesta: Response
  try {
    respuesta = await fetch(`${BASE}${ruta}`, {
      headers: { "Content-Type": "application/json" },
      ...opciones,
    })
  } catch {
    // fetch falla así cuando no hay nadie escuchando en el otro extremo:
    // no es un error de la API, es que el servidor no está arrancado.
    throw new Error(
      "No se ha podido contactar con el servidor. Comprueba que esté " +
      "arrancado en 127.0.0.1:8000.",
    )
  }
  if (!respuesta.ok) {
    const cuerpo = await respuesta.text()
    let mensaje = cuerpo
    try {
      const json = JSON.parse(cuerpo)
      if (json && typeof json.detail === "string") {
        mensaje = json.detail
      }
    } catch {
      // El cuerpo no era JSON: se usa el texto crudo tal cual.
    }
    const error = new Error(mensaje) as Error & { estado: number }
    error.estado = respuesta.status
    throw error
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

  entorno: () => pedir<Entorno>("/entorno"),

  archivosPendientes: () => pedir<ArchivoVisto[]>("/entregas/pendientes"),

  entregas: () => pedir<EntregaRegistrada[]>("/entregas"),

  confirmar: (datos: Confirmacion) =>
    pedir<FichaDeLectura>("/entregas", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  ficha: (id: string) =>
    pedir<FichaDeLectura>(`/entregas/${encodeURIComponent(id)}`),

  cambiarEstado: (id: string, estado: string, motivo: string | null) =>
    pedir<EntregaRegistrada>(`/entregas/${encodeURIComponent(id)}/estado`, {
      method: "POST",
      body: JSON.stringify({ estado, motivo }),
    }),
}
