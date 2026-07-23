<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Sedes</h1>
        <button class="btn-nueva" @click="abrirNueva">+ Nueva sede</button>
      </div>

      <div class="contenido-inner">
        <div v-if="cargando" class="sin-datos">Cargando...</div>

        <div v-else class="tabla-container">
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>Nombre</th>
                <th>Ciudad</th>
                <th>Dirección</th>
                <th>Teléfono</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <!-- Fila de creación -->
              <tr v-if="creando" class="fila-edicion">
                <td><input v-model="form.codigo" placeholder="OJEDA" class="input-fila" /></td>
                <td><input v-model="form.nombre" placeholder="Ferreutil Ojeda" class="input-fila" /></td>
                <td><input v-model="form.ciudad" placeholder="Ciudad" class="input-fila" /></td>
                <td><input v-model="form.direccion" placeholder="Dirección" class="input-fila" /></td>
                <td><input v-model="form.telefono" placeholder="Teléfono" class="input-fila" /></td>
                <td>—</td>
                <td class="col-acciones">
                  <button class="btn-guardar-fila" @click="crear" :disabled="guardando">Crear</button>
                  <button class="btn-cancelar-fila" @click="cerrarNueva">Cancelar</button>
                </td>
              </tr>

              <tr v-for="s in sedes" :key="s.id" :class="{ 'fila-edicion': editandoId === s.id, 'fila-inactiva': !s.activa }">
                <template v-if="editandoId === s.id">
                  <td><input v-model="form.codigo" class="input-fila" /></td>
                  <td><input v-model="form.nombre" class="input-fila" /></td>
                  <td><input v-model="form.ciudad" class="input-fila" /></td>
                  <td><input v-model="form.direccion" class="input-fila" /></td>
                  <td><input v-model="form.telefono" class="input-fila" /></td>
                  <td>
                    <span :class="['badge', s.activa ? 'badge-activa' : 'badge-inactiva']">
                      {{ s.activa ? 'Activa' : 'Inactiva' }}
                    </span>
                  </td>
                  <td class="col-acciones">
                    <button class="btn-guardar-fila" @click="guardar(s.id)" :disabled="guardando">Guardar</button>
                    <button class="btn-cancelar-fila" @click="cancelarEdicion">Cancelar</button>
                  </td>
                </template>
                <template v-else>
                  <td class="celda-codigo">{{ s.codigo }}</td>
                  <td>{{ s.nombre }}</td>
                  <td>{{ s.ciudad || '—' }}</td>
                  <td>{{ s.direccion || '—' }}</td>
                  <td>{{ s.telefono || '—' }}</td>
                  <td>
                    <span :class="['badge', s.activa ? 'badge-activa' : 'badge-inactiva']">
                      {{ s.activa ? 'Activa' : 'Inactiva' }}
                    </span>
                  </td>
                  <td class="col-acciones">
                    <button class="btn-editar" @click="abrirEditar(s)">Editar</button>
                    <button
                      :class="['btn-toggle-activa', s.activa ? 'desactivar' : 'activar']"
                      @click="toggleActiva(s)"
                    >
                      {{ s.activa ? 'Desactivar' : 'Activar' }}
                    </button>
                  </td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>

        <p class="msg-error" v-if="error">{{ error }}</p>
      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '../../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'AdminSedes',
  data() {
    return {
      sedes:      [],
      cargando:   true,
      editandoId: null,
      creando:    false,
      guardando:  false,
      error:      '',
      form: { codigo: '', nombre: '', ciudad: '', direccion: '', telefono: '' },
    }
  },
  async mounted() {
    await this.cargar()
  },
  methods: {
    async cargar() {
      this.cargando = true
      try {
        const res = await axios.get('/sedes/')
        this.sedes = res.data
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al cargar sedes'
      } finally {
        this.cargando = false
      }
    },
    abrirEditar(s) {
      this.creando    = false
      this.editandoId = s.id
      this.form = {
        codigo: s.codigo, nombre: s.nombre, ciudad: s.ciudad || '',
        direccion: s.direccion || '', telefono: s.telefono || '',
      }
      this.error = ''
    },
    cancelarEdicion() {
      this.editandoId = null
      this.error = ''
    },
    abrirNueva() {
      this.editandoId = null
      this.creando = true
      this.form = { codigo: '', nombre: '', ciudad: '', direccion: '', telefono: '' }
      this.error = ''
    },
    cerrarNueva() {
      this.creando = false
      this.error = ''
    },
    async guardar(id) {
      if (!this.form.codigo || !this.form.nombre) {
        this.error = 'Código y nombre son obligatorios'
        return
      }
      this.guardando = true
      this.error = ''
      try {
        await axios.put(`/sedes/${id}`, this.form)
        this.editandoId = null
        await this.cargar()
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al guardar'
      } finally {
        this.guardando = false
      }
    },
    async crear() {
      if (!this.form.codigo || !this.form.nombre) {
        this.error = 'Código y nombre son obligatorios'
        return
      }
      this.guardando = true
      this.error = ''
      try {
        await axios.post('/sedes/', this.form)
        this.creando = false
        await this.cargar()
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al crear la sede'
      } finally {
        this.guardando = false
      }
    },
    async toggleActiva(s) {
      const accion = s.activa ? 'desactivar' : 'activar'
      if (!confirm(`¿${accion.charAt(0).toUpperCase() + accion.slice(1)} la sede "${s.nombre}"?`)) return
      try {
        await axios.put(`/sedes/${s.id}`, { activa: !s.activa })
        await this.cargar()
      } catch (e) {
        this.error = e?.response?.data?.detail || `Error al ${accion}`
      }
    },
  },
}
</script>

