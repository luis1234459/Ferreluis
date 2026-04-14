<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Tasas de cambio</h1>
      </div>

      <div class="contenido-inner">
        <!-- Tarjetas de tasas actuales -->
        <div class="tasas-row">
          <div class="tasa-card">
            <p class="card-label">Tasa BCV</p>
            <p class="card-valor">Bs. {{ tasaBcv ? tasaBcv.toFixed(2) : '—' }}</p>
            <p class="card-sub">Referencia oficial</p>
          </div>
          <div class="tasa-card card-binance">
            <p class="card-label">Tasa Binance</p>
            <p class="card-valor txt-yellow">Bs. {{ tasaBinance ? tasaBinance.toFixed(2) : '—' }}</p>
            <p class="card-sub">Mercado paralelo</p>
          </div>
          <div class="tasa-card card-factor">
            <p class="card-label">Factor de protección</p>
            <p class="card-valor txt-verde">{{ factor ? factor.toFixed(4) : '—' }}</p>
            <p class="card-sub">Binance ÷ BCV</p>
          </div>
        </div>

        <p class="fecha-txt" v-if="fecha">Última actualización: {{ fecha }}</p>

        <!-- Panel de acciones -->
        <div class="acciones-box">
          <div class="accion-col">
            <h3>Actualizar desde BCV</h3>
            <p class="accion-desc">Consulta automáticamente la tasa oficial en bcv.org.ve</p>
            <button class="btn-bcv" @click="actualizarBCV" :disabled="cargando">
              {{ cargando ? 'Consultando...' : 'Actualizar BCV' }}
            </button>
          </div>

          <div class="divider"></div>

          <div class="accion-col">
            <h3>Actualizar manualmente</h3>
            <div class="input-group">
              <label>Tasa BCV (Bs/USD)</label>
              <input v-model.number="formBcv" type="number" placeholder="Ej: 45.50" />
            </div>
            <div class="input-group">
              <label>Tasa Binance (Bs/USD)</label>
              <input v-model.number="formBinance" type="number" placeholder="Ej: 48.20" />
            </div>
            <div class="factor-preview" v-if="formBcv > 0 && formBinance > 0">
              Factor: {{ (formBinance / formBcv).toFixed(4) }}
            </div>
            <button class="btn-manual" @click="actualizarManual">Guardar</button>
          </div>
        </div>

        <p class="msg-exito" v-if="exitoso">Tasas actualizadas correctamente.</p>
        <p class="msg-error" v-if="error">{{ error }}</p>
      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'Tasa',
  data() {
    return {
      usuario:     JSON.parse(localStorage.getItem('usuario') || '{}'),
      tasaBcv:     null,
      tasaBinance: null,
      factor:      null,
      fecha:       null,
      formBcv:     '',
      formBinance: '',
      cargando:    false,
      exitoso:     false,
      error:       '',
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
    await this.cargarTasa()
  },
  methods: {
    async cargarTasa() {
      try {
        const res = await axios.get('/tasa/')
        this.tasaBcv     = res.data.tasa
        this.tasaBinance = res.data.tasa_binance
        this.factor      = res.data.factor
        this.fecha       = res.data.fecha ? new Date(res.data.fecha).toLocaleString() : null
      } catch {
        this.error = 'Error al cargar las tasas'
      }
    },
    async actualizarBCV() {
      this.cargando = true
      this.error    = ''
      try {
        const res = await axios.post('/tasa/actualizar-bcv')
        if (res.data.tasa) {
          await this.cargarTasa()
          this.exitoso = true
          setTimeout(() => this.exitoso = false, 3000)
        } else {
          this.error = res.data.error || 'No se pudo obtener la tasa del BCV'
        }
      } catch {
        this.error = 'Error al conectar con el BCV'
      } finally {
        this.cargando = false
      }
    },
    async actualizarManual() {
      if (!this.formBcv) { this.error = 'Ingresa la tasa BCV'; return }
      this.error = ''
      try {
        const payload = { tasa: this.formBcv }
        if (this.formBinance) payload.tasa_binance = this.formBinance
        await axios.post('/tasa/actualizar-manual', payload)
        await this.cargarTasa()
        this.formBcv     = ''
        this.formBinance = ''
        this.exitoso     = true
        setTimeout(() => this.exitoso = false, 3000)
      } catch {
        this.error = 'Error al guardar las tasas'
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
.tasas-row { display: flex; gap: 1.5rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
.tasa-card { background: #FFFFFF; border-radius: 14px; padding: 1.5rem 2rem; min-width: 180px; text-align: center; border: 1px solid var(--borde); }
.card-binance { border-color: #FFCC0066; }
.card-factor  { border-color: #16A34A44; }
.card-label { color: var(--texto-muted); font-size: 0.85rem; margin: 0 0 0.4rem; }
.card-valor { color: var(--texto-principal); font-size: 2.2rem; font-weight: 600; margin: 0; }
.card-sub { color: var(--texto-muted); font-size: 0.8rem; margin: 0.4rem 0 0; }

.fecha-txt { color: var(--texto-muted); font-size: 0.82rem; margin-bottom: 2rem; }

.acciones-box { background: #FFFFFF; border-radius: 14px; padding: 2rem; display: flex; gap: 2rem; max-width: 750px; border: 1px solid var(--borde); }
.accion-col { flex: 1; display: flex; flex-direction: column; gap: 1rem; }
.accion-col h3 { color: var(--texto-principal); margin: 0; font-size: 1rem; font-weight: 700; }
.accion-desc { color: var(--texto-sec); font-size: 0.88rem; margin: 0; }
.divider { width: 1px; background: var(--borde); }

.input-group { display: flex; flex-direction: column; gap: 0.3rem; }
.input-group label { color: var(--texto-sec); font-size: 0.85rem; font-weight: 600; }

.factor-preview { color: #16A34A; font-size: 0.9rem; font-weight: 600; }

.btn-bcv { background: #2563EB; color: white; border: none; padding: 0.75rem; border-radius: 8px; cursor: pointer; font-size: 0.95rem; font-weight: 600; }
.btn-bcv:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-manual { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.75rem; border-radius: 8px; cursor: pointer; font-size: 0.95rem; font-weight: 600; }
</style>
