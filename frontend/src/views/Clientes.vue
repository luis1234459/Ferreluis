<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Clientes</h1>
        <button class="btn-nuevo" @click="abrirCrear">+ Nuevo cliente</button>
      </div>

      <div class="contenido-inner">
        <!-- Filtros -->
        <div class="filtros">
          <input v-model="busqueda" placeholder="Teléfono o nombre del cliente..." class="buscador" @input="cargarClientes" />
        </div>

        <!-- Tabla -->
        <div class="tabla-container">
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>Nombre</th>
                <th>Teléfono</th>
                <th>Nivel</th>
                <th>Compras</th>
                <th>Acumulado USD</th>
                <th>Crédito</th>
                <th>Desde</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in clientes" :key="c.id">
                <td><span class="codigo-cli">{{ c.codigo || '—' }}</span></td>
                <td>{{ c.nombre }}</td>
                <td>{{ c.telefono }}</td>
                <td>
                  <span v-if="c.nivel_fidelidad" class="badge-nivel" :style="{ background: c.nivel_fidelidad.color + '33', color: c.nivel_fidelidad.color, border: '1px solid ' + c.nivel_fidelidad.color }">
                    {{ c.nivel_fidelidad.nombre }}
                  </span>
                  <span v-else class="badge-sin-nivel">Sin nivel</span>
                </td>
                <td>{{ c.total_compras }}</td>
                <td class="txt-verde">${{ c.monto_acumulado_usd.toFixed(2) }}</td>
                <td>
                  <span v-if="c.tiene_credito" class="badge-credito">
                    ${{ (c.saldo_credito || 0).toFixed(2) }}
                  </span>
                  <span v-else class="txt-muted-sm">—</span>
                </td>
                <td>{{ formatFecha(c.fecha_registro) }}</td>
                <td>
                  <button class="btn-ver" @click="verDetalle(c)">Ver</button>
                  <button class="btn-editar" @click="abrirEditar(c)">Editar</button>
                  <button class="btn-whatsapp" @click="abrirWhatsapp(c.telefono)" title="WhatsApp">💬</button>
                  <button class="btn-eliminar" @click="desactivar(c.id)" v-if="esAdmin">✕</button>
                </td>
              </tr>
              <tr v-if="clientes.length === 0">
                <td colspan="9" class="sin-datos">No hay clientes registrados</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Dialog Crear/Editar -->
        <div class="overlay" v-if="mostrarForm">
          <div class="dialog">
            <h2>{{ editando ? 'Editar cliente' : 'Nuevo cliente' }}</h2>
            <div class="grid-form">
              <div class="field">
                <label>Nombre *</label>
                <input v-model="form.nombre" placeholder="Nombre completo" />
              </div>
              <div class="field">
                <label>Teléfono *</label>
                <div class="tel-input">
                  <div class="prefijos">
                    <button type="button" v-for="p in prefijos" :key="p"
                      :class="['btn-prefijo', prefijoSeleccionado === p ? 'activo' : '']"
                      @click="prefijoSeleccionado = p; actualizarTelefono()">{{ p }}</button>
                  </div>
                  <input v-model="telefonoNumeros" placeholder="1234567" maxlength="7"
                    @input="actualizarTelefono" type="tel" />
                </div>
                <small class="tel-preview" v-if="telefonoNumeros">{{ form.telefono }}</small>
              </div>
              <div class="field">
                <label>Email</label>
                <input v-model="form.email" placeholder="correo@ejemplo.com" />
              </div>
              <div class="field">
                <label>Tipo</label>
                <select v-model="form.tipo_cliente">
                  <option value="natural">Natural</option>
                  <option value="juridico">Jurídico</option>
                </select>
              </div>
              <div class="field">
                <label>Cédula / RIF</label>
                <input v-model="form.rif_cedula" placeholder="V-12345678" />
              </div>
              <div class="field">
                <label>Dirección</label>
                <input v-model="form.direccion" placeholder="Dirección" />
              </div>
              <div class="field full">
                <label>Notas</label>
                <input v-model="form.notas" placeholder="Observaciones internas..." />
              </div>

              <!-- Crédito (solo admin) -->
              <div class="field full credito-section" v-if="esAdmin">
                <div class="credito-toggle">
                  <label class="toggle-label">
                    <input type="checkbox" v-model="form.tiene_credito" />
                    <span>Habilitar crédito</span>
                  </label>
                </div>
                <div v-if="form.tiene_credito" class="credito-campos">
                  <div class="field">
                    <label>Límite de crédito (USD)</label>
                    <input v-model.number="form.limite_credito" type="number" min="0" step="0.01" placeholder="0.00" />
                  </div>
                  <div class="field" v-if="editando">
                    <label>Saldo disponible</label>
                    <input :value="'$' + (form.saldo_credito || 0).toFixed(2)" readonly style="background:#F5F5F0;color:#16A34A;font-weight:700;cursor:default" />
                  </div>
                </div>
              </div>

              <div class="field" v-if="editando && form.codigo">
                <label>Código</label>
                <input :value="form.codigo" readonly style="background:#F5F5F0;color:#888;cursor:default" />
              </div>
            </div>
            <div class="form-botones">
              <button class="btn-cancelar" @click="cerrarForm">Cancelar</button>
              <button class="btn-guardar" @click="guardar">Guardar</button>
            </div>
          </div>
        </div>

        <!-- Dialog Detalle -->
        <div class="overlay" v-if="clienteDetalle">
          <div class="dialog dialog-grande">
            <div class="detalle-header">
              <div>
                <h2>{{ clienteDetalle.nombre }}</h2>
                <p class="detalle-sub">Tel: {{ clienteDetalle.telefono }} &nbsp;|&nbsp; Desde: {{ formatFecha(clienteDetalle.fecha_registro) }}</p>
              </div>
              <span v-if="clienteDetalle.nivel_fidelidad" class="badge-nivel badge-grande"
                :style="{ background: clienteDetalle.nivel_fidelidad.color + '33', color: clienteDetalle.nivel_fidelidad.color, border: '1px solid ' + clienteDetalle.nivel_fidelidad.color }">
                {{ clienteDetalle.nivel_fidelidad.nombre }}
              </span>
              <button class="btn-cerrar-x" @click="clienteDetalle = null">✕</button>
            </div>

            <div class="stats-row">
              <div class="stat-box">
                <p class="stat-label">Compras</p>
                <p class="stat-valor">{{ clienteDetalle.total_compras }}</p>
              </div>
              <div class="stat-box">
                <p class="stat-label">Acumulado USD</p>
                <p class="stat-valor txt-verde">${{ clienteDetalle.monto_acumulado_usd.toFixed(2) }}</p>
              </div>
              <div class="stat-box" v-if="clienteDetalle.proximo_nivel">
                <p class="stat-label">Próximo nivel: {{ clienteDetalle.proximo_nivel.nombre }}</p>
                <p class="stat-valor-sm">Faltan {{ clienteDetalle.proximo_nivel.faltan_compras }} compras y ${{ clienteDetalle.proximo_nivel.faltan_monto }}</p>
              </div>
              <div class="stat-box" v-else>
                <p class="stat-label">Nivel máximo alcanzado</p>
              </div>
            </div>

            <h3 class="seccion-titulo">Historial de compras</h3>
            <div class="tabla-container">
              <table>
                <thead>
                  <tr><th>Fecha</th><th>Total</th><th>Moneda</th><th>Estado</th></tr>
                </thead>
                <tbody>
                  <tr v-for="v in clienteDetalle.historial" :key="v.id">
                    <td>{{ formatFecha(v.fecha) }}</td>
                    <td :class="v.moneda === 'USD' ? 'txt-verde' : 'txt-yellow'">{{ v.moneda === 'USD' ? '$' : 'Bs.' }} {{ v.total.toFixed(2) }}</td>
                    <td>{{ v.moneda }}</td>
                    <td><span :class="'badge badge-' + v.estado">{{ v.estado }}</span></td>
                  </tr>
                  <tr v-if="clienteDetalle.historial.length === 0">
                    <td colspan="4" class="sin-datos">Sin compras registradas</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="premios-header">
              <h3 class="seccion-titulo">Premios recibidos</h3>
              <button v-if="esAdmin" class="btn-premio" @click="mostrarPremio = true">+ Registrar premio</button>
            </div>
            <div v-if="clienteDetalle.premios.length === 0" class="sin-datos-sm">Sin premios registrados</div>
            <div v-for="p in clienteDetalle.premios" :key="p.id" class="premio-item">
              <span class="premio-fecha">{{ formatFecha(p.fecha) }}</span>
              <span class="premio-desc">{{ p.descripcion }}</span>
              <span class="premio-tipo">{{ p.tipo }}</span>
            </div>

            <!-- Form premio -->
            <div v-if="mostrarPremio && esAdmin" class="premio-form">
              <select v-model="formPremio.tipo">
                <option value="por_cantidad">Por cantidad</option>
                <option value="por_monto">Por monto</option>
              </select>
              <input v-model="formPremio.descripcion" placeholder="Descripción del premio..." />
              <input v-model="formPremio.observacion" placeholder="Observación (opcional)" />
              <div class="form-botones">
                <button class="btn-cancelar" @click="mostrarPremio = false">Cancelar</button>
                <button class="btn-guardar" @click="registrarPremio">Guardar</button>
              </div>
            </div>
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
  name: 'Clientes',
  data() {
    return {
      usuario:       JSON.parse(localStorage.getItem('usuario') || '{}'),
      clientes:      [],
      busqueda:      '',
      mostrarForm:   false,
      editando:      false,
      clienteDetalle: null,
      mostrarPremio: false,
      form: {
        id: null, nombre: '', telefono: '', email: '',
        tipo_cliente: 'natural', rif_cedula: '', direccion: '', notas: ''
      },
      formPremio: { tipo: 'por_cantidad', descripcion: '', observacion: '' },
      prefijos: ['0412', '0424', '0416', '0414', '0426'],
      prefijoSeleccionado: '0414',
      telefonoNumeros: '',
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
  },
  async mounted() {
    await this.cargarClientes()
  },
  methods: {
    async cargarClientes() {
      const params = {}
      if (this.busqueda) params.buscar = this.busqueda
      const res = await axios.get('/clientes/', { params })
      this.clientes = res.data
    },
    abrirCrear() {
      this.form = { id: null, nombre: '', telefono: '', email: '', tipo_cliente: 'natural', rif_cedula: '', direccion: '', notas: '', tiene_credito: false, limite_credito: 0, saldo_credito: 0 }
      this.telefonoNumeros     = ''
      this.prefijoSeleccionado = '0414'
      this.editando    = false
      this.mostrarForm = true
    },
    abrirEditar(c) {
      this.form = { ...c }
      // Descomponer teléfono si tiene el formato prefijo+numero
      const tel = c.telefono || ''
      const prefijo = this.prefijos.find(p => tel.startsWith(p))
      if (prefijo) {
        this.prefijoSeleccionado = prefijo
        this.telefonoNumeros     = tel.slice(prefijo.length)
      } else {
        this.telefonoNumeros = tel
      }
      this.editando    = true
      this.mostrarForm = true
    },
    async guardar() {
      if (!this.form.nombre || !this.form.telefono) {
        alert('Nombre y teléfono son requeridos')
        return
      }
      try {
        if (this.editando) {
          await axios.put(`/clientes/${this.form.id}`, this.form)
        } else {
          await axios.post('/clientes/', this.form)
        }
        await this.cargarClientes()
        this.cerrarForm()
      } catch (e) {
        if (e?.response?.status === 409) {
          const nombre = e.response.data?.cliente_existente?.nombre || 'otro cliente'
          alert(`Ya existe un cliente con ese teléfono: "${nombre}"`)
        } else {
          const detalle = e?.response?.data?.detail || e?.message || 'Error desconocido'
          alert(`Error al guardar el cliente: ${detalle}`)
        }
      }
    },
    cerrarForm() {
      this.mostrarForm = false
      this.editando    = false
    },
    async verDetalle(c) {
      const res = await axios.get(`/clientes/${c.id}`)
      this.clienteDetalle = res.data
      this.mostrarPremio  = false
    },
    async desactivar(id) {
      if (confirm('¿Desactivar este cliente?')) {
        await axios.delete(`/clientes/${id}`)
        await this.cargarClientes()
      }
    },
    async registrarPremio() {
      if (!this.formPremio.descripcion) return
      await axios.post(`/clientes/${this.clienteDetalle.id}/premios`, {
        ...this.formPremio,
        otorgado_por: this.usuario.usuario || 'admin',
      })
      const res = await axios.get(`/clientes/${this.clienteDetalle.id}`)
      this.clienteDetalle = res.data
      this.mostrarPremio  = false
      this.formPremio     = { tipo: 'por_cantidad', descripcion: '', observacion: '' }
    },
    formatFecha(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleDateString('es-VE')
    },
    actualizarTelefono() {
      this.form.telefono = this.prefijoSeleccionado + this.telefonoNumeros
    },
    abrirWhatsapp(telefono) {
      const numero   = (telefono || '').replace(/\D/g, '')
      const numeroIntl = '58' + numero.slice(1)
      window.open(`https://wa.me/${numeroIntl}`, '_blank')
    },
    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    }
  }
}
</script>