<style scoped>
.btn-nueva {
  background: #1A1A1A; color: #FFCC00; border: none;
  padding: 0.55rem 1.1rem; border-radius: 8px; cursor: pointer;
  font-weight: 700; font-size: 0.88rem;
}
.btn-nueva:hover { background: #333; }

.sin-datos { color: var(--texto-sec); padding: 2rem; text-align: center; }

.fila-inactiva { opacity: 0.55; }
.fila-edicion { background: #FFFBEB; }

.celda-codigo { font-family: monospace; font-weight: 700; letter-spacing: 0.03em; }

.input-fila {
  width: 100%; padding: 0.4rem 0.5rem;
  border: 1px solid #CCCCCC; border-radius: 6px;
  font-size: 0.85rem; color: var(--texto-principal); background: #FFFFFF;
  box-sizing: border-box;
}
.input-fila:focus { outline: none; border-color: #FFCC00; box-shadow: 0 0 0 2px #FFCC0033; }

.badge { font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 700; }
.badge-activa   { background: #DCFCE7; color: #16A34A; }
.badge-inactiva { background: #FEE2E2; color: #DC2626; }

.col-acciones { display: flex; gap: 0.4rem; white-space: nowrap; }

.btn-editar {
  background: transparent; border: 1px solid var(--borde); color: var(--texto-sec);
  padding: 0.35rem 0.7rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem;
}
.btn-editar:hover { border-color: #1A1A1A; color: #1A1A1A; }

.btn-toggle-activa {
  border: none; padding: 0.35rem 0.7rem; border-radius: 6px; cursor: pointer;
  font-size: 0.8rem; font-weight: 600;
}
.btn-toggle-activa.desactivar { background: #FEE2E2; color: #DC2626; }
.btn-toggle-activa.activar    { background: #DCFCE7; color: #16A34A; }

.btn-guardar-fila {
  background: #1A1A1A; color: #FFCC00; border: none;
  padding: 0.35rem 0.7rem; border-radius: 6px; cursor: pointer;
  font-size: 0.8rem; font-weight: 700;
}
.btn-guardar-fila:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar-fila {
  background: transparent; border: 1px solid var(--borde); color: var(--texto-sec);
  padding: 0.35rem 0.7rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem;
}

.msg-error { color: #DC2626; font-size: 0.88rem; margin-top: 1rem; }
</style>
