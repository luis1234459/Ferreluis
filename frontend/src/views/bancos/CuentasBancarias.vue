<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Cuentas y Saldos</h1>
        <button class="btn-nuevo" @click="abrirNueva">+ Nueva cuenta</button>
      </div>

      <div class="contenido-inner">
        <!-- KPIs -->
        <div class="kpis" v-if="resumen">
          <div class="kpi-card">
            <p class="kpi-label">Total USD</p>
            <p class="kpi-valor txt-verde">${{ resumen.total_usd.toFixed(2) }}</p>
          </div>
          <div class="kpi-card">
            <p class="kpi-label">Total Bs</p>
            <p class="kpi-valor txt-bs">Bs. {{ resumen.total_bs.toFixed(2) }}</p>
          </div>
          <div class="kpi-card">
            <p class="kpi-label">Deuda proveedores</p>
            <p class="kpi-valor txt-rojo">${{ resumen.deuda_proveedores.toFixed(2) }}</p>
          </div>
        </div>

        <!-- Cuentas por moneda -->
        <h2 class="subtitulo">En dólares (USD)</h2>
        <div class="cuentas-grid">
          <div v-for="c in cuentasUSD" :key="c.id" class="cuenta-card"
            :class="{ 'saldo-neg': c.saldo < 0 }">
            <div class="cuenta-tipo">{{ labelTipo(c.tipo_cuenta) }}</div>
            <p class="cuenta-nombre">{{ c.nombre }}</p>
            <p class="cuenta-banco">{{ c.banco }}{{ c.identificador ? ' · ' + c.identificador : '' }}</p>
            <p class="cuenta-saldo txt-verde">${{ c.saldo.toFixed(2) }}</p>
            <div class="cuenta-acciones">
              <button class="btn-movs" @click="verMovimientos(c)">Ver movimientos</button>
              <button class="btn-edit" @click="editar(c)">Editar</button>
            </div>
          </div>
        </div>

        <h2 class="subtitulo">En bolívares (Bs)</h2>
        <div class="cuentas-grid">
          <div v-for="c in cuentasBs" :key="c.id" class="cuenta-card cuenta-bs"
            :class="{ 'saldo-neg': c.saldo < 0 }">
            <div class="cuenta-tipo">{{ labelTipo(c.tipo_cuenta) }}</div>
            <p class="cuenta-nombre">{{ c.nombre }}</p>
            <p class="cuenta-banco">{{ c.banco }}</p>
            <p class="cuenta-saldo txt-bs">Bs. {{ c.saldo.toFixed(2) }}</p>
            <div class="cuenta-acciones">
              <button class="btn-movs" @click="verMovimientos(c)">Ver movimientos</button>
              <button class="btn-edit" @click="editar(c)">Editar</button>
            </div>
          </div>
        </div>

        <!-- Modal movimientos de cuenta -->
        <div class="overlay" v-if="cuentaDetalle" @click.self="cuentaDetalle = null">
          <div class="modal">
            <div class="modal-header">
              <h2>{{ cuentaDetalle.nombre }}</h2>
              <span class="saldo-modal txt-verde">Saldo: {{ cuentaDetalle.moneda === 'USD' ? '$' : 'Bs.' }} {{ cuentaDetalle.saldo.toFixed(2) }}</span>
              <button class="btn-cerrar-modal" @click="cuentaDetalle = null">✕</button>
            </div>
            <div v-if="movsCuenta.length === 0" class="sin-datos">Sin movimientos registrados</div>
            <table v-else>
              <thead><tr><th>Fecha</th><th>Tipo</th><th>Concepto</th><th>Entrada</th><th>Salida</th></tr></thead>
              <tbody>
                <tr v-for="m in movsCuenta" :key="m.id">
                  <td>{{ formatFecha(m.fecha) }}</td>
                  <td><span :class="'badge badge-' + m.tipo">{{ labelTipo2(m.tipo) }}</span></td>
                  <td>{{ m.concepto }}</td>
                  <td class="txt-verde">{{ m.cuenta_destino_id === cuentaDetalle.id ? (cuentaDetalle.moneda === 'USD' ? '$' : 'Bs.') + ' ' + m.monto.toFixed(2) : '' }}</td>
                  <td class="txt-rojo">{{ m.cuenta_origen_id === cuentaDetalle.id ? (cuentaDetalle.moneda === 'USD' ? '$' : 'Bs.') + ' ' + m.monto.toFixed(2) : '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Modal nueva/editar cuenta -->
        <div class="overlay" v-if="mostrarForm" @click.self="cerrarForm">
          <div class="modal modal-sm">
            <div class="modal-header">
              <h2>{{ editandoId ? 'Editar cuenta' : 'Nueva cuenta' }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarForm">✕</button>
            </div>
            <div class="form-grid">
              <div class="field field-wide"><label>Nombre *</label><input v-model="form.nombre" /></div>
              <div class="field"><label>Banco</label><input v-model="form.banco" /></div>
              <div class="field">
                <label>Tipo</label>
                <select v-model="form.tipo_cuenta">
                  <option value="personal">Personal</option>
                  <option value="juridica">Jurídica</option>
                  <option value="caja_fisica">Caja física</option>
                  <option value="billetera_digital">Billetera digital</option>
                </select>
              </div>
              <div class="field">
                <label>Moneda</label>
                <select v-model="form.moneda">
                  <option value="USD">USD</option>
                  <option value="Bs">Bs</option>
                </select>
              </div>
              <div class="field field-wide"><label>Identificador (correo, cuenta, etc.)</label><input v-model="form.identificador" /></div>
            </div>
            <div class="form-botones">
              <button class="btn-cancelar" @click="cerrarForm">Cancelar</button>
              <button class="btn-guardar" @click="guardar" :disabled="guardando">{{ guardando ? 'Guardando...' : 'Guardar' }}</button>
            </div>
            <p class="msg-error" v-if="error">{{ error }}</p>
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
  name: 'CuentasBancarias',
  data() {
    return {
      usuario:      JSON.parse(localStorage.getItem('usuario') || '{}'),
      cuentas:      [],
      resumen:      null,
      cuentaDetalle:null,
      movsCuenta:   [],
      mostrarForm:  false,
      editandoId:   null,
      guardando:    false,
      error:        '',
      form: { nombre: '', banco: '', tipo_cuenta: 'personal', moneda: 'Bs', identificador: '' },
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
    cuentasBs()  { return this.cuentas.filter(c => c.moneda === 'Bs')  },
  },
  async mounted() {
    await Promise.all([this.cargar(), this.cargarResumen()])
  },
  methods: {
    async cargar() {
      const res = await axios.get('/bancos/cuentas/')
      this.cuentas = res.data
    },
    async cargarResumen() {
      const res = await axios.get('/bancos/resumen/')
      this.resumen = res.data
    },
    async verMovimientos(c) {
      this.cuentaDetalle = c
      const res = await axios.get(`/bancos/cuentas/${c.id}/movimientos`)
      this.movsCuenta = res.data
    },
    abrirNueva() {
      this.editandoId = null
      this.form = { nombre: '', banco: '', tipo_cuenta: 'personal', moneda: 'Bs', identificador: '' }
      this.mostrarForm = true
    },
    editar(c) {
      this.editandoId = c.id
      this.form = { nombre: c.nombre, banco: c.banco, tipo_cuenta: c.tipo_cuenta, moneda: c.moneda, identificador: c.identificador || '' }
      this.mostrarForm = true
    },
    cerrarForm() { this.mostrarForm = false; this.error = '' },
    async guardar() {
      if (!this.form.nombre) { this.error = 'El nombre es obligatorio'; return }
      this.guardando = true; this.error = ''
      try {
        if (this.editandoId) {
          await axios.put(`/bancos/cuentas/${this.editandoId}`, this.form)
        } else {
          await axios.post('/bancos/cuentas/', this.form)
        }
        await Promise.all([this.cargar(), this.cargarResumen()])
        this.cerrarForm()
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al guardar'
      } finally { this.guardando = false }
    },
    labelTipo(t) {
      return { personal:'Personal', juridica:'Jurídica', caja_fisica:'Caja Física', billetera_digital:'Digital' }[t] || t
    },
    labelTipo2(t) {
      const m = { ingreso_venta:'Venta', transferencia_interna:'Transfer.', pago_proveedor:'Proveedor', gasto_nomina:'Nómina', gasto_operativo:'Operativo', gasto_administrativo:'Administ.', ingreso_externo:'Ingreso', retiro:'Retiro' }
      return m[t] || t
    },
    formatFecha(iso) { return iso ? new Date(iso).toLocaleDateString('es-VE') : '—' },
    salir() { localStorage.removeItem('usuario'); this.$router.push('/login') },
  },
}
</script>

<style scoped>
.kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem; }

.subtitulo { color: var(--texto-muted); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.06em; margin: 1.5rem 0 0.75rem; border-top: 1px solid var(--borde); padding-top: 1rem; font-weight: 700; }

.cuentas-grid { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 0.5rem; }
.cuenta-card { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 12px; padding: 1.25rem; min-width: 200px; max-width: 240px; }
.cuenta-bs   { border-color: #FFCC0066; }
.saldo-neg   { border-color: var(--danger) !important; }
.cuenta-tipo  { color: var(--info); font-size: 0.72rem; font-weight: 700; text-transform: uppercase; margin-bottom: 0.3rem; }
.cuenta-nombre{ color: var(--texto-principal); font-weight: 700; margin: 0 0 0.2rem; font-size: 0.95rem; }
.cuenta-banco { color: var(--texto-muted); font-size: 0.82rem; margin: 0 0 0.75rem; }
.cuenta-saldo { font-size: 1.5rem; font-weight: 700; margin: 0 0 0.75rem; }
.cuenta-acciones { display: flex; gap: 0.5rem; }
.btn-movs { background: var(--fondo-sidebar); color: var(--texto-sec); border: 1px solid var(--borde); padding: 0.3rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.78rem; }
.btn-movs:hover { border-color: var(--amarillo); }
.btn-edit  { background: var(--info); color: white; border: none; padding: 0.3rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.78rem; }

.modal-sm { max-width: 520px; }
.saldo-modal { font-weight: 600; }

.badge-ingreso_venta,.badge-ingreso_externo { background: #16A34A1A; color: #16A34A; }
.badge-transferencia_interna { background: #2563EB1A; color: #2563EB; }
.badge-pago_proveedor { background: #FFCC0033; color: #996600; }
.badge-gasto_nomina,.badge-gasto_operativo,.badge-gasto_administrativo { background: #DC26261A; color: #DC2626; }
.badge-retiro { background: #8888881A; color: #555555; }

.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; }
</style>
