<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Catálogo IA</h1>
        <span class="top-badge">Importar productos desde catálogo de proveedor</span>
      </div>

      <div class="contenido-inner">

        <!-- ══ PASO 1 ═══════════════════════════════════════════════════ -->
        <template v-if="paso === 1">
          <div class="aviso-catalogo">
            <strong>📋 Modo Catálogo</strong> — Este módulo es para leer catálogos de productos
            de proveedores y agregarlos al inventario. <em>No es una factura ni una orden de compra.</em>
          </div>

          <!-- Selección de proveedor -->
          <div class="card-seccion">
            <h3 class="seccion-titulo">Proveedor del catálogo</h3>
            <div class="search-wrap" style="max-width:400px">
              <input
                v-model="proveedorBusq"
                class="input-field"
                placeholder="Buscar proveedor..."
                @input="buscarProveedor"
                @focus="provAbierta = true"
                @blur="cerrarProv"
              />
              <ul v-if="provAbierta && provResultados.length" class="dropdown-list">
                <li v-for="p in provResultados" :key="p.id" @mousedown="seleccionarProveedor(p)">
                  <strong>{{ p.nombre }}</strong>
                  <small v-if="p.rif"> · {{ p.rif }}</small>
                </li>
              </ul>
            </div>
            <div v-if="proveedorId" class="prov-ok">✓ {{ proveedorBusq }}</div>
          </div>

          <!-- Upload PDF -->
          <div
            class="dropzone"
            :class="{ 'dz-over': dragging }"
            @dragover.prevent="dragging = true"
            @dragleave.prevent="dragging = false"
            @drop.prevent="onDrop"
            @click="$refs.fileInput.click()"
          >
            <input ref="fileInput" type="file" accept="image/*,.pdf" style="display:none" @change="onFileChange" />
            <div v-if="!archivoSeleccionado" class="dz-empty">
              <span class="dz-icon">📋</span>
              <p>Arrastra el catálogo PDF aquí o <strong>haz clic para seleccionar</strong></p>
              <small>JPEG, PNG, WebP o PDF — primera página del catálogo</small>
            </div>
            <div v-else class="dz-file">
              <img v-if="previewUrl" :src="previewUrl" class="dz-img" />
              <div v-else class="dz-pdf">
                <span class="dz-icon">📑</span>
                <span>{{ archivoSeleccionado.name }}</span>
              </div>
              <button class="btn-quitar" @click.stop="quitarArchivo">✕</button>
            </div>
          </div>

          <div class="paso1-acciones">
            <button
              class="btn-escanear"
              :disabled="!archivoSeleccionado || !proveedorId || escaneando"
              @click="escanear"
            >
              <span v-if="escaneando">⏳ Leyendo catálogo...</span>
              <span v-else>🔍 Leer catálogo con IA</span>
            </button>
          </div>
          <p v-if="errorScan" class="msg-error">{{ errorScan }}</p>
        </template>

        <!-- ══ PASO 2 ═══════════════════════════════════════════════════ -->
        <template v-if="paso === 2">
          <div class="paso2-header">
            <button class="btn-volver" @click="paso = 1">← Volver</button>
            <h2 class="paso2-titulo">
              Catálogo: <strong>{{ proveedorBusq }}</strong>
              <span class="badge-count">{{ lineas.length }} productos detectados</span>
            </h2>
            <span class="aviso-pendientes" v-if="lineasPendientes > 0">
              ⚠ {{ lineasPendientes }} sin configurar
            </span>
          </div>

          <div class="instrucciones-card">
            Para cada producto: confirma el nombre, asigna departamento y categoría, elige si es
            producto <strong>nuevo</strong> o si va a <strong>vincular</strong> a uno existente,
            y revisa el costo. Solo se importarán los productos con todos los campos obligatorios llenos.
          </div>

          <!-- Líneas de producto -->
          <div class="lineas-catalogo">
            <div
              v-for="(linea, idx) in lineas"
              :key="idx"
              :class="['linea-card', estaLista(linea) ? 'linea-lista' : 'linea-pendiente']"
            >
              <!-- Cabecera de la línea -->
              <div class="linea-header">
                <span class="linea-num">{{ idx + 1 }}</span>
                <span class="linea-codigo-ia" v-if="linea.codigo_ia">{{ linea.codigo_ia }}</span>
                <span class="linea-desc-ia">{{ linea.descripcion_ia }}</span>
                <span class="linea-precio-ia">${{ linea.precio_ia != null ? Number(linea.precio_ia).toFixed(2) : '—' }}</span>
                <span :class="['linea-estado', estaLista(linea) ? 'estado-ok' : 'estado-pend']">
                  {{ estaLista(linea) ? '✓ Listo' : 'Configurar' }}
                </span>
              </div>

              <!-- Cuerpo: campos editables -->
              <div class="linea-body">

                <!-- 1. Nombre -->
                <div class="field-cat">
                  <label>Nombre en inventario <span class="req">*</span></label>
                  <input
                    v-model="linea.nombre_final"
                    class="input-field"
                    :placeholder="linea.descripcion_ia"
                  />
                </div>

                <!-- 2. Departamento -->
                <div class="field-cat">
                  <label>Departamento <span class="req">*</span></label>
                  <select v-model="linea.departamento_id" class="input-field" @change="linea.categoria_id = null">
                    <option :value="null">— Seleccionar —</option>
                    <option v-for="d in departamentos" :key="d.id" :value="d.id">{{ d.nombre }}</option>
                  </select>
                </div>

                <!-- 3. Categoría -->
                <div class="field-cat">
                  <label>Categoría <span class="req">*</span></label>
                  <select v-model="linea.categoria_id" class="input-field" :disabled="!linea.departamento_id">
                    <option :value="null">— Seleccionar —</option>
                    <option v-for="c in categoriasDeLinea(linea)" :key="c.id" :value="c.id">{{ c.nombre }}</option>
                  </select>
                </div>

                <!-- 4. Acción: nuevo o vincular -->
                <div class="field-cat">
                  <label>Acción <span class="req">*</span></label>
                  <div class="accion-toggle">
                    <button
                      :class="['btn-accion', linea.accion === 'nuevo' ? 'accion-activa' : '']"
                      @click="linea.accion = 'nuevo'; linea.producto_existente = null; linea._busqProd = ''; linea._busqResultados = []"
                    >✚ Crear nuevo</button>
                    <button
                      :class="['btn-accion', linea.accion === 'vincular' ? 'accion-activa' : '']"
                      @click="linea.accion = 'vincular'"
                    >🔗 Vincular a existente</button>
                  </div>

                  <!-- Búsqueda de producto existente -->
                  <div v-if="linea.accion === 'vincular'" class="busq-existente" style="position:relative;margin-top:0.4rem">
                    <input
                      v-if="!linea.producto_existente"
                      v-model="linea._busqProd"
                      class="input-field input-sm"
                      placeholder="Buscar producto en inventario..."
                      @input="buscarProductoLinea(linea)"
                      @focus="linea._busqAbierta = true"
                      @blur="cerrarBusqLinea(linea)"
                    />
                    <ul v-if="linea._busqAbierta && linea._busqResultados.length" class="dropdown-list dropdown-sm">
                      <li v-for="p in linea._busqResultados" :key="p.id" @mousedown="seleccionarExistente(linea, p)">
                        {{ p.nombre }}
                        <small class="stock-hint"> · Stock: {{ p.stock }}</small>
                      </li>
                    </ul>
                    <div v-if="linea.producto_existente" class="prod-ok-tag">
                      ✓ {{ linea.producto_existente.nombre }}
                      <span class="desvincular" @click="linea.producto_existente = null; linea._busqProd = ''">✕</span>
                    </div>
                  </div>
                </div>

                <!-- 5. Costo -->
                <div class="field-cat">
                  <label>Costo USD</label>
                  <input
                    v-model.number="linea.costo_final"
                    type="number" min="0" step="0.0001"
                    class="input-field"
                    :placeholder="linea.precio_ia != null ? String(linea.precio_ia) : '0'"
                  />
                </div>

              </div>
            </div>
          </div>

          <!-- Botón importar -->
          <div class="importar-footer">
            <p class="importar-resumen">
              <strong>{{ lineasListas.length }}</strong> de {{ lineas.length }} productos listos para importar
            </p>
            <button
              class="btn-importar-cat"
              :disabled="lineasListas.length === 0 || importando"
              @click="importar"
            >
              {{ importando ? 'Importando...' : `↑ Importar ${lineasListas.length} producto${lineasListas.length !== 1 ? 's' : ''}` }}
            </button>
          </div>
          <p v-if="errorImport" class="msg-error">{{ errorImport }}</p>
        </template>

        <!-- ══ PASO 3: Resultado ═══════════════════════════════════════ -->
        <template v-if="paso === 3">
          <div class="resultado-card">
            <div class="resultado-icon">✓</div>
            <h2>Importación completada</h2>
            <p v-if="resultado.creados">🆕 <strong>{{ resultado.creados }}</strong> producto{{ resultado.creados !== 1 ? 's' : '' }} creado{{ resultado.creados !== 1 ? 's' : '' }} en inventario</p>
            <p v-if="resultado.vinculados">🔗 <strong>{{ resultado.vinculados }}</strong> producto{{ resultado.vinculados !== 1 ? 's' : '' }} vinculado{{ resultado.vinculados !== 1 ? 's' : '' }} a existentes</p>
            <p class="resultado-nota">
              Los códigos de proveedor quedan enlazados de forma permanente en el catálogo.
            </p>
            <div v-if="resultado.errores && resultado.errores.length" class="resultado-errores">
              <strong>{{ resultado.errores.length }} error{{ resultado.errores.length !== 1 ? 'es' : '' }}:</strong>
              <ul>
                <li v-for="(e, i) in resultado.errores" :key="i">{{ e.motivo }}</li>
              </ul>
            </div>
            <div class="resultado-acciones">
              <button class="btn-primario" @click="reset">Importar otro catálogo</button>
              <router-link to="/inventario" class="btn-secundario" style="padding:0.5rem 1.1rem;border-radius:6px;text-decoration:none;font-size:0.875rem;">Ver Inventario</router-link>
            </div>
          </div>
        </template>

      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '@/components/AppSidebar.vue'
