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

            <!-- Acciones: PDF + WhatsApp -->
            <div class="oc-acciones">
              <button class="btn-pdf" @click="descargarPDF(ordenDetalle)">📄 Descargar PDF</button>
              <button class="btn-whatsapp" @click="enviarWhatsApp(ordenDetalle)"
                :disabled="!ordenDetalle.proveedor_telefono">💬 Enviar por WhatsApp</button>
            </div>

            <!-- Recepciones -->
            <div v-if="recepcionesDetalle.length > 0" class="recepciones-section">
              <h3 class="rec-titulo">Recepciones registradas</h3>
              <div
                v-for="r in recepcionesDetalle" :key="r.id"
                class="rec-item"
                :class="{ 'rec-devuelta': r.devuelta }"
              >
                <div class="rec-row">
                  <span class="rec-id">Rec. #{{ r.id }}</span>
                  <span class="rec-fecha">{{ formatFecha(r.fecha_recepcion) }}</span>
                  <span v-if="r.numero_factura" class="rec-factura">Factura: {{ r.numero_factura }}</span>
                  <span class="rec-total">${{ r.total_recibido.toFixed(2) }}</span>
                  <span v-if="r.devuelta" class="badge badge-devuelta">Devuelta</span>
                  <button
                    v-if="esAdmin && !r.devuelta"
                    class="btn-devolver"
                    :disabled="devolviendo === r.id"
                    @click="devolverRecepcion(r)"
                  >
                    {{ devolviendo === r.id ? 'Procesando...' : '↩ Devolver todo' }}
                  </button>
                </div>
                <p v-if="errorDevolucion && devolviendo === null" class="msg-error-dev">{{ errorDevolucion }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal nueva/editar orden -->
        <div class="overlay" v-if="mostrarForm" @click.self="cerrarForm">
          <div class="modal modal-form modal-catalogo">
            <div class="modal-header">
              <h2>{{ editandoId ? 'Editar orden' : 'Nueva orden a proveedor' }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarForm">✕</button>
            </div>

            <!-- Proveedor selector (arriba) -->
            <div class="oc-prov-bar">
              <label>Proveedor</label>
              <select v-model="form.proveedor_id">
                <option value="">— Selecciona proveedor —</option>
                <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
              </select>
            </div>

            <!-- Two-panel layout -->
            <div class="oc-panels">

              <!-- LEFT: Catálogo de productos -->
              <div class="oc-catalogo">
                <div class="oc-cat-header">
                  <i class="ti ti-building-store" style="color:#FFCC00;font-size:18px" aria-hidden="true"></i>
                  <span>Catálogo de productos</span>
                  <span class="oc-cat-count">{{ opcionesFiltradas.length }} opciones</span>
                </div>

                <!-- Filtros -->
                <div class="oc-filtros">
                  <select v-model="filtroMarcaOC" class="oc-filtro-sel">
                    <option value="">Marca</option>
                    <option v-for="m in marcas" :key="m.id" :value="m.id">{{ m.nombre }}</option>
                  </select>
                  <select v-model="filtroDeptoOC" class="oc-filtro-sel" @change="cargarCategoriasOC">
                    <option value="">Departamento</option>
                    <option v-for="d in departamentos" :key="d.id" :value="d.id">{{ d.nombre }}</option>
                  </select>
                  <select v-model="filtroCategoriaOC" class="oc-filtro-sel" :disabled="!filtroDeptoOC">
                    <option value="">Categoría</option>
                    <option v-for="c in categoriasOC" :key="c.id" :value="c.id">{{ c.nombre }}</option>
                  </select>
                </div>
                <div class="oc-filtros">
                  <div class="oc-busqueda">
                    <i class="ti ti-search" style="color:#A0A0A0;font-size:15px" aria-hidden="true"></i>
                    <input v-model="filtroBusquedaOC" placeholder="Buscar producto o código..." />
                  </div>
                </div>

                <!-- Lista de productos -->
                <div class="oc-prod-list">
                  <div v-for="op in opcionesFiltradas" :key="op.key" class="oc-prod-item"
                    :class="{ 'oc-prod-en-orden': productoEnOrden(op.key) }">
                    <div class="oc-prod-info">
                      <div class="oc-prod-nombre">{{ op.label }}</div>
                      <div class="oc-prod-meta">
                        <span v-if="op.departamento_id">{{ deptoNombre(op.departamento_id) }}</span>
                        <span v-if="op.categoria_id"> > {{ catNombre(op) }}</span>
                        <span v-if="op.marca_id"> · {{ marcaNombre(op.marca_id) }}</span>
                      </div>
                    </div>
                    <div class="oc-prod-nums">
                      <span class="oc-prod-costo">${{ op.costo.toFixed(2) }}</span>
                      <span class="oc-prod-stock" :class="{ 'oc-stock-bajo': op.stock < 5 }">stk: {{ op.stock }}</span>
                    </div>
                    <button v-if="!productoEnOrden(op.key)" class="oc-btn-add" @click="agregarDesdeCatalogo(op)">+</button>
                    <span v-else class="oc-ya-agregado">
                      <i class="ti ti-check" aria-hidden="true"></i>
                    </span>
                  </div>

                  <div v-if="opcionesFiltradas.length === 0" class="oc-prod-vacio">
                    Usa los filtros para encontrar productos
                  </div>

                  <!-- Crear producto nuevo -->
                  <div class="oc-crear-nuevo" @click="agregarLinea">
                    <i class="ti ti-plus" style="font-size:14px" aria-hidden="true"></i> Crear producto nuevo
                  </div>
                </div>
              </div>

              <!-- RIGHT: Orden en preparación -->
              <div class="oc-orden">
                <div class="oc-orden-header">
                  <i class="ti ti-clipboard-list" style="color:#FFCC00;font-size:18px" aria-hidden="true"></i>
                  <span>Orden en preparación</span>
                </div>

                <div class="oc-orden-items">
                  <div v-for="(linea, i) in form.detalles" :key="i" class="oc-orden-item">
                    <div class="oc-item-nombre">
                      <span v-if="linea._key">{{ linea.nombre_producto }}</span>
                      <input v-else v-model="linea.nombre_producto" placeholder="Nombre producto nuevo"
                        class="oc-input-nombre" />
                      <span v-if="linea.es_producto_nuevo" class="tag-nuevo">NUEVO</span>
                    </div>
                    <!-- Marca/Depto para nuevo -->
                    <div v-if="!linea._key" class="oc-item-clasif">
                      <select v-model="linea.marca_id" class="oc-sel-mini">
                        <option :value="null">Marca</option>
                        <option v-for="m in marcas" :key="m.id" :value="m.id">{{ m.nombre }}</option>
                      </select>
                      <select v-model="linea.departamento_id" class="oc-sel-mini" @change="linea.categoria_id = null">
                        <option :value="null">Depto</option>
                        <option v-for="d in departamentos" :key="d.id" :value="d.id">{{ d.nombre }}</option>
                      </select>
                    </div>
                    <div class="oc-item-nums">
                      <input v-model.number="linea.cantidad_pedida" type="number" min="1" class="oc-input-cant" />
                      <span class="oc-item-x">×</span>
                      <input v-model.number="linea.precio_unitario_usd" type="number" min="0" step="0.01" class="oc-input-precio" />
                      <span class="oc-item-sub">${{ subtotalLinea(linea).toFixed(2) }}</span>
                      <button class="oc-btn-del" @click="quitarLinea(i)" title="Quitar">
                        <i class="ti ti-x" style="font-size:13px" aria-hidden="true"></i>
                      </button>
                    </div>
                  </div>

                  <div v-if="form.detalles.length === 0" class="oc-orden-vacia">
                    Agrega productos desde el catálogo
                  </div>
                </div>

                <!-- Footer orden -->
                <div class="oc-orden-footer">
                  <div class="oc-orden-total">
                    <span>{{ form.detalles.length }} producto{{ form.detalles.length !== 1 ? 's' : '' }}</span>
                    <span class="oc-total-monto">${{ totalForm.toFixed(2) }}</span>
                  </div>
                  <input v-model="form.observacion" placeholder="Observaciones..." class="oc-input-obs" />
                  <button class="oc-btn-crear" @click="guardar" :disabled="guardando || !form.proveedor_id || form.detalles.length === 0">
                    {{ guardando ? 'Guardando...' : (editandoId ? 'Actualizar orden' : 'Crear orden') }}
                  </button>
                  <p class="msg-error" v-if="error" style="margin:4px 0 0;font-size:0.8rem">{{ error }}</p>
                </div>
              </div>
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
  name: 'OrdenesCompra',
  data() {
    return {
      usuario:            JSON.parse(localStorage.getItem('usuario') || '{}'),
      ordenes:            [],
      proveedores:        [],
      productosRaw:       [],
      recepcionesDetalle: [],
      devolviendo:        null,
      errorDevolucion:    '',
      departamentos:      [],
      marcas:             [],
      filtroEstado:       '',
      filtroProveedor:    '',
      filtroMarcaOC:      '',
      filtroDeptoOC:      '',
      filtroProveedorOC:  '',
      filtroBusquedaOC:   '',
      filtroCategoriaOC:  '',
      categoriasOC:       [],
      ordenDetalle:       null,
      mostrarForm:        false,
      editandoId:         null,
      guardando:          false,
      error:              '',
      form: {
        proveedor_id: '',
        observacion:  '',
        detalles:     [],
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
              categoria_id:   p.categoria_id    || null,
              proveedor_id:   p.proveedor_id    || null,
              marca_id:       p.marca_id        || null,
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
            categoria_id:   p.categoria_id    || null,
            proveedor_id:   p.proveedor_id    || null,
            marca_id:       p.marca_id        || null,
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
      if (this.filtroMarcaOC) {
        const id = parseInt(this.filtroMarcaOC)
        lista = lista.filter(o => o.marca_id === id)
      }
      if (this.filtroDeptoOC) {
        const id = parseInt(this.filtroDeptoOC)
        lista = lista.filter(o => o.departamento_id === id)
      }
      if (this.filtroCategoriaOC) {
        const id = parseInt(this.filtroCategoriaOC)
        lista = lista.filter(o => o.categoria_id === id)
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
    await Promise.all([this.cargar(), this.cargarProveedores(), this.cargarInventario(), this.cargarDepartamentos(), this.cargarMarcas()])
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
        const res = await axios.get('/productos/departamentos-con-categorias')
        this.departamentos = res.data
      } catch {}
    },
    async cargarMarcas() {
      try {
        const res = await axios.get('/marcas/')
        this.marcas = res.data
      } catch { this.marcas = [] }
    },
    async cargarCategoriasOC() {
      if (!this.filtroDeptoOC) {
        this.categoriasOC = []
        this.filtroCategoriaOC = ''
        return
      }
      try {
        const res = await axios.get('/productos/categorias', { params: { departamento_id: this.filtroDeptoOC } })
        this.categoriasOC = res.data
        this.filtroCategoriaOC = ''
      } catch { this.categoriasOC = [] }
    },
    _lineaVacia() {
      return { _key: '', producto_id: null, variante_id: null, nombre_producto: '', cantidad_pedida: 1, precio_unitario_usd: 0, es_producto_nuevo: false, marca_id: null, departamento_id: null, categoria_id: null }
    },
    abrirNueva() {
      this.editandoId = null
      this.form = { proveedor_id: '', observacion: '', detalles: [] }
      this.filtroMarcaOC = ''; this.filtroDeptoOC = ''; this.filtroProveedorOC = ''; this.filtroBusquedaOC = ''
      this.filtroCategoriaOC = ''; this.categoriasOC = []
      this.mostrarForm = true
    },
    editarOrden(o) {
      this.editandoId = o.id
      this.filtroMarcaOC = ''; this.filtroDeptoOC = ''; this.filtroProveedorOC = ''; this.filtroBusquedaOC = ''
      this.filtroCategoriaOC = ''; this.categoriasOC = []
      this.form = {
        proveedor_id: o.proveedor_id,
        observacion:  o.observacion || '',
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
    agregarDesdeCatalogo(op) {
      if (this.productoEnOrden(op.key)) return
      this.form.detalles.push({
        _key:               op.key,
        producto_id:        op.producto_id,
        variante_id:        op.variante_id,
        nombre_producto:    op.label,
        cantidad_pedida:    1,
        precio_unitario_usd: op.costo,
        es_producto_nuevo:  false,
        marca_id:           op.marca_id || null,
        departamento_id:    op.departamento_id || null,
        categoria_id:       op.categoria_id || null,
      })
    },
    productoEnOrden(key) {
      return this.form.detalles.some(d => d._key === key && d._key !== '')
    },
    deptoNombre(id) {
      const d = this.departamentos.find(x => x.id === id)
      return d ? d.nombre : ''
    },
    catNombre(op) {
      if (!op.categoria_id) return ''
      const d = this.departamentos.find(x => x.id === op.departamento_id)
      if (!d) return ''
      // buscar en departamentos-con-categorias si disponible
      const cats = d.categorias || []
      const c = cats.find(x => x.id === op.categoria_id)
      return c ? c.nombre : ''
    },
    marcaNombre(id) {
      const m = this.marcas.find(x => x.id === id)
      return m ? m.nombre : ''
    },
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
    async verDetalle(o) {
      this.ordenDetalle    = o
      this.recepcionesDetalle = []
      this.errorDevolucion = ''
      try {
        const res = await axios.get(`/compras/ordenes/${o.id}/recepciones/`)
        this.recepcionesDetalle = res.data
      } catch (e) {
        console.error('Error cargando recepciones:', e?.response?.status, e?.response?.data)
      }
    },
    async descargarPDF(orden) {
      try {
        const res = await axios.get(`/compras/ordenes/${orden.id}/pdf`, { responseType: 'blob' })
        const url = URL.createObjectURL(res.data)
        const a = document.createElement('a')
        a.href = url
        a.download = `OC_${orden.numero || orden.id}.pdf`
        a.click()
        URL.revokeObjectURL(url)
      } catch (e) {
        alert('Error al generar PDF: ' + (e?.response?.data?.detail || e.message))
      }
    },
    enviarWhatsApp(orden) {
      let tel = (orden.proveedor_telefono || '').replace(/[^0-9]/g, '')
      if (!tel) { alert('El proveedor no tiene teléfono registrado'); return }
      // Formato Venezuela: si empieza con 0, quitar y agregar 58
      if (tel.startsWith('0')) tel = '58' + tel.substring(1)
      if (!tel.startsWith('58') && tel.length === 10) tel = '58' + tel
      const msg = encodeURIComponent(
        `Hola, le envío la Orden de Compra *${orden.numero}* de Comercial Ferre-Util C.A. `
        + `por un total de *$${orden.total.toFixed(2)}*. Adjunto el PDF.`
      )
      // Primero descarga el PDF, luego abre WhatsApp
      this.descargarPDF(orden)
      setTimeout(() => {
        window.open(`https://wa.me/${tel}?text=${msg}`, '_blank')
      }, 500)
    },
    async devolverRecepcion(rec) {
      if (!confirm(`¿Devolver recepción #${rec.id} por $${rec.total_recibido.toFixed(2)}?\nEsto revertirá el stock y los costos actualizados.`)) return
      this.devolviendo     = rec.id
      this.errorDevolucion = ''
      try {
        const res = await axios.post(`/compras/recepciones/${rec.id}/devolucion-total`, {
          usuario_rol: this.usuario.rol || ''
        })
        console.log('Devolucion OK:', res.data)
        // Actualizar estado en la lista y en recepcionesDetalle
        rec.devuelta = true
        if (this.ordenDetalle && res.data.orden_estado) {
          this.ordenDetalle.estado = res.data.orden_estado
          const enLista = this.ordenes.find(o => o.id === this.ordenDetalle.id)
          if (enLista) enLista.estado = res.data.orden_estado
        }
        alert(res.data.mensaje)
      } catch (e) {
        this.errorDevolucion = e?.response?.data?.detail || 'Error al devolver'
      } finally {
        this.devolviendo = null
      }
    },
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
.btn-ver    { background: #1A1A1A; color: #FFFFFF; border: 1px solid var(--borde); padding: 0.28rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
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

/* ── Recepciones en modal ── */
.recepciones-section { margin-top: 1.25rem; border-top: 1px solid var(--borde); padding-top: 0.75rem; }
.rec-titulo { font-size: 0.88rem; font-weight: 700; color: var(--texto-sec); margin: 0 0 0.5rem; text-transform: uppercase; letter-spacing: 0.04em; }
.rec-item { background: var(--fondo-tabla-alt, #F8F8F4); border-radius: 7px; padding: 0.55rem 0.8rem; margin-bottom: 0.4rem; }
.rec-devuelta { opacity: 0.55; }
.rec-row { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.rec-id    { font-weight: 700; font-size: 0.85rem; color: var(--texto-principal); }
.rec-fecha { font-size: 0.82rem; color: var(--texto-muted); }
.rec-factura { font-size: 0.8rem; color: var(--texto-sec); }
.rec-total { font-weight: 700; color: #16A34A; margin-left: auto; }
.badge-devuelta { background: #FEE2E2; color: #DC2626; border-radius: 4px; font-size: 0.72rem; padding: 0.1rem 0.45rem; font-weight: 700; }
.btn-devolver { background: #DC2626; color: #fff; border: none; padding: 0.3rem 0.75rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 600; }
.btn-devolver:disabled { opacity: 0.5; cursor: not-allowed; }
.msg-error-dev { color: #DC2626; font-size: 0.82rem; margin: 0.25rem 0 0; }

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
.oc-acciones { display: flex; gap: 8px; margin-top: 1rem; padding-top: 0.8rem; border-top: 1px solid var(--borde); }
.btn-pdf { background: #3A3A3A; color: #F5F5F5; border: 1px solid #555; padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.btn-pdf:hover { border-color: #FFCC00; background: #FFCC0022; }
.btn-whatsapp { background: #16A34A; color: white; border: none; padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.btn-whatsapp:hover { background: #15803D; }
.btn-whatsapp:disabled { opacity: 0.4; cursor: not-allowed; }
.sel-inline { max-width: 120px; font-size: 0.8rem; height: 30px; }
/* ── Nuevo diseño: Orden a proveedor (dos paneles) ────────────────── */
.modal-catalogo { max-width: 1200px !important; width: 98vw; }
.oc-prov-bar { padding: 0 1.25rem 0.5rem; display: flex; align-items: center; gap: 8px; }
.oc-prov-bar label { font-size: 0.82rem; color: var(--texto-sec); white-space: nowrap; }
.oc-prov-bar select { flex: 1; }
.oc-panels { display: flex; flex: 1; min-height: 380px; border-top: 1px solid var(--borde); overflow: hidden; }
.oc-catalogo { flex: 1; display: flex; flex-direction: column; border-right: 1px solid var(--borde); }
.oc-cat-header { display: flex; align-items: center; gap: 8px; padding: 10px 14px; font-size: 0.9rem; font-weight: 500; }
.oc-cat-count { margin-left: auto; font-size: 0.75rem; color: var(--texto-sec); font-weight: 400; }
.oc-filtros { display: flex; gap: 5px; padding: 0 14px 6px; }
.oc-filtro-sel { flex: 1; min-width: 0; font-size: 0.78rem; height: 30px; }
.oc-busqueda { display: flex; align-items: center; gap: 6px; flex: 1; background: var(--fondo); border: 0.5px solid var(--borde); border-radius: 6px; height: 30px; padding: 0 8px; }
.oc-busqueda input { background: transparent; border: none; color: var(--texto-principal); font-size: 0.8rem; flex: 1; outline: none; }
.oc-prod-list { flex: 1; overflow-y: auto; padding: 0 14px 8px; }
.oc-prod-item { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 0.5px solid var(--borde); cursor: default; }
.oc-prod-item:hover { background: var(--fondo-hover, rgba(255,204,0,0.03)); }
.oc-prod-en-orden { opacity: 0.5; }
.oc-prod-info { flex: 1; min-width: 0; }
.oc-prod-nombre { font-size: 0.82rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.oc-prod-meta { font-size: 0.72rem; color: var(--texto-sec); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.oc-prod-nums { text-align: right; min-width: 50px; }
.oc-prod-costo { display: block; font-size: 0.78rem; color: var(--texto-sec); }
.oc-prod-stock { display: block; font-size: 0.72rem; color: var(--texto-sec); }
.oc-stock-bajo { color: #DC2626 !important; }
.oc-btn-add { background: #FFCC00; color: #1A1A1A; border: none; border-radius: 6px; width: 26px; height: 26px; font-size: 15px; font-weight: 700; cursor: pointer; flex-shrink: 0; }
.oc-btn-add:hover { background: #FFD700; }
.oc-ya-agregado { color: #16A34A; font-size: 15px; width: 26px; text-align: center; flex-shrink: 0; }
.oc-prod-vacio { padding: 2rem 0; text-align: center; color: var(--texto-sec); font-size: 0.82rem; }
.oc-crear-nuevo { padding: 10px 0; text-align: center; color: #FFCC00; font-size: 0.8rem; cursor: pointer; border-top: 1px dashed var(--borde); margin-top: 4px; }
.oc-crear-nuevo:hover { text-decoration: underline; }
/* Panel derecho: orden */
.oc-orden { width: 350px; display: flex; flex-direction: column; background: var(--fondo); flex-shrink: 0; }
.oc-orden-header { display: flex; align-items: center; gap: 8px; padding: 10px 12px; font-size: 0.88rem; font-weight: 500; border-bottom: 0.5px solid var(--borde); }
.oc-orden-items { flex: 1; overflow-y: auto; padding: 4px 12px; }
.oc-orden-item { padding: 8px 0; border-bottom: 0.5px solid var(--borde); }
.oc-item-nombre { font-size: 0.8rem; font-weight: 500; display: flex; align-items: center; gap: 4px; }
.oc-input-nombre { background: transparent; border: none; border-bottom: 1px dashed var(--borde); color: var(--texto-principal); font-size: 0.8rem; flex: 1; outline: none; padding: 2px 0; }
.oc-item-clasif { display: flex; gap: 4px; margin-top: 3px; }
.oc-sel-mini { font-size: 0.72rem; height: 24px; flex: 1; min-width: 0; }
.oc-item-nums { display: flex; align-items: center; gap: 4px; margin-top: 4px; }
.oc-input-cant {
  width: 55px; min-width: 55px; text-align: center; font-size: 0.8rem; height: 26px;
  padding: 0 !important;
  border: 1px solid var(--borde) !important;
}
.oc-item-x { font-size: 0.72rem; color: var(--texto-sec); }
.oc-input-precio {
  width: 80px; min-width: 80px; text-align: right; font-size: 0.8rem; height: 26px;
  padding: 0 4px !important;
  border: 1px solid var(--borde) !important;
}
.oc-item-sub { font-size: 0.82rem; font-weight: 500; margin-left: auto; white-space: nowrap; }
.oc-btn-del { background: transparent; border: none; color: #DC2626; cursor: pointer; padding: 2px; flex-shrink: 0; }
.oc-orden-vacia { padding: 2rem 0; text-align: center; color: var(--texto-sec); font-size: 0.8rem; }
.oc-orden-footer { padding: 10px 12px; border-top: 1px solid var(--borde); }
.oc-orden-total { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 0.8rem; color: var(--texto-sec); }
.oc-total-monto { font-size: 1rem; font-weight: 600; color: #16A34A; }
.oc-input-obs { width: 100%; font-size: 0.75rem; height: 28px; margin-bottom: 8px; box-sizing: border-box; }
.oc-btn-crear { width: 100%; background: #FFCC00; color: #1A1A1A; border: none; border-radius: 8px; height: 36px; font-size: 0.9rem; font-weight: 600; cursor: pointer; }
.oc-btn-crear:hover { background: #FFD700; }
.oc-btn-crear:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
