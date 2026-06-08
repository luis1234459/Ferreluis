/**
 * Zebra Browser Print — utilidad para imprimir etiquetas ZPL desde Ferreutil.
 *
 * Uso:
 *   import { imprimirEtiqueta } from '@/utils/zebra'
 *   await imprimirEtiqueta({ nombre, codigo, precioUsd, precioBs })
 *
 * Requiere: Zebra Browser Print instalado y corriendo en la PC del usuario.
 * Etiqueta: 2" × 1.25" — 203 dpi — Zebra GK420t (térmica directa o transferencia).
 */

const ENDPOINTS = ['http://localhost:9100', 'https://localhost:9101']

let _device = null
let _apiBase = null

/**
 * Conecta a Zebra Browser Print y devuelve el dispositivo.
 * Cachea la conexión para no buscar en cada impresión.
 */
export async function conectarZebra() {
  if (_device && _apiBase) return { device: _device, api: _apiBase }

  for (const base of ENDPOINTS) {
    try {
      const r = await fetch(base + '/available?type=printer', { signal: AbortSignal.timeout(3000) })
      if (!r.ok) continue
      const data = await r.json()
      const printers = data.printer || data.printers || data
      const lista = Array.isArray(printers) ? printers : [printers]
      if (lista.length > 0 && lista[0].uid) {
        _device = lista[0]
        _apiBase = base
        return { device: _device, api: _apiBase }
      }
    } catch { /* intentar siguiente endpoint */ }
  }
  throw new Error('No se pudo conectar a Zebra Browser Print. ¿Está corriendo?')
}

/**
 * Resetea la conexión cacheada (útil si la impresora se desconecta).
 */
export function resetConexionZebra() {
  _device = null
  _apiBase = null
}

/**
 * Genera el ZPL para una etiqueta 2" × 1.25" con nombre, código de barras y precios.
 */
export function generarZPL({ nombre, codigo, precioUsd, precioBs }) {
  const n = (nombre || '').toUpperCase()
  const c = codigo || ''
  const usd = '$' + Number(precioUsd || 0).toFixed(2)
  const bs = 'Bs ' + Number(precioBs || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })

  const nombre1 = n.substring(0, 30)
  const nombre2 = n.length > 30 ? n.substring(30, 60) : ''
  const barcodeY = nombre2 ? 62 : 42

  let z = '^XA\n'
  z += '^PW406\n^LL254\n^LH0,0\n'
  z += '^FO10,8^A0N,24,24^FD' + nombre1 + '^FS\n'
  if (nombre2) z += '^FO10,34^A0N,22,22^FD' + nombre2 + '^FS\n'
  z += '^FO30,' + barcodeY + '^BY2^BCN,70,N,N,N^FD' + c + '^FS\n'
  z += '^FO30,' + (barcodeY + 74) + '^A0N,18,18^FD' + c + '^FS\n'
  z += '^FO10,214^GB386,1,1^FS\n'
  z += '^FO10,220^A0N,28,28^FD' + usd + '^FS\n'
  z += '^FO220,222^A0N,22,22^FD' + bs + '^FS\n'
  z += '^XZ\n'
  return z
}

/**
 * Imprime una etiqueta. Conecta automáticamente si no está conectado.
 *
 * @param {Object} datos - { nombre, codigo, precioUsd, precioBs }
 * @param {number} [cantidad=1] - cuántas etiquetas imprimir
 * @returns {Promise<{ok: boolean, mensaje: string}>}
 */
export async function imprimirEtiqueta(datos, cantidad = 1) {
  try {
    const { device, api } = await conectarZebra()
    const zpl = generarZPL(datos)

    // Repetir ZPL si se piden múltiples etiquetas
    const payload = cantidad > 1 ? zpl.repeat(cantidad) : zpl

    const r = await fetch(api + '/write', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device, data: payload })
    })

    if (r.ok) {
      return { ok: true, mensaje: cantidad > 1 ? `${cantidad} etiquetas impresas` : 'Etiqueta impresa' }
    }

    const txt = await r.text()
    // Si falla, resetear conexión para reintentar en la próxima
    resetConexionZebra()
    return { ok: false, mensaje: 'Error: ' + (txt || r.status) }

  } catch (e) {
    resetConexionZebra()
    return { ok: false, mensaje: e.message }
  }
}
