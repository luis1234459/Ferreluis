<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Ajustes masivos</h1>
      </div>

      <div class="contenido-inner">

        <!-- ── Tabs nav ── -->
        <div class="tabs-nav">
          <button class="tab-btn" :class="{ 'tab-activo': tabActivo === 'precios' }"
            @click="tabActivo = 'precios'">
            Precios
          </button>
          <button class="tab-btn" :class="{ 'tab-activo': tabActivo === 'stock' }"
            @click="tabActivo = 'stock'">
            Stock
          </button>
          <button class="tab-btn" :class="{ 'tab-activo': tabActivo === 'comisiones' }"
            @click="tabActivo = 'comisiones'">
            Comisiones
          </button>
          <button class="tab-btn" :class="{ 'tab-activo': tabActivo === 'historial' }"
            @click="cambiarTabHistorial">
            Historial
          </button>
        </div>

        <!-- ══════════════════════════════════════════════════════════════════ -->
        <!-- Tab: Precios                                                       -->
        <!-- ══════════════════════════════════════════════════════════════════ -->
        <div v-show="tabActivo === 'precios'">

          <!-- Filtros -->
          <div class="filtros-bar">
            <select v-model="filtroPrecioTipo" @change="filtroPrecioId = ''; productosPrecio = []">
              <option value="todos">Todos los productos</option>
              <option value="departamento">Por departamento</option>
              <option value="proveedor">Por proveedor</option>
              <option value="pareto">Solo productos clave</option>
            </select>
            <select v-if="filtroPrecioTipo === 'departamento' || filtroPrecioTipo === 'proveedor'"
              v-model="filtroPrecioId">
              <option value="">— Seleccionar —</option>
              <option v-for="op in opcionesFiltroPrecio" :key="op.id" :value="op.id">{{ op.nombre }}</option>
            </select>
            <button class="btn-cargar" @click="cargarProductosPrecio" :disabled="cargandoPrecio">
              {{ cargandoPrecio ? 'Cargando...' : 'Cargar productos' }}
            </button>
          </div>

          <!-- Panel acción global -->
          <div v-if="productosPrecio.length > 0" class="panel-global">
            <p class="panel-titulo">Acción global — aplica a todos los {{ productosPrecio.length }} productos cargados</p>
            <div class="panel-controles">
              <select v-model="globalPrecioTipo">
                <option value="costo_pct_aum">Aumentar costo %</option>
                <option value="costo_pct_dis">Disminuir costo %</option>
                <option value="margen_fijo">Fijar margen %</option>
                <option value="precio_directo">Fijar precio USD directo</option>
              </select>
              <input type="number" v-model.number="globalPrecioValor" min="0" step="0.0001"
                :placeholder="globalPrecioTipo === 'precio_directo' ? 'Precio USD' : 'Valor %'" />
              <button class="btn-aplicar" @click="aplicarGlobalPrecio">Aplicar a todos</button>
            </div>
          </div>

          <!-- Tabla editable -->
          <div v-if="productosPrecio.length > 0" class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Depto.</th>
                  <th>Costo USD</th>
                  <th>Margen %</th>
                  <th>Precio base USD</th>
                  <th>Stock</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in productosPrecio" :key="p.id"
                  :class="{ 'fila-modificada': p._modificado }">
                  <td style="font-weight:600">
                    {{ p.nombre }}
                    <span v-if="p.tiene_variantes" class="badge-variantes" :title="`${p.variantes_count} variantes — costo base para las que no tienen valor propio`">V</span>
                  </td>
                  <td class="txt-muted">{{ p.departamento_nombre }}</td>
                  <td>
                    <input class="input-celda" type="number" v-model.number="p._costo"
                      step="0.0001" min="0" @input="recalcularDesde(p, 'costo')" />
                  </td>
                  <td>
                    <input class="input-celda" type="number" v-model.number="p._margen"
                      step="0.1" min="0" max="9999" @input="recalcularDesde(p, 'margen')" />
                  </td>
                  <td>
                    <input class="input-celda input-precio-directo" type="number" v-model.number="p._precio"
                      step="0.0001" min="0" @input="recalcularDesde(p, 'precio')" />
                  </td>
                  <td class="txt-muted">{{ p.stock }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="productosPrecio.length > 0" class="acciones-footer">
            <span v-if="msgPrecio" class="msg-ok">{{ msgPrecio }}</span>
            <button class="btn-guardar-lote" @click="guardarCambiosPrecio" :disabled="guardandoPrecio">
              {{ guardandoPrecio ? 'Guardando...' : 'Guardar todos los cambios' }}
            </button>
          </div>

          <div v-if="productosPrecio.length === 0 && !cargandoPrecio" class="sin-datos-tab">
            Selecciona un filtro y haz clic en "Cargar productos"
          </div>

        </div>

        <!-- ══════════════════════════════════════════════════════════════════ -->
        <!-- Tab: Stock                                                         -->
        <!-- ══════════════════════════════════════════════════════════════════ -->
        <div v-show="tabActivo === 'stock'">

          <!-- Filtros -->
          <div class="filtros-bar">
            <select v-model="filtroStockTipo" @change="filtroStockId = ''; productosStock = []">
              <option value="todos">Todos los productos</option>
              <option value="departamento">Por departamento</option>
              <option value="proveedor">Por proveedor</option>
              <option value="pareto">Solo productos clave</option>
            </select>
            <select v-if="filtroStockTipo === 'departamento' || filtroStockTipo === 'proveedor'"
              v-model="filtroStockId">
              <option value="">— Seleccionar —</option>
              <option v-for="op in opcionesFiltroStock" :key="op.id" :value="op.id">{{ op.nombre }}</option>
            </select>
            <button class="btn-cargar" @click="cargarProductosStock" :disabled="cargandoStock">
              {{ cargandoStock ? 'Cargando...' : 'Cargar productos' }}
            </button>
          </div>

          <!-- Panel acción global -->
          <div v-if="productosStock.length > 0" class="panel-global">
            <p class="panel-titulo">Acción global — aplica a todos los {{ productosStock.length }} productos cargados</p>
            <div class="panel-controles">
              <select v-model="globalStockTipo">
                <option value="agregar">Agregar cantidad</option>
                <option value="restar">Restar cantidad</option>
                <option value="fijar">Fijar en valor exacto</option>
              </select>
              <input type="number" v-model.number="globalStockCantidad" min="0" step="1" placeholder="Cantidad" />
              <input type="text" v-model="globalStockMotivo" placeholder="Motivo..." style="width:180px" />
              <button class="btn-aplicar" @click="aplicarGlobalStock">Aplicar a todos</button>
            </div>
          </div>

          <!-- Tabla editable -->
          <div v-if="productosStock.length > 0" class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Depto.</th>
                  <th>Stock actual</th>
                  <th>Tipo ajuste</th>
                  <th>Cantidad</th>
                  <th>Stock resultante</th>
                  <th>Motivo</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in productosStock" :key="p.id"
                  :class="{ 'fila-modificada': p._modificado }">
                  <td style="font-weight:600">
                    {{ p.nombre }}
                    <span v-if="p.tiene_variantes" class="badge-variantes" :title="`${p.variantes_count} variantes — stock distribuido por variante`">V</span>
                  </td>
                  <td class="txt-muted">{{ p.departamento_nombre }}</td>
                  <td>{{ p.stock }}</td>
                  <td>
                    <select v-model="p._tipo" @change="p._modificado = true" class="select-celda">
                      <option value="agregar">Agregar</option>
                      <option value="restar">Restar</option>
                      <option value="fijar">Fijar</option>
                    </select>
                  </td>
                  <td>
                    <input class="input-celda" type="number" v-model.number="p._cantidad"
                      min="0" step="1" @input="p._modificado = true" />
                  </td>
                  <td :class="stockResultante(p) < 0 ? 'txt-danger' : 'txt-verde'">
                    {{ stockResultante(p) }}
                  </td>
                  <td>
                    <input class="input-celda input-motivo" type="text" v-model="p._motivo"
                      placeholder="Motivo..." @input="p._modificado = true" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="productosStock.length > 0" class="acciones-footer">
            <span v-if="msgStock" class="msg-ok">{{ msgStock }}</span>
            <button class="btn-guardar-lote" @click="guardarCambiosStock" :disabled="guardandoStock">
              {{ guardandoStock ? 'Guardando...' : 'Guardar todos los cambios' }}
            </button>
          </div>

          <div v-if="productosStock.length === 0 && !cargandoStock" class="sin-datos-tab">
            Selecciona un filtro y haz clic en "Cargar productos"
          </div>

        </div>

        <!-- ══════════════════════════════════════════════════════════════════ -->
        <!-- Tab: Comisiones                                                    -->
        <!-- ══════════════════════════════════════════════════════════════════ -->
        <div v-show="tabActivo === 'comisiones'">

          <!-- Filtros -->
          <div class="filtros-bar">
            <select v-model="filtroComisionTipo" @change="filtroComisionId = ''; productosComision = []">
              <option value="todos">Todos los productos</option>
              <option value="departamento">Por departamento</option>
              <option value="proveedor">Por proveedor</option>
              <option value="pareto">Solo productos clave</option>
            </select>
            <select v-if="filtroComisionTipo === 'departamento' || filtroComisionTipo === 'proveedor'"
              v-model="filtroComisionId">
              <option value="">— Seleccionar —</option>
              <option v-for="op in opcionesFiltroComision" :key="op.id" :value="op.id">{{ op.nombre }}</option>
            </select>
            <button class="btn-cargar" @click="cargarProductosComision" :disabled="cargandoComision">
              {{ cargandoComision ? 'Cargando...' : 'Cargar productos' }}
            </button>
          </div>

          <!-- Panel acción global -->
          <div v-if="productosComision.length > 0" class="panel-global">
            <p class="panel-titulo">Acción global — aplica a todos los {{ productosComision.length }} productos cargados</p>
            <div class="panel-controles">
              <input type="number" v-model.number="globalComisionPct" min="0" max="100"
                step="0.1" placeholder="% comisión" />
              <button class="btn-aplicar" @click="aplicarGlobalComision">Aplicar a todos</button>
            </div>
          </div>

          <!-- Tabla editable -->
          <div v-if="productosComision.length > 0" class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Depto.</th>
                  <th>Proveedor</th>
                  <th>Costo USD</th>
                  <th>Margen %</th>
                  <th>Precio base</th>
                  <th>Comisión %</th>
                  <th>Stock</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in productosComision" :key="p.id"
                  :class="{ 'fila-modificada': p._modificado }">
                  <td style="font-weight:600">
                    {{ p.nombre }}
                    <span v-if="p.tiene_variantes" class="badge-variantes" :title="`${p.variantes_count} variantes — comisión aplica a todas`">V</span>
                  </td>
                  <td class="txt-muted">{{ p.departamento_nombre }}</td>
                  <td class="txt-muted">{{ p.proveedor_nombre }}</td>
                  <td class="txt-muted">${{ p.costo_usd.toFixed(4) }}</td>
                  <td class="txt-muted">{{ (p.margen * 100).toFixed(2) }}%</td>
                  <td class="txt-verde">${{ (p.costo_usd * (1 + p.margen)).toFixed(4) }}</td>
                  <td>
                    <input class="input-celda" type="number" v-model.number="p._comision_pct"
                      step="0.1" min="0" max="100" @input="p._modificado = true" />
                  </td>
                  <td class="txt-muted">{{ p.stock }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="productosComision.length > 0" class="acciones-footer">
            <span v-if="msgComision" class="msg-ok">{{ msgComision }}</span>
            <button class="btn-guardar-lote" @click="guardarCambiosComision" :disabled="guardandoComision">
              {{ guardandoComision ? 'Guardando...' : 'Guardar todos los cambios' }}
            </button>
          </div>

          <div v-if="productosComision.length === 0 && !cargandoComision" class="sin-datos-tab">
            Selecciona un filtro y haz clic en "Cargar productos"
          </div>

        </div>

        <!-- ══════════════════════════════════════════════════════════════════ -->
        <!-- Tab: Historial                                                     -->
        <!-- ══════════════════════════════════════════════════════════════════ -->
        <div v-show="tabActivo === 'historial'">

          <div class="filtros-bar">
            <input type="date" v-model="filtroHistDesde" />
            <input type="date" v-model="filtroHistHasta" />
            <select v-model="filtroHistTipo">
              <option value="">Todos los tipos</option>
              <option value="precio">Precio</option>
              <option value="stock">Stock</option>
              <option value="comision">Comisión</option>
            </select>
            <button class="btn-cargar" @click="cargarHistorial" :disabled="cargandoHistorial">
              {{ cargandoHistorial ? 'Cargando...' : 'Filtrar' }}
            </button>
            <button class="btn-exportar" @click="exportarExcel">Excel</button>
            <button class="btn-exportar" @click="exportarPDF">PDF</button>
          </div>

          <div class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Usuario</th>
                  <th>Tipo</th>
                  <th>Descripción</th>
                  <th>Afectados</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="historial.length === 0">
                  <td colspan="5" class="sin-datos">Sin registros</td>
                </tr>
                <tr v-for="h in historial" :key="h.id">
                  <td class="txt-muted">{{ formatFecha(h.fecha) }}</td>
                  <td>{{ h.usuario }}</td>
                  <td>
                    <span :class="'badge-tipo-' + h.tipo">{{ h.tipo }}</span>
                  </td>
                  <td>{{ h.descripcion }}</td>
                  <td style="text-align:center">{{ h.productos_afectados }}</td>
                </tr>
              </tbody>
            </table>
          </div>

        </div>

      </div><!-- /contenido-inner -->
    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'Ajustes',
  data() {
    return {
      usuario: JSON.parse(localStorage.getItem('usuario') || '{}'),
      tabActivo: 'precios',

      departamentos: [],
      proveedores:   [],

      // ── Tab Precios ──────────────────────────────────────────────────────
      filtroPrecioTipo: 'todos',
      filtroPrecioId:   '',
      productosPrecio:  [],
      cargandoPrecio:   false,
      globalPrecioTipo: 'costo_pct_aum',
      globalPrecioValor: 0,
      guardandoPrecio:  false,
      msgPrecio:        '',

      // ── Tab Stock ────────────────────────────────────────────────────────
      filtroStockTipo: 'todos',
      filtroStockId:   '',
      productosStock:  [],
      cargandoStock:   false,
      globalStockTipo:     'agregar',
      globalStockCantidad: 0,
      globalStockMotivo:   '',
      guardandoStock:  false,
      msgStock:        '',

      // ── Tab Comisiones ───────────────────────────────────────────────────
      filtroComisionTipo: 'todos',
      filtroComisionId:   '',
      productosComision:  [],
      cargandoComision:   false,
      globalComisionPct:  0,
      guardandoComision:  false,
      msgComision:        '',

      // ── Tab Historial ────────────────────────────────────────────────────
      historial:          [],
      filtroHistDesde:    '',
      filtroHistHasta:    '',
      filtroHistTipo:     '',
      cargandoHistorial:  false,
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
    opcionesFiltroPrecio() {
      if (this.filtroPrecioTipo === 'departamento') return this.departamentos
      if (this.filtroPrecioTipo === 'proveedor')    return this.proveedores
      return []
    },
    opcionesFiltroStock() {
      if (this.filtroStockTipo === 'departamento') return this.departamentos
      if (this.filtroStockTipo === 'proveedor')    return this.proveedores
      return []
    },
    opcionesFiltroComision() {
      if (this.filtroComisionTipo === 'departamento') return this.departamentos
      if (this.filtroComisionTipo === 'proveedor')    return this.proveedores
      return []
    },
  },

  async mounted() {
    await Promise.all([this.cargarDepartamentos(), this.cargarProveedores()])
    await this.cargarHistorial()
  },

  methods: {
    _headers() {
      return {
        'X-Usuario-Rol':    this.usuario.rol     || '',
        'X-Usuario-Nombre': this.usuario.usuario || 'admin',
      }
    },

    // ── Carga de catálogos ─────────────────────────────────────────────────
    async cargarDepartamentos() {
      try {
        const res = await axios.get('/productos/departamentos')
        this.departamentos = res.data
      } catch { this.departamentos = [] }
    },
    async cargarProveedores() {
      try {
        const res = await axios.get('/compras/proveedores/')
        this.proveedores = res.data
      } catch { this.proveedores = [] }
    },

    // ── Tab Precios ────────────────────────────────────────────────────────
    async cargarProductosPrecio() {
      this.cargandoPrecio = true
      this.msgPrecio      = ''
      try {
        const params = { filtro_tipo: this.filtroPrecioTipo }
        if (this.filtroPrecioId) params.filtro_id = this.filtroPrecioId
        const res = await axios.get('/ajustes/productos', { params, headers: this._headers() })
        this.productosPrecio = res.data.map(p => {
          const costo  = parseFloat((p.costo_usd || 0).toFixed(4))
          const margen = parseFloat((p.margen * 100).toFixed(4))
          return {
            ...p,
            _costo:      costo,
            _margen:     margen,
            _precio:     parseFloat((costo * (1 + margen / 100)).toFixed(4)),
            _modificado: false,
          }
        })
      } finally {
        this.cargandoPrecio = false
      }
    },
    recalcularDesde(p, campo) {
      p._modificado = true
      if (campo === 'costo' || campo === 'margen') {
        p._precio = parseFloat((p._costo * (1 + p._margen / 100)).toFixed(4))
      } else if (campo === 'precio') {
        const divisor = 1 + p._margen / 100
        if (divisor > 0) {
          p._costo = parseFloat((p._precio / divisor).toFixed(4))
        }
      }
    },
    aplicarGlobalPrecio() {
      const v = this.globalPrecioValor || 0
      this.productosPrecio.forEach(p => {
        if (this.globalPrecioTipo === 'costo_pct_aum') {
          p._costo  = parseFloat((p._costo * (1 + v / 100)).toFixed(4))
          p._precio = parseFloat((p._costo * (1 + p._margen / 100)).toFixed(4))
        } else if (this.globalPrecioTipo === 'costo_pct_dis') {
          p._costo  = parseFloat((p._costo * (1 - v / 100)).toFixed(4))
          p._precio = parseFloat((p._costo * (1 + p._margen / 100)).toFixed(4))
        } else if (this.globalPrecioTipo === 'margen_fijo') {
          p._margen = v
          p._precio = parseFloat((p._costo * (1 + p._margen / 100)).toFixed(4))
        } else if (this.globalPrecioTipo === 'precio_directo') {
          p._precio = parseFloat(v.toFixed(4))
          const divisor = 1 + p._margen / 100
          if (divisor > 0) {
            p._costo = parseFloat((p._precio / divisor).toFixed(4))
          }
        }
        p._modificado = true
      })
    },
    async guardarCambiosPrecio() {
      const items = this.productosPrecio
        .filter(p => p._modificado)
        .map(p => ({
          producto_id: p.id,
          costo_usd:   p._costo,
          margen:      parseFloat((p._margen / 100).toFixed(6)),
        }))
      if (!items.length) { this.msgPrecio = 'Sin cambios pendientes'; return }
      this.guardandoPrecio = true
      try {
        await axios.post('/ajustes/precio/lote', { items }, { headers: this._headers() })
        this.productosPrecio.forEach(p => { p._modificado = false })
        this.msgPrecio = `${items.length} productos actualizados correctamente`
      } catch (e) {
        this.msgPrecio = e?.response?.data?.detail || 'Error al guardar'
      } finally {
        this.guardandoPrecio = false
      }
    },

    // ── Tab Stock ──────────────────────────────────────────────────────────
    async cargarProductosStock() {
      this.cargandoStock = true
      this.msgStock      = ''
      try {
        const params = { filtro_tipo: this.filtroStockTipo }
        if (this.filtroStockId) params.filtro_id = this.filtroStockId
        const res = await axios.get('/ajustes/productos', { params, headers: this._headers() })
        this.productosStock = res.data.map(p => ({
          ...p,
          _tipo:       'agregar',
          _cantidad:   0,
          _motivo:     '',
          _modificado: false,
        }))
      } finally {
        this.cargandoStock = false
      }
    },
    stockResultante(p) {
      const c = parseInt(p._cantidad) || 0
      if (p._tipo === 'fijar')   return c
      if (p._tipo === 'agregar') return p.stock + c
      if (p._tipo === 'restar')  return Math.max(0, p.stock - c)
      return p.stock
    },
    aplicarGlobalStock() {
      const c = parseInt(this.globalStockCantidad) || 0
      this.productosStock.forEach(p => {
        p._tipo       = this.globalStockTipo
        p._cantidad   = c
        p._motivo     = this.globalStockMotivo
        p._modificado = true
      })
    },
    async guardarCambiosStock() {
      const items = this.productosStock
        .filter(p => p._modificado && p._cantidad > 0)
        .map(p => ({
          producto_id: p.id,
          tipo:        p._tipo,
          cantidad:    p._cantidad,
          motivo:      p._motivo || 'Ajuste manual',
        }))
      if (!items.length) { this.msgStock = 'Sin cambios con cantidad > 0'; return }
      this.guardandoStock = true
      try {
        await axios.post('/ajustes/stock/lote', { items }, { headers: this._headers() })
        await this.cargarProductosStock()
        this.msgStock = `${items.length} productos actualizados correctamente`
      } catch (e) {
        this.msgStock = e?.response?.data?.detail || 'Error al guardar'
      } finally {
        this.guardandoStock = false
      }
    },

    // ── Tab Comisiones ─────────────────────────────────────────────────────
    async cargarProductosComision() {
      this.cargandoComision = true
      this.msgComision      = ''
      try {
        const params = { filtro_tipo: this.filtroComisionTipo }
        if (this.filtroComisionId) params.filtro_id = this.filtroComisionId
        const res = await axios.get('/ajustes/productos', { params, headers: this._headers() })
        this.productosComision = res.data.map(p => ({
          ...p,
          _comision_pct: parseFloat((p.comision_pct * 100).toFixed(4)),
          _modificado:   false,
        }))
      } finally {
        this.cargandoComision = false
      }
    },
    aplicarGlobalComision() {
      const pct = parseFloat(this.globalComisionPct) || 0
      this.productosComision.forEach(p => {
        p._comision_pct = pct
        p._modificado   = true
      })
    },
    async guardarCambiosComision() {
      const items = this.productosComision
        .filter(p => p._modificado)
        .map(p => ({
          producto_id:  p.id,
          comision_pct: parseFloat((p._comision_pct / 100).toFixed(6)),
        }))
      if (!items.length) { this.msgComision = 'Sin cambios pendientes'; return }
      this.guardandoComision = true
      try {
        await axios.post('/ajustes/comisiones/lote', { items }, { headers: this._headers() })
        this.productosComision.forEach(p => { p._modificado = false })
        this.msgComision = `${items.length} productos actualizados correctamente`
      } catch (e) {
        this.msgComision = e?.response?.data?.detail || 'Error al guardar'
      } finally {
        this.guardandoComision = false
      }
    },

    // ── Tab Historial ──────────────────────────────────────────────────────
    async cambiarTabHistorial() {
      this.tabActivo = 'historial'
      await this.cargarHistorial()
    },
    async cargarHistorial() {
      this.cargandoHistorial = true
      try {
        const params = {}
        if (this.filtroHistDesde) params.fecha_desde = this.filtroHistDesde
        if (this.filtroHistHasta) params.fecha_hasta = this.filtroHistHasta
        if (this.filtroHistTipo)  params.tipo         = this.filtroHistTipo
        const res = await axios.get('/ajustes/historial', { params, headers: this._headers() })
        this.historial = res.data
      } finally {
        this.cargandoHistorial = false
      }
    },
    async exportarExcel() {
      try {
        const res = await axios.get('/ajustes/exportar/excel', {
          headers:      this._headers(),
          responseType: 'blob',
        })
        const url = URL.createObjectURL(new Blob([res.data]))
        const a   = document.createElement('a')
        a.href     = url
        a.download = 'historial_ajustes.xlsx'
        a.click()
        URL.revokeObjectURL(url)
      } catch { alert('Error al exportar Excel') }
    },
    async exportarPDF() {
      try {
        const res = await axios.get('/ajustes/exportar/pdf', {
          headers:      this._headers(),
          responseType: 'blob',
        })
        const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
        const a   = document.createElement('a')
        a.href     = url
        a.download = 'historial_ajustes.pdf'
        a.click()
        URL.revokeObjectURL(url)
      } catch { alert('Error al exportar PDF') }
    },

    // ── Utilidades ─────────────────────────────────────────────────────────
    formatFecha(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleString('es-VE', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      })
    },
    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    },
  },
}
</script>

