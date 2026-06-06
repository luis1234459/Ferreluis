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
            <button v-if="esAdmin" class="btn-nuevo-depto"
              @click="abrirModalDepto(null)">
              + Nuevo departamento
            </button>
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
                <div v-if="esAdmin" class="depto-acciones" @click.stop>
                  <button class="btn-edit-depto"
                    @click.stop="abrirModalDepto(d)"
                    title="Editar">✏️</button>
                </div>
              </div>

              <div v-if="expandido === d.id" class="depto-cats">
                <div v-if="d.categorias.length === 0" class="cat-vacia">Sin categorías</div>
                <div v-else class="cats-columnas">
                  <div v-for="(col, ci) in columnasCategoria(d.categorias)" :key="ci" class="cats-col">
                    <div v-for="c in col" :key="c.id" class="cat-item">
                      <span class="cat-bullet">›</span>
                      {{ c.nombre }}
                      <button v-if="esAdmin" class="btn-edit-cat"
                        @click="abrirModalCat(d.id, c)"
                        title="Editar">✏️</button>
                    </div>
                  </div>
                </div>
                <button v-if="esAdmin" class="btn-nueva-cat"
                  @click="abrirModalCat(d.id, null)">
                  + Categoría
                </button>
              </div>
            </div>
          </div>

          <div class="mapa-resumen" v-if="!cargando">
            <span>{{ departamentos.length }} departamentos</span>
            <span>·</span>
            <span>{{ totalCategorias }} categorías en total</span>
          </div>

          <div v-if="esAdmin && !cargando" class="marcas-seccion">
            <div class="marcas-header">
              <h2 class="marcas-titulo">🏷 Marcas</h2>
              <button class="btn-nuevo-depto" @click="abrirModalMarca(null)">
                + Nueva marca
              </button>
            </div>
            <div class="marcas-grid">
              <div v-for="m in marcas" :key="m.id" class="marca-chip-admin">
                {{ m.nombre }}
                <button class="btn-edit-cat" @click="abrirModalMarca(m)">✏️</button>
              </div>
              <div v-if="marcas.length === 0" class="cat-vacia">Sin marcas registradas</div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Modal departamento -->
    <div v-if="modalDepto" class="mapa-overlay"
      @click.self="modalDepto = false">
      <div class="mapa-modal">
        <h3>{{ formDepto.id ? 'Editar' : 'Nuevo' }} departamento</h3>
        <input v-model="formDepto.nombre"
          placeholder="Nombre del departamento"
          class="mapa-input" ref="inputDepto"
        />
        <div class="mapa-modal-botones">
          <button class="btn-cancelar"
            @click="modalDepto = false">Cancelar</button>
          <button class="btn-guardar"
            @click="guardarDepto"
            :disabled="guardandoDepto || !formDepto.nombre.trim()">
            {{ guardandoDepto ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal marca -->
    <div v-if="modalMarca" class="mapa-overlay"
      @click.self="modalMarca = false">
      <div class="mapa-modal">
        <h3>{{ formMarca.id ? 'Editar' : 'Nueva' }} marca</h3>
        <input v-model="formMarca.nombre"
          placeholder="Nombre de la marca"
          class="mapa-input" ref="inputMarca"
        />
        <div class="mapa-modal-botones">
          <button class="btn-cancelar"
            @click="modalMarca = false">Cancelar</button>
          <button class="btn-guardar"
            @click="guardarMarca"
            :disabled="guardandoMarca || !formMarca.nombre.trim()">
            {{ guardandoMarca ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal categoría -->
    <div v-if="modalCat" class="mapa-overlay"
      @click.self="modalCat = false">
      <div class="mapa-modal">
        <h3>{{ formCat.id ? 'Editar' : 'Nueva' }} categoría</h3>
        <input v-model="formCat.nombre"
          placeholder="Nombre de la categoría"
          class="mapa-input" ref="inputCat"
        />
        <div class="mapa-modal-botones">
          <button class="btn-cancelar"
            @click="modalCat = false">Cancelar</button>
          <button class="btn-guardar"
            @click="guardarCat"
            :disabled="guardandoCat || !formCat.nombre.trim()">
            {{ guardandoCat ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>
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
      departamentos:  [],
      expandido:      null,
      cargando:       true,
      busqueda:       '',
      usuario:        JSON.parse(localStorage.getItem('usuario') || '{}'),
      modalDepto:     false,
      formDepto:      { id: null, nombre: '' },
      modalCat:       false,
      formCat:        { id: null, nombre: '', departamento_id: null },
      guardandoDepto: false,
      guardandoCat:   false,
      marcas:         [],
      modalMarca:     false,
      formMarca:      { id: null, nombre: '' },
      guardandoMarca: false,
    }
  },
  computed: {
    esAdmin() { return this.usuario.rol === 'admin' },
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
    abrirModalDepto(d) {
      this.formDepto = d
        ? { id: d.id, nombre: d.nombre }
        : { id: null, nombre: '' }
      this.modalDepto = true
      this.$nextTick(() => this.$refs.inputDepto?.focus())
    },
    abrirModalCat(deptoId, c) {
      this.formCat = c
        ? { id: c.id, nombre: c.nombre, departamento_id: deptoId }
        : { id: null, nombre: '', departamento_id: deptoId }
      this.modalCat = true
      this.$nextTick(() => this.$refs.inputCat?.focus())
    },
    async guardarDepto() {
      this.guardandoDepto = true
      try {
        if (this.formDepto.id) {
          await axios.put(
            `/productos/departamentos/${this.formDepto.id}`,
            { nombre: this.formDepto.nombre }
          )
        } else {
          await axios.post('/productos/departamentos',
            { nombre: this.formDepto.nombre }
          )
        }
        this.modalDepto = false
        await this.cargarDepartamentos()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al guardar')
      } finally { this.guardandoDepto = false }
    },
    async guardarCat() {
      this.guardandoCat = true
      try {
        if (this.formCat.id) {
          await axios.put(
            `/productos/categorias/${this.formCat.id}`,
            { nombre: this.formCat.nombre,
              departamento_id: this.formCat.departamento_id }
          )
        } else {
          await axios.post('/productos/categorias',
            { nombre: this.formCat.nombre,
              departamento_id: this.formCat.departamento_id }
          )
        }
        this.modalCat = false
        await this.cargarDepartamentos()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al guardar')
      } finally { this.guardandoCat = false }
    },
    async cargarDepartamentos() {
      const res = await axios.get('/productos/departamentos-con-categorias')
      this.departamentos = res.data
    },
    async cargarMarcas() {
      try {
        const res = await axios.get('/marcas/')
        this.marcas = res.data
      } catch { this.marcas = [] }
    },
    abrirModalMarca(m) {
      this.formMarca = m
        ? { id: m.id, nombre: m.nombre }
        : { id: null, nombre: '' }
      this.modalMarca = true
      this.$nextTick(() => this.$refs.inputMarca?.focus())
    },
    async guardarMarca() {
      this.guardandoMarca = true
      try {
        if (this.formMarca.id) {
          await axios.put(`/marcas/${this.formMarca.id}`, { nombre: this.formMarca.nombre })
        } else {
          await axios.post('/marcas/', { nombre: this.formMarca.nombre })
        }
        this.modalMarca = false
        await this.cargarMarcas()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al guardar')
      } finally { this.guardandoMarca = false }
    },
  },
  async mounted() {
    try {
      await Promise.all([
        this.cargarDepartamentos(),
        this.cargarMarcas(),
      ])
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
.btn-nuevo-depto { background: #1A1A1A; color: #FFCC00; border: none; border-radius: 8px; padding: 0.5rem 1rem; font-weight: 700; font-size: 0.85rem; cursor: pointer; margin-top: 0.75rem; }
.btn-nuevo-depto:hover { background: #333; }
.depto-acciones { display: flex; gap: 0.25rem; }
.btn-edit-depto { background: none; border: none; cursor: pointer; font-size: 0.85rem; padding: 0.1rem 0.25rem; opacity: 0.7; }
.btn-edit-depto:hover { opacity: 1; }
.btn-nueva-cat { background: #F1F5F9; border: 1px dashed #CBD5E1; border-radius: 6px; padding: 0.3rem 0.75rem; font-size: 0.78rem; font-weight: 600; cursor: pointer; color: #475569; margin-top: 0.25rem; width: 100%; }
.btn-nueva-cat:hover { background: #E2E8F0; border-color: #94A3B8; }
.btn-edit-cat { background: none; border: none; cursor: pointer; font-size: 0.75rem; padding: 0; opacity: 0; margin-left: auto; }
.cat-item:hover .btn-edit-cat { opacity: 0.6; }
.btn-edit-cat:hover { opacity: 1 !important; }
.mapa-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 999; display: flex; align-items: center; justify-content: center; }
.mapa-modal { background: #FFFFFF; border-radius: 12px; padding: 1.5rem; width: 100%; max-width: 380px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); display: flex; flex-direction: column; gap: 1rem; }
.mapa-modal h3 { font-size: 1rem; font-weight: 700; margin: 0; color: var(--texto-principal); }
.mapa-input { border: 1px solid var(--borde); border-radius: 8px; padding: 0.6rem 0.85rem; font-size: 0.9rem; width: 100%; box-sizing: border-box; }
.mapa-input:focus { outline: none; border-color: #FFCC00; }
.mapa-modal-botones { display: flex; gap: 0.5rem; justify-content: flex-end; }
.btn-cancelar { background: #F1F5F9; border: 1px solid var(--borde); border-radius: 8px; padding: 0.5rem 1rem; font-size: 0.85rem; cursor: pointer; color: #475569; }
.btn-cancelar:hover { background: #E2E8F0; }
.btn-guardar { background: #1A1A1A; color: #FFCC00; border: none; border-radius: 8px; padding: 0.5rem 1rem; font-weight: 700; font-size: 0.85rem; cursor: pointer; }
.btn-guardar:hover:not(:disabled) { background: #333; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.marcas-seccion { margin-top: 2rem; border-top: 2px solid var(--borde); padding-top: 1.5rem; }
.marcas-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.marcas-titulo { font-size: 1.1rem; font-weight: 800; margin: 0; color: var(--texto-principal); }
.marcas-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.marca-chip-admin { background: #F1F5F9; border: 1px solid var(--borde); border-radius: 20px; padding: 0.3rem 0.75rem; font-size: 0.82rem; font-weight: 600; display: flex; align-items: center; gap: 0.4rem; }
</style>
