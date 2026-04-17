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
                  @click="condicionPago = op.val"
                >{{ op.label }}</button>
              </div>

              <div v-if="condicionPago === 'credito_parcial'" class="field-group" style="margin-top:1rem">
                <label class="field-label">Monto abonado (USD)</label>
                <input
                  v-model.number="montoAbonado"
                  type="number"
                  step="0.01"
                  min="0"
                  class="input-field"
                />
              </div>

              <div v-if="condicionPago !== 'credito_completo'" class="field-group" style="margin-top:1rem">
                <label class="field-label">Método de pago</label>
                <select v-model="metodoPago" class="input-field">
                  <option value="">Seleccionar...</option>
                  <option value="efectivo_usd">Efectivo USD</option>
                  <option value="transferencia">Transferencia</option>
                  <option value="zelle">Zelle</option>
                  <option value="pago_movil">Pago móvil</option>
                  <option value="punto">Punto de venta</option>
                </select>
              </div>

              <div class="field-group" style="margin-top:1rem">
                <label class="field-label">Descuento (USD)</label>
                <input
                  v-model.number="descuento"
                  type="number"
                  step="0.01"
                  min="0"
                  class="input-field"
                />
              </div>
            </div>

            <div class="resumen-col">
              <h3 class="seccion-titulo">Resumen</h3>
              <div class="resumen-box">
                <div class="resumen-row">
                  <span>Subtotal</span>
                  <span>{{ fmtUSD(subtotalCalculado) }}</span>
                </div>
                <div v-if="descuento > 0" class="resumen-row descuento-row">
                  <span>Descuento</span>
                  <span>-{{ fmtUSD(descuento) }}</span>
                </div>
                <div class="resumen-row total-row">
                  <span>Total factura</span>
                  <span>{{ fmtUSD(totalCalculado) }}</span>
                </div>
                <div v-if="condicionPago === 'credito_parcial' && montoAbonado > 0" class="resumen-row abono-row">
                  <span>Abono</span>
                  <span>{{ fmtUSD(montoAbonado) }}</span>
                </div>
                <div
                  class="resumen-row"
                  :class="saldoPendiente > 0 ? 'saldo-row' : 'pagado-row'"
                >
                  <span>{{ saldoPendiente > 0 ? 'Saldo pendiente' : 'Estado' }}</span>
                  <span>{{ saldoPendiente > 0 ? fmtUSD(saldoPendiente) : '✓ Pagado' }}</span>
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
      // Paso 2 — pago
      condicionPago: 'credito_completo',
      condicionOpciones: [
        { val: 'contado',          label: 'Contado'          },
        { val: 'credito_parcial',  label: 'Crédito parcial'  },
        { val: 'credito_completo', label: 'Crédito completo' },
      ],
      montoAbonado: 0,
      metodoPago: '',
      descuento: 0,
      // Confirmación
      confirmando: false,
      errorConfirmar: '',
      confirmadoOk: false,
      resultadoConfirmar: {},
    }
  },

  computed: {
    subtotalCalculado() {
      return this.lineas.reduce(
        (s, l) => s + (Number(l.cantidad) || 0) * (Number(l.precio_unitario) || 0),
        0,
      )
    },
    totalCalculado() {
      return Math.max(this.subtotalCalculado - (Number(this.descuento) || 0), 0)
    },
    saldoPendiente() {
      if (this.condicionPago === 'contado') return 0
      if (this.condicionPago === 'credito_parcial')
        return Math.max(this.totalCalculado - (Number(this.montoAbonado) || 0), 0)
      return this.totalCalculado
    },
    puedeConfirmar() {
      return this.lineas.length > 0 && this.totalCalculado > 0
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
      this.numeroFactura = data.numero_factura || ''
      this.fechaFactura  = data.fecha          || new Date().toISOString().slice(0, 10)
      this.descuento     = Number(data.descuento_detectado) || 0
      this.proveedorBusq = data.proveedor || ''
      this.proveedorId   = null

      if (data.proveedor) this.buscarProveedorInicial(data.proveedor)

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
      this.proveedorId   = p.id
      this.proveedorBusq = p.nombre
      this.provAbierta   = false
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
          linea.match     = data[0]
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
      linea.match      = null
      linea._busqTexto = ''
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

    // ── Confirmar compra ──────────────────────────────────────────────
    async confirmarCompra() {
      this.confirmando    = true
      this.errorConfirmar = ''

      const abonadoReal =
        this.condicionPago === 'contado'         ? this.totalCalculado :
        this.condicionPago === 'credito_parcial' ? (Number(this.montoAbonado) || 0) :
        0

      const payload = {
        proveedor_id:   this.proveedorId,
        numero_factura: this.numeroFactura,
        fecha:          this.fechaFactura || new Date().toISOString().slice(0, 10),
        descuento:      Number(this.descuento) || 0,
        total_factura:  this.totalCalculado,
        condicion_pago: this.condicionPago,
        monto_abonado:  abonadoReal,
        metodo_pago:    this.condicionPago !== 'credito_completo' ? this.metodoPago : null,
        usuario:        JSON.parse(localStorage.getItem('usuario') || '{}').nombre || 'admin',
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
      this.paso            = 1
      this.archivoSeleccionado = null
      this.previewUrl      = null
      this.lineas          = []
      this.proveedorId     = null
      this.proveedorBusq   = ''
      this.provResultados  = []
      this.numeroFactura   = ''
      this.fechaFactura    = ''
      this.descuento       = 0
      this.condicionPago   = 'credito_completo'
      this.montoAbonado    = 0
      this.metodoPago      = ''
      this.errorConfirmar  = ''
      if (this.$refs.fileInput) this.$refs.fileInput.value = ''
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
.descuento-row { color: #DC2626; }
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

/* Shared */
.msg-error { color: #DC2626; font-size: 0.875rem; margin-top: 0.5rem; }
</style>