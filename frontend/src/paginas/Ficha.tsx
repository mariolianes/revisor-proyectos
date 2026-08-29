import { useEffect, useState } from "react"

import { TablaComprobaciones } from "../componentes/TablaComprobaciones"
import { api } from "../lib/api"
import type { FichaDeLectura, ResultadoAnalisis } from "../lib/tipos"

interface Props {
  id: string
  /**
   * La ficha que devolvió `POST /api/entregas`, cuando se llega aquí desde
   * confirmar un archivo. Si viene, se usa y NO se vuelve a pedir.
   *
   * No es un atajo para ahorrarse una petición. `POST /api/entregas`
   * compone avisos que solo existen en el momento de confirmar -que el
   * archivo ya estaba registrado, que el ciclo declarado no es el del
   * alumno- y que `GET /api/entregas/{id}` no puede conocer, porque nadie
   * ha declarado nada al abrir una ficha. Volver a pedirla los borraba:
   * el backend los componía, el frontend los tiraba, y los tres tests de
   * backend que los protegían pasaban todos.
   */
  inicial?: FichaDeLectura | null
  alVolver: () => void
  /**
   * Analizar llama al motor y tarda; hecho, se abre la revisión con el
   * resultado que ya trae la respuesta, igual que confirmar abre la ficha
   * con lo que devuelve `POST /api/entregas` sin volver a pedirla.
   */
  alAnalizar: (id: string, resultado: ResultadoAnalisis) => void
}

/**
 * Lo medido, lo comprobado y lo comparado de una entrega: lo que el docente
 * mira antes de sentarse a leer el PDF.
 *
 * No hay nota, ni valoración, ni semáforo, ni botón de aprobar, y no es un
 * olvido: las ponderaciones de la programación didáctica siguen sin
 * publicarse -R3 impide sustituir un dato oficial que falta por una
 * estimación-, y aprobar y calificar son del §13, reservados al docente. Que
 * la pantalla no ofrezca esos gestos es la forma de que el sistema no los
 * haga; el pie lo dice con todas las letras para que la ausencia no parezca
 * una función a medio hacer.
 *
 * `error` es un fallo técnico -sin servidor, sin red-, no una decisión que
 * le toque al docente, así que no lleva la tinta `senal`: se pinta igual
 * que en Documentos, Estado y Pendientes (ver el docstring de Entregas).
 * `senal` aquí se reserva al motivo de una entrega bloqueada y a los
 * avisos: que el servidor esté apagado no es culpa del alumno ni dice nada
 * de su trabajo, y pintarlo igual que un incumplimiento le daría un peso
 * que no tiene.
 */
