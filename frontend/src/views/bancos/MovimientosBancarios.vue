<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Movimientos Bancarios</h1>
      </div>

      <div class="contenido-inner">
        <!-- Formulario nuevo movimiento -->
        <div class="form-box">
          <h2>Registrar movimiento</h2>
          <div class="form-grid" style="grid-template-columns: repeat(3, 1fr)">
            <div class="field">
              <label>Tipo</label>
              <select v-model="form.tipo">
                <option value="transferencia_interna">Transferencia interna</option>
                <option value="pago_proveedor">Pago a proveedor</option>
                <option value="gasto_nomina">Gasto nómina</option>
                <option value="gasto_operativo">Gasto operativo</option>
                <option value="gasto_administrativo">Gasto administrativo</option>
                <option value="ingreso_externo">Ingreso externo</option>
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

            <div class="field" v-if="tieneOrigen">
              <label>Cuenta origen</label>
              <select v-model="form.cuenta_origen_id">
                <option value="">— Seleccionar —</option>
                <option v-for="c in cuentasFiltradas" :key="c.id" :value="c.id">
                  {{ c.nombre }} ({{ c.moneda === 'USD' ? '$' : 'Bs.' }}{{ c.saldo.toFixed(2) }})
                </option>
              </select>
            </div>
            <div class="field" v-if="tieneDestino">
              <label>Cuenta destino</label>
              <select v-model="form.cuenta_destino_id">
                <option value="">— Seleccionar —</option>
                <option v-for="c in cuentasFiltradas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
              </select>
            </div>

            <div class="field" v-if="form.tipo === 'pago_proveedor'">
              <label>Proveedor</label>
              <select v-model="form.proveedor_id">
                <option value="">— Seleccionar —</option>
                <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
              </select>
            </div>
            <div class="field" v-else>
              <label>Beneficiario</label>
              <input v-model="form.beneficiario" placeholder="A quién va el dinero" />
            </div>

            <div class="field">
              <label>Monto</label>
              <input v-model.number="form.monto" type="number" min="0" step="0.01" placeholder="0.00" />
            </div>
            <div class="field">
              <label>Referencia</label>
              <input v-model="form.referencia" placeholder="Nro. operación" />
            </div>
            <div class="field full">
              <label>Concepto</label>
              <input v-model="form.concepto" placeholder="Descripción del movimiento" />
            </div>
          </div>
          <div class="form-botones">
            <button class="btn-guardar" @click="guardar" :disabled="guardando">
              {{ guardando ? 'Registrando...' : 'Registrar movimiento' }}
            </button>
          </div>
          <p class="msg-error" v-if="error">{{ error }}</p>
          <p class="msg-exito" v-if="exitoso">Movimiento registrado correctamente.</p>
        </div>

        <!-- Filtros -->
        <div class="filtros">
          <select v-model="filtroTipo" @change="cargar">
            <option value="">Todos los tipos</option>
            <option value="ingreso_venta">Ingresos de venta</option>
            <option value="transferencia_interna">Transferencias</option>
            <option value="pago_proveedor">Pagos proveedores</option>
            <option value="gasto_nomina">Nómina</option>
            <option value="gasto_operativo">Operativo</option>
            <option value="gasto_administrativo">Administrativo</option>
            <option value="ingreso_externo">Ingresos externos</option>
            <option value="retiro">Retiros</option>
          </select>
          <select v-model="filtroCuenta" @change="cargar">
            <option value="">Todas las cuentas</option>
            <option v-for="c in cuentas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
          </select>
        </div>

        <!-- Tabla -->
        <div class="tabla-container">
          <table>
            <thead>
              <tr><th>Fecha</th><th>Tipo</th><th>Origen</th><th>Destino</th><th>Concepto</th><th>Monto</th><th>Ref.</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="m in movimientos" :key="m.id">
                <td>{{ formatFecha(m.fecha) }}</td>
                <td><span :class="'badge badge-' + m.tipo">{{ labelTipo(m.tipo) }}</span></td>
                <td>{{ m.cuenta_origen || '—' }}</td>
                <td>{{ m.cuenta_destino || '—' }}</td>
                <td>{{ m.concepto }}</td>
                <td :class="esIngreso(m) ? 'txt-verde' : 'txt-rojo'">
                  {{ m.moneda === 'USD' ? '$' : 'Bs.' }} {{ m.monto.toFixed(2) }}
                </td>
                <td>{{ m.referencia || '—' }}</td>
                <td><button class="btn-anular" @click="anular(m.id)" title="Anular">✕</button></td>
              </tr>
              <tr v-if="movimientos.length === 0">
                <td colspan="8" class="sin-datos">Sin movimientos</td>
              </tr>
            </tbody>
          </table>
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
  name: 'MovimientosBancarios',
  data() {
    return {
      usuario:     JSON.parse(localStorage.getItem('usuario') || '{}'),
      movimientos: [],
      cuentas:     [],
      proveedores: [],
      filtroTipo:  '',
      filtroCuenta:'',
      guardando:   false,
      exitoso:     false,
      error:       '',
      form: {
        tipo: 'transferencia_interna', moneda: 'USD',
        cuenta_origen_id: '', cuenta_destino_id: '',
        proveedor_id: '', beneficiario: '',
        monto: '', referencia: '', concepto: '',
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
    tieneOrigen() {
      return !['ingreso_externo'].includes(this.form.tipo)
    },
    tieneDestino() {
      return ['transferencia_interna', 'ingreso_externo'].includes(this.form.tipo)
    },
    cuentasFiltradas() {
      return this.cuentas.filter(c => c.moneda === this.form.moneda)
    },
  },
  async mounted() {
    await Promise.all([this.cargar(), this.cargarCuentas(), this.cargarProveedores()])
  },
  methods: {
    async cargar() {
      const params = {}
      if (this.filtroTipo)   params.tipo      = this.filtroTipo
      if (this.filtroCuenta) params.cuenta_id = this.filtroCuenta
      const res = await axios.get('/bancos/movimientos/', { params })
      this.movimientos = res.data
    },
    async cargarCuentas() {
      const res = await axios.get('/bancos/cuentas/')
      this.cuentas = res.data
    },
    async cargarProveedores() {
      const res = await axios.get('/compras/proveedores/')
      this.proveedores = res.data
    },
    async guardar() {
      this.error = ''; this.exitoso = false; this.guardando = true
      try {
        const payload = {
          ...this.form,
          cuenta_origen_id:  this.form.cuenta_origen_id  || null,
          cuenta_destino_id: this.form.cuenta_destino_id || null,
          proveedor_id:      this.form.proveedor_id      || null,
          registrado_por:    this.usuario.usuario || 'admin',
        }
        await axios.post('/bancos/movimientos/', payload)
        await Promise.all([this.cargar(), this.cargarCuentas()])
        this.exitoso = true
        this.form.monto = ''; this.form.referencia = ''; this.form.concepto = ''
        setTimeout(() => this.exitoso = false, 3000)
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al registrar'
      } finally { this.guardando = false }
    },
    async anular(id) {
      if (!confirm('¿Anular este movimiento?')) return
      await axios.delete(`/bancos/movimientos/${id}`)
      await this.cargar()
    },
    esIngreso(m) {
      return ['ingreso_venta', 'ingreso_externo'].includes(m.tipo)
    },
    labelTipo(t) {
      const m = { ingreso_venta:'Venta', transferencia_interna:'Transfer.', pago_proveedor:'Proveedor', gasto_nomina:'Nómina', gasto_operativo:'Operativo', gasto_administrativo:'Admin.', ingreso_externo:'Ingreso', retiro:'Retiro' }
      return m[t] || t
    },
    formatFecha(iso) { return iso ? new Date(iso).toLocaleString('es-VE') : '—' },
    salir() { localStorage.removeItem('usuario'); this.$router.push('/login') },
  },
}
</script>

<style scoped>
.form-box { background: #FFFFFF; border-radius: 14px; padding: 1.5rem; max-width: 860px; margin-bottom: 2rem; border: 1px solid var(--borde); }
.form-box h2 { color: var(--texto-principal); margin: 0 0 1.25rem; font-size: 1rem; font-weight: 700; }
.full { grid-column: 1 / -1; }

.btn-guardar { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }

.badge-ingreso_venta,.badge-ingreso_externo { background: #16A34A1A; color: #16A34A; }
.badge-transferencia_interna { background: #2563EB1A; color: #2563EB; }
.badge-pago_proveedor { background: #FFCC0033; color: #996600; }
.badge-gasto_nomina,.badge-gasto_operativo,.badge-gasto_administrativo { background: #DC26261A; color: #DC2626; }
.badge-retiro { background: #8888881A; color: #555555; }

.btn-anular { background: transparent; border: 1px solid var(--danger); color: var(--danger); padding: 0.2rem 0.5rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.btn-anular:hover { background: var(--danger); color: white; }
</style>