import axios from 'axios'

export default {
  name: 'CatalogoIA',
  components: { AppSidebar },

  data() {
    return {
      paso: 1,

      // Proveedor
      proveedorBusq:    '',
      proveedorId:      null,
      provResultados:   [],
      provAbierta:      false,

      // Upload
      archivoSeleccionado: null,
      previewUrl:          null,
      dragging:            false,
      escaneando:          false,
      errorScan:           '',

      // Lineas de productos del catálogo
      lineas: [],

      // Catálogos de referencia
      departamentos: [],
      categorias:    [],

      // Importar
      importando:   false,
      errorImport:  '',
      resultado:    { creados: 0, vinculados: 0, errores: [] },
    }
  },

  computed: {
    lineasListas() {
      return this.lineas.filter(l => this.estaLista(l))
    },
    lineasPendientes() {
      return this.lineas.filter(l => !this.estaLista(l)).length
    },
  },

  async mounted() {
    const [deptos, cats] = await Promise.all([
      axios.get('/productos/departamentos'),
      axios.get('/productos/categorias'),
    ])
    this.departamentos = deptos.data
    this.categorias    = cats.data
  },

  methods: {
    // ── Proveedor ──────────────────────────────────────────────────────
    async buscarProveedor() {
      if (this.proveedorBusq.length < 2) { this.provResultados = []; return }
      const r = await axios.get('/facturas/buscar-proveedor', { params: { nombre: this.proveedorBusq } })
      this.provResultados = r.data
    },
    seleccionarProveedor(p) {
      this.proveedorId   = p.id
      this.proveedorBusq = p.nombre
      this.provAbierta   = false
      this.provResultados = []
    },
    cerrarProv() { setTimeout(() => { this.provAbierta = false }, 180) },

    // ── Upload ─────────────────────────────────────────────────────────
    onDrop(e) {
      this.dragging = false
      const f = e.dataTransfer.files[0]
      if (f) this.setArchivo(f)
    },
    onFileChange(e) {
      const f = e.target.files[0]
      if (f) this.setArchivo(f)
    },
    setArchivo(f) {
      this.archivoSeleccionado = f
      this.errorScan = ''
      if (f.type.startsWith('image/')) {
        this.previewUrl = URL.createObjectURL(f)
      } else {
        this.previewUrl = null
      }
    },
    quitarArchivo() {
      this.archivoSeleccionado = null
      this.previewUrl = null
      this.$refs.fileInput.value = ''
    },

    // ── Escanear ───────────────────────────────────────────────────────
    async escanear() {
      this.escaneando = true
      this.errorScan  = ''
      try {
        const fd = new FormData()
        fd.append('archivo', this.archivoSeleccionado)
        const r = await axios.post('/facturas/escanear-catalogo', fd)
        if (r.data.error) {
          this.errorScan = `Error de IA: ${r.data.error}`
          return
        }
        const prods = r.data.productos || []
        if (prods.length === 0) {
          this.errorScan = 'La IA no detectó productos en el catálogo.'
          return
        }
        // Si la IA detectó el proveedor pero el usuario no lo había elegido
        // (no cambiamos el proveedor seleccionado — el usuario lo confirmó)
        this.lineas = prods.map(p => ({
          codigo_ia:         p.codigo     || '',
          descripcion_ia:    p.descripcion || '',
          precio_ia:         p.precio     != null ? Number(p.precio) : null,

          // Campos editables (obligatorios marcados con *)
          nombre_final:      p.descripcion || '',
          departamento_id:   null,
          categoria_id:      null,
          accion:            null,       // 'nuevo' | 'vincular'
          producto_existente: null,

          // Costo pre-relleno con precio del catálogo
          costo_final:       p.precio != null ? Number(p.precio) : 0,

          // Búsqueda producto existente
          _busqProd:         '',
          _busqResultados:   [],
          _busqAbierta:      false,
        }))
        this.paso = 2
      } catch (e) {
        this.errorScan = e?.response?.data?.detail || e?.message || 'Error al escanear'
      } finally {
        this.escaneando = false
      }
    },

    // ── Helpers de línea ───────────────────────────────────────────────
    estaLista(l) {
      if (!l.nombre_final.trim()) return false
      if (!l.departamento_id)     return false
      if (!l.categoria_id)        return false
      if (!l.accion)              return false
      if (l.accion === 'vincular' && !l.producto_existente) return false
      return true
    },
    categoriasDeLinea(l) {
      if (!l.departamento_id) return this.categorias
      return this.categorias.filter(c => c.departamento_id === l.departamento_id)
    },

    // ── Búsqueda producto existente ────────────────────────────────────
    async buscarProductoLinea(linea) {
      if (linea._busqProd.length < 2) { linea._busqResultados = []; return }
      const r = await axios.get('/productos/', { params: { busqueda: linea._busqProd, limit: 10 } })
      linea._busqResultados = r.data.productos || []
    },
    seleccionarExistente(linea, prod) {
      linea.producto_existente = prod
      linea._busqProd          = prod.nombre
      linea._busqAbierta       = false
    },
    cerrarBusqLinea(linea) {
      setTimeout(() => { linea._busqAbierta = false }, 180)
    },

    // ── Importar ───────────────────────────────────────────────────────
    async importar() {
      this.importando  = true
      this.errorImport = ''
      try {
        const items = this.lineasListas.map(l => ({
          codigo_catalogo:       l.codigo_ia || '',
          nombre_final:          l.nombre_final.trim(),
          departamento_id:       l.departamento_id,
          categoria_id:          l.categoria_id,
          accion:                l.accion,
          producto_id_existente: l.producto_existente?.id || null,
          costo_final:           Number(l.costo_final) || 0,
        }))
        const r = await axios.post('/facturas/importar-catalogo', {
          proveedor_id: this.proveedorId,
          items,
        })
        this.resultado = r.data
        this.paso = 3
      } catch (e) {
        this.errorImport = e?.response?.data?.detail || e?.message || 'Error al importar'
      } finally {
        this.importando = false
      }
    },

    reset() {
      this.paso                = 1
      this.archivoSeleccionado = null
      this.previewUrl          = null
      this.lineas              = []
      this.errorScan           = ''
      this.errorImport         = ''
      this.resultado           = { creados: 0, vinculados: 0, errores: [] }
      if (this.$refs.fileInput) this.$refs.fileInput.value = ''
    },
  },
}
</script>

