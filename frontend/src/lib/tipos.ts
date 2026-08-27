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
  /**
   * El valor sigue apareciendo, palabra por palabra, en el texto nuevo: la
   * prosa que lo respalda no lo ha tocado, así que llega al diálogo ya
   * marcado como revisado sin cambio. El docente puede desmarcarlo.
   */
  revisado_sin_cambio?: boolean
}

export interface CambioDeValor {
  fichero: string
  identificador: string
  clave: string
  /**
   * Lo que el criterio pasa a decir, o null cuando el docente ha declarado
   * que lo ha revisado y sigue siendo correcto. Las dos cosas son
   * decisiones suyas; no decir nada de un criterio no lo es.
   */
  valor_nuevo: string | null
}

export interface Infraccion {
  regla: string
  fichero: string
  detalle: string
}

export interface Resultado {
  exito: boolean
  commit: string | null
  infracciones: Infraccion[]
  mensaje: string
  /** Salida de git o de una excepción. Para quien depure, no para el docente. */
  detalle_tecnico?: string | null
}

export interface Regla {
  codigo: string
  nombre: string
  vigila: string
  limite: string
  /** 'verificada' si hay código que la comprueba, 'pendiente' si aún no. */
  estado: string
  infracciones: number
  detalles: Infraccion[]
}

export interface EstadoGobernanza {
  conforme: boolean
  reglas: Regla[]
}

export interface Pendiente {
  clave: string
  explicacion: string
}
