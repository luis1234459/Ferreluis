<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Reportes</h1>
      </div>

      <div class="contenido-inner">

        <!-- Tabs principales -->
        <div class="tabs-main">
          <button v-for="t in MAIN_TABS" :key="t.key"
            :class="['tab-main', tabMain === t.key ? 'activo' : '']"
            @click="cambiarTabMain(t.key)">{{ t.label }}</button>
        </div>

        <!-- Sub-tabs -->
        <div class="tabs-sub">
          <button v-for="s in subTabsActuales" :key="s.key"
            :class="['tab-sub', tabSub === s.key ? 'activo' : '']"
            @click="cambiarTabSub(s.key)">{{ s.label }}</button>
        </div>

        <!-- Barra de filtros + exportar -->
        <div class="barra-acciones">
          <div class="filtros" v-if="tieneFiltros">
            <div class="field-inline">
              <label>Desde (día)</label>
              <input
                v-model.number="desdeDia"
                type="number" min="1" max="31"
                placeholder="ej: 1"
                style="width:80px"
              />
              <small v-if="fechaDesde" class="fecha-preview">
                {{ formatFechaPreview(fechaDesde) }}
              </small>
            </div>
            <div class="field-inline">
              <label>Hasta (día)</label>
              <input
                v-model.number="hastaDia"
                type="number" min="1" max="31"
                placeholder="ej: 31"
                style="width:80px"
              />
              <small v-if="fechaHasta" class="fecha-preview">
                {{ formatFechaPreview(fechaHasta) }}
              </small>
            </div>
            <button class="btn-filtrar" @click="cargar">Filtrar</button>
            <button class="btn-rapido" @click="setHoy">Hoy</button>
            <button class="btn-rapido" @click="setAyer">Ayer</button>
            <button class="btn-rapido" @click="setHace2Dias">Hace 2 días</button>
            <button class="btn-rapido" @click="setSemana">Semana</button>
            <button class="btn-rapido" @click="setMes">Mes</button>
            <button class="btn-rapido" @click="setAnio">Año</button>
            <button class="btn-limpiar" @click="limpiarFiltros">Limpiar</button>
          </div>
          <button class="btn-exportar" @click="exportar">⬇ Exportar Excel</button>
        </div>

        <!-- Cargando -->
        <div v-if="cargando" class="msg-info">Cargando...</div>

        <!-- ══════════════════════════════════════════════════════════════════
             VENTAS
        ═══════════════════════════════════════════════════════════════════ -->

        <!-- Ventas → Resumen del día -->
        <template v-if="tabMain === 'ventas' && tabSub === 'resumen_dia' && !cargando && datos">
          <div class="kpi-row">
            <div class="kpi-card"><p class="kpi-label">Ventas del día</p><p class="kpi-valor">{{ datos.cantidad_ventas }}</p></div>
            <div class="kpi-card"><p class="kpi-label">Total USD</p><p class="kpi-valor txt-verde">${{ datos.total_usd.toFixed(2) }}</p></div>
            <div class="kpi-card"><p class="kpi-label">Total Bs</p><p class="kpi-valor">Bs. {{ datos.total_bs.toFixed(2) }}</p></div>
            <div class="kpi-card"><p class="kpi-label">Equiv. USD total</p><p class="kpi-valor txt-verde">${{ datos.total_usd_equiv.toFixed(2) }}</p></div>
          </div>

          <p class="sub-titulo" style="margin-bottom:0.75rem">Productos vendidos</p>
          <div class="tabla-container" style="margin-bottom:1.75rem">
            <table>
              <thead>
                <tr>
                  <th>Hora</th><th>Venta</th><th>Producto</th><th>Cant.</th>
                  <th>Precio unit.</th><th>Subtotal</th><th>USD</th><th>Vendedor</th>
                  <th>Costo</th><th>Margen</th><th>Ganancia</th><th>Stock</th><th>Auditoría</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(l, i) in datos.lineas_productos" :key="i"
                    :class="l.precio_libre ? 'fila-precio-libre' : ''">
                  <td class="txt-muted" style="white-space:nowrap">{{ l.hora }}</td>
                  <td class="txt-muted">#{{ l.venta_id }}</td>
                  <td @click="abrirPanelProducto(l)" class="nombre-clickeable">
                    {{ l.producto }}
                    <span v-if="l.precio_libre" class="badge-precio-libre" title="Precio libre aplicado">✏️</span>
                  </td>
                  <td>{{ l.cantidad }}</td>
                  <td>{{ l.moneda === 'USD' ? '$' : 'Bs.' }} {{ l.precio_unitario.toFixed(2) }}</td>
                  <td>
                    {{ l.moneda === 'USD' ? '$' : 'Bs.' }} {{ l.subtotal_venta.toFixed(2) }}
                    <small v-if="l.tasa_bcv" class="txt-muted">@{{ l.tasa_bcv }}</small>
                  </td>
                  <td class="txt-verde">${{ l.subtotal_usd.toFixed(2) }}</td>
                  <td class="txt-muted">{{ l.vendedor }}</td>
                  <td class="txt-muted" style="font-size:0.8rem">${{ Number(l.costo_usd || 0).toFixed(2) }}</td>
                  <td style="font-size:0.8rem">
                    <span :class="l.margen_pct >= 20 ? 'txt-verde' : l.margen_pct >= 10 ? 'txt-amarillo' : 'txt-danger'">
                      {{ l.margen_pct }}%
                    </span>
                  </td>
                  <td style="font-size:0.8rem;font-weight:600"
                    :class="l.ganancia_usd > 0 ? 'txt-verde' : 'txt-danger'">
                    ${{ Number(l.ganancia_usd || 0).toFixed(2) }}
                  </td>
                  <td>
                    <div class="semaforo-cell">
                      <span :class="'punto-' + l.semaforo"
                        :title="'Stock: ' + l.stock_actual + ' · Promedio/día: ' + l.promedio_diario + ' · Cobertura: ' + l.dias_cobertura + ' días'">
                        ●
                      </span>
                      <span class="stock-num">{{ l.stock_actual }}</span>
                      <span class="dias-cob" v-if="l.dias_cobertura < 999">{{ l.dias_cobertura }}d</span>
                    </div>
                  </td>
                  <td>
                    <span v-if="l.auditoria_pendiente" class="badge-audit-pendiente"
                      title="Faltante pendiente de autorización admin">
                      ⚠ Pendiente
                    </span>
                    <span v-else-if="l.auditado" class="badge-audit-ok"
                      :title="'Auditado: ' + (l.fecha_auditoria || '')">
                      ✓ {{ l.fecha_auditoria || 'Auditado' }}
                    </span>
                    <span v-else class="badge-audit-sin">Sin auditar</span>
                  </td>
                </tr>
                <tr v-if="!datos.lineas_productos || datos.lineas_productos.length === 0">
                  <td colspan="13" class="sin-datos">Sin ventas en el período</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="resumen-dos-col">
            <!-- Cobros por método + cuenta -->
            <div>
              <p class="sub-titulo">Cobros por método</p>
              <div v-if="datos.por_metodo_cuenta.length === 0" class="sin-datos">Sin pagos registrados</div>
              <div v-for="m in datos.por_metodo_cuenta" :key="m.metodo + '_' + m.cuenta_id" class="metodo-resumen-row">
                <div class="metodo-resumen-info">
                  <span class="metodo-resumen-label">{{ m.label }}</span>
                  <span v-if="m.cuenta_nombre" class="metodo-resumen-cuenta">{{ m.cuenta_nombre }}</span>
                </div>
                <div class="metodo-resumen-montos">
                  <span class="metodo-resumen-orig">
                    {{ m.moneda === 'USD' ? '$' : 'Bs.' }} {{ m.monto_original.toFixed(2) }}
                  </span>
                  <span v-if="m.moneda !== 'USD'" class="metodo-resumen-usd">${{ m.monto_usd.toFixed(2) }}</span>
                  <span class="metodo-resumen-cant">{{ m.cantidad }} pago{{ m.cantidad !== 1 ? 's' : '' }}</span>
                </div>
              </div>
            </div>

            <!-- Por vendedor -->
            <div>
              <p class="sub-titulo">Por vendedor</p>
              <div v-if="datos.por_vendedor.length === 0" class="sin-datos">Sin vendedores registrados</div>
              <div v-for="v in datos.por_vendedor" :key="v.vendedor_nombre" class="vendedor-resumen-row">
                <div class="vendedor-resumen-nombre">{{ v.vendedor_nombre }}</div>
                <div class="vendedor-resumen-stats">
                  <span class="vendedor-resumen-ventas">{{ v.cantidad_ventas }} venta{{ v.cantidad_ventas !== 1 ? 's' : '' }}</span>
                  <span class="vendedor-resumen-usd txt-verde">${{ v.subtotal_usd.toFixed(2) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Facturas del día -->
          <div class="facturas-dia" v-if="facturas.length">
            <h3 class="seccion-titulo">
              Facturas del día
              <span class="badge-count">{{ facturas.length }}</span>
            </h3>

            <div v-for="f in facturas" :key="f.venta_id"
              :class="['factura-row', f.estado === 'anulada' ? 'factura-anulada' : '']">

              <!-- Cabecera -->
              <div class="factura-header"
                @click="facturaExpandida = facturaExpandida === f.venta_id ? null : f.venta_id">
                <span class="factura-id">#{{ f.venta_id }}</span>
                <span class="factura-hora">{{ f.hora }}</span>
                <span class="factura-usuario">{{ f.usuario }}</span>
                <span class="factura-cliente">{{ f.cliente || 'Consumidor Final' }}</span>
                <span class="factura-metodos">
                  <span v-for="(m, i) in f.metodos_pago" :key="i" class="metodo-tag">
                    {{ labelMetodo(m.metodo) }}
                    <span v-if="m.cuenta" class="cuenta-tag">→ {{ m.cuenta }}</span>
                    <span class="monto-tag">${{ m.monto.toFixed(2) }}</span>
                  </span>
                </span>
                <span :class="['factura-total', f.estado === 'anulada' ? 'txt-danger' : 'txt-verde']">
                  {{ f.moneda === 'USD' ? '$' : 'Bs.' }}{{ f.total_usd.toFixed(2) }}
                </span>
                <span v-if="f.estado === 'anulada'" class="badge-anulada">ANULADA</span>
                <span class="factura-toggle">{{ facturaExpandida === f.venta_id ? '▲' : '▼' }}</span>
              </div>

              <!-- Detalle expandible -->
              <div v-if="facturaExpandida === f.venta_id" class="factura-detalle">
                <table class="tabla-detalle">
                  <thead>
                    <tr>
                      <th>Producto</th><th>Cant.</th><th>Precio</th><th>Subtotal</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(p, i) in f.productos" :key="i">
                      <td>{{ p.nombre }}</td>
                      <td style="text-align:center">{{ p.cantidad }}</td>
                      <td>{{ f.moneda === 'USD' ? '$' : 'Bs.' }}{{ p.precio_unitario.toFixed(2) }}</td>
                      <td>{{ f.moneda === 'USD' ? '$' : 'Bs.' }}{{ p.subtotal.toFixed(2) }}</td>
                    </tr>
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colspan="3" style="text-align:right;font-weight:700">Total:</td>
                      <td style="font-weight:700;color:#16A34A">
                        {{ f.moneda === 'USD' ? '$' : 'Bs.' }}{{ f.total_usd.toFixed(2) }}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </div>
        </template>

        <!-- Ventas → Por período -->
        <template v-if="tabMain === 'ventas' && tabSub === 'periodo' && !cargando && datos">
          <div class="kpi-row">
            <div class="kpi-card"><p class="kpi-label">Ventas</p><p class="kpi-valor">{{ datos.cantidad }}</p></div>
            <div class="kpi-card"><p class="kpi-label">Total USD</p><p class="kpi-valor txt-verde">${{ datos.total_usd.toFixed(2) }}</p></div>
            <div class="kpi-card"><p class="kpi-label">Total Bs</p><p class="kpi-valor">Bs. {{ datos.total_bs.toFixed(2) }}</p></div>
            <div class="kpi-card"><p class="kpi-label">Promedio USD</p><p class="kpi-valor">${{ datos.promedio_usd.toFixed(2) }}</p></div>
          </div>
          <div class="tabla-container">
            <table>
              <thead><tr><th>#</th><th>Fecha</th><th>Usuario</th><th>Moneda</th><th>Tipo precio</th><th>Total</th><th>Estado</th></tr></thead>
              <tbody>
                <tr v-for="v in datos.ventas" :key="v.id">
                  <td>#{{ v.id }}</td>
                  <td>{{ formatFecha(v.fecha) }}</td>
                  <td>{{ v.usuario }}</td>
                  <td>{{ v.moneda }}</td>
                  <td>{{ v.tipo_precio }}</td>
                  <td :class="v.moneda === 'USD' ? 'txt-verde' : ''">{{ v.moneda === 'USD' ? '$' : 'Bs.' }} {{ v.total.toFixed(2) }}</td>
                  <td><span :class="'badge badge-' + v.estado">{{ v.estado }}</span></td>
                </tr>
                <tr v-if="!datos.ventas || datos.ventas.length === 0"><td colspan="7" class="sin-datos">Sin ventas en el período</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Ventas → Por método -->
        <template v-if="tabMain === 'ventas' && tabSub === 'metodos' && !cargando && datos">
          <div class="metodos-grid">
            <div class="metodo-card" v-for="(info, key) in datos" :key="key">
              <p class="metodo-label">{{ info.label }}</p>
              <p class="metodo-moneda">{{ info.moneda }}</p>
              <p class="metodo-monto">{{ info.moneda === 'USD' ? '$' : 'Bs.' }} {{ info.monto.toFixed(2) }}</p>
              <p class="metodo-cant">{{ info.cantidad }} transacciones</p>
            </div>
            <div v-if="Object.keys(datos).length === 0" class="sin-datos">Sin pagos en el período</div>
          </div>
        </template>

        <!-- Ventas → Por departamento -->
        <template v-if="tabMain === 'ventas' && tabSub === 'departamento' && !cargando && datos != null">
          <div class="tabla-container">
            <table>
              <thead><tr><th>Departamento</th><th>Ventas</th><th>Unidades</th><th>Total USD</th><th>% del total</th></tr></thead>
              <tbody>
                <tr v-for="r in datos" :key="r.departamento_id">
                  <td style="font-weight:600">{{ r.departamento_nombre }}</td>
                  <td>{{ r.cantidad_ventas }}</td>
                  <td>{{ r.unidades_vendidas }}</td>
                  <td class="txt-verde">${{ r.total_usd.toFixed(2) }}</td>
                  <td><div class="pct-wrap"><div class="pct-fill" :style="{ width: r.pct_del_total + '%' }"></div><span class="pct-txt">{{ r.pct_del_total }}%</span></div></td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="5" class="sin-datos">Sin datos</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Ventas → Por proveedor -->
        <template v-if="tabMain === 'ventas' && tabSub === 'proveedor' && !cargando && datos != null">
          <div class="tabla-container">
            <table>
              <thead><tr><th>Proveedor</th><th>Ventas</th><th>Unidades</th><th>Total USD</th><th>% del total</th></tr></thead>
              <tbody>
                <tr v-for="r in datos" :key="r.proveedor_id">
                  <td style="font-weight:600">{{ r.proveedor_nombre }}</td>
                  <td>{{ r.cantidad_ventas }}</td>
                  <td>{{ r.unidades_vendidas }}</td>
                  <td class="txt-verde">${{ r.total_usd.toFixed(2) }}</td>
                  <td><div class="pct-wrap"><div class="pct-fill" :style="{ width: r.pct_del_total + '%' }"></div><span class="pct-txt">{{ r.pct_del_total }}%</span></div></td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="5" class="sin-datos">Sin datos</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Ventas → Pareto -->
        <template v-if="tabMain === 'ventas' && tabSub === 'pareto' && !cargando && datos">
          <div class="pareto-kpis">
            <div class="pareto-card pareto-clave">
              <p class="pareto-titulo">Productos Pareto (clave)</p>
              <p class="pareto-cant">{{ datos.pareto.cantidad_productos }} productos</p>
              <p class="pareto-usd">${{ datos.pareto.total_usd.toFixed(2) }}</p>
              <p class="pareto-pct">{{ datos.pareto.pct_del_total }}% del total · {{ datos.pareto.unidades_vendidas }} unid.</p>
            </div>
            <div class="pareto-card pareto-resto">
              <p class="pareto-titulo">Resto del catálogo</p>
              <p class="pareto-cant">{{ datos.resto.cantidad_productos }} productos</p>
              <p class="pareto-usd">${{ datos.resto.total_usd.toFixed(2) }}</p>
              <p class="pareto-pct">{{ datos.resto.pct_del_total }}% del total · {{ datos.resto.unidades_vendidas }} unid.</p>
            </div>
          </div>
          <p class="sub-titulo" style="margin-top:1.5rem">Detalle productos clave</p>
          <div class="tabla-container">
            <table>
              <thead><tr><th>Producto</th><th>Unidades vendidas</th><th>Total USD</th></tr></thead>
              <tbody>
                <tr v-for="p in datos.productos_pareto" :key="p.id">
                  <td>{{ p.nombre }}</td>
                  <td>{{ p.unidades }}</td>
                  <td class="txt-verde">${{ p.total_usd.toFixed(2) }}</td>
                </tr>
                <tr v-if="datos.productos_pareto.length === 0"><td colspan="3" class="sin-datos">Sin ventas de productos clave en el período</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Ventas → Por vendedor -->
        <template v-if="tabMain === 'ventas' && tabSub === 'vendedor' && !cargando && datos != null">
          <div class="tabla-container">
            <table>
              <thead><tr><th>Vendedor</th><th>Ventas</th><th>Total USD</th><th>Comisión ganada</th><th>% comisión prom.</th></tr></thead>
              <tbody>
                <tr v-for="r in datos" :key="r.vendedor_id">
                  <td style="font-weight:600">{{ r.vendedor_nombre }}</td>
                  <td>{{ r.cantidad_ventas }}</td>
                  <td class="txt-verde">${{ r.total_usd.toFixed(2) }}</td>
                  <td>${{ r.total_comision.toFixed(2) }}</td>
                  <td>{{ r.pct_comision_promedio }}%</td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="5" class="sin-datos">Sin comisiones en el período</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Ventas → Top productos -->
        <template v-if="tabMain === 'ventas' && tabSub === 'top' && !cargando && datos != null">
          <div class="tabla-container">
            <table>
              <thead><tr><th>Pos.</th><th>Producto</th><th>Departamento</th><th>Proveedor</th><th>Unidades</th><th>Total facturado</th></tr></thead>
              <tbody>
                <tr v-for="(p, i) in datos" :key="p.producto_id">
                  <td class="pos">{{ i + 1 }}</td>
                  <td>{{ p.nombre }}</td>
                  <td class="txt-muted">{{ p.departamento }}</td>
                  <td class="txt-muted">{{ p.proveedor }}</td>
                  <td>{{ p.total_cantidad }}</td>
                  <td class="txt-verde">${{ p.total_monto.toFixed(2) }}</td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="6" class="sin-datos">Sin datos de ventas</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- ══════════════════════════════════════════════════════════════════
             COMPRAS
        ═══════════════════════════════════════════════════════════════════ -->

        <!-- Compras → Por proveedor -->
        <template v-if="tabMain === 'compras' && tabSub === 'proveedor' && !cargando && datos != null">
          <div class="tabla-container">
            <table>
              <thead><tr><th>Proveedor</th><th>Órdenes cerradas</th><th>Total USD</th><th>Última compra</th></tr></thead>
              <tbody>
                <tr v-for="r in datos" :key="r.proveedor_id">
                  <td style="font-weight:600">{{ r.proveedor_nombre }}</td>
                  <td>{{ r.cantidad_ordenes }}</td>
                  <td class="txt-verde">${{ r.total_usd.toFixed(2) }}</td>
                  <td class="txt-muted">{{ formatFecha(r.ultima_compra) }}</td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="4" class="sin-datos">Sin órdenes cerradas</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Compras → Por departamento -->
        <template v-if="tabMain === 'compras' && tabSub === 'departamento' && !cargando && datos != null">
          <div class="tabla-container">
            <table>
              <thead><tr><th>Departamento</th><th>Items comprados</th><th>Total USD</th></tr></thead>
              <tbody>
                <tr v-for="r in datos" :key="r.departamento_id">
                  <td style="font-weight:600">{{ r.departamento_nombre }}</td>
                  <td>{{ r.cantidad_items }}</td>
                  <td class="txt-verde">${{ r.total_usd.toFixed(2) }}</td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="3" class="sin-datos">Sin datos</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Compras → Facturas pendientes -->
        <template v-if="tabMain === 'compras' && tabSub === 'facturas' && !cargando && datos != null">
          <div class="tabla-container">
            <table>
              <thead><tr><th>Proveedor</th><th>Orden</th><th>Factura</th><th>Monto</th><th>Vencimiento</th><th>Días</th><th>Estado</th></tr></thead>
              <tbody>
                <tr v-for="r in datos" :key="r.recepcion_id" :class="'fila-' + r.alerta">
                  <td style="font-weight:600">{{ r.proveedor_nombre }}</td>
                  <td class="txt-muted">{{ r.numero_orden }}</td>
                  <td>{{ r.numero_factura }}</td>
                  <td>${{ r.monto.toFixed(2) }}</td>
                  <td>{{ r.fecha_vencimiento || '—' }}</td>
                  <td>
                    <span :class="'badge-dias badge-dias-' + r.alerta">
                      {{ r.dias_restantes === null ? '—' : (r.dias_restantes < 0 ? Math.abs(r.dias_restantes) + 'd vencida' : r.dias_restantes + 'd') }}
                    </span>
                  </td>
                  <td><span :class="'badge badge-' + r.estado_pago">{{ r.estado_pago }}</span></td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="7" class="sin-datos">Sin facturas pendientes</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- ══════════════════════════════════════════════════════════════════
             INVENTARIO
        ═══════════════════════════════════════════════════════════════════ -->

        <!-- Inventario → Por departamento -->
        <template v-if="tabMain === 'inventario' && tabSub === 'departamento' && !cargando && datos != null">
          <p class="total-inventario">Valor total del inventario: <strong>${{ totalInventarioDept.toFixed(2) }}</strong></p>
          <div class="tabla-container">
            <table>
              <thead><tr><th>Departamento</th><th>Productos</th><th>Stock total</th><th>Valor USD</th><th>Bajo stock</th></tr></thead>
              <tbody>
                <tr v-for="r in datos" :key="r.departamento_id">
                  <td style="font-weight:600">{{ r.departamento_nombre }}</td>
                  <td>{{ r.cantidad_productos }}</td>
                  <td>{{ r.stock_total }}</td>
                  <td class="txt-verde">${{ r.valor_usd.toFixed(2) }}</td>
                  <td :class="r.productos_bajo_stock > 0 ? 'txt-rojo' : ''">{{ r.productos_bajo_stock }}</td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="5" class="sin-datos">Sin datos</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Inventario → Por proveedor -->
        <template v-if="tabMain === 'inventario' && tabSub === 'proveedor' && !cargando && datos != null">
          <div class="tabla-container">
            <table>
              <thead><tr><th>Proveedor</th><th>Productos</th><th>Stock total</th><th>Valor USD</th></tr></thead>
              <tbody>
                <tr v-for="r in datos" :key="r.proveedor_id">
                  <td style="font-weight:600">{{ r.proveedor_nombre }}</td>
                  <td>{{ r.cantidad_productos }}</td>
                  <td>{{ r.stock_total }}</td>
                  <td class="txt-verde">${{ r.valor_usd.toFixed(2) }}</td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="4" class="sin-datos">Sin datos</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Inventario → Pareto -->
        <template v-if="tabMain === 'inventario' && tabSub === 'pareto' && !cargando && datos != null">
          <div class="tabla-container">
            <table>
              <thead><tr><th>Producto</th><th>Stock</th><th>Valor inv.</th><th>Vendidos (período)</th><th>Rotación</th></tr></thead>
              <tbody>
                <tr v-for="r in datos" :key="r.id">
                  <td>{{ r.nombre }}</td>
                  <td>{{ r.stock }}</td>
                  <td>${{ r.valor_inventario.toFixed(2) }}</td>
                  <td>{{ r.unidades_vendidas }}</td>
                  <td>{{ r.rotacion !== null ? r.rotacion : '—' }}</td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="5" class="sin-datos">Sin productos clave registrados</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Inventario → Rotación -->
        <template v-if="tabMain === 'inventario' && tabSub === 'rotacion' && !cargando && datos != null">
          <div class="tabla-container">
            <table>
              <thead><tr><th>Producto</th><th>Depto.</th><th>Stock</th><th>Vendidos</th><th>Rotación</th><th>Días agot.</th></tr></thead>
              <tbody>
                <tr v-for="r in datos" :key="r.id"
                  :class="r.dias_agotamiento !== null && r.dias_agotamiento < 7 ? 'fila-critica' : ''">
                  <td>{{ r.nombre }}</td>
                  <td class="txt-muted">{{ r.departamento }}</td>
                  <td>{{ r.stock }}</td>
                  <td>{{ r.unidades_vendidas }}</td>
                  <td>{{ r.rotacion !== null ? r.rotacion : '—' }}</td>
                  <td :class="r.dias_agotamiento !== null && r.dias_agotamiento < 7 ? 'txt-rojo' : ''">
                    {{ r.dias_agotamiento !== null ? r.dias_agotamiento + 'd' : '—' }}
                  </td>
                </tr>
                <tr v-if="datos.length === 0"><td colspan="6" class="sin-datos">Sin datos</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Inventario → Valorización -->
        <template v-if="tabMain === 'inventario' && tabSub === 'valorizacion'">
          <!-- Selector agrupación -->
          <div class="val-agrupacion">
            <span class="val-agrupacion-label">Agrupar por:</span>
            <button :class="['btn-agrup', agrupacion === 'departamento' ? 'activo' : '']"
              @click="agrupacion = 'departamento'; cargar()">Departamento</button>
            <button :class="['btn-agrup', agrupacion === 'proveedor' ? 'activo' : '']"
              @click="agrupacion = 'proveedor'; cargar()">Proveedor</button>
          </div>

          <!-- Panel imprimir no auditados -->
          <div class="val-imprimir-panel">
            <h4 class="val-imprimir-titulo">🖨 Imprimir no auditados</h4>
            <div class="val-imprimir-filtros">
              <select v-model="imprimirDeptoId" class="filtro-sel-oc">
                <option value="">Todos los departamentos</option>
                <option v-for="d in departamentosVal" :key="d.id" :value="d.id">{{ d.nombre }}</option>
              </select>
              <input v-model="imprimirDesde" placeholder="Desde (ej: A)" class="input-field-sm" style="max-width:100px" />
              <input v-model="imprimirHasta" placeholder="Hasta (ej: Z)" class="input-field-sm" style="max-width:100px" />
              <button class="btn-imprimir-val" @click="imprimirNoAuditados">🖨 Generar PDF</button>
            </div>
            <small class="txt-muted">Vacío desde/hasta = todos los productos</small>
          </div>

          <div v-if="!datos || datos.length === 0" class="sin-datos-box">Sin productos en inventario</div>
          <div v-else>
            <div class="val-totales">
              <div class="val-total-card">
                <span class="val-total-label">Valor al costo</span>
                <span class="val-total-val txt-rojo">${{ totalGeneral('total_costo_usd') }}</span>
              </div>
              <div class="val-total-card">
                <span class="val-total-label">Valor a precio base</span>
                <span class="val-total-val txt-verde">${{ totalGeneral('total_precio_usd') }}</span>
              </div>
              <div class="val-total-card">
                <span class="val-total-label">Ganancia potencial</span>
                <span class="val-total-val txt-amarillo">${{ totalGeneral('ganancia_potencial') }}</span>
              </div>
            </div>
            <div v-for="g in datos" :key="g.departamento_id" class="val-depto-card">
              <div class="val-depto-header"
                @click="deptoExpandido = deptoExpandido === g.departamento_id ? null : g.departamento_id">
                <span class="val-depto-nombre">{{ g.departamento }}</span>
                <span class="val-depto-meta txt-muted">{{ g.total_unidades }} uds</span>
                <span class="val-col txt-rojo">${{ g.total_costo_usd.toFixed(2) }}</span>
                <span class="val-col txt-verde">${{ g.total_precio_usd.toFixed(2) }}</span>
                <span class="val-col txt-amarillo">+${{ g.ganancia_potencial.toFixed(2) }}</span>
                <span class="val-toggle">{{ deptoExpandido === g.departamento_id ? '▲' : '▼' }}</span>
              </div>
              <div v-if="deptoExpandido === g.departamento_id" class="val-productos">
                <table class="tabla-val">
                  <thead>
                    <tr>
                      <th>Producto</th><th>Categoría</th><th>Stock</th>
                      <th>Costo unit.</th><th>Precio base</th><th>Margen</th>
                      <th>Val. costo</th><th>Val. precio</th><th>Ganancia</th><th>Auditoría</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="p in g.productos" :key="p.id">
                      <td style="font-weight:600">{{ p.nombre }}</td>
                      <td class="txt-muted">{{ p.categoria }}</td>
                      <td style="text-align:center">{{ p.stock }}</td>
                      <td>${{ p.costo_usd.toFixed(2) }}</td>
                      <td>${{ p.precio_base.toFixed(2) }}</td>
                      <td>
                        <span :class="p.margen_pct >= 20 ? 'txt-verde' : p.margen_pct >= 10 ? 'txt-amarillo' : 'txt-rojo'">
                          {{ p.margen_pct }}%
                        </span>
                      </td>
                      <td class="txt-rojo">${{ p.valor_costo.toFixed(2) }}</td>
                      <td class="txt-verde">${{ p.valor_precio.toFixed(2) }}</td>
                      <td class="txt-amarillo" style="font-weight:700">+${{ p.ganancia.toFixed(2) }}</td>
                      <td>
                        <span v-if="p.auditoria_pendiente" class="badge-audit-pendiente">⚠ Pendiente</span>
                        <span v-else-if="p.auditado" class="badge-audit-ok" :title="p.fecha_auditoria || ''">
                          ✓ {{ p.fecha_auditoria || 'OK' }}
                        </span>
                        <span v-else class="badge-audit-sin">Sin auditar</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </template>

        <!-- Inventario → Conteos físicos -->
        <template v-if="tabMain === 'inventario' && tabSub === 'conteos'">
          <div v-if="!datos || datos.length === 0" class="sin-datos-box">
            No hay conteos registrados en el período
          </div>
          <div v-else>
            <div v-for="conteo in datos" :key="conteo.id" class="conteo-card">
              <div class="conteo-header"
                @click="conteoExpandido = conteoExpandido === conteo.id ? null : conteo.id">
                <span class="conteo-fecha">
                  {{ new Date(conteo.fecha).toLocaleDateString('es-VE',
                    { day:'2-digit', month:'2-digit', year:'numeric',
                      hour:'2-digit', minute:'2-digit' }) }}
                </span>
                <span class="conteo-usuario">{{ conteo.usuario }}</span>
                <span class="conteo-desc">{{ conteo.descripcion }}</span>
                <span class="badge-count">{{ conteo.productos_afectados }} productos</span>
                <span class="conteo-toggle">{{ conteoExpandido === conteo.id ? '▲' : '▼' }}</span>
              </div>
              <div v-if="conteoExpandido === conteo.id" class="conteo-detalle">
                <table class="tabla-conteo">
                  <thead>
                    <tr>
                      <th>Producto</th><th>Stock sistema</th>
                      <th>Contado</th><th>Diferencia</th><th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, i) in parsearConteo(conteo.detalle_json)" :key="i"
                      :class="item.estado === 'pendiente' ? 'fila-pendiente' : ''">
                      <td>{{ item.nombre }}</td>
                      <td style="text-align:center">{{ item.stock_sistema ?? item.stock_anterior }}</td>
                      <td style="text-align:center">{{ item.conteo ?? item.stock_nuevo }}</td>
                      <td style="text-align:center"
                        :class="item.diferencia < 0 ? 'txt-rojo' : item.diferencia > 0 ? 'txt-verde' : ''">
                        {{ item.diferencia > 0 ? '+' : '' }}{{ item.diferencia }}
                      </td>
                      <td>
                        <span v-if="item.estado === 'pendiente'" class="badge-audit-pendiente">⚠ Pendiente</span>
                        <span v-else class="badge-audit-ok">✓ OK</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </template>

        <!-- ══════════════════════════════════════════════════════════════════
             OTROS
        ═══════════════════════════════════════════════════════════════════ -->

        <!-- Otros → Cierres -->
        <template v-if="tabMain === 'otros' && tabSub === 'cierres' && !cargando && datos != null">
          <div v-for="c in datos" :key="c.id" class="cierre-card">
            <div class="cierre-header">
              <span class="cierre-id">Cierre #{{ c.id }}</span>
              <span class="cierre-fecha">{{ formatFecha(c.fecha) }}</span>
              <span class="cierre-usuario">{{ c.usuario }}</span>
              <span class="cierre-total txt-verde">${{ c.total_usd.toFixed(2) }} · {{ c.cantidad_ventas }} ventas</span>
            </div>
            <table class="tabla-cierre-detalle">
              <thead><tr><th>Método</th><th>Esperado</th><th>Contado</th><th>Diferencia</th></tr></thead>
              <tbody>
                <template v-for="(info, metodo) in c.detalle" :key="metodo">
                  <tr v-if="info.esperado > 0 || info.contado > 0">
                    <td>{{ labelMetodo(metodo) }}</td>
                    <td>{{ info.esperado }}</td>
                    <td>{{ info.contado }}</td>
                    <td :class="info.diferencia === 0 ? 'txt-verde' : (info.diferencia > 0 ? '' : 'txt-rojo')">
                      {{ info.diferencia >= 0 ? '+' : '' }}{{ info.diferencia }}
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
          <div v-if="!datos || datos.length === 0" class="sin-datos">Sin cierres registrados</div>
        </template>

        <!-- Otros → Clientes -->
        <template v-if="tabMain === 'otros' && tabSub === 'clientes' && !cargando && datos">
          <div class="kpi-row">
            <div class="kpi-card"><p class="kpi-label">Total clientes</p><p class="kpi-valor">{{ datos.total_clientes }}</p></div>
            <div class="kpi-card"><p class="kpi-label">Nuevos en período</p><p class="kpi-valor txt-verde">{{ datos.nuevos_periodo }}</p></div>
            <div class="kpi-card"><p class="kpi-label">Inactivos (30 días)</p><p class="kpi-valor txt-rojo">{{ datos.inactivos_30d }}</p></div>
          </div>
          <div class="niveles-resumen">
            <div v-for="(cant, nivel) in datos.por_nivel" :key="nivel" class="nivel-chip">
              <span class="nivel-chip-nombre">{{ nivel }}</span>
              <span class="nivel-chip-cant">{{ cant }}</span>
            </div>
          </div>
          <div class="dos-columnas">
            <div>
              <p class="sub-titulo">Top 10 por monto acumulado</p>
              <table>
                <thead><tr><th>Pos.</th><th>Cliente</th><th>Nivel</th><th>Monto USD</th></tr></thead>
                <tbody>
                  <tr v-for="(c, i) in datos.top_monto" :key="c.id">
                    <td class="pos">{{ i + 1 }}</td><td>{{ c.nombre }}</td><td>{{ c.nivel }}</td>
                    <td class="txt-verde">${{ c.monto.toFixed(2) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div>
              <p class="sub-titulo">Top 10 por compras</p>
              <table>
                <thead><tr><th>Pos.</th><th>Cliente</th><th>Nivel</th><th>Compras</th></tr></thead>
                <tbody>
                  <tr v-for="(c, i) in datos.top_compras" :key="c.id">
                    <td class="pos">{{ i + 1 }}</td><td>{{ c.nombre }}</td><td>{{ c.nivel }}</td>
                    <td>{{ c.compras }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>

      </div>

      <!-- ── Panel lateral de rotación ──────────────────────────────────── -->
      <div v-if="panelVisible" class="panel-overlay" @click.self="cerrarPanel">
        <div class="panel-lateral">

          <div class="panel-header">
            <div class="panel-nombre">{{ panelProducto && panelProducto.producto }}</div>
            <button class="panel-cerrar" @click="cerrarPanel">✕</button>
          </div>

          <div v-if="panelProducto" class="panel-kpis">
            <div class="panel-kpi">
              <span class="panel-kpi-label">Stock actual</span>
              <span class="panel-kpi-valor">{{ panelProducto.stock_actual }}</span>
            </div>
            <div class="panel-kpi">
              <span class="panel-kpi-label">Stock mínimo</span>
              <span class="panel-kpi-valor">{{ panelProducto.stock_minimo }}</span>
            </div>
            <div class="panel-kpi">
              <span class="panel-kpi-label">Vendidos 30d</span>
              <span class="panel-kpi-valor">{{ panelProducto.vendidos_30d }}</span>
            </div>
            <div class="panel-kpi">
              <span class="panel-kpi-label">Cobertura</span>
              <span class="panel-kpi-valor">{{ panelProducto.dias_cobertura < 999 ? panelProducto.dias_cobertura + 'd' : '∞' }}</span>
            </div>
          </div>

          <div v-if="panelProducto" class="panel-costos">
            <div class="panel-costo-item">
              <span>Costo</span>
              <span>${{ Number(panelProducto.costo_usd || 0).toFixed(2) }}</span>
            </div>
            <div class="panel-costo-item">
              <span>Margen</span>
              <span :class="panelProducto.margen_pct >= 20 ? 'txt-verde' : panelProducto.margen_pct >= 10 ? 'txt-amarillo' : 'txt-danger'">
                {{ panelProducto.margen_pct }}%
              </span>
            </div>
            <div class="panel-costo-item">
              <span>Ganancia</span>
              <span :class="panelProducto.ganancia_usd > 0 ? 'txt-verde' : 'txt-danger'">
                ${{ Number(panelProducto.ganancia_usd || 0).toFixed(2) }}
              </span>
            </div>
          </div>

          <div class="panel-seccion-titulo">Rotación últimos 30 días</div>
          <div v-if="panelCargando" class="panel-cargando">Cargando...</div>
          <div v-else class="panel-barras">
            <div v-for="(d, i) in panelRotacion" :key="i" class="panel-barra-wrap">
              <div class="panel-barra-col">
                <span v-if="d.cantidad > 0" class="panel-barra-val">{{ d.cantidad }}</span>
                <div class="panel-barra"
                  :style="{ height: maxRotacion > 0 ? (d.cantidad / maxRotacion * 80) + 'px' : '0px' }"
                  :class="d.cantidad > 0 ? 'panel-barra-activa' : 'panel-barra-vacia'">
                </div>
              </div>
              <span class="panel-barra-dia">{{ d.dia }}</span>
            </div>
          </div>

          <button class="panel-btn-repo" @click="agregarReposicion(panelProducto)">
            + Agregar a lista de reposición
          </button>

        </div>
      </div>

      <!-- ── Panel lista de reposición ──────────────────────────────────── -->
      <div v-if="verListaReposicion" class="panel-overlay" @click.self="verListaReposicion = false">
        <div class="panel-lateral">

          <div class="panel-header">
            <h3 style="margin:0;font-size:1rem">🛒 Lista de reposición</h3>
            <button @click="verListaReposicion = false" class="panel-cerrar">✕</button>
          </div>

          <div class="panel-body">

            <div v-if="listaReposicion.length === 0" class="panel-cargando">
              No hay productos en la lista
            </div>

            <div v-else>
              <div v-for="(p, i) in listaReposicion" :key="p.producto_id" class="repos-item">
                <div class="repos-item-info">
                  <span :class="'punto-' + p.semaforo">●</span>
                  <div class="repos-item-detalle">
                    <span class="repos-nombre">{{ p.nombre }}</span>
                    <span class="repos-meta">
                      Stock: {{ p.stock }} ·
                      {{ p.dias >= 999 ? 'Sin movimiento' : p.dias + 'd cobertura' }}
                    </span>
                  </div>
                </div>
                <div class="repos-item-acciones">
                  <input
                    v-model.number="p.cantidad_pedir"
                    type="number" min="1"
                    placeholder="Cant."
                    class="input-repos-cant"
                  />
                  <button class="btn-quitar-repos" @click="listaReposicion.splice(i, 1)">✕</button>
                </div>
              </div>

              <div class="repos-resumen">
                <p class="repos-resumen-txt">{{ listaReposicion.length }} producto(s) para reponer</p>
                <p class="repos-hint">
                  Cuando estés listo, crea la orden de compra formal desde el módulo de Compras.
                </p>
              </div>

              <div class="repos-acciones">
                <button class="btn-copiar-repos" @click="copiarListaReposicion">📋 Copiar lista</button>
                <button class="btn-whatsapp-repos" @click="enviarReposicionWhatsApp">💬 Enviar por WhatsApp</button>
                <button class="btn-limpiar-repos" @click="listaReposicion = []">🗑 Limpiar lista</button>
              </div>
            </div>

          </div>
        </div>
      </div>

      <!-- Badge flotante lista de reposición -->
      <div v-if="listaReposicion.length" class="badge-repo-flotante" @click="verListaReposicion = !verListaReposicion">
        🛒 {{ listaReposicion.length }} para reponer
      </div>

    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

const LABELS_METODO = {
  efectivo_usd: 'Efectivo $', zelle: 'Zelle', binance: 'Binance',
  efectivo_bs: 'Efectivo Bs', transferencia_bs: 'Transferencia Bs',
  pago_movil: 'Pago Móvil', punto_banesco: 'Punto Banesco', punto_provincial: 'Punto Provincial',
}

const SUBTABS = {
  ventas:     [
    { key: 'resumen_dia', label: 'Resumen del día' },
    { key: 'periodo',     label: 'Por período' },
    { key: 'metodos',     label: 'Por método' },
    { key: 'departamento',label: 'Por depto.' },
    { key: 'proveedor',   label: 'Por proveedor' },
    { key: 'pareto',      label: 'Pareto' },
    { key: 'vendedor',    label: 'Por vendedor' },
    { key: 'top',         label: 'Top productos' },
  ],
  compras:    [
    { key: 'proveedor',    label: 'Por proveedor' },
    { key: 'departamento', label: 'Por depto.' },
    { key: 'facturas',     label: 'Fact. pendientes' },
  ],
  inventario: [
    { key: 'departamento', label: 'Por depto.' },
    { key: 'proveedor',    label: 'Por proveedor' },
    { key: 'pareto',       label: 'Pareto' },
    { key: 'rotacion',     label: 'Rotación' },
    { key: 'valorizacion', label: 'Valorización' },
    { key: 'conteos',      label: 'Conteos físicos' },
  ],
  otros: [
    { key: 'cierres',  label: 'Cierres' },
    { key: 'clientes', label: 'Clientes' },
  ],
}

const URL_MAP = {
  'ventas-resumen_dia':      '/reportes/ventas/resumen-dia',
  'ventas-periodo':          '/reportes/ventas',
  'ventas-metodos':          '/reportes/ventas/por-metodo',
  'ventas-departamento':     '/reportes/ventas/por-departamento',
  'ventas-proveedor':        '/reportes/ventas/por-proveedor',
  'ventas-pareto':           '/reportes/ventas/por-pareto',
  'ventas-vendedor':         '/reportes/ventas/por-vendedor',
  'ventas-top':              '/reportes/productos/top',
  'compras-proveedor':       '/reportes/compras/por-proveedor',
  'compras-departamento':    '/reportes/compras/por-departamento',
  'compras-facturas':        '/reportes/compras/facturas-pendientes',
  'inventario-departamento': '/reportes/inventario/por-departamento',
  'inventario-proveedor':    '/reportes/inventario/por-proveedor',
  'inventario-pareto':       '/reportes/inventario/pareto',
  'inventario-rotacion':     '/reportes/inventario/rotacion',
  'inventario-valorizacion': '/reportes/inventario/valorizacion',
  'inventario-conteos':      '/ajustes/historial',
  'otros-cierres':           '/reportes/cierre/comparativo',
  'otros-clientes':          '/reportes/clientes/resumen',
}

const CON_FILTROS = new Set([
  'ventas-resumen_dia', 'ventas-periodo', 'ventas-metodos', 'ventas-departamento',
  'ventas-proveedor', 'ventas-pareto', 'ventas-vendedor', 'ventas-top',
  'compras-proveedor', 'compras-departamento',
  'inventario-pareto', 'inventario-rotacion', 'inventario-conteos', 'otros-clientes',
])

export default {
  components: { AppSidebar },
  name: 'Reportes',
  data() {
    return {
      usuario:  JSON.parse(localStorage.getItem('usuario') || '{}'),
      tabMain:  'ventas',
      tabSub:   'resumen_dia',
      datos:            null,
      cargando:         false,
      facturas:         [],
      facturaExpandida:   null,
      panelProducto:      null,
      panelVisible:       false,
      panelRotacion:      [],
      panelCargando:      false,
      listaReposicion:    [],
      verListaReposicion: false,
      conteoExpandido:    null,
      deptoExpandido:     null,
      imprimirDeptoId:    '',
      imprimirDesde:      '',
      imprimirHasta:      '',
      departamentosVal:   [],
      agrupacion:         'departamento',
      desdeDia: '',
      hastaDia: '',
      MAIN_TABS: [
        { key: 'ventas',     label: 'Ventas' },
        { key: 'compras',    label: 'Compras' },
        { key: 'inventario', label: 'Inventario' },
        { key: 'otros',      label: 'Otros' },
      ],
    }
  },
  computed: {
    mesActual() {
      return String(new Date().getMonth() + 1).padStart(2, '0')
    },
    anioActual() {
      return new Date().getFullYear()
    },
    fechaDesde() {
      if (!this.desdeDia) return ''
      const dia = String(parseInt(this.desdeDia)).padStart(2, '0')
      return `${this.anioActual}-${this.mesActual}-${dia}`
    },
    fechaHasta() {
      if (!this.hastaDia) return ''
      const dia = String(parseInt(this.hastaDia)).padStart(2, '0')
      return `${this.anioActual}-${this.mesActual}-${dia}`
    },
    esAdmin()  { return this.usuario.rol === 'admin' },
    tienePermiso() {
      return (modulo) => {
        if (this.usuario.rol === 'admin') return true
        const p = this.usuario.permisos
        if (p == null) return true
        return Array.isArray(p) ? p.includes(modulo) : true
      }
    },
    tabKey()           { return `${this.tabMain}-${this.tabSub}` },
    subTabsActuales()  { return SUBTABS[this.tabMain] || [] },
    tieneFiltros()     { return CON_FILTROS.has(this.tabKey) },
    totalInventarioDept() {
      if (this.tabMain !== 'inventario' || this.tabSub !== 'departamento' || !this.datos) return 0
      return this.datos.reduce((s, r) => s + r.valor_usd, 0)
    },
    maxRotacion() {
      if (!this.panelRotacion.length) return 1
      return Math.max(...this.panelRotacion.map(d => d.cantidad), 1)
    },
  },
  async mounted() {
    await this.cargar()
  },
  methods: {
    async cambiarTabMain(tab) {
      this.tabMain = tab
      this.tabSub  = SUBTABS[tab][0].key
      this.datos   = null
      await this.cargar()
    },
    async cambiarTabSub(sub) {
      this.tabSub = sub
      this.datos  = null
      if (sub === 'valorizacion' && this.departamentosVal.length === 0) {
        await this.cargarDepartamentosVal()
      }
      await this.cargar()
    },
    async cargar() {
      const url = URL_MAP[this.tabKey]
      if (!url) return
      this.cargando = true
      try {
        const params = {}
        if (this.tieneFiltros) {
          if (this.fechaDesde) params.desde = this.fechaDesde
          if (this.fechaHasta) params.hasta = this.fechaHasta
        }
        if (this.tabKey === 'inventario-conteos') {
          params.tipo = 'auditoria'
        }
        if (this.tabKey === 'inventario-valorizacion') {
          params.agrupar_por = this.agrupacion
        }
        const res  = await axios.get(url, { params })
        this.datos    = res.data
        this.facturas = res.data.facturas || []
      } catch (e) {
        console.error('Error cargando reporte', e)
        this.datos = null
      } finally {
        this.cargando = false
      }
    },
    limpiarFiltros() { this.desdeDia = ''; this.hastaDia = ''; this.cargar() },
    setHoy() {
      const d = new Date().getDate()
      this.desdeDia = d; this.hastaDia = d; this.cargar()
    },
    setAyer() {
      const d = new Date()
      d.setDate(d.getDate() - 1)
      this.desdeDia = d.getDate(); this.hastaDia = d.getDate(); this.cargar()
    },
    setHace2Dias() {
      const d = new Date()
      d.setDate(d.getDate() - 2)
      this.desdeDia = d.getDate(); this.hastaDia = d.getDate(); this.cargar()
    },
    setSemana() {
      const hoy = new Date()
      const lunes = new Date(hoy)
      lunes.setDate(hoy.getDate() - ((hoy.getDay() + 6) % 7))
      this.desdeDia = lunes.getDate()
      this.hastaDia = hoy.getDate()
      this.cargar()
    },
    setMes() {
      this.desdeDia = 1
      this.hastaDia = new Date().getDate()
      this.cargar()
    },
    setAnio() {
      this.desdeDia = 1
      this.hastaDia = new Date().getDate()
      this.cargar()
    },
    exportar() { alert('Función disponible próximamente') },
    labelMetodo(m) { return LABELS_METODO[m] || m },
    formatFecha(iso) { return iso ? new Date(iso).toLocaleString('es-VE') : '—' },
    parsearConteo(jsonStr) {
      try { return JSON.parse(jsonStr || '[]') } catch { return [] }
    },
    totalGeneral(campo) {
      if (!this.datos || !this.datos.length) return '0.00'
      return this.datos.reduce((s, g) => s + (g[campo] || 0), 0).toFixed(2)
    },
    async cargarDepartamentosVal() {
      try {
        const res = await axios.get('/productos/departamentos')
        this.departamentosVal = res.data
      } catch {}
    },
    async imprimirNoAuditados() {
      try {
        const params = {}
        if (this.imprimirDeptoId) params.departamento_id = this.imprimirDeptoId
        if (this.imprimirDesde)   params.desde_nombre    = this.imprimirDesde
        if (this.imprimirHasta)   params.hasta_nombre    = this.imprimirHasta
        const res = await axios.get('/reportes/inventario/no-auditados/pdf', {
          params,
          responseType: 'blob',
        })
        const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
        window.open(url, '_blank')
        setTimeout(() => URL.revokeObjectURL(url), 10000)
      } catch {
        alert('Error al generar PDF')
      }
    },
    formatFechaPreview(iso) {
      return new Date(iso + 'T00:00:00').toLocaleDateString('es-VE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    },
    salir() { localStorage.removeItem('usuario'); this.$router.push('/login') },
    async abrirPanelProducto(l) {
      this.panelProducto = l
      this.panelVisible  = true
      this.panelRotacion = []
      this.panelCargando = true
      try {
        const res = await axios.get(`/reportes/productos/${l.producto_id}/rotacion30`)
        this.panelRotacion = res.data
      } catch (e) {
        console.error('Error cargando rotación', e)
      } finally {
        this.panelCargando = false
      }
    },
    agregarReposicion(l) {
      const ya = this.listaReposicion.find(r => r.producto_id === l.producto_id)
      if (!ya) this.listaReposicion.push({
        producto_id:    l.producto_id,
        nombre:         l.producto,
        stock:          l.stock_actual,
        semaforo:       l.semaforo,
        dias:           l.dias_cobertura,
        cantidad_pedir: null,
      })
      this.verListaReposicion = true
    },
    cerrarPanel() {
      this.panelVisible  = false
      this.panelProducto = null
    },
    copiarListaReposicion() {
      const texto = this.listaReposicion.map(p =>
        `• ${p.nombre} — Stock: ${p.stock} — Pedir: ${p.cantidad_pedir || '?'}`
      ).join('\n')
      navigator.clipboard.writeText(
        `LISTA DE REPOSICIÓN\n${new Date().toLocaleDateString('es-VE')}\n\n${texto}`
      )
      alert('Lista copiada al portapapeles')
    },
    enviarReposicionWhatsApp() {
      const lineas = this.listaReposicion.map(p =>
        `• ${p.nombre}\n  Stock: ${p.stock} · Pedir: ${p.cantidad_pedir || 'por definir'}`
      ).join('\n\n')
      const msg = encodeURIComponent(
        `*LISTA DE REPOSICIÓN - FERRE-UTIL*\n_${new Date().toLocaleDateString('es-VE')}_\n\n${lineas}`
      )
      window.open(`https://wa.me/?text=${msg}`, '_blank')
    },
  },
}
</script>

<style scoped>
/* Tabs principales */
.tabs-main {
  display: flex; gap: 0.25rem; margin-bottom: 0;
  border-bottom: 2px solid var(--borde);
}
.tab-main {
  background: transparent; border: none; padding: 0.6rem 1.2rem;
  cursor: pointer; font-size: 0.9rem; font-weight: 600;
  color: var(--texto-sec); border-bottom: 3px solid transparent; margin-bottom: -2px;
}
.tab-main.activo { color: var(--texto-principal); border-bottom-color: #FFCC00; }

/* Sub-tabs */
.tabs-sub {
  display: flex; gap: 0.25rem; margin-bottom: 0;
  background: var(--fondo-sidebar); border-radius: 0 0 10px 10px;
  padding: 0.4rem 0.75rem; border: 1px solid var(--borde); border-top: none;
  margin-bottom: 1rem; flex-wrap: wrap;
}
.tab-sub {
  background: transparent; border: none; padding: 0.35rem 0.85rem;
  cursor: pointer; font-size: 0.82rem; color: var(--texto-sec);
  border-radius: 6px; font-weight: 500;
}
.tab-sub.activo { background: #FFFFFF; color: var(--texto-principal); font-weight: 700; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }

/* Barra de acciones */
.barra-acciones {
  display: flex; align-items: flex-end; gap: 0.75rem;
  flex-wrap: wrap; margin-bottom: 1.25rem;
}
.field-inline { display: flex; flex-direction: column; gap: 0.3rem; }
.field-inline label { color: var(--texto-sec); font-size: 0.78rem; font-weight: 600; }
.fecha-preview { display: block; color: #16A34A; font-size: 0.75rem; margin-top: 0.25rem; font-weight: 600; }
.btn-filtrar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.45rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; align-self: flex-end; font-weight: 600; }
.btn-limpiar  { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.45rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; align-self: flex-end; }
.btn-rapido   { background: var(--fondo-sidebar); color: var(--texto-sec); border: 1px solid var(--borde); padding: 0.45rem 0.7rem; border-radius: 6px; cursor: pointer; font-size: 0.78rem; align-self: flex-end; }
.btn-rapido:hover { color: var(--texto-principal); }
.btn-exportar { margin-left: auto; background: transparent; color: var(--texto-sec); border: 1px solid var(--borde); padding: 0.45rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; align-self: flex-end; }
.btn-exportar:hover { background: var(--fondo-sidebar); }

/* KPI */
.kpi-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }

/* Métodos */
.metodos-grid { display: flex; flex-wrap: wrap; gap: 1rem; }
.metodo-card  { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 12px; padding: 1.25rem 1.5rem; min-width: 180px; }
.metodo-label  { color: var(--texto-principal); font-weight: 600; margin: 0 0 0.2rem; font-size: 0.9rem; }
.metodo-moneda { color: var(--texto-muted); font-size: 0.78rem; margin: 0 0 0.5rem; }
.metodo-monto  { color: #16A34A; font-size: 1.4rem; font-weight: 700; margin: 0; }
.metodo-cant   { color: var(--texto-muted); font-size: 0.8rem; margin: 0.25rem 0 0; }

/* Barra de porcentaje */
.pct-wrap { position: relative; background: #FFCC0033; border-radius: 4px; height: 18px; width: 110px; display: flex; align-items: center; overflow: hidden; }
.pct-fill { position: absolute; left: 0; top: 0; height: 100%; background: #FFCC00; border-radius: 4px; }
.pct-txt  { position: relative; z-index: 1; font-size: 0.75rem; font-weight: 700; padding: 0 0.4rem; color: #555; }

/* Pareto */
.pareto-kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; max-width: 700px; }
.pareto-card { border-radius: 12px; padding: 1.25rem 1.5rem; border: 1px solid var(--borde); }
.pareto-clave { background: #FFCC0015; border-color: #FFCC0066; }
.pareto-resto { background: var(--fondo-sidebar); }
.pareto-titulo { color: var(--texto-sec); font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 0.5rem; }
.pareto-cant   { color: var(--texto-sec); font-size: 0.85rem; margin: 0; }
.pareto-usd    { color: var(--texto-principal); font-size: 1.5rem; font-weight: 700; margin: 0.25rem 0; }
.pareto-pct    { color: var(--texto-sec); font-size: 0.82rem; margin: 0; }

/* Inventario */
.total-inventario { color: var(--texto-sec); font-size: 0.9rem; margin-bottom: 0.75rem; }
.total-inventario strong { color: #16A34A; }

/* Filas coloreadas */
.fila-vencida td { background: #DC262608; }
.fila-proxima td { background: #FFCC0018; }
.fila-critica td { background: #DC262608; }

/* Días badge */
.badge-dias { font-size: 0.78rem; font-weight: 600; padding: 0.15rem 0.45rem; border-radius: 4px; }
.badge-dias-vencida { background: #DC26261A; color: #DC2626; }
.badge-dias-proxima { background: #FFCC0033; color: #996600; }
.badge-dias-ok      { background: #16A34A1A; color: #16A34A; }

/* Cierres */
.cierre-card    { background: #FFFFFF; border-radius: 12px; padding: 1.25rem; margin-bottom: 1.5rem; border: 1px solid var(--borde); }
.sin-datos-box { padding: 2rem; text-align: center; color: var(--texto-muted); font-size: 0.9rem; }
.val-totales { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1.25rem; }
.val-total-card { background: #FAFAF7; border: 1px solid var(--borde); border-radius: 10px; padding: 1rem; display: flex; flex-direction: column; gap: 0.3rem; text-align: center; }
.val-total-label { font-size: 0.72rem; font-weight: 700; color: var(--texto-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.val-total-val { font-size: 1.3rem; font-weight: 800; }
.val-depto-card { border: 1px solid var(--borde); border-radius: 8px; margin-bottom: 0.5rem; overflow: hidden; }
.val-depto-header { display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem; cursor: pointer; background: #FAFAF7; flex-wrap: wrap; }
.val-depto-header:hover { background: #F0F0E8; }
.val-depto-nombre { flex: 1; font-weight: 700; font-size: 0.9rem; }
.val-depto-meta { font-size: 0.78rem; min-width: 60px; }
.val-col { font-weight: 700; font-size: 0.88rem; min-width: 90px; text-align: right; }
.val-toggle { font-size: 0.75rem; color: var(--texto-muted); }
.val-productos { border-top: 1px solid var(--borde); background: #FFFFFF; overflow-x: auto; }
.tabla-val { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.tabla-val th { font-size: 0.72rem; font-weight: 700; color: var(--texto-muted); text-align: left; padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--borde); white-space: nowrap; }
.tabla-val td { padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--borde-suave, #F0F0EC); }
.conteo-card { border: 1px solid var(--borde); border-radius: 8px; margin-bottom: 0.5rem; overflow: hidden; }
.conteo-header { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; cursor: pointer; background: #FAFAF7; flex-wrap: wrap; }
.conteo-header:hover { background: #F0F0E8; }
.conteo-fecha { font-size: 0.8rem; color: var(--texto-muted); min-width: 130px; }
.conteo-usuario { font-weight: 700; font-size: 0.85rem; color: #996600; min-width: 100px; }
.conteo-desc { flex: 1; font-size: 0.85rem; color: var(--texto-principal); }
.conteo-toggle { font-size: 0.75rem; color: var(--texto-muted); }
.conteo-detalle { padding: 0.75rem 1rem; border-top: 1px solid var(--borde); background: #FFFFFF; }
.tabla-conteo { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
.tabla-conteo th { font-size: 0.75rem; font-weight: 700; color: var(--texto-muted); text-align: left; padding: 0.3rem 0.5rem; border-bottom: 1px solid var(--borde); }
.tabla-conteo td { padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--borde-suave, #F0F0EC); }
.fila-pendiente td { background: #FFFBEB; }
.val-agrupacion { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; }
.val-agrupacion-label { font-size: 0.82rem; font-weight: 600; color: var(--texto-muted); }
.btn-agrup { padding: 0.35rem 0.85rem; border: 1px solid var(--borde); border-radius: 6px; font-size: 0.82rem; font-weight: 600; cursor: pointer; background: #FAFAF7; color: var(--texto-sec); }
.btn-agrup.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }
.val-imprimir-panel { background: #FAFAF7; border: 1px solid var(--borde); border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1.25rem; }
.val-imprimir-titulo { font-size: 0.85rem; font-weight: 700; margin: 0 0 0.75rem; color: var(--texto-principal); }
.val-imprimir-filtros { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.btn-imprimir-val { background: #1A1A1A; color: #FFCC00; border: none; border-radius: 8px; padding: 0.5rem 1rem; font-weight: 700; font-size: 0.85rem; cursor: pointer; }
.btn-imprimir-val:hover { background: #333; }
.input-field-sm { border: 1px solid var(--borde); border-radius: 6px; padding: 0.4rem 0.6rem; font-size: 0.85rem; }
.cierre-header  { display: flex; gap: 1.5rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }
.cierre-id      { color: var(--texto-principal); font-weight: 700; }
.cierre-fecha   { color: var(--texto-muted); font-size: 0.88rem; }
.cierre-usuario { color: var(--texto-muted); font-size: 0.88rem; }
.cierre-total   { margin-left: auto; font-weight: 600; }
.tabla-cierre-detalle { margin: 0; }

/* Clientes */
.niveles-resumen { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.nivel-chip      { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 20px; padding: 0.35rem 0.9rem; display: flex; gap: 0.5rem; align-items: center; }
.nivel-chip-nombre { color: var(--texto-sec); font-size: 0.82rem; }
.nivel-chip-cant   { color: var(--texto-principal); font-weight: 700; font-size: 0.88rem; }
.dos-columnas { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }

/* Misc */
.pos        { font-weight: 700; color: var(--texto-principal); }
.sub-titulo { color: var(--texto-principal); font-size: 0.9rem; font-weight: 700; margin: 0 0 0.75rem; }

/* Resumen del día */
.resumen-dos-col { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-top: 0.5rem; }
@media (max-width: 700px) { .resumen-dos-col { grid-template-columns: 1fr; } }

.metodo-resumen-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.6rem 0.9rem; border-radius: 8px; margin-bottom: 0.5rem;
  background: var(--fondo-sidebar); border: 1px solid var(--borde);
}
.metodo-resumen-info    { display: flex; flex-direction: column; gap: 0.1rem; }
.metodo-resumen-label   { font-weight: 600; font-size: 0.88rem; color: var(--texto-principal); }
.metodo-resumen-cuenta  { font-size: 0.76rem; color: var(--texto-muted); }
.metodo-resumen-montos  { display: flex; flex-direction: column; align-items: flex-end; gap: 0.1rem; }
.metodo-resumen-orig    { font-size: 0.95rem; font-weight: 700; color: var(--texto-principal); }
.metodo-resumen-usd     { font-size: 0.78rem; color: #16A34A; }
.metodo-resumen-cant    { font-size: 0.75rem; color: var(--texto-muted); }

.vendedor-resumen-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.6rem 0.9rem; border-radius: 8px; margin-bottom: 0.5rem;
  background: var(--fondo-sidebar); border: 1px solid var(--borde);
}
.vendedor-resumen-nombre { font-weight: 600; font-size: 0.88rem; color: var(--texto-principal); }
.vendedor-resumen-stats  { display: flex; flex-direction: column; align-items: flex-end; gap: 0.1rem; }
.vendedor-resumen-ventas { font-size: 0.78rem; color: var(--texto-muted); }
.vendedor-resumen-usd    { font-size: 0.95rem; font-weight: 700; }

.fila-precio-libre td  { background: #FFFDF0; }
.badge-precio-libre    { font-size: 0.75rem; margin-left: 0.3rem; opacity: 0.7; cursor: default; }
.txt-amarillo { color: #996600; }
.semaforo-cell { display: flex; align-items: center; gap: 0.3rem; }
.punto-rojo     { color: #DC2626; font-size: 1rem; }
.punto-amarillo { color: #D97706; font-size: 1rem; }
.punto-verde    { color: #16A34A; font-size: 1rem; }
.stock-num { font-size: 0.82rem; font-weight: 700; }
.dias-cob  { font-size: 0.72rem; color: var(--texto-muted); }
.badge-audit-ok       { background: #DCFCE7; color: #15803D; font-size: 0.72rem; padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 700; white-space: nowrap; }
.badge-audit-pendiente{ background: #FEF3C7; color: #92400E; font-size: 0.72rem; padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 700; white-space: nowrap; }
.badge-audit-sin      { background: #F1F5F9; color: #6B7280; font-size: 0.72rem; padding: 0.15rem 0.5rem; border-radius: 4px; white-space: nowrap; }

/* ── Facturas del día ── */
.facturas-dia { margin-top: 2rem; }
.seccion-titulo { font-size: 0.95rem; font-weight: 700; color: var(--texto-principal); margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem; }
.badge-count { background: #1A1A1A; color: #FFCC00; font-size: 0.72rem; font-weight: 700; padding: 0.1rem 0.5rem; border-radius: 10px; }
.factura-row { border: 1px solid var(--borde); border-radius: 8px; margin-bottom: 0.5rem; overflow: hidden; }
.factura-anulada { border-color: #DC2626; opacity: 0.75; background: #FEF2F2; }
.factura-header { display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem; cursor: pointer; background: #FAFAF7; flex-wrap: wrap; }
.factura-header:hover { background: #F0F0E8; }
.factura-id { font-weight: 700; color: #996600; font-size: 0.85rem; min-width: 50px; }
.factura-hora { font-size: 0.82rem; color: var(--texto-muted); min-width: 45px; }
.factura-usuario { font-size: 0.82rem; font-weight: 600; min-width: 80px; }
.factura-cliente { flex: 1; font-size: 0.85rem; color: var(--texto-sec); }
.factura-metodos { display: flex; flex-wrap: wrap; gap: 0.25rem; }
.factura-total { font-weight: 700; font-size: 0.95rem; min-width: 80px; text-align: right; }
.badge-anulada { background: #DC2626; color: white; font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 700; }
.factura-toggle { font-size: 0.75rem; color: var(--texto-muted); }
.factura-detalle { padding: 0.75rem 1rem; border-top: 1px solid var(--borde); background: #FFFFFF; }
.tabla-detalle { width: 100%; border-collapse: collapse; }
.tabla-detalle th { font-size: 0.75rem; font-weight: 700; color: var(--texto-muted); text-align: left; padding: 0.3rem 0.5rem; border-bottom: 1px solid var(--borde); }
.tabla-detalle td { font-size: 0.83rem; padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--borde-suave, #F0F0EC); }
.tabla-detalle tfoot td { border-bottom: none; padding-top: 0.5rem; }
.metodo-tag { display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.75rem; background: #F1F5F9; border-radius: 4px; padding: 0.15rem 0.5rem; margin: 0.1rem; }
.cuenta-tag { color: #15803D; font-weight: 600; }
.monto-tag { color: #1A1A1A; font-weight: 700; }

/* Nombre clickeable en tabla */
.nombre-clickeable { font-weight: 600; cursor: pointer; text-decoration: underline; text-decoration-style: dotted; text-underline-offset: 2px; }
.nombre-clickeable:hover { color: #996600; }

/* Panel lateral */
.panel-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 200; display: flex; justify-content: flex-end; }
.panel-lateral {
  width: 400px; max-width: 95vw; background: #FFFFFF;
  height: 100%; overflow-y: auto; padding: 1.5rem;
  box-shadow: -4px 0 20px rgba(0,0,0,0.15);
  animation: slideInPanel 0.2s ease;
}
@keyframes slideInPanel {
  from { transform: translateX(100%); }
  to   { transform: translateX(0); }
}
.panel-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; gap: 0.75rem; }
.panel-nombre { font-size: 1rem; font-weight: 700; color: var(--texto-principal); line-height: 1.3; flex: 1; }
.panel-cerrar { background: transparent; border: 1px solid var(--borde); border-radius: 6px; padding: 0.2rem 0.6rem; cursor: pointer; font-size: 0.9rem; color: var(--texto-sec); flex-shrink: 0; }
.panel-cerrar:hover { background: var(--fondo-sidebar); }
.panel-kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem; }
.panel-kpi { background: var(--fondo-sidebar); border-radius: 8px; padding: 0.75rem; border: 1px solid var(--borde); display: flex; flex-direction: column; gap: 0.2rem; }
.panel-kpi-label { font-size: 0.7rem; color: var(--texto-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.04em; }
.panel-kpi-valor { font-size: 1.2rem; font-weight: 700; color: var(--texto-principal); }
.panel-costos { display: flex; gap: 0; margin-bottom: 1.25rem; border: 1px solid var(--borde); border-radius: 8px; overflow: hidden; }
.panel-costo-item { flex: 1; display: flex; flex-direction: column; gap: 0.2rem; align-items: center; padding: 0.75rem 0.5rem; border-right: 1px solid var(--borde); }
.panel-costo-item:last-child { border-right: none; }
.panel-costo-item span:first-child { font-size: 0.7rem; color: var(--texto-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
.panel-costo-item span:last-child { font-size: 0.92rem; font-weight: 700; }
.panel-seccion-titulo { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: var(--texto-muted); letter-spacing: 0.05em; margin-bottom: 0.6rem; }
.panel-cargando { text-align: center; color: var(--texto-muted); font-size: 0.85rem; padding: 1.5rem; }
.panel-barras { display: flex; align-items: flex-end; gap: 3px; height: 110px; margin-bottom: 1.25rem; overflow-x: auto; padding-bottom: 0.25rem; }
.panel-barra-wrap { display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 8px; flex: 1; }
.panel-barra-col { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 88px; }
.panel-barra-val { font-size: 0.52rem; color: var(--texto-muted); line-height: 1; margin-bottom: 1px; }
.panel-barra { width: 100%; min-height: 1px; border-radius: 2px 2px 0 0; transition: height 0.25s ease; }
.panel-barra-activa { background: #FFCC00; }
.panel-barra-vacia  { background: #E5E5E0; }
.panel-barra-dia { font-size: 0.48rem; color: var(--texto-muted); writing-mode: vertical-rl; transform: rotate(180deg); line-height: 1; }
.panel-btn-repo { width: 100%; background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600; margin-bottom: 1rem; }
.panel-btn-repo:hover { background: #333; }
.badge-repo-flotante { position: fixed; bottom: 2rem; right: 2rem; background: #1A1A1A; color: #FFCC00; font-weight: 700; font-size: 0.82rem; padding: 0.6rem 1.25rem; border-radius: 20px; cursor: pointer; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.25); }
.badge-repo-flotante:hover { background: #333; }

/* Panel lista de reposición */
.panel-body { display: flex; flex-direction: column; }
.repos-item { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid var(--borde-suave, #F0F0EC); gap: 0.5rem; }
.repos-item-info { display: flex; align-items: center; gap: 0.5rem; flex: 1; min-width: 0; }
.repos-item-detalle { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.repos-nombre { font-size: 0.85rem; font-weight: 600; color: #1A1A1A; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.repos-meta { font-size: 0.72rem; color: var(--texto-muted); }
.repos-item-acciones { display: flex; align-items: center; gap: 0.4rem; }
.input-repos-cant { width: 65px; padding: 0.3rem 0.4rem; border: 1px solid var(--borde); border-radius: 5px; font-size: 0.82rem; text-align: center; }
.btn-quitar-repos { background: none; border: none; color: #DC2626; cursor: pointer; font-size: 0.9rem; padding: 0.2rem; }
.repos-resumen { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--borde); }
.repos-resumen-txt { font-weight: 700; font-size: 0.9rem; margin: 0; }
.repos-hint { font-size: 0.75rem; color: var(--texto-muted); margin: 0.25rem 0 0; font-style: italic; }
.repos-acciones { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 1rem; }
.btn-copiar-repos { background: #F1F5F9; border: 1px solid var(--borde); border-radius: 8px; padding: 0.6rem; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-copiar-repos:hover { background: #E2E8F0; }
.btn-whatsapp-repos { background: #25D366; color: white; border: none; border-radius: 8px; padding: 0.6rem; font-weight: 700; cursor: pointer; font-size: 0.85rem; }
.btn-whatsapp-repos:hover { background: #1FB957; }
.btn-limpiar-repos { background: none; border: 1px solid #DC2626; color: #DC2626; border-radius: 8px; padding: 0.6rem; font-weight: 600; cursor: pointer; font-size: 0.85rem; }
.btn-limpiar-repos:hover { background: #DC2626; color: white; }
</style>
