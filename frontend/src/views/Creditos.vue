<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Créditos a Clientes</h1>
      </div>

      <div class="contenido-inner">

        <!-- Buscador -->
        <div class="busqueda-wrap">
          <input
            v-model="busqueda"
            @input="buscar"
            placeholder="Teléfono o nombre del cliente..."
            class="buscador"
          />
          <div v-if="resultados.length > 0" class="dropdown">
            <div
              v-for="c in resultados" :key="c.id"
              class="opcion" @click="seleccionarCliente(c)"
            >
              <span class="opcion-tel">📱 {{ c.telefono }}</span>
              <span class="opcion-nombre">— {{ c.nombre }}</span>
              <span v-if="c.tiene_credito" class="opcion-badge">
                Saldo: ${{ (c.saldo_credito || 0).toFixed(2) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Vista de cliente seleccionado -->
        <div v-if="clienteSeleccionado" class="cliente-panel">

          <!-- Encabezado -->
          <div class="panel-header">
            <div>
              <h2>{{ clienteSeleccionado.nombre }}</h2>
              <p class="sub">{{ clienteSeleccionado.telefono }}
                <span v-if="clienteSeleccionado.codigo"> · {{ clienteSeleccionado.codigo }}</span>
              </p>
            </div>
            <button class="btn-limpiar" @click="limpiar">Cambiar cliente</button>
          </div>

          <!-- Crédito no habilitado -->
          <div v-if="!clienteSeleccionado.tiene_credito" class="aviso-sin-credito">
            <p>Este cliente no tiene crédito habilitado.</p>
            <p v-if="esAdmin">Ve a <strong>Clientes → Editar</strong> para habilitarlo.</p>
          </div>

          <!-- Estado de cuenta -->
          <div v-else>
            <div class="stats-credito">
              <div class="stat">
                <p class="stat-label">Límite de crédito</p>
                <p class="stat-val">${{ (clienteSeleccionado.limite_credito || 0).toFixed(2) }}</p>
              </div>
              <div class="stat">
                <p class="stat-label">Saldo disponible</p>
                <p class="stat-val" :class="credito.saldo_credito > 0 ? 'txt-verde' : 'txt-rojo'">
                  ${{ (credito.saldo_credito || 0).toFixed(2) }}
                </p>
              </div>
              <div class="stat">
                <p class="stat-label">Deuda actual</p>
                <p class="stat-val txt-rojo">
                  ${{ Math.max(0, (clienteSeleccionado.limite_credito || 0) - (credito.saldo_credito || 0)).toFixed(2) }}
                </p>
              </div>
            </div>

            <!-- Barra de uso de crédito -->
            <div class="barra-credito-wrap" v-if="clienteSeleccionado.limite_credito > 0">
              <div class="barra-credito">
                <div class="barra-fill"
                  :style="{ width: porcentajeUso + '%' }"
                  :class="porcentajeUso > 80 ? 'barra-peligro' : ''">
                </div>
              </div>
              <span class="barra-label">{{ porcentajeUso.toFixed(0) }}% utilizado</span>
            </div>

            <!-- Formulario de abono (admin) -->
            <div v-if="esAdmin" class="abono-form">
              <h3>Registrar abono</h3>
              <div class="form-row">
                <div class="field">
                  <label>Monto (USD)</label>
                  <input v-model.number="formAbono.monto" type="number" min="0.01" step="0.01" placeholder="0.00" />
                </div>
                <div class="field">
                  <label>Método de pago</label>
                  <select v-model="formAbono.metodo_pago">
                    <option value="efectivo_usd">Efectivo $</option>
                    <option value="zelle">Zelle</option>
                    <option value="binance">Binance</option>
                    <option value="transferencia_bs">Transferencia Bs</option>
                    <option value="pago_movil">Pago Móvil</option>
                  </select>
                </div>
                <div class="field">
                  <label>Observación</label>
                  <input v-model="formAbono.observacion" placeholder="Referencia o nota..." />
                </div>
              </div>
              <button class="btn-abonar" @click="registrarAbono"
                :disabled="!formAbono.monto || formAbono.monto <= 0 || guardando">
                {{ guardando ? 'Guardando...' : 'Registrar abono' }}
              </button>
              <p class="msg-error" v-if="errorAbono">{{ errorAbono }}</p>
              <p class="msg-ok"    v-if="abonoOk">Abono registrado correctamente</p>
            </div>

            <!-- Historial de movimientos -->
            <div class="movimientos">
              <h3>Historial de movimientos</h3>
              <div v-if="cargandoCredito" class="sin-datos">Cargando...</div>
              <table v-else-if="credito.movimientos && credito.movimientos.length > 0">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Tipo</th>
                    <th>Monto</th>
                    <th>Método</th>
                    <th>Referencia</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="m in credito.movimientos" :key="m.id">
                    <td class="txt-muted">{{ formatFecha(m.fecha) }}</td>
                    <td>
                      <span :class="m.monto > 0 ? 'tag-abono' : 'tag-cargo'">
                        {{ m.monto > 0 ? 'Abono' : 'Cargo' }}
                      </span>
                    </td>
                    <td :class="m.monto > 0 ? 'txt-verde' : 'txt-rojo'">
                      {{ m.monto > 0 ? '+' : '' }}${{ Math.abs(m.monto).toFixed(2) }}
                    </td>
                    <td>{{ m.metodo_pago ? labelMetodo(m.metodo_pago) : (m.venta_id ? `Venta #${m.venta_id}` : '—') }}</td>
                    <td class="txt-muted">{{ m.observacion || '—' }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="sin-datos">Sin movimientos registrados</div>
            </div>
          </div>
        </div>

        <!-- Estado vacío -->
        <div v-else class="vacio">
          <p>Busca un cliente para ver su estado de crédito</p>
        </div>

      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

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

export default {
  components: { AppSidebar },
  name: 'Creditos',
  data() {
    return {
      usuario:           JSON.parse(localStorage.getItem('usuario') || '{}'),
      busqueda:          '',
      resultados:        [],
      busquedaTimer:     null,
      clienteSeleccionado: null,
      credito: {
        tiene_credito:  false,
        limite_credito: 0,
        saldo_credito:  0,
        movimientos:    [],
      },
      cargandoCredito: false,
      formAbono: {
        monto:       '',
        metodo_pago: 'efectivo_usd',
        observacion: '',
      },
      guardando:  false,
      errorAbono: '',
      abonoOk:    false,
    }
  },
  computed: {
    esAdmin() { return this.usuario.rol === 'admin' },
    porcentajeUso() {
      const limite = this.clienteSeleccionado?.limite_credito || 0
      if (!limite) return 0
      const usado  = limite - (this.credito.saldo_credito || 0)
      return Math.min(100, Math.max(0, (usado / limite) * 100))
    },
  },
  methods: {
    buscar() {
      clearTimeout(this.busquedaTimer)
      if (!this.busqueda || this.busqueda.length < 2) { this.resultados = []; return }
      this.busquedaTimer = setTimeout(async () => {
        try {
          const res = await axios.get('/clientes/buscar-rapido', { params: { q: this.busqueda } })
          this.resultados = res.data
        } catch { this.resultados = [] }
      }, 200)
    },
    async seleccionarCliente(c) {
      this.clienteSeleccionado = c
      this.busqueda            = ''
      this.resultados          = []
      this.abonoOk             = false
      this.errorAbono          = ''
      await this.cargarCredito(c.id)
    },
    async cargarCredito(clienteId) {
      this.cargandoCredito = true
      try {
        const res        = await axios.get(`/clientes/${clienteId}/credito`)
        this.credito     = res.data
        // Actualizar saldo en cliente seleccionado
        this.clienteSeleccionado.saldo_credito = res.data.saldo_credito
      } catch (e) {
        console.error(e)
      } finally {
        this.cargandoCredito = false
      }
    },
    async registrarAbono() {
      if (!this.formAbono.monto || this.formAbono.monto <= 0) return
      this.guardando  = true
      this.errorAbono = ''
      this.abonoOk    = false
      try {
        await axios.post(`/clientes/${this.clienteSeleccionado.id}/abono`, {
          monto:       Number(this.formAbono.monto),
          metodo_pago: this.formAbono.metodo_pago,
          observacion: this.formAbono.observacion,
          usuario:     this.usuario.usuario || 'admin',
        })
        this.abonoOk      = true
        this.formAbono.monto       = ''
        this.formAbono.observacion = ''
        await this.cargarCredito(this.clienteSeleccionado.id)
        setTimeout(() => { this.abonoOk = false }, 4000)
      } catch (e) {
        this.errorAbono = e?.response?.data?.detail || 'Error al registrar el abono'
      } finally {
        this.guardando = false
      }
    },
    limpiar() {
      this.clienteSeleccionado = null
      this.credito             = { tiene_credito: false, limite_credito: 0, saldo_credito: 0, movimientos: [] }
      this.busqueda            = ''
    },
    labelMetodo(m) { return LABELS[m] || m },
    formatFecha(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleString('es-VE', { dateStyle: 'short', timeStyle: 'short' })
    },
  },
}
</script>

<style scoped>
.busqueda-wrap { position: relative; max-width: 520px; margin-bottom: 1.5rem; }
.buscador { width: 100%; padding: 0.65rem 1rem; background: #FFFFFF; border: 1px solid #CCCCCC; border-radius: 10px; font-size: 0.95rem; color: var(--texto-principal); box-sizing: border-box; }
.buscador:focus { outline: none; border-color: #FFCC00; }

.dropdown { position: absolute; top: calc(100% + 4px); left: 0; right: 0; background: #FFFFFF; border: 1px solid var(--borde); border-radius: 10px; z-index: 50; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.opcion { display: flex; align-items: center; gap: 0.75rem; padding: 0.65rem 1rem; cursor: pointer; border-bottom: 1px solid var(--borde-suave); font-size: 0.9rem; }
.opcion:hover { background: var(--fondo-tabla-alt); }
.opcion-nombre { color: var(--texto-principal); font-weight: 600; }
.opcion-tel    { color: var(--texto-muted); font-size: 0.82rem; }
.opcion-badge  { margin-left: auto; background: #16A34A1A; color: #16A34A; font-size: 0.78rem; font-weight: 700; padding: 0.1rem 0.5rem; border-radius: 12px; }

.vacio { text-align: center; padding: 4rem 0; color: var(--texto-muted); font-size: 1rem; }

/* Panel de cliente */
.cliente-panel { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 14px; padding: 1.5rem; }

.panel-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem; }
.panel-header h2 { color: var(--texto-principal); margin: 0 0 0.25rem; font-size: 1.2rem; }
.sub { color: var(--texto-muted); font-size: 0.85rem; margin: 0; }
.btn-limpiar { padding: 0.4rem 1rem; background: transparent; border: 1px solid var(--borde); color: var(--texto-sec); border-radius: 7px; cursor: pointer; font-size: 0.85rem; }
.btn-limpiar:hover { border-color: #1A1A1A; color: #1A1A1A; }

.aviso-sin-credito { background: #FFF7ED; border: 1px solid #F59E0B; border-radius: 10px; padding: 1rem 1.25rem; color: #92400E; font-size: 0.9rem; }

.stats-credito { display: flex; gap: 1.25rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.stat { background: #FAFAF7; border: 1px solid var(--borde); border-radius: 10px; padding: 1rem 1.4rem; min-width: 160px; }
.stat-label { color: var(--texto-muted); font-size: 0.8rem; margin: 0 0 0.3rem; }
.stat-val   { color: var(--texto-principal); font-size: 1.5rem; font-weight: 700; margin: 0; }
.txt-verde  { color: #16A34A !important; }
.txt-rojo   { color: #DC2626 !important; }
.txt-muted  { color: var(--texto-muted); font-size: 0.85rem; }

.barra-credito-wrap { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; }
.barra-credito { flex: 1; height: 8px; background: #E5E7EB; border-radius: 4px; overflow: hidden; }
.barra-fill    { height: 100%; background: #16A34A; border-radius: 4px; transition: width 0.4s; }
.barra-peligro { background: #DC2626 !important; }
.barra-label   { color: var(--texto-muted); font-size: 0.82rem; white-space: nowrap; }

/* Formulario de abono */
.abono-form { background: #FAFAF7; border: 1px solid var(--borde); border-radius: 10px; padding: 1.25rem; margin-bottom: 1.5rem; }
.abono-form h3 { color: var(--texto-principal); font-size: 0.95rem; margin: 0 0 1rem; }
.form-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.75rem; margin-bottom: 0.9rem; }
.field label { color: var(--texto-sec); font-size: 0.82rem; display: block; margin-bottom: 0.3rem; font-weight: 600; }
.field input, .field select {
  width: 100%; padding: 0.5rem 0.75rem;
  background: #FFFFFF; border: 1px solid #CCCCCC;
  color: var(--texto-principal); border-radius: 8px;
  font-size: 0.9rem; box-sizing: border-box;
}
.btn-abonar { padding: 0.6rem 1.5rem; background: #1A1A1A; color: #FFCC00; border: none; border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 0.9rem; }
.btn-abonar:disabled { opacity: 0.45; cursor: not-allowed; }
.msg-error { color: #DC2626; font-size: 0.85rem; margin: 0.5rem 0 0; }
.msg-ok    { color: #16A34A; font-size: 0.85rem; margin: 0.5rem 0 0; font-weight: 600; }

/* Movimientos */
.movimientos h3 { color: var(--texto-principal); font-size: 0.95rem; margin: 0 0 0.75rem; }
.sin-datos      { text-align: center; color: var(--texto-muted); padding: 1.5rem 0; font-size: 0.9rem; }

.tag-abono { display: inline-block; background: #16A34A1A; color: #16A34A; font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 12px; }
.tag-cargo { display: inline-block; background: #DC26261A; color: #DC2626; font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 12px; }
</style>