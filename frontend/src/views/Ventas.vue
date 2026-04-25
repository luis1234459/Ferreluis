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
            <template v-if="esAdmin">
              <span>Binance: <strong class="txt-yellow">{{ tasaBinance ? tasaBinance.toFixed(2) : '...' }}</strong></span>
              <span>Factor: <strong class="txt-green">{{ factor ? factor.toFixed(4) : '...' }}</strong></span>
            </template>
            <template v-else>
              <span class="tasa-oculta">
                <span class="tasa-letra txt-yellow">B</span>
                <span class="tasa-valor">Binance: <strong class="txt-yellow">{{ tasaBinance ? tasaBinance.toFixed(2) : '...' }}</strong></span>
              </span>
              <span class="tasa-oculta">
                <span class="tasa-letra txt-green">F</span>
                <span class="tasa-valor">Factor: <strong class="txt-green">{{ factor ? factor.toFixed(4) : '...' }}</strong></span>
              </span>
            </template>
          </div>
        </div>
      </div>

      <div class="aviso-base" v-if="tabActivo === 'venta' && tipoPrecio === 'base'">
        Modo <strong>Precio Base USD</strong> — se aplicará descuento divisa. Requiere autorización.
      </div>

      <!-- ── Área interior con padding ── -->
      <div class="contenido-inner" style="padding-top:0;">

      <!-- ── Tabs nav ── -->
      <div class="tabs-nav">
        <button :class="['tab-btn', tabActivo === 'venta' ? 'tab-activo' : '']"
          @click="tabActivo = 'venta'">Nueva Venta</button>
        <button :class="['tab-btn', tabActivo === 'clientes' ? 'tab-activo' : '']"
          @click="cambiarTab('clientes')">Clientes</button>
        <button :class="['tab-btn', tabActivo === 'historial' ? 'tab-activo' : '']"
          @click="cambiarTab('historial')">Historial</button>
      </div>

      <!-- ══════════════════════════════ Tab: Nueva Venta ══════════════════════════════ -->
      <div v-show="tabActivo === 'venta'">

        <!-- Selector de cliente -->
        <div class="cliente-top">
          <div v-if="clienteSeleccionado" class="cliente-card">
            <span class="ck-check">✓</span>
            <span class="ck-nombre">{{ clienteSeleccionado.nombre }}</span>
            <span v-if="clienteSeleccionado.nivel_fidelidad" class="ck-nivel"
              :style="{ background: clienteSeleccionado.nivel_fidelidad.color + '22',
                        color: clienteSeleccionado.nivel_fidelidad.color }">
              {{ clienteSeleccionado.nivel_fidelidad.nombre }}
            </span>
            <span v-if="clienteSeleccionado.tiene_credito" class="ck-credito"
              :class="(clienteSeleccionado.saldo_credito || 0) > 0 ? 'ck-credito-ok' : 'ck-credito-agotado'"
              title="Saldo de crédito disponible">
              Crédito: ${{ (clienteSeleccionado.saldo_credito || 0).toFixed(2) }}
            </span>
            <span class="ck-stats" v-if="!clienteSeleccionado.es_cliente_generico">
              {{ clienteSeleccionado.total_compras }} compras ·
              ${{ (clienteSeleccionado.monto_acumulado_usd || 0).toFixed(0) }} USD
            </span>
            <button class="btn-cambiar-cliente" @click="quitarCliente">Cambiar cliente</button>
          </div>

          <div v-else class="cliente-selector-row">
            <div class="cliente-search-wrap">
              <input
                v-model="clienteBusqueda"
                @input="buscarCliente"
                placeholder="Teléfono o nombre del cliente..."
                class="input-cliente"
              />
              <div v-if="clienteResultados.length > 0" class="cliente-dropdown">
                <div
                  v-for="c in clienteResultados" :key="c.id"
                  class="cliente-opcion"
                  @click="seleccionarCliente(c)"
                >
                  <span class="opcion-tel">📱 {{ c.telefono }}</span>
                  <span class="opcion-nombre">— {{ c.nombre }}</span>
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

        <div v-if="!clienteSeleccionado" class="aviso-sin-cliente">
          Selecciona un cliente o usa <strong>Consumidor Final</strong> para comenzar la venta
        </div>

        <!-- ── Grid 50/50 ── -->
        <div v-if="clienteSeleccionado" class="venta-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;width:100%;">

          <!-- ── Columna izq: Catálogo ── -->
          <div class="catalogo" style="width:100%;min-width:0;">

            <!-- Buscador + botón filtros -->
            <div class="buscador-wrap">
              <input
                v-model="busqueda"
                ref="inputBuscador"
                placeholder="Buscar producto..."
                class="buscador"
                autocomplete="off"
                @keydown.down.prevent="moverAbajo"
                @keydown.up.prevent="moverArriba"
                @keydown.enter.prevent="seleccionarResaltado"
                @keydown.escape="cerrarDropdown"
              />
              <button
                class="btn-filtros-toggle"
                :class="{ active: filtrosAbiertos }"
                @click="filtrosAbiertos = !filtrosAbiertos"
                title="Filtros"
              >⚙ Filtros</button>
            </div>

            <!-- Panel de filtros colapsable -->
            <div v-if="filtrosAbiertos" class="filtros-panel">
              <select v-model="filtroDepartamento" class="filtro-sel" @change="filtroCategoria = null; cargarProductos()">
                <option :value="null">Todos los dept.</option>
                <option v-for="d in departamentos" :key="d.id" :value="d.id">{{ d.nombre }}</option>
              </select>
              <select v-model="filtroCategoria" class="filtro-sel" @change="cargarProductos()">
                <option :value="null">Todas las cat.</option>
                <option v-for="c in categoriasDeFiltro" :key="c.id" :value="c.id">{{ c.nombre }}</option>
              </select>
              <select v-model="filtroProveedor" class="filtro-sel" @change="cargarProductos()">
                <option :value="null">Todos los prov.</option>
                <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
              </select>
              <button v-if="filtroDepartamento || filtroCategoria || filtroProveedor" class="btn-limpiar-filtros" @click="limpiarFiltros">✕ Limpiar</button>
            </div>

            <!-- Acceso rápido -->
            <div v-if="!busqueda && !filtroDepartamento && !filtroCategoria && !filtroProveedor" class="acceso-rapido">
              <div v-if="ultimosVendidos.length" class="ar-grupo">
                <span class="ar-titulo">Últimos vendidos</span>
                <div class="ar-chips">
                  <button
                    v-for="p in ultimosVendidos" :key="p.id"
                    class="ar-chip"
                    @click="agregarPorId(p.id)"
                  >{{ p.nombre }}</button>
                </div>
              </div>
              <div v-if="masVendidos.length" class="ar-grupo">
                <span class="ar-titulo">Más vendidos</span>
                <div class="ar-chips">
                  <button
                    v-for="p in masVendidos" :key="p.id"
                    class="ar-chip"
                    @click="agregarPorId(p.id)"
                  >{{ p.nombre }}</button>
                </div>
              </div>
            </div>

            <!-- Lista compacta de productos -->
            <div class="prod-list" ref="tbodyCatalogo">
              <div
                v-for="(p, index) in productosFiltrados" :key="p.id"
                :class="['prod-item', index === indiceResaltado ? 'prod-item-resaltado' : '']"
                @mouseenter="indiceResaltado = index"
                @mouseleave="indiceResaltado = -1"
                @click="agregar(p); $refs.inputBuscador.focus()"
              >
                <div class="pi-nombre">
                  <span class="pi-nombre-texto">
                    {{ p.nombre }}
                    <span v-if="p.codigo && !p.tiene_variantes" class="cod-tag-v">{{ p.codigo }}</span>
                  </span>
                  <div v-if="p.tiene_variantes && (p.variantes_resumen || []).some(v => v.activo)" class="pi-vcods">
                    <span
                      v-for="v in (p.variantes_resumen || []).filter(v => v.activo).slice(0, 5)"
                      :key="v.id"
                      class="pi-vcod"
                    >{{ v.color && p.esquema_variante !== 'clase' ? v.clase + '/' + v.color : v.clase }}</span>
                    <span v-if="(p.variantes_resumen || []).filter(v => v.activo).length > 5" class="pi-vcod-mas">
                      +{{ (p.variantes_resumen || []).filter(v => v.activo).length - 5 }}
                    </span>
                  </div>
                </div>
                <span class="pi-precios">
                  <template v-if="!p.tiene_variantes">
                    <span class="pi-bs">Bs {{ precioBs(p).toFixed(2) }}</span>
                    <span class="pi-ref">${{ precioRef(p).toFixed(2) }}</span>
                    <span class="pi-stock">{{ p.stock }}</span>
                    <span class="pi-base">Base: ${{ precioBase(p).toFixed(2) }}</span>
                  </template>
                  <template v-else>
                    <span class="pi-variantes-count">{{ (p.variantes_resumen || []).filter(v => v.activo).length }} var.</span>
                    <span class="pi-stock">{{ (p.variantes_resumen || []).filter(v => v.activo).reduce((s, v) => s + (v.stock || 0), 0) }} uds</span>
                  </template>
                  <button class="btn-ubicar-v" @click.stop="abrirUbicPop(p)" title="Ver ubicaciones">📍</button>
                </span>
              </div>
              <div v-if="productosFiltrados.length === 0 && (busqueda.length >= 2 || filtroDepartamento || filtroCategoria || filtroProveedor)" class="prod-sin-res">Sin resultados</div>
              <div v-else-if="productosFiltrados.length === 0" class="prod-sin-res">Escribe 2+ caracteres para buscar</div>
            </div>
          </div>

          <!-- ── Columna der: Carrito ── -->
          <div class="carrito-col">
            <div class="carrito-box">
              <h2>Carrito</h2>
              <div v-if="carrito.length === 0" class="vacio">Sin productos</div>

              <div v-for="(item, i) in carrito" :key="i" class="item-row">
                <button class="btn-cnt" @click="restar(i)">−</button>
                <span class="item-qty">{{ item.cantidad }}</span>
                <button class="btn-cnt" @click="sumar(i)">+</button>
                <div class="item-info">
                  <span class="item-nombre">
                    {{ item.nombre }}
                    <span v-if="item.variante_label" class="variante-tag">{{ item.variante_label }}</span>
                    <span v-if="item.variante_codigo" class="cod-tag-v">{{ item.variante_codigo }}</span>
                    <span v-else-if="item.codigo && !item.variante_id" class="cod-tag-v">{{ item.codigo }}</span>
                  </span>
                  <span class="item-ref">Ref: ${{ Number(item.precio_unitario).toFixed(2) }}</span>
                </div>
                <span class="item-sub">{{ formatMonto(subtotalLinea(item), monedaVenta) }}</span>
                <button class="btn-quitar" @click="quitar(i)">✕</button>
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

            <!-- Botones inferiores (siempre visibles) -->
            <div class="botones-carrito" v-if="carrito.length > 0">
              <button class="btn-guardar-presupuesto" @click="abrirModalPresupuesto">📋 Guardar como presupuesto</button>
              <button class="btn-abrir-cobro" @click="abrirModalCobro">✓ Registrar venta</button>
            </div>

            <!-- Éxito post-venta -->
            <div v-if="exitoso" class="venta-exito-row">
              <p class="msg-exito">¡Venta #{{ ultimaVentaId }} registrada!</p>
              <button class="btn-pdf" @click="imprimirPDF(ultimaVentaId)">🖨 Imprimir PDF</button>
            </div>
          </div>

        </div><!-- /venta-grid -->
      </div><!-- /tab venta -->

      <!-- ══════════════════════════════ Tab: Clientes ══════════════════════════════ -->
      <div v-show="tabActivo === 'clientes'" class="tab-clientes">
        <div class="tc-header">
          <input
            v-model="busquedaClientes"
            @input="buscarEnTab"
            placeholder="Teléfono o nombre del cliente..."
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

      <!-- ══════════════════════════════ Tab: Historial ══════════════════════════════ -->
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

      <!-- ══════════════════════════════ Dialog: Nuevo Cliente ══════════════════════════════ -->
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

      <!-- Popup ubicaciones -->
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

      </div><!-- /contenido-inner -->
    </main>

    <!-- ══════════════════════════════ Modal: Cobro ══════════════════════════════ -->
    <div class="cobro-modal-overlay" v-if="modalCobro" @click.self="modalCobro = false">
      <div class="cobro-modal">

        <div class="cobro-modal-header">
          <h3>Cobro</h3>
          <button class="cobro-modal-cerrar" @click="modalCobro = false">✕</button>
        </div>

        <div class="cobro-modal-resumen">
          <span>Total a cobrar:</span>
          <strong>{{ formatMonto(totalEnMoneda, monedaVenta) }}</strong>
        </div>

        <div class="modo-cobro-selector">
          <button :class="['btn-modo', modoCobro === 'USD' ? 'activo' : '']" @click="modoCobro = 'USD'">💵 USD</button>
          <button :class="['btn-modo', modoCobro === 'Bs' ? 'activo' : '']" @click="modoCobro = 'Bs'">🇻🇪 Bs</button>
          <button :class="['btn-modo', modoCobro === 'mixto' ? 'activo' : '']" @click="modoCobro = 'mixto'">⚡ Mixto</button>
        </div>

        <!-- Formulario de pago -->
        <div class="cobro-modal-body">
          <div class="form-pago">
            <div class="form-pago-row">
              <select v-model="nuevoMetodo" @change="onCambioMetodo">
                <option v-for="m in metodosDisponibles" :key="m.value" :value="m.value">{{ m.label }}</option>
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
              <span v-if="nuevoMonedaPago !== monedaVenta && tasaBcv" class="equiv-cruce">
                {{ nuevoMonedaPago === 'USD' ? 'Bs. ' + (nuevoMonto * tasaBcv).toFixed(2) : '$' + (nuevoMonto / tasaBcv).toFixed(2) + ' USD' }}
              </span>
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

          <template v-if="pagos.length > 0">
            <div class="resumen-cobro" v-if="modoCobro !== 'mixto'">
              <div class="resumen-fila"><span>Total:</span><strong>{{ formatMonto(totalEnMoneda, monedaVenta) }}</strong></div>
              <div class="resumen-fila"><span>Abonado:</span><strong class="txt-verde">{{ formatMonto(totalAbonado, monedaVenta) }}</strong></div>
              <div class="resumen-fila" v-if="saldoPendiente > 0.01"><span>Falta:</span><strong class="txt-rojo">{{ formatMonto(saldoPendiente, monedaVenta) }}</strong></div>
              <div class="resumen-fila" v-if="exceso > 0.01"><span>Vuelto:</span><strong class="txt-amarillo">{{ formatMonto(exceso, monedaVenta) }}</strong></div>
            </div>
            <div class="resumen-mixto" v-else>
              <div class="resumen-mixto-fila">
                <span>Total USD:</span>
                <strong>${{ totalUSD.toFixed(2) }}</strong>
              </div>
              <div class="resumen-mixto-fila">
                <span>Total Bs:</span>
                <strong>Bs. {{ totalBs.toFixed(2) }}</strong>
              </div>
              <div class="resumen-mixto-fila" v-if="totalAbonadoUSD > 0">
                <span>Abonado USD:</span>
                <strong class="txt-verde">${{ totalAbonadoUSD.toFixed(2) }}</strong>
              </div>
              <div class="resumen-mixto-fila" v-if="totalAbonadoBs > 0">
                <span>Abonado Bs:</span>
                <strong class="txt-verde">Bs. {{ totalAbonadoBs.toFixed(2) }}</strong>
              </div>
              <template v-if="saldoPendiente > 0.01">
                <div class="resumen-mixto-fila" style="border-top:1px solid var(--borde);padding-top:0.4rem;margin-top:0.3rem;">
                  <span>Falta en USD:</span>
                  <strong class="txt-rojo">${{ saldoPendienteUSD.toFixed(2) }}</strong>
                </div>
                <div class="resumen-mixto-fila">
                  <span>Falta en Bs:</span>
                  <strong class="txt-rojo">Bs. {{ saldoPendienteBs.toFixed(2) }}</strong>
                </div>
              </template>
              <div class="resumen-mixto-fila" v-if="exceso > 0.01">
                <span>Vuelto:</span>
                <strong class="txt-amarillo">{{ formatMonto(exceso, monedaVenta) }}</strong>
              </div>
            </div>
          </template>

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

          <p class="msg-error" v-if="error">{{ error }}</p>
        </div>

        <div class="cobro-modal-footer">
          <button class="btn-cancelar-cobro" @click="modalCobro = false">✕ Cancelar</button>
          <div class="btn-cobrar-grupo">
            <button class="btn-cobrar-accion" @click="cobrar('solo')"
              :disabled="!pagoCompleto || cargando" title="Registrar">✓</button>
            <button class="btn-cobrar-accion" @click="cobrar('whatsapp')"
              :disabled="!pagoCompleto || cargando" title="Registrar y enviar WhatsApp">✓ 💬</button>
            <button class="btn-cobrar-accion" @click="cobrar('imprimir')"
              :disabled="!pagoCompleto || cargando" title="Registrar e imprimir">✓ 🖨️</button>
          </div>
        </div>

      </div>
    </div>

    <!-- ══════════════════════════════ Modal: Presupuesto ══════════════════════════════ -->
    <div class="cobro-modal-overlay" v-if="modalPresupuesto" @click.self="continuarVenta">
      <div class="cobro-modal">
        <template v-if="!presupuestoExito">
          <div class="cobro-modal-header">
            <h3>📋 Guardar Presupuesto</h3>
            <button class="cobro-modal-cerrar" @click="continuarVenta">✕</button>
          </div>
          <div class="cobro-modal-body">
            <div class="field">
              <label>Nombre / Referencia *</label>
              <input v-model="presupuestoNombre" placeholder="Ej: Cotización materiales Juan" />
            </div>
            <div class="field">
              <label>Cliente</label>
              <input class="input-readonly"
                :value="clienteSeleccionado ? clienteSeleccionado.nombre + (clienteSeleccionado.telefono ? ' · ' + clienteSeleccionado.telefono : '') : 'Consumidor Final'"
                readonly />
            </div>
            <div class="field">
              <label>Observación <small>(opcional)</small></label>
              <input v-model="presupuestoObs" placeholder="Opcional..." />
            </div>
            <div class="field">
              <label>Fecha de validez <small>(opcional)</small></label>
              <input v-model="presupuestoFechaValidez" type="date" />
            </div>
            <p class="msg-error" v-if="presupuestoError">{{ presupuestoError }}</p>
          </div>
          <div class="cobro-modal-footer">
            <button class="btn-cancelar-cobro" @click="continuarVenta">✕ Cancelar</button>
            <button class="btn-primary" @click="guardarPresupuesto" :disabled="presupuestoGuardando">
              {{ presupuestoGuardando ? 'Guardando...' : 'Guardar presupuesto' }}
            </button>
          </div>
        </template>
        <template v-else>
          <div class="cobro-modal-header">
            <h3>✓ {{ presupuestoExito.numero }}</h3>
            <button class="cobro-modal-cerrar" @click="continuarVenta">✕</button>
          </div>
          <div class="cobro-modal-body">
            <p class="pres-exito-msg">Presupuesto guardado exitosamente</p>
            <div class="pres-opciones">
              <button class="btn-primary" @click="continuarVenta">Continuar venta</button>
              <button class="btn-sec" @click="limpiarCarritoDesdePresupuesto">Limpiar carrito</button>
              <button class="btn-sec" @click="verPresupuesto">Ver presupuestos</button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Modal variantes -->
    <div class="cobro-modal-overlay" v-if="modalVariantes" @click.self="modalVariantes = false">
      <div class="cobro-modal" style="max-width:420px">
        <div class="cobro-modal-header">
          <h3>{{ productoVariantes?.nombre }}</h3>
          <button class="cobro-modal-cerrar" @click="modalVariantes = false">✕</button>
        </div>
        <div class="cobro-modal-body">
          <p style="color:var(--texto-muted);font-size:0.85rem;margin:0 0 0.75rem">
            Selecciona la variante:
          </p>
          <div class="variantes-lista">
            <button
              v-for="v in variantes"
              :key="v.id"
              class="variante-item"
              @click="seleccionarVariante(v)"
            >
              <div class="variante-info">
                <span class="variante-clase">{{ v.clase }}</span>
                <span v-if="v.color" class="variante-color">{{ v.color }}</span>
                <span v-if="v.codigo" class="variante-cod-tag">{{ v.codigo }}</span>
              </div>
              <div class="variante-right">
                <span class="variante-stock">Stock: {{ v.stock }}</span>
                <span class="variante-bs">Bs {{ variantePrecioBs(v).toFixed(2) }}</span>
                <span class="variante-ref">${{ variantePrecioRef(v).toFixed(2) }}</span>
                <span class="variante-base">Base: ${{ variantePrecioBase(v).toFixed(2) }}</span>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal garantías -->
    <ModalGarantia
      v-if="modalGarantia"
      :items="itemsGarantia"
      @confirmar="onGarantiaConfirmada"
      @cancelar="modalGarantia = false"
    />

    <!-- Nota de entrega para impresión -->
    <div id="nota-print" v-if="notaImpresion">
      <div class="np-encabezado">
        <p class="np-empresa">FERRETERÍA FERRE-UTIL</p>
        <p class="np-subtitulo">Nota de Entrega</p>
      </div>
      <div class="np-datos">
        <p><strong>Cliente:</strong> {{ notaImpresion.clienteNombre }}</p>
        <p><strong>Fecha:</strong> {{ notaImpresion.fecha }}</p>
        <p><strong>Tasa BCV:</strong> Bs. {{ Number(notaImpresion.tasaBcv).toFixed(2) }} / USD</p>
      </div>
      <table class="np-tabla">
        <thead>
          <tr>
            <th>Producto</th>
            <th class="np-th-num">Cant.</th>
            <th class="np-th-num">P.Unit. Bs</th>
            <th class="np-th-num">Subtotal Bs</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(p, i) in notaImpresion.productos" :key="i">
            <tr>
              <td>
                {{ p.nombre }}
                <span v-if="p.variante_label" class="np-variante"> — {{ p.variante_label }}</span>
                <span v-if="p.variante_codigo" class="np-cod"> [{{ p.variante_codigo }}]</span>
              </td>
              <td class="np-td-num">{{ p.cantidad }}</td>
              <td class="np-td-num">{{ (Number(p.precio_unitario) * Number(notaImpresion.tasaBcv)).toFixed(2) }}</td>
              <td class="np-td-num">{{ (Number(p.precio_unitario) * Number(notaImpresion.tasaBcv) * p.cantidad).toFixed(2) }}</td>
            </tr>
            <tr v-if="npGarantia(p.id)" class="np-fila-garantia">
              <td colspan="4">
                <div class="np-garantia-bloque">
                  <span v-if="npGarantia(p.id).serial"><strong>Serial:</strong> {{ npGarantia(p.id).serial }}</span>
                  <span v-if="npGarantia(p.id).modelo">&nbsp;·&nbsp;<strong>Modelo:</strong> {{ npGarantia(p.id).modelo }}</span>
                  <span v-if="npGarantia(p.id).meses_garantia">&nbsp;·&nbsp;<strong>Garantía:</strong> {{ npGarantia(p.id).meses_garantia }} meses</span>
                  <div v-if="npGarantia(p.id).condiciones_snapshot" class="np-garantia-cond">{{ npGarantia(p.id).condiciones_snapshot }}</div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div class="np-total">TOTAL: Bs {{ Number(notaImpresion.totalBs).toFixed(2) }}</div>

      <div class="np-firmas" v-if="notaImpresion.garantias && notaImpresion.garantias.length">
        <div class="np-firma-bloque">
          <div class="np-firma-linea"></div>
          <div class="np-firma-label">Firma del Cliente</div>
        </div>
        <div class="np-firma-bloque">
          <div class="np-firma-linea"></div>
          <div class="np-firma-label">Firma del Vendedor</div>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import ModalGarantia from '../components/ModalGarantia.vue'
