<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">

      <!-- ── Top bar ── -->
      <div class="top-bar">
        <h1>{{ tituloPagina }}</h1>
        <div class="top-meta" v-if="tabActivo === 'venta'">
          <div class="selector-group">
            <span class="selector-label">Moneda:</span>
            <button :class="['btn-sel', monedaVenta === 'USD' ? 'activo' : '']"
              @click="monedaVenta = 'USD'">USD</button>
            <button :class="['btn-sel', monedaVenta === 'Bs' ? 'activo' : '']"
              @click="monedaVenta = 'Bs'">Bs</button>
          </div>
          <div class="selector-group">
            <span class="selector-label">Precio:</span>
            <button :class="['btn-sel', tipoPrecio === 'referencial' ? 'activo' : '']"
              @click="cambiarTipoPrecio('referencial')">Referencial</button>
            <button :class="['btn-sel btn-base', tipoPrecio === 'base' ? 'activo-base' : '']"
              @click="cambiarTipoPrecio('base')">Base $</button>
          </div>
          <div class="tasas-info">
            <span>BCV: <strong>{{ tasaBcv ? tasaBcv.toFixed(2) : '...' }}</strong></span>
            <span>Binance: <strong class="txt-yellow">{{ tasaBinance ? tasaBinance.toFixed(2) : '...' }}</strong></span>
            <span>Factor: <strong class="txt-green">{{ factor ? factor.toFixed(4) : '...' }}</strong></span>
          </div>
        </div>
      </div>

      <div class="aviso-base" v-if="tabActivo === 'venta' && tipoPrecio === 'base'">
        Modo <strong>Precio Base USD</strong> — se aplicará descuento divisa. Requiere autorización.
      </div>

      <!-- ── Navegación de pestañas ── -->
      <div class="tabs-nav">
        <button :class="['tab-btn', tabActivo === 'venta' ? 'tab-activo' : '']"
          @click="tabActivo = 'venta'">Nueva Venta</button>
        <button :class="['tab-btn', tabActivo === 'clientes' ? 'tab-activo' : '']"
          @click="cambiarTab('clientes')">Clientes</button>
        <button :class="['tab-btn', tabActivo === 'historial' ? 'tab-activo' : '']"
          @click="cambiarTab('historial')">Historial</button>
      </div>

      <!-- ══════════════════════════════════════════════════════════════════ -->
      <!-- Tab: Nueva Venta                                                  -->
      <!-- ══════════════════════════════════════════════════════════════════ -->
      <div v-show="tabActivo === 'venta'">

        <!-- 1. Selector de cliente (PRIMER paso, siempre visible) -->
        <div class="cliente-top">
          <!-- Cliente ya seleccionado -->
          <div v-if="clienteSeleccionado" class="cliente-card">
            <span class="ck-check">✓</span>
            <span class="ck-nombre">{{ clienteSeleccionado.nombre }}</span>
            <span v-if="clienteSeleccionado.nivel_fidelidad" class="ck-nivel"
              :style="{ background: clienteSeleccionado.nivel_fidelidad.color + '22',
                        color: clienteSeleccionado.nivel_fidelidad.color }">
              {{ clienteSeleccionado.nivel_fidelidad.nombre }}
            </span>
            <span class="ck-stats" v-if="!clienteSeleccionado.es_cliente_generico">
              {{ clienteSeleccionado.total_compras }} compras ·
              ${{ (clienteSeleccionado.monto_acumulado_usd || 0).toFixed(0) }} USD
            </span>
            <button class="btn-cambiar-cliente" @click="quitarCliente">Cambiar cliente</button>
          </div>

          <!-- Sin cliente seleccionado -->
          <div v-else class="cliente-selector-row">
            <div class="cliente-search-wrap">
              <input
                v-model="clienteBusqueda"
                @input="buscarCliente"
                placeholder="Buscar por nombre o teléfono..."
                class="input-cliente"
              />
              <div v-if="clienteResultados.length > 0" class="cliente-dropdown">
                <div
                  v-for="c in clienteResultados" :key="c.id"
                  class="cliente-opcion"
                  @click="seleccionarCliente(c)"
                >
                  <span class="opcion-nombre">{{ c.nombre }}</span>
                  <span class="opcion-tel">{{ c.telefono }}</span>
                  <span v-if="c.nivel_fidelidad" class="opcion-nivel"
                    :style="{ color: c.nivel_fidelidad.color }">
                    {{ c.nivel_fidelidad.nombre }}
                  </span>
                </div>
              </div>
            </div>
            <button class="btn-consumidor" @click="seleccionarConsumidorFinal"
              title="Asigna el cliente genérico en un clic">
              Consumidor Final
            </button>
            <button class="btn-nuevo-cliente" @click="abrirDialogNuevo">+ Nuevo</button>
          </div>
        </div>

        <!-- Aviso si falta cliente -->
        <div v-if="!clienteSeleccionado" class="aviso-sin-cliente">
          Selecciona un cliente o usa <strong>Consumidor Final</strong> para comenzar la venta
        </div>

        <!-- 2. Grid de venta (solo cuando hay cliente) -->
        <div v-if="clienteSeleccionado" class="venta-grid">

          <!-- ── Catálogo ── -->
          <div class="catalogo">
            <input v-model="busqueda" placeholder="Buscar producto..." class="buscador" />
            <table>
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>P. Base</th>
                  <th>P. Ref.</th>
                  <th>Bs</th>
                  <th>Stock</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in productosFiltrados" :key="p.id">
                  <td>
                    {{ p.nombre }}
                    <button class="btn-ubicar-v" @click.stop="abrirUbicPop(p)" title="Ver ubicaciones">📍</button>
                  </td>
                  <td class="txt-dim">${{ precioBase(p).toFixed(2) }}</td>
                  <td :class="tipoPrecio === 'referencial' ? 'txt-green' : 'txt-dim'">
                    ${{ precioRef(p).toFixed(2) }}
                  </td>
                  <td class="txt-yellow">Bs. {{ precioBs(p).toFixed(2) }}</td>
                  <td :class="{ 'stock-bajo': p.stock < 5 }">{{ p.stock }}</td>
                  <td><button class="btn-agregar" @click="agregar(p)">+</button></td>
                </tr>
                <tr v-if="productosFiltrados.length === 0">
                  <td colspan="6" class="sin-datos">Sin resultados</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ── Panel derecho ── -->
          <div class="panel-derecho">

            <!-- Carrito -->
            <div class="carrito-box">
              <h2>Carrito</h2>
              <div v-if="carrito.length === 0" class="vacio">Sin productos</div>

              <div v-for="(item, i) in carrito" :key="i" class="item">
                <div class="item-header">
                  <span class="item-nombre">{{ item.nombre }}</span>
                  <button class="btn-quitar" @click="quitar(i)">×</button>
                </div>
                <div class="item-controles">
                  <button @click="restar(i)">−</button>
                  <span>{{ item.cantidad }}</span>
                  <button @click="sumar(i)">+</button>
                  <span class="item-precio-snap">
                    {{ tipoPrecio === 'base' ? 'Base:' : 'Ref:' }}
                    ${{ item.precio_original.toFixed(2) }}
                  </span>
                </div>
                <div class="item-precio-edit">
                  <label>Precio aplicado (USD)</label>
                  <input v-model.number="item.precio_unitario" type="number"
                    min="0" step="0.01" @input="normalizarPrecio(item)" />
                </div>
                <div class="item-subtotal">
                  <span v-if="tieneDescuento(item)" class="tag-desc">
                    Dto: ${{ descuentoLinea(item).toFixed(2) }}
                  </span>
                  <span>Sub: {{ formatMonto(subtotalLinea(item), monedaVenta) }}</span>
                </div>
              </div>

              <!-- Totales -->
              <div class="totales-box" v-if="carrito.length > 0">
                <div class="fila-total">
                  <span>Subtotal:</span>
                  <span>{{ formatMonto(subtotalEnMoneda, monedaVenta) }}</span>
                </div>
                <div class="descuento-global">
                  <label>Descuento global ({{ monedaVenta }})</label>
                  <input v-model.number="descuentoGlobal" type="number"
                    min="0" step="0.01" placeholder="0.00" />
                </div>
                <div class="fila-total" v-if="descuentoGlobal > 0">
                  <span>Descuento:</span>
                  <span class="txt-desc">−{{ formatMonto(descuentoGlobal, monedaVenta) }}</span>
                </div>
                <div class="fila-total fila-grande">
                  <span>TOTAL:</span>
                  <span>{{ formatMonto(totalEnMoneda, monedaVenta) }}</span>
                </div>
                <div class="fila-total txt-gris" v-if="tasaBcv && monedaVenta === 'USD'">
                  <span>Equiv. Bs (BCV):</span>
                  <span>Bs. {{ (totalEnMoneda * tasaBcv).toFixed(2) }}</span>
                </div>
                <div class="fila-total txt-gris" v-if="tasaBcv && monedaVenta === 'Bs'">
                  <span>Equiv. USD:</span>
                  <span>${{ (totalEnMoneda / tasaBcv).toFixed(2) }}</span>
                </div>
              </div>
            </div>

            <!-- Cobro -->
            <div class="cobro-box" v-if="carrito.length > 0">
              <h2>Cobro</h2>

              <div class="form-pago">
                <div class="form-pago-row">
                  <select v-model="nuevoMetodo" @change="onCambioMetodo">
                    <optgroup label="— USD —">
                      <option value="efectivo_usd">Efectivo $</option>
                      <option value="zelle">Zelle</option>
                      <option value="binance">Binance</option>
                    </optgroup>
                    <optgroup label="— Bolívares —">
                      <option value="efectivo_bs">Efectivo Bs</option>
                      <option value="transferencia_bs">Transferencia Bs</option>
                      <option value="pago_movil">Pago Móvil</option>
                      <option value="punto_banesco">Punto Banesco</option>
                      <option value="punto_provincial">Punto Provincial</option>
                    </optgroup>
                  </select>

                  <select v-if="cuentasDelMetodo.length > 1"
                    v-model="nuevaCuentaId" class="sel-cuenta">
                    <option :value="null">— Cuenta destino —</option>
                    <option v-for="c in cuentasDelMetodo" :key="c.id" :value="c.id">
                      {{ c.nombre }}{{ c.identificador ? ' · ' + c.identificador : '' }}
                    </option>
                  </select>
                  <span v-else-if="cuentasDelMetodo.length === 1" class="cuenta-unica">
                    {{ cuentasDelMetodo[0].nombre }}
                  </span>

                  <div class="monto-wrap">
                    <span class="moneda-tag">{{ nuevoMonedaPago === 'USD' ? '$' : 'Bs.' }}</span>
                    <input v-model.number="nuevoMonto" type="number" min="0.01"
                      step="0.01" placeholder="0.00" @input="calcularEquivPrevisualizacion" />
                  </div>

                  <button class="btn-agregar-pago" @click="agregarPago"
                    :disabled="!nuevoMonto || nuevoMonto <= 0">
                    + Agregar
                  </button>
                </div>

                <input v-model="nuevaReferencia" placeholder="Referencia (opcional)"
                  class="input-referencia" />

                <div class="equiv-preview" v-if="nuevoMonto > 0 && nuevoEquivalente !== null">
                  <span class="equiv-label">Equivale en {{ monedaVenta }}:</span>
                  <span class="equiv-valor">{{ formatMonto(nuevoEquivalente, monedaVenta) }}</span>
                  <span class="saldo-preview"
                    :class="nuevoEquivalente > saldoPendiente + 0.01 ? 'exceso' : ''">
                    (Saldo: {{ formatMonto(saldoPendiente, monedaVenta) }})
                  </span>
                </div>
              </div>

              <div class="lista-pagos" v-if="pagos.length > 0">
                <div v-for="(p, i) in pagos" :key="i" class="pago-item">
                  <div class="pago-izq">
                    <span class="pago-metodo">{{ labelMetodo(p.metodo) }}</span>
                    <span class="pago-monto">{{ p.moneda_pago === 'USD' ? '$' : 'Bs.' }}{{ p.monto_original.toFixed(2) }}</span>
                    <span class="pago-equiv">= {{ formatMonto(p.monto_equivalente, monedaVenta) }} {{ monedaVenta }}</span>
                    <span class="pago-ref" v-if="p.referencia">| {{ p.referencia }}</span>
                  </div>
                  <button class="btn-rm-pago" @click="quitarPago(i)">×</button>
                </div>
              </div>

              <div class="resumen-cobro" v-if="pagos.length > 0">
                <div class="resumen-fila"><span>Total:</span><strong>{{ formatMonto(totalEnMoneda, monedaVenta) }}</strong></div>
                <div class="resumen-fila"><span>Abonado:</span><strong class="txt-verde">{{ formatMonto(totalAbonado, monedaVenta) }}</strong></div>
                <div class="resumen-fila" v-if="saldoPendiente > 0.01"><span>Falta:</span><strong class="txt-rojo">{{ formatMonto(saldoPendiente, monedaVenta) }}</strong></div>
                <div class="resumen-fila" v-if="exceso > 0.01"><span>Vuelto:</span><strong class="txt-amarillo">{{ formatMonto(exceso, monedaVenta) }}</strong></div>
              </div>

              <div v-if="requiereAutorizacion" class="autorizacion-box">
                <p class="aut-titulo">Se requiere autorización</p>
                <ul class="aut-motivos">
                  <li v-for="(m, i) in motivosAutorizacion" :key="i">{{ m }}</li>
                </ul>
                <input v-model="autorizacionClave" type="password"
                  placeholder="Clave de autorización" />
              </div>

              <div class="field">
                <label>Observación</label>
                <input v-model="observacion" placeholder="Opcional..." />
              </div>

              <button class="btn-cobrar" @click="cobrar"
                :disabled="!pagoCompleto || cargando">
                {{ cargando ? 'Registrando...' : '✔ Registrar venta' }}
              </button>

              <div v-if="exitoso" class="venta-exito-row">
                <p class="msg-exito">¡Venta #{{ ultimaVentaId }} registrada!</p>
                <button class="btn-pdf" @click="imprimirPDF(ultimaVentaId)">🖨 Imprimir PDF</button>
              </div>
              <p class="msg-error" v-if="error">{{ error }}</p>
            </div>

          </div><!-- /panel-derecho -->
        </div><!-- /venta-grid -->
      </div><!-- /tab venta -->

      <!-- ══════════════════════════════════════════════════════════════════ -->
      <!-- Tab: Clientes                                                     -->
      <!-- ══════════════════════════════════════════════════════════════════ -->
      <div v-show="tabActivo === 'clientes'" class="tab-clientes">
        <div class="tc-header">
          <input
            v-model="busquedaClientes"
            @input="buscarEnTab"
            placeholder="Buscar por nombre o teléfono..."
            class="buscador"
          />
          <button class="btn-nuevo-cliente" @click="abrirDialogNuevo">+ Nuevo Cliente</button>
        </div>

        <p class="tc-titulo-seccion">
          {{ busquedaClientes ? 'Resultados' : 'Clientes recientes' }}
        </p>

        <div class="tc-lista">
          <template v-if="!busquedaClientes">
            <div v-for="c in clientesRecientes" :key="c.id"
              class="tc-row" @click="seleccionarDesdeTab(c)">
              <div class="tc-info">
                <span class="tc-nombre">{{ c.nombre }}</span>
                <span class="tc-tel">{{ c.telefono }}</span>
              </div>
              <div class="tc-right">
                <span v-if="c.nivel_fidelidad" class="tc-nivel"
                  :style="{ background: c.nivel_fidelidad.color + '22',
                            color: c.nivel_fidelidad.color }">
                  {{ c.nivel_fidelidad.nombre }}
                </span>
                <span class="tc-compras">{{ c.total_compras }} compras</span>
              </div>
            </div>
            <div v-if="clientesRecientes.length === 0" class="sin-datos">
              Sin actividad reciente
            </div>
          </template>

          <template v-else>
            <div v-for="c in resultadosClientes" :key="c.id"
              class="tc-row" @click="seleccionarDesdeTab(c)">
              <div class="tc-info">
                <span class="tc-nombre">{{ c.nombre }}</span>
                <span class="tc-tel">{{ c.telefono }}</span>
              </div>
              <div class="tc-right">
                <span v-if="c.nivel_fidelidad" class="tc-nivel"
                  :style="{ background: c.nivel_fidelidad.color + '22',
                            color: c.nivel_fidelidad.color }">
                  {{ c.nivel_fidelidad.nombre }}
                </span>
              </div>
            </div>
            <div v-if="resultadosClientes.length === 0" class="sin-datos">Sin resultados</div>
          </template>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════════════════ -->
      <!-- Tab: Historial                                                    -->
      <!-- ══════════════════════════════════════════════════════════════════ -->
      <div v-show="tabActivo === 'historial'" class="tab-historial">
        <div class="th-header">
          <span class="th-subtitulo">Ventas de hoy</span>
          <button class="btn-refrescar" @click="cargarVentasHoy">↺ Actualizar</button>
        </div>

        <div v-if="cargandoHistorial" class="sin-datos">Cargando...</div>
        <table v-else>
          <thead>
            <tr>
              <th>Hora</th>
              <th>Cliente</th>
              <th>Total</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in ventasHoy" :key="v.id">
              <td class="txt-dim">{{ v.hora }}</td>
              <td>{{ v.cliente }}</td>
              <td>{{ v.moneda === 'USD' ? '$' : 'Bs. ' }}{{ v.total.toFixed(2) }}</td>
              <td><span class="tag-estado">{{ v.estado }}</span></td>
              <td><button class="btn-ver" @click="imprimirPDF(v.id)">PDF</button></td>
            </tr>
            <tr v-if="ventasHoy.length === 0">
              <td colspan="5" class="sin-datos">Sin ventas registradas hoy</td>
            </tr>
          </tbody>
        </table>

        <div v-if="ventasHoy.length > 0" class="historial-resumen">
          <span>Total ventas: <strong>{{ ventasHoy.length }}</strong></span>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════════════════ -->
      <!-- Dialog: Nuevo Cliente                                             -->
      <!-- ══════════════════════════════════════════════════════════════════ -->
      <div class="dialog-overlay" v-if="dialogNuevoCliente" @click.self="cerrarDialog">
        <div class="dialog">
          <div class="dialog-header">
            <h3>Nuevo Cliente</h3>
            <button class="btn-cerrar-dialog" @click="cerrarDialog">✕</button>
          </div>
          <div class="dialog-body">
            <div class="field">
              <label>Nombre *</label>
              <input
                ref="inputNombreNuevo"
                v-model="nuevoCliente.nombre"
                @keydown.enter="$refs.inputTelefonoNuevo.focus()"
                placeholder="Nombre completo"
              />
            </div>
            <div class="field">
              <label>Teléfono *</label>
              <input
                ref="inputTelefonoNuevo"
                v-model="nuevoCliente.telefono"
                @keydown.enter="$refs.inputCedulaNuevo.focus()"
                placeholder="04XX-XXXXXXX"
              />
            </div>
            <div class="field">
              <label>Tipo</label>
              <div class="radio-group">
                <label class="radio-opt">
                  <input type="radio" v-model="nuevoCliente.tipo_cliente" value="natural" />
                  Natural
                </label>
                <label class="radio-opt">
                  <input type="radio" v-model="nuevoCliente.tipo_cliente" value="juridico" />
                  Jurídico
                </label>
              </div>
            </div>
            <div class="field">
              <label>Cédula / RIF <small>(opcional)</small></label>
              <input
                ref="inputCedulaNuevo"
                v-model="nuevoCliente.rif_cedula"
                @keydown.enter="guardarNuevoCliente"
                placeholder="V-XXXXXXXXX"
              />
            </div>

            <!-- Teléfono duplicado -->
            <div v-if="telefonoDuplicado" class="aviso-duplicado">
              <p>⚠ Ya existe un cliente con ese teléfono: <strong>{{ telefonoDuplicado.nombre }}</strong></p>
              <div class="duplicado-btns">
                <button @click="usarClienteExistente" class="btn-primary">Sí, usar ese cliente</button>
                <button @click="telefonoDuplicado = null" class="btn-sec">No, corregir teléfono</button>
              </div>
            </div>

            <p class="error-cliente" v-if="errorCliente">{{ errorCliente }}</p>
          </div>
          <div class="dialog-footer">
            <button @click="cerrarDialog" class="btn-sec">Cancelar</button>
            <button @click="guardarNuevoCliente" :disabled="guardandoCliente" class="btn-primary">
              {{ guardandoCliente ? 'Guardando...' : 'Guardar y continuar' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Popup ubicaciones producto -->
      <div class="ubic-pop-overlay" v-if="ubicPop" @click.self="ubicPop = null">
        <div class="ubic-pop">
          <div class="ubic-pop-header">
            <span>📍 {{ ubicPop.nombre }}</span>
            <button @click="ubicPop = null" class="btn-cerrar-modal">✕</button>
          </div>
          <div v-if="ubicPopCargando" class="ubic-pop-cargando">Cargando...</div>
          <table v-else-if="ubicaciones.length > 0" class="ubic-pop-tabla">
            <thead><tr><th>Área</th><th>Pasillo</th><th>Estante</th><th>Nivel</th></tr></thead>
            <tbody>
              <tr v-for="u in ubicaciones" :key="u.id">
                <td>{{ u.area_nombre }}</td>
                <td>P{{ u.pasillo_num }}</td>
                <td>E{{ u.estante_num }}</td>
                <td>{{ u.nivel }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="ubic-pop-vacio">Sin ubicaciones asignadas</p>
        </div>
      </div>

    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'
import { exportarFacturaPDF } from '@/utils/facturaPDF.js'

const METODOS_USD = ['efectivo_usd', 'zelle', 'binance']
const LABELS = {
  efectivo_usd:     'Efectivo $',
  zelle:            'Zelle',
  binance:          'Binance',
  efectivo_bs:      'Efectivo Bs',
  transferencia_bs: 'Transferencia Bs',
  pago_movil:       'Pago Móvil',
  punto_banesco:    'Punto Banesco',
  punto_provincial: 'Punto Provincial',
}
const TOLERANCIA = 0.01

export default {
  components: { AppSidebar },
  name: 'Ventas',
  data() {
    return {
      usuario:    JSON.parse(localStorage.getItem('usuario') || '{}'),
      productos:  [],
      tasaBcv:    null,
      tasaBinance:null,
      factor:     1,
      busqueda:   '',

      monedaVenta:    'USD',
      tipoPrecio:     'referencial',
      carrito:        [],
      descuentoGlobal: 0,

      pagos:            [],
      nuevoMetodo:       'efectivo_usd',
      nuevoMonto:        '',
      nuevaReferencia:   '',
      nuevaCuentaId:     null,
      nuevoEquivalente:  null,

      autorizacionClave: '',
      observacion:       '',

      // Cliente
      clienteBusqueda:     '',
      clienteResultados:   [],
      clienteSeleccionado: null,
      clienteTimer:        null,

      // Estado de la venta
      cargando:      false,
      exitoso:       false,
      error:         '',
      ultimaVentaId: null,
      cuentasPorMetodo: {},

      // Tabs
      tabActivo: 'venta',

      // Tab Clientes
      busquedaClientes:  '',
      resultadosClientes:[],
      clientesRecientes: [],
      busquedaTabTimer:  null,

      // Tab Historial
      ventasHoy:         [],
      cargandoHistorial: false,

      // Dialog Nuevo Cliente
      dialogNuevoCliente: false,
      nuevoCliente: { nombre: '', telefono: '', tipo_cliente: 'natural', rif_cedula: '' },
      guardandoCliente: false,
      errorCliente:     '',
      telefonoDuplicado: null,

      // Popup ubicaciones
      ubicPop:        null,
      ubicaciones:    [],
      ubicPopCargando: false,
    }
  },
  computed: {
    tituloPagina() {
      if (this.tabActivo === 'clientes') return 'Clientes'
      if (this.tabActivo === 'historial') return 'Historial del Día'
      return 'Nueva Venta'
    },
    productosFiltrados() {
      const q = this.busqueda.toLowerCase()
      return this.productos.filter(p =>
        p.nombre.toLowerCase().includes(q) ||
        (p.categoria && p.categoria.toLowerCase().includes(q))
      )
    },
    subtotalUSD() {
      return this.carrito.reduce(
        (s, i) => s + Number(i.precio_unitario) * Number(i.cantidad), 0
      )
    },
    subtotalEnMoneda() {
      if (this.monedaVenta === 'USD') return this.subtotalUSD
      return this.tasaBcv ? this.subtotalUSD * this.tasaBcv : 0
    },
    descuentoEnMoneda() { return Number(this.descuentoGlobal || 0) },
    totalEnMoneda()     { return Math.max(this.subtotalEnMoneda - this.descuentoEnMoneda, 0) },
    totalAbonado()      { return this.pagos.reduce((s, p) => s + p.monto_equivalente, 0) },
    saldoPendiente()    { return Math.max(this.totalEnMoneda - this.totalAbonado, 0) },
    exceso() {
      return this.totalAbonado > this.totalEnMoneda
        ? this.totalAbonado - this.totalEnMoneda : 0
    },
    pagoCompleto() {
      return this.saldoPendiente <= TOLERANCIA && this.pagos.length > 0
    },
    motivosAutorizacion() {
      const m = []
      if (this.tipoPrecio === 'base')
        m.push('Descuento divisa: precios en USD base')
      for (const item of this.carrito) {
        if (Number(item.cantidad) > Number(item.stock))
          m.push(`Sin stock suficiente: ${item.nombre}`)
        if (Number(item.precio_unitario) < Number(item.precio_original) - TOLERANCIA)
          m.push(`Descuento en producto: ${item.nombre}`)
      }
      if (Number(this.descuentoGlobal || 0) > 0)
        m.push('Descuento global de factura')
      return m
    },
    requiereAutorizacion() { return this.motivosAutorizacion.length > 0 },
    nuevoMonedaPago()      { return METODOS_USD.includes(this.nuevoMetodo) ? 'USD' : 'Bs' },
    esAdmin()              { return this.usuario.rol === 'admin' },
    tienePermiso() {
      return (modulo) => {
        if (this.usuario.rol === 'admin') return true
        const p = this.usuario.permisos
        if (p == null) return true
        return Array.isArray(p) ? p.includes(modulo) : true
      }
    },
    cuentasDelMetodo()     { return this.cuentasPorMetodo[this.nuevoMetodo] || [] },
  },
  async mounted() {
    await Promise.all([
      this.cargarProductos(),
      this.cargarTasa(),
      this.cargarCuentasPorMetodo(),
    ])
  },
  methods: {
    // ── Carga inicial ─────────────────────────────────────────────────────────
    async cargarProductos() {
      const r = await axios.get('/productos/')
      this.productos = r.data
    },
    async cargarCuentasPorMetodo() {
      try {
        const r = await axios.get('/bancos/metodos-pago/cuentas')
        this.cuentasPorMetodo = r.data
      } catch { /* módulo bancario aún no configurado */ }
    },
    async cargarTasa() {
      const r = await axios.get('/tasa/')
      this.tasaBcv     = r.data.tasa
      this.tasaBinance = r.data.tasa_binance
      this.factor      = r.data.factor || 1
    },

    // ── Precios ───────────────────────────────────────────────────────────────
    precioBase(p)     { return Number(p.costo_usd || 0) * (1 + Number(p.margen || 0)) },
    precioRef(p)      { return this.precioBase(p) * this.factor },
    precioBs(p)       { return this.precioBase(p) * (this.tasaBinance || 0) },
    precioParaTier(p) { return this.tipoPrecio === 'base' ? this.precioBase(p) : this.precioRef(p) },

    // ── Carrito ───────────────────────────────────────────────────────────────
    cambiarTipoPrecio(nuevo) {
      this.tipoPrecio = nuevo
      this.carrito.forEach(item => {
        const p = this.productos.find(x => x.id === item.id)
        if (!p) return
        const precio = this.precioParaTier(p)
        item.precio_original = precio
        item.precio_unitario = precio
      })
    },
    agregar(p) {
      const existe = this.carrito.find(i => i.id === p.id)
      if (existe) { existe.cantidad++; return }
      const precio = this.precioParaTier(p)
      this.carrito.push({
        ...p,
        cantidad:        1,
        precio_original: precio,
        precio_unitario: precio,
      })
    },
    sumar(i)  { this.carrito[i].cantidad++ },
    restar(i) {
      if (this.carrito[i].cantidad > 1) this.carrito[i].cantidad--
      else this.quitar(i)
    },
    quitar(i) { this.carrito.splice(i, 1) },
    normalizarPrecio(item) {
      const v = Number(item.precio_unitario || 0)
      item.precio_unitario = v >= 0 ? v : 0
    },
    subtotalLinea(item) {
      const usd = Number(item.precio_unitario) * Number(item.cantidad)
      if (this.monedaVenta === 'USD') return usd
      return this.tasaBcv ? usd * this.tasaBcv : 0
    },
    descuentoLinea(item) {
      return (Number(item.precio_original) - Number(item.precio_unitario)) * Number(item.cantidad)
    },
    tieneDescuento(item) {
      return Number(item.precio_unitario) < Number(item.precio_original) - TOLERANCIA
    },

    // ── Pagos ─────────────────────────────────────────────────────────────────
    labelMetodo(metodo) { return LABELS[metodo] || metodo },
    calcularEquivalente(monto, monedaPago) {
      if (!this.tasaBcv && monedaPago !== this.monedaVenta) return null
      if (monedaPago === this.monedaVenta) return Number(monto.toFixed(2))
      if (monedaPago === 'USD' && this.monedaVenta === 'Bs')
        return Number((monto * this.tasaBcv).toFixed(2))
      if (monedaPago === 'Bs' && this.monedaVenta === 'USD')
        return this.tasaBcv > 0 ? Number((monto / this.tasaBcv).toFixed(2)) : null
      return null
    },
    calcularEquivPrevisualizacion() {
      const monto = Number(this.nuevoMonto || 0)
      if (monto <= 0) { this.nuevoEquivalente = null; return }
      this.nuevoEquivalente = this.calcularEquivalente(monto, this.nuevoMonedaPago)
    },
    onCambioMetodo() {
      this.nuevoMonto       = ''
      this.nuevoEquivalente = null
      const cuentas = this.cuentasPorMetodo[this.nuevoMetodo] || []
      this.nuevaCuentaId = cuentas.length === 1 ? cuentas[0].id : null
    },
    agregarPago() {
      const monto = Number(this.nuevoMonto || 0)
      if (monto <= 0) { this.error = 'El monto debe ser mayor a cero'; return }

      const monedaPago  = this.nuevoMonedaPago
      const equivalente = this.calcularEquivalente(monto, monedaPago)
      if (equivalente === null) {
        this.error = 'No se puede calcular el equivalente. Verifica la tasa.'
        return
      }

      const esEfectivo = ['efectivo_usd', 'efectivo_bs'].includes(this.nuevoMetodo)
      if (!esEfectivo && equivalente > this.saldoPendiente + TOLERANCIA) {
        this.error = `El pago (${this.formatMonto(equivalente, this.monedaVenta)}) excede el saldo (${this.formatMonto(this.saldoPendiente, this.monedaVenta)}). Solo efectivo puede tener exceso.`
        return
      }

      const cuentas  = this.cuentasDelMetodo
      if (cuentas.length > 1 && !this.nuevaCuentaId) {
        this.error = `Debes seleccionar la cuenta destino para ${this.nuevoMetodo}`
        return
      }
      const cuentaId     = this.nuevaCuentaId || (cuentas.length === 1 ? cuentas[0].id : null)
      const cuentaNombre = cuentas.find(c => c.id === cuentaId)?.nombre || null

      this.error = ''
      this.pagos.push({
        metodo:            this.nuevoMetodo,
        moneda_pago:       monedaPago,
        monto_original:    monto,
        monto_equivalente: equivalente,
        referencia:        this.nuevaReferencia,
        cuenta_destino_id: cuentaId,
        cuenta_nombre:     cuentaNombre,
      })
      this.nuevoMonto       = ''
      this.nuevoEquivalente = null
      this.nuevaReferencia  = ''
    },
    quitarPago(i) { this.pagos.splice(i, 1) },

    // ── Cliente ───────────────────────────────────────────────────────────────
    buscarCliente() {
      clearTimeout(this.clienteTimer)
      if (this.clienteBusqueda.length < 2) { this.clienteResultados = []; return }
      this.clienteTimer = setTimeout(async () => {
        try {
          const res = await axios.get('/clientes/buscar-rapido',
            { params: { q: this.clienteBusqueda } })
          this.clienteResultados = res.data
        } catch { /* ignorar */ }
      }, 200)
    },
    seleccionarCliente(c) {
      this.clienteSeleccionado = c
      this.clienteBusqueda     = ''
      this.clienteResultados   = []
    },
    quitarCliente() {
      this.clienteSeleccionado = null
      this.clienteBusqueda     = ''
      this.clienteResultados   = []
    },
    async seleccionarConsumidorFinal() {
      try {
        const res = await axios.get('/clientes/consumidor-final')
        this.seleccionarCliente(res.data)
      } catch {
        this.error = 'No se encontró el cliente "Consumidor Final". Reinicia el servidor.'
      }
    },

    // ── Dialog Nuevo Cliente ──────────────────────────────────────────────────
    abrirDialogNuevo() {
      this.nuevoCliente      = { nombre: '', telefono: '', tipo_cliente: 'natural', rif_cedula: '' }
      this.errorCliente      = ''
      this.telefonoDuplicado = null
      this.dialogNuevoCliente = true
      this.$nextTick(() => this.$refs.inputNombreNuevo?.focus())
    },
    cerrarDialog() {
      this.dialogNuevoCliente = false
      this.errorCliente       = ''
      this.telefonoDuplicado  = null
    },
    async guardarNuevoCliente() {
      if (!this.nuevoCliente.nombre.trim()) {
        this.errorCliente = 'El nombre es requerido'
        return
      }
      if (!this.nuevoCliente.telefono.trim()) {
        this.errorCliente = 'El teléfono es requerido'
        return
      }
      this.guardandoCliente  = true
      this.errorCliente      = ''
      this.telefonoDuplicado = null
      try {
        const res = await axios.post('/clientes/', this.nuevoCliente)
        this.cerrarDialog()
        this.seleccionarCliente(res.data)
        this.tabActivo = 'venta'
      } catch (e) {
        if (e?.response?.status === 409) {
          this.telefonoDuplicado = e.response.data.cliente_existente
        } else {
          this.errorCliente = e?.response?.data?.detail || 'Error al crear el cliente'
        }
      } finally {
        this.guardandoCliente = false
      }
    },
    async usarClienteExistente() {
      try {
        const res = await axios.get(`/clientes/${this.telefonoDuplicado.id}`)
        this.cerrarDialog()
        this.seleccionarCliente(res.data)
        this.tabActivo = 'venta'
      } catch {
        this.errorCliente = 'Error al cargar el cliente existente'
      }
    },

    // ── Tabs ──────────────────────────────────────────────────────────────────
    cambiarTab(tab) {
      this.tabActivo = tab
      if (tab === 'clientes') this.cargarClientesRecientes()
      if (tab === 'historial') this.cargarVentasHoy()
    },
    async cargarClientesRecientes() {
      try {
        const res = await axios.get('/clientes/recientes')
        this.clientesRecientes = res.data
      } catch { this.clientesRecientes = [] }
    },
    buscarEnTab() {
      clearTimeout(this.busquedaTabTimer)
      if (!this.busquedaClientes || this.busquedaClientes.length < 2) {
        this.resultadosClientes = []
        return
      }
      this.busquedaTabTimer = setTimeout(async () => {
        try {
          const res = await axios.get('/clientes/buscar-rapido',
            { params: { q: this.busquedaClientes } })
          this.resultadosClientes = res.data
        } catch { this.resultadosClientes = [] }
      }, 200)
    },
    seleccionarDesdeTab(c) {
      this.seleccionarCliente(c)
      this.tabActivo = 'venta'
    },
    async cargarVentasHoy() {
      this.cargandoHistorial = true
      try {
        const res = await axios.get('/ventas/hoy')
        this.ventasHoy = res.data
      } catch { this.ventasHoy = [] }
      finally { this.cargandoHistorial = false }
    },

    // ── Confirmar venta ───────────────────────────────────────────────────────
    async cobrar() {
      this.error = ''
      if (!this.pagoCompleto)        { this.error = 'El cobro no cubre el total'; return }
      if (this.requiereAutorizacion && !this.autorizacionClave)
                                     { this.error = 'Ingresa la clave de autorización'; return }
      if (!this.tasaBcv)             { this.error = 'No hay tasa definida. Ve a Tasa BCV.'; return }

      this.cargando = true
      try {
        const payload = {
          usuario:            this.usuario.usuario || 'cajero',
          moneda_venta:       this.monedaVenta,
          tipo_precio:        this.tipoPrecio,
          descuento:          Number(this.descuentoGlobal || 0),
          observacion:        this.observacion,
          autorizacion_clave: this.autorizacionClave || '',
          cliente_id:         this.clienteSeleccionado ? this.clienteSeleccionado.id : null,
          detalles: this.carrito.map(item => ({
            producto_id:     Number(item.id),
            cantidad:        Number(item.cantidad),
            precio_unitario: Number(item.precio_unitario),
          })),
          pagos: this.pagos.map(p => ({
            metodo:            p.metodo,
            monto:             p.monto_original,
            referencia:        p.referencia || '',
            cuenta_destino_id: p.cuenta_destino_id || null,
          })),
        }

        const res = await axios.post('/ventas/', payload)
        this.ultimaVentaId = res.data.venta_id
        this.exitoso       = true

        // Limpiar estado de la venta
        this.carrito           = []
        this.pagos             = []
        this.descuentoGlobal   = 0
        this.autorizacionClave = ''
        this.observacion       = ''
        this.clienteSeleccionado = null
        this.nuevoMonto        = ''

        setTimeout(() => { this.exitoso = false }, 5000)
        await this.cargarProductos()
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al registrar la venta'
      } finally {
        this.cargando = false
      }
    },

    // ── Utilidades ────────────────────────────────────────────────────────────
    formatMonto(valor, moneda) {
      if (moneda === 'USD') return `$${Number(valor).toFixed(2)}`
      return `Bs. ${Number(valor).toFixed(2)}`
    },
    async imprimirPDF(ventaId) {
      try {
        const res = await axios.get(`/ventas/${ventaId}`)
        exportarFacturaPDF(res.data)
      } catch {
        alert('Error al generar el PDF')
      }
    },
    async abrirUbicPop(p) {
      this.ubicPop        = p
      this.ubicaciones    = []
      this.ubicPopCargando = true
      try {
        const res = await axios.get(`/ubicaciones/producto/${p.id}`)
        this.ubicaciones = res.data
      } catch { /* sin ubicaciones */ }
      this.ubicPopCargando = false
    },

    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    },
  }
}
</script>

<style scoped>
/* ── Top bar extras ── */
.top-meta { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
.selector-group { display: flex; align-items: center; gap: 0.4rem; }
.selector-label { color: #555555; font-size: 0.88rem; font-weight: 600; }
.btn-sel { padding: 0.3rem 0.8rem; background: #FFFFFF; color: var(--texto-sec); border: 1px solid var(--borde); border-radius: 6px; cursor: pointer; font-size: 0.88rem; }
.btn-sel.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }
.btn-base { border-color: #7b2cbf; }
.btn-base.activo-base { background: #7b2cbf; color: white; border-color: #7b2cbf; }
.tasas-info { display: flex; gap: 1rem; font-size: 0.85rem; color: var(--texto-sec); }
.tasas-info strong { color: var(--texto-principal); }
.aviso-base { background: #F3E8FF; border: 1px solid #7b2cbf; color: #6b21a8; border-radius: 8px; padding: 0.6rem 1rem; margin-bottom: 1rem; font-size: 0.88rem; }

/* ── Tabs nav ── */
.tabs-nav { display: flex; gap: 0.25rem; margin-bottom: 1.25rem; border-bottom: 2px solid var(--borde); }
.tab-btn { padding: 0.6rem 1.4rem; background: transparent; color: var(--texto-sec); border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; font-size: 0.9rem; transition: all 0.15s; }
.tab-btn:hover { color: var(--texto-principal); }
.tab-activo { color: var(--texto-principal) !important; border-bottom-color: #1A1A1A !important; font-weight: 700; }

/* ── Selector de cliente ── */
.cliente-top { background: #FFFFFF; border-radius: 10px; padding: 0.9rem 1.1rem; margin-bottom: 1rem; border: 1px solid var(--borde); }
.cliente-card { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.ck-check { color: #16A34A; font-size: 1.1rem; font-weight: 700; }
.ck-nombre { color: var(--texto-principal); font-weight: 600; font-size: 1rem; }
.ck-nivel { padding: 0.15rem 0.6rem; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }
.ck-stats { color: var(--texto-muted); font-size: 0.82rem; }
.btn-cambiar-cliente { margin-left: auto; padding: 0.3rem 0.85rem; background: transparent; border: 1px solid var(--borde); color: var(--texto-sec); border-radius: 6px; cursor: pointer; font-size: 0.82rem; }
.btn-cambiar-cliente:hover { border-color: var(--texto-principal); color: var(--texto-principal); }

.cliente-selector-row { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; }
.cliente-search-wrap { position: relative; flex: 1; min-width: 220px; }
.input-cliente { width: 100%; padding: 0.55rem 0.9rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 8px; font-size: 0.9rem; box-sizing: border-box; }
.cliente-dropdown { position: absolute; top: calc(100% + 4px); left: 0; right: 0; background: #FFFFFF; border: 1px solid var(--borde); border-radius: 8px; z-index: 50; max-height: 240px; overflow-y: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.cliente-opcion { display: flex; gap: 0.75rem; align-items: center; padding: 0.6rem 1rem; cursor: pointer; font-size: 0.88rem; border-bottom: 1px solid var(--borde-suave); }
.cliente-opcion:hover { background: var(--fondo-tabla-alt); }
.opcion-nombre { color: var(--texto-principal); font-weight: 500; }
.opcion-tel { color: var(--texto-muted); font-size: 0.8rem; }
.opcion-nivel { font-size: 0.78rem; font-weight: 700; margin-left: auto; }

.btn-consumidor { padding: 0.5rem 1rem; background: #FFFFFF; border: 1px solid var(--borde); color: var(--texto-sec); border-radius: 8px; cursor: pointer; font-size: 0.88rem; white-space: nowrap; }
.btn-consumidor:hover { background: var(--borde-suave); }
.btn-nuevo-cliente { padding: 0.5rem 1rem; background: var(--success); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 0.88rem; white-space: nowrap; }

.aviso-sin-cliente { background: var(--fondo-tabla-alt); border: 1px dashed var(--borde); color: var(--texto-sec); border-radius: 8px; padding: 1.5rem; text-align: center; margin-bottom: 1rem; font-size: 0.95rem; }
.aviso-sin-cliente strong { color: var(--texto-principal); }

/* ── Grid de venta ── */
.venta-grid { display: grid; grid-template-columns: 1fr 420px; gap: 1.5rem; }

/* ── Catálogo ── */
.catalogo { background: #FFFFFF; border-radius: 12px; padding: 1rem; border: 1px solid var(--borde); }
.buscador { width: 100%; padding: 0.6rem 1rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 8px; margin-bottom: 0.75rem; box-sizing: border-box; }
.txt-dim { color: var(--texto-muted); }
.stock-bajo { color: var(--danger) !important; }
.sin-datos { text-align: center; color: var(--texto-muted); padding: 1.5rem 0; }
.btn-agregar { background: #1A1A1A; color: #FFCC00; border: none; width: 28px; height: 28px; border-radius: 6px; cursor: pointer; font-size: 1.1rem; font-weight: 700; }

/* ── Panel derecho ── */
.panel-derecho { display: flex; flex-direction: column; gap: 1rem; }

/* ── Carrito ── */
.carrito-box { background: #FFFFFF; border-radius: 12px; padding: 1.25rem; border: 1px solid var(--borde); }
.carrito-box h2 { color: var(--texto-principal); margin: 0 0 1rem; font-size: 1rem; font-weight: 700; }
.vacio { color: var(--texto-muted); text-align: center; padding: 1.5rem 0; font-size: 0.9rem; }

.item { border-bottom: 1px solid var(--borde-suave); padding: 0.75rem 0; display: flex; flex-direction: column; gap: 0.4rem; }
.item-header { display: flex; justify-content: space-between; align-items: center; }
.item-nombre { color: var(--texto-principal); font-weight: 600; font-size: 0.9rem; }
.btn-quitar { background: var(--danger); color: white; border: none; width: 22px; height: 22px; border-radius: 4px; cursor: pointer; font-size: 0.9rem; }

.item-controles { display: flex; align-items: center; gap: 0.5rem; }
.item-controles button { background: var(--borde-suave); color: var(--texto-principal); border: 1px solid var(--borde); width: 24px; height: 24px; border-radius: 4px; cursor: pointer; }
.item-precio-snap { color: var(--texto-sec); font-size: 0.82rem; margin-left: auto; }

.item-precio-edit { display: flex; flex-direction: column; gap: 0.2rem; }
.item-precio-edit label { color: var(--texto-sec); font-size: 0.8rem; }
.item-precio-edit input { padding: 0.4rem 0.6rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 6px; font-size: 0.9rem; width: 100%; box-sizing: border-box; }

.item-subtotal { display: flex; justify-content: space-between; color: var(--texto-sec); font-size: 0.85rem; }
.tag-desc { color: #996600; }

.totales-box { border-top: 1px solid var(--borde); margin-top: 0.75rem; padding-top: 0.75rem; }
.fila-total { display: flex; justify-content: space-between; padding: 0.2rem 0; color: var(--texto-sec); font-size: 0.9rem; }
.fila-grande { color: var(--texto-principal); font-size: 1.1rem; font-weight: 700; margin-top: 0.4rem; }
.txt-desc { color: #996600; }
.txt-gris { color: var(--texto-muted); font-size: 0.82rem; }

.descuento-global { margin: 0.5rem 0; }
.descuento-global label { color: var(--texto-sec); font-size: 0.82rem; display: block; margin-bottom: 0.25rem; font-weight: 600; }
.descuento-global input { width: 100%; padding: 0.4rem 0.6rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 6px; box-sizing: border-box; }

/* ── Cobro ── */
.cobro-box { background: #FFFFFF; border-radius: 12px; padding: 1.25rem; border: 1px solid var(--borde); }
.cobro-box h2 { color: var(--texto-principal); margin: 0 0 1rem; font-size: 1rem; font-weight: 700; }

.form-pago { background: var(--borde-suave); border-radius: 8px; padding: 0.75rem; margin-bottom: 0.75rem; }
.form-pago-row { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.form-pago select { flex: 1; min-width: 140px; padding: 0.5rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 6px; font-size: 0.88rem; }
.monto-wrap { display: flex; align-items: center; gap: 0.25rem; }
.moneda-tag { color: #16A34A; font-weight: 700; font-size: 0.9rem; }
.monto-wrap input { width: 100px; padding: 0.5rem 0.4rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 6px; font-size: 0.9rem; }
.btn-agregar-pago { padding: 0.5rem 0.9rem; background: #1A1A1A; color: #FFCC00; border: none; border-radius: 6px; cursor: pointer; font-size: 0.88rem; white-space: nowrap; font-weight: 600; }
.btn-agregar-pago:disabled { opacity: 0.45; cursor: not-allowed; }
.input-referencia { width: 100%; margin-top: 0.5rem; padding: 0.4rem 0.6rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-sec); border-radius: 6px; font-size: 0.85rem; box-sizing: border-box; }

.equiv-preview { margin-top: 0.5rem; display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; font-size: 0.85rem; }
.equiv-label { color: var(--texto-sec); }
.equiv-valor { color: #16A34A; font-weight: 600; }
.saldo-preview { color: var(--texto-sec); }
.saldo-preview.exceso { color: var(--danger); }

.lista-pagos { margin: 0.75rem 0; display: flex; flex-direction: column; gap: 0.4rem; }
.pago-item { display: flex; justify-content: space-between; align-items: center; background: var(--borde-suave); border-radius: 6px; padding: 0.5rem 0.75rem; border: 1px solid var(--borde); }
.pago-izq { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; font-size: 0.85rem; }
.pago-metodo { color: var(--texto-principal); font-weight: 600; }
.pago-monto { color: var(--texto-sec); }
.pago-equiv { color: #16A34A; font-weight: 600; }
.pago-ref { color: var(--texto-muted); font-size: 0.8rem; }
.btn-rm-pago { background: var(--danger); color: white; border: none; width: 22px; height: 22px; border-radius: 4px; cursor: pointer; font-size: 0.9rem; flex-shrink: 0; }

.resumen-cobro { background: var(--borde-suave); border-radius: 8px; padding: 0.75rem; margin: 0.75rem 0; border: 1px solid var(--borde); }
.resumen-fila { display: flex; justify-content: space-between; padding: 0.2rem 0; color: var(--texto-sec); font-size: 0.9rem; }
.txt-verde  { color: #16A34A; font-weight: 600; }
.txt-rojo   { color: #DC2626; font-weight: 600; }
.txt-amarillo { color: #996600; font-weight: 600; }

.autorizacion-box { background: #FFF7ED; border: 1px solid #F59E0B; border-radius: 8px; padding: 0.75rem; margin: 0.75rem 0; }
.aut-titulo { color: #92400E; font-weight: 700; margin: 0 0 0.5rem; font-size: 0.9rem; }
.aut-motivos { color: #78350F; font-size: 0.85rem; margin: 0 0 0.5rem; padding-left: 1rem; }
.autorizacion-box input { width: 100%; padding: 0.5rem; background: #FFFFFF; border: 1px solid #F59E0B; color: var(--texto-principal); border-radius: 6px; box-sizing: border-box; }

.field { margin: 0.5rem 0; }
.field label { color: var(--texto-sec); font-size: 0.85rem; display: block; margin-bottom: 0.25rem; font-weight: 600; }
.field input { width: 100%; padding: 0.5rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 6px; box-sizing: border-box; }

.btn-cobrar { width: 100%; padding: 0.85rem; background: #1A1A1A; color: #FFCC00; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; margin-top: 0.5rem; font-weight: 700; }
.btn-cobrar:disabled { opacity: 0.45; cursor: not-allowed; }
.venta-exito-row { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-top: 0.75rem; flex-wrap: wrap; }
.msg-exito { color: #16A34A; font-weight: 600; margin: 0; }
.btn-pdf { background: var(--success); color: white; border: none; padding: 0.45rem 1.1rem; border-radius: 8px; cursor: pointer; font-size: 0.9rem; }
.sel-cuenta { padding: 0.4rem 0.6rem; background: #FFFFFF; border: 1px solid var(--borde); color: var(--texto-principal); border-radius: 6px; font-size: 0.82rem; min-width: 160px; }
.cuenta-unica { color: #16A34A; font-size: 0.82rem; align-self: center; white-space: nowrap; font-weight: 600; }
.msg-error { color: var(--danger); margin-top: 0.5rem; font-size: 0.9rem; }

/* ── Tab: Clientes ── */
.tab-clientes { background: #FFFFFF; border-radius: 12px; padding: 1.25rem; border: 1px solid var(--borde); }
.tc-header { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }
.tc-header .buscador { flex: 1; min-width: 200px; margin-bottom: 0; }
.tc-titulo-seccion { color: var(--texto-muted); font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin: 0.75rem 0 0.5rem; }
.tc-lista { display: flex; flex-direction: column; gap: 0.3rem; }
.tc-row { display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0.9rem; background: var(--fondo-tabla-alt); border-radius: 8px; cursor: pointer; gap: 1rem; flex-wrap: wrap; border: 1px solid var(--borde); }
.tc-row:hover { background: var(--borde-suave); border-color: var(--amarillo); }
.tc-info { display: flex; flex-direction: column; gap: 0.15rem; }
.tc-nombre { color: var(--texto-principal); font-weight: 600; font-size: 0.9rem; }
.tc-tel { color: var(--texto-muted); font-size: 0.8rem; }
.tc-right { display: flex; align-items: center; gap: 0.75rem; }
.tc-nivel { padding: 0.15rem 0.6rem; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }
.tc-compras { color: var(--texto-muted); font-size: 0.8rem; }

/* ── Tab: Historial ── */
.tab-historial { background: #FFFFFF; border-radius: 12px; padding: 1.25rem; border: 1px solid var(--borde); }
.th-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.th-subtitulo { color: var(--texto-sec); font-size: 0.9rem; font-weight: 700; }
.btn-refrescar { padding: 0.3rem 0.8rem; background: var(--borde-suave); border: 1px solid var(--borde); color: var(--texto-sec); border-radius: 6px; cursor: pointer; font-size: 0.82rem; }
.btn-refrescar:hover { background: var(--borde); color: var(--texto-principal); }
.tag-estado { padding: 0.15rem 0.55rem; background: #16A34A1A; color: #16A34A; border-radius: 12px; font-size: 0.78rem; font-weight: 600; }
.btn-ver { padding: 0.25rem 0.7rem; background: var(--borde-suave); border: 1px solid var(--borde); color: var(--texto-sec); border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
.btn-ver:hover { border-color: var(--texto-principal); color: var(--texto-principal); }
.historial-resumen { margin-top: 0.75rem; color: var(--texto-sec); font-size: 0.88rem; }
.historial-resumen strong { color: var(--texto-principal); }

/* ── Dialog ── */
.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 100; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.dialog { background: #FFFFFF; border-radius: 12px; width: 100%; max-width: 440px; box-shadow: 0 8px 32px rgba(0,0,0,0.15); border: 0.5px solid var(--borde); }
.dialog-header { display: flex; justify-content: space-between; align-items: center; padding: 1.1rem 1.25rem; border-bottom: 1px solid var(--borde); }
.dialog-header h3 { margin: 0; color: var(--texto-principal); font-size: 1rem; font-weight: 700; }
.btn-cerrar-dialog { background: transparent; border: none; color: var(--texto-muted); font-size: 1.1rem; cursor: pointer; padding: 0.2rem 0.4rem; }
.btn-cerrar-dialog:hover { color: var(--texto-principal); }
.dialog-body { padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem; }
.dialog-body .field label { color: var(--texto-sec); font-size: 0.85rem; display: block; margin-bottom: 0.3rem; font-weight: 600; }
.dialog-body .field label small { color: var(--texto-muted); }
.dialog-body .field input { width: 100%; padding: 0.55rem 0.8rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 8px; font-size: 0.9rem; box-sizing: border-box; }
.dialog-body .field input:focus { outline: none; border-color: var(--amarillo); box-shadow: 0 0 0 2px rgba(255,204,0,0.25); }
.radio-group { display: flex; gap: 1.5rem; }
.radio-opt { display: flex; align-items: center; gap: 0.4rem; color: var(--texto-sec); font-size: 0.88rem; cursor: pointer; }
.aviso-duplicado { background: #FFF7ED; border: 1px solid #F59E0B; border-radius: 8px; padding: 0.75rem; }
.aviso-duplicado p { margin: 0 0 0.6rem; color: #92400E; font-size: 0.88rem; }
.aviso-duplicado strong { color: var(--texto-principal); }
.duplicado-btns { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.error-cliente { color: var(--danger); font-size: 0.85rem; margin: 0; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 0.6rem; padding: 1rem 1.25rem; border-top: 1px solid var(--borde); }
.btn-primary { padding: 0.55rem 1.2rem; background: #1A1A1A; color: #FFCC00; border: none; border-radius: 8px; cursor: pointer; font-size: 0.9rem; font-weight: 700; }
.btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-sec { padding: 0.55rem 1.2rem; background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); border-radius: 8px; cursor: pointer; font-size: 0.9rem; }
.btn-sec:hover { background: var(--borde-suave); }

/* ── Ubicaciones popup ── */
.btn-ubicar-v { background: transparent; border: none; cursor: pointer; font-size: 0.85rem; padding: 0 0.15rem; opacity: 0.6; }
.btn-ubicar-v:hover { opacity: 1; }

.ubic-pop-overlay { position: fixed; inset: 0; z-index: 200; display: flex; align-items: center; justify-content: center; }
.ubic-pop { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 12px; box-shadow: 0 8px 32px #0000001A; width: 420px; max-width: 95vw; overflow: hidden; }
.ubic-pop-header { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; border-bottom: 1px solid var(--borde); font-weight: 600; font-size: 0.9rem; color: var(--texto-principal); }
.ubic-pop-cargando { padding: 1rem; color: var(--texto-muted); font-size: 0.88rem; }
.ubic-pop-vacio    { padding: 1rem; color: var(--texto-muted); font-size: 0.88rem; margin: 0; }
.ubic-pop-tabla    { width: 100%; border-collapse: collapse; }
.ubic-pop-tabla th { padding: 0.45rem 0.75rem; background: var(--fondo-sidebar); color: var(--texto-muted); font-size: 0.78rem; text-align: left; font-weight: 700; }
.ubic-pop-tabla td { padding: 0.45rem 0.75rem; border-top: 1px solid var(--borde-suave); font-size: 0.88rem; color: var(--texto-principal); }
</style>
