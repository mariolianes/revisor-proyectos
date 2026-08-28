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

// --- El flujo de entregas -------------------------------------------------
//
// Se llama PropuestaArchivo, no Propuesta, para no chocar con el Propuesta
// del editor (más arriba en este fichero). Las formas siguen al backend
// (backend/vigilancia/carpeta.py, backend/vigilancia/nombres.py,
// backend/servicios/lectura_objetiva.py), no al brief de la Task 13: hay
// diferencias entre ambos y manda el backend -están explicadas en el
// informe de esa tarea.

export interface PropuestaArchivo {
  codigo_alumno: string | null
  ciclo: string | null
  fase: string | null
  fecha: string | null
  version: number | null
  motivo: string
  completa: boolean
}

export interface ArchivoVisto {
  /**
   * La ruta relativa a la carpeta de entregas, no el nombre suelto del
   * archivo: puede incluir la subcarpeta del alumno (§15.2).
   */
  nombre: string
  ruta: string
  modificado_en: string | null
  propuesta: PropuestaArchivo
  /**
   * Por qué no se ha podido leer el archivo -permiso denegado, bloqueo del
   * antivirus, un archivo aún no descargado de la nube-. Vacío cuando no
   * hay ningún problema.
   */
  problema: string
}

export interface EntregaRegistrada {
  id: string
  codigo_alumno: string
  ciclo: string
  fase: string
  version: number
  nombre_archivo: string
  huella: string
  recibida_en: string
  estado: string
  motivo_bloqueo: string | null
  version_criterios: string
}

export interface Comprobacion {
  criterio: string
  veredicto: "CUMPLE" | "NO_CUMPLE" | "NO_VERIFICABLE"
  esperado: string
  medido: string
  fuente: string
  nota: string
}

export interface Evolucion {
  proporcion_conservada: number
  proporcion_nueva: number
  parrafos_antes: number
  parrafos_despues: number
  avisos: string[]
}

export interface PaginaMedida {
  numero: number
  caracteres: number
  en_blanco: boolean
  ancho_pt: number
  alto_pt: number
}

export interface MedidasDeTexto {
  familia_dominante: string
  cuerpo_dominante: number | null
  proporcion_cuerpo_dominante: number
  ratio_interlineado: number | null
  margen_izquierdo_cm: number | null
  margen_derecho_cm: number | null
  margen_superior_cm: number | null
  margen_inferior_cm: number | null
  proporcion_lineas_al_margen_derecho: number | null
}

export interface EntradaDeIndice {
  titulo: string
  pagina_declarada: number
  pagina_encontrada: number | null
}

export interface MedidasDeEstructura {
  pagina_del_indice: number | null
  primera_pagina_de_contenido: number | null
  primera_pagina_de_anexos: number | null
  paginas_de_contenido: number | null
  entradas_de_indice: EntradaDeIndice[]
  titulos_no_encontrados: string[]
  paginas_declaradas_incorrectas: string[]
}

export interface ImagenMedida {
  pagina: number
  ancho_px: number
  alto_px: number
  dpi_efectivo: number
  proporcion_de_pagina: number
}

export interface MedidasDeEntrega {
  nombre_archivo: string
  huella: string
  paginas: PaginaMedida[]
  total_paginas: number
  paginas_en_blanco: number[]
  escaneado: boolean
  texto: MedidasDeTexto
  estructura: MedidasDeEstructura
  imagenes: ImagenMedida[]
}

export interface FichaDeLectura {
  entrega: EntregaRegistrada
  medidas: MedidasDeEntrega | null
  comprobaciones: Comprobacion[]
  evolucion: Evolucion | null
  comparada_con: string | null
  aviso: string
}

export interface Entorno {
  hay_carpeta: boolean
  carpeta: string | null
  persistencia_duradera: boolean
  version_criterios: string
  avisos: string[]
}

export interface Confirmacion {
  nombre_archivo: string
  codigo_alumno: string
  ciclo: string
  fase: string
  version: number
}

export const FASES = ["TEMA", "E1", "E2", "E3", "FINAL", "DEFENSA"] as const
