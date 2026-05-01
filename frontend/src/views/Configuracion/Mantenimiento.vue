<template>
  <div class="layout">
    <AppSidebar />
    <main class="contenido">
      <div class="top-bar">
        <h1>Mantenimiento</h1>
      </div>

      <div class="contenido-inner">

        <!-- Estadísticas actuales -->
        <div class="stats-grid" v-if="stats">
          <div class="stat-card">
            <span class="stat-num">{{ stats.ventas }}</span>
            <span class="stat-label">Ventas</span>
          </div>
          <div class="stat-card">
            <span class="stat-num">{{ stats.ordenes_compra }}</span>
            <span class="stat-label">Órdenes de compra</span>
          </div>
          <div class="stat-card">
            <span class="stat-num">{{ stats.recepciones }}</span>
            <span class="stat-label">Recepciones</span>
          </div>
          <div class="stat-card">
            <span class="stat-num">{{ stats.movimientos }}</span>
            <span class="stat-label">Movimientos bancarios</span>
          </div>
          <div class="stat-card">
            <span class="stat-num">{{ stats.cierres }}</span>
            <span class="stat-label">Cierres de caja</span>
          </div>
        </div>

        <!-- Acciones de limpieza -->
        <div class="acciones-grid">

          <!-- Limpiar ventas -->
          <div class="accion-card">
            <div class="accion-header">
              <span class="accion-icon">🗑️</span>
              <div>
                <h3>Limpiar ventas</h3>
                <p>Elimina ventas y todos sus registros asociados (pagos, detalles, comisiones).</p>
              </div>
            </div>
            <div class="accion-filtros">
              <div class="campo-fila">
                <div class="campo">
                  <label>Desde</label>
                  <input v-model="ventasFiltro.desde" type="date" class="input-field" />
                </div>
                <div class="campo">
                  <label>Hasta</label>
                  <input v-model="ventasFiltro.hasta" type="date" class="input-field" />
                </div>
              </div>
              <small class="txt-muted">Deja vacío para eliminar todas. Usa fechas para limitar el rango.</small>
            </div>
            <button class="btn-peligro" @click="confirmarAccion('ventas')" :disabled="procesando">
              Limpiar ventas
            </button>
          </div>

          <!-- Limpiar compras -->
          <div class="accion-card">
            <div class="accion-header">
              <span class="accion-icon">🗑️</span>
              <div>
                <h3>Limpiar compras</h3>
                <p>Elimina órdenes de compra, recepciones y detalles asociados.</p>
              </div>
            </div>
            <div class="accion-filtros">
              <div class="campo-fila">
                <div class="campo">
                  <label>Desde</label>
                  <input v-model="comprasFiltro.desde" type="date" class="input-field" />
                </div>
                <div class="campo">
                  <label>Hasta</label>
                  <input v-model="comprasFiltro.hasta" type="date" class="input-field" />
                </div>
              </div>
              <small class="txt-muted">Deja vacío para eliminar todas. Usa fechas para limitar el rango.</small>
            </div>
            <button class="btn-peligro" @click="confirmarAccion('compras')" :disabled="procesando">
              Limpiar compras
            </button>
          </div>

          <!-- Limpiar movimientos bancarios -->
          <div class="accion-card">
            <div class="accion-header">
              <span class="accion-icon">🏦</span>
              <div>
                <h3>Limpiar movimientos bancarios</h3>
                <p>Elimina todos los movimientos bancarios registrados.</p>
              </div>
            </div>
            <button class="btn-peligro" @click="confirmarAccion('movimientos')" :disabled="procesando">
              Limpiar movimientos
            </button>
          </div>

          <!-- Limpiar cierres de caja -->
          <div class="accion-card">
            <div class="accion-header">
              <span class="accion-icon">🧾</span>
              <div>
                <h3>Limpiar cierres de caja</h3>
                <p>Elimina el historial de cierres de caja.</p>
              </div>
            </div>
            <button class="btn-peligro" @click="confirmarAccion('cierres')" :disabled="procesando">
              Limpiar cierres
            </button>
          </div>

        </div>

        <!-- Modal de confirmación -->
        <div v-if="modalConfirmar" class="modal-overlay" @click.self="modalConfirmar = false">
          <div class="modal-box">
            <div class="modal-header">
              <h3>⚠ Confirmar eliminación</h3>
              <button class="btn-cerrar-modal" @click="modalConfirmar = false">✕</button>
            </div>
            <div class="modal-body">
              <p class="aviso-peligro">Esta acción es <strong>irreversible</strong>. Los datos eliminados no se pueden recuperar.</p>
              <p>¿Estás seguro de que deseas continuar?</p>
              <div class="campo" style="margin-top:1rem">
                <label>Escribe <strong>CONFIRMAR</strong> para proceder</label>
                <input v-model="textoConfirmar" class="input-field" placeholder="CONFIRMAR" />
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-cancelar" @click="modalConfirmar = false">Cancelar</button>
              <button
                class="btn-peligro"
                :disabled="textoConfirmar !== 'CONFIRMAR' || procesando"
                @click="ejecutarAccion"
              >
                {{ procesando ? 'Procesando...' : 'Sí, eliminar' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Resultado -->
        <div v-if="resultado" class="resultado-box" :class="resultado.error ? 'resultado-error' : 'resultado-ok'">
          {{ resultado.mensaje }}
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
  name: 'Mantenimiento',
  data() {
    return {
      stats:          null,
      procesando:     false,
      modalConfirmar: false,
      accionPendiente: null,
      textoConfirmar:  '',
      resultado:       null,
      ventasFiltro:  { desde: '', hasta: '' },
      comprasFiltro: { desde: '', hasta: '' },
    }
  },
  async mounted() {
    await this.cargarStats()
  },
  methods: {
    async cargarStats() {
      try {
        const { data } = await axios.get('/admin/estadisticas')
        this.stats = data
      } catch {}
    },
    confirmarAccion(accion) {
      this.accionPendiente = accion
      this.textoConfirmar  = ''
      this.resultado       = null
      this.modalConfirmar  = true
    },
    async ejecutarAccion() {
      if (this.textoConfirmar !== 'CONFIRMAR') return
      this.procesando = true
      this.modalConfirmar = false
      try {
        let res
        if (this.accionPendiente === 'ventas') {
          res = await axios.delete('/admin/limpiar-ventas', { data: {
            fecha_desde: this.ventasFiltro.desde || null,
            fecha_hasta: this.ventasFiltro.hasta ? this.ventasFiltro.hasta + 'T23:59:59' : null,
          }})
          this.resultado = { mensaje: `✓ ${res.data.eliminadas} ventas eliminadas correctamente.` }
        } else if (this.accionPendiente === 'compras') {
          res = await axios.delete('/admin/limpiar-compras', { data: {
            fecha_desde: this.comprasFiltro.desde || null,
            fecha_hasta: this.comprasFiltro.hasta ? this.comprasFiltro.hasta + 'T23:59:59' : null,
          }})
          this.resultado = { mensaje: `✓ ${res.data.eliminadas} órdenes de compra eliminadas correctamente.` }
        } else if (this.accionPendiente === 'movimientos') {
          res = await axios.delete('/admin/limpiar-movimientos')
          this.resultado = { mensaje: `✓ ${res.data.eliminados} movimientos bancarios eliminados.` }
        } else if (this.accionPendiente === 'cierres') {
          res = await axios.delete('/admin/limpiar-cierres')
          this.resultado = { mensaje: `✓ ${res.data.eliminados} cierres de caja eliminados.` }
        }
        await this.cargarStats()
      } catch (e) {
        this.resultado = { error: true, mensaje: e?.response?.data?.detail || 'Error al procesar.' }
      } finally {
        this.procesando      = false
        this.accionPendiente = null
        this.textoConfirmar  = ''
      }
    },
  },
}
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.stat-card {
  background: #FFFFFF;
  border: 1px solid var(--borde);
  border-radius: 10px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
}
.stat-num {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--texto-principal);
}
.stat-label {
  font-size: 0.78rem;
  color: var(--texto-muted);
  text-align: center;
}
.acciones-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.25rem;
}
.accion-card {
  background: #FFFFFF;
  border: 1px solid var(--borde);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.accion-header {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}
.accion-icon { font-size: 1.5rem; flex-shrink: 0; }
.accion-header h3 { margin: 0 0 0.25rem; font-size: 0.95rem; color: var(--texto-principal); }
.accion-header p  { margin: 0; font-size: 0.82rem; color: var(--texto-muted); }
.accion-filtros { display: flex; flex-direction: column; gap: 0.5rem; }
.campo-fila { display: flex; gap: 0.75rem; }
.campo { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.campo label { font-size: 0.75rem; font-weight: 600; color: var(--texto-sec); }
.input-field {
  border: 1px solid var(--borde); border-radius: 6px;
  padding: 0.45rem 0.65rem; font-size: 0.875rem;
  color: var(--texto-principal); background: var(--fondo-app);
  width: 100%; box-sizing: border-box;
}
.txt-muted { color: var(--texto-muted); font-size: 0.78rem; }
.btn-peligro {
  background: #DC2626; color: white; border: none;
  border-radius: 8px; padding: 0.65rem 1.25rem;
  font-weight: 700; font-size: 0.875rem; cursor: pointer;
  align-self: flex-start;
}
.btn-peligro:hover:not(:disabled) { background: #B91C1C; }
.btn-peligro:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar {
  background: none; border: 1px solid var(--borde);
  border-radius: 6px; padding: 0.5rem 1rem;
  cursor: pointer; color: var(--texto-sec); font-size: 0.875rem;
}
.aviso-peligro {
  background: #FEE2E2; border: 1px solid #DC2626;
  border-radius: 8px; padding: 0.75rem 1rem;
  color: #DC2626; font-size: 0.88rem; margin: 0 0 0.75rem;
}
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  z-index: 9999; display: flex; align-items: center; justify-content: center;
}
.modal-box {
  background: #FFFFFF; border-radius: 12px;
  width: 100%; max-width: 440px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.2);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--borde);
}
.modal-header h3 { margin: 0; font-size: 1rem; color: #DC2626; }
.btn-cerrar-modal {
  background: none; border: none; font-size: 1.1rem;
  cursor: pointer; color: var(--texto-muted);
}
.modal-body {
  padding: 1.25rem 1.5rem;
  display: flex; flex-direction: column; gap: 0.5rem;
}
.modal-footer {
  padding: 1rem 1.5rem; border-top: 1px solid var(--borde);
  display: flex; justify-content: flex-end; gap: 0.75rem;
}
.resultado-box {
  margin-top: 1.5rem; border-radius: 10px;
  padding: 1rem 1.25rem; font-size: 0.9rem; font-weight: 600;
}
.resultado-ok    { background: #DCFCE7; color: #15803D; border: 1px solid #16A34A; }
.resultado-error { background: #FEE2E2; color: #DC2626; border: 1px solid #DC2626; }
</style>
