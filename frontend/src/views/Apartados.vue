<template>
  <div class="layout">
    <AppSidebar />
    <main class="contenido">
      <div class="top-bar">
        <h1>📦 Apartados</h1>
        <div class="apt-filtros">
          <button :class="['btn-filtro', filtroEstado === '' ? 'activo' : '']" @click="filtroEstado = ''; cargar()">Todos</button>
          <button :class="['btn-filtro', filtroEstado === 'activo' ? 'activo' : '']" @click="filtroEstado = 'activo'; cargar()">Activos</button>
          <button :class="['btn-filtro', filtroEstado === 'pagado' ? 'activo' : '']" @click="filtroEstado = 'pagado'; cargar()">Pagados</button>
          <button :class="['btn-filtro', filtroEstado === 'cancelado' ? 'activo' : '']" @click="filtroEstado = 'cancelado'; cargar()">Cancelados</button>
        </div>
      </div>

      <div class="contenido-inner">
        <div v-if="cargando" class="sin-datos">Cargando...</div>

        <div v-else-if="apartados.length === 0" class="sin-datos">
          No hay apartados en este estado
        </div>

        <div v-else class="apt-lista">
          <div v-for="apt in apartados" :key="apt.id" class="apt-card">

            <!-- Header -->
            <div class="apt-card-header">
              <div class="apt-header-izq">
                <span class="apt-numero">{{ apt.numero }}</span>
                <span :class="['apt-estado-badge', 'estado-' + apt.estado]">{{ labelEstado(apt.estado) }}</span>
              </div>
              <div class="apt-header-der">
                <span class="apt-fecha">{{ fmtFecha(apt.fecha_creacion) }}</span>
                <span v-if="apt.fecha_maxima" class="apt-fecha-max" :class="{ vencido: estaVencido(apt.fecha_maxima) }">
                  Vence: {{ fmtFecha(apt.fecha_maxima) }}
                </span>
              </div>
            </div>

            <!-- Cliente + semáforo -->
            <div class="apt-card-body">
              <div class="apt-cliente">
                <span class="apt-nombre">{{ apt.cliente_nombre || 'Sin nombre' }}</span>
                <span v-if="apt.cliente_telefono" class="apt-tel">📞 {{ apt.cliente_telefono }}</span>
              </div>

              <!-- Barra de progreso -->
              <div class="apt-progreso-wrap">
                <div class="apt-progreso-bar">
                  <div class="apt-progreso-fill"
                    :style="{ width: pctAbonado(apt) + '%' }"
                    :class="colorProgreso(apt)"></div>
                </div>
                <div class="apt-progreso-nums">
                  <span class="apt-abonado">${{ apt.abonado_usd.toFixed(2) }} abonado</span>
                  <span class="apt-total">${{ apt.total_usd.toFixed(2) }} total</span>
                </div>
              </div>

              <!-- Semáforo -->
              <div class="apt-semaforo">
                <span :class="['semaforo-dot', colorSemaforo(apt)]"></span>
                <span class="semaforo-label">{{ labelSemaforo(apt) }}</span>
              </div>

              <!-- Cuotas -->
              <div v-if="apt.cuotas" class="apt-cuotas">
                {{ apt.cuotas }} cuotas de ${{ apt.monto_cuota?.toFixed(2) }}
              </div>

              <!-- Productos -->
              <div class="apt-productos">
                <div v-for="d in apt.detalles" :key="d.id" class="apt-prod-row">
                  <span>{{ d.cantidad }}× {{ d.nombre_producto }}</span>
                  <span>${{ d.subtotal_usd.toFixed(2) }}</span>
                </div>
              </div>

              <!-- Observación -->
              <p v-if="apt.observacion" class="apt-obs">{{ apt.observacion }}</p>
            </div>

            <!-- Acciones -->
            <div class="apt-card-footer" v-if="apt.estado === 'activo'">
              <button class="btn-abonar" @click="abrirAbono(apt)">💰 Abonar</button>
              <button class="btn-convertir" @click="convertir(apt)" :disabled="procesando === apt.id">
                {{ procesando === apt.id ? '...' : '✓ Convertir a venta' }}
              </button>
              <button class="btn-cancelar-apt" @click="cancelar(apt)" :disabled="procesando === apt.id">Cancelar</button>
            </div>
          </div>
        </div>

        <!-- Modal abono -->
        <div class="overlay" v-if="modalAbono" @click.self="modalAbono = false">
          <div class="modal" style="max-width:420px">
            <div class="modal-header">
              <h2>Registrar abono — {{ abonoApt?.numero }}</h2>
              <button class="btn-cerrar-modal" @click="modalAbono = false">✕</button>
            </div>
            <div style="padding:1.25rem;display:flex;flex-direction:column;gap:0.75rem">
              <div class="field">
                <label>Monto</label>
                <input v-model.number="formAbono.monto" type="number" min="0" step="0.01" placeholder="0.00" class="input-field" />
              </div>
              <div class="field">
                <label>Moneda</label>
                <select v-model="formAbono.moneda_pago" class="input-field">
                  <option value="USD">USD</option>
                  <option value="Bs">Bolívares</option>
                </select>
              </div>
              <div class="field">
                <label>Método de pago</label>
                <select v-model="formAbono.metodo_pago" class="input-field">
                  <option value="efectivo_usd">Efectivo $</option>
                  <option value="zelle">Zelle</option>
                  <option value="binance">Binance</option>
                  <option value="efectivo_bs">Efectivo Bs</option>
                  <option value="transferencia_bs">Transferencia Bs</option>
                  <option value="pago_movil">Pago Móvil</option>
                </select>
              </div>
              <div class="field">
                <label>Referencia (opcional)</label>
                <input v-model="formAbono.referencia" placeholder="Nro. operación" class="input-field" />
              </div>
              <p v-if="errorAbono" style="color:#DC2626;font-size:0.85rem">{{ errorAbono }}</p>
            </div>
            <div class="form-botones">
              <button class="btn-cancelar" @click="modalAbono = false">Cancelar</button>
              <button class="btn-guardar" @click="confirmarAbono" :disabled="abonando">
                {{ abonando ? 'Registrando...' : 'Confirmar abono' }}
              </button>
            </div>
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
  name: 'Apartados',
  data() {
    return {
      usuario:      JSON.parse(localStorage.getItem('usuario') || '{}'),
      apartados:    [],
      cargando:     false,
      filtroEstado: 'activo',
      procesando:   null,
      modalAbono:   false,
      abonoApt:     null,
      abonando:     false,
      errorAbono:   '',
      formAbono: { monto: null, moneda_pago: 'USD', metodo_pago: 'efectivo_usd', referencia: '' },
    }
  },
  async mounted() { await this.cargar() },
  methods: {
    async cargar() {
      this.cargando = true
      try {
        const res = await axios.get('/apartados/', {
          params: { estado: this.filtroEstado || undefined },
          headers: {
            'x-usuario-nombre': this.usuario.usuario || this.usuario.nombre || '',
            'x-usuario-rol':    this.usuario.rol || '',
          },
        })
        this.apartados = res.data
      } catch {} finally { this.cargando = false }
    },
    abrirAbono(apt) {
      this.abonoApt  = apt
      this.formAbono = { monto: null, moneda_pago: 'USD', metodo_pago: 'efectivo_usd', referencia: '' }
      this.errorAbono = ''
      this.modalAbono = true
    },
    async confirmarAbono() {
      if (!this.formAbono.monto || this.formAbono.monto <= 0) { this.errorAbono = 'Ingresa un monto válido'; return }
      this.abonando = true; this.errorAbono = ''
      try {
        await axios.post(`/apartados/${this.abonoApt.id}/abono`, this.formAbono, {
          headers: { 'x-usuario-nombre': this.usuario.usuario || '' },
        })
        this.modalAbono = false
        await this.cargar()
      } catch (e) {
        this.errorAbono = e?.response?.data?.detail || 'Error al registrar abono'
      } finally { this.abonando = false }
    },
    async cancelar(apt) {
      if (!confirm(`¿Cancelar apartado ${apt.numero}? Se devolverá el stock.`)) return
      this.procesando = apt.id
      try {
        await axios.post(`/apartados/${apt.id}/cancelar`)
        await this.cargar()
      } catch (e) { alert(e?.response?.data?.detail || 'Error al cancelar') }
      finally { this.procesando = null }
    },
    async convertir(apt) {
      if (!confirm(`¿Convertir ${apt.numero} a venta? El stock ya estaba descontado.`)) return
      this.procesando = apt.id
      try {
        const res = await axios.post(`/apartados/${apt.id}/convertir-venta`, {}, {
          headers: { 'x-usuario-nombre': this.usuario.usuario || '' },
        })
        alert(`Venta #${res.data.venta_id} registrada exitosamente`)
        await this.cargar()
      } catch (e) { alert(e?.response?.data?.detail || 'Error al convertir') }
      finally { this.procesando = null }
    },
    pctAbonado(apt) {
      if (!apt.total_usd) return 0
      return Math.min(100, Math.round((apt.abonado_usd / apt.total_usd) * 100))
    },
    colorProgreso(apt) {
      const p = this.pctAbonado(apt)
      if (p >= 100) return 'progreso-verde'
      if (p > 0)    return 'progreso-azul'
      return 'progreso-gris'
    },
    colorSemaforo(apt) {
      const p = this.pctAbonado(apt)
      if (p >= 100) return 'dot-verde'
      if (p > 0)    return 'dot-azul'
      return 'dot-amarillo'
    },
    labelSemaforo(apt) {
      const p = this.pctAbonado(apt)
      if (p >= 100) return 'Listo para entregar'
      if (p > 0)    return `${p}% abonado`
      return 'Sin abono'
    },
    labelEstado(e) { return { activo: 'Activo', pagado: 'Pagado', cancelado: 'Cancelado' }[e] || e },
    estaVencido(fecha) { return fecha && new Date(fecha) < new Date() },
    fmtFecha(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleDateString('es-VE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    },
  },
}
</script>

<style scoped>
.apt-filtros { display: flex; gap: 0.4rem; }
.btn-filtro { background: var(--fondo-sidebar); border: 1px solid var(--borde); border-radius: 6px; padding: 0.35rem 0.75rem; cursor: pointer; font-size: 0.82rem; color: var(--texto-sec); }
.btn-filtro.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }

