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
          <button :class="['tab', tab === 'cliente' ? 'tab-activo' : '']" @click="tab = 'cliente'">
            Devoluciones de clientes
          </button>
          <button :class="['tab', tab === 'proveedor' ? 'tab-activo' : '']" @click="tab = 'proveedor'; cargarProveedor()">
            Devoluciones a proveedores
          </button>
        </div>

        <!-- ═══════════════════════════════ TAB CLIENTES ═══════════════════════════════ -->
        <div v-if="tab === 'cliente'">

          <div class="card-form">
            <h3 class="seccion-titulo">Buscar ventas</h3>

            <!-- PASO 1: Selección de cliente -->
            <div v-if="!clienteDevolucion && !modoSinCliente">
              <div class="busq-cliente-wrap">
                <input
                  v-model="busqClienteTexto"
                  @input="buscarClienteDevolucion"
                  placeholder="Teléfono o nombre del cliente..."
                  class="input-busq-cliente"
                  autocomplete="off"
                />
                <div v-if="busqClienteResultados.length" class="dropdown-cli">
                  <div
                    v-for="c in busqClienteResultados"
                    :key="c.id"
                    class="cli-opcion"
                    @click="seleccionarClienteDevolucion(c)"
                  >
                    <span class="cli-tel">📱 {{ c.telefono }}</span>
                    <span class="cli-nombre">— {{ c.nombre }}</span>
                  </div>
                </div>
              </div>
              <button class="link-sin-cliente" @click="modoSinCliente = true">
                Buscar sin teléfono (Consumidor Final)
              </button>
            </div>

            <!-- Cliente seleccionado o modo CF -->
            <div v-if="clienteDevolucion || modoSinCliente" class="cliente-elegido">
              <span v-if="clienteDevolucion" class="elegido-info">
                <span class="elegido-check">✓</span>
                <span class="elegido-tel">📱 {{ clienteDevolucion.telefono }}</span>
                <span class="elegido-nombre">— {{ clienteDevolucion.nombre }}</span>
              </span>
              <span v-else class="elegido-info elegido-cf">
                <span class="elegido-check">✓</span>
                <span class="elegido-nombre">Consumidor Final</span>
              </span>
              <button class="btn-cambiar-cli" @click="limpiarClienteDevolucion">Cambiar</button>
            </div>

            <!-- PASO 2: Período (aparece al tener cliente o modo CF) -->
            <div v-if="clienteDevolucion || modoSinCliente" class="periodo-wrap">
              <p class="periodo-label">Selecciona el período:</p>
              <div class="fecha-botones">
                <button
                  :class="['btn-fecha', busqFecha === 'hoy' ? 'btn-fecha-activo' : '']"
                  @click="busqFecha = 'hoy'; buscarVentas()"
                >Hoy</button>
                <button
                  :class="['btn-fecha', busqFecha === 'ayer' ? 'btn-fecha-activo' : '']"
                  @click="busqFecha = 'ayer'; buscarVentas()"
                >Ayer</button>
                <button
                  :class="['btn-fecha', busqFecha === 'rango' ? 'btn-fecha-activo' : '']"
                  @click="busqFecha = 'rango'"
                >Rango de fechas</button>
              </div>
              <div v-if="busqFecha === 'rango'" class="fecha-rango">
                <input type="date" v-model="busqFechaInicio" />
                <span class="fecha-sep">—</span>
                <input type="date" v-model="busqFechaFin" />
                <button class="btn-buscar" @click="buscarVentas" :disabled="buscando">
                  {{ buscando ? '...' : 'Buscar ventas' }}
                </button>
              </div>
              <div v-if="buscando" class="buscando-msg">Buscando...</div>
            </div>
          </div>

          <!-- Resultados -->
          <div v-if="ventasEncontradas.length > 0">
            <p class="resultados-meta">{{ ventasEncontradas.length }} venta(s) encontrada(s)</p>

            <div v-for="v in ventasEncontradas" :key="v.venta_id" class="venta-card">
              <div class="venta-header" @click="toggleVenta(v.venta_id)">
                <div class="venta-info">
                  <span class="venta-id">#{{ v.venta_id }}</span>
                  <span class="venta-cliente">{{ v.cliente_nombre }}</span>
                  <span class="venta-fecha txt-muted">{{ formatFecha(v.fecha) }}</span>
                </div>
                <div class="venta-derecha">
                  <span class="venta-total">${{ Number(v.total).toFixed(2) }}</span>
                  <span class="venta-flecha">{{ ventasExpandidas[v.venta_id] ? '▲' : '▼' }}</span>
                </div>
              </div>

              <div v-if="ventasExpandidas[v.venta_id]" class="venta-productos">
                <div v-for="p in v.productos" :key="p.detalle_id" class="prod-row">
                  <div class="prod-row-info">
                    <span class="prod-nombre">{{ p.nombre }}</span>
                    <span class="prod-cant txt-muted">Cant: {{ p.cantidad }}</span>
                    <span class="prod-precio txt-muted">${{ Number(p.precio_unitario).toFixed(2) }} c/u</span>
                    <span v-if="p.cantidad_disponible === 0" class="badge-devuelto">Ya devuelto</span>
                    <span v-else-if="p.cantidad_devuelta > 0" class="badge-parcial">Parcial: {{ p.cantidad_devuelta }} devuelto(s)</span>
                  </div>
                  <button
                    v-if="p.cantidad_disponible > 0"
                    class="btn-devolver"
                    @click="abrirModal(v, p)"
                  >Devolver</button>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="busqRealizada && !buscando" class="sin-resultados">
            Sin ventas en ese período
          </div>

        </div>

        <!-- ═══════════════════════════════ TAB PROVEEDOR ═══════════════════════════════ -->
        <div v-if="tab === 'proveedor'">

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

          <div v-if="pendientes.length" class="alerta-pendientes">
            <strong>{{ pendientes.length }} devolución(es) pendiente(s) de resolver</strong>
          </div>

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

    <!-- ═══════════════════════════════ MODAL DEVOLUCIÓN ═══════════════════════════════ -->
    <div v-if="modalAbierto" class="modal-overlay" @click.self="cerrarModal">
      <div class="modal-box">

        <div class="modal-header">
          <h3>Devolución de producto</h3>
          <button class="modal-cerrar" @click="cerrarModal">✕</button>
        </div>

        <div class="modal-prod-info">
          <strong>{{ modalProducto?.nombre }}</strong>
          <span class="txt-muted">Venta #{{ modalProducto?.venta_id }} · {{ modalProducto?.cliente_nombre }}</span>
          <span class="txt-muted">Precio unitario: ${{ Number(modalProducto?.precio_unitario || 0).toFixed(2) }}</span>
        </div>

        <div class="modal-field">
          <label>Cantidad a devolver</label>
          <div class="cant-row">
            <input
              type="number"
              v-model.number="modalCantidad"
              min="1"
              :max="modalProducto?.cantidad_disponible ?? modalProducto?.cantidad"
              class="inp-cant"
            />
            <span class="txt-muted">/ {{ modalProducto?.cantidad_disponible ?? modalProducto?.cantidad }} disponibles</span>
          </div>
        </div>

        <div class="modal-label-sec">Tipo de resolución</div>
        <div class="modal-opciones">
          <div
            :class="['opcion-card', modalTipo === 'reembolso' ? 'opcion-activa' : '']"
            @click="modalTipo = 'reembolso'"
          >
            <span class="opcion-icono">💰</span>
            <div>
              <div class="opcion-titulo">Reembolso</div>
              <div class="opcion-desc">Devolver dinero al cliente</div>
            </div>
          </div>
          <div
            :class="['opcion-card', modalTipo === 'cambio' ? 'opcion-activa' : '']"
            @click="modalTipo = 'cambio'"
          >
            <span class="opcion-icono">🔄</span>
            <div>
              <div class="opcion-titulo">Cambio</div>
              <div class="opcion-desc">Cambiar por otro producto</div>
            </div>
          </div>
          <div
            v-if="!modalProducto?.es_consumidor"
            :class="['opcion-card', modalTipo === 'credito' ? 'opcion-activa' : '']"
            @click="modalTipo = 'credito'"
          >
            <span class="opcion-icono">🏦</span>
            <div>
              <div class="opcion-titulo">Crédito</div>
              <div class="opcion-desc">Saldo para futura compra</div>
            </div>
          </div>
        </div>

        <!-- Reembolso -->
        <div v-if="modalTipo === 'reembolso'" class="modal-sub">
          <div class="modal-field">
            <label>Moneda</label>
            <div class="btn-group">
              <button :class="['btn-moneda', modalMoneda === 'USD' ? 'activo' : '']" @click="modalMoneda = 'USD'">USD</button>
              <button :class="['btn-moneda', modalMoneda === 'Bs' ? 'activo' : '']" @click="modalMoneda = 'Bs'">Bs</button>
            </div>
          </div>
          <div class="modal-field">
            <label>Método de devolución</label>
            <select v-model="modalMetodoPago">
              <option value="efectivo_usd">Efectivo USD</option>
              <option value="efectivo_bs">Efectivo Bs</option>
              <option value="pago_movil">Pago Móvil</option>
              <option value="zelle">Zelle</option>
              <option value="transferencia">Transferencia</option>
            </select>
          </div>
          <div class="monto-preview-modal">
            Monto a devolver: <strong>{{ simboloMoneda }} {{ montoEnMoneda.toFixed(2) }}</strong>
          </div>
        </div>

        <!-- Cambio -->
        <div v-if="modalTipo === 'cambio'" class="modal-sub">
          <div class="modal-field">
            <label>Buscar nuevo producto</label>
            <div class="busq-prod-wrap">
              <input
                v-model="busqProductoNuevo"
                placeholder="Nombre o código..."
                @input="buscarProductoNuevo"
                @keydown.down.prevent="moverAbajoCambio"
                @keydown.up.prevent="moverArribaCambio"
                @keydown.enter.prevent="seleccionarResaltadoCambio"
                @keydown.escape="productosNuevoResultados = []"
                autocomplete="off"
              />
              <div v-if="productosNuevoResultados.length" class="dropdown-prod" ref="dropdownCambio">
                <div
                  v-for="(prod, idx) in productosNuevoResultados"
                  :key="prod.id"
                  :class="['drop-item', idx === indiceResaltadoCambio ? 'drop-item-resaltado' : '']"
                  @click="seleccionarProductoNuevo(prod)"
                  @mouseenter="indiceResaltadoCambio = idx"
                >
                  <span class="drop-nombre">{{ prod.nombre }}</span>
                  <span class="drop-precio txt-muted">${{ Number(prod.precio_referencial_usd || prod.precio_base_usd || 0).toFixed(2) }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="productoNuevoSeleccionado" class="prod-nuevo-info">
            <span class="prod-nv-nombre">{{ productoNuevoSeleccionado.nombre }}</span>
            <span class="txt-muted">Stock: {{ productoNuevoSeleccionado.stock }}</span>
            <span class="txt-muted">${{ Number(productoNuevoSeleccionado.precio_referencial_usd || productoNuevoSeleccionado.precio_base_usd || 0).toFixed(2) }}</span>
          </div>

          <div v-if="productoNuevoSeleccionado" class="modal-field mt-50">
            <label>Cantidad del producto nuevo</label>
            <input
              v-model.number="cantidadNueva"
              type="number" min="1"
              :max="productoNuevoSeleccionado.stock"
              placeholder="1"
              class="inp-cant"
            />
          </div>

          <div v-if="productoNuevoSeleccionado" class="cambio-resumen">
            <div class="cambio-fila"><span>Total devuelto:</span><span>${{ totalDevuelto.toFixed(2) }}</span></div>
            <div class="cambio-fila"><span>Total producto nuevo ({{ cantidadNueva }} u.):</span><span>${{ totalNuevo.toFixed(2) }}</span></div>
            <div class="cambio-fila cambio-diff" v-if="diferenciaCambio > 0">
              <span>Cliente paga:</span><span class="txt-verde">{{ simboloMoneda }} {{ montoEnMoneda.toFixed(2) }}</span>
            </div>
            <div class="cambio-fila cambio-diff" v-else-if="diferenciaCambio < 0">
              <span>Negocio devuelve:</span><span class="txt-rojo">{{ simboloMoneda }} {{ montoEnMoneda.toFixed(2) }}</span>
            </div>
            <div class="cambio-fila" v-else><span>Sin diferencia</span></div>
          </div>

          <div v-if="productoNuevoSeleccionado && diferenciaCambio !== 0" class="modal-field mt-50">
            <label>Moneda</label>
            <div class="btn-group">
              <button :class="['btn-moneda', modalMoneda === 'USD' ? 'activo' : '']" @click="modalMoneda = 'USD'">USD</button>
              <button :class="['btn-moneda', modalMoneda === 'Bs' ? 'activo' : '']" @click="modalMoneda = 'Bs'">Bs</button>
            </div>
          </div>

          <div v-if="productoNuevoSeleccionado && diferenciaCambio < 0" class="modal-field mt-50">
            <label>¿Cómo recibe el cliente la diferencia?</label>
            <div class="btn-group">
              <button :class="['btn-opcion', resolucionDiferencia === 'devolver' ? 'activo' : '']"
                @click="resolucionDiferencia = 'devolver'">💵 Devolver dinero</button>
              <button :class="['btn-opcion', resolucionDiferencia === 'credito' ? 'activo' : '']"
                @click="resolucionDiferencia = 'credito'">🏦 Saldo a favor</button>
            </div>
          </div>

          <div v-if="productoNuevoSeleccionado && (diferenciaCambio > 0 || (diferenciaCambio < 0 && resolucionDiferencia === 'devolver'))"
               class="diferencia-box"
               :class="diferenciaCambio > 0 ? 'dif-cobrar' : 'dif-devolver'">
            <div class="modal-field">
              <label>{{ diferenciaCambio > 0 ? 'Método de cobro' : 'Método de devolución' }}</label>
              <select v-model="modalMetodoPago">
                <option value="efectivo_usd">Efectivo USD</option>
                <option value="efectivo_bs">Efectivo Bs</option>
                <option value="pago_movil">Pago Móvil</option>
                <option value="zelle">Zelle</option>
                <option value="transferencia">Transferencia</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Crédito -->
        <div v-if="modalTipo === 'credito'" class="modal-sub">
          <div class="credito-info-box">
            <span class="opcion-icono">🏦</span>
            <div>
              <div>Se acreditarán <strong>${{ montoDevolucion.toFixed(2) }}</strong> al saldo del cliente</div>
              <div class="txt-muted">El cliente podrá usarlo en su próxima compra</div>
            </div>
          </div>
        </div>

        <div class="modal-field">
          <label>Observación (opcional)</label>
          <input v-model="modalObservacion" placeholder="Motivo u observaciones..." />
        </div>

        <div class="modal-footer">
          <button class="btn-cancelar" @click="cerrarModal">Cancelar</button>
          <button
            :class="['btn-confirmar', modalTipo === 'reembolso' ? 'btn-rojo' : 'btn-negro']"
            @click="procesarDevolucion"
            :disabled="procesando || !puedeConfirmar"
          >{{ procesando ? 'Procesando...' : labelBotonConfirmar }}</button>
        </div>

      </div>
    </div>

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
      usuario:               JSON.parse(localStorage.getItem('usuario') || '{}'),
      tab:                   'cliente',
      error:                 '',

      // ─── Proveedor tab ────────────────────────────────────────────────────
      devolucionesProveedor: [],
      pendientes:            [],
      proveedores:           [],
      productosProveedor:    [],
      devProv: {
        proveedor_id:    '',
        producto_id:     '',
        nombre_producto: '',
        cantidad:        1,
        costo_unitario:  0,
        tipo_resolucion: 'credito',
        motivo:          '',
        observacion:     '',
      },

      // ─── Cliente tab — paso 1: selección cliente ──────────────────────────
      busqClienteTexto:      '',
      busqClienteResultados: [],
      busqClienteTimer:      null,
      clienteDevolucion:     null,
      modoSinCliente:        false,

      // ─── Cliente tab — paso 2: período ────────────────────────────────────
      busqFecha:       'hoy',
      busqFechaInicio: '',
      busqFechaFin:    '',
      buscando:        false,
      busqRealizada:   false,

      // ─── Resultados ───────────────────────────────────────────────────────
      ventasEncontradas: [],
      ventasExpandidas:  {},

      // ─── Modal devolución ──────────────────────────────────────────────────
      modalAbierto:              false,
      modalVenta:                null,
      modalProducto:             null,
      modalCantidad:             1,
      modalTipo:                 'reembolso',
      modalMetodoPago:           'efectivo_usd',
      modalObservacion:          '',
      busqProductoNuevo:         '',
      productosNuevoResultados:  [],
      productoNuevoSeleccionado: null,
      indiceResaltadoCambio:     -1,
      cantidadNueva:             1,
      modalMoneda:               'USD',
      resolucionDiferencia:      'devolver',
      tasaBcv:                   null,
      procesando:                false,
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
    montoDevolucion() {
      if (!this.modalProducto) return 0
      return this.modalCantidad * Number(this.modalProducto.precio_unitario || 0)
    },
    totalDevuelto() {
      if (!this.modalProducto) return 0
      return this.modalCantidad * Number(this.modalProducto.precio_unitario || 0)
    },
    totalNuevo() {
      if (!this.productoNuevoSeleccionado) return 0
      return this.cantidadNueva * Number(this.productoNuevoSeleccionado.precio_referencial_usd || this.productoNuevoSeleccionado.precio_base_usd || 0)
    },
    diferenciaCambio() {
      if (!this.productoNuevoSeleccionado || !this.modalProducto) return 0
      return this.totalNuevo - this.totalDevuelto
    },
    montoEnMoneda() {
      const monto = this.modalTipo === 'cambio' ? Math.abs(this.diferenciaCambio) : this.totalDevuelto
      if (this.modalMoneda === 'Bs' && this.tasaBcv) return monto * this.tasaBcv
      return monto
    },
    simboloMoneda() { return this.modalMoneda === 'USD' ? '$' : 'Bs.' },
    puedeConfirmar() {
      if (!this.modalProducto) return false
      const maxDev = this.modalProducto.cantidad_disponible ?? this.modalProducto.cantidad
      if (this.modalCantidad < 1 || this.modalCantidad > maxDev) return false
      if (this.modalTipo === 'cambio' && !this.productoNuevoSeleccionado) return false
      return true
    },
    labelBotonConfirmar() {
      if (this.modalTipo === 'reembolso') return '💰 Confirmar reembolso'
      if (this.modalTipo === 'cambio')    return '🔄 Confirmar cambio'
      if (this.modalTipo === 'credito')   return '🏦 Acreditar saldo'
      return 'Confirmar'
    },
  },
  async mounted() {
    await Promise.all([this.cargarProveedores(), this.cargarTasa()])
  },
  methods: {

    // ─── Proveedor ───────────────────────────────────────────────────────────

    async cargarProveedor() {
      try {
        const [res, resPend] = await Promise.all([
          axios.get('/devoluciones/proveedor/'),
          axios.get('/devoluciones/proveedor/pendientes/'),
        ])
        this.devolucionesProveedor = res.data
        this.pendientes            = resPend.data
      } catch (e) {
        this.error = 'Error al cargar devoluciones'
      }
    },

    async cargarProveedores() {
      try {
        const res = await axios.get('/compras/proveedores/')
        this.proveedores = res.data
      } catch (_) {}
    },

    async cargarTasa() {
      try {
        const res = await axios.get('/tasa/')
        this.tasaBcv = res.data.tasa || null
      } catch (_) {}
    },

    async cargarProductosProveedor() {
      if (!this.devProv.proveedor_id) { this.productosProveedor = []; return }
      const res = await axios.get('/productos/', { params: { proveedor_id: this.devProv.proveedor_id } })
      this.productosProveedor = Array.isArray(res.data) ? res.data : (res.data.productos || [])
    },

    seleccionarProductoProv() {
      const prod = this.productosProveedor.find(p => p.id === this.devProv.producto_id)
      if (prod) {
        this.devProv.nombre_producto = prod.nombre
        this.devProv.costo_unitario  = parseFloat(prod.costo_usd || 0)
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
        await this.cargarProveedor()
        alert('Devolución a proveedor registrada')
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al registrar'
      }
    },

    async resolver(id) {
      if (!confirm('¿Marcar esta devolución como resuelta?')) return
      try {
        await axios.put(`/devoluciones/proveedor/${id}/resolver`)
        await this.cargarProveedor()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error')
      }
    },

    // ─── Cliente — paso 1: búsqueda de cliente ───────────────────────────────

    buscarClienteDevolucion() {
      clearTimeout(this.busqClienteTimer)
      const q = this.busqClienteTexto.trim()
      if (q.length < 3) { this.busqClienteResultados = []; return }
      this.busqClienteTimer = setTimeout(async () => {
        try {
          const res = await axios.get('/clientes/buscar-rapido', { params: { q } })
          this.busqClienteResultados = res.data
        } catch (_) { this.busqClienteResultados = [] }
      }, 200)
    },

    seleccionarClienteDevolucion(c) {
      this.clienteDevolucion     = c
      this.busqClienteTexto      = ''
      this.busqClienteResultados = []
      this.modoSinCliente        = false
      // Reset results
      this.ventasEncontradas     = []
      this.ventasExpandidas      = {}
      this.busqRealizada         = false
      this.busqFecha             = 'hoy'
    },

    limpiarClienteDevolucion() {
      this.clienteDevolucion     = null
      this.modoSinCliente        = false
      this.busqClienteTexto      = ''
      this.busqClienteResultados = []
      this.ventasEncontradas     = []
      this.ventasExpandidas      = {}
      this.busqRealizada         = false
    },

    // ─── Cliente — paso 2: búsqueda de ventas ────────────────────────────────

    async buscarVentas() {
      const expandidasAntes  = { ...this.ventasExpandidas }
      this.buscando          = true
      this.busqRealizada     = true
      this.ventasEncontradas = []
      this.ventasExpandidas  = {}
      this.error             = ''
      try {
        const params = {}

        // Identificar el cliente
        if (this.clienteDevolucion) {
          params.cliente_id = this.clienteDevolucion.id
        } else {
          params.solo_consumidor_final = true
        }

        // Fechas
        const hoy  = new Date()
        const ayer = new Date(hoy); ayer.setDate(ayer.getDate() - 1)
        const fmt  = d => d.toISOString().split('T')[0]

        if (this.busqFecha === 'hoy') {
          params.fecha_inicio = fmt(hoy)
          params.fecha_fin    = fmt(hoy)
        } else if (this.busqFecha === 'ayer') {
          params.fecha_inicio = fmt(ayer)
          params.fecha_fin    = fmt(ayer)
        } else if (this.busqFecha === 'rango') {
          params.fecha_inicio = this.busqFechaInicio
          params.fecha_fin    = this.busqFechaFin
        }

        const res = await axios.get('/devoluciones/buscar-ventas', { params })
        this.ventasEncontradas = res.data

        const nuevasExpandidas = {}
        res.data.forEach(v => {
          if (expandidasAntes[v.venta_id]) nuevasExpandidas[v.venta_id] = true
        })
        if (res.data.length === 1) nuevasExpandidas[res.data[0].venta_id] = true
        this.ventasExpandidas = nuevasExpandidas
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al buscar ventas'
      } finally {
        this.buscando = false
      }
    },

    toggleVenta(id) {
      this.ventasExpandidas = {
        ...this.ventasExpandidas,
        [id]: !this.ventasExpandidas[id],
      }
    },

    // ─── Modal ───────────────────────────────────────────────────────────────

    abrirModal(venta, producto) {
      this.modalVenta                = venta
      this.modalProducto             = {
        ...producto,
        venta_id:       venta.venta_id,
        cliente_nombre: venta.cliente_nombre,
        cliente_id:     venta.cliente_id,
        es_consumidor:  venta.es_consumidor,
      }
      this.modalCantidad             = 1
      this.modalTipo                 = 'reembolso'
      this.modalMetodoPago           = 'efectivo_usd'
      this.modalObservacion          = ''
      this.busqProductoNuevo         = ''
      this.productosNuevoResultados  = []
      this.productoNuevoSeleccionado = null
      this.indiceResaltadoCambio     = -1
      this.cantidadNueva             = 1
      this.modalMoneda               = 'USD'
      this.resolucionDiferencia      = 'devolver'
      this.procesando                = false
      this.modalAbierto              = true
    },

    cerrarModal() {
      this.modalAbierto = false
    },

    async buscarProductoNuevo() {
      this.indiceResaltadoCambio    = -1
      this.productoNuevoSeleccionado = null
      const q = this.busqProductoNuevo.trim()
      if (q.length < 2) { this.productosNuevoResultados = []; return }
      try {
        const res = await axios.get('/productos/', { params: { busqueda: q, limit: 20 } })
        this.productosNuevoResultados = Array.isArray(res.data) ? res.data : (res.data.productos || [])
      } catch (_) {}
    },

    moverAbajoCambio() {
      if (!this.productosNuevoResultados.length) return
      this.indiceResaltadoCambio = (this.indiceResaltadoCambio + 1) % this.productosNuevoResultados.length
      this._scrollCambio()
    },

    moverArribaCambio() {
      if (!this.productosNuevoResultados.length) return
      this.indiceResaltadoCambio = (this.indiceResaltadoCambio - 1 + this.productosNuevoResultados.length) % this.productosNuevoResultados.length
      this._scrollCambio()
    },

    seleccionarResaltadoCambio() {
      if (this.indiceResaltadoCambio >= 0 && this.productosNuevoResultados[this.indiceResaltadoCambio]) {
        this.seleccionarProductoNuevo(this.productosNuevoResultados[this.indiceResaltadoCambio])
      }
    },

    _scrollCambio() {
      this.$nextTick(() => {
        const el = this.$refs.dropdownCambio
        if (!el) return
        const item = el.children[this.indiceResaltadoCambio]
        if (item) item.scrollIntoView({ block: 'nearest' })
      })
    },

    seleccionarProductoNuevo(prod) {
      this.productoNuevoSeleccionado = prod
      this.busqProductoNuevo         = prod.nombre
      this.productosNuevoResultados  = []
      this.indiceResaltadoCambio     = -1
    },

    async procesarDevolucion() {
      if (!this.puedeConfirmar || this.procesando) return
      this.procesando = true
      this.error      = ''
      try {
        const payload = {
          detalle_id:        this.modalProducto.detalle_id,
          cantidad_devuelta: this.modalCantidad,
          tipo:              this.modalTipo,
          usuario:           this.usuario.usuario || 'admin',
          observacion:       this.modalObservacion || null,
          metodo_pago:       this.modalTipo !== 'credito' ? this.modalMetodoPago : null,
        }
        payload.moneda   = this.modalMoneda
        payload.tasa_bcv = this.tasaBcv
        if (this.modalTipo === 'cambio' && this.productoNuevoSeleccionado) {
          payload.producto_nuevo_id    = this.productoNuevoSeleccionado.id
          payload.cantidad_nueva       = this.cantidadNueva
          payload.monto_diferencia     = Math.abs(this.diferenciaCambio)
          payload.direccion_diferencia = this.diferenciaCambio > 0
            ? 'cobrar'
            : this.diferenciaCambio < 0
              ? (this.resolucionDiferencia === 'credito' ? 'credito_cliente' : 'devolver')
              : 'ninguna'
        }
        await axios.post('/devoluciones/cliente/procesar', payload)
        this.cerrarModal()
        await this.buscarVentas()
        alert('Devolución procesada correctamente')
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al procesar la devolución'
      } finally {
        this.procesando = false
      }
    },

    formatFecha(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleDateString('es-VE')
    },
  },
}
</script>

