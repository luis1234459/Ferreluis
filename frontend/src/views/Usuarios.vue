<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Gestión de Usuarios</h1>
        <button class="btn-nuevo" @click="abrirNuevo">+ Nuevo usuario</button>
      </div>

      <div class="contenido-inner">
        <div class="tabla-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Email</th>
                <th>Rol</th>
                <th>Módulos asignados</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in usuarios" :key="u.id" :class="{ 'fila-inactiva': !u.activo }">
                <td class="txt-muted">#{{ u.id }}</td>
                <td>{{ u.nombre }}</td>
                <td class="txt-muted">{{ u.email }}</td>
                <td><span :class="['badge', 'badge-rol-' + u.rol]">{{ u.rol }}</span></td>
                <td>
                  <span v-if="u.rol === 'admin'" class="txt-muted">Acceso total</span>
                  <span v-else-if="!u.permisos" class="txt-muted">Sin restricciones</span>
                  <span v-else-if="u.permisos.length === 0" class="txt-warn">Sin acceso</span>
                  <span v-else class="permisos-lista">{{ u.permisos.join(', ') }}</span>
                </td>
                <td class="acciones-celda">
                  <button class="btn-edit" @click="abrirEditar(u)">Editar</button>
                  <button
                    class="btn-toggle"
                    :class="u.activo ? 'btn-desactivar' : 'btn-activar'"
                    @click="toggleActivo(u)"
                    :disabled="u.id === usuario.id"
                  >{{ u.activo ? 'Desactivar' : 'Activar' }}</button>
                  <button class="btn-del" @click="eliminarUsuario(u)"
                    :disabled="u.id === usuario.id">Eliminar</button>
                </td>
              </tr>
              <tr v-if="usuarios.length === 0">
                <td colspan="6" class="sin-datos">No hay usuarios registrados</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>

    <!-- ── Modal crear / editar ── -->
    <div class="modal-overlay" v-if="modalAbierto" @click.self="cerrarModal">
      <div class="modal">
        <h2>{{ modoEdicion ? 'Editar usuario' : 'Nuevo usuario' }}</h2>

        <div class="campo">
          <label>Nombre</label>
          <input v-model="form.nombre" placeholder="Nombre completo" />
        </div>
        <div class="campo">
          <label>Email</label>
          <input v-model="form.email" type="email" placeholder="correo@ejemplo.com" />
        </div>
        <div class="campo">
          <label>{{ modoEdicion ? 'Nueva contraseña (dejar vacío = no cambiar)' : 'Contraseña' }}</label>
          <input v-model="form.password" type="password" placeholder="••••••••" />
        </div>
        <div class="campo">
          <label>Rol</label>
          <select v-model="form.rol">
            <option value="vendedor">Vendedor</option>
            <option value="gestionador">Gestionador</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        <div class="campo" v-if="form.rol !== 'admin'">
          <label>Módulos permitidos</label>
          <p class="campo-nota">Deja todos sin marcar para acceso completo (sin restricciones).</p>
          <div class="permisos-grid">
            <label v-for="mod in MODULOS" :key="mod.key" class="permiso-check">
              <input type="checkbox" :value="mod.key" v-model="form.permisos" />
              {{ mod.label }}
            </label>
          </div>
        </div>

        <div v-if="errorModal" class="error-msg">{{ errorModal }}</div>

        <div class="modal-acciones">
          <button class="btn-cancelar" @click="cerrarModal">Cancelar</button>
          <button class="btn-guardar" @click="guardar" :disabled="guardando">
            {{ guardando ? 'Guardando…' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

const MODULOS = [
  { key: 'ventas',      label: 'Ventas' },
  { key: 'cierre',      label: 'Cierre de Caja' },
  { key: 'compras',     label: 'Compras / Facturas IA' },
  { key: 'tasa',        label: 'Tasa BCV' },
  { key: 'depositos',   label: 'Depósitos' },
  { key: 'reportes',    label: 'Reportes' },
  { key: 'clientes',    label: 'Clientes' },
  { key: 'fidelidad',   label: 'Fidelidad' },
  { key: 'mi_comision', label: 'Mi Comisión' },
  { key: 'proveedores',  label: 'Proveedores (Compras)' },
  { key: 'presupuestos', label: 'Presupuestos' },
  { key: 'devoluciones', label: 'Devoluciones' },
]

export default {
  components: { AppSidebar },
  name: 'Usuarios',
  data() {
    return {
      usuario:      JSON.parse(localStorage.getItem('usuario') || '{}'),
      usuarios:     [],
      modalAbierto: false,
      modoEdicion:  false,
      editandoId:   null,
      form: {
        nombre:   '',
        email:    '',
        password: '',
        rol:      'vendedor',
        permisos: [],
      },
      errorModal: '',
      guardando:  false,
      MODULOS,
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
    headers() {
      return {
        'X-Usuario-Rol':    this.usuario.rol,
        'X-Usuario-Nombre': this.usuario.usuario,
      }
    },
  },
  async mounted() {
    await this.cargar()
  },
  methods: {
    async cargar() {
      try {
        const res = await axios.get('/usuarios/', { headers: this.headers })
        this.usuarios = res.data
      } catch (e) {
        console.error('Error cargando usuarios', e)
      }
    },
    abrirNuevo() {
      this.modoEdicion  = false
      this.editandoId   = null
      this.form = { nombre: '', email: '', password: '', rol: 'vendedor', permisos: [] }
      this.errorModal   = ''
      this.modalAbierto = true
    },
    abrirEditar(u) {
      this.modoEdicion  = true
      this.editandoId   = u.id
      this.form = {
        nombre:   u.nombre,
        email:    u.email,
        password: '',
        rol:      u.rol,
        permisos: u.permisos ? [...u.permisos] : [],
      }
      this.errorModal   = ''
      this.modalAbierto = true
    },
    cerrarModal() {
      this.modalAbierto = false
    },
    async guardar() {
      this.errorModal = ''
      if (!this.form.nombre.trim() || !this.form.email.trim()) {
        this.errorModal = 'Nombre y email son obligatorios.'
        return
      }
      if (!this.modoEdicion && !this.form.password) {
        this.errorModal = 'La contraseña es obligatoria para usuarios nuevos.'
        return
      }
      this.guardando = true
      try {
        const permisos = this.form.rol === 'admin' ? null
          : (this.form.permisos.length > 0 ? this.form.permisos : null)

        if (this.modoEdicion) {
          const payload = {
            nombre:   this.form.nombre,
            email:    this.form.email,
            rol:      this.form.rol,
            permisos: permisos,
          }
          if (this.form.password) payload.password = this.form.password
          await axios.put(`/usuarios/${this.editandoId}`, payload, { headers: this.headers })
        } else {
          await axios.post('/usuarios/', {
            nombre:   this.form.nombre,
            email:    this.form.email,
            password: this.form.password,
            rol:      this.form.rol,
            permisos: permisos,
          }, { headers: this.headers })
        }
        this.cerrarModal()
        await this.cargar()
      } catch (e) {
        this.errorModal = e.response?.data?.detail || 'Error al guardar usuario.'
      } finally {
        this.guardando = false
      }
    },
    async toggleActivo(u) {
      try {
        await axios.patch(`/usuarios/${u.id}/activo`, { activo: !u.activo })
        u.activo = !u.activo
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al cambiar estado')
      }
    },
    async eliminarUsuario(u) {
      if (u.id === this.usuario.id) return
      if (!confirm(`¿Eliminar al usuario "${u.nombre}"?`)) return
      try {
        await axios.delete(`/usuarios/${u.id}`, { headers: this.headers })
        await this.cargar()
      } catch (e) {
        alert(e.response?.data?.detail || 'Error al eliminar usuario.')
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
.permisos-lista { font-size: 0.8rem; color: var(--texto-secundario); }
.campo-nota     { font-size: 0.78rem; color: var(--texto-secundario); margin: 0.15rem 0 0.5rem; }
.txt-warn       { color: #e67e22; font-size: 0.82rem; }

.permisos-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.4rem 1rem;
  margin-top: 0.25rem;
}
.permiso-check {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  cursor: pointer;
}
.permiso-check input { accent-color: var(--acento); cursor: pointer; }

.badge-rol-admin      { background: #c0392b22; color: #c0392b; }
.badge-rol-vendedor   { background: #27ae6022; color: #27ae60; }
.badge-rol-gestionador{ background: #2980b922; color: #2980b9; }

.fila-inactiva td { opacity: 0.45; }
.btn-toggle { border: none; border-radius: 5px; padding: 0.25rem 0.6rem; font-size: 0.78rem; cursor: pointer; font-weight: 600; }
.btn-activar    { background: #DCFCE7; color: #15803D; }
.btn-desactivar { background: #FEF9C3; color: #854D0E; }
.acciones-celda { display: flex; gap: 0.4rem; align-items: center; }
</style>
