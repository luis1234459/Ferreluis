<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Depósitos y Transferencias</h1>
      </div>

      <div class="contenido-inner">
        <!-- Resumen -->
        <div class="resumen-row" v-if="resumen">
          <div class="kpi-card">
            <p class="kpi-label">Total USD</p>
            <p class="kpi-valor txt-verde">${{ resumen.total_usd.toFixed(2) }}</p>
          </div>
          <div class="kpi-card">
            <p class="kpi-label">Total Bs</p>
            <p class="kpi-valor txt-yellow">Bs. {{ resumen.total_bs.toFixed(2) }}</p>
          </div>
          <div class="kpi-card">
            <p class="kpi-label">Movimientos</p>
            <p class="kpi-valor">{{ resumen.cantidad }}</p>
          </div>
        </div>

        <!-- Formulario nuevo depósito -->
        <div class="form-box">
          <h2>{{ editandoId ? 'Editar movimiento' : 'Nuevo movimiento' }}</h2>
          <div class="form-grid">
            <div class="field">
              <label>Tipo</label>
              <select v-model="form.tipo">
                <option value="deposito">Depósito</option>
                <option value="transferencia">Transferencia</option>
                <option value="retiro">Retiro</option>
              </select>
            </div>
            <div class="field">
              <label>Moneda</label>
              <select v-model="form.moneda">
                <option value="USD">USD</option>
                <option value="Bs">Bs</option>
              </select>
            </div>
            <div class="field">
              <label>Monto</label>
              <input v-model.number="form.monto" type="number" min="0" step="0.01" placeholder="0.00" />
            </div>
            <div class="field">
              <label>Banco origen</label>
              <input v-model="form.banco_origen" placeholder="Ej: Banesco" />
            </div>
            <div class="field">
              <label>Banco destino</label>
              <input v-model="form.banco_destino" placeholder="Ej: Provincial" />
            </div>
            <div class="field">
              <label>Referencia</label>
              <input v-model="form.referencia" placeholder="Nro. de referencia" />
            </div>
            <div class="field field-wide">
              <label>Concepto</label>
              <input v-model="form.concepto" placeholder="Descripción del movimiento" />
            </div>
          </div>
          <div class="form-acciones">
            <button class="btn-cancelar" v-if="editandoId" @click="cancelarEdicion">Cancelar</button>
            <button class="btn-guardar" @click="guardar" :disabled="guardando">
              {{ guardando ? 'Guardando...' : (editandoId ? 'Actualizar' : 'Registrar') }}
            </button>
          </div>
          <p class="msg-error" v-if="error">{{ error }}</p>
          <p class="msg-exito" v-if="exitoso">Movimiento registrado correctamente.</p>
        </div>

        <!-- Filtros -->
        <div class="filtros">
          <select v-model="filtroMoneda" @change="cargar">
            <option value="">Todas las monedas</option>
            <option value="USD">USD</option>
            <option value="Bs">Bolívares</option>
          </select>
          <select v-model="filtroTipo" @change="cargar">
            <option value="">Todos los tipos</option>
            <option value="deposito">Depósito</option>
            <option value="transferencia">Transferencia</option>
            <option value="retiro">Retiro</option>
          </select>
        </div>

        <!-- Tabla -->
        <div class="tabla-container">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Tipo</th>
                <th>Banco origen</th>
                <th>Banco destino</th>
                <th>Concepto</th>
                <th>Referencia</th>
                <th>Monto</th>
                <th>Usuario</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in depositos" :key="d.id">
                <td>{{ formatFecha(d.fecha) }}</td>
                <td><span :class="'badge badge-' + d.tipo">{{ labelTipo(d.tipo) }}</span></td>
                <td>{{ d.banco_origen || '—' }}</td>
                <td>{{ d.banco_destino || '—' }}</td>
                <td>{{ d.concepto || '—' }}</td>
                <td>{{ d.referencia || '—' }}</td>
                <td :class="d.moneda === 'USD' ? 'txt-verde' : 'txt-yellow'">
                  {{ d.moneda === 'USD' ? '$' : 'Bs.' }} {{ Number(d.monto).toFixed(2) }}
                </td>
                <td>{{ d.usuario }}</td>
                <td>
                  <button class="btn-editar" @click="editar(d)">Editar</button>
                  <button class="btn-eliminar" @click="eliminar(d.id)">Eliminar</button>
                </td>
              </tr>
              <tr v-if="depositos.length === 0">
                <td colspan="9" class="sin-datos">No hay movimientos registrados</td>
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
  name: 'Depositos',
  data() {
    return {
      usuario:      JSON.parse(localStorage.getItem('usuario') || '{}'),
      depositos:    [],
      resumen:      null,
      filtroMoneda: '',
      filtroTipo:   '',
      guardando:    false,
      exitoso:      false,
      error:        '',
      editandoId:   null,
      form: {
        tipo:          'deposito',
        moneda:        'USD',
        monto:         '',
        banco_origen:  '',
        banco_destino: '',
        referencia:    '',
        concepto:      '',
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
  },
  async mounted() {
    await Promise.all([this.cargar(), this.cargarResumen()])
  },
  methods: {
    async cargar() {
      const params = {}
      if (this.filtroMoneda) params.moneda = this.filtroMoneda
      if (this.filtroTipo)   params.tipo   = this.filtroTipo
      const res = await axios.get('/depositos/', { params })
      this.depositos = res.data
    },
    async cargarResumen() {
      const res = await axios.get('/depositos/resumen')
      this.resumen = res.data
    },
    async guardar() {
      if (!this.form.monto || this.form.monto <= 0) {
        this.error = 'Ingresa un monto válido'
        return
      }
      this.error    = ''
      this.guardando = true
      try {
        const payload = { ...this.form, usuario: this.usuario.usuario || 'sistema' }
        if (this.editandoId) {
          await axios.put(`/depositos/${this.editandoId}`, payload)
        } else {
          await axios.post('/depositos/', payload)
        }
        await Promise.all([this.cargar(), this.cargarResumen()])
        this.resetForm()
        this.exitoso = true
        setTimeout(() => this.exitoso = false, 3000)
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al guardar'
      } finally {
        this.guardando = false
      }
    },
    editar(d) {
      this.editandoId      = d.id
      this.form.tipo         = d.tipo
      this.form.moneda       = d.moneda
      this.form.monto        = d.monto
      this.form.banco_origen = d.banco_origen || ''
      this.form.banco_destino= d.banco_destino || ''
      this.form.referencia   = d.referencia || ''
      this.form.concepto     = d.concepto || ''
    },
    cancelarEdicion() {
      this.editandoId = null
      this.resetForm()
    },
    async eliminar(id) {
      if (!confirm('¿Eliminar este movimiento?')) return
      await axios.delete(`/depositos/${id}`)
      await Promise.all([this.cargar(), this.cargarResumen()])
    },
    resetForm() {
      this.editandoId      = null
      this.form.tipo         = 'deposito'
      this.form.moneda       = 'USD'
      this.form.monto        = ''
      this.form.banco_origen = ''
      this.form.banco_destino= ''
      this.form.referencia   = ''
      this.form.concepto     = ''
    },
    labelTipo(tipo) {
      return { deposito: 'Depósito', transferencia: 'Transferencia', retiro: 'Retiro' }[tipo] || tipo
    },
    formatFecha(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleString('es-VE')
    },
    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    },
  },
}
</script>

