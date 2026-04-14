<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Mi Comisión</h1>
        <div class="top-acciones">
          <button class="btn-refrescar" @click="cargarDatos">↻ Actualizar</button>
        </div>
      </div>

      <div class="contenido-inner">

        <!-- Sin perfil de vendedor -->
        <div v-if="!cargando && !perfilId" class="sin-perfil">
          <p>No tienes perfil de vendedor configurado.</p>
          <p>Contacta al administrador para activar el seguimiento de comisiones.</p>
        </div>

        <template v-if="perfilId">

          <!-- ── KPIs ── -->
          <div class="kpis-comision">
            <div class="kpi-grande">
              <p class="kpi-etiqueta">Comisión ganada hoy</p>
              <p class="kpi-numero txt-verde">${{ resumen.comision_hoy?.toFixed(2) ?? '0.00' }}</p>
              <p class="kpi-sub">{{ resumen.cantidad_ventas_hoy ?? 0 }} venta(s) — ${{ resumen.ventas_usd_hoy?.toFixed(2) ?? '0.00' }} en ventas</p>
            </div>

            <div class="kpi-periodo" v-if="resumen.periodo_activo">
              <p class="kpi-etiqueta">Período actual</p>
              <p class="kpi-numero-sm txt-verde">${{ resumen.periodo_activo.total_comision?.toFixed(2) ?? '0.00' }}</p>
              <p class="kpi-sub">
                {{ formatFecha(resumen.periodo_activo.fecha_inicio) }} —
                {{ formatFecha(resumen.periodo_activo.fecha_fin) }}
              </p>
              <span :class="resumen.periodo_activo.estado === 'pagado' ? 'badge-pagado' : 'badge-pendiente'">
                {{ resumen.periodo_activo.estado === 'pagado' ? 'Pagado' : 'Pendiente' }}
              </span>
            </div>
            <div class="kpi-periodo" v-else>
              <p class="kpi-etiqueta">Período actual</p>
              <p class="kpi-sub" style="padding-top:0.5rem">Sin período activo definido</p>
            </div>
          </div>

          <!-- ── Tabla de ventas del día ── -->
          <div class="seccion-titulo">Ventas del día — detalle de comisiones</div>

          <div class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Hora</th>
                  <th>Venta #</th>
                  <th>Producto</th>
                  <th>Monto USD</th>
                  <th>% Comisión</th>
                  <th>Comisión</th>
                  <th>Regla</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="cargando">
                  <td colspan="7" class="sin-datos">Cargando...</td>
                </tr>
                <tr v-else-if="ventasHoy.length === 0">
                  <td colspan="7" class="sin-datos">Sin ventas registradas hoy</td>
                </tr>
                <tr v-for="v in ventasHoy" :key="v.id">
                  <td class="txt-muted">{{ formatHora(v.fecha) }}</td>
                  <td class="txt-muted">#{{ v.venta_id }}</td>
                  <td style="font-weight:600">{{ v.producto_nombre }}</td>
                  <td>${{ Number(v.monto_venta_usd).toFixed(2) }}</td>
                  <td class="txt-verde">{{ (v.porcentaje_aplicado * 100).toFixed(1) }}%</td>
                  <td class="txt-verde" style="font-weight:700">${{ Number(v.monto_comision).toFixed(2) }}</td>
                  <td>
                    <span class="badge-regla">{{ v.tipo_regla }}</span>
                  </td>
                </tr>
              </tbody>
              <tfoot v-if="ventasHoy.length > 0">
                <tr class="fila-total">
                  <td colspan="3" style="text-align:right;font-weight:700;color:var(--texto-sec)">Total del día</td>
                  <td style="font-weight:700">${{ totalVentasHoy.toFixed(2) }}</td>
                  <td></td>
                  <td class="txt-verde" style="font-weight:700">${{ totalComisionHoy.toFixed(2) }}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>

        </template>

      </div><!-- /contenido-inner -->
    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'MiComision',
  data() {
    return {
      usuario:   JSON.parse(localStorage.getItem('usuario') || '{}'),
      cargando:  true,
      perfilId:  null,
      resumen:   {},
      ventasHoy: [],
    }
  },

  computed: {
    esAdmin() { return this.usuario.rol === 'admin' },
    tienePermiso() {
      return (modulo) => {
        if (this.usuario.rol === 'admin') return true
        const p = this.usuario.permisos
        if (p == null) return true
        return Array.isArray(p) ? p.includes(modulo) : true
      }
    },
    totalVentasHoy()  { return this.ventasHoy.reduce((s, v) => s + Number(v.monto_venta_usd), 0) },
    totalComisionHoy(){ return this.ventasHoy.reduce((s, v) => s + Number(v.monto_comision),  0) },
  },

  async mounted() {
    await this.cargarDatos()
  },

  methods: {
    async cargarDatos() {
      this.cargando = true
      try {
        // Buscar el perfil del usuario actual
        const headers = { 'X-Usuario-Rol': this.usuario.rol || '' }
        const res = await axios.get('/vendedores/', { headers })
        const nombre = this.usuario.usuario || ''
        const perfil = res.data.find(v => v.usuario_nombre === nombre)
        if (!perfil) { this.perfilId = null; return }
        this.perfilId = perfil.id

        const [resumenRes, ventasRes] = await Promise.all([
          axios.get(`/vendedores/${perfil.id}/resumen`),
          axios.get(`/vendedores/${perfil.id}/ventas-hoy`),
        ])
        this.resumen   = resumenRes.data
        this.ventasHoy = ventasRes.data
      } catch {
        this.perfilId = null
      } finally {
        this.cargando = false
      }
    },

    formatFecha(s) {
      if (!s) return '—'
      return new Date(s + 'T00:00:00').toLocaleDateString('es-VE')
    },
    formatHora(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' })
    },

    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    },
  },
}
</script>

