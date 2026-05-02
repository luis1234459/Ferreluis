<template>
  <div class="layout">
    <AppSidebar />
    <main class="contenido">
      <div class="top-bar">
        <h1>Avisos</h1>
        <button v-if="esAdmin" class="btn-nuevo" @click="modalNuevo = true">+ Nuevo aviso</button>
      </div>

      <div class="contenido-inner">

        <div v-if="avisos.length === 0" class="sin-datos">
          No hay avisos activos.
        </div>

        <div v-for="a in avisos" :key="a.id" class="aviso-card">
          <div class="aviso-header">
            <span class="aviso-titulo">{{ a.titulo }}</span>
            <div class="aviso-meta">
              <span class="aviso-fecha">{{ formatFecha(a.fecha) }}</span>
              <span v-if="a.destinatario" class="aviso-dest">→ {{ a.destinatario }}</span>
              <span v-else class="aviso-dest todos">→ Todos</span>
              <button v-if="esAdmin" class="btn-del-aviso" @click="eliminarAviso(a.id)">✕</button>
            </div>
          </div>
          <p class="aviso-mensaje">{{ a.mensaje }}</p>
        </div>

        <div v-if="modalNuevo" class="modal-overlay" @click.self="modalNuevo = false">
          <div class="modal-box">
            <div class="modal-header">
              <h3>Nuevo aviso</h3>
              <button class="btn-cerrar-modal" @click="modalNuevo = false">✕</button>
            </div>
            <div class="modal-body">
              <div class="campo">
                <label>Título *</label>
                <input v-model="form.titulo" class="input-field" placeholder="Ej: Cambio de precios" />
              </div>
              <div class="campo">
                <label>Mensaje *</label>
                <textarea v-model="form.mensaje" class="input-field" rows="4" placeholder="Escribe el aviso..."></textarea>
              </div>
              <div class="campo">
                <label>Destinatario (opcional)</label>
                <select v-model="form.destinatario" class="input-field">
                  <option value="">Todos los usuarios</option>
                  <option v-for="u in usuarios" :key="u.id" :value="u.nombre">{{ u.nombre }}</option>
                </select>
              </div>
              <p v-if="errorForm" class="msg-error">{{ errorForm }}</p>
            </div>
            <div class="modal-footer">
              <button class="btn-cancelar" @click="modalNuevo = false">Cancelar</button>
              <button class="btn-guardar" @click="crearAviso" :disabled="guardando">
                {{ guardando ? 'Publicando...' : 'Publicar aviso' }}
              </button>
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
  name: 'Avisos',
  data() {
    return {
      usuario:    JSON.parse(localStorage.getItem('usuario') || '{}'),
      avisos:     [],
      usuarios:   [],
      modalNuevo: false,
      guardando:  false,
      errorForm:  '',
      form: { titulo: '', mensaje: '', destinatario: '' },
    }
  },
  computed: {
    esAdmin() { return this.usuario.rol === 'admin' },
  },
  async mounted() {
    await this.cargarAvisos()
    if (this.esAdmin) await this.cargarUsuarios()
  },
  methods: {
    async cargarAvisos() {
      try {
        const nombre = this.usuario.usuario || ''
        const { data } = await axios.get('/notificaciones/avisos', { params: { usuario: nombre } })
        this.avisos = data
      } catch {}
    },
    async cargarUsuarios() {
      try {
        const { data } = await axios.get('/usuarios/')
        this.usuarios = data.filter(u => u.rol !== 'admin')
      } catch {}
    },
    async crearAviso() {
      if (!this.form.titulo.trim() || !this.form.mensaje.trim()) {
        this.errorForm = 'Título y mensaje son obligatorios'
        return
      }
      this.guardando = true
      this.errorForm = ''
      try {
        await axios.post('/notificaciones/avisos', {
          titulo:       this.form.titulo.trim(),
          mensaje:      this.form.mensaje.trim(),
          destinatario: this.form.destinatario || null,
          creado_por:   this.usuario.usuario || 'admin',
        })
        this.modalNuevo = false
        this.form = { titulo: '', mensaje: '', destinatario: '' }
        await this.cargarAvisos()
      } catch (e) {
        this.errorForm = e?.response?.data?.detail || 'Error al publicar'
      } finally {
        this.guardando = false
      }
    },
    async eliminarAviso(id) {
      try {
        await axios.delete(`/notificaciones/avisos/${id}`)
        await this.cargarAvisos()
      } catch {}
    },
    formatFecha(f) {
      if (!f) return ''
      return new Date(f).toLocaleString('es-VE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    },
  },
}
</script>

<style scoped>
.btn-nuevo { background: #1A1A1A; color: #FFCC00; border: none; border-radius: 8px; padding: 0.5rem 1.25rem; font-weight: 700; cursor: pointer; }
.sin-datos { text-align: center; padding: 3rem; color: var(--texto-muted); }
.aviso-card { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; }
.aviso-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; gap: 1rem; }
.aviso-titulo { font-weight: 700; font-size: 1rem; color: var(--texto-principal); }
.aviso-meta { display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }
.aviso-fecha { font-size: 0.78rem; color: var(--texto-muted); }
.aviso-dest { font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 4px; background: #F1F5F9; color: var(--texto-sec); }
.aviso-dest.todos { background: #FFCC0022; color: #996600; }
.aviso-mensaje { color: var(--texto-sec); font-size: 0.9rem; margin: 0; line-height: 1.5; }
.btn-del-aviso { background: none; border: none; color: #DC2626; cursor: pointer; font-size: 0.9rem; padding: 0.1rem 0.3rem; border-radius: 3px; }
.btn-del-aviso:hover { background: #FEE2E2; }
.campo { display: flex; flex-direction: column; gap: 0.3rem; }
.campo label { font-size: 0.78rem; font-weight: 600; color: var(--texto-sec); text-transform: uppercase; }
.input-field { border: 1px solid var(--borde); border-radius: 6px; padding: 0.5rem 0.65rem; font-size: 0.875rem; color: var(--texto-principal); background: var(--fondo-app); width: 100%; box-sizing: border-box; }
.input-field:focus { outline: none; border-color: #FFCC00; }
textarea.input-field { resize: vertical; min-height: 80px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: center; justify-content: center; }
.modal-box { background: #FFFFFF; border-radius: 12px; width: 100%; max-width: 480px; box-shadow: 0 16px 48px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--borde); }
.modal-header h3 { margin: 0; font-size: 1rem; color: var(--texto-principal); }
.btn-cerrar-modal { background: none; border: none; font-size: 1.1rem; cursor: pointer; color: var(--texto-muted); }
.modal-body { padding: 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 0.75rem; }
.modal-footer { padding: 1rem 1.5rem; border-top: 1px solid var(--borde); display: flex; justify-content: flex-end; gap: 0.75rem; }
.btn-cancelar { background: none; border: 1px solid var(--borde); border-radius: 6px; padding: 0.5rem 1rem; cursor: pointer; color: var(--texto-sec); }
.btn-guardar { background: #1A1A1A; color: #FFCC00; border: none; border-radius: 8px; padding: 0.6rem 1.5rem; font-weight: 700; cursor: pointer; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.msg-error { color: #DC2626; font-size: 0.85rem; }
</style>
