<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Facturas IA</h1>
      </div>

      <div class="contenido-inner">

        <!-- ══ PASO 1 ══════════════════════════════════════════════════ -->
        <template v-if="paso === 1">
          <div
            class="dropzone"
            :class="{ 'dz-over': dragging }"
            @dragover.prevent="dragging = true"
            @dragleave.prevent="dragging = false"
            @drop.prevent="onDrop"
            @click="$refs.fileInput.click()"
          >
            <input
              ref="fileInput"
              type="file"
              accept="image/*,.pdf"
              style="display:none"
              @change="onFileChange"
            />
            <div v-if="!archivoSeleccionado" class="dz-empty">
              <span class="dz-icon">📄</span>
              <p>Arrastra la factura aquí o <strong>haz clic para seleccionar</strong></p>
              <small>JPEG, PNG, WebP, GIF o PDF</small>
            </div>
            <div v-else class="dz-file">
              <img v-if="previewUrl" :src="previewUrl" class="dz-img" />
              <div v-else class="dz-pdf">
                <span class="dz-icon">📑</span>
                <span class="dz-pdf-name">{{ archivoSeleccionado.name }}</span>
              </div>
              <button class="btn-quitar-archivo" @click.stop="quitarArchivo">✕</button>
            </div>
          </div>

          <div class="paso1-acciones">
            <button
              class="btn-escanear"
              :disabled="!archivoSeleccionado || escaneando"
              @click="escanear"
            >
              <span v-if="escaneando">⏳ Analizando con IA...</span>
              <span v-else>🔍 Escanear con IA</span>
            </button>
          </div>
          <p v-if="errorScan" class="msg-error">{{ errorScan }}</p>
        </template>

        <!-- ══ PASO 2 ══════════════════════════════════════════════════ -->
        <template v-if="paso === 2">
          <div class="paso2-header">
            <button class="btn-volver" @click="paso = 1">← Volver</button>
            <h2 class="paso2-titulo">Revisión de factura</h2>
          </div>

          <!-- Datos generales -->
          <div class="card-seccion">
            <div class="datos-generales">
              <div class="field-group" style="flex:2; min-width:220px">
                <label class="field-label">Proveedor</label>
                <div class="search-wrap">
                  <input
                    v-model="proveedorBusq"
                    class="input-field"
                    placeholder="Buscar proveedor..."
                    @input="buscarProveedor"
                    @focus="abrirProvDropdown"
                    @blur="cerrarProvDropdown"
                  />
                  <ul v-if="provAbierta && provResultados.length" class="dropdown-list">
                    <li
                      v-for="p in provResultados"
                      :key="p.id"
                      @mousedown="seleccionarProveedor(p)"
                    >
                      <strong>{{ p.nombre }}</strong>
                      <small v-if="p.rif"> · {{ p.rif }}</small>
                    </li>
                  </ul>
                  <div v-if="provAbierta && !provResultados.length && proveedorBusq.length >= 2" class="dropdown-vacio">
                    <span>Sin resultados</span>
                    <button class="btn-crear-prov" @mousedown.prevent="abrirModalProveedor">+ Crear proveedor</button>
                  </div>
                </div>
                <div v-if="proveedorId" class="prov-seleccionado">
                  ✓ {{ proveedorBusq }}
                  <span class="prov-desvincular" @click="limpiarProveedor">✕</span>
                </div>
              </div>

              <!-- Modal crear proveedor -->
              <div v-if="modalProveedor" class="modal-overlay" @click.self="modalProveedor = false">
                <div class="modal-box">
                  <div class="modal-header">
                    <h3>Nuevo proveedor</h3>
                    <button class="btn-cerrar-modal" @click="modalProveedor = false">✕</button>
                  </div>
                  <div class="modal-body">
                    <div class="field-group">
                      <label class="field-label">Nombre *</label>
                      <input v-model="nuevoProv.nombre" class="input-field" placeholder="Nombre del proveedor" />
                    </div>
                    <div class="field-group">
                      <label class="field-label">RIF</label>
                      <input v-model="nuevoProv.rif" class="input-field" placeholder="J-12345678-9" />
                    </div>
                    <div class="field-group">
                      <label class="field-label">Teléfono</label>
                      <input v-model="nuevoProv.telefono" class="input-field" placeholder="04XX-XXXXXXX" />
                    </div>
                    <div class="field-group">
                      <label class="field-label">Contacto</label>
                      <input v-model="nuevoProv.contacto" class="input-field" placeholder="Nombre del contacto" />
                    </div>
                    <p v-if="errorNuevoProv" class="msg-error">{{ errorNuevoProv }}</p>
                  </div>
                  <div class="modal-footer">
                    <button class="btn-condicion" @click="modalProveedor = false">Cancelar</button>
                    <button class="btn-confirmar" style="width:auto;padding:0.6rem 1.5rem" @click="crearProveedor" :disabled="creandoProv">
                      {{ creandoProv ? 'Guardando...' : 'Guardar proveedor' }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- Modal renombrar proveedor -->
              <div v-if="modalRenombrar && proveedorPendiente" class="modal-overlay" @click.self="modalRenombrar = false">
                <div class="modal-box">
                  <div class="modal-header">
                    <h3>Nombre del proveedor</h3>
                    <button class="btn-cerrar-modal" @click="modalRenombrar = false">✕</button>
                  </div>
                  <div class="modal-body">
                    <p style="color:var(--texto-sec);font-size:0.9rem;margin:0 0 0.75rem">
                      La factura indica un nombre diferente al registrado en el sistema:
                    </p>
                    <div class="renombrar-comparacion">
                      <div class="renombrar-fila">
                        <span class="renombrar-etiqueta">En factura</span>
                        <span class="renombrar-valor txt-amarillo">{{ proveedorNombreIA }}</span>
                      </div>
                      <div class="renombrar-fila">
                        <span class="renombrar-etiqueta">En sistema</span>
                        <span class="renombrar-valor">{{ proveedorPendiente.nombre }}</span>
                      </div>
                    </div>
                    <p style="color:var(--texto-sec);font-size:0.88rem;margin:0.75rem 0 0">
                      ¿Deseas actualizar el nombre oficial del proveedor al de la factura?
                    </p>
                  </div>
                  <div class="modal-footer">
                    <button class="btn-condicion" @click="_confirmarProveedor(proveedorPendiente, false)">
                      No, mantener "{{ proveedorPendiente.nombre }}"
                    </button>
                    <button class="btn-confirmar" style="width:auto;padding:0.6rem 1.5rem"
                      @click="renombrarYConfirmar">
                      Sí, usar "{{ proveedorNombreIA }}"
                    </button>
                  </div>
                </div>
              </div>

              <div class="field-group">
                <label class="field-label">Nº Factura</label>
                <input v-model="numeroFactura" class="input-field" placeholder="FAC-001" />
              </div>
              <div class="field-group">
                <label class="field-label">Fecha</label>
                <input v-model="fechaFactura" type="date" class="input-field" />
              </div>
            </div>
          </div>

          <!-- Selector OC existente -->
          <div v-if="ordenesDisponibles.length" class="card-seccion oc-selector-card">
            <h3 class="seccion-titulo">¿Vincular a orden de compra existente?</h3>
            <div class="oc-opciones">
              <div
                class="oc-opcion"
                :class="{ 'oc-opcion-activa': ordenSeleccionada === null }"
                @click="desvincularOrden"
              >
                <span class="oc-badge nuevo">Nueva</span>
                <span class="oc-label">Crear OC nueva</span>
              </div>
              <div
                v-for="oc in ordenesDisponibles"
                :key="oc.id"
                class="oc-opcion"
                :class="{ 'oc-opcion-activa': ordenSeleccionada && ordenSeleccionada.id === oc.id }"
                @click="seleccionarOrden(oc)"
              >
                <span class="oc-badge" :class="oc.estado === 'aprobada' ? 'aprobada' : 'parcial'">
                  {{ oc.estado === 'aprobada' ? 'Aprobada' : 'Parcial' }}
                </span>
                <span class="oc-label">{{ oc.numero }}</span>
                <span class="oc-total">${{ oc.total.toFixed(2) }}</span>
                <span class="oc-items">{{ oc.detalles.length }} ítem{{ oc.detalles.length !== 1 ? 's' : '' }}</span>
              </div>
            </div>
            <small v-if="ordenSeleccionada" class="txt-muted" style="margin-top:0.5rem;display:block">
              Productos pre-cargados desde {{ ordenSeleccionada.numero }}. Puedes ajustar cantidades y precios.
            </small>
          </div>

          <!-- Tabla de productos -->
          <div class="card-seccion">
            <h3 class="seccion-titulo">
              Productos
              <span class="badge-count">{{ lineas.length }}</span>
            </h3>
            <div class="tabla-scroll">
              <table class="tabla-productos">
                <thead>
                  <tr>
                    <th class="th-num">#</th>
                    <th style="min-width:140px">Nombre detectado</th>
                    <th style="min-width:210px">Producto en inventario</th>
                    <th style="min-width:110px">Cod. proveedor</th>
                    <th style="min-width:80px; text-align:right">Cantidad</th>
                    <th style="min-width:100px; text-align:right">Precio USD</th>
                    <th style="min-width:90px; text-align:right">Subtotal</th>
                    <th class="th-num" style="min-width:60px">Act. costo</th>
                    <th class="th-num"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(linea, idx) in lineas" :key="idx">
                    <td class="tc dim">{{ idx + 1 }}</td>
                    <td><span class="nombre-ia">{{ linea.nombre_ia || '—' }}</span></td>
                    <td style="position:relative">
                      <div class="match-estado">
                        <span v-if="linea.buscandoMatch" class="match-buscando">⏳ buscando...</span>
                        <template v-else>
                          <span
                            v-if="linea.match"
                            class="match-ok"
                            @click="limpiarMatch(linea)"
                            title="Clic para desvincular"
                          >✓ {{ linea.match.nombre }}</span>
                          <span v-else class="match-sin">Sin match</span>
                        </template>
                      </div>
                      <div style="position:relative; margin-top:4px">
                        <input
                          v-model="linea._busqTexto"
                          class="input-field input-sm"
                          placeholder="Buscar en inventario..."
                          @input="buscarProductoLinea(linea)"
                          @focus="abrirLineaDropdown(linea)"
                          @blur="cerrarLineaDropdown(linea)"
                        />
                        <ul
                          v-if="linea._busqAbierta && linea._busqResultados.length"
                          class="dropdown-list dropdown-sm"
                        >
                          <li
                            v-for="prod in linea._busqResultados"
                            :key="prod.id"
                            @mousedown="seleccionarMatch(linea, prod)"
                          >
                            {{ prod.nombre }}
                            <small v-if="prod.codigo"> ({{ prod.codigo }})</small>
                            <small class="stock-hint"> · Stock: {{ prod.stock }}</small>
                          </li>
                        </ul>
                      </div>
                    </td>
                    <td>
                      <input
                        v-model="linea.codigo_proveedor"
                        class="input-field input-sm"
                        placeholder="—"
                      />
                    </td>
                    <td>
                      <input
                        v-model.number="linea.cantidad"
                        type="number"
                        min="1"
                        class="input-field input-sm tr"
                      />
                    </td>
                    <td>
                      <input
                        v-model.number="linea.precio_unitario"
                        type="number"
                        step="0.01"
                        min="0"
                        class="input-field input-sm tr"
                      />
                    </td>
                    <td class="tr dim">{{ fmtUSD(linea.cantidad * linea.precio_unitario) }}</td>
                    <td class="tc">
                      <input
                        type="checkbox"
                        v-model="linea.actualizar_costo"
                        :disabled="!linea.match"
                        title="Actualizar costo en inventario"
                      />
                    </td>
                    <td class="tc">
                      <button
                        class="btn-del-linea"
                        @click="lineas.splice(idx, 1)"
                        title="Eliminar línea"
                      >✕</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <button class="btn-add-linea" @click="agregarLinea">+ Agregar línea</button>
          </div>

          <!-- Pago y resumen -->
          <div class="card-seccion pago-resumen-grid">
            <div class="pago-col">
              <h3 class="seccion-titulo">Condición de pago</h3>
              <div class="condicion-grupo">
                <button
                  v-for="op in condicionOpciones"
                  :key="op.val"
                  class="btn-condicion"
                  :class="{ active: condicionPago === op.val }"
                  @click="condicionPago = op.val; pagos = []"
                >{{ op.label }}</button>
              </div>

              <!-- Descuento en % -->
              <div class="field-group" style="margin-top:1rem">
                <label class="field-label">¿La factura tiene descuento?</label>
                <div class="btn-group">
                  <button
                    :class="['btn-condicion', !tieneDescuento ? 'active' : '']"
                    @click="tieneDescuento = false; descuentoPct = 0"
                  >No</button>
                  <button
                    :class="['btn-condicion', tieneDescuento ? 'active' : '']"
                    @click="tieneDescuento = true"
                  >Sí</button>
                </div>
              </div>
              <div v-if="tieneDescuento" class="field-group" style="margin-top:0.5rem">
                <label class="field-label">Descuento del proveedor (%)</label>
                <div style="display:flex;gap:0.5rem;align-items:center">
                  <input
                    v-model.number="descuentoPct"
                    type="number" min="0" max="100" step="0.1"
                    class="input-field" placeholder="0.0" style="max-width:100px"
                  />
                  <button class="btn-condicion active" @click="aplicarDescuento">Aplicar</button>
                </div>
                <small class="txt-muted" v-if="descuentoPct > 0">
                  Se aplicará {{ descuentoPct }}% a cada producto
                </small>
              </div>

              <!-- Pagos múltiples -->
              <div v-if="condicionPago !== 'credito_completo'" style="margin-top:1rem">
                <label class="field-label">Pagos</label>

                <!-- Lista de pagos agregados -->
                <div v-for="(p, i) in pagos" :key="i" class="pago-item">
                  <span class="pago-metodo">{{ p.label }}</span>
                  <span class="pago-cuenta" v-if="p.cuenta_nombre">· {{ p.cuenta_nombre }}</span>
                  <span class="pago-monto">{{ p.moneda === 'USD' ? '$' : 'Bs.' }}{{ p.monto.toFixed(2) }}</span>
                  <span class="pago-usd" v-if="p.moneda === 'Bs'">≈ ${{ p.monto_usd.toFixed(2) }}</span>
                  <button class="btn-del-linea" @click="pagos.splice(i, 1)">✕</button>
                </div>

                <!-- Formulario nuevo pago -->
                <div class="nuevo-pago-form" v-if="saldoPendiente > 0.01">
                  <div class="btn-group" style="margin-bottom:0.5rem">
                    <button
                      :class="['btn-condicion', nuevoPagoMoneda === 'USD' ? 'active' : '']"
                      @click="nuevoPagoMoneda = 'USD'; nuevoPagoMetodo = 'efectivo_usd'; nuevoPagoCuentaId = null"
                    >USD</button>
                    <button
                      :class="['btn-condicion', nuevoPagoMoneda === 'Bs' ? 'active' : '']"
                      @click="nuevoPagoMoneda = 'Bs'; nuevoPagoMetodo = 'efectivo_bs'; nuevoPagoCuentaId = null"
                    >Bs</button>
                  </div>
                  <div style="display:flex;gap:0.5rem;flex-wrap:wrap;align-items:center">
                    <select
                      v-model="nuevoPagoMetodo"
                      class="input-field" style="flex:1;min-width:140px"
                      @change="nuevoPagoCuentaId = null"
                    >
                      <option v-for="m in metodosDisponiblesPago" :key="m.value" :value="m.value">{{ m.label }}</option>
                    </select>
                    <select
                      v-if="cuentasDelNuevoPago.length > 1"
                      v-model="nuevoPagoCuentaId"
                      class="input-field" style="flex:1;min-width:140px"
                    >
                      <option :value="null">— Cuenta —</option>
                      <option v-for="c in cuentasDelNuevoPago" :key="c.id" :value="c.id">
                        {{ c.nombre }}{{ c.identificador ? ' · ' + c.identificador : '' }}
                      </option>
                    </select>
                    <span v-else-if="cuentasDelNuevoPago.length === 1" class="cuenta-unica">
                      {{ cuentasDelNuevoPago[0].nombre }}
                    </span>
                    <input
                      v-model.number="nuevoPagoMonto"
                      type="number" min="0.01" step="0.01"
                      :placeholder="nuevoPagoMoneda === 'USD' ? '$0.00' : 'Bs. 0.00'"
                      class="input-field" style="width:110px"
                    />
                    <button class="btn-condicion active" @click="agregarPago">+ Agregar</button>
                  </div>
                  <small class="txt-muted" v-if="tasaBcv">Tasa BCV: Bs. {{ tasaBcv.toFixed(2) }}</small>
                </div>
                <div
                  v-if="saldoPendiente <= 0.01 && pagos.length > 0"
                  class="pagado-row"
                  style="margin-top:0.5rem;font-size:0.85rem"
                >✓ Pago completo</div>
              </div>
            </div>

            <div class="resumen-col">
              <h3 class="seccion-titulo">Resumen</h3>
              <div class="resumen-box">
                <div class="resumen-row total-row">
                  <span>Total factura</span>
                  <span>{{ fmtUSD(totalCalculado) }}</span>
                </div>
                <div v-if="condicionPago !== 'credito_completo' && totalPagado > 0" class="resumen-row abono-row">
                  <span>Pagado</span>
                  <span>{{ fmtUSD(totalPagado) }}</span>
                </div>
                <div
                  class="resumen-row"
                  :class="saldoPendiente > 0.01 ? 'saldo-row' : 'pagado-row'"
                >
                  <span>{{ saldoPendiente > 0.01 ? 'Saldo pendiente' : 'Estado' }}</span>
                  <span>{{ saldoPendiente > 0.01 ? fmtUSD(saldoPendiente) : '✓ Pagado' }}</span>
                </div>
              </div>
              <button
                class="btn-confirmar"
                :disabled="!puedeConfirmar || confirmando"
                @click="confirmarCompra"
              >
                <span v-if="confirmando">⏳ Registrando...</span>
                <span v-else>✓ Confirmar compra</span>
              </button>
              <p v-if="errorConfirmar" class="msg-error">{{ errorConfirmar }}</p>
            </div>
          </div>
        </template>

        <!-- ══ TOAST ÉXITO ═══════════════════════════════════════════ -->
        <div v-if="confirmadoOk" class="toast-exito" @click="confirmadoOk = false">
          <span class="toast-icon">✅</span>
          <div class="toast-body">
            <strong>Compra registrada exitosamente</strong>
            <p>Orden {{ resultadoConfirmar.orden_numero }} · Recepción #{{ resultadoConfirmar.recepcion_id }}</p>
            <p v-if="resultadoConfirmar.saldo_pendiente > 0">
              Saldo pendiente: {{ fmtUSD(resultadoConfirmar.saldo_pendiente) }}
            </p>
            <small>Clic para cerrar</small>
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
  name: 'Facturas',

  data() {
    return {
      paso: 1,
      // Paso 1
      archivoSeleccionado: null,
      previewUrl: null,
      dragging: false,
      escaneando: false,
      errorScan: '',
      // Paso 2 — cabecera
      proveedorId: null,
      proveedorBusq: '',
      provResultados: [],
      provAbierta: false,
      numeroFactura: '',
      fechaFactura: '',
      // Paso 2 — productos
      lineas: [],
      // Paso 2 — descuento
      tieneDescuento: false,
      descuentoPct: 0,
      // Paso 2 — condición de pago
      condicionPago: 'credito_completo',
      condicionOpciones: [
        { val: 'contado',          label: 'Contado'          },
        { val: 'credito_parcial',  label: 'Crédito parcial'  },
        { val: 'credito_completo', label: 'Crédito completo' },
      ],
      // Paso 2 — pagos múltiples
      pagos: [],
      nuevoPagoMetodo:   'efectivo_usd',
      nuevoPagoMoneda:   'USD',
      nuevoPagoCuentaId: null,
      nuevoPagoMonto:    '',
      cuentasPorMetodo:  {},
      tasaBcv:           null,
      // Confirmación
      confirmando: false,
      errorConfirmar: '',
      confirmadoOk: false,
      resultadoConfirmar: {},
      // Modal nuevo proveedor
      modalProveedor: false,
      nuevoProv: { nombre: '', rif: '', telefono: '', contacto: '' },
      errorNuevoProv: '',
      creandoProv: false,
      // Renombrar proveedor
      proveedorNombreIA:  '',
      modalRenombrar:     false,
      proveedorPendiente: null,
      // Selector OC existente
      ordenesDisponibles: [],
      ordenSeleccionada: null,
    }
  },

  async mounted() {
    try {
      const r = await axios.get('/bancos/metodos-pago/cuentas')
      this.cuentasPorMetodo = r.data
    } catch {}
    try {
      const t = await axios.get('/tasa/')
      this.tasaBcv = t.data.tasa
    } catch {}
  },

  computed: {
    subtotalCalculado() {
      return this.lineas.reduce(
        (s, l) => s + (Number(l.cantidad) || 0) * (Number(l.precio_unitario) || 0),
        0,
      )
    },
    totalCalculado() {
      return this.subtotalCalculado
    },
    totalPagado() {
      return this.pagos.reduce((s, p) => s + p.monto_usd, 0)
    },
    saldoPendiente() {
      if (this.condicionPago === 'credito_completo') return this.totalCalculado
      return Math.max(this.totalCalculado - this.totalPagado, 0)
    },
    puedeConfirmar() {
      return this.lineas.length > 0 && this.totalCalculado > 0
    },
    metodosDisponiblesPago() {
      const USD = [
        { value: 'efectivo_usd', label: 'Efectivo $' },
        { value: 'zelle',        label: 'Zelle' },
        { value: 'binance',      label: 'Binance' },
      ]
      const BS = [
        { value: 'efectivo_bs',      label: 'Efectivo Bs' },
        { value: 'transferencia_bs', label: 'Transferencia Bs' },
        { value: 'pago_movil',       label: 'Pago Móvil' },
        { value: 'punto_banesco',    label: 'Punto Banesco' },
        { value: 'punto_provincial', label: 'Punto Provincial' },
      ]
      return this.nuevoPagoMoneda === 'USD' ? USD : BS
    },
    cuentasDelNuevoPago() {
      return this.cuentasPorMetodo[this.nuevoPagoMetodo] || []
    },
  },

  methods: {
    // ── Paso 1 ────────────────────────────────────────────────────────
    onDrop(e) {
      this.dragging = false
      const f = e.dataTransfer.files[0]
      if (f) this.setArchivo(f)
    },
    onFileChange(e) {
      const f = e.target.files[0]
      if (f) this.setArchivo(f)
    },
    setArchivo(f) {
      this.archivoSeleccionado = f
      this.previewUrl = null
      this.errorScan = ''
      if (f.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onload = ev => { this.previewUrl = ev.target.result }
        reader.readAsDataURL(f)
      }
    },
    quitarArchivo() {
      this.archivoSeleccionado = null
      this.previewUrl = null
      this.$refs.fileInput.value = ''
    },
    async escanear() {
      if (!this.archivoSeleccionado) return
      this.escaneando = true
      this.errorScan = ''
      try {
        const fd = new FormData()
        fd.append('archivo', this.archivoSeleccionado)
        const res = await axios.post('/facturas/escanear', fd)
        if (res.data.error) throw new Error(res.data.error)
        this.cargarDatosScan(res.data)
        this.paso = 2
      } catch (e) {
        this.errorScan = e?.response?.data?.detail || e.message || 'Error al procesar la factura.'
      } finally {
        this.escaneando = false
      }
    },

    // ── Carga de datos escaneados ─────────────────────────────────────
    cargarDatosScan(data) {
      this.numeroFactura  = data.numero_factura || ''
      this.fechaFactura   = data.fecha || new Date().toISOString().slice(0, 10)
      this.tieneDescuento = false
      this.descuentoPct   = 0
      this.proveedorBusq     = data.proveedor || ''
      this.proveedorId       = null
      this.proveedorNombreIA = data.proveedor || ''

      this.lineas = (data.productos || []).map(p => ({
        nombre_ia:        p.nombre           || '',
        codigo_proveedor: p.codigo_proveedor  || '',
        cantidad:         Number(p.cantidad)  || 1,
        precio_unitario:  Number(p.precio_unitario) || 0,
        actualizar_costo: true,
        match:            null,
        buscandoMatch:    false,
        _busqTexto:       '',
        _busqResultados:  [],
        _busqAbierta:     false,
      }))

      this.lineas.forEach(l => this.autoMatchProducto(l))
    },

    // ── Descuento % ───────────────────────────────────────────────────
    aplicarDescuento() {
      if (!this.tieneDescuento || !this.descuentoPct) return
      const factor = 1 - (this.descuentoPct / 100)
      this.lineas.forEach(l => {
        l.precio_unitario = Math.round(Number(l.precio_unitario) * factor * 10000) / 10000
      })
      this.tieneDescuento = false
      this.descuentoPct   = 0
    },

    // ── Proveedor ─────────────────────────────────────────────────────
    async buscarProveedorInicial(nombre) {
      try {
        const { data } = await axios.get('/facturas/buscar-proveedor', { params: { nombre } })
        if (data.length === 1) {
          this.seleccionarProveedor(data[0])
        } else if (data.length > 1) {
          this.provResultados = data
          this.provAbierta = true
        }
      } catch {}
    },
    async buscarProveedor() {
      const q = this.proveedorBusq.trim()
      if (q.length < 2) { this.provResultados = []; this.provAbierta = false; return }
      try {
        const { data } = await axios.get('/facturas/buscar-proveedor', { params: { nombre: q } })
        this.provResultados = data
        this.provAbierta = data.length > 0
      } catch {}
    },
    seleccionarProveedor(p) {
      this.provAbierta = false
      const nombreIA      = (this.proveedorNombreIA || '').trim()
      const nombreSistema = (p.nombre || '').trim()
      const sonDiferentes = nombreIA && nombreIA.toLowerCase() !== nombreSistema.toLowerCase()

      if (sonDiferentes) {
        this.proveedorPendiente = p
        this.modalRenombrar     = true
      } else {
        this._confirmarProveedor(p, false)
      }
    },

    _confirmarProveedor(p, renombrar) {
      this.proveedorId        = p.id
      this.proveedorBusq      = renombrar ? this.proveedorNombreIA : p.nombre
      this.proveedorPendiente = null
      this.modalRenombrar     = false
      this.ordenSeleccionada  = null
      this.ordenesDisponibles = []

      const nombreIA = (this.proveedorNombreIA || '').trim()
      if (nombreIA && nombreIA.toLowerCase() !== p.nombre.toLowerCase()) {
        const usuario = JSON.parse(localStorage.getItem('usuario') || '{}').nombre || ''
        axios.post('/facturas/guardar-alias', {
          alias:        nombreIA,
          proveedor_id: p.id,
          usuario,
        }).catch(() => {})
      }

      this.cargarOrdenesPendientes(p.id)
    },

    async renombrarYConfirmar() {
      const p = this.proveedorPendiente
      if (!p) return
      try {
        await axios.put(`/compras/proveedores/${p.id}`, {
          nombre: this.proveedorNombreIA.trim()
        }, {
          headers: { 'x-usuario-rol': 'admin' }
        })
        p.nombre = this.proveedorNombreIA.trim()
      } catch { /* si falla el renombrado, continuar igual */ }
      this._confirmarProveedor(p, true)
    },
    abrirProvDropdown() {
      if (this.provResultados.length) this.provAbierta = true
    },
    cerrarProvDropdown() {
      setTimeout(() => { this.provAbierta = false }, 200)
    },

    // ── Auto-match ────────────────────────────────────────────────────
    async autoMatchProducto(linea) {
      const texto = (linea.codigo_proveedor || linea.nombre_ia || '').trim()
      if (texto.length < 2) return
      linea.buscandoMatch = true
      try {
        const params = { nombre: texto }
        if (this.proveedorId) params.proveedor_id = this.proveedorId
        const { data } = await axios.get('/facturas/buscar-producto', { params })
        if (data.length > 0) {
          linea.match      = data[0]
          linea._busqTexto = data[0].nombre
        }
      } catch {}
      finally { linea.buscandoMatch = false }
    },

    // ── Búsqueda inline por línea ─────────────────────────────────────
    async buscarProductoLinea(linea) {
      const q = linea._busqTexto.trim()
      if (q.length < 2) { linea._busqResultados = []; linea._busqAbierta = false; return }
      try {
        const params = { nombre: q }
        if (this.proveedorId) params.proveedor_id = this.proveedorId
        const { data } = await axios.get('/facturas/buscar-producto', { params })
        linea._busqResultados = data
        linea._busqAbierta    = data.length > 0
      } catch {}
    },
    seleccionarMatch(linea, prod) {
      linea.match           = prod
      linea._busqTexto      = prod.nombre
      linea._busqAbierta    = false
      linea._busqResultados = []
    },
    limpiarMatch(linea) {
      linea.match            = null
      linea._busqTexto       = ''
      linea.actualizar_costo = false
    },
    abrirLineaDropdown(linea) {
      if (linea._busqResultados.length) linea._busqAbierta = true
    },
    cerrarLineaDropdown(linea) {
      setTimeout(() => { linea._busqAbierta = false }, 200)
    },

    // ── Tabla ─────────────────────────────────────────────────────────
    agregarLinea() {
      this.lineas.push({
        nombre_ia: '', codigo_proveedor: '', cantidad: 1, precio_unitario: 0,
        actualizar_costo: true,
        match: null, buscandoMatch: false,
        _busqTexto: '', _busqResultados: [], _busqAbierta: false,
      })
    },

    // ── Pagos múltiples ───────────────────────────────────────────────
    agregarPago() {
      const monto = Number(this.nuevoPagoMonto || 0)
      if (monto <= 0) return
      const cuentas = this.cuentasDelNuevoPago
      if (cuentas.length > 1 && !this.nuevoPagoCuentaId) {
        alert('Selecciona la cuenta destino')
        return
      }
      const cuentaId     = this.nuevoPagoCuentaId || (cuentas.length === 1 ? cuentas[0].id : null)
      const cuentaNombre = cuentas.find(c => c.id === cuentaId)?.nombre || null
      const monto_usd    = this.nuevoPagoMoneda === 'USD'
        ? monto
        : (this.tasaBcv ? monto / this.tasaBcv : monto)
      const label = this.metodosDisponiblesPago.find(m => m.value === this.nuevoPagoMetodo)?.label || this.nuevoPagoMetodo
      this.pagos.push({
        metodo:       this.nuevoPagoMetodo,
        moneda:       this.nuevoPagoMoneda,
        monto,
        monto_usd:    Math.round(monto_usd * 100) / 100,
        cuenta_id:    cuentaId,
        cuenta_nombre: cuentaNombre,
        label,
      })
      this.nuevoPagoMonto = ''
    },

    // ── Confirmar compra ──────────────────────────────────────────────
    async confirmarCompra() {
      this.confirmando    = true
      this.errorConfirmar = ''

      const abonadoReal = this.condicionPago === 'credito_completo' ? 0 : this.totalPagado

      const payload = {
        proveedor_id:        this.proveedorId,
        numero_factura:      this.numeroFactura,
        fecha:               this.fechaFactura || new Date().toISOString().slice(0, 10),
        descuento:           0,
        orden_id_existente:  this.ordenSeleccionada ? this.ordenSeleccionada.id : null,
        total_factura:  this.totalCalculado,
        condicion_pago: this.condicionPago,
        monto_abonado:  abonadoReal,
        metodo_pago:    this.pagos[0]?.metodo || null,
        usuario:        JSON.parse(localStorage.getItem('usuario') || '{}').nombre || 'admin',
        pagos: this.pagos.map(p => ({
          metodo:    p.metodo,
          moneda:    p.moneda,
          monto:     p.monto,
          monto_usd: p.monto_usd,
          cuenta_id: p.cuenta_id,
        })),
        productos: this.lineas.map(l => ({
          producto_id:         l.match?.id        || null,
          nombre_producto:     l.match?.nombre    || l.nombre_ia,
          codigo_proveedor:    l.codigo_proveedor || '',
          cantidad:            Number(l.cantidad) || 0,
          precio_unitario_usd: Number(l.precio_unitario) || 0,
          subtotal:            Math.round((Number(l.cantidad) * Number(l.precio_unitario)) * 100) / 100,
          actualizar_costo:    l.actualizar_costo && !!l.match,
        })),
      }

      try {
        const { data } = await axios.post('/facturas/confirmar-compra', payload)
        this.resultadoConfirmar = data
        this.confirmadoOk = true
        setTimeout(() => {
          this.confirmadoOk = false
          this.resetearFormulario()
        }, 7000)
      } catch (e) {
        this.errorConfirmar = e?.response?.data?.detail || e.message || 'Error al registrar compra.'
      } finally {
        this.confirmando = false
      }
    },

    resetearFormulario() {
      this.paso                = 1
      this.archivoSeleccionado = null
      this.previewUrl          = null
      this.lineas              = []
      this.proveedorId         = null
      this.proveedorBusq       = ''
      this.provResultados      = []
      this.numeroFactura       = ''
      this.fechaFactura        = ''
      this.tieneDescuento      = false
      this.descuentoPct        = 0
      this.condicionPago       = 'credito_completo'
      this.pagos               = []
      this.nuevoPagoMonto      = ''
      this.nuevoPagoMoneda     = 'USD'
      this.nuevoPagoMetodo     = 'efectivo_usd'
      this.nuevoPagoCuentaId   = null
      this.errorConfirmar      = ''
      this.ordenesDisponibles  = []
      this.ordenSeleccionada   = null
      if (this.$refs.fileInput) this.$refs.fileInput.value = ''
    },

    limpiarProveedor() {
      this.proveedorId        = null
      this.proveedorBusq      = ''
      this.provResultados     = []
      this.ordenesDisponibles = []
      this.ordenSeleccionada  = null
    },

    // ── OC existentes ─────────────────────────────────────────────────────────
    async cargarOrdenesPendientes(proveedorId) {
      try {
        const { data } = await axios.get('/facturas/ordenes-pendientes', {
          params: { proveedor_id: proveedorId }
        })
        this.ordenesDisponibles = data
      } catch {
        this.ordenesDisponibles = []
      }
    },
    seleccionarOrden(oc) {
      this.ordenSeleccionada = oc
      this.lineas = oc.detalles.map(d => ({
        nombre_ia:        d.nombre_producto || '',
        codigo_proveedor: d.codigo_proveedor || '',
        cantidad:         d.cantidad_pedida,
        precio_unitario:  d.precio_unitario_usd,
        actualizar_costo: true,
        match:            d.producto_id ? { id: d.producto_id, nombre: d.nombre_producto } : null,
        buscandoMatch:    false,
        _busqTexto:       d.nombre_producto || '',
        _busqResultados:  [],
        _busqAbierta:     false,
      }))
    },
    desvincularOrden() {
      this.ordenSeleccionada = null
      this.lineas            = []
    },
    abrirModalProveedor() {
      this.nuevoProv = {
        nombre:   this.proveedorBusq,
        rif:      '',
        telefono: '',
        contacto: '',
      }
      this.errorNuevoProv = ''
      this.modalProveedor = true
      this.provAbierta    = false
    },
    async crearProveedor() {
      if (!this.nuevoProv.nombre.trim()) {
        this.errorNuevoProv = 'El nombre es obligatorio'
        return
      }
      this.creandoProv    = true
      this.errorNuevoProv = ''
      try {
        const { data } = await axios.post('/compras/proveedores/', {
          nombre:   this.nuevoProv.nombre.trim(),
          rif:      this.nuevoProv.rif.trim(),
          telefono: this.nuevoProv.telefono.trim(),
          contacto: this.nuevoProv.contacto.trim(),
        }, {
          headers: { 'x-usuario-rol': 'admin' }
        })
        this.seleccionarProveedor(data)
        this.modalProveedor = false
        this.nuevoProv = { nombre: '', rif: '', telefono: '', contacto: '' }
      } catch (e) {
        this.errorNuevoProv = e?.response?.data?.detail || 'Error al crear proveedor'
      } finally {
        this.creandoProv = false
      }
    },

    fmtUSD(v) {
      return '$' + (Number(v) || 0).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    },
  },
}
</script>

