<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Proveedores</h1>
        <button class="btn-nuevo" @click="abrirNuevo">+ Nuevo proveedor</button>
      </div>

      <div class="contenido-inner">
        <!-- Lista -->
        <div class="tabla-container">
          <table>
            <thead>
              <tr><th>Nombre</th><th>RIF</th><th>Teléfono</th><th>Contacto</th><th>Email</th><th>Crédito</th><th>Acciones</th></tr>
            </thead>
            <tbody>
              <tr v-for="p in proveedores" :key="p.id">
                <td style="font-weight:600">{{ p.nombre }}</td>
                <td>{{ p.rif || '—' }}</td>
                <td>{{ p.telefono || '—' }}</td>
                <td>{{ p.contacto || '—' }}</td>
                <td>{{ p.email || '—' }}</td>
                <td>{{ p.dias_credito ? p.dias_credito + ' días' : '—' }}</td>
                <td>
                  <button class="btn-editar" @click="editar(p)">Editar</button>
                  <button class="btn-catalogo" @click="verCatalogo(p)">Catálogo</button>
                  <button class="btn-eliminar" @click="eliminar(p.id)">Desactivar</button>
                </td>
              </tr>
              <tr v-if="proveedores.length === 0">
                <td colspan="7" class="sin-datos">No hay proveedores registrados</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Modal proveedor -->
        <div class="overlay" v-if="mostrarForm" @click.self="cerrarForm">
          <div class="modal">
            <div class="modal-header">
              <h2>{{ editandoId ? 'Editar proveedor' : 'Nuevo proveedor' }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarForm">✕</button>
            </div>
            <div class="form-grid">
              <div class="field field-wide">
                <label>Nombre *</label>
                <input v-model="form.nombre" placeholder="Nombre del proveedor" />
              </div>
              <div class="field">
                <label>RIF</label>
                <input v-model="form.rif" placeholder="J-12345678-9" />
              </div>
              <div class="field">
                <label>Teléfono</label>
                <input v-model="form.telefono" placeholder="0414-0000000" />
              </div>
              <div class="field">
                <label>Email</label>
                <input v-model="form.email" placeholder="proveedor@email.com" />
              </div>
              <div class="field">
                <label>Contacto</label>
                <input v-model="form.contacto" placeholder="Nombre del representante" />
              </div>
              <div class="field field-wide">
                <label>Dirección</label>
                <input v-model="form.direccion" placeholder="Dirección o ciudad" />
              </div>
              <div class="field">
                <label>Días de crédito</label>
                <input v-model.number="form.dias_credito" type="number" min="0" placeholder="0 = sin crédito" />
              </div>
            </div>
            <div class="form-botones">
              <button class="btn-cancelar" @click="cerrarForm">Cancelar</button>
              <button class="btn-guardar" @click="guardar" :disabled="guardando">
                {{ guardando ? 'Guardando...' : 'Guardar' }}
              </button>
            </div>
            <p class="msg-error" v-if="error">{{ error }}</p>
          </div>
        </div>

        <!-- Modal catálogo -->
        <div class="overlay" v-if="proveedorCatalogo" @click.self="proveedorCatalogo = null">
          <div class="modal modal-catalogo">
            <div class="modal-header">
              <h2>Catálogo — {{ proveedorCatalogo.nombre }}</h2>
              <button class="btn-cerrar-modal" @click="proveedorCatalogo = null">✕</button>
            </div>

            <table class="tabla-catalogo">
              <thead><tr><th>Producto</th><th>Código proveedor</th><th>P. referencia USD</th><th></th></tr></thead>
              <tbody>
                <tr v-for="item in catalogoItems" :key="item.id">
                  <td>{{ item.nombre_producto }}</td>
                  <td>{{ item.codigo_proveedor || '—' }}</td>
                  <td>${{ item.precio_referencia_usd ? Number(item.precio_referencia_usd).toFixed(2) : '—' }}</td>
                  <td><button class="btn-eliminar" @click="eliminarCatalogo(item.id)">✕</button></td>
                </tr>
                <tr v-if="catalogoItems.length === 0">
                  <td colspan="4" class="sin-datos">Sin ítems en catálogo</td>
                </tr>
              </tbody>
            </table>

            <div class="agregar-catalogo">
              <h3>Agregar ítem</h3>
              <div class="form-grid">
                <div class="field">
                  <label>Producto (inventario)</label>
                  <select v-model="nuevoItem.producto_id" @change="llenarNombreItem">
                    <option value="">— Producto externo —</option>
                    <option v-for="p in productosInventario" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                  </select>
                </div>
                <div class="field">
                  <label>Nombre en catálogo</label>
                  <input v-model="nuevoItem.nombre_producto" placeholder="Como lo llama el proveedor" />
                </div>
                <div class="field">
                  <label>Código proveedor</label>
                  <input v-model="nuevoItem.codigo_proveedor" />
                </div>
                <div class="field">
                  <label>P. referencia USD</label>
                  <input v-model.number="nuevoItem.precio_referencia_usd" type="number" min="0" step="0.01" />
                </div>
              </div>
              <button class="btn-agregar" @click="agregarItemCatalogo">Agregar al catálogo</button>
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
  name: 'Proveedores',
  data() {
    return {
      usuario:             JSON.parse(localStorage.getItem('usuario') || '{}'),
      proveedores:         [],
      productosInventario: [],
      mostrarForm:         false,
      editandoId:          null,
      guardando:           false,
      error:               '',
      form: { nombre: '', rif: '', telefono: '', email: '', contacto: '', direccion: '', dias_credito: 0 },
      proveedorCatalogo:   null,
      catalogoItems:       [],
      nuevoItem: { producto_id: '', nombre_producto: '', codigo_proveedor: '', precio_referencia_usd: '' },
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
    await Promise.all([this.cargar(), this.cargarInventario()])
  },
  methods: {
    async cargar() {
      const res = await axios.get('/compras/proveedores/')
      this.proveedores = res.data
    },
    async cargarInventario() {
      const res = await axios.get('/productos/')
      this.productosInventario = res.data
    },
    abrirNuevo() {
      this.editandoId = null
      this.form = { nombre: '', rif: '', telefono: '', email: '', contacto: '', direccion: '', dias_credito: 0 }
      this.mostrarForm = true
    },
    editar(p) {
      this.editandoId = p.id
      this.form = { nombre: p.nombre, rif: p.rif || '', telefono: p.telefono || '', email: p.email || '', contacto: p.contacto || '', direccion: p.direccion || '', dias_credito: p.dias_credito || 0 }
      this.mostrarForm = true
    },
    cerrarForm() { this.mostrarForm = false; this.error = '' },
    async guardar() {
      if (!this.form.nombre) { this.error = 'El nombre es obligatorio'; return }
      this.guardando = true; this.error = ''
      try {
        if (this.editandoId) {
          await axios.put(`/compras/proveedores/${this.editandoId}`, this.form)
        } else {
          await axios.post('/compras/proveedores/', this.form)
        }
        await this.cargar()
        this.cerrarForm()
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al guardar'
      } finally { this.guardando = false }
    },
    async eliminar(id) {
      if (!confirm('¿Desactivar este proveedor?')) return
      await axios.delete(`/compras/proveedores/${id}`)
      await this.cargar()
    },
    async verCatalogo(p) {
      this.proveedorCatalogo = p
      const res = await axios.get(`/compras/proveedores/${p.id}/catalogo`)
      this.catalogoItems = res.data
    },
    llenarNombreItem() {
      const prod = this.productosInventario.find(p => p.id === this.nuevoItem.producto_id)
      if (prod) this.nuevoItem.nombre_producto = prod.nombre
    },
    async agregarItemCatalogo() {
      if (!this.nuevoItem.nombre_producto) { alert('Ingresa el nombre del producto'); return }
      await axios.post(`/compras/proveedores/${this.proveedorCatalogo.id}/catalogo`, {
        ...this.nuevoItem,
        producto_id: this.nuevoItem.producto_id || null,
      })
      const res = await axios.get(`/compras/proveedores/${this.proveedorCatalogo.id}/catalogo`)
      this.catalogoItems = res.data
      this.nuevoItem = { producto_id: '', nombre_producto: '', codigo_proveedor: '', precio_referencia_usd: '' }
    },
    async eliminarCatalogo(itemId) {
      if (!confirm('¿Eliminar este ítem?')) return
      await axios.delete(`/compras/proveedores/${this.proveedorCatalogo.id}/catalogo/${itemId}`)
      this.catalogoItems = this.catalogoItems.filter(i => i.id !== itemId)
    },
    salir() { localStorage.removeItem('usuario'); this.$router.push('/login') },
  },
}
</script>

<style scoped>
.btn-editar   { background: var(--info); color: white; border: none; padding: 0.28rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; margin-right: 0.3rem; }
.btn-catalogo { background: var(--success); color: white; border: none; padding: 0.28rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; margin-right: 0.3rem; }
.btn-eliminar { background: var(--danger); color: white; border: none; padding: 0.28rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }

.modal-catalogo { max-width: 700px; }
.tabla-catalogo { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; }
.agregar-catalogo { border-top: 1px solid var(--borde); padding-top: 1rem; }
.agregar-catalogo h3 { color: var(--texto-principal); font-size: 0.9rem; margin: 0 0 0.75rem; font-weight: 700; }
.btn-agregar { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.55rem 1.2rem; border-radius: 8px; cursor: pointer; margin-top: 0.75rem; font-weight: 600; }

.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; }
</style>
