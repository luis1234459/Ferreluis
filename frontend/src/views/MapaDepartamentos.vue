<template>
  <div class="layout">
    <AppSidebar />
    <main class="contenido">
      <div class="contenido-inner">
        <div class="mapa-wrap">
          <div class="mapa-header">
            <h1 class="mapa-titulo">🗂 Mapa de departamentos</h1>
            <p class="mapa-sub">Estructura de departamentos y categorías del inventario</p>
            <input v-model="busqueda"
              placeholder="🔍 Buscar departamento o categoría..."
              class="mapa-busqueda"
            />
          </div>

          <div v-if="cargando" class="mapa-cargando">Cargando estructura...</div>

          <div v-else class="mapa-grid">
            <div v-for="d in departamentosFiltrados" :key="d.id"
              class="depto-card"
              :class="{ 'depto-expandido': expandido === d.id }">

              <div class="depto-header"
                @click="expandido = expandido === d.id ? null : d.id">
                <span class="depto-icono">📦</span>
                <span class="depto-nombre">{{ d.nombre }}</span>
                <span class="depto-badge">
                  {{ d.categorias.length }} {{ d.categorias.length === 1 ? 'categoría' : 'categorías' }}
                </span>
                <span class="depto-toggle">{{ expandido === d.id ? '▲' : '▼' }}</span>
              </div>

              <div v-if="expandido === d.id" class="depto-cats">
                <div v-if="d.categorias.length === 0" class="cat-vacia">Sin categorías</div>
                <div v-else class="cats-columnas">
                  <div v-for="(col, ci) in columnasCategoria(d.categorias)" :key="ci" class="cats-col">
                    <div v-for="c in col" :key="c.id" class="cat-item">
                      <span class="cat-bullet">›</span>
                      {{ c.nombre }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="mapa-resumen" v-if="!cargando">
            <span>{{ departamentos.length }} departamentos</span>
            <span>·</span>
            <span>{{ totalCategorias }} categorías en total</span>
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
  name: 'MapaDepartamentos',
  data() {
    return {
      departamentos: [],
      expandido:     null,
      cargando:      true,
      busqueda:      '',
    }
  },
  computed: {
    totalCategorias() {
      return this.departamentos.reduce((s, d) => s + d.categorias.length, 0)
    },
    departamentosFiltrados() {
      if (!this.busqueda.trim()) return this.departamentos
      const q = this.busqueda.toLowerCase()
      return this.departamentos.filter(d =>
        d.nombre.toLowerCase().includes(q) ||
        d.categorias.some(c => c.nombre.toLowerCase().includes(q))
      )
    },
  },
  methods: {
    columnasCategoria(cats) {
      const porColumna = 4
      const cols = []
      for (let i = 0; i < cats.length; i += porColumna) {
        cols.push(cats.slice(i, i + porColumna))
      }
      return cols
    },
  },
  async mounted() {
    try {
      const res = await axios.get('/productos/departamentos-con-categorias')
      this.departamentos = res.data
    } catch {
      this.departamentos = []
    } finally {
      this.cargando = false
    }
  },
}
</script>

<style scoped>
.mapa-wrap { max-width: 900px; margin: 0 auto; padding: 1.5rem; }
.mapa-header { margin-bottom: 1.5rem; }
.mapa-titulo { font-size: 1.3rem; font-weight: 800; color: var(--texto-principal); margin: 0 0 0.25rem; }
.mapa-sub { font-size: 0.85rem; color: var(--texto-muted); margin: 0 0 0.75rem; }
.mapa-busqueda { width: 100%; max-width: 400px; border: 1px solid var(--borde); border-radius: 8px; padding: 0.5rem 0.85rem; font-size: 0.9rem; }
.mapa-busqueda:focus { outline: none; border-color: #FFCC00; }
.mapa-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem; }
.depto-card { border: 1px solid var(--borde); border-radius: 10px; overflow: hidden; transition: box-shadow 0.2s; }
.depto-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
.depto-expandido { border-color: #FFCC00; box-shadow: 0 2px 12px rgba(255,204,0,0.15); }
.depto-header { display: flex; align-items: center; gap: 0.6rem; padding: 0.85rem 1rem; cursor: pointer; background: #FAFAF7; user-select: none; }
.depto-expandido .depto-header { background: #1A1A1A; color: #FFCC00; }
.depto-icono { font-size: 1.1rem; flex-shrink: 0; }
.depto-nombre { flex: 1; font-weight: 700; font-size: 0.9rem; }
.depto-expandido .depto-nombre { color: #FFCC00; }
.depto-badge { font-size: 0.72rem; font-weight: 700; background: #F1F5F9; color: #475569; padding: 0.15rem 0.5rem; border-radius: 10px; white-space: nowrap; }
.depto-expandido .depto-badge { background: rgba(255,204,0,0.2); color: #FFCC00; }
.depto-toggle { font-size: 0.72rem; color: var(--texto-muted); flex-shrink: 0; }
.depto-expandido .depto-toggle { color: #FFCC00; }
.depto-cats { padding: 0.75rem 1rem; border-top: 1px solid var(--borde); background: #FFFFFF; }
.cats-columnas { display: flex; gap: 1.5rem; flex-wrap: wrap; }
.cats-col { display: flex; flex-direction: column; gap: 0.3rem; min-width: 160px; }
.cat-item { display: flex; align-items: center; gap: 0.35rem; font-size: 0.82rem; color: var(--texto-principal); padding: 0.2rem 0; border-bottom: 1px solid #F0F0EC; }
.cat-item:last-child { border-bottom: none; }
.cat-bullet { color: #FFCC00; font-weight: 900; font-size: 1rem; line-height: 1; }
.cat-vacia { font-size: 0.78rem; color: var(--texto-muted); font-style: italic; }
.mapa-resumen { display: flex; gap: 0.5rem; font-size: 0.78rem; color: var(--texto-muted); justify-content: center; }
.mapa-cargando { text-align: center; padding: 3rem; color: var(--texto-muted); }
</style>
