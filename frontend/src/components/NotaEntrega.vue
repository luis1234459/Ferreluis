<template>
  <!-- Modal principal -->
  <div class="ne-overlay" @click.self="$emit('cerrar')">
    <div class="ne-modal">

      <!-- ── Paso 1: ¿Enviar nota? ── -->
      <template v-if="paso === 'preguntar'">
        <p class="ne-titulo">¿Desea enviar nota de entrega?</p>
        <div class="ne-botones">
          <button class="ne-btn-si" @click="paso = 'opciones'">Sí</button>
          <button class="ne-btn-no" @click="$emit('cerrar')">No</button>
        </div>
      </template>

      <!-- ── Paso 2: WhatsApp / Imprimir ── -->
      <template v-else-if="paso === 'opciones'">
        <p class="ne-titulo">Selecciona el método de entrega</p>
        <div class="ne-botones">
          <button class="ne-btn-accion" @click="iniciarWhatsapp">💬 WhatsApp</button>
          <button class="ne-btn-accion" @click="imprimir">🖨 Imprimir</button>
        </div>
        <button class="ne-btn-volver" @click="paso = 'preguntar'">← Volver</button>
      </template>

      <!-- ── Paso 3: Ingresar teléfono manual ── -->
      <template v-else-if="paso === 'telefono'">
        <p class="ne-titulo">Cliente sin teléfono registrado</p>
        <p class="ne-desc">Ingresa el número para enviar por WhatsApp y guardarlo en el perfil del cliente.</p>
        <div class="ne-field">
          <label>Número (ej: 584121234567)</label>
          <input v-model="telefonoManual" placeholder="584121234567" type="tel"
            @keyup.enter="guardarYEnviar" />
        </div>
        <p class="ne-error" v-if="errorTel">{{ errorTel }}</p>
        <div class="ne-botones">
          <button class="ne-btn-accion" :disabled="guardando" @click="guardarYEnviar">
            {{ guardando ? 'Guardando...' : 'Guardar y enviar' }}
          </button>
          <button class="ne-btn-no" @click="paso = 'opciones'">Cancelar</button>
        </div>
      </template>

    </div>
  </div>

  <!-- Nota de entrega oculta — se renderiza para PDF/impresión -->
  <div id="nota-entrega-doc" ref="notaDoc" class="nota-doc">
    <div class="nota-encabezado">
      <p class="nota-empresa">FERRETERÍA FERRE-UTIL</p>
      <p class="nota-subtitulo">Nota de Entrega</p>
    </div>

    <div class="nota-datos">
      <p><strong>Cliente:</strong> {{ clienteNombre }}</p>
      <p><strong>Fecha:</strong> {{ fechaFormateada }}</p>
      <p><strong>Tasa BCV:</strong> Bs. {{ Number(tasaBcv).toFixed(2) }} / USD</p>
    </div>

    <table class="nota-tabla">
      <thead>
        <tr>
          <th>Producto</th>
          <th class="nota-th-num">Cant.</th>
          <th class="nota-th-num">P.Unit. Bs</th>
          <th class="nota-th-num">Subtotal Bs</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="(p, i) in productos" :key="i">
          <tr>
            <td>
              {{ p.nombre }}
              <span v-if="p.variante_label" style="color:#666"> — {{ p.variante_label }}</span>
            </td>
            <td class="nota-td-num">{{ p.cantidad }}</td>
            <td class="nota-td-num">{{ precioUnitBs(p).toFixed(2) }}</td>
            <td class="nota-td-num">{{ (precioUnitBs(p) * p.cantidad).toFixed(2) }}</td>
          </tr>
          <tr v-if="garantiasPorProducto[p.producto_id || p.id]" class="nota-fila-garantia">
            <td colspan="4">
              <div class="nota-garantia-bloque">
                <span v-if="garantiasPorProducto[p.producto_id || p.id].serial">
                  <strong>Serial:</strong> {{ garantiasPorProducto[p.producto_id || p.id].serial }}
                </span>
                <span v-if="garantiasPorProducto[p.producto_id || p.id].modelo">
                  &nbsp;·&nbsp;<strong>Modelo:</strong> {{ garantiasPorProducto[p.producto_id || p.id].modelo }}
                </span>
                <span v-if="garantiasPorProducto[p.producto_id || p.id].meses_garantia">
                  &nbsp;·&nbsp;<strong>Garantía:</strong> {{ garantiasPorProducto[p.producto_id || p.id].meses_garantia }} meses
                </span>
                <div v-if="garantiasPorProducto[p.producto_id || p.id].condiciones_snapshot" class="nota-garantia-cond">
                  {{ garantiasPorProducto[p.producto_id || p.id].condiciones_snapshot }}
                </div>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <div class="nota-total">
      TOTAL: Bs {{ Number(totalBs).toFixed(2) }}
    </div>

    <div class="nota-firmas" v-if="garantias && garantias.length > 0">
      <div class="nota-firma-bloque">
        <div class="nota-firma-linea"></div>
        <div class="nota-firma-label">Firma del Cliente</div>
      </div>
      <div class="nota-firma-bloque">
        <div class="nota-firma-linea"></div>
        <div class="nota-firma-label">Firma del Vendedor</div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'NotaEntrega',
  emits: ['cerrar'],
  props: {
    ventaId:         { type: Number,  required: true },
    clienteId:       { type: Number,  default: null  },
    clienteNombre:   { type: String,  default: 'Consumidor Final' },
    clienteTelefono: { type: String,  default: '' },
    productos:       { type: Array,   required: true },  // [{nombre, cantidad, precio_unitario}]
    garantias:       { type: Array,   default: () => [] }, // [{producto_id, serial, modelo, meses_garantia, condiciones_snapshot}]
    totalBs:         { type: Number,  required: true },
    tasaBcv:         { type: Number,  required: true },
    pasoInicial:     { type: String,  default: 'preguntar' },
  },
  data() {
    return {
      paso:           this.pasoInicial === 'whatsapp' || this.pasoInicial === 'imprimir'
                        ? 'opciones'
                        : 'preguntar',
      telefonoManual: '',
      errorTel:       '',
      guardando:      false,
    }
  },
  mounted() {
    if (this.pasoInicial === 'whatsapp') {
      this.iniciarWhatsapp()
    } else if (this.pasoInicial === 'imprimir') {
      this.imprimir()
    }
  },
  computed: {
    fechaFormateada() {
      return new Date().toLocaleDateString('es-VE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    },
    telefonoEfectivo() {
      return this.clienteTelefono || this.telefonoManual
    },
    garantiasPorProducto() {
      const map = {}
      for (const g of (this.garantias || [])) {
        map[g.producto_id] = g
      }
      return map
    },
  },
  methods: {
    precioUnitBs(p) {
      // precio_unitario viene en USD → convertir a Bs
      return Number(p.precio_unitario || 0) * Number(this.tasaBcv || 1)
    },

    // ── WhatsApp ─────────────────────────────────────────────────────────────
    iniciarWhatsapp() {
      if (this.clienteTelefono) {
        this._enviarWhatsapp(this.clienteTelefono)
      } else {
        this.paso = 'telefono'
      }
    },
    async guardarYEnviar() {
      const num = this.telefonoManual.trim().replace(/\D/g, '')
      if (num.length < 10) {
        this.errorTel = 'Número demasiado corto. Ejemplo: 584121234567'
        return
      }
      this.errorTel  = ''
      this.guardando = true
      try {
        if (this.clienteId) {
          await axios.put(`/clientes/${this.clienteId}`, { telefono: num })
        }
        this._enviarWhatsapp(num)
      } catch {
        // No bloqueamos el envío por un error al guardar
        this._enviarWhatsapp(num)
      } finally {
        this.guardando = false
      }
    },
    async _enviarWhatsapp(telefono) {
      await this._generarYDescargarPDF()
      const num     = String(telefono).replace(/\D/g, '')
      const fecha   = this.fechaFormateada
      const mensaje = encodeURIComponent(
        `Nota de entrega FERRETERÍA FERRE-UTIL — Cliente: ${this.clienteNombre} — Total: Bs ${Number(this.totalBs).toFixed(2)} — Fecha: ${fecha}`
      )
      window.open(`https://wa.me/${num}?text=${mensaje}`, '_blank')
      this.$emit('cerrar')
    },

    // ── Imprimir ─────────────────────────────────────────────────────────────
    imprimir() {
      window.print()
      this.$emit('cerrar')
    },

    // ── Generar PDF ──────────────────────────────────────────────────────────
    async _generarYDescargarPDF() {
      const el = this.$refs.notaDoc
      if (!el) return
      // Hacer visible momentáneamente para captura
      el.style.position = 'fixed'
      el.style.left     = '-9999px'
      el.style.top      = '0'
      el.style.display  = 'block'

      try {
        const canvas = await window.html2canvas(el, { scale: 2, useCORS: true })
        const imgData = canvas.toDataURL('image/png')
        const { jsPDF } = window.jspdf
        const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a5' })
        const pdfW = pdf.internal.pageSize.getWidth()
        const ratio = canvas.height / canvas.width
        pdf.addImage(imgData, 'PNG', 10, 10, pdfW - 20, (pdfW - 20) * ratio)
        pdf.save(`nota-entrega-${this.ventaId}.pdf`)
      } finally {
        el.style.display  = ''
        el.style.position = ''
        el.style.left     = ''
        el.style.top      = ''
      }
    },
  },
}
</script>

<style scoped>
/* ── Overlay y modal ── */
.ne-overlay {
  position: fixed; inset: 0; z-index: 500;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
}
.ne-modal {
  background: #FAFAF7; border-radius: 14px;
  padding: 2rem 2.5rem; max-width: 380px; width: 100%;
  box-shadow: 0 8px 40px rgba(0,0,0,0.18);
  border: 1px solid #DDDDDD;
  text-align: center;
}
.ne-titulo  { font-size: 1.05rem; font-weight: 700; color: #1A1A1A; margin: 0 0 1.5rem; }
.ne-desc    { font-size: 0.88rem; color: #555; margin: 0 0 1rem; }
.ne-botones { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; }
.ne-error   { color: #DC2626; font-size: 0.85rem; margin: 0.5rem 0 0; }

.ne-btn-si {
  background: #1A1A1A; color: #FFCC00;
  border: none; padding: 0.65rem 2rem;
  border-radius: 8px; cursor: pointer; font-size: 0.95rem; font-weight: 700;
}
.ne-btn-si:hover { background: #333; }
.ne-btn-no {
  background: transparent; color: #1A1A1A;
  border: 1px solid #DDDDDD; padding: 0.65rem 2rem;
  border-radius: 8px; cursor: pointer; font-size: 0.95rem;
}
.ne-btn-no:hover { background: #F0EFE8; }
.ne-btn-accion {
  background: #1A1A1A; color: #FFCC00;
  border: none; padding: 0.65rem 1.5rem;
  border-radius: 8px; cursor: pointer; font-size: 0.95rem; font-weight: 700;
}
.ne-btn-accion:disabled { opacity: 0.55; cursor: not-allowed; }
.ne-btn-accion:not(:disabled):hover { background: #333; }
.ne-btn-volver {
  background: transparent; color: #888; border: none;
  cursor: pointer; font-size: 0.82rem; margin-top: 1rem;
  text-decoration: underline;
}

.ne-field { text-align: left; margin-bottom: 1rem; }
.ne-field label { display: block; font-size: 0.82rem; font-weight: 600; color: #555; margin-bottom: 0.3rem; }
.ne-field input { width: 100%; padding: 0.55rem 0.85rem; border: 1px solid #CCC; border-radius: 6px; font-size: 0.95rem; box-sizing: border-box; }
.ne-field input:focus { outline: none; border-color: #FFCC00; box-shadow: 0 0 0 2px rgba(255,204,0,0.25); }

/* ── Documento de nota — oculto por defecto, visible al imprimir ── */
.nota-doc {
  display: none;
  font-family: Arial, sans-serif;
  padding: 20px;
  background: #fff;
  color: #000;
  width: 520px;
}
.nota-encabezado { text-align: center; margin-bottom: 16px; border-bottom: 2px solid #000; padding-bottom: 10px; }
.nota-empresa    { font-size: 1.3rem; font-weight: 900; margin: 0; letter-spacing: 0.05em; }
.nota-subtitulo  { font-size: 0.9rem; margin: 4px 0 0; color: #444; }
.nota-datos      { margin-bottom: 14px; font-size: 0.88rem; line-height: 1.7; }
.nota-datos p    { margin: 0; }

.nota-tabla { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-bottom: 14px; }
.nota-tabla th { background: #1A1A1A; color: #FFCC00; padding: 6px 8px; text-align: left; }
.nota-th-num   { text-align: right !important; }
.nota-tabla td { padding: 5px 8px; border-bottom: 1px solid #ddd; }
.nota-td-num   { text-align: right; }
.nota-tabla tbody tr:nth-child(even) { background: #F5F5F0; }

.nota-total { text-align: right; font-size: 1rem; font-weight: 900; border-top: 2px solid #000; padding-top: 8px; }

.nota-fila-garantia td { padding: 4px 8px 8px; border-bottom: 1px solid #ddd; background: #FAFAF5; }
.nota-garantia-bloque { font-size: 0.78rem; color: #333; }
.nota-garantia-cond   { margin-top: 4px; white-space: pre-wrap; color: #555; font-size: 0.74rem; line-height: 1.45; }

.nota-firmas {
  display: flex; gap: 2rem; margin-top: 2rem; padding-top: 1rem;
  border-top: 1px solid #ccc;
}
.nota-firma-bloque { flex: 1; text-align: center; }
.nota-firma-linea  { border-top: 1px solid #000; margin-bottom: 4px; margin-top: 2.5rem; }
.nota-firma-label  { font-size: 0.8rem; color: #444; }

/* ── Media print — oculta TODO excepto .nota-doc ── */
@media print {
  body > * { display: none !important; }
  #app     { display: none !important; }
  .nota-doc {
    display: block !important;
    position: fixed !important;
    inset: 0 !important;
    width: 100% !important;
    padding: 20px !important;
    z-index: 99999 !important;
  }
}
</style>
