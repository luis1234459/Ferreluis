// Estado global de la sede activa (Fase 1K) — fuente única de verdad,
// persistido en localStorage y compartido entre AppSidebar (el selector)
// y las vistas que necesitan reaccionar a un cambio (Inventario, Reposición,
// Ventas, Caja). El interceptor de axios en main.js lee la misma clave para
// mandar X-Sede-Id en cada request de endpoints operativos.
const CLAVE = 'ferreutil_sede_activa'
export const EVENTO_CAMBIO = 'ferreutil:sede-cambiada'

// Valor guardado: id numérico (string) de una sede, 'todas' (vista agregada,
// solo admin/puede_alternar_sedes), o null/ausente (sin elección explícita
// todavía — el backend resuelve la sede "home" del usuario por default).
export function obtenerSedeActiva() {
  return localStorage.getItem(CLAVE) || ''
}

// Para requests con sede_id como query param (reportes, dashboard, export,
// reposición): 'todas' o vacío = sin filtro (agregado, comportamiento actual).
export function sedeIdParaQuery() {
  const v = obtenerSedeActiva()
  return (v && v !== 'todas') ? v : ''
}

export function fijarSedeActiva(valor) {
  if (valor) {
    localStorage.setItem(CLAVE, String(valor))
  } else {
    localStorage.removeItem(CLAVE)
  }
  window.dispatchEvent(new CustomEvent(EVENTO_CAMBIO, { detail: { sede: valor } }))
}