import axios from 'axios'
import { exportarFacturaPDF } from '@/utils/facturaPDF.js'

const METODOS_USD = ['efectivo_usd', 'zelle', 'binance', 'credito']
const LABELS = {
  efectivo_usd:     'Efectivo $',
  zelle:            'Zelle',
  binance:          'Binance',
  efectivo_bs:      'Efectivo Bs',
  transferencia_bs: 'Transferencia Bs',
  pago_movil:       'Pago Móvil',
  punto_banesco:    'Punto Banesco',
  punto_provincial: 'Punto Provincial',
  credito:          'A crédito',
}
const TOLERANCIA = 0.01

export default {
  components: { AppSidebar, ModalGarantia },
  name: 'Ventas',
  data() {
    return {
      usuario:    JSON.parse(localStorage.getItem('usuario') || '{}'),
      productos:  [],
      tasaBcv:    null,
      tasaBinance:null,
      factor:     1,
      busqueda:        '',
      indiceResaltado: -1,

      filtrosAbiertos:    false,
      departamentos:      [],
      categorias:         [],
      proveedores:        [],
      filtroDepartamento: null,
      filtroCategoria:    null,
      filtroProveedor:    null,
      masVendidos:        [],
      ultimosVendidos:    [],

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

      // Estado
      cargando:      false,
      exitoso:       false,
      error:         '',
      ultimaVentaId: null,
      cuentasPorMetodo: {},

      // Modal cobro
      modalCobro: false,
      modoCobro: 'USD',

      // Modal presupuesto
      modalPresupuesto: false,
      presupuestoNombre: '',
      presupuestoObs: '',
      presupuestoFechaValidez: '',
      presupuestoGuardando: false,
      presupuestoError: '',
      presupuestoExito: null,

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

      // Nota de entrega
      notaImpresion: null,

      // Variantes
      modalVariantes:    false,
      productoVariantes: null,
      variantes:         [],
      cargandoVariantes: false,

      // Garantías
      modalGarantia:       false,
      itemsGarantia:       [],
      garantiasPendientes: [],  // se llena al confirmar el modal
    }
  },
  computed: {
    tituloPagina() {
      if (this.tabActivo === 'clientes') return 'Clientes'
      if (this.tabActivo === 'historial') return 'Historial del Día'
      return 'Nueva Venta'
    },
    productosFiltrados() {
      const q = this.busqueda.trim().toLowerCase()
      const tienesFiltro = this.filtroDepartamento || this.filtroCategoria || this.filtroProveedor
      if (q.length < 2 && !tienesFiltro) return []
      if (q.length >= 2) {
        // Código exacto en producto simple
        const exactCodigo = this.productos.filter(p =>
          p.codigo && p.codigo.toLowerCase() === q
        )
        if (exactCodigo.length) return exactCodigo
        // Código exacto en variante → retorna el padre (se auto-agrega en seleccionarResaltado)
        const exactVariante = this.productos.filter(p =>
          p.variantes_resumen && p.variantes_resumen.some(v => v.codigo && v.codigo.toLowerCase() === q)
        )
        if (exactVariante.length) return exactVariante
        return this.productos
      }
      return this.productos
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
    categoriasDeFiltro() {
      if (!this.filtroDepartamento) return this.categorias
      return this.categorias.filter(c => c.departamento_id === this.filtroDepartamento)
    },
    tienePermiso() {
      return (modulo) => {
        if (this.usuario.rol === 'admin') return true
        const p = this.usuario.permisos
        if (p == null) return true
        return Array.isArray(p) ? p.includes(modulo) : true
      }
    },
    cuentasDelMetodo() { return this.cuentasPorMetodo[this.nuevoMetodo] || [] },
    metodosDisponibles() {
      const USD = [
        { value: 'efectivo_usd',  label: 'Efectivo $' },
        { value: 'zelle',         label: 'Zelle' },
        { value: 'binance',       label: 'Binance' },
      ]
      const BS = [
        { value: 'efectivo_bs',      label: 'Efectivo Bs' },
        { value: 'transferencia_bs', label: 'Transferencia Bs' },
        { value: 'pago_movil',       label: 'Pago Móvil' },
        { value: 'punto_banesco',    label: 'Punto Banesco' },
        { value: 'punto_provincial', label: 'Punto Provincial' },
      ]
      if (this.modoCobro === 'USD') return USD
      if (this.modoCobro === 'Bs')  return BS
      const all = [...USD, ...BS]
      if (this.clienteSeleccionado?.tiene_credito)
        all.push({ value: 'credito', label: 'A crédito' })
      return all
    },
    totalAbonadoUSD() {
      return this.pagos.filter(p => p.moneda_pago === 'USD').reduce((s, p) => s + p.monto_original, 0)
    },
    totalAbonadoBs() {
      return this.pagos.filter(p => p.moneda_pago === 'Bs').reduce((s, p) => s + p.monto_original, 0)
    },
    totalUSD() {
      const descuentoUSD = this.monedaVenta === 'USD'
        ? Number(this.descuentoGlobal || 0)
        : (this.tasaBcv ? Number(this.descuentoGlobal || 0) / this.tasaBcv : 0)
      return Math.max(this.subtotalUSD - descuentoUSD, 0)
    },
    totalBs() {
      return this.tasaBcv ? this.totalUSD * this.tasaBcv : 0
    },
    pagadoUSD() {
      return this.pagos.reduce((s, p) => {
        if (p.moneda_pago === 'USD') return s + p.monto_original
        return s + (this.tasaBcv ? p.monto_original / this.tasaBcv : 0)
      }, 0)
    },
    pagadoBs() {
      return this.pagos.reduce((s, p) => {
        if (p.moneda_pago === 'Bs') return s + p.monto_original
        return s + p.monto_original * (this.tasaBcv || 1)
      }, 0)
    },
    saldoPendienteUSD() {
      return Math.max(this.totalUSD - this.pagadoUSD, 0)
    },
    saldoPendienteBs() {
      return Math.max(this.totalBs - this.pagadoBs, 0)
    },
  },
  watch: {
    modoCobro() {
      if (!this.metodosDisponibles.some(m => m.value === this.nuevoMetodo)) {
        this.nuevoMetodo = this.metodosDisponibles[0]?.value || 'efectivo_usd'
        this.onCambioMetodo()
      }
    },
    busqueda() {
      this.indiceResaltado = -1
      clearTimeout(this._busquedaTimer)
      this._busquedaTimer = setTimeout(() => this.cargarProductos(), 400)
    },
  },
  async mounted() {
    await Promise.all([
      this.cargarProductos(),
      this.cargarTasa(),
      this.cargarCuentasPorMetodo(),
      this.cargarDepartamentos(),
      this.cargarCategorias(),
      this.cargarProveedores(),
      this.cargarMasVendidos(),
    ])
    this.cargarUltimosVendidos()
  },
  methods: {
    async cargarProductos() {
      const params = { limit: 100 }
      if (this.busqueda)          params.busqueda       = this.busqueda
      if (this.filtroDepartamento) params.departamento_id = this.filtroDepartamento
      if (this.filtroCategoria)   params.categoria_id   = this.filtroCategoria
      if (this.filtroProveedor)   params.proveedor_id   = this.filtroProveedor
      const r = await axios.get('/productos/', { params })
      this.productos = Array.isArray(r.data) ? r.data : (r.data.productos || [])
    },
    async cargarCuentasPorMetodo() {
      try {
        const r = await axios.get('/bancos/metodos-pago/cuentas')
        this.cuentasPorMetodo = r.data
      } catch { /* módulo bancario no configurado */ }
    },
    async cargarTasa() {
      const r = await axios.get('/tasa/')
      this.tasaBcv     = r.data.tasa
      this.tasaBinance = r.data.tasa_binance
      this.factor      = r.data.factor || 1
    },

    precioBase(p)     { return Number(p.costo_usd || 0) * (1 + Number(p.margen || 0)) },
    precioRef(p)      { return this.precioBase(p) * this.factor },
    precioBs(p)       { return this.precioBase(p) * (this.tasaBinance || 0) },

    variantePrecioBase(v) {
      const costo = v.precio_override_usd ?? (this.productoVariantes?.costo_usd || 0)
      return Number(costo) * (1 + Number(this.productoVariantes?.margen || 0))
    },
    variantePrecioRef(v)  { return this.variantePrecioBase(v) * this.factor },
    variantePrecioBs(v)   { return this.variantePrecioBase(v) * (this.tasaBinance || 0) },
    precioParaTier(p) { return this.tipoPrecio === 'base' ? this.precioBase(p) : this.precioRef(p) },

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
    async agregar(p) {
      this.cargandoVariantes = true
      try {
        const res = await axios.get(`/productos/${p.id}/variantes`)
        const activas = res.data.filter(v => v.activo && v.stock > 0)
        if (activas.length > 0) {
          this.productoVariantes = p
          this.variantes         = activas
          this.modalVariantes    = true
          return
        }
      } catch { /* si falla, agregar normal */ }
      finally { this.cargandoVariantes = false }
      this._agregarDirecto(p)
    },

    _agregarDirecto(p, variante = null) {
      const key    = variante ? `${p.id}-${variante.id}` : String(p.id)
      const existe = this.carrito.find(i => i._key === key)
      if (existe) { existe.cantidad++; return }

      const costoBase   = variante?.precio_override_usd ?? p.costo_usd
      const productoMod = { ...p, costo_usd: costoBase }
      const precio      = this.precioParaTier(productoMod)

      this.carrito.push({
        ...p,
        _key:            key,
        variante_id:     variante?.id     || null,
        variante_label:  variante ? `${variante.clase}${variante.color ? ' · ' + variante.color : ''}` : null,
        variante_codigo: variante?.codigo || null,
        stock:           variante?.stock  ?? p.stock,
        costo_usd:       costoBase,
        cantidad:        1,
        precio_original: precio,
        precio_unitario: precio,
      })
    },

    seleccionarVariante(variante) {
      this._agregarDirecto(this.productoVariantes, variante)
      this.modalVariantes    = false
      this.productoVariantes = null
      this.variantes         = []
      this.$refs.inputBuscador?.focus()
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

      if (this.nuevoMetodo === 'credito') {
        if (!this.clienteSeleccionado || !this.clienteSeleccionado.tiene_credito) {
          this.error = 'El cliente no tiene crédito habilitado'; return
        }
        const equivalente = this.monedaVenta === 'USD'
          ? monto
          : (this.tasaBcv ? Number((monto * this.tasaBcv).toFixed(2)) : monto)
        if (equivalente > this.saldoPendiente + TOLERANCIA) {
          this.error = `El crédito excede el saldo pendiente (${this.formatMonto(this.saldoPendiente, this.monedaVenta)})`
          return
        }
        const saldoUSD = Number(this.clienteSeleccionado.saldo_credito || 0)
        if (monto > saldoUSD + TOLERANCIA) {
          this.error = `Crédito insuficiente. Saldo disponible: $${saldoUSD.toFixed(2)}`
          return
        }
        this.error = ''
        this.pagos.push({
          metodo: 'credito', moneda_pago: 'USD',
          monto_original: monto, monto_equivalente: equivalente,
          referencia: '', cuenta_destino_id: null, cuenta_nombre: null,
        })
        this.nuevoMonto = ''; this.nuevoEquivalente = null
        return
      }

      const monedaPago  = this.nuevoMonedaPago
      const equivalente = this.calcularEquivalente(monto, monedaPago)
      if (equivalente === null) {
        this.error = 'No se puede calcular el equivalente. Verifica la tasa.'; return
      }

      const esEfectivo = ['efectivo_usd', 'efectivo_bs'].includes(this.nuevoMetodo)
      if (!esEfectivo && equivalente > this.saldoPendiente + TOLERANCIA) {
        this.error = `El pago (${this.formatMonto(equivalente, this.monedaVenta)}) excede el saldo (${this.formatMonto(this.saldoPendiente, this.monedaVenta)}). Solo efectivo puede tener exceso.`
        return
      }

      const cuentas = this.cuentasDelMetodo
      if (cuentas.length > 1 && !this.nuevaCuentaId) {
        this.error = `Debes seleccionar la cuenta destino para ${this.nuevoMetodo}`; return
      }
      const cuentaId     = this.nuevaCuentaId || (cuentas.length === 1 ? cuentas[0].id : null)
      const cuentaNombre = cuentas.find(c => c.id === cuentaId)?.nombre || null

      this.error = ''
      this.pagos.push({
        metodo: this.nuevoMetodo, moneda_pago: monedaPago,
        monto_original: monto, monto_equivalente: equivalente,
        referencia: this.nuevaReferencia,
        cuenta_destino_id: cuentaId, cuenta_nombre: cuentaNombre,
      })
      this.nuevoMonto = ''; this.nuevoEquivalente = null; this.nuevaReferencia = ''
    },
    quitarPago(i) { this.pagos.splice(i, 1) },

    buscarCliente() {
      clearTimeout(this.clienteTimer)
      if (this.clienteBusqueda.length < 2) { this.clienteResultados = []; return }
      this.clienteTimer = setTimeout(async () => {
        try {
          const res = await axios.get('/clientes/buscar-rapido', { params: { q: this.clienteBusqueda } })
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
      if (!this.nuevoCliente.nombre.trim()) { this.errorCliente = 'El nombre es requerido'; return }
      if (!this.nuevoCliente.telefono.trim()) { this.errorCliente = 'El teléfono es requerido'; return }
      this.guardandoCliente = true; this.errorCliente = ''; this.telefonoDuplicado = null
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
        this.resultadosClientes = []; return
      }
      this.busquedaTabTimer = setTimeout(async () => {
        try {
          const res = await axios.get('/clientes/buscar-rapido', { params: { q: this.busquedaClientes } })
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

    abrirModalCobro() {
      this.modoCobro = this.monedaVenta === 'Bs' ? 'Bs' : 'USD'
      this.modalCobro = true
    },

    onGarantiaConfirmada(datos) {
      this.garantiasPendientes = datos
      this.modalGarantia = false
      this.cobrar(this._accionCobro || 'solo')
    },
    async cobrar(accion = 'solo') {
      this.error = ''
      if (!this.pagoCompleto)       { this.error = 'El cobro no cubre el total'; return }
      if (this.requiereAutorizacion && !this.autorizacionClave)
                                    { this.error = 'Ingresa la clave de autorización'; return }
      if (!this.tasaBcv)            { this.error = 'No hay tasa definida. Ve a Tasa BCV.'; return }

      // ── Pre-check garantías ─────────────────────────────────────────────────
      const itemsConGarantia = this.carrito.filter(
        item => item.requiere_serial || item.garantia
      )
      if (itemsConGarantia.length > 0 && this.garantiasPendientes.length === 0) {
        this.itemsGarantia = itemsConGarantia.map(item => ({
          id:            item.id,
          nombre:        item.nombre,
          variante_id:   item.variante_id || null,
          variante_label:item.variante_label || null,
          requiere_serial: !!item.requiere_serial,
          garantia:      item.garantia || null,
        }))
        this._accionCobro = accion
        this.modalGarantia = true
        return
      }

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
            variante_id:     item.variante_id ? Number(item.variante_id) : null,
            cantidad:        Number(item.cantidad),
            precio_unitario: Number(item.precio_unitario),
          })),
          pagos: this.pagos.map(p => ({
            metodo:            p.metodo,
            monto:             p.monto_original,
            referencia:        p.referencia || '',
            cuenta_destino_id: p.cuenta_destino_id || null,
          })),
          garantias: this.garantiasPendientes,
        }

        const res = await axios.post('/ventas/', payload)
        this.ultimaVentaId = res.data.venta_id
        this.exitoso       = true
        this.modalCobro    = false

        const snapshotProductos = this.carrito.map(item => ({
          id:              item.id,
          nombre:          item.nombre,
          variante_label:  item.variante_label  || null,
          variante_codigo: item.variante_codigo || null,
          cantidad:        Number(item.cantidad),
          precio_unitario: Number(item.precio_unitario),
        }))
        // Enriquecer garantías con condiciones de la plantilla (disponibles en el carrito)
        const garantiaMap = {}
        for (const item of this.carrito) {
          if (item.garantia) garantiaMap[item.id] = item.garantia
        }
        const snapshotGarantias = this.garantiasPendientes.map(g => ({
          producto_id:          g.producto_id,
          serial:               g.serial,
          modelo:               g.modelo,
          meses_garantia:       garantiaMap[g.producto_id]?.meses       || null,
          condiciones_snapshot: garantiaMap[g.producto_id]?.condiciones || null,
          nombre_plantilla:     garantiaMap[g.producto_id]?.nombre      || null,
        }))

        const snapshotCliente = this.clienteSeleccionado
        const snapshotTasaBcv = this.tasaBcv
        const snapshotTotalBs = this.subtotalUSD * (this.tasaBcv || 1)
        const snapshotVentaId = res.data.venta_id

        this.guardarUltimosVendidos(this.carrito)
        this.carrito = []; this.pagos = []; this.descuentoGlobal = 0
        this.autorizacionClave = ''; this.observacion = ''
        this.clienteSeleccionado = null; this.nuevoMonto = ''
        this.garantiasPendientes = []; this.itemsGarantia = []

        setTimeout(() => { this.exitoso = false }, 5000)
        await this.cargarProductos()

        if (accion === 'whatsapp') {
          const nombre  = snapshotCliente ? snapshotCliente.nombre : 'Consumidor Final'
          const fecha   = new Date().toLocaleDateString('es-VE')
          const mensaje = encodeURIComponent(
            `Nota de entrega FERRETERÍA FERRE-UTIL — Cliente: ${nombre} — Total: Bs ${Number(snapshotTotalBs).toFixed(2)} — Fecha: ${fecha}`
          )
          let num = snapshotCliente ? String(snapshotCliente.telefono || '').replace(/\D/g, '') : ''
          if (!num) {
            const ingresado = prompt('Cliente sin teléfono registrado.\nIngresa el número (ej: 584121234567):')
            if (ingresado) {
              num = String(ingresado).replace(/\D/g, '')
              if (snapshotCliente?.id) {
                try { await axios.put(`/clientes/${snapshotCliente.id}`, { telefono: num }) } catch {}
              }
            }
          }
          if (num) window.open(`https://wa.me/${num}?text=${mensaje}`, '_blank')

        } else if (accion === 'imprimir') {
          this.notaImpresion = {
            ventaId:   snapshotVentaId,
            clienteNombre: snapshotCliente ? snapshotCliente.nombre : 'Consumidor Final',
            fecha:     new Date().toLocaleDateString('es-VE'),
            productos: snapshotProductos,
            garantias: snapshotGarantias,
            totalBs:   Number(snapshotTotalBs),
            tasaBcv:   Number(snapshotTasaBcv),
          }
          await this.$nextTick()
          window.print()
          this.notaImpresion = null
        }

      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al registrar la venta'
      } finally {
        this.cargando = false
      }
    },

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
      this.ubicPop = p; this.ubicaciones = []; this.ubicPopCargando = true
      try {
        const res = await axios.get(`/ubicaciones/producto/${p.id}`)
        this.ubicaciones = res.data
      } catch { /* sin ubicaciones */ }
      this.ubicPopCargando = false
    },

    moverAbajo() {
      const max = this.productosFiltrados.length - 1
      if (max < 0) return
      this.indiceResaltado = this.indiceResaltado < max ? this.indiceResaltado + 1 : 0
      this._scrollResaltado()
    },
    moverArriba() {
      const max = this.productosFiltrados.length - 1
      if (max < 0) return
      this.indiceResaltado = this.indiceResaltado > 0 ? this.indiceResaltado - 1 : max
      this._scrollResaltado()
    },
    seleccionarResaltado() {
      if (this.indiceResaltado >= 0 && this.indiceResaltado < this.productosFiltrados.length) {
        const p = this.productosFiltrados[this.indiceResaltado]
        const q = this.busqueda.trim().toLowerCase()
        // Código exacto de variante → agregar esa variante directamente sin abrir modal
        if (q && p.variantes_resumen) {
          const varMatch = p.variantes_resumen.find(v => v.codigo && v.codigo.toLowerCase() === q)
          if (varMatch) {
            this._agregarDirecto(p, varMatch)
            this.busqueda        = ''
            this.indiceResaltado = -1
            this.$refs.inputBuscador?.focus()
            return
          }
        }
        this.agregar(p)
        this.indiceResaltado = -1
      }
    },
    cerrarDropdown() {
      this.indiceResaltado = -1
      this.busqueda        = ''
    },
    _scrollResaltado() {
      this.$nextTick(() => {
        const cont = this.$refs.tbodyCatalogo
        if (!cont) return
        const fila = cont.children[this.indiceResaltado]
        if (fila) fila.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      })
    },

    abrirModalPresupuesto() {
      this.presupuestoNombre = ''
      this.presupuestoObs = ''
      this.presupuestoFechaValidez = ''
      this.presupuestoError = ''
      this.presupuestoExito = null
      this.modalPresupuesto = true
    },
    async guardarPresupuesto() {
      if (!this.presupuestoNombre.trim()) {
        this.presupuestoError = 'El nombre/referencia es requerido'
        return
      }
      this.presupuestoGuardando = true
      this.presupuestoError = ''
      try {
        const obs = [this.presupuestoNombre.trim(), this.presupuestoObs.trim()].filter(Boolean).join(' — ')
        const payload = {
          cliente_id:       this.clienteSeleccionado?.id || null,
          cliente_nombre:   this.clienteSeleccionado?.nombre || 'Consumidor Final',
          cliente_telefono: this.clienteSeleccionado?.telefono || null,
          usuario:          this.usuario.usuario || 'cajero',
          moneda:           this.monedaVenta,
          descuento:        Number(this.descuentoGlobal || 0),
          observacion:      obs,
          productos: this.carrito.map(item => ({
            producto_id:     Number(item.id),
            variante_id:     item.variante_id ? Number(item.variante_id) : null,
            nombre_producto: item.nombre,
            cantidad:        Number(item.cantidad),
            precio_unitario: Number(item.precio_unitario),
          })),
        }
        if (this.presupuestoFechaValidez) payload.fecha_vencimiento = this.presupuestoFechaValidez
        const res = await axios.post('/presupuestos/', payload)
        this.presupuestoExito = res.data
      } catch (e) {
        this.presupuestoError = e?.response?.data?.detail || 'Error al guardar el presupuesto'
      } finally {
        this.presupuestoGuardando = false
      }
    },
    continuarVenta() {
      this.modalPresupuesto = false
      this.presupuestoExito = null
      this.presupuestoNombre = ''
      this.presupuestoObs = ''
      this.presupuestoFechaValidez = ''
    },
    limpiarCarritoDesdePresupuesto() {
      this.carrito = []
      this.descuentoGlobal = 0
      this.continuarVenta()
    },
    verPresupuesto() {
      this.$router.push('/presupuestos')
      this.continuarVenta()
    },

    async cargarDepartamentos() {
      try {
        const r = await axios.get('/productos/departamentos')
        this.departamentos = r.data
      } catch { this.departamentos = [] }
    },
    async cargarCategorias() {
      try {
        const r = await axios.get('/productos/categorias')
        this.categorias = r.data
      } catch { this.categorias = [] }
    },
    async cargarProveedores() {
      try {
        const r = await axios.get('/compras/proveedores/')
        this.proveedores = r.data
      } catch { this.proveedores = [] }
    },
    async cargarMasVendidos() {
      try {
        const r = await axios.get('/ventas/productos-frecuentes', { params: { n: 8 } })
        this.masVendidos = r.data
      } catch { this.masVendidos = [] }
    },
    cargarUltimosVendidos() {
      try {
        const raw = localStorage.getItem('ultimos_vendidos')
        this.ultimosVendidos = raw ? JSON.parse(raw) : []
      } catch { this.ultimosVendidos = [] }
    },
    npGarantia(productoId) {
      if (!this.notaImpresion?.garantias?.length) return null
      return this.notaImpresion.garantias.find(g => g.producto_id === productoId) || null
    },
    guardarUltimosVendidos(carritoSnapshot) {
      const nuevos  = carritoSnapshot.map(i => ({ id: i.id, nombre: i.nombre }))
      const previos = this.ultimosVendidos.filter(p => !nuevos.some(n => n.id === p.id))
      const lista   = [...nuevos, ...previos].slice(0, 10)
      this.ultimosVendidos = lista
      localStorage.setItem('ultimos_vendidos', JSON.stringify(lista))
    },
    async agregarPorId(id) {
      const p = this.productos.find(x => x.id === id)
      if (p) { this.agregar(p); return }
      try {
        const r = await axios.get(`/productos/${id}`)
        if (r.data) this.agregar(r.data)
      } catch { /* producto no disponible */ }
    },
    limpiarFiltros() {
      this.filtroDepartamento = null
      this.filtroCategoria    = null
      this.filtroProveedor    = null
      this.cargarProductos()
    },

    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    },
  }
}
</script>