.apt-lista { display: flex; flex-direction: column; gap: 1rem; }
.apt-card { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 14px; overflow: hidden; }

.apt-card-header { display: flex; justify-content: space-between; align-items: center; padding: 0.85rem 1.25rem; background: #1A1A1A; border-bottom: 1px solid var(--borde); }
.apt-header-izq { display: flex; align-items: center; gap: 0.6rem; }
.apt-numero { font-weight: 800; font-size: 0.95rem; color: #FFCC00; }
.apt-estado-badge { font-size: 0.7rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 4px; }
.estado-activo { background: #DBEAFE; color: #1E40AF; }
.estado-pagado { background: #DCFCE7; color: #15803D; }
.estado-cancelado { background: #F1F5F9; color: #6B7280; }
.apt-header-der { display: flex; flex-direction: column; align-items: flex-end; gap: 0.1rem; }
.apt-fecha { font-size: 0.78rem; color: var(--texto-muted); }
.apt-fecha-max { font-size: 0.72rem; color: #D97706; }
.apt-fecha-max.vencido { color: #DC2626; font-weight: 700; }

.apt-card-body { padding: 1rem 1.25rem; display: flex; flex-direction: column; gap: 0.65rem; }
.apt-cliente { display: flex; align-items: center; gap: 0.75rem; }
.apt-nombre { font-weight: 700; font-size: 0.95rem; }
.apt-tel { font-size: 0.82rem; color: var(--texto-sec); }

.apt-progreso-wrap { display: flex; flex-direction: column; gap: 0.3rem; }
.apt-progreso-bar { height: 8px; background: #E5E7EB; border-radius: 4px; overflow: hidden; }
.apt-progreso-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
.progreso-verde { background: #16A34A; }
.progreso-azul  { background: #2563EB; }
.progreso-gris  { background: #9CA3AF; }
.apt-progreso-nums { display: flex; justify-content: space-between; font-size: 0.78rem; }
.apt-abonado { color: #16A34A; font-weight: 600; }
.apt-total   { color: var(--texto-muted); }

.apt-semaforo { display: flex; align-items: center; gap: 0.4rem; }
.semaforo-dot { width: 10px; height: 10px; border-radius: 50%; }
.dot-verde    { background: #16A34A; }
.dot-azul     { background: #2563EB; }
.dot-amarillo { background: #D97706; }
.semaforo-label { font-size: 0.82rem; font-weight: 600; color: var(--texto-sec); }

.apt-cuotas { font-size: 0.8rem; color: #7C3AED; font-weight: 600; background: #EDE9FE; padding: 0.2rem 0.6rem; border-radius: 4px; display: inline-block; }
.apt-productos { border-top: 1px solid var(--borde); padding-top: 0.5rem; display: flex; flex-direction: column; gap: 0.2rem; }
.apt-prod-row { display: flex; justify-content: space-between; font-size: 0.82rem; color: var(--texto-sec); }
.apt-obs { font-size: 0.8rem; color: var(--texto-muted); font-style: italic; margin: 0; }

.apt-card-footer { padding: 0.75rem 1.25rem; border-top: 1px solid var(--borde); display: flex; gap: 0.5rem; flex-wrap: wrap; }
.btn-abonar     { background: #2563EB; color: white; border: none; padding: 0.45rem 1rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }
.btn-convertir  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.45rem 1rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }
.btn-cancelar-apt { background: transparent; color: #DC2626; border: 1px solid #DC2626; padding: 0.45rem 1rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem; }
.btn-convertir:disabled, .btn-cancelar-apt:disabled { opacity: 0.4; cursor: not-allowed; }

.input-field { border: 1px solid var(--borde); border-radius: 6px; padding: 0.5rem 0.65rem; font-size: 0.875rem; width: 100%; box-sizing: border-box; }
.input-field:focus { outline: none; border-color: #FFCC00; }
.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; }
</style>
