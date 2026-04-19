<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Recibir mercancía</h1>
      </div>

      <div class="contenido-inner">
        <!-- Selector de orden -->
        <div class="selector-orden">
          <label>Selecciona una orden aprobada</label>
          <select v-model="ordenId" @change="cargarOrden">
            <option value="">— Seleccionar orden —</option>
            <option v-for="o in ordenesDisponibles" :key="o.id" :value="o.id">
              {{ o.numero }} — {{ o.proveedor_nombre }} (${{ o.total.toFixed(2) }})
              <span v-if="o.estado === 'recibida_parcial'"> [PARCIAL]</span>
            </option>
          </select>
        </div>

        <div v-if="orden" class="recepcion-box">
          <div class="orden-meta">
            <span>Proveedor: <strong>{{ orden.proveedor_nombre }}</strong></span>
            <span><span :class="'badge badge-' + orden.estado">{{ labelEstado(orden.estado) }}</span></span>
            <span>Total OC: <strong class="txt-verde">${{ orden.total.toFixed(2) }}</strong></span>
          </div>

          <!-- Alerta productos nuevos -->
          <div class="alerta-nuevos" v-if="productosNuevos.length > 0">
            <p class="alerta-titulo">⚠ Hay productos nuevos sin registrar en inventario</p>
            <p>Regístralos en <router-link to="/inventario">Inventario</router-link> antes de recibir, o selecciona el producto equivalente abajo.</p>
            <ul>
              <li v-for="p in productosNuevos" :key="p.id">{{ p.nombre_producto }}</li>
            </ul>
          </div>

          <!-- Líneas de recepción -->
          <h2 class="subtitulo">Productos a recibir</h2>
          <div v-for="(item, i) in items" :key="i" class="linea-recepcion">
            <div class="linea-header">
              <span class="prod-nombre">{{ item.nombre_producto }}</span>
              <span class="prod-pedido">Pedido: {{ item.cantidad_pedida }} u.</span>
              <span class="tag-nuevo" v-if="item.es_producto_nuevo">NUEVO</span>
            </div>

            <div class="field" v-if="!item.producto_id">
              <label>Vincular con producto en inventario</label>
              <div v-if="!item._busqVisible && !item.esNuevo" class="match-pendiente" style="display:flex;gap:0.5rem">
                <button class="btn-match-opcion" @click="item._busqVisible = true">🔍 Buscar</button>
                <button class="btn-match-nuevo" @click="item.esNuevo = true">✚ Nuevo</button>
              </div>
              <div v-if="item._busqVisible && !item.producto_id" style="position:relative">
                <input
                  v-model="item._busqTexto"
                  class="input-sm"
                  placeholder="Buscar producto..."
                  @input="buscarProductoItem(item)"
                  @blur="setTimeout(() => item._busqAbierta = false, 200)"
                />
                <ul v-if="item._busqAbierta && item._busqResultados.length" class="dropdown-list dropdown-sm">
                  <li v-for="prod in item._busqResultados" :key="prod.id"
                    @mousedown="item.producto_id = prod.id; item._busqVisible = false; item._busqTexto = prod.nombre">
                    {{ prod.nombre }} · Stock: {{ prod.stock }}
                  </li>
                </ul>
              </div>
              <div v-if="item.esNuevo" class="match-nuevo-tag">
                ✚ Se creará como producto nuevo
                <span class="prov-desvincular" @click="item.esNuevo = false">✕</span>
              </div>
            </div>

            <div class="linea-inputs">
              <div class="field">
                <label>Cantidad recibida</label>
                <input v-model.number="item.cantidad_recibida" type="number" min="0" step="0.01" />
              </div>
              <div class="field">
                <label>Precio real USD</label>
                <input v-model.number="item.precio_unitario_real_usd" type="number" min="0" step="0.01" />
              </div>
              <div class="field">
                <label>Subtotal</label>
                <span class="subtotal-val">${{ subtotalItem(item).toFixed(2) }}</span>
              </div>
            </div>

            <!-- Asignar ubicación (opcional) -->
            <div class="linea-ubicacion">
              <span class="ubic-toggle" @click="item._mostrarUbic = !item._mostrarUbic">
                📍 {{ item._mostrarUbic ? 'Ocultar ubicación' : 'Asignar ubicación (opcional)' }}
              </span>
              <div v-if="item._mostrarUbic" class="ubic-campos">
                <div class="field">
                  <label>Área</label>
                  <select v-model="item._area_id" @change="item._pasillo_id = ''; item._estante_id = ''">
                    <option value="">— Sin asignar —</option>
                    <option v-for="a in areas" :key="a.id" :value="a.id">{{ a.nombre }}</option>
                  </select>
                </div>
                <div class="field">
                  <label>Pasillo</label>
                  <select v-model="item._pasillo_id" @change="item._estante_id = ''" :disabled="!item._area_id">
                    <option value="">— Seleccionar —</option>
                    <option v-for="p in pasillosPorArea(item._area_id)" :key="p.id" :value="p.id">Pasillo {{ p.numero }}</option>
                  </select>
                </div>
                <div class="field">
                  <label>Estante</label>
                  <select v-model="item._estante_id" :disabled="!item._pasillo_id">
                    <option value="">— Seleccionar —</option>
                    <option v-for="e in estandesPorPasillo(item._pasillo_id)" :key="e.id" :value="e.id">Estante {{ e.numero }}</option>
                  </select>
                </div>
                <div class="field">
                  <label>Nivel</label>
                  <input v-model.number="item._nivel" type="number" min="1" placeholder="1" style="max-width:70px" />
                </div>
              </div>
            </div>

            <div class="alerta-precio" v-if="diferenciaPrecio(item) > 0.01">
              ⚠ El precio real difiere del pedido (${{ item.precio_unitario_usd.toFixed(2) }}). Se actualizará el costo del producto.
            </div>
          </div>

          <div class="field" style="max-width:400px;margin-top:1rem">
            <label>Observación</label>
            <input v-model="observacion" placeholder="Notas de la recepción..." />
          </div>

          <div class="resumen-recepcion">
            <span>Total recibido: <strong class="txt-verde">${{ totalRecibido.toFixed(2) }}</strong></span>
            <button class="btn-confirmar" @click="confirmar" :disabled="confirmando">
              {{ confirmando ? 'Procesando...' : 'Confirmar recepción' }}
            </button>
          </div>

          <p class="msg-error" v-if="error">{{ error }}</p>

          <div class="resultado-box" v-if="resultado">
            <p class="txt-verde">✓ Recepción #{{ resultado.recepcion_id }} registrada — Orden: <strong>{{ resultado.orden_estado }}</strong></p>
            <p v-for="c in resultado.cambios" :key="c" class="cambio-costo">{{ c }}</p>
            <div v-if="resultado.ubicAsignadas && resultado.ubicAsignadas.length > 0" class="ubic-resultado">
              <p class="ubic-resultado-titulo">📍 Ubicaciones asignadas:</p>
              <table class="ubic-resultado-tabla">
                <thead><tr><th>Producto</th><th>Cantidad</th><th>Ubicación</th></tr></thead>
                <tbody>
                  <tr v-for="u in resultado.ubicAsignadas" :key="u.nombre">
                    <td>{{ u.nombre }}</td>
                    <td>{{ u.cantidad }}</td>
                    <td>{{ u.ubicacion }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
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
  name: 'RecibirCompra',
  data() {
    return {
      usuario:            JSON.parse(localStorage.getItem('usuario') || '{}'),
      ordenesDisponibles: [],
      productosInventario:[],
      ordenId:            '',
      orden:              null,
      items:              [],
      observacion:        '',
      confirmando:        false,
      error:              '',
      resultado:          null,
      // Ubicaciones
      areas:    [],
      pasillos: [],
      estantes: [],
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
    productosNuevos() {
      return this.items.filter(i => i.es_producto_nuevo && !i.producto_id)
    },
    totalRecibido() {
      return this.items.reduce((s, i) => s + this.subtotalItem(i), 0)
    },
  },
  async mounted() {
    await Promise.all([this.cargarOrdenes(), this.cargarInventario(), this.cargarEstructura()])
  },
  methods: {
    async cargarOrdenes() {
      const res = await axios.get('/compras/ordenes/', { params: { estado: 'aprobada' } })
      const res2 = await axios.get('/compras/ordenes/', { params: { estado: 'recibida_parcial' } })
      this.ordenesDisponibles = [...res.data, ...res2.data]
    },
    async cargarInventario() {
      const res = await axios.get('/productos/')
      this.productosInventario = Array.isArray(res.data) ? res.data : (res.data.productos || [])
    },
    async cargarEstructura() {
      try {
        const [ra, rp, re] = await Promise.all([
          axios.get('/ubicaciones/areas'),
          axios.get('/ubicaciones/pasillos'),
          axios.get('/ubicaciones/estantes'),
        ])
        this.areas    = ra.data
        this.pasillos = rp.data
        this.estantes = re.data
      } catch { /* módulo de ubicaciones aún no disponible */ }
    },
    pasillosPorArea(areaId) {
      if (!areaId) return []
      return this.pasillos.filter(p => p.area_id === Number(areaId))
    },
    estandesPorPasillo(pasilloId) {
      if (!pasilloId) return []
      return this.estantes.filter(e => e.pasillo_id === Number(pasilloId))
    },
    async cargarOrden() {
      this.orden    = null
      this.items    = []
      this.resultado= null
      this.error    = ''
      if (!this.ordenId) return
      const res = await axios.get(`/compras/ordenes/${this.ordenId}`)
      this.orden = res.data
      this.items = res.data.detalles.map(d => ({
        detalle_orden_id:      d.id,
        nombre_producto:       d.nombre_producto,
        cantidad_pedida:       d.cantidad_pedida,
        precio_unitario_usd:   d.precio_unitario_usd,
        es_producto_nuevo:     d.es_producto_nuevo,
        producto_id:           d.producto_id || '',
        cantidad_recibida:     d.cantidad_pedida,
        precio_unitario_real_usd: d.precio_unitario_usd,
        // match inline
        esNuevo:         false,
        nombreFinal:     '',
        _busqVisible:    false,
        _busqTexto:      '',
        _busqResultados: [],
        _busqAbierta:    false,
        // ubicación
        _mostrarUbic: false,
        _area_id:     '',
        _pasillo_id:  '',
        _estante_id:  '',
        _nivel:       1,
      }))
    },
    subtotalItem(item) {
      return (Number(item.cantidad_recibida) || 0) * (Number(item.precio_unitario_real_usd) || 0)
    },
    diferenciaPrecio(item) {
      return Math.abs((Number(item.precio_unitario_real_usd) || 0) - (Number(item.precio_unitario_usd) || 0))
    },
    labelEstado(e) {
      return { borrador:'Borrador', aprobada:'Aprobada', recibida_parcial:'Parcial', cerrada:'Cerrada', anulada:'Anulada' }[e] || e
    },
    async confirmar() {
      this.error     = ''
      this.resultado = null
      this.confirmando = true
      try {
        const payload = {
          recibido_por: this.usuario.usuario || '',
          observacion:  this.observacion,
          items: this.items.map(i => ({
            detalle_orden_id:        i.detalle_orden_id,
            producto_id:             i.producto_id || null,
            cantidad_recibida:       Number(i.cantidad_recibida),
            precio_unitario_real_usd:Number(i.precio_unitario_real_usd),
          })),
        }
        const res = await axios.post(`/compras/ordenes/${this.ordenId}/recepciones/`, payload)

        // Asignar ubicaciones si el producto tiene un producto_id y se seleccionó ubicación
        const ubicAsignadas = []
        for (const i of this.items) {
          const prodId = i.producto_id || null
          if (prodId && i._area_id && i._pasillo_id && i._estante_id) {
            try {
              await axios.post('/ubicaciones/producto', {
                producto_id: Number(prodId),
                area_id:     Number(i._area_id),
                pasillo_id:  Number(i._pasillo_id),
                estante_id:  Number(i._estante_id),
                nivel:       Number(i._nivel) || 1,
                cantidad:    Number(i.cantidad_recibida) || 0,
              })
              const area = this.areas.find(a => a.id === Number(i._area_id))
              const pasillo = this.pasillos.find(p => p.id === Number(i._pasillo_id))
              const estante = this.estantes.find(e => e.id === Number(i._estante_id))
              ubicAsignadas.push({
                nombre:    i.nombre_producto,
                cantidad:  i.cantidad_recibida,
                ubicacion: `${area?.nombre || ''} / P${pasillo?.numero || ''} / E${estante?.numero || ''} / Nivel ${i._nivel || 1}`,
              })
            } catch { /* ubicación no crítica */ }
          }
        }

        const cambios = this.items
          .filter(i => this.diferenciaPrecio(i) > 0.01)
          .map(i => `Costo actualizado: ${i.nombre_producto} → $${Number(i.precio_unitario_real_usd).toFixed(2)}`)

        this.resultado = { ...res.data, cambios, ubicAsignadas }
        await this.cargarOrdenes()
        this.ordenId = ''
        this.orden   = null
        this.items   = []
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al registrar recepción'
      } finally {
        this.confirmando = false
      }
    },
    async buscarProductoItem(item) {
      const q = item._busqTexto.trim()
      if (q.length < 2) { item._busqResultados = []; item._busqAbierta = false; return }
      try {
        const { data } = await axios.get('/facturas/buscar-producto', { params: { nombre: q } })
        item._busqResultados = data
        item._busqAbierta    = data.length > 0
      } catch {}
    },
    salir() { localStorage.removeItem('usuario'); this.$router.push('/login') },
  },
}
</script>

<style scoped>
.selector-orden { max-width: 500px; margin-bottom: 2rem; }
.selector-orden label { color: var(--texto-sec); font-size: 0.85rem; display: block; margin-bottom: 0.4rem; font-weight: 600; }

.recepcion-box { max-width: 800px; }
.orden-meta { display: flex; gap: 2rem; background: #FFFFFF; padding: 1rem 1.25rem; border-radius: 10px; margin-bottom: 1.5rem; flex-wrap: wrap; align-items: center; border: 1px solid var(--borde); }
.orden-meta span { color: var(--texto-sec); font-size: 0.9rem; }
.orden-meta strong { color: var(--texto-principal); }

.alerta-nuevos { background: #DC26261A; border: 1px solid var(--danger); border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1.5rem; }
.alerta-titulo { color: var(--danger); font-weight: 600; margin: 0 0 0.4rem; }
.alerta-nuevos p { color: var(--texto-sec); font-size: 0.9rem; margin: 0 0 0.5rem; }
.alerta-nuevos a { color: var(--success); }
.alerta-nuevos ul { color: var(--danger); margin: 0; padding-left: 1.25rem; font-size: 0.9rem; }

.subtitulo { color: var(--texto-principal); font-size: 0.95rem; margin: 0 0 0.75rem; border-top: 1px solid var(--borde); padding-top: 1rem; font-weight: 700; }

.linea-recepcion { background: #FFFFFF; border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 0.75rem; border: 1px solid var(--borde); }
.linea-header { display: flex; gap: 1rem; align-items: center; margin-bottom: 0.75rem; }
.prod-nombre { color: var(--texto-principal); font-weight: 600; }
.prod-pedido { color: var(--texto-muted); font-size: 0.85rem; }
.tag-nuevo { background: #FFCC0022; color: #996600; border-radius: 4px; font-size: 0.72rem; padding: 0.15rem 0.5rem; font-weight: 700; }

.linea-inputs { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; }
.subtotal-val { color: #16A34A; font-size: 1rem; font-weight: 600; padding-top: 0.3rem; display: block; }

.alerta-precio { background: #FFCC0022; border: 1px solid #FFCC00; border-radius: 6px; padding: 0.5rem 0.75rem; margin-top: 0.5rem; color: #996600; font-size: 0.85rem; }

.resumen-recepcion { display: flex; justify-content: space-between; align-items: center; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--borde); }
.resumen-recepcion span { color: var(--texto-sec); font-size: 0.95rem; }

.btn-confirmar { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.7rem 2rem; border-radius: 8px; cursor: pointer; font-size: 1rem; font-weight: 700; }
.btn-confirmar:disabled { opacity: 0.5; cursor: not-allowed; }

.resultado-box { background: #16A34A1A; border: 1px solid var(--success); border-radius: 10px; padding: 1rem 1.25rem; margin-top: 1rem; }
.resultado-box p { margin: 0.25rem 0; font-size: 0.9rem; }
.cambio-costo { color: #996600; }

.linea-ubicacion { margin-top: 0.6rem; }
.ubic-toggle { font-size: 0.82rem; color: var(--texto-sec); cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
.ubic-toggle:hover { color: var(--texto-principal); }
.ubic-campos { display: grid; grid-template-columns: 1fr 1fr 1fr 80px; gap: 0.75rem; margin-top: 0.5rem; }

.ubic-resultado { margin-top: 0.75rem; }
.ubic-resultado-titulo { color: #16A34A; font-weight: 700; font-size: 0.88rem; margin: 0 0 0.4rem; }
.ubic-resultado-tabla { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.ubic-resultado-tabla th { text-align: left; padding: 0.3rem 0.6rem; color: var(--texto-muted); font-weight: 700; border-bottom: 1px solid #16A34A44; }
.ubic-resultado-tabla td { padding: 0.3rem 0.6rem; color: var(--texto-principal); border-bottom: 1px solid #16A34A22; }
</style>
