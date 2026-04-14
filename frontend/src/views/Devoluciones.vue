<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Devoluciones</h1>
      </div>

      <div class="contenido-inner">

        <!-- Tabs -->
        <div class="tabs">
          <button :class="['tab', tab === 'cliente' ? 'tab-activo' : '']" @click="tab = 'cliente'; cargar()">
            Devoluciones de clientes
          </button>
          <button :class="['tab', tab === 'proveedor' ? 'tab-activo' : '']" @click="tab = 'proveedor'; cargar()">
            Devoluciones a proveedores
          </button>
        </div>

        <!-- ═══════════════════════════════ TAB CLIENTES ═══════════════════════════════ -->
        <div v-if="tab === 'cliente'">

          <!-- Formulario registro -->
          <div class="card-form" v-if="esAdmin || tienePermiso('devoluciones')">
            <h3 class="seccion-titulo">Registrar devolución de cliente</h3>

            <div class="grid-form">
              <div class="field">
                <label>ID de la venta *</label>
                <div class="busq-row">
                  <input v-model.number="devCli.venta_id" type="number" placeholder="Ej: 123" />
                  <button class="btn-buscar" @click="cargarVenta">Buscar</button>
                </div>
              </div>
              <div class="field" v-if="ventaInfo">
                <label>Cliente</label>
                <input :value="ventaInfo.cliente || '—'" disabled />
              </div>
            </div>

            <!-- Productos de la venta -->
            <div v-if="ventaInfo" class="productos-devolver">
              <h4 class="sub-titulo">Selecciona productos a devolver</h4>
              <div v-for="(item, i) in ventaInfo.productos" :key="i" class="prod-devolucion">
                <label class="check-label">
                  <input type="checkbox" v-model="item.seleccionado" />
                  <span>{{ item.nombre }} — ${{ item.precio_unitario.toFixed(2) }}</span>
                </label>
                <div v-if="item.seleccionado" class="prod-opciones">
                  <div class="inp-group">
                    <label>Cantidad</label>
                    <input type="number" v-model.number="item.cant_devolver" min="1" :max="item.cantidad" class="inp-sm" />
                  </div>
                  <div class="inp-group">
                    <label>¿Vuelve al inventario?</label>
                    <select v-model="item.vuelve_inventario" class="sel-sm">
                      <option :value="true">Sí</option>
                      <option :value="false">No</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div class="grid-form" v-if="ventaInfo">
              <div class="field">
                <label>Tipo resolución *</label>
                <select v-model="devCli.tipo_resolucion">
                  <option value="dinero">Devolver dinero</option>
                  <option value="credito">Crédito para próxima compra</option>
                </select>
              </div>
              <div class="field full">
                <label>Motivo *</label>
                <input v-model="devCli.motivo" placeholder="Describe el motivo de la devolución..." />
              </div>
              <div class="field full">
                <label>Observación</label>
                <input v-model="devCli.observacion" placeholder="Opcional..." />
              </div>
            </div>

            <div class="form-botones" v-if="ventaInfo">
              <button class="btn-guardar" @click="registrarDevCli">Registrar devolución</button>
            </div>
          </div>

          <!-- Tabla historial -->
          <div class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th><th>Venta</th><th>Cliente</th>
                  <th>Monto</th><th>Tipo</th><th>Motivo</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in devolucionesCliente" :key="d.id">
                  <td>{{ formatFecha(d.fecha) }}</td>
                  <td>#{{ d.venta_id }}</td>
                  <td>{{ d.cliente_nombre || '—' }}</td>
                  <td class="txt-verde">${{ d.monto_total.toFixed(2) }}</td>
                  <td><span :class="['badge-tipo', d.tipo_resolucion === 'credito' ? 'badge-credito' : 'badge-dinero']">{{ d.tipo_resolucion === 'credito' ? 'Crédito' : 'Dinero' }}</span></td>
                  <td class="txt-muted">{{ d.motivo }}</td>
                </tr>
                <tr v-if="devolucionesCliente.length === 0">
                  <td colspan="6" class="sin-datos">Sin devoluciones registradas</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- ═══════════════════════════════ TAB PROVEEDOR ═══════════════════════════════ -->
        <div v-if="tab === 'proveedor'">

          <!-- Formulario -->
          <div class="card-form" v-if="esAdmin || tienePermiso('devoluciones')">
            <h3 class="seccion-titulo">Registrar devolución a proveedor</h3>

            <div class="grid-form">
              <div class="field">
                <label>Proveedor *</label>
                <select v-model="devProv.proveedor_id" @change="cargarProductosProveedor">
                  <option value="">— Seleccionar —</option>
                  <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                </select>
              </div>
              <div class="field">
                <label>Producto *</label>
                <select v-model="devProv.producto_id" @change="seleccionarProductoProv">
                  <option value="">— Seleccionar —</option>
                  <option v-for="p in productosProveedor" :key="p.id" :value="p.id">{{ p.nombre }} (stock: {{ p.stock }})</option>
                </select>
              </div>
              <div class="field">
                <label>Cantidad *</label>
                <input type="number" v-model.number="devProv.cantidad" min="1" />
              </div>
              <div class="field">
                <label>Costo unitario USD *</label>
                <input type="number" v-model.number="devProv.costo_unitario" min="0" step="0.01" />
              </div>
              <div class="field">
                <label>Tipo resolución *</label>
                <select v-model="devProv.tipo_resolucion">
                  <option value="descuento_factura">Descontar de factura pendiente</option>
                  <option value="credito">Crédito a favor</option>
                </select>
              </div>
              <div class="field full">
                <label>Motivo *</label>
                <input v-model="devProv.motivo" placeholder="Describe el motivo..." />
              </div>
              <div class="field full">
                <label>Observación</label>
                <input v-model="devProv.observacion" placeholder="Opcional..." />
              </div>
            </div>

            <div class="monto-preview" v-if="devProv.cantidad && devProv.costo_unitario">
              Monto total: <strong>${{ (devProv.cantidad * devProv.costo_unitario).toFixed(2) }}</strong>
            </div>

            <div class="form-botones">
              <button class="btn-guardar" @click="registrarDevProv">Registrar devolución</button>
            </div>
          </div>

          <!-- Pendientes por resolver -->
          <div v-if="pendientes.length" class="alerta-pendientes">
            <strong>{{ pendientes.length }} devolución(es) pendiente(s) de resolver</strong>
          </div>

          <!-- Tabla -->
          <div class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th><th>Proveedor</th><th>Producto</th>
                  <th>Cant.</th><th>Monto</th><th>Resolución</th>
                  <th>Estado</th><th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in devolucionesProveedor" :key="d.id">
                  <td>{{ formatFecha(d.fecha) }}</td>
                  <td>{{ d.proveedor_nombre }}</td>
                  <td>{{ d.nombre_producto }}</td>
                  <td>{{ d.cantidad }}</td>
                  <td class="txt-verde">${{ d.monto_total.toFixed(2) }}</td>
                  <td class="txt-muted">{{ d.tipo_resolucion === 'credito' ? 'Crédito' : 'Desc. factura' }}</td>
                  <td>
                    <span :class="['badge-tipo', d.estado === 'resuelto' ? 'badge-resuelto' : 'badge-pendiente-dev']">
                      {{ d.estado }}
                    </span>
                  </td>
                  <td>
                    <button v-if="d.estado === 'pendiente' && esAdmin" class="btn-resolver"
                      @click="resolver(d.id)">Resolver</button>
                  </td>
                </tr>
                <tr v-if="devolucionesProveedor.length === 0">
                  <td colspan="8" class="sin-datos">Sin devoluciones registradas</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

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
  name: 'Devoluciones',
  data() {
    return {
      usuario:              JSON.parse(localStorage.getItem('usuario') || '{}'),
      tab:                  'cliente',
      devolucionesCliente:  [],
      devolucionesProveedor:[],
      pendientes:           [],
      proveedores:          [],
      productosProveedor:   [],
      ventaInfo:            null,
      error:                '',
      devCli: {
        venta_id:        null,
        tipo_resolucion: 'dinero',
        motivo:          '',
        observacion:     '',
      },
      devProv: {
        proveedor_id:   '',
        producto_id:    '',
        nombre_producto:'',
        cantidad:       1,
        costo_unitario: 0,
        tipo_resolucion:'credito',
        motivo:         '',
        observacion:    '',
      },
    }
  },
  computed: {
    esAdmin()      { return this.usuario.rol === 'admin' },
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
    await this.cargar()
    await this.cargarProveedores()
  },
  methods: {
    async cargar() {
      try {
        if (this.tab === 'cliente') {
          const res = await axios.get('/devoluciones/cliente/')
          this.devolucionesCliente = res.data
        } else {
          const [res, resPend] = await Promise.all([
            axios.get('/devoluciones/proveedor/'),
            axios.get('/devoluciones/proveedor/pendientes/'),
          ])
          this.devolucionesProveedor = res.data
          this.pendientes            = resPend.data
        }
      } catch (e) {
        this.error = 'Error al cargar devoluciones'
      }
    },

    async cargarProveedores() {
      const res = await axios.get('/compras/proveedores/')
      this.proveedores = res.data
    },

    async cargarProductosProveedor() {
      if (!this.devProv.proveedor_id) { this.productosProveedor = []; return }
      const res = await axios.get('/productos/', { params: { proveedor_id: this.devProv.proveedor_id } })
      this.productosProveedor = res.data
    },

    seleccionarProductoProv() {
      const prod = this.productosProveedor.find(p => p.id === this.devProv.producto_id)
      if (prod) {
        this.devProv.nombre_producto = prod.nombre
        this.devProv.costo_unitario  = parseFloat(prod.costo_usd || 0)
      }
    },

    async cargarVenta() {
      if (!this.devCli.venta_id) return
      try {
        const res = await axios.get(`/ventas/${this.devCli.venta_id}`)
        const v   = res.data
        this.ventaInfo = {
          id:       v.id,
          cliente:  v.cliente_nombre || null,
          cliente_id: v.cliente_id   || null,
          productos: (v.productos || []).map(p => ({
            producto_id:     p.producto_id,
            nombre:          p.nombre,
            precio_unitario: parseFloat(p.precio_unitario || 0),
            cantidad:        parseInt(p.cantidad || 0),
            seleccionado:    false,
            cant_devolver:   1,
            vuelve_inventario: true,
          })),
        }
      } catch (e) {
        alert(e?.response?.data?.detail || 'Venta no encontrada')
        this.ventaInfo = null
      }
    },

    async registrarDevCli() {
      this.error = ''
      if (!this.devCli.motivo) { alert('El motivo es obligatorio'); return }
      const seleccionados = (this.ventaInfo?.productos || []).filter(p => p.seleccionado)
      if (!seleccionados.length) { alert('Selecciona al menos un producto'); return }

      const payload = {
        venta_id:        this.devCli.venta_id,
        cliente_id:      this.ventaInfo.cliente_id,
        usuario:         this.usuario.usuario || 'admin',
        motivo:          this.devCli.motivo,
        tipo_resolucion: this.devCli.tipo_resolucion,
        observacion:     this.devCli.observacion,
        productos: seleccionados.map(p => ({
          producto_id:       p.producto_id,
          nombre_producto:   p.nombre,
          cantidad:          p.cant_devolver,
          precio_unitario:   p.precio_unitario,
          vuelve_inventario: p.vuelve_inventario,
        })),
      }

      try {
        await axios.post('/devoluciones/cliente/', payload)
        this.ventaInfo = null
        this.devCli    = { venta_id: null, tipo_resolucion: 'dinero', motivo: '', observacion: '' }
        await this.cargar()
        alert('Devolución registrada correctamente')
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al registrar'
      }
    },

    async registrarDevProv() {
      this.error = ''
      if (!this.devProv.proveedor_id || !this.devProv.producto_id) { alert('Selecciona proveedor y producto'); return }
      if (!this.devProv.motivo) { alert('El motivo es obligatorio'); return }
      try {
        await axios.post('/devoluciones/proveedor/', {
          ...this.devProv,
          usuario: this.usuario.usuario || 'admin',
        })
        this.devProv = { proveedor_id: '', producto_id: '', nombre_producto: '', cantidad: 1, costo_unitario: 0, tipo_resolucion: 'credito', motivo: '', observacion: '' }
        this.productosProveedor = []
        await this.cargar()
        alert('Devolución a proveedor registrada')
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al registrar'
      }
    },

    async resolver(id) {
      if (!confirm('¿Marcar esta devolución como resuelta?')) return
      try {
        await axios.put(`/devoluciones/proveedor/${id}/resolver`)
        await this.cargar()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error')
      }
    },

    formatFecha(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleDateString('es-VE')
    },
    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    },
  },
}
</script>

