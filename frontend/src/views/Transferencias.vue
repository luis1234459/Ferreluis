<template>
  <div class="layout">
    <AppSidebar />
    <main class="contenido">
      <div class="top-bar">
        <h1>🔁 Transferencias entre sedes</h1>
        <button class="btn-nueva" @click="abrirNueva">+ Nueva transferencia</button>
      </div>

      <div class="contenido-inner">
        <!-- Filtros -->
        <div class="tra-filtros">
          <select v-model="filtros.sede_origen_id" class="input-field" @change="cargar">
            <option :value="''">Origen: todas</option>
            <option v-for="s in sedes" :key="'fo'+s.id" :value="s.id">Origen: {{ s.nombre }}</option>
          </select>
          <select v-model="filtros.sede_destino_id" class="input-field" @change="cargar">
            <option :value="''">Destino: todas</option>
            <option v-for="s in sedes" :key="'fd'+s.id" :value="s.id">Destino: {{ s.nombre }}</option>
          </select>
          <select v-model="filtros.estado" class="input-field" @change="cargar">
            <option value="">Estado: todos</option>
            <option value="pendiente">Pendiente</option>
            <option value="en_transito">En tránsito</option>
            <option value="recibida">Recibida</option>
            <option value="cancelada">Cancelada</option>
          </select>
          <input type="date" v-model="filtros.fecha_inicio" class="input-field" @change="cargar" />
          <input type="date" v-model="filtros.fecha_fin" class="input-field" @change="cargar" />
          <button class="btn-limpiar" @click="limpiarFiltros">Limpiar</button>
        </div>

        <div v-if="cargando" class="sin-datos">Cargando...</div>
        <div v-else-if="transferencias.length === 0" class="sin-datos">No hay transferencias con estos filtros</div>

        <div v-else class="tra-lista">
          <div v-for="t in transferencias" :key="t.id" class="tra-card">
            <div class="tra-card-header">
              <div class="tra-header-izq">
                <span class="tra-ruta">{{ t.sede_origen_nombre }} → {{ t.sede_destino_nombre }}</span>
                <span :class="['tra-estado-badge', 'estado-' + t.estado]">{{ labelEstado(t.estado) }}</span>
              </div>
              <div class="tra-header-der">
                <span class="tra-fecha">{{ fmtFecha(t.fecha) }}</span>
                <span class="tra-usuario" v-if="t.usuario_nombre">{{ t.usuario_nombre }}</span>
              </div>
            </div>

            <div class="tra-card-body">
              <div class="tra-productos">
                <div v-for="d in t.detalles" :key="d.id" class="tra-prod-row">
                  <span>{{ d.cantidad }}× {{ d.nombre_producto }}</span>
                </div>
              </div>
              <p v-if="t.notas" class="tra-notas">{{ t.notas }}</p>
            </div>

            <div class="tra-card-footer" v-if="t.estado !== 'recibida' && t.estado !== 'cancelada'">
              <button v-if="t.estado === 'pendiente'" class="btn-confirmar" @click="confirmar(t)" :disabled="procesando === t.id">
                {{ procesando === t.id ? '...' : '✓ Confirmar (descuenta origen)' }}
              </button>
              <button v-if="t.estado === 'en_transito'" class="btn-recibir" @click="recibir(t)" :disabled="procesando === t.id">
                {{ procesando === t.id ? '...' : '📥 Recibir (suma destino)' }}
              </button>
              <button class="btn-cancelar-tra" @click="cancelar(t)" :disabled="procesando === t.id">Cancelar</button>
            </div>
          </div>
        </div>

        <!-- Modal nueva transferencia -->
        <div class="overlay" v-if="modalNueva" @click.self="cerrarNueva">
          <div class="modal" style="max-width:560px">
            <div class="modal-header">
              <h2>Nueva transferencia</h2>
              <button class="btn-cerrar-modal" @click="cerrarNueva">✕</button>
            </div>
            <div style="padding:1.25rem;display:flex;flex-direction:column;gap:0.75rem">
              <div class="tra-form-row">
                <div class="field">
                  <label>Sede origen</label>
                  <select v-model="form.sede_origen_id" class="input-field">
                    <option v-for="s in sedes" :key="'so'+s.id" :value="s.id">{{ s.nombre }}</option>
                  </select>
                </div>
                <div class="field">
                  <label>Sede destino</label>
                  <select v-model="form.sede_destino_id" class="input-field">
                    <option v-for="s in sedes" :key="'sd'+s.id" :value="s.id">{{ s.nombre }}</option>
                  </select>
                </div>
              </div>

              <div class="field">
                <label>Agregar producto</label>
                <input v-model="busqueda" @input="buscarProductos" placeholder="Código o nombre..." class="input-field" autocomplete="off" />
                <div v-if="resultadosBusqueda.length" class="tra-autocomplete">
                  <div v-for="p in resultadosBusqueda" :key="p.id" class="tra-autocomplete-item" @click="agregarProducto(p)">
                    <span>{{ p.nombre }} <small v-if="p.codigo">[{{ p.codigo }}]</small></span>
                    <span class="tra-autocomplete-stock">stock origen: {{ p.stock }}</span>
                  </div>
                </div>
              </div>

              <div v-if="form.productos.length" class="tra-productos-form">
                <div v-for="(p, idx) in form.productos" :key="p.producto_id" class="tra-producto-form-row">
                  <span class="tra-producto-form-nombre">{{ p.nombre }}</span>
                  <input type="number" min="1" v-model.number="p.cantidad" class="input-field" style="width:90px" />
                  <button class="btn-quitar" @click="form.productos.splice(idx, 1)">✕</button>
                </div>
              </div>

              <div class="field">
                <label>Notas (opcional)</label>
                <textarea v-model="form.notas" class="input-field" rows="2"></textarea>
              </div>

              <p v-if="errorForm" style="color:#DC2626;font-size:0.85rem">{{ errorForm }}</p>
            </div>
            <div class="form-botones">
              <button class="btn-cancelar" @click="cerrarNueva">Cancelar</button>
              <button class="btn-guardar" @click="crearTransferencia" :disabled="guardando">
                {{ guardando ? 'Creando...' : 'Crear transferencia' }}
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
  name: 'Transferencias',
  data() {
    return {
      usuario:      JSON.parse(localStorage.getItem('usuario') || '{}'),
      sedes:        [],
      transferencias: [],
      cargando:     false,
      procesando:   null,
      filtros: { sede_origen_id: '', sede_destino_id: '', estado: '', fecha_inicio: '', fecha_fin: '' },
      modalNueva:   false,
      guardando:    false,
      errorForm:    '',
      busqueda:     '',
      resultadosBusqueda: [],
      form: { sede_origen_id: null, sede_destino_id: null, productos: [], notas: '' },
      _buscarTimer: null,
    }
  },
  async mounted() {
    await this.cargarSedes()
    await this.cargar()
  },
  methods: {
    async cargarSedes() {
      try {
        const res = await axios.get('/auth/contexto-sede')
        this.sedes = res.data.sedes_disponibles || []
        this.form.sede_origen_id = res.data.sede_activa || res.data.sede_id || (this.sedes[0] && this.sedes[0].id)
      } catch {}
    },
    async cargar() {
      this.cargando = true
      try {
        const params = {}
        if (this.filtros.sede_origen_id)  params.sede_origen_id  = this.filtros.sede_origen_id
        if (this.filtros.sede_destino_id) params.sede_destino_id = this.filtros.sede_destino_id
        if (this.filtros.estado)          params.estado          = this.filtros.estado
        if (this.filtros.fecha_inicio)    params.fecha_inicio    = this.filtros.fecha_inicio
        if (this.filtros.fecha_fin)       params.fecha_fin       = this.filtros.fecha_fin
        const res = await axios.get('/transferencias/', { params })
        this.transferencias = res.data
      } catch {} finally { this.cargando = false }
    },
    limpiarFiltros() {
      this.filtros = { sede_origen_id: '', sede_destino_id: '', estado: '', fecha_inicio: '', fecha_fin: '' }
      this.cargar()
    },
    abrirNueva() {
      this.form = { sede_origen_id: this.form.sede_origen_id, sede_destino_id: null, productos: [], notas: '' }
      this.busqueda = ''
      this.resultadosBusqueda = []
      this.errorForm = ''
      this.modalNueva = true
    },
    cerrarNueva() { this.modalNueva = false },
    buscarProductos() {
      clearTimeout(this._buscarTimer)
      if (this.busqueda.trim().length < 2 || !this.form.sede_origen_id) {
        this.resultadosBusqueda = []
        return
      }
      this._buscarTimer = setTimeout(async () => {
        try {
          const res = await axios.get('/productos/', {
            params: { busqueda: this.busqueda, limit: 8 },
            headers: { 'X-Sede-Id': this.form.sede_origen_id },
          })
          this.resultadosBusqueda = res.data.productos || []
        } catch { this.resultadosBusqueda = [] }
      }, 350)
    },
    agregarProducto(p) {
      if (this.form.productos.some(x => x.producto_id === p.id)) return
      this.form.productos.push({ producto_id: p.id, nombre: p.nombre, cantidad: 1, disponible: p.stock })
      this.busqueda = ''
      this.resultadosBusqueda = []
    },
    async crearTransferencia() {
      this.errorForm = ''
      if (!this.form.sede_origen_id || !this.form.sede_destino_id) {
        this.errorForm = 'Selecciona sede de origen y destino'; return
      }
      if (this.form.sede_origen_id === this.form.sede_destino_id) {
        this.errorForm = 'La sede de origen y destino no pueden ser la misma'; return
      }
      if (!this.form.productos.length) {
        this.errorForm = 'Agrega al menos un producto'; return
      }
      for (const p of this.form.productos) {
        if (!p.cantidad || p.cantidad <= 0) { this.errorForm = `Cantidad inválida para ${p.nombre}`; return }
      }
      this.guardando = true
      try {
        await axios.post('/transferencias/', {
          sede_origen_id:  this.form.sede_origen_id,
          sede_destino_id: this.form.sede_destino_id,
          productos: this.form.productos.map(p => ({ producto_id: p.producto_id, cantidad: p.cantidad })),
          notas: this.form.notas || null,
        })
        this.modalNueva = false
        await this.cargar()
      } catch (e) {
        this.errorForm = e?.response?.data?.detail || 'Error al crear la transferencia'
      } finally { this.guardando = false }
    },
    async confirmar(t) {
      if (!confirm(`¿Confirmar transferencia ${t.sede_origen_nombre} → ${t.sede_destino_nombre}? Se descontará el stock de origen.`)) return
      this.procesando = t.id
      try {
        await axios.put(`/transferencias/${t.id}/confirmar`)
        await this.cargar()
      } catch (e) { alert(e?.response?.data?.detail || 'Error al confirmar') }
      finally { this.procesando = null }
    },
    async recibir(t) {
      if (!confirm(`¿Marcar como recibida en ${t.sede_destino_nombre}? Se sumará el stock en destino.`)) return
      this.procesando = t.id
      try {
        await axios.put(`/transferencias/${t.id}/recibir`)
        await this.cargar()
      } catch (e) { alert(e?.response?.data?.detail || 'Error al recibir') }
      finally { this.procesando = null }
    },
    async cancelar(t) {
      if (!confirm(`¿Cancelar esta transferencia?${t.estado === 'en_transito' ? ' Se revertirá el descuento en origen.' : ''}`)) return
      this.procesando = t.id
      try {
        await axios.put(`/transferencias/${t.id}/cancelar`)
        await this.cargar()
      } catch (e) { alert(e?.response?.data?.detail || 'Error al cancelar') }
      finally { this.procesando = null }
    },
    labelEstado(e) {
      return { pendiente: 'Pendiente', en_transito: 'En tránsito', recibida: 'Recibida', cancelada: 'Cancelada' }[e] || e
    },
    fmtFecha(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleDateString('es-VE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    },
  },
}
</script>

<style scoped>
.tra-filtros { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
.btn-nueva { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-limpiar { background: transparent; color: var(--texto-sec); border: 1px solid var(--borde); border-radius: 6px; padding: 0.35rem 0.75rem; cursor: pointer; font-size: 0.82rem; }

.tra-lista { display: flex; flex-direction: column; gap: 1rem; }
.tra-card { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 14px; overflow: hidden; }

.tra-card-header { display: flex; justify-content: space-between; align-items: center; padding: 0.85rem 1.25rem; background: #1A1A1A; border-bottom: 1px solid var(--borde); }
.tra-header-izq { display: flex; align-items: center; gap: 0.6rem; }
.tra-ruta { font-weight: 800; font-size: 0.95rem; color: #FFCC00; }
.tra-estado-badge { font-size: 0.7rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 4px; }
.estado-pendiente   { background: #F1F5F9; color: #475569; }
.estado-en_transito { background: #FFCC00; color: #1A1A1A; }
.estado-recibida    { background: #DCFCE7; color: #15803D; }
.estado-cancelada   { background: #FEE2E2; color: #DC2626; }
.tra-header-der { display: flex; flex-direction: column; align-items: flex-end; gap: 0.1rem; }
.tra-fecha { font-size: 0.78rem; color: #D1D5DB; }
.tra-usuario { font-size: 0.72rem; color: #9CA3AF; }

.tra-card-body { padding: 1rem 1.25rem; display: flex; flex-direction: column; gap: 0.5rem; }
.tra-productos { display: flex; flex-direction: column; gap: 0.2rem; }
.tra-prod-row { font-size: 0.85rem; color: var(--texto-sec); }
.tra-notas { font-size: 0.8rem; color: var(--texto-muted); font-style: italic; margin: 0; }

.tra-card-footer { padding: 0.75rem 1.25rem; border-top: 1px solid var(--borde); display: flex; gap: 0.5rem; flex-wrap: wrap; }
.btn-confirmar    { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.45rem 1rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }
.btn-recibir      { background: #16A34A; color: #FFFFFF; border: none; padding: 0.45rem 1rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }
.btn-cancelar-tra { background: transparent; color: #DC2626; border: 1px solid #DC2626; padding: 0.45rem 1rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem; }
.btn-confirmar:disabled, .btn-recibir:disabled, .btn-cancelar-tra:disabled { opacity: 0.4; cursor: not-allowed; }

.tra-form-row { display: flex; gap: 0.75rem; }
.tra-form-row .field { flex: 1; }
.field { display: flex; flex-direction: column; gap: 0.3rem; }
.field label { font-size: 0.8rem; font-weight: 600; color: var(--texto-sec); }

.tra-autocomplete { border: 1px solid var(--borde); border-radius: 8px; margin-top: 0.3rem; max-height: 180px; overflow-y: auto; }
.tra-autocomplete-item { display: flex; justify-content: space-between; padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.85rem; border-bottom: 1px solid var(--borde); }
.tra-autocomplete-item:last-child { border-bottom: none; }
.tra-autocomplete-item:hover { background: #FFF8DC; }
.tra-autocomplete-stock { color: var(--texto-muted); font-size: 0.78rem; }

.tra-productos-form { display: flex; flex-direction: column; gap: 0.4rem; }
.tra-producto-form-row { display: flex; align-items: center; gap: 0.5rem; }
.tra-producto-form-nombre { flex: 1; font-size: 0.85rem; }
.btn-quitar { background: transparent; border: none; color: #DC2626; cursor: pointer; font-size: 0.9rem; }

.input-field { border: 1px solid var(--borde); border-radius: 6px; padding: 0.5rem 0.65rem; font-size: 0.875rem; width: 100%; box-sizing: border-box; }
.input-field:focus { outline: none; border-color: #FFCC00; }
.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; }
</style>
