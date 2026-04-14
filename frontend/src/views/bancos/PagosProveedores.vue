<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Pagos a Proveedores</h1>
      </div>

      <div class="contenido-inner">
        <!-- Tabla de deuda -->
        <div class="tabla-container">
          <table>
            <thead>
              <tr><th>Proveedor</th><th>Total comprado</th><th>Total pagado</th><th>Saldo pendiente</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="p in deuda" :key="p.proveedor_id"
                :class="{ 'sin-deuda': p.saldo_pendiente <= 0 }">
                <td style="font-weight:600">{{ p.proveedor }}</td>
                <td>${{ p.total_comprado.toFixed(2) }}</td>
                <td class="txt-verde">${{ p.total_pagado.toFixed(2) }}</td>
                <td :class="p.saldo_pendiente > 0 ? 'txt-rojo' : 'txt-verde'">
                  ${{ p.saldo_pendiente.toFixed(2) }}
                </td>
                <td>
                  <button class="btn-pagar" @click="abrirPago(p)" :disabled="p.saldo_pendiente <= 0">
                    Registrar pago
                  </button>
                  <button class="btn-historial" @click="verHistorial(p.proveedor_id)">Historial</button>
                </td>
              </tr>
              <tr v-if="deuda.length === 0">
                <td colspan="5" class="sin-datos">Sin deuda con proveedores</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Modal pago -->
        <div class="overlay" v-if="proveedorPago" @click.self="cerrarPago">
          <div class="modal">
            <div class="modal-header">
              <h2>Pago a {{ proveedorPago.proveedor }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarPago">✕</button>
            </div>
            <p class="deuda-info">Saldo pendiente: <strong class="txt-rojo">${{ proveedorPago.saldo_pendiente.toFixed(2) }}</strong></p>
            <div class="form-grid">
              <div class="field">
                <label>Cuenta bancaria origen</label>
                <select v-model="formPago.cuenta_id">
                  <option value="">— Seleccionar cuenta USD —</option>
                  <option v-for="c in cuentasUSD" :key="c.id" :value="c.id">
                    {{ c.nombre }} (${{ c.saldo.toFixed(2) }})
                  </option>
                </select>
              </div>
              <div class="field">
                <label>Monto a pagar</label>
                <input v-model.number="formPago.monto" type="number" min="0" step="0.01"
                  :placeholder="'Máx. $' + proveedorPago.saldo_pendiente.toFixed(2)" />
              </div>
              <div class="field">
                <label>Referencia bancaria</label>
                <input v-model="formPago.referencia" placeholder="Nro. operación" />
              </div>
              <div class="field">
                <label>Orden de compra (opcional)</label>
                <select v-model="formPago.orden_compra_id">
                  <option value="">— Sin asociar —</option>
                  <option v-for="o in ordenesProveedor" :key="o.id" :value="o.id">
                    {{ o.numero }} (${{ o.total.toFixed ? o.total.toFixed(2) : o.total }})
                  </option>
                </select>
              </div>
            </div>
            <div class="form-botones">
              <button class="btn-cancelar" @click="cerrarPago">Cancelar</button>
              <button class="btn-confirmar" @click="confirmarPago" :disabled="pagando">
                {{ pagando ? 'Procesando...' : 'Confirmar pago' }}
              </button>
            </div>
            <p class="msg-error" v-if="errorPago">{{ errorPago }}</p>
          </div>
        </div>

        <!-- Modal historial -->
        <div class="overlay" v-if="historial" @click.self="historial = null">
          <div class="modal">
            <div class="modal-header">
              <h2>Historial — {{ historial.proveedor }}</h2>
              <button class="btn-cerrar-modal" @click="historial = null">✕</button>
            </div>
            <div class="resumen-hist">
              <span>Comprado: <strong>${{ historial.total_comprado.toFixed(2) }}</strong></span>
              <span>Pagado: <strong class="txt-verde">${{ historial.total_pagado.toFixed(2) }}</strong></span>
              <span>Pendiente: <strong class="txt-rojo">${{ historial.saldo_pendiente.toFixed(2) }}</strong></span>
            </div>
            <h3 class="subtitulo-hist">Órdenes de compra</h3>
            <table>
              <thead><tr><th>Número</th><th>Estado</th><th>Total</th></tr></thead>
              <tbody>
                <tr v-for="o in historial.ordenes" :key="o.id">
                  <td>{{ o.numero }}</td>
                  <td><span :class="'badge badge-' + o.estado">{{ o.estado }}</span></td>
                  <td>${{ Number(o.total).toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
            <h3 class="subtitulo-hist">Pagos realizados</h3>
            <table>
              <thead><tr><th>Fecha</th><th>Monto</th><th>Referencia</th></tr></thead>
              <tbody>
                <tr v-for="p in historial.pagos" :key="p.id">
                  <td>{{ formatFecha(p.fecha) }}</td>
                  <td class="txt-verde">${{ p.monto.toFixed(2) }}</td>
                  <td>{{ p.referencia || '—' }}</td>
                </tr>
                <tr v-if="historial.pagos.length === 0">
                  <td colspan="3" class="sin-datos">Sin pagos registrados</td>
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
import AppSidebar from '../../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'PagosProveedores',
  data() {
    return {
      usuario:          JSON.parse(localStorage.getItem('usuario') || '{}'),
      deuda:            [],
      cuentas:          [],
      proveedorPago:    null,
      ordenesProveedor: [],
      historial:        null,
      pagando:          false,
      errorPago:        '',
      formPago: { cuenta_id: '', monto: '', referencia: '', orden_compra_id: '' },
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
    cuentasUSD() { return this.cuentas.filter(c => c.moneda === 'USD') },
  },
  async mounted() {
    await Promise.all([this.cargar(), this.cargarCuentas()])
  },
  methods: {
    async cargar() {
      const res = await axios.get('/bancos/proveedores/deuda/')
      this.deuda = res.data
    },
    async cargarCuentas() {
      const res = await axios.get('/bancos/cuentas/')
      this.cuentas = res.data
    },
    async abrirPago(p) {
      this.proveedorPago    = p
      this.errorPago        = ''
      this.formPago         = { cuenta_id: '', monto: '', referencia: '', orden_compra_id: '' }
      const res             = await axios.get(`/bancos/proveedores/${p.proveedor_id}/estado/`)
      this.ordenesProveedor = res.data.ordenes.filter(o => ['recibida_parcial','cerrada'].includes(o.estado))
    },
    cerrarPago() { this.proveedorPago = null },
    async confirmarPago() {
      if (!this.formPago.cuenta_id) { this.errorPago = 'Selecciona la cuenta bancaria'; return }
      if (!this.formPago.monto || this.formPago.monto <= 0) { this.errorPago = 'Ingresa un monto válido'; return }
      this.pagando = true; this.errorPago = ''
      try {
        await axios.post(`/bancos/proveedores/${this.proveedorPago.proveedor_id}/pago/`, {
          ...this.formPago,
          moneda:        'USD',
          orden_compra_id: this.formPago.orden_compra_id || null,
          registrado_por:  this.usuario.usuario || 'admin',
        })
        await Promise.all([this.cargar(), this.cargarCuentas()])
        this.cerrarPago()
      } catch (e) {
        this.errorPago = e?.response?.data?.detail || 'Error al registrar el pago'
      } finally { this.pagando = false }
    },
    async verHistorial(proveedorId) {
      const res = await axios.get(`/bancos/proveedores/${proveedorId}/estado/`)
      this.historial = res.data
    },
    formatFecha(iso) { return iso ? new Date(iso).toLocaleDateString('es-VE') : '—' },
    salir() { localStorage.removeItem('usuario'); this.$router.push('/login') },
  },
}
</script>

<style scoped>
.sin-deuda td { opacity: 0.45; }
.btn-pagar    { background: var(--success); color: white; border: none; padding: 0.3rem 0.7rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; margin-right: 0.3rem; }
.btn-pagar:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-historial{ background: var(--fondo-sidebar); color: var(--texto-sec); border: 1px solid var(--borde); padding: 0.3rem 0.7rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; }

.deuda-info { color: var(--texto-sec); font-size: 0.9rem; margin-bottom: 1rem; }
.btn-confirmar { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-confirmar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; }

.resumen-hist { display: flex; gap: 2rem; background: var(--borde-suave); padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem; flex-wrap: wrap; border: 1px solid var(--borde); }
.resumen-hist span { color: var(--texto-sec); font-size: 0.9rem; }
.resumen-hist strong { color: var(--texto-principal); }
.subtitulo-hist { color: var(--texto-principal); font-size: 0.85rem; margin: 1rem 0 0.5rem; font-weight: 700; }

.badge-aprobada { background: #16A34A1A; color: #16A34A; }
.badge-cerrada  { background: #8888881A; color: #555555; }
.badge-recibida_parcial { background: #FFCC0033; color: #996600; }
</style>
