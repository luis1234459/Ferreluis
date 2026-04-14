<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Programa de Fidelidad</h1>
      </div>

      <div class="contenido-inner">
        <!-- Niveles -->
        <h2 class="seccion-h2">Niveles configurados</h2>
        <div class="niveles-grid">
          <div v-for="n in niveles" :key="n.id" class="nivel-card" :style="{ borderColor: n.color_badge }">
            <div class="nivel-badge" :style="{ background: n.color_badge + '22', color: n.color_badge }">{{ n.nombre }}</div>
            <div class="nivel-condiciones">
              <span>{{ n.min_compras }} compras</span>
              <span>+</span>
              <span>${{ n.min_monto_usd }} acumulados</span>
            </div>
            <p class="nivel-beneficio">{{ n.beneficio_descripcion }}</p>
            <button class="btn-editar-nivel" @click="abrirEditarNivel(n)">Editar</button>
          </div>
        </div>

        <!-- Ranking -->
        <h2 class="seccion-h2">Ranking de clientes</h2>
        <div class="tabs">
          <button :class="['tab', criterio === 'monto' ? 'activo' : '']" @click="cambiarCriterio('monto')">Por monto</button>
          <button :class="['tab', criterio === 'compras' ? 'activo' : '']" @click="cambiarCriterio('compras')">Por compras</button>
        </div>
        <div class="tabla-container">
          <table>
            <thead>
              <tr>
                <th>Pos.</th>
                <th>Cliente</th>
                <th>Nivel</th>
                <th>Compras</th>
                <th>Acumulado USD</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(c, i) in ranking" :key="c.id">
                <td class="pos">{{ i + 1 }}</td>
                <td>{{ c.nombre }}</td>
                <td>
                  <span v-if="c.nivel_fidelidad" class="badge-nivel"
                    :style="{ background: c.nivel_fidelidad.color + '33', color: c.nivel_fidelidad.color, border: '1px solid ' + c.nivel_fidelidad.color }">
                    {{ c.nivel_fidelidad.nombre }}
                  </span>
                  <span v-else class="sin-nivel">—</span>
                </td>
                <td>{{ c.total_compras }}</td>
                <td class="txt-verde">${{ c.monto_acumulado_usd.toFixed(2) }}</td>
              </tr>
              <tr v-if="ranking.length === 0">
                <td colspan="5" class="sin-datos">Sin clientes registrados</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Dialog editar nivel -->
        <div class="overlay" v-if="nivelEditar">
          <div class="dialog">
            <h2>Editar nivel: {{ nivelEditar.nombre }}</h2>
            <div class="grid-form">
              <div class="field">
                <label>Nombre</label>
                <input v-model="nivelEditar.nombre" />
              </div>
              <div class="field">
                <label>Color (hex)</label>
                <input v-model="nivelEditar.color_badge" type="color" />
              </div>
              <div class="field">
                <label>Mín. compras</label>
                <input v-model.number="nivelEditar.min_compras" type="number" min="0" />
              </div>
              <div class="field">
                <label>Mín. monto USD</label>
                <input v-model.number="nivelEditar.min_monto_usd" type="number" min="0" step="0.01" />
              </div>
              <div class="field full">
                <label>Beneficio</label>
                <input v-model="nivelEditar.beneficio_descripcion" />
              </div>
            </div>
            <div class="form-botones">
              <button class="btn-cancelar" @click="nivelEditar = null">Cancelar</button>
              <button class="btn-guardar" @click="guardarNivel">Guardar</button>
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
  name: 'Fidelidad',
  data() {
    return {
      usuario:     JSON.parse(localStorage.getItem('usuario') || '{}'),
      niveles:     [],
      ranking:     [],
      criterio:    'monto',
      nivelEditar: null,
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
    await Promise.all([this.cargarNiveles(), this.cargarRanking()])
  },
  methods: {
    async cargarNiveles() {
      const res = await axios.get('/clientes/fidelidad/niveles')
      this.niveles = res.data
    },
    async cargarRanking() {
      const res = await axios.get('/clientes/fidelidad/ranking', { params: { criterio: this.criterio } })
      this.ranking = res.data
    },
    async cambiarCriterio(c) {
      this.criterio = c
      await this.cargarRanking()
    },
    abrirEditarNivel(n) {
      this.nivelEditar = { ...n }
    },
    async guardarNivel() {
      await axios.put(`/clientes/fidelidad/niveles/${this.nivelEditar.id}`, this.nivelEditar)
      await this.cargarNiveles()
      this.nivelEditar = null
    },
    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    }
  }
}
</script>

<style scoped>
.seccion-h2 { color: var(--texto-principal); font-size: 1.1rem; margin: 1.5rem 0 1rem; font-weight: 700; }

.niveles-grid { display: flex; gap: 1.25rem; flex-wrap: wrap; margin-bottom: 2rem; }
.nivel-card { background: #FFFFFF; border: 2px solid; border-radius: 14px; padding: 1.25rem 1.5rem; min-width: 200px; display: flex; flex-direction: column; gap: 0.75rem; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.nivel-badge { display: inline-block; padding: 0.3rem 0.9rem; border-radius: 20px; font-weight: 700; font-size: 0.95rem; align-self: flex-start; }
.nivel-condiciones { display: flex; gap: 0.5rem; color: var(--texto-sec); font-size: 0.85rem; align-items: center; }
.nivel-beneficio { color: var(--texto-sec); font-size: 0.82rem; margin: 0; flex: 1; }
.btn-editar-nivel { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.35rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; align-self: flex-start; }

.pos { font-weight: 700; color: var(--texto-principal); }
.sin-nivel { color: var(--texto-muted); }
.badge-nivel { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 20px; font-size: 0.78rem; font-weight: 700; }

.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.55rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: 600; }
.btn-cancelar { background: transparent; color: #1A1A1A; border: 1px solid #DDDDDD; padding: 0.55rem 1.2rem; border-radius: 6px; cursor: pointer; }
</style>
