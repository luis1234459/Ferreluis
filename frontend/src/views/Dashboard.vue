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

          <!-- Facturas de proveedores -->
          <div v-if="d.facturas_pendientes && d.facturas_pendientes.length > 0"
            class="seccion-facturas" style="margin-top:1.5rem">
            <h2 class="panel-titulo">Facturas de proveedores pendientes</h2>
            <div class="tabla-container">
              <table>
                <thead>
                  <tr><th>Proveedor</th><th>Factura</th><th>Orden</th><th>Monto</th><th>Vencimiento</th><th>Días</th><th></th></tr>
                </thead>
                <tbody>
                  <tr v-for="f in d.facturas_pendientes" :key="f.recepcion_id"
                    :class="'fila-' + f.alerta">
                    <td style="font-weight:600">{{ f.proveedor }}</td>
                    <td>{{ f.numero_factura }}</td>
                    <td class="txt-muted">{{ f.orden }}</td>
                    <td>${{ fmt(f.monto_factura) }}</td>
                    <td>{{ f.fecha_vencimiento || '—' }}</td>
                    <td>
                      <span :class="'badge-dias badge-dias-' + f.alerta">
                        {{ f.dias_restantes === null ? '—' : (f.dias_restantes < 0 ? Math.abs(f.dias_restantes) + 'd vencida' : f.dias_restantes + 'd') }}
                      </span>
                    </td>
                    <td>
                      <button class="btn-pagar-factura" @click="marcarPagada(f.recepcion_id)"
                        :disabled="marcandoPago === f.recepcion_id">
                        {{ marcandoPago === f.recepcion_id ? '...' : 'Marcar pagada' }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

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
      marcandoPago: null,
      d: {
        ventas_hoy: 0, total_hoy_usd: 0, total_hoy_bs: 0,
        ticket_promedio_usd: 0, unidades_vendidas_hoy: 0, clientes_hoy: 0,
        total_productos: 0, productos_stock_bajo: 0, productos_sin_stock: 0,
        valor_inventario_usd: 0, comision_total_hoy: 0, comisiones_pendientes_pago: 0,
        tasa_bcv: 0, tasa_binance: 0, factor: 1,
        alertas: [], ultimas_ventas: [], productos_alerta: [], facturas_pendientes: [],
        ultimas_compras: [], productos_precio_subio: [],
      },
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
      } catch (e) {
        console.error('Error cargando dashboard', e)
      } finally {
        this.cargando = false
      }
    },
    async marcarPagada(recepcionId) {
      if (!confirm('¿Marcar esta factura como pagada?')) return
      this.marcandoPago = recepcionId
      try {
        await axios.put(`/compras/facturas/${recepcionId}/pagar`)
        await this.cargar()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al marcar como pagada')
      } finally {
        this.marcandoPago = null
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
</style>
