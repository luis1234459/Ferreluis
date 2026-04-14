<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Vendedores y Comisiones</h1>
        <div class="top-acciones">
          <button class="btn-nuevo" @click="abrirNuevoVendedor">+ Nuevo vendedor</button>
        </div>
      </div>

      <div class="contenido-inner">

        <!-- ── Tabs ── -->
        <div class="tabs-nav">
          <button class="tab-btn" :class="{ 'tab-activo': tabActivo === 'vendedores' }"
            @click="tabActivo = 'vendedores'">
            Vendedores
            <span class="tab-badge">{{ vendedores.length }}</span>
          </button>
          <button class="tab-btn" :class="{ 'tab-activo': tabActivo === 'periodos' }"
            @click="cambiarTabPeriodos">
            Períodos de pago
            <span class="tab-badge">{{ periodos.length }}</span>
          </button>
        </div>

        <!-- ══════════════════════════════════════════════════════════ -->
        <!-- Tab: Vendedores                                            -->
        <!-- ══════════════════════════════════════════════════════════ -->
        <div v-show="tabActivo === 'vendedores'">
          <div class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Email</th>
                  <th>Período de pago</th>
                  <th>Comisión base</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="vendedores.length === 0">
                  <td colspan="6" class="sin-datos">Sin vendedores registrados</td>
                </tr>
                <tr v-for="v in vendedores" :key="v.id">
                  <td style="font-weight:600">{{ v.usuario_nombre }}</td>
                  <td class="txt-muted">{{ v.usuario_email }}</td>
                  <td>
                    <span class="badge-periodo">{{ v.periodo_pago === 'semanal' ? 'Semanal' : 'Quincenal' }}</span>
                  </td>
                  <td class="txt-verde">{{ (v.comision_base * 100).toFixed(1) }}%</td>
                  <td>
                    <span :class="v.activo ? 'badge-activa' : 'badge-inactiva'">
                      {{ v.activo ? 'Activo' : 'Inactivo' }}
                    </span>
                  </td>
                  <td>
                    <div class="acciones">
                      <button class="btn-editar" @click="editarVendedor(v)">Editar</button>
                      <button class="btn-comisiones" @click="abrirComisiones(v)">Comisiones</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════ -->
        <!-- Tab: Períodos                                              -->
        <!-- ══════════════════════════════════════════════════════════ -->
        <div v-show="tabActivo === 'periodos'">
          <div class="periodos-header">
            <span class="periodos-desc">Períodos de liquidación de comisiones</span>
            <button class="btn-nuevo" @click="abrirNuevoPeriodo">+ Nuevo período</button>
          </div>
          <div class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Vendedor</th>
                  <th>Desde</th>
                  <th>Hasta</th>
                  <th>Ventas USD</th>
                  <th>Comisión</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="periodos.length === 0">
                  <td colspan="7" class="sin-datos">Sin períodos registrados</td>
                </tr>
                <tr v-for="p in periodos" :key="p.id">
                  <td style="font-weight:600">{{ p.vendedor_nombre }}</td>
                  <td class="txt-muted">{{ formatFecha(p.fecha_inicio) }}</td>
                  <td class="txt-muted">{{ formatFecha(p.fecha_fin) }}</td>
                  <td>${{ Number(p.total_ventas_usd).toFixed(2) }}</td>
                  <td class="txt-verde">${{ Number(p.total_comision).toFixed(2) }}</td>
                  <td>
                    <span :class="p.estado === 'pagado' ? 'badge-activa' : 'badge-pendiente'">
                      {{ p.estado === 'pagado' ? 'Pagado' : 'Pendiente' }}
                    </span>
                  </td>
                  <td>
                    <div class="acciones">
                      <button v-if="p.estado === 'pendiente'" class="btn-pagar"
                        @click="abrirPagarPeriodo(p)">
                        Marcar pagado
                      </button>
                      <span v-else class="txt-muted" style="font-size:0.82rem">
                        {{ p.pagado_por ? 'Por: ' + p.pagado_por : '—' }}
                      </span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </div><!-- /contenido-inner -->

      <!-- ══════════════════════════════════════════════════════════════════ -->
      <!-- Modal: Nuevo / Editar vendedor                                    -->
      <!-- ══════════════════════════════════════════════════════════════════ -->
  <div class="overlay" v-if="mostrarFormVendedor" @click.self="cerrarFormVendedor">
    <div class="modal modal-form">
      <div class="modal-header">
        <h2>{{ editandoVendedorId ? 'Editar vendedor' : 'Nuevo vendedor' }}</h2>
        <button class="btn-cerrar-modal" @click="cerrarFormVendedor">✕</button>
      </div>

      <div class="grid-form">
        <div class="field-wide">
          <label>Usuario del sistema</label>
          <select v-model="formVendedor.usuario_id" :disabled="!!editandoVendedorId">
            <option value="">— Seleccionar —</option>
            <option v-for="u in usuariosSistema" :key="u.id" :value="u.id">
              {{ u.nombre }} ({{ u.rol }})
            </option>
          </select>
        </div>
        <div>
          <label>Período de pago</label>
          <select v-model="formVendedor.periodo_pago">
            <option value="semanal">Semanal</option>
            <option value="quincenal">Quincenal</option>
          </select>
        </div>
        <div>
          <label>Comisión base (%)</label>
          <input type="number" step="0.1" min="0" max="100"
            v-model="formVendedor.comision_base_pct"
            placeholder="ej: 3" />
        </div>
        <div class="field-wide">
          <label class="check-opt">
            <input type="checkbox" v-model="formVendedor.activo" />
            <span class="check-label">
              <strong>Activo</strong>
              <small>Los vendedores inactivos no acumulan comisiones</small>
            </span>
          </label>
        </div>
      </div>

      <p v-if="errorVendedor" class="msg-error">{{ errorVendedor }}</p>

      <div class="modal-footer">
        <button class="btn-cancelar" @click="cerrarFormVendedor">Cancelar</button>
        <button class="btn-guardar" @click="guardarVendedor" :disabled="guardando">
          {{ guardando ? 'Guardando...' : 'Guardar' }}
        </button>
      </div>
    </div>
  </div>

      <!-- ══════════════════════════════════════════════════════════════════ -->
      <!-- Modal: Comisiones especiales                                      -->
      <!-- ══════════════════════════════════════════════════════════════════ -->
  <div class="overlay" v-if="modalComisiones" @click.self="cerrarComisiones">
    <div class="modal modal-variantes">
      <div class="modal-header">
        <h2>Comisiones — {{ modalComisiones.usuario_nombre }}</h2>
        <button class="btn-cerrar-modal" @click="cerrarComisiones">✕</button>
      </div>

      <p class="desc-comp">
        Comisión base: <strong class="txt-verde">{{ (modalComisiones.comision_base * 100).toFixed(1) }}%</strong>
        — Se aplica la regla con el porcentaje más alto.
      </p>

      <!-- Tabla de comisiones especiales -->
      <table style="width:100%; margin-bottom:1rem">
        <thead>
          <tr>
            <th>Tipo</th>
            <th>Referencia</th>
            <th>%</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="comisionesEspeciales.length === 0">
            <td colspan="4" class="sin-datos">Sin comisiones especiales</td>
          </tr>
          <tr v-for="ce in comisionesEspeciales" :key="ce.id">
            <td>
              <span class="badge-tipo-ce">{{ ce.tipo }}</span>
            </td>
            <td class="txt-muted">{{ nombreReferencia(ce) }}</td>
            <td class="txt-verde">{{ (ce.porcentaje * 100).toFixed(1) }}%</td>
            <td>
              <button class="btn-eliminar" @click="eliminarComisionEspecial(ce.id)">✕</button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Formulario agregar comisión especial -->
      <div class="subform">
        <p class="subtitulo-subform">Agregar comisión especial</p>
        <div class="grid-form-sm">
          <div>
            <label>Tipo</label>
            <select v-model="formCE.tipo" @change="formCE.referencia_id = ''">
              <option value="departamento">Departamento</option>
              <option value="proveedor">Proveedor</option>
              <option value="pareto">Producto clave (Pareto)</option>
              <option value="producto">Producto específico</option>
            </select>
          </div>
          <div v-if="formCE.tipo !== 'pareto'">
            <label>Referencia</label>
            <select v-model="formCE.referencia_id">
              <option value="">— Seleccionar —</option>
              <option v-for="item in opcionesReferencia" :key="item.id" :value="item.id">{{ item.nombre }}</option>
            </select>
          </div>
          <div v-else>
            <label>Referencia</label>
            <input disabled value="Todos los productos clave" style="opacity:0.5" />
          </div>
          <div>
            <label>Porcentaje (%)</label>
            <input type="number" step="0.1" min="0" max="100"
              v-model="formCE.porcentaje_pct" placeholder="ej: 5" />
          </div>
        </div>
        <p v-if="errorCE" class="msg-error">{{ errorCE }}</p>
        <button class="btn-agregar-linea" @click="guardarComisionEspecial" :disabled="guardando">
          + Agregar comisión especial
        </button>
      </div>
    </div>
  </div>

      <!-- ══════════════════════════════════════════════════════════════════ -->
      <!-- Modal: Nuevo período                                              -->
      <!-- ══════════════════════════════════════════════════════════════════ -->
  <div class="overlay" v-if="mostrarFormPeriodo" @click.self="cerrarFormPeriodo">
    <div class="modal modal-sm">
      <div class="modal-header">
        <h2>Nuevo período</h2>
        <button class="btn-cerrar-modal" @click="cerrarFormPeriodo">✕</button>
      </div>
      <div class="grid-form">
        <div class="field-wide">
          <label>Vendedor</label>
          <select v-model="formPeriodo.vendedor_id">
            <option value="">— Seleccionar —</option>
            <option v-for="v in vendedores" :key="v.id" :value="v.id">{{ v.usuario_nombre }}</option>
          </select>
        </div>
        <div>
          <label>Fecha inicio</label>
          <input type="date" v-model="formPeriodo.fecha_inicio" />
        </div>
        <div>
          <label>Fecha fin</label>
          <input type="date" v-model="formPeriodo.fecha_fin" />
        </div>
      </div>
      <p v-if="errorPeriodo" class="msg-error">{{ errorPeriodo }}</p>
      <div class="modal-footer">
        <button class="btn-cancelar" @click="cerrarFormPeriodo">Cancelar</button>
        <button class="btn-guardar" @click="guardarPeriodo" :disabled="guardando">
          {{ guardando ? 'Calculando...' : 'Crear período' }}
        </button>
      </div>
    </div>
  </div>

      <!-- ══════════════════════════════════════════════════════════════════ -->
      <!-- Modal: Marcar período pagado                                      -->
      <!-- ══════════════════════════════════════════════════════════════════ -->
  <div class="overlay" v-if="modalPagar" @click.self="modalPagar = null">
    <div class="modal modal-sm">
      <div class="modal-header">
        <h2>Confirmar pago</h2>
        <button class="btn-cerrar-modal" @click="modalPagar = null">✕</button>
      </div>
      <div style="padding:0 0 1rem">
        <p style="color:var(--texto-sec); margin-bottom:1rem">
          Marcar como pagado el período de
          <strong>{{ modalPagar?.vendedor_nombre }}</strong>
          por <strong class="txt-verde">${{ Number(modalPagar?.total_comision || 0).toFixed(2) }}</strong>
        </p>
        <p style="color:var(--texto-sec);font-size:0.85rem;font-weight:600;margin:0 0 0.4rem">
          Observación (opcional)
        </p>
        <input v-model="observacionPago" placeholder="ej: Transferencia #12345..."
          style="width:100%;padding:0.5rem 0.8rem;background:#FFF;border:1px solid #CCC;border-radius:8px;box-sizing:border-box" />
      </div>
      <div class="modal-footer">
        <button class="btn-cancelar" @click="modalPagar = null">Cancelar</button>
        <button class="btn-guardar" @click="confirmarPago" :disabled="guardando">
          {{ guardando ? 'Guardando...' : 'Confirmar pago' }}
        </button>
      </div>
    </div>
  </div>

    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'Vendedores',
  data() {
    return {
      usuario: JSON.parse(localStorage.getItem('usuario') || '{}'),

      vendedores:       [],
      periodos:         [],
      usuariosSistema:  [],
      departamentos:    [],
      proveedores:      [],
      productos:        [],

      tabActivo: 'vendedores',

      // Modal vendedor
      mostrarFormVendedor: false,
      editandoVendedorId:  null,
      guardando:           false,
      errorVendedor:       '',
      formVendedor: {
        usuario_id:       '',
        periodo_pago:     'quincenal',
        comision_base_pct: 0,
        activo:           true,
      },

      // Modal comisiones especiales
      modalComisiones:      null,
      comisionesEspeciales: [],
      errorCE:              '',
      formCE: { tipo: 'departamento', referencia_id: '', porcentaje_pct: 0 },

      // Modal período
      mostrarFormPeriodo: false,
      errorPeriodo:       '',
      formPeriodo: { vendedor_id: '', fecha_inicio: '', fecha_fin: '' },

      // Modal pagar
      modalPagar:      null,
      observacionPago: '',
    }
  },

  computed: {
    esAdmin() { return this.usuario.rol === 'admin' },
    tienePermiso() {
      return (modulo) => {
        if (this.usuario.rol === 'admin') return true
        const p = this.usuario.permisos
        if (p == null) return true
        return Array.isArray(p) ? p.includes(modulo) : true
      }
    },
    opcionesReferencia() {
      if (this.formCE.tipo === 'departamento') return this.departamentos
      if (this.formCE.tipo === 'proveedor') return this.proveedores
      if (this.formCE.tipo === 'producto') return this.productos
      return []
    },
  },

  async mounted() {
    await Promise.all([
      this.cargarVendedores(),
      this.cargarUsuarios(),
      this.cargarDepartamentos(),
      this.cargarProveedores(),
      this.cargarProductos(),
    ])
  },

  methods: {
    // ── Carga ─────────────────────────────────────────────────────────────────
    async cargarVendedores() {
      const res = await axios.get('/vendedores/', { headers: this._headers() })
      this.vendedores = res.data
    },
    async cargarPeriodos() {
      const res = await axios.get('/vendedores/periodos/', { headers: this._headers() })
      this.periodos = res.data
    },
    async cargarUsuarios() {
      try {
        const res = await axios.get('/usuarios/', { headers: this._headers() })
        this.usuariosSistema = res.data
      } catch { this.usuariosSistema = [] }
    },
    async cargarDepartamentos() {
      try {
        const res = await axios.get('/productos/departamentos')
        this.departamentos = res.data
      } catch { this.departamentos = [] }
    },
    async cargarProveedores() {
      try {
        const res = await axios.get('/compras/proveedores/')
        this.proveedores = res.data
      } catch { this.proveedores = [] }
    },
    async cargarProductos() {
      try {
        const res = await axios.get('/productos/')
        this.productos = res.data
      } catch { this.productos = [] }
    },

    _headers() {
      return { 'X-Usuario-Rol': this.usuario.rol || '' }
    },

    // ── Tabs ──────────────────────────────────────────────────────────────────
    async cambiarTabPeriodos() {
      this.tabActivo = 'periodos'
      await this.cargarPeriodos()
    },

    // ── Utilidades ────────────────────────────────────────────────────────────
    formatFecha(s) {
      if (!s) return '—'
      return new Date(s + 'T00:00:00').toLocaleDateString('es-VE')
    },
    nombreReferencia(ce) {
      if (ce.tipo === 'pareto') return 'Todos los productos clave'
      if (!ce.referencia_id) return '—'
      if (ce.tipo === 'departamento') {
        const d = this.departamentos.find(x => x.id === ce.referencia_id)
        return d ? d.nombre : `ID ${ce.referencia_id}`
      }
      if (ce.tipo === 'proveedor') {
        const p = this.proveedores.find(x => x.id === ce.referencia_id)
        return p ? p.nombre : `ID ${ce.referencia_id}`
      }
      if (ce.tipo === 'producto') {
        const p = this.productos.find(x => x.id === ce.referencia_id)
        return p ? p.nombre : `ID ${ce.referencia_id}`
      }
      return `ID ${ce.referencia_id}`
    },

    // ── CRUD Vendedores ───────────────────────────────────────────────────────
    abrirNuevoVendedor() {
      this.editandoVendedorId = null
      this.errorVendedor      = ''
      this.formVendedor = { usuario_id: '', periodo_pago: 'quincenal', comision_base_pct: 0, activo: true }
      this.mostrarFormVendedor = true
    },
    editarVendedor(v) {
      this.editandoVendedorId = v.id
      this.errorVendedor      = ''
      this.formVendedor = {
        usuario_id:        v.usuario_id,
        periodo_pago:      v.periodo_pago,
        comision_base_pct: Number((v.comision_base * 100).toFixed(2)),
        activo:            v.activo,
      }
      this.mostrarFormVendedor = true
    },
    cerrarFormVendedor() {
      this.mostrarFormVendedor = false
      this.editandoVendedorId  = null
      this.errorVendedor       = ''
    },
    async guardarVendedor() {
      if (!this.formVendedor.usuario_id) { this.errorVendedor = 'Selecciona un usuario'; return }
      this.guardando = true; this.errorVendedor = ''
      try {
        const payload = {
          usuario_id:    Number(this.formVendedor.usuario_id),
          periodo_pago:  this.formVendedor.periodo_pago,
          comision_base: Number(this.formVendedor.comision_base_pct || 0) / 100,
          activo:        this.formVendedor.activo,
        }
        if (this.editandoVendedorId) {
          await axios.put(`/vendedores/${this.editandoVendedorId}`, payload, { headers: this._headers() })
        } else {
          await axios.post('/vendedores/', payload, { headers: this._headers() })
        }
        await this.cargarVendedores()
        this.cerrarFormVendedor()
      } catch (e) {
        this.errorVendedor = e?.response?.data?.detail || 'Error al guardar'
      } finally {
        this.guardando = false
      }
    },

    // ── Comisiones especiales ─────────────────────────────────────────────────
    async abrirComisiones(v) {
      this.modalComisiones = v
      this.errorCE         = ''
      this.formCE          = { tipo: 'departamento', referencia_id: '', porcentaje_pct: 0 }
      const res = await axios.get(`/vendedores/${v.id}/comisiones`, { headers: this._headers() })
      this.comisionesEspeciales = res.data
    },
    cerrarComisiones() {
      this.modalComisiones      = null
      this.comisionesEspeciales = []
      this.errorCE              = ''
    },
    async guardarComisionEspecial() {
      if (this.formCE.tipo !== 'pareto' && !this.formCE.referencia_id) {
        this.errorCE = 'Selecciona una referencia'; return
      }
      if (!this.formCE.porcentaje_pct) { this.errorCE = 'Ingresa el porcentaje'; return }
      this.guardando = true; this.errorCE = ''
      try {
        await axios.post(`/vendedores/${this.modalComisiones.id}/comisiones`, {
          vendedor_id:   this.modalComisiones.id,
          tipo:          this.formCE.tipo,
          referencia_id: this.formCE.tipo === 'pareto' ? null : Number(this.formCE.referencia_id),
          porcentaje:    Number(this.formCE.porcentaje_pct || 0) / 100,
        }, { headers: this._headers() })
        const res = await axios.get(`/vendedores/${this.modalComisiones.id}/comisiones`, { headers: this._headers() })
        this.comisionesEspeciales = res.data
        this.formCE = { tipo: 'departamento', referencia_id: '', porcentaje_pct: 0 }
      } catch (e) {
        this.errorCE = e?.response?.data?.detail || 'Error al agregar'
      } finally {
        this.guardando = false
      }
    },
    async eliminarComisionEspecial(id) {
      if (!confirm('¿Eliminar esta comisión especial?')) return
      await axios.delete(`/vendedores/comisiones/${id}`, { headers: this._headers() })
      const res = await axios.get(`/vendedores/${this.modalComisiones.id}/comisiones`, { headers: this._headers() })
      this.comisionesEspeciales = res.data
    },

    // ── Períodos ──────────────────────────────────────────────────────────────
    abrirNuevoPeriodo() {
      this.errorPeriodo = ''
      const hoy = new Date().toISOString().split('T')[0]
      this.formPeriodo = { vendedor_id: '', fecha_inicio: hoy, fecha_fin: hoy }
      this.mostrarFormPeriodo = true
    },
    cerrarFormPeriodo() {
      this.mostrarFormPeriodo = false
      this.errorPeriodo       = ''
    },
    async guardarPeriodo() {
      if (!this.formPeriodo.vendedor_id)  { this.errorPeriodo = 'Selecciona un vendedor'; return }
      if (!this.formPeriodo.fecha_inicio) { this.errorPeriodo = 'Fecha inicio requerida'; return }
      if (!this.formPeriodo.fecha_fin)    { this.errorPeriodo = 'Fecha fin requerida'; return }
      this.guardando = true; this.errorPeriodo = ''
      try {
        await axios.post('/vendedores/periodos/', {
          vendedor_id:  Number(this.formPeriodo.vendedor_id),
          fecha_inicio: this.formPeriodo.fecha_inicio,
          fecha_fin:    this.formPeriodo.fecha_fin,
        }, { headers: this._headers() })
        await this.cargarPeriodos()
        this.cerrarFormPeriodo()
      } catch (e) {
        this.errorPeriodo = e?.response?.data?.detail || 'Error al crear período'
      } finally {
        this.guardando = false
      }
    },
    abrirPagarPeriodo(p) {
      this.modalPagar      = p
      this.observacionPago = ''
    },
    async confirmarPago() {
      this.guardando = true
      try {
        await axios.put(`/vendedores/periodos/${this.modalPagar.id}/pagar`,
          { observacion: this.observacionPago || null },
          { headers: { ...this._headers(), 'X-Usuario-Nombre': this.usuario.usuario || 'admin' } }
        )
        await this.cargarPeriodos()
        this.modalPagar = null
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al marcar como pagado')
      } finally {
        this.guardando = false
      }
    },

    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    },
  },
}
</script>