<style scoped>
/* ── PASO 1 ──────────────────────────────────────────────────────────── */
.dropzone {
  border: 2px dashed var(--borde);
  border-radius: 12px;
  cursor: pointer;
  padding: 3rem 2rem;
  text-align: center;
  background: #FFFFFF;
  max-width: 640px;
  transition: border-color 0.2s, background 0.2s;
  position: relative;
}
.dropzone:hover, .dz-over { border-color: #FFCC00; background: #FFFDF0; }
.dz-icon { font-size: 3rem; display: block; margin-bottom: 0.5rem; }
.dz-empty p  { color: var(--texto-sec); margin: 0.25rem 0; font-size: 0.95rem; }
.dz-empty small { color: var(--texto-muted); font-size: 0.8rem; }
.dz-file { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.dz-img  { max-width: 100%; max-height: 280px; border-radius: 8px; }
.dz-pdf  { display: flex; flex-direction: column; align-items: center; gap: 0.4rem; }
.dz-pdf-name { font-weight: 600; font-size: 0.9rem; color: var(--texto-principal); word-break: break-all; }
.btn-quitar-archivo {
  position: absolute; top: 10px; right: 10px;
  background: #DC2626; color: white; border: none; border-radius: 50%;
  width: 26px; height: 26px; cursor: pointer; font-size: 0.8rem; line-height: 1;
}
.paso1-acciones { margin-top: 1rem; }
.btn-escanear {
  background: #1A1A1A; color: #FFCC00; border: none;
  padding: 0.75rem 2rem; border-radius: 8px;
  font-weight: 700; font-size: 0.95rem; cursor: pointer;
}
.btn-escanear:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── PASO 2 ──────────────────────────────────────────────────────────── */
.paso2-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.25rem; }
.btn-volver {
  background: none; border: 1px solid var(--borde);
  border-radius: 6px; padding: 0.4rem 0.85rem;
  cursor: pointer; color: var(--texto-sec); font-size: 0.875rem;
}
.btn-volver:hover { background: var(--fondo-sidebar); }
.paso2-titulo { margin: 0; font-size: 1.1rem; font-weight: 700; color: var(--texto-principal); }

.card-seccion {
  background: #FFFFFF;
  border: 1px solid var(--borde);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.25rem;
}
.seccion-titulo { font-size: 0.9rem; font-weight: 700; color: var(--texto-principal); margin: 0 0 1rem; text-transform: uppercase; letter-spacing: 0.04em; }
.badge-count { background: #FFCC0033; color: #996600; font-size: 0.75rem; padding: 0.1rem 0.5rem; border-radius: 999px; margin-left: 0.4rem; font-weight: 700; vertical-align: middle; }

/* Datos generales */
.datos-generales { display: flex; gap: 1rem; flex-wrap: wrap; align-items: flex-end; }
.field-group { display: flex; flex-direction: column; gap: 0.3rem; min-width: 160px; }
.field-label { font-size: 0.75rem; font-weight: 600; color: var(--texto-sec); text-transform: uppercase; letter-spacing: 0.04em; }
.input-field {
  border: 1px solid var(--borde); border-radius: 6px;
  padding: 0.5rem 0.65rem; font-size: 0.875rem;
  color: var(--texto-principal); background: var(--fondo-app);
  width: 100%; box-sizing: border-box;
}
.input-field:focus { outline: none; border-color: #FFCC00; }
select.input-field { cursor: pointer; }
.input-sm { padding: 0.3rem 0.45rem; font-size: 0.8rem; }
.tr { text-align: right; }

/* Search / Dropdown */
.search-wrap { position: relative; }
.dropdown-list {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 999;
  background: #FFFFFF; border: 1px solid var(--borde);
  border-radius: 6px; max-height: 220px; overflow-y: auto;
  list-style: none; padding: 0; margin: 2px 0 0;
  box-shadow: 0 6px 20px rgba(0,0,0,0.12);
}
.dropdown-list li {
  padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.875rem;
  border-bottom: 1px solid var(--borde); display: flex; align-items: center; gap: 0.3rem;
}
.dropdown-list li:last-child { border-bottom: none; }
.dropdown-list li:hover { background: #FFFDF0; }
.dropdown-sm li { font-size: 0.8rem; padding: 0.35rem 0.6rem; }
.stock-hint { color: var(--texto-muted); font-size: 0.75rem; }

/* Tabla */
.tabla-scroll { overflow-x: auto; }
.tabla-productos { width: 100%; border-collapse: collapse; }
.tabla-productos th, .tabla-productos td {
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid var(--borde);
  vertical-align: top;
  font-size: 0.85rem;
}
.tabla-productos th {
  font-size: 0.72rem; text-transform: uppercase;
  color: var(--texto-muted); font-weight: 600; white-space: nowrap;
}
.th-num { text-align: center; }
.tc  { text-align: center; }
.dim { color: var(--texto-muted); }
.nombre-ia { font-size: 0.82rem; color: var(--texto-sec); }
.match-estado { min-height: 22px; }
.match-buscando { font-size: 0.75rem; color: var(--texto-muted); }
.match-ok {
  background: #DCFCE7; color: #15803D; font-size: 0.78rem;
  padding: 0.15rem 0.5rem; border-radius: 4px; cursor: pointer;
  display: inline-block; max-width: 100%; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; font-weight: 600;
}
.match-ok:hover { background: #BBF7D0; }
.match-sin {
  background: #F1F5F9; color: var(--texto-muted);
  font-size: 0.78rem; padding: 0.15rem 0.5rem; border-radius: 4px; display: inline-block;
}
.btn-del-linea {
  background: none; border: none; color: #DC2626;
  cursor: pointer; font-size: 0.9rem; padding: 0.2rem 0.35rem; border-radius: 4px;
}
.btn-del-linea:hover { background: #FEE2E2; }
.btn-add-linea {
  margin-top: 0.75rem; background: none;
  border: 1px dashed var(--borde); border-radius: 6px;
  padding: 0.45rem 1rem; cursor: pointer;
  font-size: 0.85rem; color: var(--texto-sec); width: 100%;
}
.btn-add-linea:hover { background: #FFFDF0; border-color: #FFCC00; color: #996600; }

/* Pago / Resumen */
.pago-resumen-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
@media (max-width: 860px) { .pago-resumen-grid { grid-template-columns: 1fr; } }
.condicion-grupo { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.btn-condicion {
  border: 1px solid var(--borde); background: #FFFFFF;
  border-radius: 6px; padding: 0.45rem 0.9rem;
  cursor: pointer; font-size: 0.85rem; color: var(--texto-sec);
  transition: all 0.15s;
}
.btn-condicion.active { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; font-weight: 600; }
.btn-condicion:not(.active):hover { border-color: #FFCC00; }

.btn-group { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.txt-muted { color: var(--texto-muted); font-size: 0.78rem; display: block; margin-top: 0.25rem; }

/* Pagos múltiples */
.pago-item {
  display: flex; align-items: center; gap: 0.5rem;
  background: var(--fondo-tabla-alt, #F8F8F4); border-radius: 6px;
  padding: 0.4rem 0.75rem; margin-bottom: 0.35rem;
  font-size: 0.85rem; flex-wrap: wrap;
}
.pago-metodo { font-weight: 600; color: var(--texto-principal); }
.pago-cuenta { color: var(--texto-muted); font-size: 0.8rem; }
.pago-monto  { color: #DC2626; font-weight: 600; margin-left: auto; }
.pago-usd    { color: var(--texto-muted); font-size: 0.78rem; }
.nuevo-pago-form {
  background: var(--fondo-tabla-alt, #F8F8F4);
  border-radius: 8px; padding: 0.75rem; margin-top: 0.5rem;
}
.cuenta-unica { color: #16A34A; font-size: 0.82rem; font-weight: 600; }

.resumen-box {
  background: var(--fondo-sidebar, #F8F8F8);
  border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem;
}
.resumen-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.35rem 0; font-size: 0.9rem; color: var(--texto-sec);
  border-bottom: 1px solid var(--borde);
}
.resumen-row:last-child { border-bottom: none; }
.total-row     { font-weight: 700; font-size: 1rem; color: var(--texto-principal); }
.abono-row     { color: #15803D; }
.saldo-row     { color: #DC2626; font-weight: 600; }
.pagado-row    { color: #15803D; font-weight: 600; }

.btn-confirmar {
  width: 100%; background: #1A1A1A; color: #FFCC00; border: none;
  padding: 0.85rem; border-radius: 8px; font-weight: 700; font-size: 1rem; cursor: pointer;
}
.btn-confirmar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-confirmar:not(:disabled):hover { background: #333; }

/* Toast */
.toast-exito {
  position: fixed; bottom: 2rem; right: 2rem; z-index: 9999;
  background: #1A1A1A; color: white; border-radius: 12px;
  padding: 1rem 1.5rem; display: flex; align-items: flex-start;
  gap: 1rem; max-width: 380px; box-shadow: 0 8px 28px rgba(0,0,0,0.25);
  cursor: pointer; animation: slideIn 0.3s ease;
}
@keyframes slideIn { from { transform: translateX(120%); opacity:0; } to { transform: translateX(0); opacity:1; } }
.toast-icon  { font-size: 1.5rem; flex-shrink: 0; margin-top: 2px; }
.toast-body strong { display: block; color: #FFCC00; font-size: 0.95rem; margin-bottom: 0.3rem; }
.toast-body p      { margin: 0.15rem 0; font-size: 0.83rem; color: #ccc; }
.toast-body small  { font-size: 0.75rem; color: #888; }

/* OC selector */
.oc-selector-card { padding-bottom: 1rem; }
.oc-opciones { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem; }
.oc-opcion {
  display: flex; align-items: center; gap: 0.5rem;
  border: 1px solid var(--borde); border-radius: 8px;
  padding: 0.5rem 0.9rem; cursor: pointer;
  background: #FFFFFF; transition: all 0.15s;
}
.oc-opcion:hover { border-color: #FFCC00; background: #FFFDF0; }
.oc-opcion-activa { border-color: #1A1A1A; background: #1A1A1A; }
.oc-opcion-activa .oc-label,
.oc-opcion-activa .oc-total,
.oc-opcion-activa .oc-items { color: #FFCC00 !important; }
.oc-label { font-size: 0.85rem; font-weight: 600; color: var(--texto-principal); }
.oc-total { font-size: 0.82rem; color: #15803D; font-weight: 600; }
.oc-items { font-size: 0.78rem; color: var(--texto-muted); }
.oc-badge {
  font-size: 0.7rem; font-weight: 700; padding: 0.15rem 0.45rem;
  border-radius: 4px; text-transform: uppercase; letter-spacing: 0.03em;
}
.oc-badge.nuevo     { background: #E0F2FE; color: #0369A1; }
.oc-badge.aprobada  { background: #DCFCE7; color: #15803D; }
.oc-badge.parcial   { background: #FEF9C3; color: #854D0E; }

.renombrar-comparacion {
  background: var(--fondo-sidebar, #F8F8F8);
  border-radius: 8px; padding: 0.75rem 1rem;
  display: flex; flex-direction: column; gap: 0.5rem;
}
.renombrar-fila { display: flex; align-items: center; gap: 0.75rem; }
.renombrar-etiqueta {
  font-size: 0.75rem; font-weight: 700; color: var(--texto-muted);
  text-transform: uppercase; min-width: 80px;
}
.renombrar-valor { font-size: 0.9rem; color: var(--texto-principal); font-weight: 600; }
.txt-amarillo { color: #996600; }

/* Shared */
.msg-error { color: #DC2626; font-size: 0.875rem; margin-top: 0.5rem; }

.dropdown-vacio {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 999;
  background: #FFFFFF; border: 1px solid var(--borde);
  border-radius: 6px; padding: 0.6rem 0.75rem;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 6px 20px rgba(0,0,0,0.12);
  font-size: 0.85rem; color: var(--texto-muted);
}
.btn-crear-prov {
  background: #1A1A1A; color: #FFCC00; border: none;
  border-radius: 6px; padding: 0.3rem 0.75rem;
  font-size: 0.8rem; font-weight: 700; cursor: pointer;
}
.prov-seleccionado {
  margin-top: 0.4rem; font-size: 0.82rem; color: #15803D;
  font-weight: 600; display: flex; align-items: center; gap: 0.4rem;
}
.prov-desvincular {
  cursor: pointer; color: #DC2626; font-size: 0.8rem;
  padding: 0.1rem 0.3rem; border-radius: 3px;
}
.prov-desvincular:hover { background: #FEE2E2; }
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  z-index: 9999; display: flex; align-items: center; justify-content: center;
}
.modal-box {
  background: #FFFFFF; border-radius: 12px;
  width: 100%; max-width: 440px; padding: 0;
  box-shadow: 0 16px 48px rgba(0,0,0,0.2);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--borde);
}
.modal-header h3 { margin: 0; font-size: 1rem; color: var(--texto-principal); }
.btn-cerrar-modal {
  background: none; border: none; font-size: 1.1rem;
  cursor: pointer; color: var(--texto-muted); padding: 0.2rem 0.4rem;
}
.modal-body {
  padding: 1.25rem 1.5rem;
  display: flex; flex-direction: column; gap: 0.75rem;
}
.modal-footer {
  padding: 1rem 1.5rem; border-top: 1px solid var(--borde);
  display: flex; justify-content: flex-end; gap: 0.75rem;
}
</style>
