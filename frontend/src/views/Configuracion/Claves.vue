<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Claves de Autorización</h1>
      </div>

      <div class="contenido-inner">
        <div class="info-box">
          <p>Estas claves protegen acciones sensibles en el sistema. La clave por defecto es <strong>1234</strong>. Cámbiala para mayor seguridad.</p>
        </div>

        <div v-if="cargando" class="sin-datos">Cargando...</div>

        <div v-else class="claves-grid">
          <div v-for="c in claves" :key="c.accion" class="clave-card">
            <div class="clave-info">
              <h3>{{ c.descripcion }}</h3>
              <span class="clave-accion">{{ c.accion }}</span>
            </div>

            <div class="clave-form" v-if="editando === c.accion">
              <input
                v-model="nuevaClave[c.accion]"
                type="password"
                placeholder="Nueva clave..."
                @keydown.enter="guardar(c.accion)"
                @keydown.esc="editando = null"
                ref="inputClave"
              />
              <div class="clave-btns">
                <button class="btn-cancelar" @click="editando = null">Cancelar</button>
                <button class="btn-guardar" @click="guardar(c.accion)"
                  :disabled="!nuevaClave[c.accion]">Guardar</button>
              </div>
              <p class="msg-error" v-if="errores[c.accion]">{{ errores[c.accion] }}</p>
              <p class="msg-ok" v-if="okAcciones[c.accion]">Clave actualizada correctamente</p>
            </div>

            <button v-else class="btn-cambiar" @click="abrirEditar(c.accion)">
              Cambiar clave
            </button>
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
  name: 'Claves',
  data() {
    return {
      claves:     [],
      cargando:   true,
      editando:   null,
      nuevaClave: {},
      errores:    {},
      okAcciones: {},
    }
  },
  async mounted() {
    await this.cargar()
  },
  methods: {
    async cargar() {
      this.cargando = true
      try {
        const res = await axios.get('/claves/')
        this.claves = res.data
      } catch (e) {
        console.error(e)
      } finally {
        this.cargando = false
      }
    },
    abrirEditar(accion) {
      this.editando              = accion
      this.nuevaClave[accion]    = ''
      this.errores[accion]       = ''
      this.okAcciones[accion]    = false
      this.$nextTick(() => {
        const inp = this.$refs.inputClave
        if (inp) { (Array.isArray(inp) ? inp[0] : inp).focus() }
      })
    },
    async guardar(accion) {
      const clave = (this.nuevaClave[accion] || '').trim()
      if (!clave) { this.errores[accion] = 'La clave no puede estar vacía'; return }

      try {
        await axios.put(`/claves/${accion}`, { clave })
        this.okAcciones[accion] = true
        this.errores[accion]    = ''
        this.editando           = null
        setTimeout(() => { this.okAcciones[accion] = false }, 3000)
      } catch (e) {
        this.errores[accion] = e?.response?.data?.detail || 'Error al guardar'
      }
    },
  },
}
</script>

<style scoped>
.info-box {
  background: #FFFBEB;
  border: 1px solid #F59E0B;
  border-radius: 10px;
  padding: 0.9rem 1.2rem;
  margin-bottom: 1.5rem;
  color: #92400E;
  font-size: 0.9rem;
}
.info-box strong { color: #1A1A1A; }

.claves-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.clave-card {
  background: #FFFFFF;
  border: 1px solid var(--borde);
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.clave-info h3 {
  color: var(--texto-principal);
  font-size: 0.95rem;
  margin: 0 0 0.35rem;
  font-weight: 700;
}

.clave-accion {
  display: inline-block;
  background: #1A1A1A;
  color: #FFCC00;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.15rem 0.55rem;
  border-radius: 4px;
  letter-spacing: 0.04em;
  font-family: monospace;
}

.btn-cambiar {
  padding: 0.55rem 1.2rem;
  background: transparent;
  border: 1px solid #DDDDDD;
  color: var(--texto-sec);
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.88rem;
  align-self: flex-start;
  transition: border-color 0.15s, color 0.15s;
}
.btn-cambiar:hover { border-color: #1A1A1A; color: #1A1A1A; }

.clave-form { display: flex; flex-direction: column; gap: 0.6rem; }
.clave-form input {
  padding: 0.55rem 0.8rem;
  background: #FFFFFF;
  border: 1px solid #CCCCCC;
  color: var(--texto-principal);
  border-radius: 8px;
  font-size: 0.9rem;
  box-sizing: border-box;
}
.clave-form input:focus { outline: none; border-color: #FFCC00; box-shadow: 0 0 0 2px #FFCC0033; }

.clave-btns { display: flex; gap: 0.5rem; }
.btn-guardar {
  flex: 1;
  padding: 0.5rem;
  background: #1A1A1A;
  color: #FFCC00;
  border: none;
  border-radius: 7px;
  cursor: pointer;
  font-weight: 700;
  font-size: 0.88rem;
}
.btn-guardar:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-cancelar {
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid #DDDDDD;
  color: var(--texto-sec);
  border-radius: 7px;
  cursor: pointer;
  font-size: 0.88rem;
}

.msg-error { color: #DC2626; font-size: 0.85rem; margin: 0; }
.msg-ok    { color: #16A34A; font-size: 0.85rem; margin: 0; font-weight: 600; }
</style>