<style scoped>
.badge-nivel { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 20px; font-size: 0.78rem; font-weight: 700; }
.badge-sin-nivel { color: var(--texto-muted); font-size: 0.82rem; }

/* Teléfono con prefijo */
.tel-input    { display: flex; flex-direction: column; gap: 0.4rem; }
.prefijos     { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.btn-prefijo  { background: #F5F5F0; color: #555; border: 1px solid #DDD; padding: 0.2rem 0.55rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.btn-prefijo.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; font-weight: 700; }
.tel-preview  { color: var(--texto-muted); font-size: 0.78rem; margin-top: 0.15rem; }

.btn-whatsapp { background: #25D366; color: white; border: none; padding: 0.3rem 0.55rem; border-radius: 5px; cursor: pointer; font-size: 0.82rem; margin-right: 0.3rem; }

.btn-ver      { background: #F5F5F0; color: #1A1A1A; border: 1px solid #DDDDDD; padding: 0.3rem 0.7rem; border-radius: 5px; cursor: pointer; font-size: 0.82rem; margin-right: 0.3rem; }
.btn-editar   { background: #2563EB; color: white; border: none; padding: 0.3rem 0.7rem; border-radius: 5px; cursor: pointer; margin-right: 0.3rem; font-size: 0.82rem; }
.btn-eliminar { background: transparent; color: #DC2626; border: 1px solid #DC2626; padding: 0.25rem 0.5rem; border-radius: 5px; cursor: pointer; font-size: 0.82rem; }

.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.55rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: 600; }
.btn-cancelar { background: transparent; color: #1A1A1A; border: 1px solid #DDDDDD; padding: 0.55rem 1.2rem; border-radius: 6px; cursor: pointer; }

.codigo-cli { font-size: 0.78rem; font-weight: 700; color: #996600; background: #FFCC0033; padding: 0.15rem 0.4rem; border-radius: 4px; }

/* Overlay / Dialog */
.dialog-grande { max-width: 720px; }

/* Detalle */
.detalle-header { display: flex; gap: 1rem; align-items: flex-start; margin-bottom: 1.5rem; }
.detalle-header h2 { color: var(--texto-principal); margin: 0 0 0.25rem; }
.detalle-sub { color: var(--texto-muted); font-size: 0.85rem; margin: 0; }
.badge-grande { padding: 0.35rem 1rem; font-size: 0.88rem; margin-top: 0.25rem; }
.btn-cerrar-x { margin-left: auto; background: transparent; color: var(--texto-muted); border: none; font-size: 1.2rem; cursor: pointer; }

.stats-row { display: flex; gap: 1.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.stat-box { background: #FAFAF7; border: 1px solid var(--borde); border-radius: 10px; padding: 1rem 1.5rem; }
.stat-label { color: var(--texto-muted); font-size: 0.8rem; margin: 0 0 0.3rem; }
.stat-valor { color: var(--texto-principal); font-size: 1.6rem; font-weight: 600; margin: 0; }
.stat-valor-sm { color: #16A34A; font-size: 0.88rem; margin: 0; }

.seccion-titulo { color: var(--texto-principal); font-size: 1rem; margin: 1.5rem 0 0.75rem; }

.premios-header { display: flex; align-items: center; gap: 1rem; }
.btn-premio { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.35rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.sin-datos-sm { color: var(--texto-muted); font-size: 0.85rem; margin: 0.5rem 0 1rem; }
.premio-item { display: flex; gap: 1rem; padding: 0.5rem 0; border-bottom: 1px solid var(--borde-suave); }
.premio-fecha { color: var(--texto-muted); font-size: 0.82rem; white-space: nowrap; }
.premio-desc { color: var(--texto-sec); flex: 1; font-size: 0.88rem; }
.premio-tipo { color: #16A34A; font-size: 0.78rem; }

.premio-form { background: #FAFAF7; border-radius: 8px; padding: 1rem; margin-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem; border: 1px solid var(--borde); }

/* Crédito en tabla */
.badge-credito { display: inline-block; background: #16A34A1A; color: #16A34A; font-size: 0.78rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 12px; }
.txt-muted-sm  { color: var(--texto-muted); font-size: 0.82rem; }

/* Crédito en formulario */
.credito-section { border-top: 1px solid var(--borde-suave); padding-top: 0.75rem; }
.credito-toggle  { margin-bottom: 0.5rem; }
.toggle-label    { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; color: var(--texto-sec); font-size: 0.9rem; font-weight: 600; }
.toggle-label input[type="checkbox"] { width: 16px; height: 16px; cursor: pointer; }
.credito-campos  { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-top: 0.5rem; }
</style>
