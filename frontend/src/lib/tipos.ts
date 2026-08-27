export interface Seccion {
  ancla: string
  titulo: string
  texto: string
  hash: string
  criterios_que_la_citan: number
}

export interface Documento {
  clave: string
  titulo: string
  fichero: string
  secciones: Seccion[]
}

export interface CriterioDerivado {
  fichero: string
  identificador: string
  valores: Record<string, string>
  fuente: string
}

export interface Propuesta {
  fichero: string
  identificador: string
  clave: string
  valor_actual: string
  valor_propuesto: string | null
  motivo: string
}

export interface CambioDeValor {
  fichero: string
  identificador: string
  clave: string
  valor_nuevo: string
}

export interface Resultado {
  exito: boolean
  commit: string | null
  infracciones: { regla: string; fichero: string; detalle: string }[]
  mensaje: string
}

export interface Regla {
  codigo: string
  nombre: string
  vigila: string
  limite: string
  infracciones: number
}

export interface EstadoGobernanza {
  conforme: boolean
  reglas: Regla[]
}

export interface Pendiente {
  clave: string
  explicacion: string
}
