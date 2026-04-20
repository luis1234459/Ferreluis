<template>
  <div class="layout">
    <AppSidebar />
    <main class="contenido">
      <div class="top-bar">
        <h1>Compras</h1>
      </div>

      <div class="contenido-inner">

        <!-- Botones de entrada -->
        <div class="hub-acciones">
          <button class="hub-btn" @click="$router.push('/compras/escanear')">
            <span class="hub-icon">📄</span>
            <span class="hub-label">Escanear factura con IA</span>
            <span class="hub-desc">Sube una foto o PDF de la factura</span>
          </button>
          <button class="hub-btn" @click="$router.push('/compras/ordenes')">
            <span class="hub-icon">✏️</span>
            <span class="hub-label">Crear orden manual</span>
            <span class="hub-desc">Genera una orden de compra tradicional</span>
          </button>
        </div>

        <!-- Lista de órdenes recientes -->
        <div class="card-seccion">
          <div class="seccion-header">
            <h2 class="seccion-titulo">Órdenes recientes</h2>
            <div class="filtros-estado">
              <button
                v-for="f in filtros"
                :key="f.val"
                class="btn-filtro"
                :class="{ active: filtroActivo === f.val }"
                @click="filtroActivo = f.val; cargarOrdenes()"
              >{{ f.label }}</button>
            </div>
          </div>

          <div v-if="cargando" class="estado-vacio">Cargando...</div>
          <div v-else-if="ordenes.length === 0" class="estado-vacio">No hay órdenes</div>

          <table v-else class="tabla-ordenes">
            <thead>
              <tr>
                <th>Número</th>
                <th>Proveedor</th>
                <th>Fecha</th>
                <th>Total</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="o in ordenes" :key="o.id">
                <td class="td-numero">{{ o.numero }}</td>
                <td>{{ o.proveedor_nombre }}</td>
                <td class="td-fecha">{{ fmtFecha(o.fecha_creacion) }}</td>
                <td class="td-total">${{ o.total.toFixed(2) }}</td>
                <td>
                  <span class="badge" :class="'badge-' + o.estado">
                    {{ labelEstado(o.estado) }}
                  </span>
                </td>
                <td>
                  <button
                    v-if="o.estado === 'aprobada' || o.estado === 'recibida_parcial'"
                    class="btn-recibir"
                    @click="irARecibir(o.id)"
                  >Recibir</button>
                  <button
                    v-else
                    class="btn-ver"
                    @click="irAOrden(o.id)"
                  >Ver</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '../../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'ComprasHub',
  data() {
    return {
      ordenes:      [],
      cargando:     false,
      filtroActivo: 'todas',
      filtros: [
        { val: 'todas',            label: 'Todas'    },
        { val: 'borrador',         label: 'Borrador' },
        { val: 'aprobada',         label: 'Aprobadas' },
        { val: 'recibida_parcial', label: 'Parciales' },
        { val: 'cerrada',          label: 'Cerradas'  },
      ],
    }
  },
  async mounted() {
    await this.cargarOrdenes()
  },
  methods: {
    async cargarOrdenes() {
      this.cargando = true
      try {
        const params = {}
        if (this.filtroActivo !== 'todas') params.estado = this.filtroActivo
        const { data } = await axios.get('/compras/ordenes/', { params })
        this.ordenes = data
      } catch {
        this.ordenes = []
      } finally {
        this.cargando = false
      }
    },
    irARecibir(ordenId) {
      this.$router.push({ path: '/compras/recibir', query: { orden: ordenId } })
    },
    irAOrden(ordenId) {
      this.$router.push({ path: '/compras/ordenes', query: { id: ordenId } })
    },
    labelEstado(e) {
      return {
        borrador:         'Borrador',
        aprobada:         'Aprobada',
        recibida_parcial: 'Parcial',
        cerrada:          'Cerrada',
        anulada:          'Anulada',
      }[e] || e
    },
    fmtFecha(f) {
      if (!f) return '—'
      return new Date(f).toLocaleDateString('es-VE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    },
  },
}
</script>

<style scoped>
.hub-acciones {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  margin-bottom: 1.5rem;
  max-width: 700px;
}
@media (max-width: 600px) { .hub-acciones { grid-template-columns: 1fr; } }

.hub-btn {
  background: #FFFFFF;
  border: 2px solid var(--borde);
  border-radius: 14px;
  padding: 1.75rem 1.5rem;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.4rem;
  transition: all 0.15s;
  text-align: left;
}
.hub-btn:hover {
  border-color: #FFCC00;
  background: #FFFDF0;
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.hub-icon  { font-size: 2rem; }
.hub-label {
  font-size: 1rem;
  font-weight: 700;
  color: var(--texto-principal);
}
.hub-desc  {
  font-size: 0.82rem;
  color: var(--texto-muted);
}

.card-seccion {
  background: #FFFFFF;
  border: 1px solid var(--borde);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
}
.seccion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.seccion-titulo {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--texto-principal);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.filtros-estado { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.btn-filtro {
  border: 1px solid var(--borde);
  background: #FFFFFF;
  border-radius: 6px;
  padding: 0.3rem 0.75rem;
  font-size: 0.78rem;
  cursor: pointer;
  color: var(--texto-sec);
}
.btn-filtro.active {
  background: #1A1A1A;
  color: #FFCC00;
  border-color: #1A1A1A;
  font-weight: 700;
}

.tabla-ordenes {
  width: 100%;
  border-collapse: collapse;
}
.tabla-ordenes th {
  font-size: 0.72rem;
  text-transform: uppercase;
  color: var(--texto-muted);
  font-weight: 600;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--borde);
  text-align: left;
}
.tabla-ordenes td {
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid var(--borde);
  font-size: 0.875rem;
  color: var(--texto-principal);
}
.tabla-ordenes tr:last-child td { border-bottom: none; }
.tabla-ordenes tr:hover td { background: #FAFAFA; }

.td-numero { font-weight: 700; color: var(--texto-principal); }
.td-fecha  { color: var(--texto-muted); font-size: 0.82rem; }
.td-total  { color: #16A34A; font-weight: 600; }

.badge {
  font-size: 0.72rem; font-weight: 700;
  padding: 0.2rem 0.55rem; border-radius: 4px;
  text-transform: uppercase; letter-spacing: 0.03em;
}
.badge-borrador         { background: #F1F5F9; color: var(--texto-muted); }
.badge-aprobada         { background: #DCFCE7; color: #15803D; }
.badge-recibida_parcial { background: #FEF9C3; color: #854D0E; }
.badge-cerrada          { background: #F0FDF4; color: #166534; }
.badge-anulada          { background: #FEE2E2; color: #DC2626; }

.btn-recibir {
  background: #1A1A1A; color: #FFCC00;
  border: none; border-radius: 6px;
  padding: 0.3rem 0.75rem;
  font-size: 0.78rem; font-weight: 700; cursor: pointer;
}
.btn-recibir:hover { background: #333; }
.btn-ver {
  background: none; border: 1px solid var(--borde);
  border-radius: 6px; padding: 0.3rem 0.75rem;
  font-size: 0.78rem; cursor: pointer; color: var(--texto-sec);
}
.btn-ver:hover { border-color: #FFCC00; }

.estado-vacio {
  text-align: center;
  padding: 2rem;
  color: var(--texto-muted);
  font-size: 0.9rem;
}
</style>