<style scoped>
.resumen-row { display: flex; gap: 1.5rem; margin-bottom: 2rem; flex-wrap: wrap; }

.form-box { background: #FFFFFF; border-radius: 14px; padding: 1.5rem; max-width: 800px; margin-bottom: 2rem; border: 1px solid var(--borde); }
.form-box h2 { color: var(--texto-principal); margin: 0 0 1.25rem; font-size: 1rem; font-weight: 700; }
.form-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
.field-wide { grid-column: span 2; }
.form-acciones { display: flex; gap: 1rem; margin-top: 1rem; justify-content: flex-end; }

.badge-deposito      { background: #16A34A1A; color: #16A34A; }
.badge-transferencia { background: #2563EB1A; color: #2563EB; }
.badge-retiro        { background: #DC26261A; color: #DC2626; }

.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: #1A1A1A; border: 1px solid #DDDDDD; padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; }
.btn-editar   { background: #2563EB; color: white; border: none; padding: 0.3rem 0.7rem; border-radius: 5px; cursor: pointer; margin-right: 0.3rem; font-size: 0.82rem; }
.btn-eliminar { background: #DC2626; color: white; border: none; padding: 0.3rem 0.7rem; border-radius: 5px; cursor: pointer; font-size: 0.82rem; }
</style>