<style scoped>
/* Tabs */
.tabs      { display: flex; gap: 0; margin-bottom: 1.5rem; border-bottom: 2px solid var(--borde); }
.tab       { background: transparent; border: none; border-bottom: 2px solid transparent; padding: 0.6rem 1.2rem; cursor: pointer; font-size: 0.9rem; color: var(--texto-muted); margin-bottom: -2px; transition: all 0.15s; }
.tab-activo{ color: #1A1A1A; border-bottom-color: #FFCC00; font-weight: 700; }

/* Form card */
.card-form  { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; }

/* Buscar venta */
.busq-row   { display: flex; gap: 0.5rem; }
.busq-row input { flex: 1; padding: 0.4rem 0.75rem; border: 1px solid var(--borde); border-radius: 6px; font-size: 0.88rem; }
.btn-buscar { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.4rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }

/* Productos a devolver */
.productos-devolver { margin: 1rem 0; display: flex; flex-direction: column; gap: 0.75rem; }
.sub-titulo   { font-size: 0.85rem; font-weight: 600; color: var(--texto-sec); margin: 0 0 0.5rem; }
.prod-devolucion { background: #FAFAF7; border: 1px solid var(--borde); border-radius: 8px; padding: 0.75rem 1rem; }
.check-label  { display: flex; align-items: center; gap: 0.5rem; font-size: 0.88rem; cursor: pointer; }
.prod-opciones{ display: flex; gap: 1.5rem; margin-top: 0.5rem; }
.inp-group    { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.8rem; color: var(--texto-muted); }
.inp-sm       { width: 70px; padding: 0.25rem 0.4rem; border: 1px solid var(--borde); border-radius: 4px; font-size: 0.85rem; }
.sel-sm       { padding: 0.25rem 0.4rem; border: 1px solid var(--borde); border-radius: 4px; font-size: 0.85rem; }

/* Monto preview */
.monto-preview { background: #FFCC0022; border: 1px solid #FFCC00; border-radius: 6px; padding: 0.5rem 1rem; font-size: 0.88rem; color: #1A1A1A; margin: 0.75rem 0; }

/* Pendientes alerta */
.alerta-pendientes { background: #FFCC0022; border-left: 4px solid #FFCC00; padding: 0.6rem 1rem; border-radius: 4px; font-size: 0.88rem; margin-bottom: 1rem; }

/* Badges */
.badge-tipo          { display: inline-block; padding: 0.18rem 0.55rem; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }
.badge-dinero        { background: #2563EB1A; color: #2563EB; }
.badge-credito       { background: #16A34A1A; color: #16A34A; }
.badge-resuelto      { background: #16A34A1A; color: #16A34A; }
.badge-pendiente-dev { background: #FFCC0033; color: #996600; }

/* Resolver btn */
.btn-resolver { background: #16A34A; color: white; border: none; padding: 0.25rem 0.65rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }

.txt-muted { color: var(--texto-muted); font-size: 0.85rem; }
</style>
