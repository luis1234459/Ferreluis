<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Facturas IA</h1>
      </div>

      <div class="contenido-inner">

        <!-- Zona de subida -->
        <div class="upload-area" @click="$refs.fileInput.click()">
          <input
            type="file"
            ref="fileInput"
            accept="image/*,.pdf"
            @change="seleccionarArchivo"
            style="display:none"
          />
          <div v-if="!imagenPreview && !archivoPdf">
            <p class="upload-icon">📄</p>
            <p class="upload-txt">Haz clic para subir la factura</p>
            <p class="upload-hint">JPG, PNG, WebP o PDF</p>
          </div>
          <div v-if="archivoPdf" class="pdf-preview">
            <p class="upload-icon">📑</p>
            <p class="pdf-nombre">{{ archivoPdf }}</p>
            <p class="upload-hint">PDF listo para analizar</p>
          </div>
          <img v-if="imagenPreview" :src="imagenPreview" class="preview" />
        </div>

        <button class="btn-escanear" @click="escanear" :disabled="!archivo || cargando">
          {{ cargando ? 'Analizando con IA...' : 'Escanear con IA' }}
        </button>

        <!-- Resultado -->
        <div v-if="resultado" class="resultado-box">
          <div class="resultado-header">
            <div>
              <h2 class="resultado-titulo">Resultado del escaneo</h2>
              <p class="proveedor-txt">
                Proveedor: <strong>{{ resultado.proveedor || '—' }}</strong>
                &nbsp;·&nbsp; Fecha: <strong>{{ resultado.fecha || '—' }}</strong>
              </p>
            </div>
            <button class="btn-cargar-todos" @click="cargarTodos" :disabled="todosYaCargados">
              {{ todosYaCargados ? '✓ Todos cargados' : 'Cargar todos al inventario' }}
            </button>
          </div>

          <div class="tabla-container tabla-facturas">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Categoría</th>
                  <th>Precio compra</th>
                  <th>Precio venta</th>
                  <th>Margen %</th>
                  <th>Stock</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(p, i) in resultado.productos" :key="i"
                  :class="p.cargado ? 'fila-cargada' : ''">
                  <td>
                    <input class="inp-tabla" v-model="p.nombre" :disabled="p.cargado" />
                  </td>
                  <td>
                    <input class="inp-tabla inp-corto" v-model="p.categoria"
                      placeholder="ej. Herramientas" :disabled="p.cargado" />
                  </td>
                  <td>
                    <input class="inp-tabla inp-numero" type="number" min="0" step="0.01"
                      v-model.number="p.precio_compra" :disabled="p.cargado" />
                  </td>
                  <td>
                    <input class="inp-tabla inp-numero" type="number" min="0" step="0.01"
                      v-model.number="p.precio_venta" :disabled="p.cargado" />
                  </td>
                  <td>
                    <span :class="['margen-badge', claseMargen(p)]">
                      {{ calcMargenPct(p) }}
                    </span>
                  </td>
                  <td>
                    <input class="inp-tabla inp-numero" type="number" min="0" step="1"
                      v-model.number="p.stock" :disabled="p.cargado" />
                  </td>
                  <td>
                    <button class="btn-cargar" @click="cargarProducto(p)" :disabled="p.cargado">
                      {{ p.cargado ? '✓ Cargado' : 'Cargar' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <p class="msg-error" v-if="error">{{ error }}</p>
      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'Facturas',
  data() {
    return {
      usuario:       JSON.parse(localStorage.getItem('usuario') || '{}'),
      archivo:       null,
      imagenPreview: null,
      archivoPdf:    null,
      resultado:     null,
      cargando:      false,
      error:         '',
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
    todosYaCargados() {
      return this.resultado?.productos?.length > 0 &&
        this.resultado.productos.every(p => p.cargado)
    },
  },
  methods: {
    seleccionarArchivo(e) {
      const f = e.target.files[0]
      if (!f) return
      this.archivo       = f
      this.resultado     = null
      this.error         = ''
      if (f.type === 'application/pdf') {
        this.imagenPreview = null
        this.archivoPdf    = f.name
      } else {
        this.archivoPdf    = null
        this.imagenPreview = URL.createObjectURL(f)
      }
    },

    async escanear() {
      this.cargando = true
      this.error    = ''
      try {
        const formData = new FormData()
        formData.append('archivo', this.archivo)
        const res = await axios.post('/facturas/escanear', formData)

        if (res.data.error) {
          this.error = `Error del servidor: ${res.data.error}`
          return
        }

        // Inicializar campos editables en cada producto
        res.data.productos = (res.data.productos || []).map(p => {
          const compra = parseFloat(p.precio_unitario) || 0
          const venta  = parseFloat(p.precio_venta_sugerido) || parseFloat((compra * 1.30).toFixed(2))
          return {
            nombre:         p.nombre       || '',
            descripcion:    p.descripcion  || '',
            categoria:      '',
            precio_compra:  compra,
            precio_venta:   venta,
            stock:          parseInt(p.cantidad) || 0,
            cargado:        false,
          }
        })
        this.resultado = res.data
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al procesar la factura. Intenta de nuevo.'
      } finally {
        this.cargando = false
      }
    },

    calcMargenPct(p) {
      const c = parseFloat(p.precio_compra) || 0
      const v = parseFloat(p.precio_venta)  || 0
      if (c <= 0) return '—'
      if (v <= c) return '0%'
      return ((v - c) / c * 100).toFixed(1) + '%'
    },

    claseMargen(p) {
      const c = parseFloat(p.precio_compra) || 0
      const v = parseFloat(p.precio_venta)  || 0
      if (c <= 0) return ''
      const pct = (v - c) / c * 100
      if (pct >= 25) return 'margen-ok'
      if (pct >= 10) return 'margen-medio'
      return 'margen-bajo'
    },

    _calcMargenDecimal(p) {
      const c = parseFloat(p.precio_compra) || 0
      const v = parseFloat(p.precio_venta)  || 0
      if (c > 0 && v > c) return parseFloat(((v - c) / c).toFixed(4))
      return 0.30
    },

    async cargarProducto(p) {
      try {
        await axios.post('/productos/', {
          nombre:      p.nombre,
          descripcion: p.descripcion || '',
          categoria:   p.categoria   || '',
          costo_usd:   parseFloat(p.precio_compra) || 0,
          margen:      this._calcMargenDecimal(p),
          stock:       parseInt(p.stock) || 0,
          foto_url:    '',
        })
        p.cargado = true
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al cargar el producto')
      }
    },

    async cargarTodos() {
      for (const p of this.resultado.productos) {
        if (!p.cargado) await this.cargarProducto(p)
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
.upload-area {
  border: 2px dashed var(--borde);
  border-radius: 12px; padding: 3rem; text-align: center;
  cursor: pointer; color: var(--texto-muted);
  margin-bottom: 1rem; transition: border-color 0.2s;
  background: #FFFFFF; max-width: 600px;
}
.upload-area:hover { border-color: #FFCC00; }
.upload-icon { font-size: 3rem; margin-bottom: 0.5rem; }
.upload-txt  { color: var(--texto-sec); font-size: 0.95rem; margin: 0; }
.upload-hint { font-size: 0.82rem; color: var(--texto-muted); margin: 0.3rem 0 0; }
.preview     { max-width: 100%; max-height: 300px; border-radius: 8px; }
.pdf-preview { display: flex; flex-direction: column; align-items: center; gap: 0.3rem; }
.pdf-nombre  { color: var(--texto-principal); font-weight: 600; font-size: 0.9rem; margin: 0; word-break: break-all; }

.btn-escanear {
  background: #1A1A1A; color: #FFCC00; border: none;
  padding: 0.75rem 2rem; border-radius: 8px; cursor: pointer;
  font-size: 0.95rem; font-weight: 700; margin-bottom: 2rem;
}
.btn-escanear:disabled { opacity: 0.5; cursor: not-allowed; }

/* Resultado */
.resultado-box    { background: #FFFFFF; border-radius: 14px; padding: 1.5rem; border: 1px solid var(--borde); }
.resultado-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.resultado-titulo { color: var(--texto-principal); font-size: 1.05rem; font-weight: 700; margin: 0 0 0.35rem; }
.proveedor-txt    { color: var(--texto-sec); font-size: 0.88rem; margin: 0; }
.proveedor-txt strong { color: var(--texto-principal); }

/* Tabla editable */
.tabla-facturas table { table-layout: fixed; }
.inp-tabla {
  width: 100%; background: var(--fondo-sidebar);
  border: 1px solid var(--borde); border-radius: 5px;
  padding: 0.3rem 0.5rem; font-size: 0.82rem;
  color: var(--texto-principal); box-sizing: border-box;
}
.inp-tabla:disabled  { opacity: 0.5; cursor: not-allowed; }
.inp-tabla:focus     { outline: none; border-color: #FFCC00; }
.inp-corto  { width: 90px; }
.inp-numero { width: 80px; }

/* Fila cargada */
.fila-cargada td { opacity: 0.55; }

/* Margen badge */
.margen-badge { font-size: 0.78rem; font-weight: 700; padding: 0.15rem 0.45rem; border-radius: 4px; }
.margen-ok    { background: #16A34A1A; color: #16A34A; }
.margen-medio { background: #FFCC0033; color: #996600; }
.margen-bajo  { background: #DC26261A; color: #DC2626; }

/* Botones */
.btn-cargar {
  background: var(--success); color: white; border: none;
  padding: 0.3rem 0.75rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; white-space: nowrap;
}
.btn-cargar:disabled { background: #888; opacity: 0.6; cursor: not-allowed; }

.btn-cargar-todos {
  background: #1A1A1A; color: #FFCC00; border: none;
  padding: 0.55rem 1.2rem; border-radius: 8px; cursor: pointer;
  font-weight: 600; font-size: 0.88rem; white-space: nowrap; flex-shrink: 0;
}
.btn-cargar-todos:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
