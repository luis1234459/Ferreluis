<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Órdenes de compra</h1>
        <button class="btn-nuevo" @click="abrirNueva">+ Nueva orden</button>
      </div>

      <div class="contenido-inner">
        <!-- Filtros -->
        <div class="filtros">
          <select v-model="filtroEstado" @change="cargar">
            <option value="">Todos los estados</option>
            <option value="borrador">Borrador</option>
            <option value="aprobada">Aprobada</option>
            <option value="recibida_parcial">Recibida parcial</option>
            <option value="cerrada">Cerrada</option>
            <option value="anulada">Anulada</option>
          </select>
          <select v-model="filtroProveedor" @change="cargar">
            <option value="">Todos los proveedores</option>
            <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
          </select>
        </div>

        <!-- Tabla de órdenes -->
        <div class="tabla-container">
          <table>
            <thead>
              <tr>
                <th>Nro.</th>
                <th>Proveedor</th>
                <th>Fecha</th>
                <th>Esperada</th>
                <th>Total</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="o in ordenes" :key="o.id">
                <td style="font-weight:700">{{ o.numero }}</td>
                <td>{{ o.proveedor_nombre }}</td>
                <td>{{ formatFecha(o.fecha_creacion) }}</td>
                <td>{{ o.fecha_esperada ? formatFecha(o.fecha_esperada) : '—' }}</td>
                <td class="txt-verde">${{ o.total.toFixed(2) }}</td>
                <td><span :class="'badge badge-' + o.estado">{{ labelEstado(o.estado) }}</span></td>
                <td class="acciones">
                  <button class="btn-ver" @click="verDetalle(o)">Ver</button>
                  <button v-if="o.estado === 'borrador'" class="btn-editar" @click="editarOrden(o)">Editar</button>
                  <button v-if="o.estado === 'borrador' && esAdmin" class="btn-aprobar" @click="aprobar(o.id)">Aprobar</button>
                  <button v-if="['borrador','aprobada'].includes(o.estado)" class="btn-anular" @click="anular(o.id)">Anular</button>
                </td>
              </tr>
              <tr v-if="ordenes.length === 0">
                <td colspan="7" class="sin-datos">No hay órdenes</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Modal detalle -->
        <div class="overlay" v-if="ordenDetalle" @click.self="ordenDetalle = null">
          <div class="modal">
            <div class="modal-header">
              <h2>{{ ordenDetalle.numero }}</h2>
              <span :class="'badge badge-' + ordenDetalle.estado">{{ labelEstado(ordenDetalle.estado) }}</span>
              <button class="btn-cerrar-modal" @click="ordenDetalle = null">✕</button>
            </div>
            <p class="detalle-meta">
              Proveedor: <strong>{{ ordenDetalle.proveedor_nombre }}</strong> ·
              Creado por: <strong>{{ ordenDetalle.creado_por }}</strong>
            </p>
            <table class="tabla-detalle">
              <thead><tr><th>Producto</th><th>Cant.</th><th>P. unitario</th><th>Subtotal</th></tr></thead>
              <tbody>
                <tr v-for="d in ordenDetalle.detalles" :key="d.id" :class="{ 'nuevo-prod': d.es_producto_nuevo }">
                  <td>{{ d.nombre_producto }} <span v-if="d.es_producto_nuevo" class="tag-nuevo">NUEVO</span></td>
                  <td>{{ d.cantidad_pedida }}</td>
                  <td>${{ d.precio_unitario_usd.toFixed(2) }}</td>
                  <td>${{ d.subtotal.toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
            <div class="modal-totales">
              <span>Subtotal: <strong>${{ ordenDetalle.subtotal.toFixed(2) }}</strong></span>
              <span v-if="ordenDetalle.descuento > 0">Desc.: <strong>-${{ ordenDetalle.descuento.toFixed(2) }}</strong></span>
              <span class="total-grande">Total: <strong>${{ ordenDetalle.total.toFixed(2) }}</strong></span>
            </div>
            <p v-if="ordenDetalle.observacion" class="obs">{{ ordenDetalle.observacion }}</p>
          </div>
        </div>

        <!-- Modal nueva/editar orden -->
        <div class="overlay" v-if="mostrarForm" @click.self="cerrarForm">
          <div class="modal modal-form">
            <div class="modal-header">
              <h2>{{ editandoId ? 'Editar orden' : 'Nueva orden de compra' }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarForm">✕</button>
            </div>

            <div class="form-grid">
              <div class="field">
                <label>Proveedor</label>
                <select v-model="form.proveedor_id">
                  <option value="">— Selecciona —</option>
                  <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                </select>
              </div>
              <div class="field">
                <label>Fecha esperada</label>
                <input type="date" v-model="form.fecha_esperada" />
              </div>
              <div class="field field-wide">
                <label>Observación</label>
                <input v-model="form.observacion" placeholder="Notas u observaciones" />
              </div>
            </div>

            <h3 class="subtitulo">Productos</h3>

            <!-- Filtros de búsqueda de producto -->
            <div class="filtros-producto-oc">
              <input v-model="filtroBusquedaOC" class="filtro-busq-oc" placeholder="🔍 Buscar producto o código..." />
              <select v-model="filtroDeptoOC" class="filtro-sel-oc">
                <option value="">Todos los departamentos</option>
                <option v-for="d in departamentos" :key="d.id" :value="d.id">{{ d.nombre }}</option>
              </select>
              <select v-model="filtroProveedorOC" class="filtro-sel-oc">
                <option value="">Todos los proveedores</option>
                <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
              </select>
              <span class="filtro-contador">{{ opcionesFiltradas.length }} opciones</span>
            </div>

            <!-- Cabecera tabla de líneas -->
            <div class="lineas-head">
              <span>Producto / Variante</span>
              <span>Nombre</span>
              <span class="tc">Cant.</span>
              <span class="tc">Precio $</span>
              <span class="tr">Subtotal</span>
              <span></span>
            </div>
            <!-- Filas de líneas (scrollable) -->
            <div class="lineas-scroll">
              <div v-for="(linea, i) in form.detalles" :key="i" class="fila-linea">
                <select v-model="linea._key" @change="llenarDesdeInventario(linea)">
                  <option value="">— Nuevo producto —</option>
                  <option v-for="op in opcionesFiltradas" :key="op.key" :value="op.key">
                    {{ op.label }}{{ op.stock_label }}
                  </option>
                </select>
                <input v-model="linea.nombre_producto" placeholder="Nombre del producto" :disabled="!!linea._key" />
                <input v-model.number="linea.cantidad_pedida" type="number" min="1" class="tc" />
                <input v-model.number="linea.precio_unitario_usd" type="number" min="0" step="0.01" class="tc" />
                <span class="fila-sub">${{ subtotalLinea(linea).toFixed(2) }}</span>
                <button class="btn-del-fila" @click="quitarLinea(i)" title="Quitar">✕</button>
              </div>
              <div v-if="form.detalles.length === 0" class="fila-vacia">Sin productos — agrega uno abajo</div>
            </div>
            <button class="btn-agregar-linea" @click="agregarLinea">+ Agregar producto</button>

            <div class="form-footer">
              <div class="totales-form">
                <span>Total: <strong class="txt-verde">${{ totalForm.toFixed(2) }}</strong></span>
              </div>
              <div class="form-botones">
                <button class="btn-cancelar" @click="cerrarForm">Cancelar</button>
                <button class="btn-guardar" @click="guardar" :disabled="guardando">
                  {{ guardando ? 'Guardando...' : (editandoId ? 'Actualizar' : 'Crear orden') }}
                </button>
              </div>
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
  name: 'OrdenesCompra',
  data() {
    return {
      usuario:            JSON.parse(localStorage.getItem('usuario') || '{}'),
      ordenes:            [],
      proveedores:        [],
      productosRaw:       [],
      departamentos:      [],
      filtroEstado:       '',
      filtroProveedor:    '',
      filtroDeptoOC:      '',
      filtroProveedorOC:  '',
      filtroBusquedaOC:   '',
      ordenDetalle:       null,
      mostrarForm:        false,
      editandoId:         null,
      guardando:          false,
      error:              '',
      form: {
        proveedor_id:   '',
        fecha_esperada: '',
        observacion:    '',
        detalles:       [],
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
    totalForm() {
      return this.form.detalles.reduce((s, l) => s + this.subtotalLinea(l), 0)
    },
    opcionesProductos() {
      const lista = []
      for (const p of this.productosRaw) {
        const variantes = (p.variantes_resumen || []).filter(v => v.activo)
        if (variantes.length > 0) {
          for (const v of variantes) {
            const costo = v.costo_usd != null ? v.costo_usd : (p.costo_usd || 0)
            const base  = v.color
              ? `${p.nombre} (${v.clase} / ${v.color})`
              : `${p.nombre} (${v.clase})`
            const label = v.codigo ? `[${v.codigo}] ${base}` : base
            lista.push({
              key:            `${p.id}_${v.id}`,
              producto_id:    p.id,
              variante_id:    v.id,
              departamento_id:p.departamento_id || null,
              proveedor_id:   p.proveedor_id    || null,
              label,
              labelBusq:      label.toLowerCase(),
              costo,
              stock:          v.stock || 0,
              stock_label:    v.stock < 5 ? ` · ⚠ stock:${v.stock}` : ` · stock:${v.stock}`,
            })
          }
        } else {
          lista.push({
            key:            `${p.id}`,
            producto_id:    p.id,
            variante_id:    null,
            departamento_id:p.departamento_id || null,
            proveedor_id:   p.proveedor_id    || null,
            label:          p.nombre,
            labelBusq:      p.nombre.toLowerCase(),
            costo:          p.costo_usd || 0,
            stock:          p.stock || 0,
            stock_label:    (p.stock || 0) < 5 ? ` · ⚠ stock:${p.stock}` : ` · stock:${p.stock}`,
          })
        }
      }
      return lista.sort((a, b) => a.label.localeCompare(b.label))
    },
    opcionesFiltradas() {
      let lista = this.opcionesProductos
      if (this.filtroDeptoOC) {
        const id = parseInt(this.filtroDeptoOC)
        lista = lista.filter(o => o.departamento_id === id)
      }
      if (this.filtroProveedorOC) {
        const id = parseInt(this.filtroProveedorOC)
        lista = lista.filter(o => o.proveedor_id === id)
      }
      if (this.filtroBusquedaOC.trim()) {
        const q = this.filtroBusquedaOC.trim().toLowerCase()
        lista = lista.filter(o => o.labelBusq.includes(q))
      }
      return lista
    },
  },
  async mounted() {
    await Promise.all([this.cargar(), this.cargarProveedores(), this.cargarInventario(), this.cargarDepartamentos()])
  },
  methods: {
    async cargar() {
      const params = {}
      if (this.filtroEstado)    params.estado       = this.filtroEstado
      if (this.filtroProveedor) params.proveedor_id = this.filtroProveedor
      const res = await axios.get('/compras/ordenes/', { params })
      this.ordenes = res.data
    },
    async cargarProveedores() {
      const res = await axios.get('/compras/proveedores/')
      this.proveedores = res.data
    },
    async cargarInventario() {
      const res = await axios.get('/productos/', { params: { limit: 9999, incluir_inactivos: false } })
      this.productosRaw = Array.isArray(res.data) ? res.data : (res.data.productos || [])
    },
    async cargarDepartamentos() {
      try {
        const res = await axios.get('/productos/departamentos')
        this.departamentos = res.data
      } catch {}
    },
    _lineaVacia() {
      return { _key: '', producto_id: null, variante_id: null, nombre_producto: '', cantidad_pedida: 1, precio_unitario_usd: 0, es_producto_nuevo: false }
    },
    abrirNueva() {
      this.editandoId = null
      this.form = { proveedor_id: '', fecha_esperada: '', observacion: '', detalles: [] }
      this.filtroDeptoOC = ''; this.filtroProveedorOC = ''; this.filtroBusquedaOC = ''
      this.agregarLinea()
      this.mostrarForm = true
    },
    editarOrden(o) {
      this.editandoId = o.id
      this.filtroDeptoOC = ''; this.filtroProveedorOC = ''; this.filtroBusquedaOC = ''
      this.form = {
        proveedor_id:   o.proveedor_id,
        fecha_esperada: o.fecha_esperada ? o.fecha_esperada.split('T')[0] : '',
        observacion:    o.observacion || '',
        detalles: o.detalles.map(d => ({
          _key:               d.variante_id ? `${d.producto_id}_${d.variante_id}` : (d.producto_id ? `${d.producto_id}` : ''),
          producto_id:        d.producto_id  || null,
          variante_id:        d.variante_id  || null,
          nombre_producto:    d.nombre_producto,
          cantidad_pedida:    d.cantidad_pedida,
          precio_unitario_usd:d.precio_unitario_usd,
          es_producto_nuevo:  d.es_producto_nuevo,
        })),
      }
      this.mostrarForm = true
    },
    cerrarForm() { this.mostrarForm = false; this.error = '' },
    agregarLinea() { this.form.detalles.push(this._lineaVacia()) },
    quitarLinea(i) { this.form.detalles.splice(i, 1) },
    llenarDesdeInventario(linea) {
      if (!linea._key) {
        linea.producto_id = null
        linea.variante_id = null
        linea.nombre_producto = ''
        linea.es_producto_nuevo = true
        return
      }
      const op = this.opcionesProductos.find(o => o.key === linea._key)
      if (op) {
        linea.producto_id        = op.producto_id
        linea.variante_id        = op.variante_id
        linea.nombre_producto    = op.label
        linea.precio_unitario_usd= op.costo
        linea.es_producto_nuevo  = false
      }
    },
    subtotalLinea(l) {
      return (Number(l.cantidad_pedida) || 0) * (Number(l.precio_unitario_usd) || 0)
    },
    async guardar() {
      if (!this.form.proveedor_id) { this.error = 'Selecciona un proveedor'; return }
      if (!this.form.detalles.length) { this.error = 'Agrega al menos un producto'; return }
      this.guardando = true
      this.error = ''
      try {
        const payload = {
          ...this.form,
          creado_por: this.usuario.usuario || '',
          detalles: this.form.detalles.map(l => ({
            producto_id:         l.producto_id  || null,
            variante_id:         l.variante_id  || null,
            nombre_producto:     l.nombre_producto,
            cantidad_pedida:     l.cantidad_pedida,
            precio_unitario_usd: l.precio_unitario_usd,
            es_producto_nuevo:   !l.producto_id,
          })),
        }
        if (this.editandoId) {
          await axios.put(`/compras/ordenes/${this.editandoId}`, payload)
        } else {
          await axios.post('/compras/ordenes/', payload)
        }
        await this.cargar()
        this.cerrarForm()
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al guardar'
      } finally {
        this.guardando = false
      }
    },
    async aprobar(id) {
      if (!confirm('¿Aprobar esta orden?')) return
      try {
        await axios.post(`/compras/ordenes/${id}/aprobar`, { aprobado_por: this.usuario.usuario })
        await this.cargar()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al aprobar')
      }
    },
    async anular(id) {
      if (!confirm('¿Anular esta orden?')) return
      try {
        await axios.post(`/compras/ordenes/${id}/anular`)
        await this.cargar()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al anular')
      }
    },
    verDetalle(o) { this.ordenDetalle = o },
    labelEstado(e) {
      return { borrador:'Borrador', aprobada:'Aprobada', recibida_parcial:'Parcial', cerrada:'Cerrada', anulada:'Anulada' }[e] || e
    },
    formatFecha(iso) { return iso ? new Date(iso).toLocaleDateString('es-VE') : '—' },
    salir() { localStorage.removeItem('usuario'); this.$router.push('/login') },
  },
}
</script>

<style scoped>
.acciones { display: flex; gap: 0.35rem; }
.btn-ver    { background: var(--fondo-sidebar); color: var(--texto-sec); border: 1px solid var(--borde); padding: 0.28rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
.btn-editar { background: var(--info); color: white; border: none; padding: 0.28rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
.btn-aprobar{ background: var(--success); color: white; border: none; padding: 0.28rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
.btn-anular { background: var(--danger); color: white; border: none; padding: 0.28rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }

.detalle-meta { color: var(--texto-sec); font-size: 0.9rem; margin: -0.5rem 0 1rem; }
.detalle-meta strong { color: var(--texto-principal); }
.tabla-detalle { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
.nuevo-prod td { color: #996600; }
.tag-nuevo { background: #FFCC0022; color: #996600; border-radius: 4px; font-size: 0.72rem; padding: 0.1rem 0.4rem; margin-left: 0.4rem; }
.modal-totales { display: flex; gap: 1.5rem; justify-content: flex-end; flex-wrap: wrap; }
.modal-totales span { color: var(--texto-sec); font-size: 0.9rem; }
.modal-totales strong { color: var(--texto-principal); }
.total-grande strong { color: #16A34A; font-size: 1.1rem; }
.obs { color: var(--texto-sec); font-size: 0.88rem; font-style: italic; margin-top: 0.75rem; }

/* ── modal form ancho ── */
.modal-form { max-width: 1080px !important; width: 96vw !important; padding: 1.5rem !important; }

.subtitulo { color: var(--texto-principal); font-size: 0.88rem; margin: 1rem 0 0.4rem; border-top: 1px solid var(--borde); padding-top: 0.75rem; font-weight: 700; }
.filtros-producto-oc { display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.4rem; }
.filtro-busq-oc { flex: 1; min-width: 140px; padding: 0.3rem 0.5rem; border: 1px solid var(--borde); border-radius: 5px; background: var(--fondo-tabla-alt); color: var(--texto-principal); font-size: 0.82rem; height: 30px; }
.filtro-sel-oc  { padding: 0.3rem 0.5rem; border: 1px solid var(--borde); border-radius: 5px; background: var(--fondo-tabla-alt); color: var(--texto-principal); font-size: 0.82rem; max-width: 160px; height: 30px; }
.filtro-contador { font-size: 0.75rem; color: var(--texto-sec); white-space: nowrap; }

/* ── tabla de líneas ── */
.lineas-head,
.fila-linea {
  display: grid;
  grid-template-columns: 3fr 2fr 72px 100px 88px 26px;
  gap: 4px;
  align-items: center;
  padding: 0 0.4rem;
}
.lineas-head {
  height: 28px;
  background: var(--fondo-sidebar);
  border: 1px solid var(--borde);
  border-radius: 6px 6px 0 0;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--texto-sec);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.lineas-head .tc { text-align: center; }
.lineas-head .tr { text-align: right; }
.lineas-scroll {
  border: 1px solid var(--borde);
  border-top: none;
  border-radius: 0 0 6px 6px;
  max-height: 510px;
  overflow-y: auto;
}
.fila-linea {
  height: 34px;
  border-bottom: 1px solid var(--borde);
}
.fila-linea:last-child { border-bottom: none; }
.fila-linea:nth-child(even) { background: var(--fondo-tabla-alt); }
.fila-linea select,
.fila-linea input {
  width: 100%; height: 26px; padding: 0 0.35rem;
  border: 1px solid transparent; border-radius: 4px;
  background: transparent; color: var(--texto-principal);
  font-size: 0.82rem;
}
.fila-linea select:focus,
.fila-linea input:focus  { border-color: var(--amarillo); background: #FFFDF0; outline: none; }
.fila-linea input:disabled { color: var(--texto-sec); }
.fila-linea .tc { text-align: center; }
.fila-sub { font-size: 0.82rem; font-weight: 600; color: #16A34A; text-align: right; padding-right: 0.3rem; }
.btn-del-fila { background: transparent; border: none; color: var(--danger); cursor: pointer; font-size: 0.85rem; padding: 0; text-align: center; line-height: 1; }
.fila-vacia { padding: 0.6rem 0.5rem; font-size: 0.82rem; color: var(--texto-sec); font-style: italic; }
.btn-agregar-linea { background: transparent; border: 1px dashed var(--borde); color: var(--texto-sec); padding: 0.35rem 1rem; border-radius: 0 0 6px 6px; cursor: pointer; margin-top: 0; font-size: 0.82rem; width: 100%; border-top: none; }
.btn-agregar-linea:hover { border-color: var(--amarillo); background: #FFCC0011; color: var(--amarillo); }

.form-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--borde); }
.totales-form { color: var(--texto-sec); }
.totales-form strong { font-size: 1.1rem; }
.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; }
</style>
