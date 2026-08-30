import { useState } from "react"

import { FASES, MODALIDADES } from "../lib/tipos"
import type { ArchivoVisto, Confirmacion } from "../lib/tipos"

interface Props {
  archivo: ArchivoVisto
  alConfirmar: (datos: Confirmacion) => void
}

/**
 * Un archivo de la carpeta, con lo que el sistema propone y el gesto con el
 * que el docente lo confirma.
 *
 * La propuesta nunca se da por buena sola: aunque venga completa, siempre
 * hay un botón para corregirla. Es lo que D-009 reserva al docente, y la
 * interfaz no debería dejarle sin esa puerta de salida.
 */
export function ArchivoPendiente({ archivo, alConfirmar }: Props) {
  const { propuesta } = archivo
  const [editando, setEditando] = useState(!propuesta.completa)
  const [codigo, setCodigo] = useState(propuesta.codigo_alumno ?? "")
  const [ciclo, setCiclo] = useState(propuesta.ciclo ?? "")
  const [fase, setFase] = useState(propuesta.fase ?? "")
  const [version, setVersion] = useState(String(propuesta.version ?? 1))
  // El nombre del archivo no codifica la modalidad (§15.3), así que nunca
  // hay una propuesta que deducir: siempre empieza vacía. Es del proyecto,
  // no de esta entrega -mismo caso que el ciclo-, y puede faltar sin que
  // eso bloquee la confirmación: no existe todavía una pantalla propia de
  // validación de tema (§3.2) desde la que fijarla antes de la primera
  // entrega.
  const [modalidad, setModalidad] = useState("")

  // La versión entra en la condición de "listo": el campo lleva min={1},
  // pero eso no basta -no está dentro de un <form> con envío validado, así
  // que el navegador no lo hace cumplir-, y sin esta comprobación el botón
  // seguía habilitado con "-3" o con el campo vacío. El backend lo habría
  // rechazado, pero con un aviso desconectado del archivo que lo causó.
  const versionNumero = Number(version)
  const versionValida = Number.isInteger(versionNumero) && versionNumero >= 1
  const listo =
    codigo.trim() !== "" && ciclo.trim() !== "" && fase !== "" && versionValida

  function confirmar() {
    alConfirmar({
      nombre_archivo: archivo.nombre,
      codigo_alumno: codigo.trim().toUpperCase(),
      ciclo: ciclo.trim().toUpperCase(),
      fase,
      version: versionNumero,
      modalidad: modalidad || null,
    })
  }

  /**
   * Vuelve a lo que proponía el sistema y sale de la corrección.
   *
   * La pantalla entera existe para que el docente pueda corregir la
   * propuesta; dejarle atrapado dentro de una corrección que empezó por
   * error, o de la que se arrepiente, contradice eso mismo. Solo tiene
   * sentido cuando había una propuesta completa a la que volver -si el
   * archivo llegó sin deducir, el formulario es la única vista posible y
   * no hay nada que descartar.
   */
  function descartar() {
    setCodigo(propuesta.codigo_alumno ?? "")
    setCiclo(propuesta.ciclo ?? "")
    setFase(propuesta.fase ?? "")
    setVersion(String(propuesta.version ?? 1))
    setModalidad("")
    setEditando(false)
  }

  return (
    <li className="border-b border-grisclaro py-5">
      <p className="font-mono text-[13px]">{archivo.nombre}</p>

      {!editando ? (
        <p className="mt-2 text-[13px] text-gris">
          {codigo} · {ciclo} · {fase} · versión {version}
        </p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-4">
          <label className="text-[12px] uppercase tracking-[0.08em] text-gris">
            Código
            <input
              value={codigo}
              onChange={(evento) => setCodigo(evento.target.value)}
              className="block mt-1 border-b border-tinta bg-transparent
                         text-[14px] normal-case tracking-normal text-tinta py-1"
            />
          </label>
          <label className="text-[12px] uppercase tracking-[0.08em] text-gris">
            Ciclo
            <input
              value={ciclo}
              onChange={(evento) => setCiclo(evento.target.value)}
              className="block mt-1 border-b border-tinta bg-transparent
                         text-[14px] normal-case tracking-normal text-tinta py-1"
            />
          </label>
          <label className="text-[12px] uppercase tracking-[0.08em] text-gris">
            Fase
            <select
              value={fase}
              onChange={(evento) => setFase(evento.target.value)}
              className="block mt-1 border-b border-tinta bg-transparent
                         text-[14px] normal-case tracking-normal text-tinta py-1"
            >
              <option value="">—</option>
              {FASES.map((cada) => (
                <option key={cada} value={cada}>{cada}</option>
              ))}
            </select>
          </label>
          <label className="text-[12px] uppercase tracking-[0.08em] text-gris">
            Modalidad
            <select
              value={modalidad}
              onChange={(evento) => setModalidad(evento.target.value)}
              className="block mt-1 border-b border-tinta bg-transparent
                         text-[14px] normal-case tracking-normal text-tinta py-1"
            >
              <option value="">Sin especificar</option>
              {MODALIDADES.map((cada) => (
                <option key={cada} value={cada}>{cada}</option>
              ))}
            </select>
          </label>
          <label className="text-[12px] uppercase tracking-[0.08em] text-gris">
            Versión
            <input
              type="number"
              min={1}
              value={version}
              onChange={(evento) => setVersion(evento.target.value)}
              className="block mt-1 w-20 border-b border-tinta bg-transparent
                         text-[14px] normal-case tracking-normal text-tinta py-1"
            />
          </label>
        </div>
      )}

      {archivo.problema && (
        // El archivo no se ha podido leer bien al mirar la carpeta -permiso,
        // antivirus, sincronización en la nube-. No es la identificación lo
        // que falla, pero también es algo que el docente tiene que mirar
        // antes de confiar en lo que sigue.
        <p className="mt-3 max-w-lectura text-[13px] senal">{archivo.problema}</p>
      )}

      {propuesta.motivo && (
        <p className="mt-3 max-w-lectura text-[13px] senal">{propuesta.motivo}</p>
      )}

      <div className="mt-4 flex gap-5">
        <button
          onClick={confirmar}
          disabled={!listo}
          className="text-[13px] border-b-2 border-tinta pb-1
                     disabled:border-grisclaro disabled:text-gris"
        >
          Confirmar
        </button>
        {!editando && (
          <button
            onClick={() => setEditando(true)}
            className="text-[13px] text-gris pb-1"
          >
            Corregir
          </button>
        )}
        {editando && propuesta.completa && (
          <button
            onClick={descartar}
            className="text-[13px] text-gris pb-1"
          >
            Descartar
          </button>
        )}
      </div>
    </li>
  )
}
