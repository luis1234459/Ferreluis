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
              <label>Desde</label>
              <input type="date" v-model="desde" />
            </div>
            <div class="field-inline">
              <label>Hasta</label>
              <input type="date" v-model="hasta" />
            </div>
            <button class="btn-filtrar" @click="cargar">Filtrar</button>
            <button class="btn-rapido" @click="setHoy">Hoy</button>
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
  'otros-cierres':           '/reportes/cierre/comparativo',
  'otros-clientes':          '/reportes/clientes/resumen',
}

const CON_FILTROS = new Set([
  'ventas-resumen_dia', 'ventas-periodo', 'ventas-metodos', 'ventas-departamento',
  'ventas-proveedor', 'ventas-pareto', 'ventas-vendedor', 'ventas-top',
  'compras-proveedor', 'compras-departamento',
  'inventario-pareto', 'inventario-rotacion', 'otros-clientes',
])

export default {
  components: { AppSidebar },
  name: 'Reportes',
  data() {
    return {
      usuario:  JSON.parse(localStorage.getItem('usuario') || '{}'),
      tabMain:  'ventas',
      tabSub:   'resumen_dia',
      datos:    null,
      cargando: false,
      desde:    '',
      hasta:    '',
      MAIN_TABS: [
        { key: 'ventas',     label: 'Ventas' },
        { key: 'compras',    label: 'Compras' },
        { key: 'inventario', label: 'Inventario' },
        { key: 'otros',      label: 'Otros' },
      ],
    }
  },
  computed: {
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
      await this.cargar()
    },
    async cargar() {
      const url = URL_MAP[this.tabKey]
      if (!url) return
      this.cargando = true
      try {
        const params = {}
        if (this.tieneFiltros) {
          if (this.desde) params.desde = this.desde
          if (this.hasta) params.hasta = this.hasta
        }
        const res  = await axios.get(url, { params })
        this.datos = res.data
      } catch (e) {
        console.error('Error cargando reporte', e)
        this.datos = null
      } finally {
        this.cargando = false
      }
    },
    limpiarFiltros() { this.desde = ''; this.hasta = ''; this.cargar() },
    setHoy()   {
      const h = new Date().toISOString().slice(0, 10)
      this.desde = h; this.hasta = h; this.cargar()
    },
    setSemana() {
      const hoy = new Date()
      const lunes = new Date(hoy)
      lunes.setDate(hoy.getDate() - ((hoy.getDay() + 6) % 7))
      this.desde = lunes.toISOString().slice(0, 10)
      this.hasta = hoy.toISOString().slice(0, 10)
      this.cargar()
    },
    setMes() {
      const hoy = new Date()
      this.desde = `${hoy.getFullYear()}-${String(hoy.getMonth()+1).padStart(2,'0')}-01`
      this.hasta = hoy.toISOString().slice(0, 10)
      this.cargar()
    },
    setAnio() {
      const hoy = new Date()
      this.desde = `${hoy.getFullYear()}-01-01`
      this.hasta = hoy.toISOString().slice(0, 10)
      this.cargar()
    },
    exportar() { alert('Función disponible próximamente') },
    labelMetodo(m) { return LABELS_METODO[m] || m },
    formatFecha(iso) { return iso ? new Date(iso).toLocaleString('es-VE') : '—' },
    salir() { localStorage.removeItem('usuario'); this.$router.push('/login') },
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
</style>
