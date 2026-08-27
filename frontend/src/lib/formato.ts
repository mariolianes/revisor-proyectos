/**
 * Los valores de los criterios llegan como cadenas. Cuando el campo original
 * era una lista en el YAML, el backend la sirve con el formato de Python
 * (p.ej. "['E2', 'E3', 'FINAL']"). Sigue siendo una cadena: esto solo la
 * hace legible, no la convierte en otra cosa.
 */
export function formatearValor(valor: string): string {
  const esListaDePython = /^\[.*\]$/.test(valor.trim())
  if (!esListaDePython) return valor

  return valor
    .trim()
    .slice(1, -1)
    .split(",")
    .map((elemento) => elemento.trim().replace(/^['"]|['"]$/g, ""))
    .filter((elemento) => elemento.length > 0)
    .join(", ")
}
