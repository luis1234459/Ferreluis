<template>
  <div class="layout">
    <AppSidebar />
    <main class="contenido">
      <div class="top-bar">
        <h1>Radar de Demanda</h1>
        <div class="top-acciones">
          <input v-model="fechaFiltro" type="date" class="input-fecha" @change="cargarDetalle" />
          <button class="btn-refrescar" @click="cargarTodo">↻ Actualizar</button>
        </div>
      </div>

      <div class="contenido-inner">

        <div class="resumen-grid" v-if="resumen.length > 0">
          <div v-for="item in resumen" :key="item.nombre_producto" class="resumen-card"
            :class="{ 'card-urgente': item.ventas_perdidas > 0, 'card-alerta': item.alertas_precio.length > 0 }">
            <div class="resumen-nombre">{{ item.nombre_producto }}</div>
            <div class="resumen-badges">
              <span v-if="item.ventas_perdidas > 0" class="badge-perdida">
                🔴 {{ item.ventas_perdidas }} venta(s) perdida(s) — {{ item.cantidad_perdida }} uds
              </span>
              <span v-if="item.consultas > 0" class="badge-consulta">
                🟡 {{ item.consultas }} consulta(s)
              </span>
              <span v-for="(a, i) in item.alertas_precio" :key="i" class="badge-alerta">
                💬 {{ a.competencia }}: ${{ a.precio }}
              </span>
            </div>
          </div>
        </div>
        <div v-else-if="!cargando" class="sin-datos">Sin registros para hoy.</div>

        <div class="tabla-container" v-if="detalle.length > 0" style="margin-top:1.5rem">
          <h2 class="seccion-titulo">Detalle del día</h2>
          <table>
            <thead>
              <tr>
                <th>Hora</th>
                <th>Tipo</th>
                <th>Producto</th>
                <th>Detalle</th>
                <th>Vendedor</th>
                <th>Visto</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in detalle" :key="r.id" :class="{ 'fila-no-vista': !r.visto_por_admin }">
                <td class="txt-muted">{{ formatHora(r.fecha) }}</td>
                <td>
                  <span :class="'badge-tipo badge-' + r.tipo">{{ labelTipo(r.tipo) }}</span>
                </td>
                <td class="prod-nombre">{{ r.nombre_producto }}</td>
                <td>
                  <span v-if="r.tipo === 'venta_perdida'">{{ r.cantidad }} uds</span>
                  <span v-else-if="r.tipo === 'alerta_precio'">
                    {{ r.competencia }} · ${{ r.precio_competencia }}
                    <span v-if="r.precio_sistema" class="diff-precio">
                      (sistema: ${{ r.precio_sistema?.toFixed(2) }})
                    </span>
                  </span>
                  <span v-else class="txt-muted">—</span>
                  <small v-if="r.observacion" class="observacion-text">{{ r.observacion }}</small>
                </td>
                <td class="txt-muted">{{ r.vendedor }}</td>
                <td>
                  <button v-if="!r.visto_por_admin" class="btn-marcar-visto" @click="marcarVisto(r)">
                    Marcar visto
                  </button>
                  <span v-else class="txt-muted">✓</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'RadarDemanda',
  data() {
    return {
      resumen:     [],
      detalle:     [],
      cargando:    false,
      fechaFiltro: new Date().toISOString().slice(0, 10),
    }
  },
  async mounted() {
    await this.cargarTodo()
  },
  methods: {
    async cargarTodo() {
      this.cargando = true
      await Promise.all([this.cargarResumen(), this.cargarDetalle()])
      this.cargando = false
    },
    async cargarResumen() {
      try {
        const { data } = await axios.get('/notificaciones/demanda/resumen')
        this.resumen = data
      } catch {}
    },
    async cargarDetalle() {
      try {
        const { data } = await axios.get('/notificaciones/demanda', {
          params: { fecha: this.fechaFiltro }
        })
        this.detalle = data
      } catch {}
    },
    async marcarVisto(r) {
      try {
        await axios.patch(`/notificaciones/demanda/${r.id}/visto`)
        r.visto_por_admin = true
      } catch {}
    },
    labelTipo(t) {
      return { venta_perdida: '🔴 Venta perdida', consulta: '🟡 Consulta', alerta_precio: '💬 Precio' }[t] || t
    },
    formatHora(f) {
      if (!f) return '—'
      return new Date(f).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' })
    },
  },
}
</script>

<style scoped>
.top-acciones { display: flex; gap: 0.75rem; align-items: center; }
.input-fecha { border: 1px solid var(--borde); border-radius: 6px; padding: 0.4rem 0.65rem; font-size: 0.875rem; color: var(--texto-principal); background: var(--fondo-app); }
.btn-refrescar { padding: 0.4rem 1rem; background: var(--borde-suave, #F1F1F1); border: 1px solid var(--borde); color: var(--texto-sec); border-radius: 8px; cursor: pointer; font-size: 0.88rem; }
.sin-datos { text-align: center; padding: 3rem; color: var(--texto-muted); }
.resumen-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; margin-bottom: 1rem; }
.resumen-card { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 12px; padding: 1rem 1.25rem; }
.card-urgente { border-color: #DC2626; background: #FEF2F2; }
.card-alerta  { border-color: #F59E0B; background: #FFFBEB; }
.resumen-nombre { font-weight: 700; font-size: 0.95rem; color: var(--texto-principal); margin-bottom: 0.5rem; }
.resumen-badges { display: flex; flex-direction: column; gap: 0.3rem; }
.badge-perdida { font-size: 0.82rem; color: #DC2626; font-weight: 600; }
.badge-consulta { font-size: 0.82rem; color: #D97706; font-weight: 600; }
.badge-alerta  { font-size: 0.82rem; color: #7C3AED; font-weight: 600; }
.seccion-titulo { font-size: 0.9rem; font-weight: 700; color: var(--texto-principal); margin: 0 0 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; }
.fila-no-vista { background: #FFFBEB; }
.txt-muted { color: var(--texto-muted); font-size: 0.85rem; }
.prod-nombre { font-weight: 600; }
.badge-tipo { font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600; white-space: nowrap; }
.badge-venta_perdida { background: #FEE2E2; color: #DC2626; }
.badge-consulta      { background: #FEF9C3; color: #854D0E; }
.badge-alerta_precio { background: #EDE9FE; color: #7C3AED; }
.diff-precio { color: var(--texto-muted); font-size: 0.78rem; margin-left: 0.3rem; }
.observacion-text { display: block; color: var(--texto-muted); font-size: 0.78rem; margin-top: 0.2rem; font-style: italic; }
.btn-marcar-visto { background: none; border: 1px solid var(--borde); border-radius: 5px; padding: 0.2rem 0.6rem; font-size: 0.75rem; cursor: pointer; color: var(--texto-sec); }
.btn-marcar-visto:hover { border-color: #FFCC00; }
</style>
