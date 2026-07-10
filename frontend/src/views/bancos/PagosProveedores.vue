<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Pagos a Proveedores</h1>
      </div>

      <div class="contenido-inner">
        <!-- Tabla de deuda -->
        <div class="tabla-container">
          <table>
            <thead>
              <tr><th>Proveedor</th><th>Total comprado</th><th>Total pagado</th><th>Saldo pendiente</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="p in deuda" :key="p.proveedor_id"
                :class="{ 'sin-deuda': p.saldo_pendiente <= 0 }">
                <td style="font-weight:600">{{ p.proveedor }}</td>
                <td>${{ p.total_comprado.toFixed(2) }}</td>
                <td class="txt-verde">${{ p.total_pagado.toFixed(2) }}</td>
                <td :class="p.saldo_pendiente > 0 ? 'txt-rojo' : 'txt-verde'">
                  ${{ p.saldo_pendiente.toFixed(2) }}
                </td>
                <td>
                  <button class="btn-pagar" @click="abrirPago(p)" :disabled="p.saldo_pendiente <= 0">
                    Registrar pago
                  </button>
                  <button class="btn-historial" @click="verHistorial(p.proveedor_id)">Historial</button>
                  <button class="btn-ajuste-deuda" @click="abrirAjusteDeuda(p)">✏️ Ajustar deuda</button>
                </td>
              </tr>
              <tr v-if="deuda.length === 0">
                <td colspan="5" class="sin-datos">Sin deuda con proveedores</td>
              </tr>
            </tbody>
          </table>
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
                <span class="txt-rojo">${{ fmt(liquidez[capaActiva].deuda_proveedores) }}</span>
              </div>
              <div v-if="capaActiva === 'realista' && liquidez.realista.abonos_proyectados > 0" class="liquidez-linea sub">
                <span style="color:var(--texto-muted)">  − Abonos proyectados 10d</span>
                <span class="txt-verde">−${{ fmt(liquidez.realista.abonos_proyectados) }}</span>
              </div>
              <div class="liquidez-linea">
                <span>+ Ventas proyectadas 10d</span>
                <span>${{ fmt(liquidez[capaActiva].proyeccion_ventas_10d) }}</span>
              </div>
              <div class="liquidez-linea">
                <span>− Crédito proveedores ({{ liquidez[capaActiva].dias_credito_usados }}d prom.)</span>
                <span class="txt-verde">−${{ fmt(liquidez[capaActiva].credito_proveedores) }}</span>
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
                <span style="color:var(--texto-muted);font-size:0.75rem">(edita el «real» para ajustar el cálculo)</span>
              </div>
              <div v-for="d in liquidez.detalle_proveedores" :key="d.proveedor_id"
                class="liquidez-prov-row">
                <span class="lp-nombre">{{ d.proveedor }}</span>
                <span class="lp-saldo txt-rojo">${{ fmt(d.saldo) }}</span>
                <span class="lp-label" style="color:var(--texto-muted)">Formal:</span>
                <span class="lp-dias">{{ d.dias_credito_formal }}d</span>
                <span class="lp-label" style="color:var(--texto-muted)">Real:</span>
                <input type="number" :value="d.dias_credito_real"
                  class="lp-input-dias"
                  min="0" max="365"
                  @change="actualizarCreditoReal(d.proveedor_id, $event.target.value)" />
                <span class="lp-label" style="color:var(--texto-muted)">d</span>
                <span v-if="d.abono_proyectado_10d > 0" class="lp-abono txt-verde">
                  −${{ fmt(d.abono_proyectado_10d) }} abono est.
                </span>
              </div>
            </div>
          </div>

          <div v-else class="liquidez-loading" style="color:var(--texto-muted)">Sin datos suficientes para calcular</div>
        </div>
        <!-- fin WIDGET LIQUIDEZ -->

        <!-- Modal pago -->
        <div class="overlay" v-if="proveedorPago" @click.self="cerrarPago">
          <div class="modal">
            <div class="modal-header">
              <h2>Pago a {{ proveedorPago.proveedor }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarPago">✕</button>
            </div>
            <p class="deuda-info">Saldo pendiente: <strong class="txt-rojo">${{ proveedorPago.saldo_pendiente.toFixed(2) }}</strong></p>
            <div class="form-grid">
              <!-- Selector moneda -->
              <div class="field field-wide">
                <label>Moneda del pago</label>
                <div class="moneda-toggle">
                  <button
                    :class="['btn-moneda', formPago.moneda === 'USD' ? 'activo' : '']"
                    @click="formPago.moneda = 'USD'; formPago.cuenta_id = ''; formPago.tasa_cambio = ''"
                    type="button"
                  >💵 USD</button>
                  <button
                    :class="['btn-moneda', formPago.moneda === 'Bs' ? 'activo' : '']"
                    @click="formPago.moneda = 'Bs'; formPago.cuenta_id = ''"
                    type="button"
                  >🇻🇪 Bolívares</button>
                </div>
              </div>

              <!-- Tasa manual (solo Bs) -->
              <div class="field" v-if="formPago.moneda === 'Bs'">
                <label>Tasa de cambio del día del pago (Bs por $1)</label>
                <input
                  v-model.number="formPago.tasa_cambio"
                  type="number" min="0" step="0.01"
                  placeholder="Ej: 92.50"
                />
                <span class="field-hint">
                  Ingresa la tasa BCV o acordada del día que se realizó el pago
                </span>
              </div>

              <!-- Cuenta bancaria -->
              <div class="field">
                <label>Cuenta bancaria origen</label>
                <select v-model="formPago.cuenta_id">
                  <option value="">— Seleccionar cuenta {{ formPago.moneda }} —</option>
                  <option v-for="c in cuentasDisponibles" :key="c.id" :value="c.id">
                    {{ c.nombre }}
                    ({{ c.moneda === 'USD' ? '$' : 'Bs.' }}{{ c.saldo.toFixed(2) }})
                  </option>
                </select>
                <span v-if="cuentasDisponibles.length === 0" class="aviso-sin-cuentas">
                  ⚠ No hay cuentas en {{ formPago.moneda }} disponibles
                </span>
              </div>

              <!-- Monto -->
              <div class="field">
                <label>Monto a pagar ({{ formPago.moneda }})</label>
                <input
                  v-model.number="formPago.monto"
                  type="number" min="0" step="0.01"
                  :placeholder="formPago.moneda === 'USD'
                    ? 'Máx. $' + proveedorPago.saldo_pendiente.toFixed(2)
                    : 'Monto en Bs'"
                />
                <span v-if="formPago.moneda === 'Bs' && montoUSDEquivalente" class="equiv-usd">
                  ≈ ${{ montoUSDEquivalente }} USD
                  <span
                    v-if="parseFloat(montoUSDEquivalente) > proveedorPago.saldo_pendiente"
                    class="aviso-exceso"
                  > ⚠ Excede la deuda</span>
                </span>
              </div>

              <!-- Referencia -->
              <div class="field">
                <label>Referencia bancaria</label>
                <input v-model="formPago.referencia" placeholder="Nro. operación" />
              </div>

              <!-- Orden de compra -->
              <div class="field">
                <label>Orden de compra (opcional)</label>
                <select v-model="formPago.orden_compra_id">
                  <option value="">— Sin asociar —</option>
                  <option v-for="o in ordenesProveedor" :key="o.id" :value="o.id">
                    {{ o.numero }}
                    (${{ o.total.toFixed ? o.total.toFixed(2) : o.total }})
                  </option>
                </select>
              </div>
            </div>
            <div class="form-botones">
              <button class="btn-cancelar" @click="cerrarPago">Cancelar</button>
              <button class="btn-confirmar" @click="confirmarPago" :disabled="pagando">
                {{ pagando ? 'Procesando...' : 'Confirmar pago' }}
              </button>
            </div>
            <p class="msg-error" v-if="errorPago">{{ errorPago }}</p>
          </div>
        </div>

        <!-- Modal historial -->
        <div class="overlay" v-if="historial" @click.self="historial = null">
          <div class="modal">
            <div class="modal-header">
              <h2>Historial — {{ historial.proveedor }}</h2>
              <button class="btn-cerrar-modal" @click="historial = null">✕</button>
            </div>
            <div class="resumen-hist">
              <span>Comprado: <strong>${{ historial.total_comprado.toFixed(2) }}</strong></span>
              <span>Pagado: <strong class="txt-verde">${{ historial.total_pagado.toFixed(2) }}</strong></span>
              <span>Pendiente: <strong class="txt-rojo">${{ historial.saldo_pendiente.toFixed(2) }}</strong></span>
            </div>
            <h3 class="subtitulo-hist">Órdenes de compra</h3>
            <table>
              <thead><tr><th>Número</th><th>Estado</th><th>Total</th></tr></thead>
              <tbody>
                <tr v-for="o in historial.ordenes" :key="o.id">
                  <td>{{ o.numero }}</td>
                  <td><span :class="'badge badge-' + o.estado">{{ o.estado }}</span></td>
                  <td>${{ Number(o.total).toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
            <h3 class="subtitulo-hist">Pagos realizados</h3>
            <table>
              <thead><tr><th>Fecha</th><th>Monto</th><th>Referencia</th></tr></thead>
              <tbody>
                <tr v-for="p in historial.pagos" :key="p.id">
                  <td>{{ formatFecha(p.fecha) }}</td>
                  <td class="txt-verde">
                    {{ p.moneda === 'Bs' ? 'Bs.' : '$' }}{{ p.monto.toFixed(2) }}
                    <span v-if="p.moneda === 'Bs' && p.monto_convertido" class="equiv-hist">
                      ≈ ${{ Number(p.monto_convertido).toFixed(2) }}
                    </span>
                    <span v-if="p.moneda === 'Bs' && p.tasa_cambio" class="tasa-hist">
                      @{{ p.tasa_cambio }}
                    </span>
                  </td>
                  <td>{{ p.referencia || '—' }}</td>
                </tr>
                <tr v-if="historial.pagos.length === 0">
                  <td colspan="3" class="sin-datos">Sin pagos registrados</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <!-- Modal ajuste de deuda -->
        <div class="overlay" v-if="modalAjusteDeuda" @click.self="modalAjusteDeuda = false">
          <div class="modal" style="max-width:420px">
            <div class="modal-header">
              <h2>Ajustar deuda — {{ ajusteDeudaProv?.proveedor }}</h2>
              <button class="btn-cerrar-modal" @click="modalAjusteDeuda = false">✕</button>
            </div>
            <div style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem">
              <div class="field">
                <label>Monto a descontar de la deuda (USD)</label>
                <input v-model.number="ajusteMonto" type="number" min="0" step="0.01"
                  placeholder="0.00" class="input-field" />
              </div>
              <div class="field">
                <label>Motivo del ajuste</label>
                <input v-model="ajusteMotivo"
                  placeholder="ej: Nota de crédito, descuento acordado..."
                  class="input-field" />
              </div>
              <p style="font-size:0.82rem;color:var(--texto-muted)">
                ⚠ Este ajuste reduce la deuda registrada sin afectar las cuentas bancarias.
              </p>
            </div>
            <div class="form-botones">
              <button class="btn-cancelar" @click="modalAjusteDeuda = false">Cancelar</button>
              <button class="btn-confirmar" @click="confirmarAjusteDeuda"
                :disabled="ajustando || !ajusteMonto">
                {{ ajustando ? 'Ajustando...' : 'Confirmar ajuste' }}
              </button>
            </div>
          </div>
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
  name: 'PagosProveedores',
  data() {
    return {
      usuario:          JSON.parse(localStorage.getItem('usuario') || '{}'),
      deuda:            [],
      cuentas:          [],
      proveedorPago:    null,
      ordenesProveedor: [],
      historial:        null,
      pagando:          false,
      errorPago:        '',
      modalAjusteDeuda: false,
      ajusteDeudaProv:  null,
      ajusteMonto:      null,
      ajusteMotivo:     '',
      ajustando:        false,
      liquidez:         null,
      cargandoLiquidez: false,
      colchonPct:       18,
      capaActiva:       'realista',
      formPago: {
        cuenta_id:       '',
        monto:           '',
        referencia:      '',
        orden_compra_id: '',
        moneda:          'USD',
        tasa_cambio:     '',
      },
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
    cuentasUSD() { return this.cuentas.filter(c => c.moneda === 'USD') },
    cuentasBs() { return this.cuentas.filter(c => c.moneda === 'Bs') },
    cuentasDisponibles() {
      return this.formPago.moneda === 'USD' ? this.cuentasUSD : this.cuentasBs
    },
    montoUSDEquivalente() {
      if (this.formPago.moneda === 'USD') return this.formPago.monto
      const tasa = parseFloat(this.formPago.tasa_cambio)
      if (!tasa || tasa <= 0 || !this.formPago.monto) return null
      return (parseFloat(this.formPago.monto) / tasa).toFixed(2)
    },
  },
  async mounted() {
    await Promise.all([this.cargar(), this.cargarCuentas()])
    this.cargarLiquidez()
  },
  methods: {
    async cargar() {
      const res = await axios.get('/bancos/proveedores/deuda/')
      this.deuda = res.data
    },
    async cargarCuentas() {
      const res = await axios.get('/bancos/cuentas/')
      this.cuentas = res.data
    },
    async abrirPago(p) {
      this.proveedorPago    = p
      this.errorPago        = ''
      this.formPago         = { cuenta_id: '', monto: '', referencia: '', orden_compra_id: '', moneda: 'USD', tasa_cambio: '' }
      const res             = await axios.get(`/bancos/proveedores/${p.proveedor_id}/estado/`)
      this.ordenesProveedor = res.data.ordenes.filter(o => ['recibida_parcial','cerrada'].includes(o.estado))
    },
    cerrarPago() {
      this.proveedorPago = null
      this.formPago = { cuenta_id: '', monto: '', referencia: '', orden_compra_id: '', moneda: 'USD', tasa_cambio: '' }
    },
    async confirmarPago() {
      if (!this.formPago.cuenta_id) { this.errorPago = 'Selecciona la cuenta bancaria'; return }
      if (!this.formPago.monto || this.formPago.monto <= 0) { this.errorPago = 'Ingresa un monto válido'; return }
      if (this.formPago.moneda === 'Bs' && !this.formPago.tasa_cambio) {
        this.errorPago = 'Ingresa la tasa de cambio para pagos en Bs'; return
      }
      this.pagando = true; this.errorPago = ''
      try {
        await axios.post(
          `/bancos/proveedores/${this.proveedorPago.proveedor_id}/pago/`,
          {
            cuenta_id:       this.formPago.cuenta_id,
            monto:           this.formPago.monto,
            moneda:          this.formPago.moneda,
            tasa_cambio:     this.formPago.moneda === 'Bs' ? this.formPago.tasa_cambio : null,
            referencia:      this.formPago.referencia,
            orden_compra_id: this.formPago.orden_compra_id || null,
            registrado_por:  this.usuario.usuario || 'admin',
          }
        )
        await Promise.all([this.cargar(), this.cargarCuentas()])
        this.cerrarPago()
      } catch (e) {
        this.errorPago = e?.response?.data?.detail || 'Error al registrar el pago'
      } finally {
        this.pagando = false
      }
    },
    async verHistorial(proveedorId) {
      const res = await axios.get(`/bancos/proveedores/${proveedorId}/estado/`)
      this.historial = res.data
    },
    abrirAjusteDeuda(prov) {
      this.ajusteDeudaProv  = prov
      this.ajusteMonto      = null
      this.ajusteMotivo     = ''
      this.modalAjusteDeuda = true
    },
    async confirmarAjusteDeuda() {
      if (!this.ajusteMonto || this.ajusteMonto <= 0) {
        alert('Ingresa un monto válido')
        return
      }
      this.ajustando = true
      try {
        await axios.post(
          `/bancos/proveedores/${this.ajusteDeudaProv.proveedor_id}/ajuste-deuda`,
          { monto: this.ajusteMonto, motivo: this.ajusteMotivo || 'Ajuste manual' },
          { headers: { 'x-usuario-nombre': this.usuario.usuario || '' } }
        )
        this.modalAjusteDeuda = false
        await this.cargar()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al ajustar deuda')
      } finally { this.ajustando = false }
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
    fmt(v) { return Number(v || 0).toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) },
    formatFecha(iso) { return iso ? new Date(iso).toLocaleDateString('es-VE') : '—' },
    salir() { localStorage.removeItem('usuario'); this.$router.push('/login') },
  },
}
</script>

<style scoped>
.sin-deuda td { opacity: 0.45; }
.btn-pagar    { background: var(--success); color: white; border: none; padding: 0.3rem 0.7rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; margin-right: 0.3rem; }
.btn-pagar:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-historial{ background: #1A1A1A; color: #FFFFFF; border: 1px solid var(--borde); padding: 0.3rem 0.7rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; }

.deuda-info { color: var(--texto-sec); font-size: 0.9rem; margin-bottom: 1rem; }
.btn-confirmar { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-confirmar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; }

.resumen-hist { display: flex; gap: 2rem; background: var(--borde-suave); padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem; flex-wrap: wrap; border: 1px solid var(--borde); }
.resumen-hist span { color: var(--texto-sec); font-size: 0.9rem; }
.resumen-hist strong { color: var(--texto-principal); }
.subtitulo-hist { color: var(--texto-principal); font-size: 0.85rem; margin: 1rem 0 0.5rem; font-weight: 700; }

.badge-aprobada { background: #16A34A1A; color: #16A34A; }
.badge-cerrada  { background: #8888881A; color: #555555; }
.badge-recibida_parcial { background: #FFCC0033; color: #996600; }

.moneda-toggle { display: flex; gap: 0.5rem; }
.btn-moneda {
  flex: 1; padding: 0.5rem; border-radius: 6px; cursor: pointer;
  border: 2px solid var(--borde); background: white;
  font-weight: 600; font-size: 0.85rem; transition: all 0.15s;
}
.btn-moneda.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }
.field-hint { font-size: 0.72rem; color: var(--texto-muted); display: block; margin-top: 0.25rem; }
.equiv-usd { display: block; margin-top: 0.3rem; font-size: 0.82rem; color: #16A34A; font-weight: 600; }
.aviso-exceso { color: #DC2626; font-size: 0.78rem; }
.aviso-sin-cuentas { display: block; margin-top: 0.25rem; font-size: 0.78rem; color: #DC2626; font-weight: 600; }
.equiv-hist { font-size: 0.75rem; color: #16A34A; margin-left: 0.3rem; }
.tasa-hist { font-size: 0.72rem; color: var(--texto-muted); margin-left: 0.3rem; }
.btn-ajuste-deuda { background: #F1F5F9; border: 1px solid var(--borde); border-radius: 6px; padding: 0.35rem 0.75rem; font-size: 0.82rem; cursor: pointer; color: var(--texto-sec); margin-left: 0.3rem; }
.btn-ajuste-deuda:hover { border-color: #FFCC00; background: #FFFDF0; }
.input-field { border: 1px solid var(--borde); border-radius: 6px; padding: 0.5rem 0.65rem; font-size: 0.875rem; color: var(--texto-principal); background: var(--fondo-app, #fff); width: 100%; box-sizing: border-box; }
.input-field:focus { outline: none; border-color: #FFCC00; }
/* ── Widget Liquidez Prudente ── */
.liquidez-widget { background:var(--fondo-card); border:1px solid var(--borde); border-radius:10px; padding:1.2rem 1.4rem; }
.liquidez-header { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.6rem; margin-bottom:1rem; }
.panel-titulo { font-size:1rem; font-weight:700; color:var(--texto-principal); }
.liquidez-controles { display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap; }
.liquidez-input-pct { width:52px; text-align:center; border:1px solid var(--borde); border-radius:5px; padding:3px 5px; font-size:0.85rem; background:var(--fondo-input,#fff); color:var(--texto-principal); }
.btn-toggle-capa { padding:4px 12px; border:1px solid var(--borde); border-radius:6px; background:var(--fondo-app,#fff); color:var(--texto-sec); cursor:pointer; font-size:0.8rem; }
.btn-toggle-capa.activo { background:#FFCC00; color:#1A1A1A; border-color:#FFCC00; font-weight:600; }
.btn-reload-liquidez { padding:4px 10px; border:1px solid var(--borde); border-radius:6px; background:transparent; cursor:pointer; font-size:1rem; color:var(--texto-sec); }
.liquidez-loading { text-align:center; padding:1.5rem; color:var(--texto-muted); font-size:0.9rem; }
.liquidez-body { display:grid; grid-template-columns:200px 1fr 1fr; gap:1.5rem; }
@media (max-width:900px) { .liquidez-body { grid-template-columns:1fr; } }
.liquidez-principal { background:var(--fondo-app,#fafafa); border-radius:8px; padding:1rem; text-align:center; border:1px solid var(--borde); }
.liquidez-label { font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:var(--texto-muted); margin-bottom:0.4rem; }
.liquidez-monto { font-size:2rem; font-weight:700; color:var(--texto-principal); }
.liquidez-sub { font-size:0.75rem; color:var(--texto-muted); margin-top:0.3rem; }
.liquidez-desglose { display:flex; flex-direction:column; gap:4px; }
.liquidez-linea { display:flex; justify-content:space-between; font-size:0.85rem; padding:4px 0; border-bottom:0.5px solid var(--borde-suave,#eee); }
.liquidez-linea.sub { padding-left:1rem; font-size:0.8rem; }
.liquidez-linea.colchon { color:var(--texto-sec); border-top:1px dashed var(--borde); margin-top:4px; }
.liquidez-linea.total { font-weight:700; font-size:0.95rem; border-top:2px solid var(--borde); margin-top:4px; padding-top:6px; }
.liquidez-creditos { display:flex; flex-direction:column; gap:6px; }
.liquidez-creditos-titulo { font-size:0.78rem; font-weight:600; color:var(--texto-sec); margin-bottom:4px; }
.liquidez-prov-row { display:flex; align-items:center; gap:6px; font-size:0.8rem; flex-wrap:wrap; }
.lp-nombre { flex:1; min-width:100px; font-weight:500; }
.lp-saldo { min-width:60px; text-align:right; }
.lp-dias { min-width:28px; }
.lp-input-dias { width:64px; text-align:center; border:1px solid var(--borde); border-radius:4px; padding:3px 6px; font-size:0.85rem; background:var(--fondo-input,#fff); color:var(--texto-principal); }
.lp-input-dias:focus { border-color:#FFCC00; outline:none; }
.lp-abono { font-size:0.75rem; margin-left:auto; }
.txt-verde { color:#16A34A; }
.txt-rojo  { color:#DC2626; }
</style>