export function Ficha({ id, inicial, alVolver, alAnalizar }: Props) {
  const [ficha, setFicha] = useState<FichaDeLectura | null>(inicial ?? null)
  const [error, setError] = useState("")
  const [analizando, setAnalizando] = useState(false)
  const [errorAnalisis, setErrorAnalisis] = useState("")

  useEffect(() => {
    // Con la ficha ya leída no se pide nada: la del POST está recién medida
    // -pasa por el mismo `leer()`- y además trae los avisos de confirmar,
    // que un GET no devuelve. Refrescarla sería cambiar una ficha completa
    // por otra con menos.
    if (inicial) return
    let vigente = true
    api.ficha(id)
      .then((leida) => { if (vigente) setFicha(leida) })
      .catch((fallo) => {
        if (vigente) setError(fallo instanceof Error ? fallo.message : String(fallo))
      })
    return () => { vigente = false }
  }, [id, inicial])

  if (error) {
    return (
      <div className="max-w-3xl">
        <p className="mb-6 max-w-lectura text-[13px] text-tinta">{error}</p>
        <button onClick={alVolver} className="text-[13px] text-gris">
          Volver
        </button>
      </div>
    )
  }

  if (!ficha) {
    return <p className="text-[13px] text-gris">Leyendo el documento…</p>
  }

  const { entrega, medidas, evolucion } = ficha

  // Solo con la entrega RECIBIDO y sin bloquear: RECIBIDO ya excluye
  // BLOQUEADO -son valores del mismo campo `estado`-, pero se comprueban
  // las dos cosas por separado porque son dos preguntas distintas y no hay
  // que fiarse de que una las implique siempre a la otra si el backend
  // cambiara. Una entrega ANALIZADO no vuelve a ofrecerlo: pedirlo dos
  // veces vuelve a llamar al motor y a costar dinero, y esta pantalla no
  // abre un camino para eso.
  const puedeAnalizar = entrega.estado === "RECIBIDO" && !entrega.motivo_bloqueo

  async function analizar() {
    if (analizando) return
    setErrorAnalisis("")
    setAnalizando(true)
    try {
      const resultado = await api.analizar(id)
      alAnalizar(id, resultado)
    } catch (fallo) {
      setErrorAnalisis(fallo instanceof Error ? fallo.message : String(fallo))
    } finally {
      setAnalizando(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <button onClick={alVolver} className="text-[13px] text-gris mb-8">
        ← Volver
      </button>

      <h2 className="text-[19px] mb-1">
        {entrega.codigo_alumno} · {entrega.ciclo} · {entrega.fase} · versión{" "}
        {entrega.version}
      </h2>
      <p className="font-mono text-[12px] text-gris mb-6">
        {entrega.nombre_archivo}
      </p>

      {puedeAnalizar && (
        <div className="mb-10">
          <button
            onClick={analizar}
            disabled={analizando}
            className="px-4 py-2 text-[13px] bg-tinta text-papel disabled:opacity-30"
          >
            {analizando ? "Analizando…" : "Analizar"}
          </button>
          {errorAnalisis && (
            <p className="mt-3 max-w-lectura text-[13px] text-tinta">
              {errorAnalisis}
            </p>
          )}
        </div>
      )}

      {entrega.estado === "BLOQUEADO" && entrega.motivo_bloqueo && (
        <p className="mb-10 max-w-lectura text-[13px] senal">
          {entrega.motivo_bloqueo}
        </p>
      )}

      {ficha.aviso && (
        <p className="mb-10 max-w-lectura text-[13px] senal">{ficha.aviso}</p>
      )}

      {medidas && (
        <section className="mb-14">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
            Lo que se ha medido
          </h3>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-[13px] md:grid-cols-3">
            <Dato rotulo="Páginas" valor={String(medidas.total_paginas)} />
            <Dato
              rotulo="De contenido"
              valor={medidas.estructura.paginas_de_contenido !== null
                ? String(medidas.estructura.paginas_de_contenido)
                : "no se ha podido contar"}
            />
            <Dato
              rotulo="Tipografía"
              valor={medidas.texto.familia_dominante
                && medidas.texto.cuerpo_dominante !== null
                ? `${medidas.texto.familia_dominante} ${medidas.texto.cuerpo_dominante}`
                : "sin texto extraíble"}
            />
            <Dato
              rotulo="Interlineado"
              valor={medidas.texto.ratio_interlineado !== null
                ? `ratio ${medidas.texto.ratio_interlineado.toFixed(2)}`
                : "no medible"}
            />
            <Dato
              rotulo="Páginas en blanco"
              valor={medidas.paginas_en_blanco.length
                ? medidas.paginas_en_blanco.join(", ")
                : "ninguna"}
            />
            <Dato rotulo="Imágenes" valor={String(medidas.imagenes.length)} />
          </dl>
        </section>
      )}

      {ficha.comprobaciones.length > 0 && (
        <section className="mb-14">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
            Formato
          </h3>
          <TablaComprobaciones comprobaciones={ficha.comprobaciones} />
        </section>
      )}

      {evolucion && (
        <section className="mb-14">
          <h3 className="text-[12px] uppercase tracking-[0.12em] text-gris mb-4">
            Frente a la entrega anterior
          </h3>
          <p className="text-[13px] text-gris mb-3">
            Comparada con{" "}
            <span className="font-mono">{ficha.comparada_con}</span>.
          </p>
          <p className="max-w-lectura text-[13px]">
            Se conserva el {(evolucion.proporcion_conservada * 100).toFixed(0)}
            {" "}% de lo anterior. El{" "}
            {(evolucion.proporcion_nueva * 100).toFixed(0)} % del texto actual
            no estaba antes. Antes tenía {evolucion.parrafos_antes} párrafos;
            ahora tiene {evolucion.parrafos_despues}.
          </p>
          {evolucion.avisos.map((aviso) => (
            <p key={aviso} className="mt-3 max-w-lectura text-[13px] senal">
              {aviso}
            </p>
          ))}
        </section>
      )}

      <p className="max-w-lectura border-t border-grisclaro pt-5 text-[12px] text-gris">
        Esta ficha no propone calificación. Las ponderaciones de la
        programación didáctica siguen sin publicarse, y el sistema no
        sustituye un dato oficial que falta por una estimación. La
        valoración es tuya.
      </p>
    </div>
  )
}

function Dato({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-[0.08em] text-gris">
        {rotulo}
      </dt>
      <dd className="mt-1">{valor}</dd>
    </div>
  )
}