<style scoped>
/* ── Top bar ── */
.top-acciones { display: flex; gap: 0.6rem; align-items: center; }

/* ── Tabs ── */
.tabs-nav { display: flex; gap: 0.25rem; margin-bottom: 1.25rem; border-bottom: 2px solid var(--borde); }
.tab-btn  { padding: 0.6rem 1.4rem; background: transparent; color: var(--texto-sec); border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; font-size: 0.9rem; display: flex; align-items: center; gap: 0.4rem; }
.tab-btn:hover { color: var(--texto-principal); }
.tab-activo { color: var(--texto-principal) !important; border-bottom-color: #1A1A1A !important; font-weight: 700; }
.tab-badge  { background: var(--amarillo); color: #1A1A1A; font-size: 0.72rem; font-weight: 700; padding: 0.1rem 0.45rem; border-radius: 10px; }

/* ── Períodos header ── */
.periodos-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; }
.periodos-desc   { color: var(--texto-sec); font-size: 0.88rem; }

/* ── Badges ── */
.badge-periodo  { background: var(--borde-suave); color: var(--texto-sec); font-size: 0.78rem; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 10px; }
.badge-activa   { background: #16A34A1A; color: #16A34A;  font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 10px; }
.badge-inactiva { background: #8888881A; color: #555555;  font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 10px; }
.badge-pendiente{ background: #F59E0B1A; color: #92400E;  font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 10px; }
.badge-tipo-ce  { background: #1A1A1A1A; color: #1A1A1A;  font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 10px; text-transform: capitalize; }

/* ── Textos ── */
.txt-muted { color: var(--texto-muted); }
.txt-verde { color: #16A34A; font-weight: 600; }

/* ── Acciones ── */
.acciones       { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.btn-editar     { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.btn-comisiones { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.btn-pagar      { background: #16A34A; color: white;   border: none; padding: 0.25rem 0.7rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; font-weight: 600; }
.btn-eliminar   { background: var(--danger); color: white; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }

/* ── Modales ── */
.modal-form     { max-width: 540px; }
.modal-variantes{ max-width: 680px; }
.modal-sm       { max-width: 480px; }

.grid-form    { display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; }
.field-wide   { grid-column: 1 / -1; }
.grid-form label,
.subform label { color: var(--texto-sec); font-size: 0.85rem; font-weight: 600; display: block; margin-bottom: 0.3rem; }

.subform          { background: var(--borde-suave); border-radius: 10px; padding: 1rem; margin-top: 1rem; border: 1px solid var(--borde); }
.subtitulo-subform{ color: var(--texto-principal); font-size: 0.88rem; font-weight: 700; margin: 0 0 0.75rem; }
.grid-form-sm     { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.desc-comp        { color: var(--texto-sec); font-size: 0.88rem; margin-bottom: 0.75rem; }

.btn-agregar-linea { background: transparent; border: 1px dashed var(--borde); color: var(--texto-sec); padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; margin-top: 0.75rem; font-size: 0.88rem; width: 100%; }
.btn-agregar-linea:hover { border-color: var(--amarillo); background: #FFCC0011; }
.btn-agregar-linea:disabled { opacity: 0.45; cursor: not-allowed; }

.check-opt  { display: flex; align-items: flex-start; gap: 0.6rem; cursor: pointer; }
.check-opt input[type="checkbox"] { margin-top: 0.2rem; width: 15px; height: 15px; flex-shrink: 0; accent-color: #1A1A1A; }
.check-label        { display: flex; flex-direction: column; gap: 0.1rem; }
.check-label strong { color: var(--texto-principal); font-size: 0.9rem; }
.check-label small  { color: var(--texto-muted); font-size: 0.8rem; }

.modal-footer { display: flex; justify-content: flex-end; gap: 0.6rem; margin-top: 1.25rem; }
.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.55rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.55rem 1.2rem; border-radius: 6px; cursor: pointer; }
.msg-error    { color: var(--danger); font-size: 0.88rem; margin-top: 0.5rem; }
</style>