<style scoped>
/* ── Tabs ── */
.tabs-nav  { display: flex; gap: 0.25rem; margin-bottom: 1.25rem; border-bottom: 2px solid var(--borde); }
.tab-btn   { padding: 0.6rem 1.4rem; background: transparent; color: var(--texto-sec); border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; font-size: 0.9rem; }
.tab-btn:hover  { color: var(--texto-principal); }
.tab-activo     { color: var(--texto-principal) !important; border-bottom-color: #1A1A1A !important; font-weight: 700; }

/* ── Barra de filtros ── */
.filtros-bar { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; margin-bottom: 1rem; }
.filtros-bar select,
.filtros-bar input[type="date"],
.filtros-bar input[type="text"] {
  padding: 0.45rem 0.75rem; border: 1px solid var(--borde); border-radius: 7px;
  background: #fff; color: var(--texto-principal); font-size: 0.88rem;
}
.btn-cargar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.45rem 1rem; border-radius: 7px; cursor: pointer; font-size: 0.88rem; font-weight: 600; }
.btn-cargar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-exportar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.4rem 0.9rem; border-radius: 7px; cursor: pointer; font-size: 0.84rem; }
.btn-exportar:hover { border-color: #1A1A1A; background: #F5F5F0; }

/* ── Panel acción global ── */
.panel-global   { background: #FFCC0015; border: 1px solid #FFCC0055; border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 1rem; }
.panel-titulo   { font-size: 0.84rem; font-weight: 700; color: var(--texto-sec); margin: 0 0 0.6rem; }
.panel-controles{ display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; }
.panel-controles select,
.panel-controles input { padding: 0.4rem 0.7rem; border: 1px solid var(--borde); border-radius: 7px; background: #fff; font-size: 0.88rem; }
.btn-aplicar { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.42rem 1rem; border-radius: 7px; cursor: pointer; font-size: 0.88rem; font-weight: 600; }

/* ── Tabla editable ── */
.input-celda  { width: 90px; padding: 0.25rem 0.4rem; border: 1px solid var(--borde); border-radius: 5px; font-size: 0.85rem; background: #fff; }
.input-precio-directo { border-color: #16A34A55; background: #F0FDF4; color: #15803D; font-weight: 600; }
.input-precio-directo:focus { border-color: #16A34A; outline: none; }
.input-motivo { width: 140px; }
.select-celda { padding: 0.25rem 0.4rem; border: 1px solid var(--borde); border-radius: 5px; font-size: 0.85rem; background: #fff; }
.fila-modificada { background: #FFCC0022 !important; }

/* ── Pie de tabla ── */
.acciones-footer  { display: flex; justify-content: flex-end; align-items: center; gap: 1rem; margin-top: 1rem; }
.btn-guardar-lote { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.4rem; border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 0.92rem; }
.btn-guardar-lote:disabled { opacity: 0.5; cursor: not-allowed; }
.msg-ok    { color: #16A34A; font-size: 0.88rem; font-weight: 600; }

/* ── Badges ── */
.badge-periodo  { background: var(--borde-suave); color: var(--texto-sec); font-size: 0.76rem; font-weight: 600; padding: 0.12rem 0.5rem; border-radius: 10px; }
.badge-activa    { background: #16A34A1A; color: #16A34A;  font-size: 0.75rem; font-weight: 700; padding: 0.12rem 0.5rem; border-radius: 10px; }
.badge-inactiva  { background: #8888881A; color: #555555;  font-size: 0.75rem; font-weight: 700; padding: 0.12rem 0.5rem; border-radius: 10px; }
.badge-variantes { background: #3B82F61A; color: #1D4ED8;  font-size: 0.7rem; font-weight: 700; padding: 0.1rem 0.4rem; border-radius: 8px; margin-left: 4px; cursor: help; }

.badge-tipo-precio   { background: #1A1A1A1A; color: #1A1A1A;  font-size: 0.75rem; font-weight: 700; padding: 0.12rem 0.5rem; border-radius: 10px; }
.badge-tipo-stock    { background: #F59E0B1A; color: #92400E;  font-size: 0.75rem; font-weight: 700; padding: 0.12rem 0.5rem; border-radius: 10px; }
.badge-tipo-comision { background: #16A34A1A; color: #16A34A;  font-size: 0.75rem; font-weight: 700; padding: 0.12rem 0.5rem; border-radius: 10px; }

/* ── Textos ── */
.txt-muted   { color: var(--texto-muted); }
.txt-verde   { color: #16A34A; font-weight: 600; }
.txt-danger  { color: var(--danger); font-weight: 600; }
.sin-datos   { text-align: center; color: var(--texto-muted); padding: 1.5rem; }
.sin-datos-tab { text-align: center; color: var(--texto-muted); padding: 3rem; font-size: 0.92rem; }
</style>
