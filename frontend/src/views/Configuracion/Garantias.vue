<template>
  <div class="gar-wrap">
    <div class="gar-header">
      <h2 class="gar-titulo">Plantillas de Garantía</h2>
      <button class="gar-btn-nuevo" @click="abrirNueva">+ Nueva plantilla</button>
    </div>

    <p class="gar-desc">
      Define los tipos de garantía que puedes asignar a tus productos.
      El texto de condiciones se imprime en la nota de entrega.
    </p>

    <!-- Lista -->
    <div class="gar-tabla-wrap">
      <table class="gar-tabla" v-if="plantillas.length">
        <thead>
          <tr>
            <th>Nombre</th>
            <th class="gar-th-c">Meses</th>
            <th>Condiciones (resumen)</th>
            <th class="gar-th-c">Estado</th>
            <th class="gar-th-c">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in plantillas" :key="p.id" :class="{ 'gar-inactiva': !p.activa }">
            <td class="gar-nombre">{{ p.nombre }}</td>
            <td class="gar-td-c">{{ p.meses }} mes{{ p.meses !== 1 ? 'es' : '' }}</td>
            <td class="gar-resumen">{{ resumen(p.condiciones) }}</td>
            <td class="gar-td-c">
              <span :class="p.activa ? 'gar-badge-activa' : 'gar-badge-inactiva'">
                {{ p.activa ? 'Activa' : 'Inactiva' }}
              </span>
            </td>
            <td class="gar-td-c gar-acciones">
              <button class="gar-btn-edit" @click="abrirEditar(p)" title="Editar">✏️</button>
              <button class="gar-btn-toggle" @click="toggleActiva(p)" :title="p.activa ? 'Desactivar' : 'Activar'">
                {{ p.activa ? '🔒' : '✅' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p class="gar-vacia" v-else>No hay plantillas creadas todavía.</p>
    </div>

    <!-- Dialog crear/editar -->
    <div class="gar-overlay" v-if="dialog" @click.self="cerrar">
      <div class="gar-dialog">
        <div class="gar-dialog-header">
          <span>{{ editando ? 'Editar plantilla' : 'Nueva plantilla' }}</span>
          <button class="gar-dialog-cerrar" @click="cerrar">✕</button>
        </div>
        <div class="gar-dialog-body">
          <div class="gar-field">
            <label>Nombre <span class="gar-req">*</span></label>
            <input v-model="form.nombre" placeholder="Ej: Garantía Bombas Sumergibles" />
          </div>
          <div class="gar-field">
            <label>Duración (meses)</label>
            <input v-model.number="form.meses" type="number" min="0" placeholder="0" />
          </div>
          <div class="gar-field">
            <label>Condiciones de garantía</label>
            <textarea
              v-model="form.condiciones"
              rows="8"
              placeholder="Escribe aquí las condiciones completas que aparecerán en la nota de entrega..."
            ></textarea>
          </div>
          <div class="gar-field-row">
            <label class="gar-check-label">
              <input type="checkbox" v-model="form.activa" /> Plantilla activa
            </label>
          </div>
          <p class="gar-error" v-if="error">{{ error }}</p>
        </div>
        <div class="gar-dialog-footer">
          <button class="gar-btn-cancel" @click="cerrar">Cancelar</button>
          <button class="gar-btn-save" :disabled="guardando" @click="guardar">
            {{ guardando ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'GarantiasConfig',
  data() {
    return {
      plantillas: [],
      dialog:     false,
      editando:   null,
      guardando:  false,
      error:      '',
      form: { nombre: '', meses: 0, condiciones: '', activa: true },
    }
  },
  async mounted() {
    await this.cargar()
  },
  methods: {
    async cargar() {
      const r = await axios.get('/garantias/plantillas?solo_activas=false')
      this.plantillas = r.data
    },
    resumen(txt) {
      if (!txt) return '—'
      return txt.length > 80 ? txt.slice(0, 80) + '…' : txt
    },
    abrirNueva() {
      this.editando = null
      this.form     = { nombre: '', meses: 0, condiciones: '', activa: true }
      this.error    = ''
      this.dialog   = true
    },
    abrirEditar(p) {
      this.editando = p.id
      this.form     = { nombre: p.nombre, meses: p.meses, condiciones: p.condiciones || '', activa: p.activa }
      this.error    = ''
      this.dialog   = true
    },
    cerrar() {
      this.dialog = false
    },
    async guardar() {
      if (!this.form.nombre.trim()) { this.error = 'El nombre es obligatorio'; return }
      this.guardando = true
      this.error     = ''
      try {
        if (this.editando) {
          await axios.put(`/garantias/plantillas/${this.editando}`, this.form)
        } else {
          await axios.post('/garantias/plantillas', this.form)
        }
        await this.cargar()
        this.dialog = false
      } catch (e) {
        this.error = e.response?.data?.detail || 'Error al guardar'
      } finally {
        this.guardando = false
      }
    },
    async toggleActiva(p) {
      await axios.put(`/garantias/plantillas/${p.id}`, { ...p, activa: !p.activa })
      await this.cargar()
    },
  },
}
</script>

<style scoped>
.gar-wrap   { padding: 1.5rem 2rem; max-width: 900px; }
.gar-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; }
.gar-titulo { font-size: 1.15rem; font-weight: 700; color: #1A1A1A; margin: 0; }
.gar-desc   { font-size: 0.85rem; color: #666; margin: 0 0 1.5rem; }

.gar-btn-nuevo {
  background: #1A1A1A; color: #FFCC00;
  border: none; padding: 0.55rem 1.2rem;
  border-radius: 8px; cursor: pointer; font-size: 0.9rem; font-weight: 700;
}
.gar-btn-nuevo:hover { background: #333; }

.gar-tabla-wrap { overflow-x: auto; }
.gar-tabla { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.gar-tabla th { background: #1A1A1A; color: #FFCC00; padding: 8px 12px; text-align: left; }
.gar-th-c  { text-align: center !important; }
.gar-tabla td { padding: 8px 12px; border-bottom: 1px solid #E5E5E0; }
.gar-td-c  { text-align: center; }
.gar-inactiva td { opacity: 0.5; }
.gar-nombre  { font-weight: 600; }
.gar-resumen { color: #555; font-size: 0.82rem; max-width: 300px; }

.gar-badge-activa  { background: #D1FAE5; color: #065F46; padding: 2px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 700; }
.gar-badge-inactiva{ background: #F3F4F6; color: #6B7280; padding: 2px 10px; border-radius: 20px; font-size: 0.78rem; }

.gar-acciones { display: flex; gap: 0.4rem; justify-content: center; }
.gar-btn-edit, .gar-btn-toggle { background: none; border: none; cursor: pointer; font-size: 1rem; }

.gar-vacia { color: #888; font-size: 0.9rem; padding: 1.5rem 0; }

/* Dialog */
.gar-overlay {
  position: fixed; inset: 0; z-index: 700;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; padding: 1rem;
}
.gar-dialog {
  background: #FAFAF7; border-radius: 14px;
  padding: 1.5rem 2rem; width: 100%; max-width: 560px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.2); border: 1px solid #DDD;
}
.gar-dialog-header {
  display: flex; justify-content: space-between; align-items: center;
  font-weight: 700; font-size: 1rem; color: #1A1A1A; margin-bottom: 1.25rem;
}
.gar-dialog-cerrar { background: none; border: none; cursor: pointer; font-size: 1.1rem; color: #888; }
.gar-dialog-cerrar:hover { color: #1A1A1A; }

.gar-field { margin-bottom: 1rem; }
.gar-field label { display: block; font-size: 0.82rem; font-weight: 600; color: #555; margin-bottom: 0.3rem; }
.gar-req   { color: #DC2626; }
.gar-field input, .gar-field textarea {
  width: 100%; padding: 0.5rem 0.75rem;
  border: 1px solid #CCC; border-radius: 6px;
  font-size: 0.93rem; box-sizing: border-box;
  font-family: inherit;
}
.gar-field input:focus, .gar-field textarea:focus {
  outline: none; border-color: #FFCC00; box-shadow: 0 0 0 2px rgba(255,204,0,0.25);
}
.gar-field-row { display: flex; align-items: center; gap: 0.5rem; }
.gar-check-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.88rem; cursor: pointer; }
.gar-error { color: #DC2626; font-size: 0.85rem; margin: 0.5rem 0 0; }

.gar-dialog-footer { display: flex; gap: 0.75rem; justify-content: flex-end; margin-top: 1.25rem; }
.gar-btn-cancel {
  background: transparent; color: #1A1A1A; border: 1px solid #DDD;
  padding: 0.55rem 1.25rem; border-radius: 8px; cursor: pointer;
}
.gar-btn-cancel:hover { background: #F0EFE8; }
.gar-btn-save {
  background: #1A1A1A; color: #FFCC00; border: none;
  padding: 0.55rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 700;
}
.gar-btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
.gar-btn-save:not(:disabled):hover { background: #333; }
</style>