<style scoped>
/* ── Aviso modo catálogo ── */
.aviso-catalogo {
  background: #EFF6FF; border: 1px solid #BFDBFE;
  color: #1D4ED8; border-radius: 8px;
  padding: 0.75rem 1.1rem; margin-bottom: 1.25rem;
  font-size: 0.875rem; line-height: 1.5;
}
.top-badge {
  font-size: 0.78rem; background: #EFF6FF; color: #1D4ED8;
  border: 1px solid #BFDBFE; border-radius: 20px;
  padding: 0.2rem 0.75rem; font-weight: 600;
}

/* ── Card sección ── */
.card-seccion {
  background: #FFFFFF; border: 0.5px solid var(--borde);
  border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;
}
.seccion-titulo {
  font-size: 0.85rem; font-weight: 700; color: var(--texto-sec);
  text-transform: uppercase; letter-spacing: 0.05em;
  margin: 0 0 0.75rem;
}

/* ── Dropzone ── */
.dropzone {
  border: 2px dashed var(--borde); border-radius: 10px;
  padding: 2rem; text-align: center; cursor: pointer;
  background: #FAFAF7; transition: all 0.15s; margin-bottom: 1.25rem;
}
.dropzone:hover, .dz-over { border-color: #FFCC00; background: #FFFDF0; }
.dz-empty { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.dz-icon  { font-size: 2.5rem; }
.dz-empty p { margin: 0; font-size: 0.9rem; color: var(--texto-sec); }
.dz-empty small { color: var(--texto-muted); font-size: 0.8rem; }
.dz-file  { position: relative; display: inline-block; }
.dz-img   { max-height: 200px; border-radius: 6px; }
.dz-pdf   { display: flex; flex-direction: column; align-items: center; gap: 0.4rem; }
.btn-quitar {
  position: absolute; top: -8px; right: -8px;
  background: #DC2626; color: white; border: none;
  border-radius: 50%; width: 22px; height: 22px;
  cursor: pointer; font-size: 0.75rem; line-height: 1;
}

/* ── Paso 1 acciones ── */
.paso1-acciones { display: flex; justify-content: center; margin-bottom: 1rem; }
.btn-escanear {
  background: #1A1A1A; color: #FFCC00; border: none;
  padding: 0.75rem 2rem; border-radius: 8px; cursor: pointer;
  font-size: 0.95rem; font-weight: 700;
}
.btn-escanear:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-escanear:not(:disabled):hover { background: #333; }
.prov-ok {
  margin-top: 0.4rem; font-size: 0.82rem;
  color: #15803D; font-weight: 600;
}

/* ── Paso 2 header ── */
.paso2-header {
  display: flex; align-items: center; gap: 1rem;
  margin-bottom: 1rem; flex-wrap: wrap;
}
.btn-volver {
  background: none; border: 1px solid var(--borde);
  color: var(--texto-sec); padding: 0.4rem 0.9rem;
  border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}
.btn-volver:hover { background: var(--borde-suave); }
.paso2-titulo { margin: 0; font-size: 1.1rem; flex: 1; }
.badge-count {
  font-size: 0.78rem; background: var(--amarillo);
  color: #1A1A1A; padding: 0.15rem 0.55rem;
  border-radius: 10px; margin-left: 0.5rem; font-weight: 700;
}
.aviso-pendientes { color: #996600; font-size: 0.85rem; font-weight: 600; }

/* ── Instrucciones ── */
.instrucciones-card {
  background: #F8F9FA; border: 1px solid var(--borde);
  border-radius: 8px; padding: 0.65rem 1rem;
  font-size: 0.83rem; color: var(--texto-sec);
  margin-bottom: 1rem; line-height: 1.5;
}

/* ── Líneas de catálogo ── */
.lineas-catalogo { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1.5rem; }

.linea-card {
  background: #FFFFFF; border: 1px solid var(--borde);
  border-radius: 10px; overflow: hidden;
}
.linea-lista    { border-left: 4px solid #16A34A; }
.linea-pendiente{ border-left: 4px solid #D1D5DB; }

.linea-header {
  display: flex; align-items: center; gap: 0.6rem;
  padding: 0.5rem 1rem;
  background: #FAFAF7; border-bottom: 1px solid var(--borde-suave);
  flex-wrap: wrap;
}
.linea-num {
  width: 1.5rem; text-align: center;
  font-size: 0.72rem; color: var(--texto-muted); font-weight: 700;
}
.linea-codigo-ia {
  font-size: 0.75rem; font-weight: 700; color: #5B21B6;
  background: #EDE9FE; padding: 0.1rem 0.45rem; border-radius: 3px;
}
.linea-desc-ia {
  flex: 1; font-size: 0.85rem; color: var(--texto-sec);
  font-style: italic; font-weight: 500;
}
.linea-precio-ia {
  font-size: 0.82rem; color: #15803D; font-weight: 700;
}
.linea-estado { font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 10px; }
.estado-ok   { background: #DCFCE7; color: #15803D; }
.estado-pend { background: #F3F4F6; color: #6B7280; }

.linea-body {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 2fr 1fr;
  gap: 0.75rem; padding: 0.85rem 1rem;
}
@media (max-width: 1200px) {
  .linea-body { grid-template-columns: 1fr 1fr 1fr; }
}
@media (max-width: 768px) {
  .linea-body { grid-template-columns: 1fr; }
}

.field-cat { display: flex; flex-direction: column; gap: 0.25rem; }
.field-cat label { font-size: 0.75rem; font-weight: 700; color: var(--texto-sec); }
.req { color: #DC2626; }

/* ── Acción toggle ── */
.accion-toggle { display: flex; gap: 0.4rem; }
.btn-accion {
  flex: 1; padding: 0.3rem 0.5rem; border-radius: 6px;
  border: 1px solid var(--borde); background: #FFFFFF;
  color: var(--texto-sec); cursor: pointer; font-size: 0.78rem;
  transition: all 0.15s;
}
.btn-accion:hover { border-color: var(--amarillo); }
.accion-activa { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; font-weight: 700; }

/* ── Búsqueda existente ── */
.busq-existente { position: relative; }
.prod-ok-tag {
  font-size: 0.82rem; color: #15803D; font-weight: 600;
  display: flex; align-items: center; gap: 0.3rem;
  background: #F0FDF4; padding: 0.25rem 0.5rem; border-radius: 5px;
}
.desvincular { cursor: pointer; color: #DC2626; font-size: 0.78rem; padding: 0 0.2rem; }
.desvincular:hover { background: #FEE2E2; border-radius: 3px; }

/* ── Footer importar ── */
.importar-footer {
  display: flex; align-items: center; justify-content: space-between;
  background: #FFFFFF; border: 1px solid var(--borde);
  border-radius: 10px; padding: 1rem 1.5rem;
  position: sticky; bottom: 1rem;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.08);
}
.importar-resumen { margin: 0; font-size: 0.875rem; color: var(--texto-sec); }
.btn-importar-cat {
  background: #16A34A; color: white; border: none;
  padding: 0.65rem 1.5rem; border-radius: 8px;
  cursor: pointer; font-size: 0.95rem; font-weight: 700;
}
.btn-importar-cat:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-importar-cat:not(:disabled):hover { background: #15803D; }

/* ── Resultado ── */
.resultado-card {
  background: #FFFFFF; border: 1px solid var(--borde);
  border-radius: 12px; padding: 2rem; text-align: center;
  max-width: 480px; margin: 2rem auto;
}
.resultado-icon { font-size: 3rem; margin-bottom: 0.5rem; color: #16A34A; }
.resultado-card h2 { margin: 0 0 1.25rem; color: var(--texto-principal); }
.resultado-card p  { margin: 0.35rem 0; font-size: 0.9rem; color: var(--texto-sec); }
.resultado-nota {
  font-size: 0.8rem; color: var(--texto-muted);
  background: #F8F9FA; border-radius: 6px;
  padding: 0.5rem 0.75rem; margin-top: 0.75rem !important;
}
.resultado-errores {
  text-align: left; background: #FEF2F2; border-radius: 6px;
  padding: 0.75rem 1rem; margin-top: 0.75rem;
  font-size: 0.82rem; color: #DC2626;
}
.resultado-errores ul { margin: 0.25rem 0 0; padding-left: 1.2rem; }
.resultado-acciones {
  display: flex; gap: 0.75rem; justify-content: center; margin-top: 1.5rem;
}

/* ── Dropdowns ── */
.search-wrap { position: relative; }
.dropdown-list {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 999;
  background: #FFFFFF; border: 1px solid var(--borde);
  border-radius: 6px; max-height: 200px; overflow-y: auto;
  list-style: none; padding: 0; margin: 2px 0 0;
  box-shadow: 0 6px 20px rgba(0,0,0,0.12);
}
.dropdown-list li {
  padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.875rem;
  border-bottom: 1px solid var(--borde);
}
.dropdown-list li:last-child { border-bottom: none; }
.dropdown-list li:hover { background: #FFFDF0; }
.dropdown-sm li { font-size: 0.8rem; padding: 0.3rem 0.55rem; }
.stock-hint { color: var(--texto-muted); font-size: 0.75rem; }
.input-sm { padding: 0.3rem 0.5rem; font-size: 0.82rem; }
.input-field { width: 100%; box-sizing: border-box; }
</style>
