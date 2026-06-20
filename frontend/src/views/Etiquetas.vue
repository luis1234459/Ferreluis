<template>
  <div class="page-wrap">
    <header class="page-header">
      <h1>🏷 Etiquetas de productos</h1>
    </header>

    <div class="etiquetas-filtros">
      <input v-model="busqueda"
        placeholder="🔍 Buscar producto o código..."
        class="filtro-input" />

      <select v-model="filtroMarca" @change="cargarProductos">
        <option value="">Todas las marcas</option>
        <option v-for="m in marcas" :key="m.id" :value="m.id">
          {{ m.nombre }}
        </option>
      </select>

      <select v-model="filtroDepto" @change="cargarCategorias">
        <option value="">Todos los departamentos</option>
        <option v-for="d in departamentos" :key="d.id" :value="d.id">
          {{ d.nombre }}
        </option>
      </select>

      <select v-model="filtroCategoria" :disabled="!filtroDepto" @change="cargarProductos">
        <option value="">Todas las categorías</option>
        <option v-for="c in categorias" :key="c.id" :value="c.id">
          {{ c.nombre }}
        </option>
      </select>
    </div>

    <div class="etiquetas-acciones-top">
      <label class="check-todos">
        <input type="checkbox"
          :checked="todosSeleccionados"
          @change="toggleTodos" />
        Seleccionar todos ({{ seleccionados.length }})
      </label>
    </div>

    <div class="etiquetas-tabla-wrap">
      <table class="etiquetas-tabla">
        <thead>
          <tr>
            <th></th>
            <th>Código</th>
            <th>Producto</th>
            <th>Precio ref.</th>
            <th>Oferta</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in productosFiltrados" :key="p.id">
            <td>
              <input type="checkbox"
                :checked="seleccionados.includes(p.id)"
                @change="toggleSeleccion(p.id)" />
            </td>
            <td class="txt-muted">{{ p.codigo || '—' }}</td>
            <td style="font-weight:600">{{ p.nombre }}</td>
            <td>${{ Number(p.precio_referencial_usd || 0).toFixed(2) }}</td>
            <td>
              <span v-if="p.oferta_activa" class="badge-oferta">
                🔥 ${{ Number(p.precio_oferta_usd || 0).toFixed(2) }}
              </span>
              <span v-else class="txt-muted">—</span>
            </td>
          </tr>
          <tr v-if="productosFiltrados.length === 0">
            <td colspan="5" class="sin-datos">Sin productos</td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<script>
import axios from 'axios'
export default {
  name: 'Etiquetas',
  data() {
    return {
      usuario:         JSON.parse(localStorage.getItem('usuario') || '{}'),
      productos:       [],
      marcas:          [],
      departamentos:   [],
      categorias:      [],
      busqueda:        '',
      filtroMarca:     '',
      filtroDepto:     '',
      filtroCategoria: '',
      seleccionados:   [],
    }
  },
  computed: {
    productosFiltrados() {
      if (!this.busqueda.trim()) return this.productos
      const q = this.busqueda.trim().toLowerCase()
      return this.productos.filter(p =>
        (p.nombre  || '').toLowerCase().includes(q) ||
        (p.codigo  || '').toLowerCase().includes(q)
      )
    },
    todosSeleccionados() {
      return this.productosFiltrados.length > 0 &&
        this.productosFiltrados.every(p => this.seleccionados.includes(p.id))
    },
  },
  async mounted() {
    await Promise.all([
      this.cargarMarcas(),
      this.cargarDepartamentos(),
      this.cargarProductos(),
    ])
  },
  methods: {
    async cargarMarcas() {
      try {
        const res = await axios.get('/marcas/')
        this.marcas = res.data
      } catch {}
    },
    async cargarDepartamentos() {
      try {
        const res = await axios.get('/productos/departamentos')
        this.departamentos = res.data
      } catch {}
    },
    async cargarCategorias() {
      this.filtroCategoria = ''
      if (!this.filtroDepto) {
        this.categorias = []
        this.cargarProductos()
        return
      }
      try {
        const res = await axios.get('/productos/categorias',
          { params: { departamento_id: this.filtroDepto } })
        this.categorias = res.data
      } catch { this.categorias = [] }
      this.cargarProductos()
    },
    _headers() {
      return {
        'X-Usuario-Rol':    this.usuario.rol     || '',
        'X-Usuario-Nombre': this.usuario.usuario || 'admin',
      }
    },
    async cargarProductos() {
      try {
        // /ajustes/productos usa filtro_tipo + filtro_id, no nombre de campo directo.
        // Prioridad: departamento > marca > todos. busqueda se aplica client-side.
        const params = { filtro_tipo: 'todos' }
        if (this.filtroDepto) {
          params.filtro_tipo = 'departamento'
          params.filtro_id   = this.filtroDepto
          if (this.filtroCategoria) params.categoria_id = this.filtroCategoria
        } else if (this.filtroMarca) {
          params.filtro_tipo = 'marca'
          params.filtro_id   = this.filtroMarca
        }
        const res = await axios.get('/ajustes/productos', { params, headers: this._headers() })
        this.productos = res.data
      } catch { this.productos = [] }
    },
    toggleSeleccion(id) {
      const idx = this.seleccionados.indexOf(id)
      if (idx >= 0) this.seleccionados.splice(idx, 1)
      else this.seleccionados.push(id)
    },
    toggleTodos() {
      if (this.todosSeleccionados) {
        this.seleccionados = this.seleccionados.filter(
          id => !this.productosFiltrados.some(p => p.id === id)
        )
      } else {
        this.productosFiltrados.forEach(p => {
          if (!this.seleccionados.includes(p.id))
            this.seleccionados.push(p.id)
        })
      }
    },
  },
}
</script>

<style scoped>
.page-wrap { padding: 1.5rem; max-width: 1100px; margin: 0 auto; }
.page-header h1 { font-size: 1.3rem; font-weight: 800; margin-bottom: 1rem; }
.etiquetas-filtros {
  display: flex; flex-wrap: wrap; gap: 0.5rem;
  margin-bottom: 1rem;
}
.filtro-input {
  flex: 1; min-width: 200px;
  border: 1px solid var(--borde);
  border-radius: 8px; padding: 0.5rem 0.85rem;
}
.etiquetas-filtros select {
  border: 1px solid var(--borde);
  border-radius: 8px; padding: 0.5rem 0.85rem;
}
.etiquetas-acciones-top { margin-bottom: 0.75rem; }
.check-todos {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.85rem; font-weight: 600; cursor: pointer;
}
.etiquetas-tabla-wrap {
  border: 1px solid var(--borde);
  border-radius: 10px; overflow: hidden;
}
.etiquetas-tabla { width: 100%; border-collapse: collapse; }
.etiquetas-tabla th {
  background: #FFCC00; color: #1A1A1A;
  text-align: left; padding: 0.6rem 0.75rem;
  font-size: 0.8rem; font-weight: 700;
}
.etiquetas-tabla td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--borde-suave, #F0F0EC);
  font-size: 0.85rem;
}
.badge-oferta {
  background: #FEE2E2; color: #DC2626;
  font-weight: 700; padding: 0.15rem 0.5rem;
  border-radius: 4px; font-size: 0.78rem;
}
.sin-datos { text-align: center; padding: 2rem; color: var(--texto-muted); }
</style>
