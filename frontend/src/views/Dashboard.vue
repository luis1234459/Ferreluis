<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Panel principal</h1>
        <span class="fecha-hoy">{{ fechaHoy }}</span>
      </div>

      <div class="contenido-inner">

        <!-- Skeleton -->
        <template v-if="cargando">
          <div class="kpis-grid-6">
            <div v-for="i in 6" :key="i" class="kpi-card skeleton"></div>
          </div>
          <div class="kpis-grid-4" style="margin-top:1rem">
            <div v-for="i in 4" :key="i" class="kpi-card skeleton"></div>
          </div>
        </template>

        <template v-else>
          <!-- Tasa BCV bar -->
          <div class="tasa-bar">
            <span class="tasa-item">
              BCV: <strong>{{ d.tasa_bcv ? d.tasa_bcv.toFixed(2) : '—' }} Bs/$</strong>
            </span>
            <template v-if="mostrarBinance">
              <span class="tasa-sep">|</span>
              <span class="tasa-item">
                Binance: <strong>{{ d.tasa_binance ? d.tasa_binance.toFixed(2) : '—' }} Bs/$</strong>
              </span>
              <span class="tasa-sep">|</span>
              <span class="tasa-item">
                Factor: <strong>{{ d.factor ? d.factor.toFixed(4) : '—' }}</strong>
              </span>
            </template>
          </div>

          <!-- Alertas -->
          <div class="alertas-box" v-if="d.alertas && d.alertas.length > 0">
            <span class="alerta-icon">⚠</span>
            <ul class="alertas-list">
              <li v-for="(a, i) in d.alertas" :key="i"
                :class="'alerta-' + a.tipo">{{ a.mensaje }}</li>
            </ul>
          </div>

          <!-- ══ PEDIDOS EN CAMINO (admin + vendedor) ══ -->
          <div class="pedidos-camino" v-if="pedidosEnCamino.length > 0">
            <h3 class="seccion-titulo">
              🚚 Pedidos en camino
              <span class="badge-count">{{ pedidosEnCamino.length }}</span>
            </h3>
            <div v-for="p in pedidosEnCamino" :key="p.id" class="pedido-card">
              <div class="pedido-header"
                @click="ordenExpandida = ordenExpandida === p.id ? null : p.id">
                <span class="pedido-num">{{ p.numero }}</span>
                <span class="pedido-prov">{{ p.proveedor }}</span>
                <span :class="['pedido-estado', p.estado === 'aprobada' ? 'estado-aprobada' : 'estado-parcial']">
                  {{ p.estado === 'aprobada' ? 'En camino' : 'Recibido parcial' }}
                </span>
                <span class="pedido-fecha">{{ p.fecha }}</span>
                <span class="pedido-total">${{ p.total.toFixed(2) }}</span>
                <span class="pedido-toggle">{{ ordenExpandida === p.id ? '▲' : '▼' }}</span>
              </div>
              <div v-if="ordenExpandida === p.id" class="pedido-detalle">
                <table class="tabla-pedido">
                  <thead>
                    <tr><th>Producto</th><th>Cantidad</th><th>Precio USD</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="(prod, i) in p.productos" :key="i">
                      <td>{{ prod.nombre }}</td>
                      <td style="text-align:center">{{ prod.cantidad }}</td>
                      <td>${{ prod.precio.toFixed(2) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- ══ DASHBOARD ADMIN ══ -->
          <template v-if="esAdmin">

          <!-- KPIs ventas (6) -->
          <div class="seccion-label">Ventas hoy</div>
          <div class="kpis-grid-6">
            <div class="kpi-card">
              <p class="kpi-label">Transacciones</p>
              <p class="kpi-valor">{{ d.ventas_hoy }}</p>
            </div>
            <div class="kpi-card">
              <p class="kpi-label">Total USD</p>
              <p class="kpi-valor txt-verde">${{ fmt(d.total_hoy_usd) }}</p>
            </div>
            <div class="kpi-card">
              <p class="kpi-label">Total Bs</p>
              <p class="kpi-valor">Bs.{{ fmt(d.total_hoy_bs) }}</p>
            </div>
            <div class="kpi-card">
              <p class="kpi-label">Ticket promedio</p>
              <p class="kpi-valor">${{ fmt(d.ticket_promedio_usd) }}</p>
            </div>
            <div class="kpi-card">
              <p class="kpi-label">Unidades vendidas</p>
              <p class="kpi-valor">{{ d.unidades_vendidas_hoy }}</p>
            </div>
            <div class="kpi-card">
              <p class="kpi-label">Clientes atendidos</p>
              <p class="kpi-valor">{{ d.clientes_hoy }}</p>
            </div>
          </div>

          <!-- KPIs inventario (4) -->
          <div class="seccion-label" style="margin-top:1.5rem">Inventario</div>
          <div class="kpis-grid-4">
            <div class="kpi-card">
              <p class="kpi-label">Total productos</p>
              <p class="kpi-valor">{{ d.total_productos }}</p>
            </div>
            <div class="kpi-card">
              <p class="kpi-label">Stock bajo (&lt; 5)</p>
              <p class="kpi-valor" :class="d.productos_stock_bajo > 0 ? 'txt-amarillo' : ''">{{ d.productos_stock_bajo }}</p>
            </div>
            <div class="kpi-card">
              <p class="kpi-label">Sin stock</p>
              <p class="kpi-valor" :class="d.productos_sin_stock > 0 ? 'txt-rojo' : ''">{{ d.productos_sin_stock }}</p>
            </div>
            <div class="kpi-card">
              <p class="kpi-label">Valor inventario</p>
              <p class="kpi-valor">${{ fmt(d.valor_inventario_usd) }}</p>
            </div>
          </div>

          <!-- KPIs comisiones -->
          <div class="kpis-grid-2" style="margin-top:1rem">
            <div class="kpi-card">
              <p class="kpi-label">Comisiones generadas hoy</p>
              <p class="kpi-valor">${{ fmt(d.comision_total_hoy) }}</p>
            </div>
            <div class="kpi-card">
              <p class="kpi-label">Comisiones pendientes de pago</p>
              <p class="kpi-valor" :class="d.comisiones_pendientes_pago > 0 ? 'txt-amarillo' : ''">${{ fmt(d.comisiones_pendientes_pago) }}</p>
            </div>
          </div>

          <!-- Dos columnas: últimas ventas + productos alerta -->
          <div class="dos-col" style="margin-top:1.5rem">
            <!-- Últimas ventas del día -->
            <div class="col-panel">
              <h2 class="panel-titulo">Últimas ventas del día</h2>
              <div class="tabla-container">
                <table>
                  <thead>
                    <tr><th>#</th><th>Usuario</th><th>Total</th><th>Estado</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="v in d.ultimas_ventas" :key="v.id">
                      <td class="txt-muted">#{{ v.id }}</td>
                      <td>{{ v.usuario }}</td>
                      <td :class="v.moneda_venta === 'USD' ? 'txt-verde' : ''">
                        {{ v.moneda_venta === 'USD' ? '$' : 'Bs.' }}{{ fmt(v.total) }}
                      </td>
                      <td><span :class="'badge badge-' + v.estado">{{ v.estado }}</span></td>
                    </tr>
                    <tr v-if="!d.ultimas_ventas || d.ultimas_ventas.length === 0">
                      <td colspan="4" class="sin-datos">Sin ventas hoy</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Productos con stock bajo -->
            <div class="col-panel">
              <h2 class="panel-titulo">Productos con stock bajo</h2>
              <div class="tabla-container">
                <table>
                  <thead>
                    <tr><th>Producto</th><th>Categoría</th><th>Stock</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="p in d.productos_alerta" :key="p.id"
                      :class="p.stock <= 0 ? 'fila-sin-stock' : 'fila-stock-bajo'">
                      <td>{{ p.nombre }}</td>
                      <td class="txt-muted">{{ p.categoria }}</td>
                      <td :class="p.stock <= 0 ? 'txt-rojo' : 'txt-amarillo'">{{ p.stock }}</td>
                    </tr>
                    <tr v-if="!d.productos_alerta || d.productos_alerta.length === 0">
                      <td colspan="3" class="sin-datos">Sin alertas de stock</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- ══ WIDGET LIQUIDEZ PRUDENTE ══ -->
          <div class="liquidez-widget" style="margin-top:1.5rem">
            <div class="liquidez-header">
              <h2 class="panel-titulo" style="margin:0">💧 Liquidez prudente — próximos 10 días hábiles</h2>
              <div class="liquidez-controles">
                <label style="font-size:0.8rem;color:var(--texto-sec)">Colchón:</label>
                <input type="number" v-model.number="colchonPct" min="5" max="50" step="1"
                  class="liquidez-input-pct" @change="cargarLiquidez" />
                <span style="font-size:0.8rem;color:var(--texto-sec)">%</span>
                <button class="btn-toggle-capa"
                  :class="{ activo: capaActiva === 'conservadora' }"
                  @click="capaActiva = 'conservadora'">Conservadora</button>
                <button class="btn-toggle-capa"
                  :class="{ activo: capaActiva === 'realista' }"
                  @click="capaActiva = 'realista'">Realista</button>
                <button class="btn-reload-liquidez" @click="cargarLiquidez"
                  :disabled="cargandoLiquidez">↻</button>
              </div>
            </div>

            <div v-if="cargandoLiquidez" class="liquidez-loading">Calculando...</div>

            <div v-else-if="liquidez" class="liquidez-body">
              <!-- Número principal -->
              <div class="liquidez-principal">
                <div class="liquidez-label">Mantener en caja ({{ capaActiva }})</div>
                <div class="liquidez-monto">${{ fmt(liquidez[capaActiva].liquidez) }}</div>
                <div class="liquidez-sub">
                  {{ capaActiva === 'realista' ? 'Con crédito real y abonos proyectados' : 'Con crédito formal, deuda total' }}
                </div>
              </div>

              <!-- Desglose -->
              <div class="liquidez-desglose">
                <div class="liquidez-linea">
                  <span>Deuda proveedores</span>
                  <span class="txt-danger">${{ fmt(liquidez[capaActiva].deuda_proveedores) }}</span>
                </div>
                <div v-if="capaActiva === 'realista' && liquidez.realista.abonos_proyectados > 0" class="liquidez-linea sub">
                  <span class="txt-muted">  − Abonos proyectados 10d</span>
                  <span class="txt-success">−${{ fmt(liquidez.realista.abonos_proyectados) }}</span>
                </div>
                <div class="liquidez-linea">
                  <span>+ Ventas proyectadas 10d</span>
                  <span>${{ fmt(liquidez[capaActiva].proyeccion_ventas_10d) }}</span>
                </div>
                <div class="liquidez-linea">
                  <span>− Crédito proveedores ({{ liquidez[capaActiva].dias_credito_usados }}d prom.)</span>
                  <span class="txt-success">−${{ fmt(liquidez[capaActiva].credito_proveedores) }}</span>
                </div>
                <div class="liquidez-linea colchon">
                  <span>+ Colchón {{ colchonPct }}%</span>
                  <span>${{ fmt(liquidez[capaActiva].colchon) }}</span>
                </div>
                <div class="liquidez-linea total">
                  <span>= Liquidez prudente</span>
                  <span>${{ fmt(liquidez[capaActiva].liquidez) }}</span>
                </div>
              </div>

              <!-- Días de crédito real por proveedor -->
              <div class="liquidez-creditos">
                <div class="liquidez-creditos-titulo">
                  Días de crédito por proveedor
                  <span class="txt-muted" style="font-size:0.75rem">(edita el «real» para ajustar el cálculo)</span>
                </div>
                <div v-for="d in liquidez.detalle_proveedores" :key="d.proveedor_id"
                  class="liquidez-prov-row">
                  <span class="lp-nombre">{{ d.proveedor }}</span>
                  <span class="lp-saldo txt-danger">${{ fmt(d.saldo) }}</span>
                  <span class="lp-label txt-muted">Formal:</span>
                  <span class="lp-dias">{{ d.dias_credito_formal }}d</span>
                  <span class="lp-label txt-muted">Real:</span>
                  <input type="number" :value="d.dias_credito_real"
                    class="lp-input-dias"
                    min="0" max="365"
                    @change="actualizarCreditoReal(d.proveedor_id, $event.target.value)" />
                  <span class="lp-label txt-muted">d</span>
                  <span v-if="d.abono_proyectado_10d > 0" class="lp-abono txt-success">
                    −${{ fmt(d.abono_proyectado_10d) }} abono est.
                  </span>
                </div>
              </div>
            </div>

            <div v-else class="liquidez-loading txt-muted">Sin datos suficientes para calcular</div>
          </div>
          <!-- fin WIDGET LIQUIDEZ -->

          </template>
          <!-- fin DASHBOARD ADMIN -->

          <!-- ══ DASHBOARD VENDEDOR ══ -->
          <template v-if="esVendedor">

            <!-- KPIs del vendedor -->
            <div class="seccion-label">Mis ventas hoy</div>
            <div class="kpis-grid-3">
              <div class="kpi-card">
                <p class="kpi-label">Transacciones</p>
                <p class="kpi-valor">{{ d.ventas_hoy }}</p>
              </div>
              <div class="kpi-card">
                <p class="kpi-label">Total USD</p>
                <p class="kpi-valor txt-verde">${{ fmt(d.total_hoy_usd) }}</p>
              </div>
              <div class="kpi-card">
                <p class="kpi-label">Unidades vendidas</p>
                <p class="kpi-valor">{{ d.unidades_vendidas_hoy }}</p>
              </div>
            </div>

            <!-- Dos columnas: compras recibidas + precios actualizados -->
            <div class="dos-col" style="margin-top:1.5rem">

              <!-- Últimas compras recibidas -->
              <div class="col-panel">
                <h2 class="panel-titulo">📦 Últimas compras recibidas</h2>
                <div class="tabla-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Producto</th>
                        <th>Depto.</th>
                        <th>Categoría</th>
                        <th>Precio $</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(c, i) in d.ultimas_compras" :key="i">
                        <td style="font-weight:600">{{ c.producto }}</td>
                        <td class="txt-muted">{{ c.departamento }}</td>
                        <td class="txt-muted">{{ c.categoria }}</td>
                        <td class="txt-verde">${{ fmt(c.precio_usd) }}</td>
                      </tr>
                      <tr v-if="!d.ultimas_compras || d.ultimas_compras.length === 0">
                        <td colspan="4" class="sin-datos">Sin compras recientes</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Productos con precio actualizado -->
              <div class="col-panel">
                <h2 class="panel-titulo">📈 Precios actualizados</h2>
                <div class="tabla-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Producto</th>
                        <th>Depto.</th>
                        <th>Precio actual $</th>
                        <th>Fecha</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(p, i) in d.productos_precio_subio" :key="i">
                        <td style="font-weight:600">{{ p.producto }}</td>
                        <td class="txt-muted">{{ p.departamento }}</td>
                        <td class="txt-amarillo">${{ fmt(p.precio_actual) }}</td>
                        <td class="txt-muted">{{ fmtFecha(p.fecha) }}</td>
                      </tr>
                      <tr v-if="!d.productos_precio_subio || d.productos_precio_subio.length === 0">
                        <td colspan="4" class="sin-datos">Sin cambios de precio recientes</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Últimas ventas del día (vendedor) -->
            <div class="col-panel" style="margin-top:1rem">
              <h2 class="panel-titulo">Últimas ventas del día</h2>
              <div class="tabla-container">
                <table>
                  <thead>
                    <tr><th>#</th><th>Total</th><th>Estado</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="v in d.ultimas_ventas" :key="v.id">
                      <td class="txt-muted">#{{ v.id }}</td>
                      <td :class="v.moneda_venta === 'USD' ? 'txt-verde' : ''">
                        {{ v.moneda_venta === 'USD' ? '$' : 'Bs.' }}{{ fmt(v.total) }}
                      </td>
                      <td>
                        <span :class="'badge badge-' + v.estado">{{ v.estado }}</span>
                      </td>
                    </tr>
                    <tr v-if="!d.ultimas_ventas || d.ultimas_ventas.length === 0">
                      <td colspan="3" class="sin-datos">Sin ventas hoy</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

          </template>
          <!-- fin DASHBOARD VENDEDOR -->

        </template>
      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'Dashboard',
  data() {
    return {
      usuario:      JSON.parse(localStorage.getItem('usuario') || '{}'),
      tipoPrecio:   localStorage.getItem('tipoPrecio') || 'referencial',
      cargando:     true,
      // Liquidez prudente
      liquidez:         null,
      cargandoLiquidez: false,
      colchonPct:       18,
      capaActiva:       'realista',
      d: {
        ventas_hoy: 0, total_hoy_usd: 0, total_hoy_bs: 0,
        ticket_promedio_usd: 0, unidades_vendidas_hoy: 0, clientes_hoy: 0,
        total_productos: 0, productos_stock_bajo: 0, productos_sin_stock: 0,
        valor_inventario_usd: 0, comision_total_hoy: 0, comisiones_pendientes_pago: 0,
        tasa_bcv: 0, tasa_binance: 0, factor: 1,
        alertas: [], ultimas_ventas: [], productos_alerta: [], facturas_pendientes: [],
        ultimas_compras: [], productos_precio_subio: [],
      },
      pedidosEnCamino: [],
      ordenExpandida:  null,
      _timer: null,
    }
  },
  computed: {
    esAdmin() { return this.usuario.rol === 'admin' },
    esVendedor() { return this.usuario.rol !== 'admin' },
    mostrarBinance() { return this.esAdmin || this.tipoPrecio === 'base' },
    tienePermiso() {
      return (modulo) => {
        if (this.usuario.rol === 'admin') return true
        const p = this.usuario.permisos
        if (p == null) return true
        return Array.isArray(p) ? p.includes(modulo) : true
      }
    },
    fechaHoy() {
      return new Date().toLocaleDateString('es-VE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
    },
  },
  async mounted() {
    await this.cargar()
    if (this.usuario.rol === 'admin') this.cargarLiquidez()
    this._timer = setInterval(this.cargar, 5 * 60 * 1000)
  },
  beforeUnmount() {
    if (this._timer) clearInterval(this._timer)
  },
  methods: {
    async cargar() {
      try {
        const res = await axios.get('/dashboard/resumen')
        this.d = res.data
        this.pedidosEnCamino = res.data.pedidos_en_camino || []
      } catch (e) {
        console.error('Error cargando dashboard', e)
      } finally {
        this.cargando = false
      }
    },
    async cargarLiquidez() {
      this.cargandoLiquidez = true
      try {
        const res = await axios.get('/reportes/liquidez-prudente', {
          params: { colchon_pct: this.colchonPct / 100 }
        })
        this.liquidez = res.data
      } catch (e) {
        console.error('Error cargando liquidez', e)
      } finally {
        this.cargandoLiquidez = false
      }
    },
    async actualizarCreditoReal(proveedorId, dias) {
      try {
        await axios.patch(`/reportes/liquidez-prudente/credito-real/${proveedorId}`, {
          dias_credito_real: parseInt(dias) || 0
        })
        await this.cargarLiquidez()
      } catch (e) {
        console.error('Error actualizando crédito real', e)
      }
    },
    fmt(n) { return n != null ? Number(n).toFixed(2) : '0.00' },
    fmtFecha(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleDateString('es-VE', { day: '2-digit', month: '2-digit' })
    },
    salir() { localStorage.removeItem('usuario'); this.$router.push('/login') },
  },
}
</script>

<style scoped>
.top-bar { display: flex; align-items: center; justify-content: space-between; }
.fecha-hoy { color: var(--texto-sec); font-size: 0.85rem; }

/* Tasa bar */
.tasa-bar {
  display: flex; align-items: center; gap: 0.5rem;
  background: var(--fondo-sidebar); border: 1px solid var(--borde);
  border-radius: 10px; padding: 0.55rem 1rem; margin-bottom: 1rem;
  font-size: 0.85rem; color: var(--texto-sec); flex-wrap: wrap;
}
.tasa-item strong { color: var(--texto-principal); }
.tasa-sep { color: var(--borde); }

/* Alertas */
.alertas-box {
  display: flex; align-items: flex-start; gap: 0.75rem;
  background: #FFCC0022; border: 1px solid #FFCC0066;
  border-radius: 10px; padding: 0.75rem 1rem; margin-bottom: 1rem;
}
.alerta-icon { font-size: 1.1rem; color: #996600; flex-shrink: 0; margin-top: 1px; }
.alertas-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.25rem; }
.alertas-list li { font-size: 0.85rem; color: #665500; }

/* Labels de sección */
.seccion-label { color: var(--texto-sec); font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.6rem; }

/* KPI grids */
.kpis-grid-6 { display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.85rem; }
.kpis-grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.85rem; }
.kpis-grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.85rem; }

@media (max-width: 1200px) {
  .kpis-grid-6 { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 900px) {
  .kpis-grid-6, .kpis-grid-4 { grid-template-columns: repeat(2, 1fr); }
}

/* Skeleton */
.skeleton { background: linear-gradient(90deg, var(--borde-suave) 25%, var(--borde) 50%, var(--borde-suave) 75%); background-size: 200% 100%; animation: shimmer 1.4s infinite; min-height: 80px; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* Dos columnas */
.dos-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 900px) { .dos-col { grid-template-columns: 1fr; } }

.col-panel { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 14px; padding: 1.25rem; }
.panel-titulo { color: var(--texto-principal); font-size: 0.9rem; font-weight: 700; margin: 0 0 0.85rem; }

/* Filas coloreadas */
.fila-sin-stock  td { background: #DC262608; }
.fila-stock-bajo td { background: #FFCC0008; }
.fila-vencida    td { background: #DC262610; }
.fila-proxima    td { background: #FFCC0018; }

/* Facturas */
.seccion-facturas { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 14px; padding: 1.25rem; }

.badge-dias { font-size: 0.78rem; font-weight: 600; padding: 0.18rem 0.5rem; border-radius: 4px; }
.badge-dias-vencida { background: #DC26261A; color: #DC2626; }
.badge-dias-proxima { background: #FFCC0033; color: #996600; }
.badge-dias-ok      { background: #16A34A1A; color: #16A34A; }

.btn-pagar-factura {
  background: #1A1A1A; color: #FFCC00; border: none;
  padding: 0.3rem 0.7rem; border-radius: 6px; cursor: pointer;
  font-size: 0.8rem; font-weight: 600;
}
.btn-pagar-factura:disabled { opacity: 0.4; cursor: not-allowed; }

.txt-amarillo { color: #996600; }

.kpis-grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.85rem; }
@media (max-width: 700px) { .kpis-grid-3 { grid-template-columns: 1fr 1fr; } }

/* Pedidos en camino */
.pedidos-camino { margin-bottom: 1.5rem; }
.seccion-titulo { font-size: 0.95rem; font-weight: 700; color: var(--texto-principal); margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem; }
.badge-count { background: #1A1A1A; color: #FFCC00; font-size: 0.72rem; font-weight: 700; padding: 0.1rem 0.5rem; border-radius: 10px; }
.pedido-card { border: 1px solid var(--borde); border-radius: 8px; margin-bottom: 0.5rem; overflow: hidden; }
.pedido-header { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; cursor: pointer; background: #FAFAF7; flex-wrap: wrap; }
.pedido-header:hover { background: #F0F0E8; }
.pedido-num { font-weight: 700; color: #996600; font-size: 0.85rem; min-width: 80px; }
.pedido-prov { flex: 1; font-size: 0.85rem; font-weight: 600; color: var(--texto-principal); }
.pedido-estado { font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 4px; }
.estado-aprobada { background: #DCFCE7; color: #15803D; }
.estado-parcial { background: #FEF9C3; color: #854D0E; }
.pedido-fecha { font-size: 0.78rem; color: var(--texto-muted); }
.pedido-total { font-weight: 700; font-size: 0.9rem; color: var(--texto-principal); }
.pedido-toggle { font-size: 0.75rem; color: var(--texto-muted); }
.pedido-detalle { padding: 0.75rem 1rem; border-top: 1px solid var(--borde); background: #FFFFFF; }
.tabla-pedido { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
.tabla-pedido th { font-size: 0.75rem; font-weight: 700; color: var(--texto-muted); text-align: left; padding: 0.3rem 0.5rem; border-bottom: 1px solid var(--borde); }
.tabla-pedido td { padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--borde-suave, #F0F0EC); }
/* ── Widget Liquidez Prudente ── */
.liquidez-widget { background:var(--fondo-card); border:1px solid var(--borde); border-radius:10px; padding:1.2rem 1.4rem; }
.liquidez-header { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.6rem; margin-bottom:1rem; }
.liquidez-controles { display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap; }
.liquidez-input-pct { width:52px; text-align:center; border:1px solid var(--borde); border-radius:5px; padding:3px 5px; font-size:0.85rem; background:var(--fondo-input); color:var(--texto-principal); }
.btn-toggle-capa { padding:4px 12px; border:1px solid var(--borde); border-radius:6px; background:var(--fondo-app); color:var(--texto-sec); cursor:pointer; font-size:0.8rem; }
.btn-toggle-capa.activo { background:var(--amarillo); color:#1A1A1A; border-color:var(--amarillo); font-weight:600; }
.btn-reload-liquidez { padding:4px 10px; border:1px solid var(--borde); border-radius:6px; background:transparent; cursor:pointer; font-size:1rem; color:var(--texto-sec); }
.liquidez-loading { text-align:center; padding:1.5rem; color:var(--texto-muted); font-size:0.9rem; }
.liquidez-body { display:grid; grid-template-columns:200px 1fr 1fr; gap:1.5rem; }
@media (max-width:900px) { .liquidez-body { grid-template-columns:1fr; } }
.liquidez-principal { background:var(--fondo-app); border-radius:8px; padding:1rem; text-align:center; border:1px solid var(--borde); }
.liquidez-label { font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:var(--texto-muted); margin-bottom:0.4rem; }
.liquidez-monto { font-size:2rem; font-weight:700; color:var(--texto-principal); }
.liquidez-sub { font-size:0.75rem; color:var(--texto-muted); margin-top:0.3rem; }
.liquidez-desglose { display:flex; flex-direction:column; gap:4px; }
.liquidez-linea { display:flex; justify-content:space-between; font-size:0.85rem; padding:4px 0; border-bottom:0.5px solid var(--borde-suave); }
.liquidez-linea.sub { padding-left:1rem; font-size:0.8rem; }
.liquidez-linea.colchon { color:var(--texto-sec); border-top:1px dashed var(--borde); margin-top:4px; }
.liquidez-linea.total { font-weight:700; font-size:0.95rem; border-top:2px solid var(--borde); margin-top:4px; padding-top:6px; }
.liquidez-creditos { display:flex; flex-direction:column; gap:6px; }
.liquidez-creditos-titulo { font-size:0.78rem; font-weight:600; color:var(--texto-sec); margin-bottom:4px; }
.liquidez-prov-row { display:flex; align-items:center; gap:6px; font-size:0.8rem; flex-wrap:wrap; }
.lp-nombre { flex:1; min-width:100px; font-weight:500; }
.lp-saldo { min-width:60px; text-align:right; }
.lp-label { color:var(--texto-muted); }
.lp-dias { min-width:28px; }
.lp-input-dias { width:48px; text-align:center; border:1px solid var(--borde); border-radius:4px; padding:2px 4px; font-size:0.8rem; background:var(--fondo-input); color:var(--texto-principal); }
.lp-input-dias:focus { border-color:var(--amarillo); outline:none; }
.lp-abono { font-size:0.75rem; margin-left:auto; }
</style>
