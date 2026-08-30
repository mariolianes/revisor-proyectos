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
  /**
   * 'verificada' si hay código que la comprueba; 'parcial' si protege una
   * parte real de lo que promete y el resto es un hueco conocido, no un
   * olvido; 'pendiente' si aún no vigila nada.
   */
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

// --- El análisis y la revisión docente -------------------------------------
//
// Las formas siguen a `backend/api/analisis.py`, `backend/analisis/
// verificacion.py` y `backend/salidas/{informe,borrador}.py`, no al brief de
// la Task 13. `Revision` es el nombre del componente de esta misma tarea
// (`frontend/src/paginas/Revision.tsx`); el cuerpo que ese componente envía
// a `POST /entregas/{id}/revision` se llama aquí `PeticionRevision`, no
// `Revision`, por la misma razón que `PropuestaArchivo` no se llama
// `Propuesta`: para no chocar con el nombre con el que ya se necesita este
// fichero en otro sitio.

export interface Evidencia {
  cita: string
  apartado: string
}

export interface ValoracionVerificada {
  dimension: string
  nivel: string
  prioridad: string | null
  evidencia: Evidencia
  observacion: string
  /**
   * Si la cita se ha encontrado, literal, en el texto del trabajo. En falso
   * quiere decir que el docente puede verla y decidir, pero que tal como
   * está no pasará a la devolución del alumno.
   */
  evidencia_localizada: boolean
}

export interface FortalezaVerificada {
  descripcion: string
  evidencia: Evidencia
  /**
   * Igual que en `ValoracionVerificada`: si es falso, al alumno no le llega
   * -el borrador la filtra-, pero el informe interno la trae de todos
   * modos para que el docente la vea y decida.
   */
  evidencia_localizada: boolean
}

export interface IndicioDeAutoriaVerificado {
  descripcion: string
  evidencia: Evidencia
  evidencia_localizada: boolean
}

export interface Reparo {
  regla: string
  detalle: string
}

// Los cinco estados de `Informe.estado_nota` (D-015, `docs/decisions.md`):
// nace `pendiente_de_rubrica` -o `no_aplicable`, en TEMA y DEFENSA, que
// nunca llevan nota de corrección- y solo pasa a `propuesta` cuando existe
// una rúbrica oficial cargada y versionada de la que calcular un número.
// `aprobada` y `modificada` son la decisión del docente en `revisar()`:
// nunca las pone el motor, y nunca hay una sin que antes exista una
// `propuesta` sobre la que decidir.
export const ESTADOS_NOTA = [
  "pendiente_de_rubrica", "propuesta", "modificada", "aprobada", "no_aplicable",
] as const
export type EstadoNota = (typeof ESTADOS_NOTA)[number]

export const CODIGOS_SEMAFORO = ["VERDE", "AMBAR", "ROJO", "GRIS"] as const
export type CodigoDeSemaforo = (typeof CODIGOS_SEMAFORO)[number]

export interface Informe {
  identificacion: Record<string, string>
  control_administrativo: string[]
  resumen: string
  /**
   * La síntesis provisional de D-017: cinco o seis líneas compuestas por el
   * sistema a partir de piezas ya verificadas, para que el docente las
   * reescriba en la lectura del conjunto que el §17.1 y el §11.1 describen.
   * Nunca se cierra sola: `revisar()` la guarda tal cual la deje el
   * docente, editada o no.
   */
  sintesis_provisional: string
  valoraciones: ValoracionVerificada[]
  fortalezas: FortalezaVerificada[]
  /** Como mucho las que fija la economía pedagógica (hoy, cuatro). */
  prioridades: ValoracionVerificada[]
  /** Tenían prioridad y evidencia, pero no cupieron en el límite. */
  prioridades_descartadas: ValoracionVerificada[]
  dudas: string[]
  indicios: IndicioDeAutoriaVerificado[]
  reparos: Reparo[]
  dimensiones_ausentes: string[]
  /**
   * El que propone el sistema al analizar (D-016). Inalterable después de
   * ese momento -ni siquiera `revisar()` lo recalcula-: es la prueba de
   * auditoría de lo que se propuso antes de que nadie revisara nada.
   */
  semaforo_propuesto: string
  /**
   * El que el docente confirma al cerrar la revisión, o `null` mientras no
   * lo haya hecho. No puede ser un color menos severo del que sostienen
   * las observaciones que siguen aprobadas -`revisar()` lo rechaza antes de
   * guardar nada si lo es-.
   */
  semaforo_final_docente: string | null
  recomendacion: string | null
  /**
   * La estimación interna del sistema (D-015). `null` mientras
   * `estado_nota` sea `pendiente_de_rubrica` o `no_aplicable`: no hay
   * número que enseñar cuando no hay de qué calcularlo. Nunca la propone
   * el motor -el contrato del motor sigue sin admitir ningún campo de
   * nota-, la calcula el sistema a partir de una rúbrica oficial.
   */
  nota_propuesta_sistema: number | null
  estado_nota: EstadoNota
  /** De qué rúbrica salió `nota_propuesta_sistema`, o `null` sin rúbrica. */
  version_rubrica: string | null
  /** El peso de cada dimensión en el cálculo, o `null` sin rúbrica. */
  ponderaciones_nota: Record<string, number> | null
  /** Lo que el docente aprueba o modifica en `revisar()` (§13). */
  nota_final_docente: number | null
  /**
   * Opcional. Sobre el criterio de corrección -qué pesó en el cambio-,
   * nunca sobre el alumno: no hay ningún campo de este sistema donde una
   * circunstancia personal tenga sitio.
   */
  motivo_modificacion_nota: string | null
  motor: string
}

export interface Devolucion {
  apertura: string
  fortalezas: string[]
  acciones: string[]
  cierre: string
}

export interface ResultadoAnalisis {
  entrega: EntregaRegistrada
  informe: Informe
  /**
   * `null` cuando el informe salió bien y solo falló la redacción del
   * borrador (`aviso` explica por qué). No es un error: el informe sigue
   * siendo válido y usable.
   */
  devolucion: Devolucion | null
  motor: string
  /** Presente solo en el caso de arriba. */
  aviso: string | null
}

export const DECISIONES = ["ACEPTADA", "EDITADA", "DESCARTADA"] as const
export type CodigoDeDecision = (typeof DECISIONES)[number]

export interface Decision {
  dimension: string
  decision: CodigoDeDecision
  /** Solo se usa -y solo se manda- cuando `decision` es `EDITADA`. */
  texto?: string | null
}

/**
 * El cuerpo de `POST /entregas/{id}/revision`.
 *
 * Los cuatro campos nuevos comparten un criterio con el backend
 * (`Revision` en `backend/api/analisis.py`): omitirlos -o mandar `null`- no
 * borra nada, conserva lo que ya hubiera guardado. Solo `decisiones` es
 * obligatorio; el resto son opcionales a propósito, para que una petición
 * que no toca ninguno de los tres siga funcionando igual que antes de esta
 * tarea.
 */
export interface PeticionRevision {
  decisiones: Decision[]
  semaforo_final_docente?: string | null
  nota_final_docente?: number | null
  motivo_modificacion_nota?: string | null
  sintesis_provisional?: string | null
}
