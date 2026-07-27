<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Cartelería Digital</h1>
      </div>

      <div class="contenido-inner">
        <div class="info-box">
          <p>
            Cada pantalla tiene su propia URL <code>/pantalla/&lt;id&gt;</code> para abrir en el TV.
            Solo entran a la cola productos y ofertas que tengan foto cargada.
          </p>
        </div>

        <div v-if="cargando" class="sin-datos">Cargando...</div>

        <template v-else>
          <!-- ═══════════ Pantallas ═══════════ -->
          <div class="cart-seccion-header">
            <h2 class="cart-subtitulo">Pantallas</h2>
          </div>

          <div class="cart-grid">
            <div v-for="p in pantallas" :key="p.id" class="cart-card">
              <div class="cart-card-header">
                <div>
                  <strong>{{ p.nombre }}</strong>
                  <span :class="p.activa ? 'badge-activa' : 'badge-inactiva'">
                    {{ p.activa ? 'Activa' : 'Inactiva' }}
                  </span>
                </div>
                <div class="cart-card-acciones">
                  <a class="cart-link" :href="`/pantalla/${p.id}`" target="_blank">Abrir ↗</a>
                  <button class="btn-editar" @click="editarPantalla(p)">Editar</button>
                </div>
              </div>
              <div class="cart-card-body">
                <p class="cart-deptos">
                  <strong>Departamentos:</strong>
                  {{ nombresDepartamentos(p.departamento_ids) || 'Ninguno asignado' }}
                </p>
                <p class="cart-timing">
                  Producto {{ p.segundos_producto }}s · Oferta {{ p.segundos_oferta }}s · Marca {{ p.segundos_marca }}s
                  &nbsp;|&nbsp; Proporción {{ p.ratio_producto }}:{{ p.ratio_oferta }}:{{ p.ratio_marca }}
                </p>
              </div>
            </div>
          </div>

          <!-- ═══════════ Slides de marca ═══════════ -->
          <div class="cart-seccion-header" style="margin-top:2rem">
            <h2 class="cart-subtitulo">Slides de marca</h2>
            <button class="btn-nuevo" @click="abrirNuevoSlide">+ Nuevo slide</button>
          </div>
          <p class="cart-desc">Imágenes institucionales/marca que se intercalan entre productos y ofertas.</p>

          <div class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Foto</th>
                  <th>Título</th>
                  <th>Orden</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in slides" :key="s.id">
                  <td><img v-if="s.foto_url" :src="s.foto_url" class="cart-thumb" /></td>
                  <td>{{ s.titulo || '—' }}</td>
                  <td>{{ s.orden }}</td>
                  <td>
                    <span :class="s.activo ? 'badge-activa' : 'badge-inactiva'">
                      {{ s.activo ? 'Activo' : 'Inactivo' }}
                    </span>
                  </td>
                  <td class="acciones">
                    <button class="btn-editar" @click="editarSlide(s)">Editar</button>
                    <button class="btn-eliminar" @click="eliminarSlide(s.id)">Eliminar</button>
                  </td>
                </tr>
                <tr v-if="slides.length === 0">
                  <td colspan="5" class="sin-datos">No hay slides de marca creados</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- ═══════════ Modal: Editar pantalla ═══════════ -->
        <div class="overlay" v-if="mostrarFormPantalla" @click.self="cerrarPantalla">
          <div class="modal modal-sm">
            <div class="modal-header">
              <h2>Editar pantalla</h2>
              <button class="btn-cerrar-modal" @click="cerrarPantalla">✕</button>
            </div>
            <div class="grid-form">
              <div class="field field-wide">
                <label>Nombre</label>
                <input v-model="formPantalla.nombre" placeholder="Ej: Valera - TV 1" />
              </div>
              <div class="field field-wide">
                <label class="check-opt">
                  <input type="checkbox" v-model="formPantalla.activa" />
                  <span class="check-label"><strong>Pantalla activa</strong></span>
                </label>
              </div>
              <div class="field field-wide">
                <label>Departamentos asignados</label>
                <div class="cart-deptos-check">
                  <label v-for="d in departamentos" :key="d.id" class="check-opt cart-depto-opt">
                    <input type="checkbox" :value="d.id" v-model="formPantalla.departamento_ids" />
                    <span>{{ d.nombre }}</span>
                  </label>
                </div>
              </div>
              <div class="field">
                <label>Segundos por producto</label>
                <input v-model.number="formPantalla.segundos_producto" type="number" min="1" />
              </div>
              <div class="field">
                <label>Segundos por oferta</label>
                <input v-model.number="formPantalla.segundos_oferta" type="number" min="1" />
              </div>
              <div class="field">
                <label>Segundos por slide de marca</label>
                <input v-model.number="formPantalla.segundos_marca" type="number" min="1" />
              </div>
              <div class="field">
                <label>Proporción producto <small>(peso relativo)</small></label>
                <input v-model.number="formPantalla.ratio_producto" type="number" min="0" />
              </div>
              <div class="field">
                <label>Proporción oferta <small>(peso relativo)</small></label>
                <input v-model.number="formPantalla.ratio_oferta" type="number" min="0" />
              </div>
              <div class="field">
                <label>Proporción marca <small>(peso relativo)</small></label>
                <input v-model.number="formPantalla.ratio_marca" type="number" min="0" />
              </div>
            </div>
            <div class="form-botones" style="margin-top:1rem">
              <button class="btn-cancelar" @click="cerrarPantalla">Cancelar</button>
              <button class="btn-guardar" @click="guardarPantalla" :disabled="guardando">
                {{ guardando ? 'Guardando...' : 'Guardar' }}
              </button>
            </div>
            <p class="msg-error" v-if="errorPantalla">{{ errorPantalla }}</p>
          </div>
        </div>

        <!-- ═══════════ Modal: Nuevo/Editar slide de marca ═══════════ -->
        <div class="overlay" v-if="mostrarFormSlide" @click.self="cerrarSlide">
          <div class="modal modal-sm">
            <div class="modal-header">
              <h2>{{ editandoSlideId ? 'Editar slide' : 'Nuevo slide' }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarSlide">✕</button>
            </div>
            <div class="grid-form">
              <div class="field field-wide">
                <label>URL de imagen *</label>
                <input v-model="formSlide.foto_url" type="url" placeholder="https://ejemplo.com/marca.jpg" />
                <img v-if="formSlide.foto_url" :src="formSlide.foto_url"
                  style="max-height:80px; margin-top:0.5rem; border-radius:6px; border:1px solid var(--borde)"
                  @error="formSlide.foto_url = ''" />
              </div>
              <div class="field field-wide">
                <label>Título <small>(opcional)</small></label>
                <input v-model="formSlide.titulo" placeholder="Ej: Bienvenidos a Ferreutil" />
              </div>
              <div class="field">
                <label>Orden</label>
                <input v-model.number="formSlide.orden" type="number" min="0" />
              </div>
              <div class="field">
                <label class="check-opt" style="margin-top:1.35rem">
                  <input type="checkbox" v-model="formSlide.activo" />
                  <span class="check-label"><strong>Activo</strong></span>
                </label>
              </div>
            </div>
            <div class="form-botones" style="margin-top:1rem">
              <button class="btn-cancelar" @click="cerrarSlide">Cancelar</button>
              <button class="btn-guardar" @click="guardarSlide" :disabled="guardando">
                {{ guardando ? 'Guardando...' : 'Guardar' }}
              </button>
            </div>
            <p class="msg-error" v-if="errorSlide">{{ errorSlide }}</p>
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
  name: 'Cartelera',
  components: { AppSidebar },
  data() {
    return {
      cargando: true,
      pantallas: [],
      departamentos: [],
      slides: [],

      mostrarFormPantalla: false,
      editandoPantallaId: null,
      formPantalla: {},
      errorPantalla: '',

      mostrarFormSlide: false,
      editandoSlideId: null,
      formSlide: {},
      errorSlide: '',

      guardando: false,
    }
  },
  async mounted() {
    await this.cargarTodo()
  },
  methods: {
    async cargarTodo() {
      this.cargando = true
      try {
        const [rPantallas, rDeptos, rSlides] = await Promise.all([
          axios.get('/pantallas/'),
          axios.get('/productos/departamentos'),
          axios.get('/pantallas/slides-marca'),
        ])
        this.pantallas     = rPantallas.data
        this.departamentos = rDeptos.data
        this.slides        = rSlides.data
      } finally {
        this.cargando = false
      }
    },
    nombresDepartamentos(ids) {
      if (!ids || !ids.length) return ''
      return ids
        .map(id => this.departamentos.find(d => d.id === id)?.nombre)
        .filter(Boolean)
        .join(', ')
    },

    // ── Pantallas ──────────────────────────────────────────────────────────
    editarPantalla(p) {
      this.editandoPantallaId = p.id
      this.errorPantalla      = ''
      this.formPantalla = {
        nombre:            p.nombre,
        activa:            p.activa,
        segundos_producto: p.segundos_producto,
        segundos_oferta:   p.segundos_oferta,
        segundos_marca:    p.segundos_marca,
        ratio_producto:    p.ratio_producto,
        ratio_oferta:      p.ratio_oferta,
        ratio_marca:       p.ratio_marca,
        departamento_ids:  [...(p.departamento_ids || [])],
      }
      this.mostrarFormPantalla = true
    },
    cerrarPantalla() {
      this.mostrarFormPantalla = false
      this.editandoPantallaId  = null
      this.errorPantalla       = ''
    },
    async guardarPantalla() {
      if (!this.formPantalla.nombre?.trim()) { this.errorPantalla = 'El nombre es obligatorio'; return }
      this.guardando = true; this.errorPantalla = ''
      try {
        await axios.put(`/pantallas/${this.editandoPantallaId}`, this.formPantalla)
        await this.cargarTodo()
        this.cerrarPantalla()
      } catch (e) {
        this.errorPantalla = e?.response?.data?.detail || 'Error al guardar'
      } finally {
        this.guardando = false
      }
    },

    // ── Slides de marca ──────────────────────────────────────────────────────
    abrirNuevoSlide() {
      this.editandoSlideId = null
      this.errorSlide       = ''
      this.formSlide = { foto_url: '', titulo: '', orden: 0, activo: true }
      this.mostrarFormSlide = true
    },
    editarSlide(s) {
      this.editandoSlideId = s.id
      this.errorSlide       = ''
      this.formSlide = { foto_url: s.foto_url, titulo: s.titulo || '', orden: s.orden, activo: s.activo }
      this.mostrarFormSlide = true
    },
    cerrarSlide() {
      this.mostrarFormSlide = false
      this.editandoSlideId  = null
      this.errorSlide       = ''
    },
    async guardarSlide() {
      if (!this.formSlide.foto_url?.trim()) { this.errorSlide = 'La URL de imagen es obligatoria'; return }
      this.guardando = true; this.errorSlide = ''
      try {
        if (this.editandoSlideId) {
          await axios.put(`/pantallas/slides-marca/${this.editandoSlideId}`, this.formSlide)
        } else {
          await axios.post('/pantallas/slides-marca', this.formSlide)
        }
        await this.cargarTodo()
        this.cerrarSlide()
      } catch (e) {
        this.errorSlide = e?.response?.data?.detail || 'Error al guardar'
      } finally {
        this.guardando = false
      }
    },
    async eliminarSlide(id) {
      if (!confirm('¿Eliminar este slide?')) return
      await axios.delete(`/pantallas/slides-marca/${id}`)
      await this.cargarTodo()
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
.info-box code { background: rgba(0,0,0,0.08); padding: 0.1rem 0.4rem; border-radius: 4px; }

.cart-seccion-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem; }
.cart-subtitulo { font-size: 1rem; font-weight: 700; color: var(--texto-principal); margin: 0; }
.cart-desc { color: var(--texto-sec); font-size: 0.85rem; margin: 0 0 1rem; }

.btn-nuevo {
  background: #1A1A1A; color: #FFCC00;
  border: none; padding: 0.55rem 1.2rem;
  border-radius: 8px; cursor: pointer; font-size: 0.9rem; font-weight: 700;
}
.btn-nuevo:hover { background: #333; }

.cart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}
.cart-card {
  background: #FFFFFF;
  border: 1px solid var(--borde);
  border-radius: 12px;
  padding: 1.1rem 1.25rem;
}
.cart-card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; }
.cart-card-acciones { display: flex; gap: 0.6rem; align-items: center; }
.cart-link { font-size: 0.82rem; color: #2563EB; text-decoration: none; }
.cart-link:hover { text-decoration: underline; }
.cart-card-body { margin-top: 0.6rem; }
.cart-deptos { font-size: 0.85rem; color: var(--texto-principal); margin: 0 0 0.35rem; }
.cart-timing { font-size: 0.78rem; color: var(--texto-sec); margin: 0; }

.cart-thumb { max-height: 44px; max-width: 70px; border-radius: 4px; object-fit: cover; }

.cart-deptos-check {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.4rem 0.8rem;
  border: 1px solid var(--borde);
  border-radius: 8px;
  padding: 0.75rem;
}
.cart-depto-opt { font-size: 0.85rem; }

.badge-activa  { background: #D1FAE5; color: #065F46; padding: 2px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; margin-left: 0.5rem; }
.badge-inactiva{ background: #F3F4F6; color: #6B7280; padding: 2px 10px; border-radius: 20px; font-size: 0.72rem; margin-left: 0.5rem; }

.modal-sm   { max-width: 560px; }
.acciones     { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.btn-editar   { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.btn-eliminar { background: var(--danger);  color: white; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }

.check-opt  { display: flex; align-items: flex-start; gap: 0.6rem; cursor: pointer; }
.check-opt input[type="checkbox"] { margin-top: 0.2rem; width: 15px; height: 15px; flex-shrink: 0; accent-color: #1A1A1A; }
.check-label        { display: flex; flex-direction: column; gap: 0.1rem; }
.check-label strong { color: var(--texto-principal); font-size: 0.9rem; }
.check-label small  { color: var(--texto-muted); font-size: 0.8rem; }

.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.55rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.55rem 1.2rem; border-radius: 6px; cursor: pointer; }
.form-botones { display: flex; gap: 0.75rem; justify-content: flex-end; }
.msg-error { color: #DC2626; font-size: 0.85rem; margin: 0.5rem 0 0; }
</style>
