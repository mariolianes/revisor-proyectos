import { useEffect, useState } from "react"

import { DialogoGuardar } from "../componentes/DialogoGuardar"
import { PanelCriterios } from "../componentes/PanelCriterios"
import { api } from "../lib/api"
import type {
  CambioDeValor, CriterioDerivado, Propuesta, Resultado, Seccion,
} from "../lib/tipos"

interface Props {
  ancla: string
  alVolver: () => void
}

export function Editor({ ancla, alVolver }: Props) {
  const [seccion, setSeccion] = useState<Seccion | null>(null)
  const [criterios, setCriterios] = useState<CriterioDerivado[]>([])
  const [texto, setTexto] = useState("")
  const [propuestas, setPropuestas] = useState<Propuesta[] | null>(null)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setError(null)
    api.seccion(ancla).then(({ seccion, criterios }) => {
      setSeccion(seccion)
      setCriterios(criterios)
      setTexto(seccion.texto)
    }).catch((e: Error) => setError(e.message))
  }, [ancla])

  // Este retorno anticipado a pantalla completa es solo para cuando la
  // sección nunca llegó a cargarse: ahí no hay texto ni enlace que
  // proteger. Un fallo posterior (al proponer o al guardar) NO pasa por
  // aquí — se enseña dentro de la pantalla, para no borrar lo que el
  // profesor lleva escrito. Ver guardar() y abrirDialogo() más abajo.
  if (!seccion) {
    return error
      ? <p className="text-tinta">{error}</p>
      : <p className="text-gris">Cargando…</p>
  }

  const sinCambios = texto === seccion.texto

  const abrirDialogo = async () => {
    setError(null)
    try {
      setPropuestas(await api.propuesta(ancla, texto))
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const guardar = async (datos: {
    cambios: CambioDeValor[]
    motivo: string
    fuente: string
  }) => {
    setError(null)
    try {
      const respuesta = await api.guardar({
        ancla,
        texto_nuevo: texto,
        cambios: datos.cambios,
        motivo: datos.motivo,
        fuente: datos.fuente,
        hash_esperado: seccion.hash,
      })
      setPropuestas(null)
      setResultado(respuesta)
      if (respuesta.exito) {
        const recargada = await api.seccion(ancla)
        setSeccion(recargada.seccion)
        setCriterios(recargada.criterios)
        setTexto(recargada.seccion.texto)
      }
    } catch (e) {
      setPropuestas(null)
      setError((e as Error).message)
    }
  }

  return (
    <div>
      <button onClick={alVolver} className="text-[12px] text-gris mb-6">
        ← Documentos
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_20rem] gap-12">
        <div>
          <h2 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-gris mb-1">
            {seccion.titulo}
          </h2>
          <p className="font-mono text-[11px] text-gris mb-6">{seccion.ancla}</p>

          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            className="w-full max-w-lectura min-h-[24rem] border border-grisclaro
                       bg-white p-4 text-[15px] leading-[1.65] font-base"
          />

          <div className="mt-4 flex items-center gap-4">
            <button
              onClick={abrirDialogo}
              disabled={sinCambios}
              className="px-4 py-2 text-[13px] bg-tinta text-papel disabled:opacity-30"
            >
              Guardar cambio
            </button>
            {sinCambios && (
              <span className="text-[12px] text-gris">No has cambiado nada.</span>
            )}
          </div>

          {error && (
            <p className="mt-4 text-[13px] text-tinta">{error}</p>
          )}

          {resultado && (
            <div className="mt-6 border-t border-grisclaro pt-4">
              <p className="text-[13px]">{resultado.mensaje}</p>
              {resultado.commit && (
                <p className="font-mono text-[12px] text-gris mt-1">
                  commit {resultado.commit}
                </p>
              )}
              {resultado.infracciones.length > 0 && (
                <ul className="mt-3 space-y-2">
                  {resultado.infracciones.map((i, indice) => (
                    <li key={indice} className="text-[12px]">
                      <span className="font-mono text-tinta">[{i.regla}]</span>{" "}
                      <span className="font-mono text-gris">{i.fichero}</span>
                      <p className="text-gris mt-1">{i.detalle}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <aside>
          <PanelCriterios criterios={criterios} />
        </aside>
      </div>

      {propuestas && (
        <DialogoGuardar
          propuestas={propuestas}
          alConfirmar={guardar}
          alCancelar={() => setPropuestas(null)}
        />
      )}
    </div>
  )
}
