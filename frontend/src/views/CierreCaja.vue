<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Cierre de caja</h1>
      </div>

      <div class="contenido-inner">
        <div v-if="cargando" class="msg-info">Cargando resumen...</div>

        <div v-else-if="resumen && resumen.cantidad_ventas === 0" class="sin-ventas">
          No hay ventas pendientes de cierre.
        </div>

        <div v-else-if="resumen">
          <!-- Encabezado del período -->
          <div class="periodo-card">
            <div class="periodo-item">
              <span class="periodo-label">Período desde</span>
              <span class="periodo-valor">{{ resumen.desde ? formatFecha(resumen.desde) : 'Inicio del sistema' }}</span>
            </div>
            <div class="periodo-item">
              <span class="periodo-label">Hasta</span>
              <span class="periodo-valor">{{ formatFecha(resumen.hasta) }}</span>
            </div>
            <div class="periodo-item">
              <span class="periodo-label">Total ventas</span>
              <span class="periodo-valor highlight">{{ resumen.cantidad_ventas }} ventas — ${{ resumen.total_usd.toFixed(2) }}</span>
            </div>
          </div>

          <!-- Comisiones del día -->
          <div class="comision-card" v-if="!esAdmin && (resumen.comision_hoy > 0 || resumen.comision_periodo > 0)">
            <div class="comision-header">
              <span class="comision-titulo">💰 Tus comisiones</span>
            </div>
            <div class="comision-body">
              <div class="comision-fila grande">
                <span>Comisión generada hoy</span>
                <span class="comision-monto-grande">${{ (resumen.comision_hoy || 0).toFixed(2) }}</span>
              </div>
              <div class="comision-fila">
                <span>Acumulado del período</span>
                <span class="comision-monto">${{ (resumen.comision_periodo || 0).toFixed(2) }}</span>
              </div>
            </div>
          </div>

          <!-- Tabla de formas de pago -->
          <div class="tabla-cierre tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Método de pago</th>
                  <th>Sistema registró</th>
                  <th>Cajero contó</th>
                  <th>Diferencia</th>
                </tr>
              </thead>
              <tbody>
                <!-- USD -->
                <tr class="seccion-header">
                  <td colspan="4">Pagos en dólares (USD)</td>
                </tr>
                <tr v-for="m in metodosUsd" :key="m.key">
                  <td class="metodo-nombre">{{ m.label }}</td>
                  <td class="monto-sistema">${{ (resumen.totales[m.key] || 0).toFixed(2) }}</td>
                  <td>
                    <input
                      v-model.number="contados[m.key]"
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      class="input-contado"
                      :disabled="(resumen.totales[m.key] || 0) === 0"
                    />
                  </td>
                  <td :class="claseDiferencia(m.key, 'usd')">
                    {{ diferencia(m.key, 'usd') }}
                  </td>
                </tr>

                <!-- Bs -->
                <tr class="seccion-header">
                  <td colspan="4">Pagos en bolívares (Bs)</td>
                </tr>
                <tr v-for="m in metodosBs" :key="m.key">
                  <td class="metodo-nombre">{{ m.label }}</td>
                  <td class="monto-sistema">Bs. {{ (resumen.totales[m.key] || 0).toFixed(2) }}</td>
                  <td>
                    <input
                      v-model.number="contados[m.key]"
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      class="input-contado"
                      :disabled="(resumen.totales[m.key] || 0) === 0"
                    />
                  </td>
                  <td :class="claseDiferencia(m.key, 'bs')">
                    {{ diferencia(m.key, 'bs') }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Devoluciones del período -->
          <div class="devoluciones-card" v-if="resumen.devoluciones && resumen.devoluciones.cantidad > 0">
            <div class="devoluciones-header">
              <span class="devoluciones-titulo">⚠ Devoluciones del período</span>
              <span class="devoluciones-cantidad">{{ resumen.devoluciones.cantidad }} devolución(es)</span>
            </div>
            <div class="devoluciones-body">
              <div class="dev-fila">
                <span>Total devuelto (egreso):</span>
                <span class="dev-monto">${{ (resumen.devoluciones.total_usd || 0).toFixed(2) }}</span>
              </div>
              <div class="dev-fila" v-for="(monto, moneda) in resumen.devoluciones.por_moneda" :key="moneda">
                <span>Devuelto en {{ moneda }}:</span>
                <span class="dev-monto">{{ moneda === 'USD' ? '$' : 'Bs.' }} {{ monto.toFixed(2) }}</span>
              </div>
              <div class="dev-fila dev-neto">
                <span>Neto del período (ventas − devoluciones):</span>
                <span class="dev-monto-neto">${{ Math.max((resumen.total_usd || 0) - (resumen.devoluciones.total_usd || 0), 0).toFixed(2) }}</span>
              </div>
            </div>
            <div v-if="resumen.devoluciones.detalle && resumen.devoluciones.detalle.length > 0" style="margin-top:0.75rem;">
              <p style="font-size:0.82rem;font-weight:700;color:#92400E;margin:0 0 0.5rem;">Detalle por devolución:</p>
              <table class="tabla-dev-detalle">
                <thead>
                  <tr>
                    <th>Hora</th>
                    <th>Cliente</th>
                    <th>Producto(s)</th>
                    <th>Tipo</th>
                    <th>Monto</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(d, i) in resumen.devoluciones.detalle" :key="i">
                    <td>{{ formatHora(d.fecha) }}</td>
                    <td>{{ d.cliente }}</td>
                    <td>
                      <span v-for="(p, j) in d.productos" :key="j">
                        {{ p.nombre }} x{{ p.cantidad }}<br v-if="j < d.productos.length - 1"/>
                      </span>
                    </td>
                    <td>{{ d.tipo }}</td>
                    <td class="txt-rojo">
                      {{ d.moneda === 'USD' ? '$' : 'Bs.' }}{{ Number(d.monto).toFixed(2) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Observación y cierre -->
          <div class="cierre-footer">
            <div class="field">
              <label>Observación</label>
              <input v-model="observacion" placeholder="Novedades del turno..." />
            </div>
            <button class="btn-cerrar" @click="cerrarCaja" :disabled="cerrando">
              {{ cerrando ? 'Cerrando...' : 'Cerrar caja' }}
            </button>
          </div>

          <p class="msg-exito" v-if="exitoso">¡Caja cerrada correctamente! Cierre #{{ cierreId }}</p>
          <p class="msg-error" v-if="error">{{ error }}</p>
        </div>

        <!-- Historial -->
        <div class="historial" v-if="historial.length > 0">
          <h2 class="seccion-titulo">Historial de cierres</h2>
          <div class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Fecha</th>
                  <th>Usuario</th>
                  <th>Ventas</th>
                  <th>Total USD</th>
                  <th>Estado</th>
                  <th v-if="esAdmin"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in historial" :key="c.id">
                  <td>#{{ c.id }}</td>
                  <td>{{ formatFecha(c.fecha) }}</td>
                  <td>{{ c.usuario }}</td>
                  <td>{{ c.cantidad_ventas }}</td>
                  <td>${{ (c.total_ventas_usd || 0).toFixed(2) }}</td>
                  <td>
                    <span :class="'badge badge-' + (c.estado_revision || 'pendiente')">
                      {{ c.estado_revision === 'aprobado' ? '✓ Aprobado'
                       : c.estado_revision === 'con_diferencias' ? '⚠ Diferencias'
                       : 'Pendiente' }}
                    </span>
                  </td>
                  <td v-if="esAdmin">
                    <button
                      v-if="c.estado_revision === 'pendiente'"
                      class="btn-aprobar-cierre"
                      @click="aprobarCierre(c.id)"
                      :disabled="aprobando === c.id"
                    >
                      {{ aprobando === c.id ? '...' : '✓ Aprobar' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
  name: 'CierreCaja',
  data() {
    return {
      usuario: JSON.parse(localStorage.getItem('usuario') || '{}'),
      resumen: null,
      historial: [],
      cargando: true,
      cerrando: false,
      exitoso: false,
      cierreId: null,
      error: '',
      aprobando: null,
      observacion: '',
      contados: {
        efectivo_usd: '',
        zelle: '',
        binance: '',
        efectivo_bs: '',
        transferencia_bs: '',
        pago_movil: '',
        punto_banesco: '',
        punto_provincial: '',
      },
      metodosUsd: [
        { key: 'efectivo_usd', label: 'Efectivo $' },
        { key: 'zelle', label: 'Zelle' },
        { key: 'binance', label: 'Binance' },
      ],
      metodosBs: [
        { key: 'efectivo_bs', label: 'Efectivo Bs' },
        { key: 'transferencia_bs', label: 'Transferencia Bs' },
        { key: 'pago_movil', label: 'Pago Móvil' },
        { key: 'punto_banesco', label: 'Punto Banesco' },
        { key: 'punto_provincial', label: 'Punto Provincial' },
      ],
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
  },
  async mounted() {
    await Promise.all([this.cargarResumen(), this.cargarHistorial()])
    this.cargando = false
  },
  methods: {
    async cargarResumen() {
      const nombre = this.usuario.usuario || ''
      const params = this.esAdmin ? {} : { usuario: nombre }
      const res = await axios.get('/cierres/resumen', { params })
      this.resumen = res.data
    },
    async cargarHistorial() {
      const nombre = this.usuario.usuario || ''
      const params = this.esAdmin ? {} : { usuario: nombre }
      const res = await axios.get('/cierres/', { params })
      this.historial = res.data
    },
    diferencia(key, moneda) {
      const esperado = this.resumen?.totales?.[key] || 0
      const contado = Number(this.contados[key] || 0)
      const diff = contado - esperado
      const prefix = moneda === 'usd' ? '$' : 'Bs.'
      if (esperado === 0 && contado === 0) return '—'
      return `${diff >= 0 ? '+' : ''}${prefix}${diff.toFixed(2)}`
    },
    claseDiferencia(key, moneda) {
      const esperado = this.resumen?.totales?.[key] || 0
      const contado = Number(this.contados[key] || 0)
      if (esperado === 0 && contado === 0) return 'diff-neutro'
      const diff = contado - esperado
      if (Math.abs(diff) < 0.01) return 'diff-ok'
      return diff > 0 ? 'diff-sobre' : 'diff-faltan'
    },
    async cerrarCaja() {
      this.error = ''
      this.cerrando = true
      try {
        const res = await axios.post('/cierres/', {
          usuario: this.usuario.usuario || '',
          observacion: this.observacion,
          contados: this.contados,
        })
        this.cierreId = res.data.cierre_id
        this.exitoso = true
        this.observacion = ''
        Object.keys(this.contados).forEach(k => this.contados[k] = '')
        await Promise.all([this.cargarResumen(), this.cargarHistorial()])
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al cerrar la caja'
      } finally {
        this.cerrando = false
      }
    },
    formatFecha(iso) {
      if (!iso) return ''
      return new Date(iso).toLocaleString('es-VE')
    },
    formatHora(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' })
    },
    async aprobarCierre(id) {
      if (!confirm('¿Aprobar este cierre?')) return
      this.aprobando = id
      try {
        await axios.put(`/cierres/${id}/revisar`, {
          estado_revision: 'aprobado',
          revisado_por: this.usuario.usuario || 'admin',
        })
        await this.cargarHistorial()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al aprobar')
      } finally {
        this.aprobando = null
      }
    },
    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    }
  }
}
</script>

<style scoped>
.sin-ventas {
  background: #FFFFFF; padding: 2rem; border-radius: 12px;
  color: var(--texto-sec); text-align: center; font-size: 1.1rem;
  border: 1px solid var(--borde);
}

.periodo-card {
  display: flex; gap: 2rem; background: #FFFFFF;
  padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;
  flex-wrap: wrap; border: 1px solid var(--borde);
}
.periodo-item { display: flex; flex-direction: column; gap: 0.25rem; }
.periodo-label { color: var(--texto-muted); font-size: 0.82rem; }
.periodo-valor { color: var(--texto-principal); font-weight: 600; }
.highlight { color: #16A34A; font-size: 1.05rem; font-weight: 700; }

.seccion-header td {
  background: #FFCC0022; color: var(--texto-sec);
  font-size: 0.82rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em;
  padding: 0.4rem 1rem;
}

.metodo-nombre { font-weight: 600; }
.monto-sistema { color: #16A34A; font-weight: 600; }

.input-contado {
  width: 130px; padding: 0.4rem 0.6rem;
  background: #FFFFFF; border: 1px solid #CCCCCC;
  color: var(--texto-principal); border-radius: 6px; font-size: 0.9rem;
}
.input-contado:disabled { opacity: 0.35; cursor: not-allowed; }

.diff-neutro { color: var(--texto-muted); }
.diff-ok { color: #16A34A; font-weight: 600; }
.diff-sobre { color: #996600; font-weight: 600; }
.diff-faltan { color: #DC2626; font-weight: 700; }

.cierre-footer { display: flex; gap: 1rem; align-items: flex-end; margin: 1.5rem 0 1rem; }
.cierre-footer .field { flex: 1; }

.btn-cerrar {
  padding: 0.7rem 2rem; background: #1A1A1A; color: #FFCC00;
  border: none; border-radius: 8px; cursor: pointer; font-size: 1rem;
  white-space: nowrap; font-weight: 700;
}
.btn-cerrar:disabled { opacity: 0.5; cursor: not-allowed; }

.historial { margin-top: 2rem; }
.seccion-titulo { color: var(--texto-principal); font-size: 1.05rem; font-weight: 700; margin: 0 0 1rem; }

.devoluciones-card {
  background: #FFF7ED; border: 1px solid #F59E0B;
  border-radius: 12px; padding: 1rem 1.25rem;
  margin-bottom: 1.5rem;
}
.devoluciones-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 0.75rem;
}
.devoluciones-titulo { font-weight: 700; color: #92400E; font-size: 0.95rem; }
.devoluciones-cantidad { color: #92400E; font-size: 0.85rem; }
.devoluciones-body { display: flex; flex-direction: column; gap: 0.3rem; }
.dev-fila { display: flex; justify-content: space-between; font-size: 0.9rem; color: var(--texto-sec); }
.dev-monto { color: #DC2626; font-weight: 600; }
.dev-neto { border-top: 1px solid #F59E0B; padding-top: 0.5rem; margin-top: 0.25rem; }
.dev-monto-neto { color: #16A34A; font-weight: 700; font-size: 1rem; }

.tabla-dev-detalle { width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-top: 0.5rem; }
.tabla-dev-detalle th { background: #F59E0B22; color: #92400E; padding: 0.35rem 0.6rem; text-align: left; font-weight: 700; font-size: 0.78rem; }
.tabla-dev-detalle td { padding: 0.35rem 0.6rem; border-bottom: 1px solid #F59E0B33; color: var(--texto-principal); vertical-align: top; }
.txt-rojo { color: #DC2626; font-weight: 600; }

.comision-card {
  background: linear-gradient(135deg, #1A1A1A 0%, #2D2D2D 100%);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
  border: 1px solid #FFCC0044;
}
.comision-header { margin-bottom: 0.75rem; }
.comision-titulo { color: #FFCC00; font-weight: 700; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em; }
.comision-body { display: flex; flex-direction: column; gap: 0.5rem; }
.comision-fila { display: flex; justify-content: space-between; align-items: center; color: #CCCCCC; font-size: 0.9rem; }
.comision-fila.grande { font-size: 1rem; font-weight: 600; color: #FFFFFF; }
.comision-monto-grande { color: #FFCC00; font-size: 1.75rem; font-weight: 800; line-height: 1; }
.comision-monto { color: #16A34A; font-weight: 700; font-size: 1rem; }

.badge-aprobado        { background:#DCFCE7; color:#16A34A; font-size:0.75rem; padding:0.15rem 0.45rem; border-radius:4px; font-weight:700; }
.badge-con_diferencias { background:#FEF3C7; color:#92400E; font-size:0.75rem; padding:0.15rem 0.45rem; border-radius:4px; font-weight:700; }
.badge-pendiente       { background:#F1F5F9; color:#64748B; font-size:0.75rem; padding:0.15rem 0.45rem; border-radius:4px; font-weight:700; }

.btn-aprobar-cierre { background:#16A34A; color:white; border:none; padding:0.3rem 0.75rem; border-radius:6px; cursor:pointer; font-size:0.8rem; font-weight:700; }
.btn-aprobar-cierre:disabled { opacity:0.5; cursor:not-allowed; }
.btn-aprobar-cierre:hover:not(:disabled) { background:#15803D; }
</style>
