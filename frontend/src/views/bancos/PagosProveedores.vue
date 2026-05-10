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
              <!-- Selector moneda -->
              <div class="field field-wide">
                <label>Moneda del pago</label>
                <div class="moneda-toggle">
                  <button
                    :class="['btn-moneda', formPago.moneda === 'USD' ? 'activo' : '']"
                    @click="formPago.moneda = 'USD'; formPago.cuenta_id = ''; formPago.tasa_cambio = ''"
                    type="button"
                  >💵 USD</button>
                  <button
                    :class="['btn-moneda', formPago.moneda === 'Bs' ? 'activo' : '']"
                    @click="formPago.moneda = 'Bs'; formPago.cuenta_id = ''"
                    type="button"
                  >🇻🇪 Bolívares</button>
                </div>
              </div>

              <!-- Tasa manual (solo Bs) -->
              <div class="field" v-if="formPago.moneda === 'Bs'">
                <label>Tasa de cambio del día del pago (Bs por $1)</label>
                <input
                  v-model.number="formPago.tasa_cambio"
                  type="number" min="0" step="0.01"
                  placeholder="Ej: 92.50"
                />
                <span class="field-hint">
                  Ingresa la tasa BCV o acordada del día que se realizó el pago
                </span>
              </div>

              <!-- Cuenta bancaria -->
              <div class="field">
                <label>Cuenta bancaria origen</label>
                <select v-model="formPago.cuenta_id">
                  <option value="">— Seleccionar cuenta {{ formPago.moneda }} —</option>
                  <option v-for="c in cuentasDisponibles" :key="c.id" :value="c.id">
                    {{ c.nombre }}
                    ({{ c.moneda === 'USD' ? '$' : 'Bs.' }}{{ c.saldo.toFixed(2) }})
                  </option>
                </select>
                <span v-if="cuentasDisponibles.length === 0" class="aviso-sin-cuentas">
                  ⚠ No hay cuentas en {{ formPago.moneda }} disponibles
                </span>
              </div>

              <!-- Monto -->
              <div class="field">
                <label>Monto a pagar ({{ formPago.moneda }})</label>
                <input
                  v-model.number="formPago.monto"
                  type="number" min="0" step="0.01"
                  :placeholder="formPago.moneda === 'USD'
                    ? 'Máx. $' + proveedorPago.saldo_pendiente.toFixed(2)
                    : 'Monto en Bs'"
                />
                <span v-if="formPago.moneda === 'Bs' && montoUSDEquivalente" class="equiv-usd">
                  ≈ ${{ montoUSDEquivalente }} USD
                  <span
                    v-if="parseFloat(montoUSDEquivalente) > proveedorPago.saldo_pendiente"
                    class="aviso-exceso"
                  > ⚠ Excede la deuda</span>
                </span>
              </div>

              <!-- Referencia -->
              <div class="field">
                <label>Referencia bancaria</label>
                <input v-model="formPago.referencia" placeholder="Nro. operación" />
              </div>

              <!-- Orden de compra -->
              <div class="field">
                <label>Orden de compra (opcional)</label>
                <select v-model="formPago.orden_compra_id">
                  <option value="">— Sin asociar —</option>
                  <option v-for="o in ordenesProveedor" :key="o.id" :value="o.id">
                    {{ o.numero }}
                    (${{ o.total.toFixed ? o.total.toFixed(2) : o.total }})
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
                  <td class="txt-verde">
                    {{ p.moneda === 'Bs' ? 'Bs.' : '$' }}{{ p.monto.toFixed(2) }}
                    <span v-if="p.moneda === 'Bs' && p.monto_convertido" class="equiv-hist">
                      ≈ ${{ Number(p.monto_convertido).toFixed(2) }}
                    </span>
                    <span v-if="p.moneda === 'Bs' && p.tasa_cambio" class="tasa-hist">
                      @{{ p.tasa_cambio }}
                    </span>
                  </td>
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
      formPago: {
        cuenta_id:       '',
        monto:           '',
        referencia:      '',
        orden_compra_id: '',
        moneda:          'USD',
        tasa_cambio:     '',
      },
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
    cuentasBs() { return this.cuentas.filter(c => c.moneda === 'Bs') },
    cuentasDisponibles() {
      return this.formPago.moneda === 'USD' ? this.cuentasUSD : this.cuentasBs
    },
    montoUSDEquivalente() {
      if (this.formPago.moneda === 'USD') return this.formPago.monto
      const tasa = parseFloat(this.formPago.tasa_cambio)
      if (!tasa || tasa <= 0 || !this.formPago.monto) return null
      return (parseFloat(this.formPago.monto) / tasa).toFixed(2)
    },
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
      this.formPago         = { cuenta_id: '', monto: '', referencia: '', orden_compra_id: '', moneda: 'USD', tasa_cambio: '' }
      const res             = await axios.get(`/bancos/proveedores/${p.proveedor_id}/estado/`)
      this.ordenesProveedor = res.data.ordenes.filter(o => ['recibida_parcial','cerrada'].includes(o.estado))
    },
    cerrarPago() {
      this.proveedorPago = null
      this.formPago = { cuenta_id: '', monto: '', referencia: '', orden_compra_id: '', moneda: 'USD', tasa_cambio: '' }
    },
    async confirmarPago() {
      if (!this.formPago.cuenta_id) { this.errorPago = 'Selecciona la cuenta bancaria'; return }
      if (!this.formPago.monto || this.formPago.monto <= 0) { this.errorPago = 'Ingresa un monto válido'; return }
      if (this.formPago.moneda === 'Bs' && !this.formPago.tasa_cambio) {
        this.errorPago = 'Ingresa la tasa de cambio para pagos en Bs'; return
      }
      this.pagando = true; this.errorPago = ''
      try {
        await axios.post(
          `/bancos/proveedores/${this.proveedorPago.proveedor_id}/pago/`,
          {
            cuenta_id:       this.formPago.cuenta_id,
            monto:           this.formPago.monto,
            moneda:          this.formPago.moneda,
            tasa_cambio:     this.formPago.moneda === 'Bs' ? this.formPago.tasa_cambio : null,
            referencia:      this.formPago.referencia,
            orden_compra_id: this.formPago.orden_compra_id || null,
            registrado_por:  this.usuario.usuario || 'admin',
          }
        )
        await Promise.all([this.cargar(), this.cargarCuentas()])
        this.cerrarPago()
      } catch (e) {
        this.errorPago = e?.response?.data?.detail || 'Error al registrar el pago'
      } finally {
        this.pagando = false
      }
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

.moneda-toggle { display: flex; gap: 0.5rem; }
.btn-moneda {
  flex: 1; padding: 0.5rem; border-radius: 6px; cursor: pointer;
  border: 2px solid var(--borde); background: white;
  font-weight: 600; font-size: 0.85rem; transition: all 0.15s;
}
.btn-moneda.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }
.field-hint { font-size: 0.72rem; color: var(--texto-muted); display: block; margin-top: 0.25rem; }
.equiv-usd { display: block; margin-top: 0.3rem; font-size: 0.82rem; color: #16A34A; font-weight: 600; }
.aviso-exceso { color: #DC2626; font-size: 0.78rem; }
.aviso-sin-cuentas { display: block; margin-top: 0.25rem; font-size: 0.78rem; color: #DC2626; font-weight: 600; }
.equiv-hist { font-size: 0.75rem; color: #16A34A; margin-left: 0.3rem; }
.tasa-hist { font-size: 0.72rem; color: var(--texto-muted); margin-left: 0.3rem; }
</style>
