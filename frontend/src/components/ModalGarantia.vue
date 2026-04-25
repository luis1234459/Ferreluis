<template>
  <div class="mg-overlay" @click.self="$emit('cancelar')">
    <div class="mg-modal">

      <div class="mg-header">
        <span class="mg-titulo">Datos de Garantía</span>
        <button class="mg-cerrar" @click="$emit('cancelar')">✕</button>
      </div>

      <p class="mg-desc">
        Los siguientes productos requieren datos de garantía antes de finalizar la venta.
      </p>

      <div
        v-for="(item, idx) in itemsLocales"
        :key="idx"
        class="mg-item"
      >
        <div class="mg-item-nombre">
          {{ item.nombre }}
          <span v-if="item.variante_label" class="mg-variante"> — {{ item.variante_label }}</span>
        </div>

        <div class="mg-garantia-info" v-if="item.garantia">
          <span class="mg-badge">{{ item.garantia.nombre }} · {{ item.garantia.meses }} meses</span>
        </div>

        <div class="mg-fields">
          <div class="mg-field" v-if="item.requiere_serial">
            <label>Serial <span class="mg-req">*</span></label>
            <input
              v-model="item._serial"
              placeholder="Número de serie del producto"
              :class="{ 'mg-error-input': enviado && item.requiere_serial && !item._serial }"
            />
          </div>
          <div class="mg-field">
            <label>Modelo <span class="mg-opt">(opcional)</span></label>
            <input v-model="item._modelo" placeholder="Modelo del producto" />
          </div>
        </div>

        <div class="mg-condiciones" v-if="item.garantia && item.garantia.condiciones">
          <p class="mg-cond-titulo">Condiciones de garantía:</p>
          <pre class="mg-cond-texto">{{ item.garantia.condiciones }}</pre>
        </div>
      </div>

      <p class="mg-error" v-if="errorMsg">{{ errorMsg }}</p>

      <div class="mg-footer">
        <button class="mg-btn-cancelar" @click="$emit('cancelar')">Cancelar</button>
        <button class="mg-btn-confirmar" @click="confirmar">Confirmar y continuar</button>
      </div>

    </div>
  </div>
</template>

<script>
export default {
  name: 'ModalGarantia',
  emits: ['confirmar', 'cancelar'],

  props: {
    // items: [{ id, nombre, variante_id, variante_label, requiere_serial, garantia: {id,nombre,meses,condiciones} }]
    items: { type: Array, required: true },
  },

  data() {
    return {
      itemsLocales: this.items.map(i => ({ ...i, _serial: '', _modelo: '' })),
      enviado:  false,
      errorMsg: '',
    }
  },

  methods: {
    confirmar() {
      this.enviado  = true
      this.errorMsg = ''

      const faltaSerial = this.itemsLocales.find(i => i.requiere_serial && !i._serial.trim())
      if (faltaSerial) {
        this.errorMsg = `Falta el serial de: ${faltaSerial.nombre}`
        return
      }

      const resultado = this.itemsLocales.map(i => ({
        producto_id:  i.id,
        variante_id:  i.variante_id || null,
        serial:       i._serial.trim() || null,
        modelo:       i._modelo.trim() || null,
      }))

      this.$emit('confirmar', resultado)
    },
  },
}
</script>

<style scoped>
.mg-overlay {
  position: fixed; inset: 0; z-index: 600;
  background: rgba(0,0,0,0.55);
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
}
.mg-modal {
  background: #FAFAF7; border-radius: 14px;
  padding: 1.5rem 2rem; width: 100%; max-width: 520px;
  max-height: 88vh; overflow-y: auto;
  box-shadow: 0 8px 40px rgba(0,0,0,0.2);
  border: 1px solid #DDD;
}
.mg-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 0.5rem;
}
.mg-titulo  { font-size: 1.05rem; font-weight: 700; color: #1A1A1A; }
.mg-cerrar  { background: none; border: none; font-size: 1.1rem; cursor: pointer; color: #888; }
.mg-cerrar:hover { color: #1A1A1A; }
.mg-desc    { font-size: 0.85rem; color: #666; margin: 0 0 1.25rem; }

.mg-item {
  border: 1px solid #DDD; border-radius: 10px;
  padding: 1rem; margin-bottom: 1rem; background: #fff;
}
.mg-item-nombre { font-weight: 700; color: #1A1A1A; margin-bottom: 0.4rem; }
.mg-variante    { font-weight: 400; color: #666; }
.mg-garantia-info { margin-bottom: 0.75rem; }
.mg-badge {
  display: inline-block; background: #1A1A1A; color: #FFCC00;
  font-size: 0.78rem; font-weight: 700; padding: 0.2rem 0.65rem;
  border-radius: 20px;
}

.mg-fields { display: flex; flex-direction: column; gap: 0.6rem; margin-bottom: 0.75rem; }
.mg-field label { display: block; font-size: 0.8rem; font-weight: 600; color: #555; margin-bottom: 0.25rem; }
.mg-req  { color: #DC2626; }
.mg-opt  { font-weight: 400; color: #999; }
.mg-field input {
  width: 100%; padding: 0.5rem 0.75rem;
  border: 1px solid #CCC; border-radius: 6px;
  font-size: 0.93rem; box-sizing: border-box;
}
.mg-field input:focus { outline: none; border-color: #FFCC00; box-shadow: 0 0 0 2px rgba(255,204,0,0.25); }
.mg-error-input { border-color: #DC2626 !important; }

.mg-condiciones  { margin-top: 0.5rem; }
.mg-cond-titulo  { font-size: 0.78rem; font-weight: 700; color: #555; margin: 0 0 0.3rem; }
.mg-cond-texto   {
  font-size: 0.75rem; color: #444; white-space: pre-wrap;
  background: #F5F5F0; border-radius: 6px; padding: 0.6rem 0.75rem;
  margin: 0; max-height: 120px; overflow-y: auto;
  font-family: inherit; line-height: 1.5;
}

.mg-error  { color: #DC2626; font-size: 0.85rem; margin: 0.5rem 0; }

.mg-footer {
  display: flex; gap: 0.75rem; justify-content: flex-end; margin-top: 1.25rem;
}
.mg-btn-cancelar {
  background: transparent; color: #1A1A1A;
  border: 1px solid #DDD; padding: 0.6rem 1.25rem;
  border-radius: 8px; cursor: pointer; font-size: 0.92rem;
}
.mg-btn-cancelar:hover { background: #F0EFE8; }
.mg-btn-confirmar {
  background: #1A1A1A; color: #FFCC00;
  border: none; padding: 0.6rem 1.5rem;
  border-radius: 8px; cursor: pointer; font-size: 0.92rem; font-weight: 700;
}
.mg-btn-confirmar:hover { background: #333; }
</style>