<style scoped>
/* ── Top bar ── */
.top-meta { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
.selector-group { display: flex; align-items: center; gap: 0.4rem; }
.selector-label { color: #555555; font-size: 0.88rem; font-weight: 600; }
.btn-sel { padding: 0.3rem 0.8rem; background: #FFFFFF; color: var(--texto-sec); border: 1px solid var(--borde); border-radius: 6px; cursor: pointer; font-size: 0.88rem; }
.btn-sel.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }
.btn-base { border-color: #7b2cbf; }
.btn-base.activo-base { background: #7b2cbf; color: white; border-color: #7b2cbf; }
.tasas-info { display: flex; gap: 1rem; font-size: 0.85rem; color: var(--texto-sec); }
.tasas-info strong { color: var(--texto-principal); }
.tasa-oculta { cursor: default; position: relative; }
.tasa-oculta .tasa-valor { display: none; }
.tasa-oculta:hover .tasa-letra { display: none; }
.tasa-oculta:hover .tasa-valor { display: inline; }
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
.ck-credito { font-size: 0.78rem; font-weight: 700; padding: 0.15rem 0.6rem; border-radius: 12px; }
.ck-credito-ok      { background: #16A34A1A; color: #16A34A; }
.ck-credito-agotado { background: #DC26261A; color: #DC2626; }

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

/* ── Grid 50/50 ── */
.venta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  align-items: start;
}

/* ── Catálogo (col izq) ── */
.catalogo { background: #FFFFFF; border-radius: 12px; padding: 0.85rem; border: 1px solid var(--borde); min-width: 0; }
.buscador { width: 100%; padding: 0.55rem 0.9rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 8px; margin-bottom: 0.5rem; box-sizing: border-box; font-size: 0.9rem; }

/* Lista compacta de productos */
.prod-list {
  max-height: calc(100vh - 320px);
  min-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--borde);
  border-radius: 8px;
}
.prod-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.3rem 0.6rem;
  cursor: pointer;
  border-bottom: 1px solid var(--borde-suave);
  font-size: 0.82rem;
  position: relative;
  transition: background 0.08s;
  width: 100%;
  box-sizing: border-box;
}
.prod-item:last-child { border-bottom: none; }
.prod-item:hover, .prod-item-resaltado { background: #FFCC00; }
.prod-item:hover .pi-nombre,
.prod-item:hover .pi-bs,
.prod-item:hover .pi-ref,
.prod-item:hover .pi-stock,
.prod-item-resaltado .pi-nombre,
.prod-item-resaltado .pi-bs,
.prod-item-resaltado .pi-ref,
.prod-item-resaltado .pi-stock { color: #1A1A1A !important; }
.prod-item:hover .cod-tag-v,
.prod-item-resaltado .cod-tag-v { background: #1A1A1A; color: #FFCC00; }
.prod-item:hover .pi-base,
.prod-item-resaltado .pi-base { display: inline; }
.prod-item:hover .pi-precios,
.prod-item-resaltado .pi-precios { color: #1A1A1A; }

.pi-nombre {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.pi-nombre-texto {
  font-weight: 600;
  color: var(--texto-principal);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pi-vcods {
  display: flex;
  flex-wrap: wrap;
  gap: 0.2rem;
}
.pi-vcod {
  font-size: 0.68rem;
  font-weight: 700;
  color: #5B21B6;
  background: #EDE9FE;
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
  white-space: nowrap;
}
.prod-item:hover .pi-nombre-texto,
.prod-item-resaltado .pi-nombre-texto { color: #1A1A1A; }
.prod-item:hover .pi-vcod,
.prod-item-resaltado .pi-vcod { background: #7c3aed; color: #fff; }
.pi-vcod-mas {
  font-size: 0.65rem; font-weight: 700; color: #6B7280;
  background: #F3F4F6; border: 1px solid #D1D5DB;
  padding: 0.05rem 0.3rem; border-radius: 3px; white-space: nowrap;
}
.prod-item:hover .pi-vcod-mas,
.prod-item-resaltado .pi-vcod-mas { background: #D1D5DB; color: #1A1A1A; }
.pi-precios {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-shrink: 0;
}
.pi-bs    { color: #B08800; font-size: 0.85rem; font-weight: 700; min-width: 72px; text-align: right; }
.pi-ref   { color: #16A34A; font-size: 0.85rem; font-weight: 700; min-width: 60px; text-align: right; }
.pi-stock { color: var(--texto-muted); font-size: 0.82rem; white-space: nowrap; background: var(--borde-suave); padding: 0.1rem 0.4rem; border-radius: 4px; }
.pi-base   { color: var(--texto-muted); font-size: 0.75rem; display: none; white-space: nowrap; }

.prod-sin-res { text-align: center; color: var(--texto-muted); padding: 1.5rem 0; font-size: 0.88rem; }
.txt-dim { color: var(--texto-muted); }
.sin-datos { text-align: center; color: var(--texto-muted); padding: 1.5rem 0; }

/* ── Carrito (col der) ── */
.carrito-col {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  height: calc(100vh - 280px);
  position: sticky;
  top: 1rem;
  min-width: 0;
}

.carrito-box {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 0.85rem 1rem;
  border: 1px solid var(--borde);
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}
.carrito-box h2 { color: var(--texto-principal); margin: 0 0 0.65rem; font-size: 0.95rem; font-weight: 700; position: sticky; top: 0; background: #FFFFFF; padding-bottom: 0.4rem; border-bottom: 1px solid var(--borde-suave); }
.vacio { color: var(--texto-muted); text-align: center; padding: 1.5rem 0; font-size: 0.88rem; }

/* Item row compacto */
.item-row { display: flex; align-items: center; gap: 0.35rem; padding: 0.35rem 0; border-bottom: 1px solid var(--borde-suave); font-size: 0.82rem; }
.item-row:last-child { border-bottom: none; }
.btn-cnt { background: var(--borde-suave); color: var(--texto-principal); border: 1px solid var(--borde); width: 22px; height: 22px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; flex-shrink: 0; line-height: 1; }
.btn-cnt:hover { background: var(--borde); }
.item-qty { min-width: 18px; text-align: center; font-weight: 700; color: var(--texto-principal); font-size: 0.85rem; }
.item-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.05rem; }
.item-nombre { font-weight: 600; color: var(--texto-principal); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.82rem; }
.item-ref { color: #16A34A; font-size: 0.75rem; font-weight: 600; }
.item-sub { color: var(--texto-sec); font-size: 0.78rem; white-space: nowrap; font-weight: 600; }
.btn-quitar { background: transparent; color: var(--texto-muted); border: none; width: 20px; height: 20px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; flex-shrink: 0; }
.btn-quitar:hover { background: #DC26261A; color: #DC2626; }

/* Botones inferiores fijos */
.botones-carrito { display: flex; flex-direction: column; gap: 0.4rem; flex-shrink: 0; }

.totales-box { border-top: 1px solid var(--borde); margin-top: 0.75rem; padding-top: 0.75rem; }
.fila-total { display: flex; justify-content: space-between; padding: 0.2rem 0; color: var(--texto-sec); font-size: 0.9rem; }
.fila-grande { color: var(--texto-principal); font-size: 1.1rem; font-weight: 700; margin-top: 0.4rem; }
.txt-desc { color: #996600; }
.txt-gris { color: var(--texto-muted); font-size: 0.82rem; }

.descuento-global { margin: 0.5rem 0; }
.descuento-global label { color: var(--texto-sec); font-size: 0.82rem; display: block; margin-bottom: 0.25rem; font-weight: 600; }
.descuento-global input { width: 100%; padding: 0.4rem 0.6rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 6px; box-sizing: border-box; }

/* Botones carrito inferiores */
.btn-abrir-cobro {
  width: 100%;
  padding: 0.75rem;
  background: #1A1A1A;
  color: #FFCC00;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  transition: background 0.15s;
}
.btn-abrir-cobro:hover { background: #333333; }
.btn-guardar-presupuesto {
  width: 100%;
  padding: 0.6rem;
  background: #FFFFFF;
  color: #1A1A1A;
  border: 1px solid var(--borde);
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 600;
  transition: all 0.15s;
}
.btn-guardar-presupuesto:hover { border-color: #1A1A1A; background: var(--fondo-tabla-alt); }

/* Éxito post-venta */
.venta-exito-row { display: flex; align-items: center; justify-content: center; gap: 1rem; flex-wrap: wrap; padding: 0.75rem; background: #F0FDF4; border: 1px solid #16A34A33; border-radius: 8px; }
.msg-exito { color: #16A34A; font-weight: 600; margin: 0; font-size: 0.9rem; }
.btn-pdf { background: var(--success); color: white; border: none; padding: 0.45rem 1.1rem; border-radius: 8px; cursor: pointer; font-size: 0.88rem; }

/* ── Modal Cobro ── */
.cobro-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.cobro-modal {
  background: #FAFAF7;
  border-radius: 14px;
  width: 100%;
  max-width: 500px;
  max-height: 92vh;
  overflow-y: auto;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.22);
  display: flex;
  flex-direction: column;
}
.cobro-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem 0.85rem;
  border-bottom: 1px solid var(--borde);
  background: #FFFFFF;
  border-radius: 14px 14px 0 0;
  position: sticky;
  top: 0;
  z-index: 1;
}
.cobro-modal-header h3 { margin: 0; font-size: 1.05rem; font-weight: 700; color: #1A1A1A; }
.cobro-modal-cerrar { background: transparent; border: none; font-size: 1.1rem; cursor: pointer; color: var(--texto-muted); padding: 0.2rem 0.45rem; border-radius: 4px; }
.cobro-modal-cerrar:hover { background: #F3F4F6; color: #1A1A1A; }

.cobro-modal-resumen {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 1.25rem;
  background: #1A1A1A;
  color: #FFCC00;
  font-size: 0.95rem;
  font-weight: 600;
}
.cobro-modal-resumen strong { font-size: 1.1rem; }

.cobro-modal-body { padding: 0.75rem 1.25rem; flex: 1; }

.cobro-modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.85rem 1.25rem;
  border-top: 1px solid var(--borde);
  background: #FFFFFF;
  border-radius: 0 0 14px 14px;
  position: sticky;
  bottom: 0;
}
.btn-cancelar-cobro {
  padding: 0.6rem 1rem;
  background: transparent;
  border: 1px solid var(--borde);
  color: var(--texto-sec);
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 600;
}
.btn-cancelar-cobro:hover { border-color: #DC2626; color: #DC2626; }

/* Formulario de pago en modal */
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
.txt-verde   { color: #16A34A; font-weight: 600; }
.txt-rojo    { color: #DC2626; font-weight: 600; }
.txt-amarillo { color: #996600; font-weight: 600; }

.autorizacion-box { background: #FFF7ED; border: 1px solid #F59E0B; border-radius: 8px; padding: 0.75rem; margin: 0.75rem 0; }
.aut-titulo { color: #92400E; font-weight: 700; margin: 0 0 0.5rem; font-size: 0.9rem; }
.aut-motivos { color: #78350F; font-size: 0.85rem; margin: 0 0 0.5rem; padding-left: 1rem; }
.autorizacion-box input { width: 100%; padding: 0.5rem; background: #FFFFFF; border: 1px solid #F59E0B; color: var(--texto-principal); border-radius: 6px; box-sizing: border-box; }

.field { margin: 0.5rem 0; }
.field label { color: var(--texto-sec); font-size: 0.85rem; display: block; margin-bottom: 0.25rem; font-weight: 600; }
.field input { width: 100%; padding: 0.5rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 6px; box-sizing: border-box; }

.btn-cobrar-grupo { display: flex; gap: 0.5rem; }
.btn-cobrar-accion { flex: 1; padding: 0.75rem; background: #1A1A1A; color: #FFCC00; border: none; border-radius: 8px; cursor: pointer; font-size: 1.05rem; font-weight: 700; }
.btn-cobrar-accion:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-cobrar-accion:not(:disabled):hover { background: #333; }

.msg-error { color: var(--danger); margin-top: 0.5rem; font-size: 0.9rem; }
.sel-cuenta { padding: 0.4rem 0.6rem; background: #FFFFFF; border: 1px solid var(--borde); color: var(--texto-principal); border-radius: 6px; font-size: 0.82rem; min-width: 160px; }
.cuenta-unica { color: #16A34A; font-size: 0.82rem; align-self: center; white-space: nowrap; font-weight: 600; }

/* ── Código tag ── */
.cod-tag-v { font-size: 0.72rem; font-weight: 700; color: #996600; background: #FFCC0033; padding: 0.1rem 0.35rem; border-radius: 3px; margin-left: 0.25rem; }

/* ── Ubicaciones popup ── */
.btn-ubicar-v { background: transparent; border: none; cursor: pointer; font-size: 0.8rem; padding: 0 0.1rem; opacity: 0.5; flex-shrink: 0; }
.btn-ubicar-v:hover { opacity: 1; }

.ubic-pop-overlay { position: fixed; inset: 0; z-index: 200; display: flex; align-items: center; justify-content: center; }
.ubic-pop { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 12px; box-shadow: 0 8px 32px #0000001A; width: 420px; max-width: 95vw; overflow: hidden; }
.ubic-pop-header { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; border-bottom: 1px solid var(--borde); font-weight: 600; font-size: 0.9rem; color: var(--texto-principal); }
.btn-cerrar-modal { background: transparent; border: none; cursor: pointer; color: var(--texto-muted); font-size: 1rem; }
.btn-cerrar-modal:hover { color: var(--texto-principal); }
.ubic-pop-cargando { padding: 1rem; color: var(--texto-muted); font-size: 0.88rem; }
.ubic-pop-vacio    { padding: 1rem; color: var(--texto-muted); font-size: 0.88rem; margin: 0; }
.ubic-pop-tabla    { width: 100%; border-collapse: collapse; }
.ubic-pop-tabla th { padding: 0.45rem 0.75rem; background: var(--fondo-sidebar); color: var(--texto-muted); font-size: 0.78rem; text-align: left; font-weight: 700; }
.ubic-pop-tabla td { padding: 0.45rem 0.75rem; border-top: 1px solid var(--borde-suave); font-size: 0.88rem; color: var(--texto-principal); }

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

/* ── Nota de entrega (print) ── */
#nota-print { display: none; font-family: Arial, sans-serif; padding: 20px; background: #fff; color: #000; width: 520px; }
.np-encabezado { text-align: center; margin-bottom: 16px; border-bottom: 2px solid #000; padding-bottom: 10px; }
.np-empresa    { font-size: 1.3rem; font-weight: 900; margin: 0; letter-spacing: 0.05em; }
.np-subtitulo  { font-size: 0.9rem; margin: 4px 0 0; color: #444; }
.np-datos      { margin-bottom: 14px; font-size: 0.88rem; line-height: 1.7; }
.np-datos p    { margin: 0; }
.np-tabla { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-bottom: 14px; }
.np-tabla th { background: #1A1A1A; color: #FFCC00; padding: 6px 8px; text-align: left; }
.np-th-num    { text-align: right !important; }
.np-tabla td  { padding: 5px 8px; border-bottom: 1px solid #ddd; }
.np-td-num    { text-align: right; }
.np-tabla tbody tr:nth-child(even) { background: #F5F5F0; }
.np-total    { text-align: right; font-size: 1rem; font-weight: 900; border-top: 2px solid #000; padding-top: 8px; }
.np-variante { font-size: 0.82rem; color: #444; font-style: italic; }
.np-cod      { font-size: 0.78rem; color: #666; font-weight: 700; }

.np-fila-garantia td   { padding: 3px 8px 8px; border-bottom: 1px solid #ddd; background: #FAFAF5; }
.np-garantia-bloque    { font-size: 0.78rem; color: #333; }
.np-garantia-cond      { margin-top: 3px; white-space: pre-wrap; color: #555; font-size: 0.74rem; line-height: 1.45; }

.np-firmas       { display: flex; gap: 3rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ccc; }
.np-firma-bloque { flex: 1; text-align: center; }
.np-firma-linea  { border-top: 1px solid #000; margin-bottom: 4px; margin-top: 2.5rem; }
.np-firma-label  { font-size: 0.8rem; color: #444; }

@media print {
  body > * { display: none !important; }
  #app      { display: none !important; }
  #nota-print {
    display: block !important;
    position: fixed !important;
    inset: 0 !important;
    width: 100% !important;
    padding: 20px !important;
    z-index: 99999 !important;
  }
}

/* ── Presupuesto modal extras ── */
.input-readonly { background: var(--fondo-tabla-alt) !important; color: var(--texto-sec) !important; cursor: default; }
.pres-exito-msg { color: #16A34A; font-weight: 700; font-size: 1rem; margin: 0 0 1.25rem; text-align: center; }
.pres-opciones { display: flex; flex-direction: column; gap: 0.5rem; }
.pres-opciones .btn-primary { padding: 0.75rem; font-size: 0.95rem; }
.pres-opciones .btn-sec { padding: 0.6rem; font-size: 0.9rem; text-align: center; }

/* ── Responsive monitores medianos ── */
@media (max-width: 1300px) {
  .pi-bs  { min-width: 62px; font-size: 0.8rem; }
  .pi-ref { min-width: 52px; font-size: 0.8rem; }
  .pi-precios { gap: 0.4rem; }
  .pi-stock { font-size: 0.78rem; }
}
@media (max-width: 1100px) {
  .venta-grid { grid-template-columns: 58fr 42fr; }
  .pi-base { display: none !important; }
}

/* ── Responsive móvil ── */
@media (max-width: 768px) {
  .venta-grid { grid-template-columns: 1fr; }
  .prod-list  { max-height: 40vh; }
  .carrito-col { height: auto; position: static; }
  .carrito-box { flex: none; max-height: 50vh; }
}

.modo-cobro-selector { display: flex; gap: 0.5rem; padding: 0.75rem 1.25rem; background: var(--borde-suave); border-bottom: 1px solid var(--borde); }
.btn-modo { flex: 1; padding: 0.5rem; background: #FFFFFF; border: 1px solid var(--borde); border-radius: 8px; cursor: pointer; font-size: 0.88rem; font-weight: 600; color: var(--texto-sec); transition: all 0.15s; }
.btn-modo:hover { border-color: #1A1A1A; color: var(--texto-principal); }
.btn-modo.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }
.resumen-mixto { background: var(--borde-suave); border-radius: 8px; padding: 0.75rem; margin: 0.75rem 0; border: 1px solid var(--borde); display: flex; flex-direction: column; gap: 0.3rem; }
.resumen-mixto-fila { display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--texto-sec); }
.equiv-cruce { color: var(--texto-muted); font-size: 0.82rem; background: var(--borde-suave); padding: 0.1rem 0.4rem; border-radius: 4px; }

/* ── Buscador + filtros ── */
.buscador-wrap { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.5rem; }
.buscador-wrap .buscador { flex: 1; margin-bottom: 0; }
.btn-filtros-toggle { padding: 0.45rem 0.85rem; background: #FFFFFF; border: 1px solid var(--borde); color: var(--texto-sec); border-radius: 8px; cursor: pointer; font-size: 0.82rem; white-space: nowrap; flex-shrink: 0; transition: all 0.15s; }
.btn-filtros-toggle:hover, .btn-filtros-toggle.active { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }

.filtros-panel { display: flex; gap: 0.4rem; flex-wrap: wrap; align-items: center; margin-bottom: 0.5rem; padding: 0.55rem 0.65rem; background: var(--fondo-tabla-alt); border: 1px solid var(--borde); border-radius: 8px; }
.filtro-sel { flex: 1; min-width: 130px; padding: 0.4rem 0.55rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 6px; font-size: 0.82rem; }
.btn-limpiar-filtros { padding: 0.35rem 0.75rem; background: transparent; border: 1px solid #DC2626; color: #DC2626; border-radius: 6px; cursor: pointer; font-size: 0.78rem; white-space: nowrap; flex-shrink: 0; }
.btn-limpiar-filtros:hover { background: #DC26261A; }

/* ── Acceso rápido ── */
.acceso-rapido { margin-bottom: 0.5rem; display: flex; flex-direction: column; gap: 0.4rem; }
.ar-grupo { display: flex; flex-direction: column; gap: 0.25rem; }
.ar-titulo { font-size: 0.72rem; font-weight: 700; color: var(--texto-muted); text-transform: uppercase; letter-spacing: 0.05em; padding: 0 0.1rem; }
.ar-chips { display: flex; flex-wrap: wrap; gap: 0.3rem; }
.ar-chip { padding: 0.25rem 0.65rem; background: #FFCC0022; border: 1px solid #FFCC0077; color: #7A6000; border-radius: 20px; cursor: pointer; font-size: 0.78rem; font-weight: 600; transition: all 0.12s; white-space: nowrap; max-width: 180px; overflow: hidden; text-overflow: ellipsis; }
.ar-chip:hover { background: #FFCC00; color: #1A1A1A; border-color: #FFCC00; }

/* ── Variantes ── */
.variantes-lista {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.variante-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 0.9rem;
  background: #FFFFFF;
  border: 1px solid var(--borde);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.12s;
  width: 100%;
}
.variante-item:hover {
  border-color: #FFCC00;
  background: #FFFDF0;
}
.variante-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
}
.variante-clase {
  font-weight: 700;
  color: var(--texto-principal);
  font-size: 0.9rem;
}
.variante-color {
  font-size: 0.8rem;
  color: var(--texto-sec);
}
.variante-cod-tag {
  font-size: 0.72rem;
  font-weight: 700;
  color: #5B21B6;
  background: #EDE9FE;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  margin-top: 0.1rem;
}
.variante-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.15rem;
}
.variante-stock {
  font-size: 0.78rem;
  color: var(--texto-muted);
  background: var(--borde-suave);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}
.variante-bs   { color: #B08800; font-weight: 700; font-size: 0.82rem; }
.variante-ref  { color: #16A34A; font-weight: 700; font-size: 0.9rem; }
.variante-base { color: #7b2cbf; font-size: 0.75rem; font-weight: 600; display: none; }
.variante-item:hover .variante-base { display: block; }
.pi-variantes-count { color: #0369A1; font-size: 0.78rem; font-weight: 700; background: #E0F2FE; padding: 0.1rem 0.4rem; border-radius: 4px; }
.variante-tag {
  font-size: 0.72rem;
  font-weight: 700;
  color: #0369A1;
  background: #E0F2FE;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  margin-left: 0.25rem;
}
</style>