<style scoped>
/* ── Top bar ── */
.top-acciones { display: flex; gap: 0.6rem; align-items: center; }
.btn-refrescar { padding: 0.4rem 1rem; background: var(--borde-suave); border: 1px solid var(--borde); color: var(--texto-sec); border-radius: 8px; cursor: pointer; font-size: 0.88rem; }
.btn-refrescar:hover { background: var(--borde); color: var(--texto-principal); }

/* ── Sin perfil ── */
.sin-perfil { background: var(--borde-suave); border: 1px dashed var(--borde); border-radius: 12px; padding: 2.5rem; text-align: center; color: var(--texto-sec); }
.sin-perfil p { margin: 0.3rem 0; }

/* ── KPIs comisión ── */
.kpis-comision { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 1.75rem; }
.kpi-grande, .kpi-periodo {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 1.5rem 1.75rem;
  border: 1px solid var(--borde);
}
.kpi-etiqueta  { color: var(--texto-muted); font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 0.6rem; }
.kpi-numero    { font-size: 2.5rem; font-weight: 800; margin: 0 0 0.4rem; line-height: 1; }
.kpi-numero-sm { font-size: 1.75rem; font-weight: 800; margin: 0 0 0.4rem; line-height: 1; }
.kpi-sub       { color: var(--texto-sec); font-size: 0.85rem; margin: 0 0 0.6rem; }

/* ── Badges período ── */
.badge-pagado   { background: #16A34A1A; color: #16A34A; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 10px; }
.badge-pendiente{ background: #F59E0B1A; color: #92400E; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 10px; }
.badge-regla    { background: #1A1A1A1A; color: #1A1A1A; font-size: 0.75rem; font-weight: 600; padding: 0.15rem 0.5rem; border-radius: 8px; text-transform: capitalize; }

/* ── Textos ── */
.txt-muted { color: var(--texto-muted); }
.txt-verde { color: #16A34A; font-weight: 600; }

/* ── Sección título ── */
.seccion-titulo { color: var(--texto-muted); font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem; }

/* ── Tabla total ── */
.fila-total td { border-top: 2px solid var(--borde); background: var(--borde-suave); padding: 0.5rem 0.75rem; }
</style>