<style scoped>
/* Tabs principales */
.tabs       { display: flex; gap: 0; margin-bottom: 1.5rem; border-bottom: 2px solid var(--borde); }
.tab        { background: transparent; border: none; border-bottom: 2px solid transparent; padding: 0.6rem 1.2rem; cursor: pointer; font-size: 0.9rem; color: var(--texto-muted); margin-bottom: -2px; transition: all 0.15s; }
.tab-activo { color: #1A1A1A; border-bottom-color: #FFCC00; font-weight: 700; }

/* Card form */
.card-form    { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; }

/* Búsqueda de cliente (paso 1) */
.busq-cliente-wrap   { position: relative; margin-bottom: 0.5rem; }
.input-busq-cliente  { width: 100%; padding: 0.55rem 0.85rem; border: 1px solid var(--borde); border-radius: 8px; font-size: 0.9rem; box-sizing: border-box; }
.input-busq-cliente:focus { outline: none; border-color: #FFCC00; }

.dropdown-cli      { position: absolute; top: calc(100% + 4px); left: 0; right: 0; background: #FFFFFF; border: 1px solid var(--borde); border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); z-index: 50; }
.cli-opcion        { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 0.85rem; cursor: pointer; font-size: 0.88rem; border-bottom: 1px solid var(--borde-suave); }
.cli-opcion:hover  { background: #FAFAF7; }
.cli-opcion:last-child { border-bottom: none; }
.cli-tel           { color: #1A1A1A; font-weight: 600; }
.cli-nombre        { color: var(--texto-sec); }

.link-sin-cliente  { background: none; border: none; color: var(--texto-muted); font-size: 0.8rem; cursor: pointer; padding: 0; text-decoration: underline; }
.link-sin-cliente:hover { color: #1A1A1A; }

/* Cliente elegido */
.cliente-elegido   { display: flex; align-items: center; justify-content: space-between; background: #F0FDF4; border: 1px solid #16A34A33; border-radius: 8px; padding: 0.55rem 0.85rem; margin-bottom: 1rem; }
.elegido-info      { display: flex; align-items: center; gap: 0.5rem; font-size: 0.88rem; }
.elegido-check     { color: #16A34A; font-weight: 700; }
.elegido-tel       { color: #1A1A1A; font-weight: 600; }
.elegido-nombre    { color: var(--texto-sec); }
.elegido-cf .elegido-nombre { color: #1A1A1A; font-weight: 600; }
.btn-cambiar-cli   { background: transparent; border: 1px solid var(--borde); color: var(--texto-sec); padding: 0.25rem 0.65rem; border-radius: 5px; cursor: pointer; font-size: 0.8rem; }
.btn-cambiar-cli:hover { border-color: #1A1A1A; color: #1A1A1A; }

/* Período (paso 2) */
.periodo-wrap   { margin-top: 0.25rem; }
.periodo-label  { font-size: 0.82rem; font-weight: 600; color: var(--texto-sec); margin: 0 0 0.5rem; }
.fecha-botones  { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
.btn-fecha      { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 6px; padding: 0.4rem 0.85rem; cursor: pointer; font-size: 0.85rem; color: var(--texto-sec); transition: all 0.15s; }
.btn-fecha:hover  { border-color: #1A1A1A; }
.btn-fecha-activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; font-weight: 700; }
.fecha-rango    { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.fecha-rango input { padding: 0.4rem 0.6rem; border: 1px solid var(--borde); border-radius: 6px; font-size: 0.85rem; }
.fecha-sep      { color: var(--texto-muted); }
.btn-buscar     { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.4rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 700; }
.btn-buscar:disabled { opacity: 0.5; cursor: not-allowed; }
.buscando-msg   { font-size: 0.82rem; color: var(--texto-muted); margin-top: 0.4rem; }

/* Resultados */
.resultados-meta { font-size: 0.82rem; color: var(--texto-muted); margin-bottom: 0.75rem; }
.sin-resultados  { text-align: center; padding: 2rem; color: var(--texto-muted); font-size: 0.9rem; background: #FFFFFF; border: 1px solid var(--borde); border-radius: 10px; }

/* Tarjetas de venta */
.venta-card    { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 10px; margin-bottom: 0.75rem; overflow: hidden; }
.venta-header  { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; cursor: pointer; user-select: none; transition: background 0.12s; }
.venta-header:hover { background: #FAFAF7; }
.venta-info    { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.venta-id      { font-weight: 700; font-size: 0.88rem; color: #1A1A1A; }
.venta-cliente { font-size: 0.88rem; color: #1A1A1A; }
.venta-fecha   { font-size: 0.8rem; }
.venta-derecha { display: flex; align-items: center; gap: 0.75rem; }
.venta-total   { font-weight: 700; font-size: 0.9rem; color: #16A34A; }
.venta-flecha  { font-size: 0.65rem; color: var(--texto-muted); }

.venta-productos { border-top: 1px solid var(--borde); padding: 0.5rem 0.75rem; display: flex; flex-direction: column; gap: 0.4rem; }
.prod-row        { display: flex; justify-content: space-between; align-items: center; padding: 0.45rem 0.5rem; border-radius: 6px; background: #FAFAF7; }
.prod-row-info   { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; flex: 1; }
.prod-nombre     { font-size: 0.87rem; font-weight: 600; color: #1A1A1A; }
.prod-cant       { font-size: 0.8rem; }
.prod-precio     { font-size: 0.8rem; }
.btn-devolver    { background: #DC2626; color: #FFFFFF; border: none; padding: 0.3rem 0.7rem; border-radius: 5px; cursor: pointer; font-size: 0.8rem; font-weight: 700; white-space: nowrap; flex-shrink: 0; }
.btn-devolver:hover { background: #B91C1C; }
.badge-devuelto  { background: #DC26261A; color: #DC2626; font-size: 0.73rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 20px; flex-shrink: 0; }
.badge-parcial   { background: #FFCC0033; color: #996600; font-size: 0.73rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 20px; flex-shrink: 0; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
.modal-box     { background: #FFFFFF; border-radius: 14px; width: 100%; max-width: 520px; max-height: 90vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }

.modal-header  { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.25rem 0.75rem; border-bottom: 1px solid var(--borde); }
.modal-header h3 { font-size: 1rem; font-weight: 700; margin: 0; color: #1A1A1A; }
.modal-cerrar  { background: transparent; border: none; font-size: 1rem; cursor: pointer; color: var(--texto-muted); padding: 0.2rem 0.4rem; border-radius: 4px; }
.modal-cerrar:hover { background: #F3F4F6; color: #1A1A1A; }

.modal-prod-info { display: flex; flex-direction: column; gap: 0.2rem; padding: 0.85rem 1.25rem; background: #FAFAF7; border-bottom: 1px solid var(--borde); }
.modal-prod-info strong { font-size: 0.95rem; color: #1A1A1A; }

.modal-field       { padding: 0.6rem 1.25rem; display: flex; flex-direction: column; gap: 0.3rem; }
.modal-field label { font-size: 0.8rem; font-weight: 600; color: var(--texto-sec); }
.modal-field input, .modal-field select { padding: 0.4rem 0.7rem; border: 1px solid var(--borde); border-radius: 6px; font-size: 0.88rem; }
.modal-label-sec   { padding: 0.4rem 1.25rem 0; font-size: 0.8rem; font-weight: 600; color: var(--texto-sec); }
.cant-row          { display: flex; align-items: center; gap: 0.5rem; }
.inp-cant          { width: 80px; }
.mt-50             { margin-top: 0.5rem; }

.modal-opciones   { display: flex; gap: 0.6rem; padding: 0.5rem 1.25rem 0.75rem; }
.opcion-card      { flex: 1; display: flex; align-items: center; gap: 0.5rem; padding: 0.65rem 0.75rem; border: 2px solid var(--borde); border-radius: 10px; cursor: pointer; transition: all 0.15s; background: #FAFAF7; }
.opcion-card:hover { border-color: #1A1A1A; }
.opcion-activa    { border-color: #FFCC00 !important; background: #FFCC0018 !important; }
.opcion-icono     { font-size: 1.2rem; flex-shrink: 0; }
.opcion-titulo    { font-size: 0.82rem; font-weight: 700; color: #1A1A1A; }
.opcion-desc      { font-size: 0.73rem; color: var(--texto-muted); }

.modal-sub { border-top: 1px solid var(--borde); padding-top: 0.25rem; padding-bottom: 0.5rem; }

.monto-preview-modal { margin: 0 1.25rem 0.5rem; background: #FFCC0022; border: 1px solid #FFCC00; border-radius: 6px; padding: 0.45rem 0.85rem; font-size: 0.88rem; color: #1A1A1A; }

.busq-prod-wrap { position: relative; }
.busq-prod-wrap input { width: 100%; padding: 0.4rem 0.7rem; border: 1px solid var(--borde); border-radius: 6px; font-size: 0.88rem; box-sizing: border-box; }
.dropdown-prod  { position: absolute; top: calc(100% + 4px); left: 0; right: 0; background: #FFFFFF; border: 1px solid var(--borde); border-radius: 8px; box-shadow: 0 6px 20px rgba(0,0,0,0.12); z-index: 200; max-height: 200px; overflow-y: auto; }
.drop-item      { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0.75rem; cursor: pointer; transition: background 0.1s; font-size: 0.85rem; }
.drop-item:hover { background: #F9FAFB; }
.drop-item-resaltado { background: #FFCC00 !important; color: #1A1A1A !important; }
.drop-nombre    { font-weight: 500; }
.drop-precio    { font-size: 0.8rem; }

.prod-nuevo-info { display: flex; gap: 0.75rem; align-items: center; margin: 0.25rem 1.25rem 0.5rem; padding: 0.5rem 0.75rem; background: #FAFAF7; border: 1px solid var(--borde); border-radius: 7px; font-size: 0.85rem; flex-wrap: wrap; }
.prod-nv-nombre  { font-weight: 600; color: #1A1A1A; }

.monto-info  { margin: 0.25rem 1.25rem 0.5rem; background: var(--borde-suave); border: 1px solid var(--borde); border-radius: 8px; padding: 0.6rem 0.85rem; display: flex; flex-direction: column; gap: 0.25rem; }
.monto-fila  { display: flex; justify-content: space-between; font-size: 0.87rem; color: var(--texto-sec); }
.cambio-resumen { background: var(--borde-suave); border-radius: 8px; padding: 0.75rem; margin: 0.75rem 1.25rem 0.5rem; display: flex; flex-direction: column; gap: 0.3rem; }
.cambio-fila { display: flex; justify-content: space-between; font-size: 0.9rem; color: var(--texto-sec); }
.cambio-diff { font-weight: 700; font-size: 1rem; border-top: 1px solid var(--borde); padding-top: 0.4rem; margin-top: 0.2rem; }
.btn-moneda { padding: 0.4rem 1rem; background: #FFFFFF; border: 1px solid var(--borde); border-radius: 6px; cursor: pointer; font-size: 0.88rem; font-weight: 600; color: var(--texto-sec); }
.btn-moneda.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }
.btn-opcion { padding: 0.5rem 1rem; background: #FFFFFF; border: 1px solid var(--borde); border-radius: 6px; cursor: pointer; font-size: 0.85rem; color: var(--texto-sec); }
.btn-opcion.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }
.btn-group { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.diferencia-box { margin: 0.25rem 1.25rem 0.5rem; padding: 0.6rem 0.85rem; border-radius: 7px; font-size: 0.87rem; }
.dif-cobrar     { background: #DCFCE7; border: 1px solid #16A34A33; }
.dif-devolver   { background: #FEE2E2; border: 1px solid #DC262633; }
.dif-igual      { background: #F3F4F6; border: 1px solid var(--borde); color: var(--texto-muted); }

.credito-info-box { display: flex; align-items: center; gap: 0.75rem; margin: 0.5rem 1.25rem; padding: 0.75rem 1rem; background: #F0FDF4; border: 1px solid #16A34A33; border-radius: 8px; font-size: 0.88rem; }

.modal-footer  { display: flex; justify-content: flex-end; gap: 0.6rem; padding: 0.85rem 1.25rem; border-top: 1px solid var(--borde); }
.btn-cancelar  { background: #F3F4F6; color: #1A1A1A; border: 1px solid var(--borde); padding: 0.45rem 1rem; border-radius: 7px; cursor: pointer; font-size: 0.87rem; font-weight: 600; }
.btn-cancelar:hover { background: #E5E7EB; }
.btn-confirmar { border: none; padding: 0.45rem 1.1rem; border-radius: 7px; cursor: pointer; font-size: 0.87rem; font-weight: 700; }
.btn-confirmar:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-rojo      { background: #DC2626; color: #FFFFFF; }
.btn-rojo:hover:not(:disabled) { background: #B91C1C; }
.btn-negro     { background: #1A1A1A; color: #FFCC00; }
.btn-negro:hover:not(:disabled) { background: #333333; }

/* Texto */
.txt-verde  { color: #16A34A; }
.txt-rojo   { color: #DC2626; }
.txt-muted  { color: var(--texto-muted); font-size: 0.82rem; }

/* Proveedor tab */
.monto-preview { background: #FFCC0022; border: 1px solid #FFCC00; border-radius: 6px; padding: 0.5rem 1rem; font-size: 0.88rem; color: #1A1A1A; margin: 0.75rem 0; }
.alerta-pendientes { background: #FFCC0022; border-left: 4px solid #FFCC00; padding: 0.6rem 1rem; border-radius: 4px; font-size: 0.88rem; margin-bottom: 1rem; }
.badge-tipo          { display: inline-block; padding: 0.18rem 0.55rem; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }
.badge-credito       { background: #16A34A1A; color: #16A34A; }
.badge-resuelto      { background: #16A34A1A; color: #16A34A; }
.badge-pendiente-dev { background: #FFCC0033; color: #996600; }
.btn-resolver { background: #16A34A; color: white; border: none; padding: 0.25rem 0.65rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
</style>