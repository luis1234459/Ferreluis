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

    <div class="etiquetas-generar-bar"
      v-if="seleccionados.length > 0">
      <span class="generar-count">
        {{ seleccionados.length }} producto(s) seleccionado(s)
      </span>
      <button class="btn-generar-tipo1"
        @click="abrirModalGenerar('exhibicion')">
        🏷 Etiqueta exhibición
      </button>
      <button class="btn-generar-tipo2"
        @click="abrirModalGenerar('deposito')">
        📦 Etiqueta depósito
      </button>
    </div>

    <!-- Modal configuración -->
    <div v-if="modalGenerar" class="overlay"
      @click.self="modalGenerar = false">
      <div class="modal" style="max-width:420px">
        <div class="modal-header">
          <h2>Generar etiquetas —
            {{ tipoEtiqueta === 'exhibicion' ? 'Exhibición' : 'Depósito' }}
          </h2>
          <button class="btn-cerrar-modal"
            @click="modalGenerar = false">✕</button>
        </div>
        <div style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem">

          <div v-if="tipoEtiqueta === 'exhibicion'" class="field">
            <label>Formato</label>
            <select v-model="formatoExhibicion">
              <option value="auto">Automático (oferta = Amazon)</option>
              <option value="amazon">Forzar estilo Amazon</option>
              <option value="basico">Básico (sin precio anterior)</option>
            </select>
            <small class="txt-muted">
              "Automático" usa formato Amazon solo en
              productos con oferta activa
            </small>
          </div>

          <p style="font-size:0.85rem;color:var(--texto-muted)">
            Se generarán {{ seleccionados.length }} etiquetas
            listas para imprimir.
          </p>
        </div>
        <div class="form-botones">
          <button class="btn-cancelar"
            @click="modalGenerar = false">Cancelar</button>
          <button class="btn-guardar"
            @click="generarEtiquetas">
            Generar
          </button>
        </div>
      </div>
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

    <!-- Vista de impresión -->
    <div v-if="vistaImpresion" class="vista-impresion-overlay">
      <div class="vista-impresion-toolbar">
        <button class="btn-volver-impresion"
          @click="vistaImpresion = false">
          ← Volver
        </button>
        <button class="btn-imprimir-ahora"
          @click="imprimirPagina">
          🖨 Imprimir
        </button>
        <button v-if="tipoEtiqueta === 'exhibicion'"
          class="btn-imprimir-zebra"
          @click="imprimirEnZebra"
          :disabled="imprimiendoZebra">
          🏷️ {{ imprimiendoZebra ? 'Imprimiendo...' : 'Imprimir en Zebra' }}
        </button>
      </div>

      <div class="hoja-etiquetas">
        <div v-for="(e, i) in etiquetasParaImprimir" :key="i"
          :class="['etiqueta-card',
            e.tipo === 'exhibicion' ? 'etiqueta-exhibicion' : 'etiqueta-deposito']">

          <!-- ETIQUETA EXHIBICIÓN -->
          <template v-if="e.tipo === 'exhibicion'">
            <div class="etq-nombre">{{ e.nombre }}</div>

            <template v-if="e.usarAmazon">
              <div class="etq-precio-editable no-print">
                <div class="fila-antes">
                  <label>Antes:</label>
                  <input type="number" step="0.01"
                    v-model.number="e.precio_referencial_usd"
                    class="input-precio-etq" />
                </div>
                <div class="fila-ahora">
                  <label>Ahora:</label>
                  <input type="number" step="0.01"
                    v-model.number="e.precio_oferta_usd"
                    class="input-precio-etq input-precio-ahora-grande" />
                </div>
              </div>
              <div class="etq-precio-amazon print-only">
                <span class="etq-precio-antes">
                  Antes: <s>${{ Number(e.precio_referencial_usd).toFixed(2) }}</s>
                </span>
                <span class="etq-precio-ahora">
                  ${{ Number(e.precio_oferta_usd).toFixed(2) }}
                </span>
              </div>
            </template>
            <template v-else>
              <div class="etq-precio-editable no-print">
                <label>Precio:</label>
                <input type="number" step="0.01"
                  v-model.number="e.precio_referencial_usd"
                  class="input-precio-etq" />
              </div>
              <div class="etq-precio-basico print-only">
                ${{ Number(e.precio_referencial_usd || 0).toFixed(2) }}
              </div>
            </template>

            <div class="etq-codigo">{{ e.codigo || '—' }}</div>
          </template>

          <!-- ETIQUETA DEPÓSITO -->
          <template v-else>
            <div class="etq-codigo-grande">{{ e.codigo || '—' }}</div>
            <div class="etq-nombre-pequeno">{{ e.nombre }}</div>
          </template>

        </div>
      </div>
    </div>

  </div>
</template>

<script>
import axios from 'axios'
import { imprimirEtiqueta } from '@/utils/zebra'
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
      seleccionados:         [],
      modalGenerar:          false,
      tipoEtiqueta:          '',
      formatoExhibicion:     'auto',
      vistaImpresion:        false,
      etiquetasParaImprimir: [],
      imprimiendoZebra:      false,
      tasaBcv:               null,
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
    try {
      const res = await axios.get('/tasa/')
      this.tasaBcv = res.data.tasa
    } catch {}
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
    abrirModalGenerar(tipo) {
      this.tipoEtiqueta = tipo
      this.modalGenerar = true
    },
    generarEtiquetas() {
      const seleccionadosObjs = this.productos.filter(
        p => this.seleccionados.includes(p.id)
      )
      this.etiquetasParaImprimir = seleccionadosObjs.map(p => {
        const tieneOferta = p.oferta_activa
        let usarAmazon = false
        if (this.tipoEtiqueta === 'exhibicion') {
          if (this.formatoExhibicion === 'amazon') usarAmazon = true
          else if (this.formatoExhibicion === 'auto') usarAmazon = tieneOferta
        }
        return {
          ...p,
          tipo: this.tipoEtiqueta,
          usarAmazon,
        }
      })
      this.modalGenerar = false
      this.vistaImpresion = true
    },
    imprimirPagina() { window.print() },
    async imprimirEnZebra() {
      if (!this.tasaBcv) {
        alert('No hay tasa BCV disponible. Verifica la conexión.')
        return
      }
      this.imprimiendoZebra = true
      try {
        for (const e of this.etiquetasParaImprimir) {
          const precioUsd = e.usarAmazon
            ? e.precio_oferta_usd
            : e.precio_referencial_usd
          const precioBs = precioUsd * this.tasaBcv
          await imprimirEtiqueta({
            nombre: e.nombre,
            codigo: e.codigo || '',
            precioUsd,
            precioBs,
          })
        }
        alert('Etiquetas enviadas a la impresora Zebra.')
      } catch (err) {
        alert('Error al imprimir en Zebra: ' + (err.message || err))
      } finally {
        this.imprimiendoZebra = false
      }
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

.etiquetas-generar-bar {
  display: flex; align-items: center; gap: 0.75rem;
  background: #FFFDF0; border: 1px solid #FFCC00;
  border-radius: 8px; padding: 0.6rem 1rem;
  margin-bottom: 0.75rem;
}
.generar-count {
  font-size: 0.85rem; font-weight: 700;
  color: var(--texto-principal);
}
.btn-generar-tipo1, .btn-generar-tipo2 {
  background: #1A1A1A; color: #FFCC00;
  border: none; border-radius: 6px;
  padding: 0.45rem 0.85rem; font-weight: 700;
  font-size: 0.82rem; cursor: pointer;
}
.btn-generar-tipo1:hover, .btn-generar-tipo2:hover { background: #333; }

/* Modal — reutiliza clases globales del proyecto */
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  z-index: 500; display: flex; align-items: center; justify-content: center;
  padding: 1rem;
}
.modal {
  background: #FAFAF7; border-radius: 14px;
  width: 100%; max-width: 580px; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 12px 48px rgba(0,0,0,0.2);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1rem 1.25rem; border-bottom: 1px solid var(--borde);
  background: #FFFFFF; border-radius: 14px 14px 0 0;
}
.modal-header h2 { margin: 0; font-size: 1rem; font-weight: 700; color: #1A1A1A; }
.btn-cerrar-modal {
  background: transparent; border: none; font-size: 1.1rem;
  cursor: pointer; color: var(--texto-muted); padding: 0.2rem 0.45rem;
}
.btn-cerrar-modal:hover { background: #F3F4F6; color: #1A1A1A; }
.field { display: flex; flex-direction: column; gap: 0.4rem; }
.field label { font-size: 0.82rem; font-weight: 600; color: var(--texto-sec); }
.field select {
  padding: 0.5rem 0.7rem; border: 1px solid #CCCCCC;
  border-radius: 7px; background: #FFFFFF; font-size: 0.88rem;
}
.form-botones {
  display: flex; justify-content: flex-end; gap: 0.6rem;
  padding: 1rem 1.25rem; border-top: 1px solid var(--borde);
}
.btn-cancelar {
  padding: 0.55rem 1.1rem; background: transparent;
  border: 1px solid var(--borde); color: var(--texto-sec);
  border-radius: 8px; cursor: pointer; font-size: 0.88rem;
}
.btn-cancelar:hover { border-color: #DC2626; color: #DC2626; }
.btn-guardar {
  padding: 0.55rem 1.2rem; background: #1A1A1A; color: #FFCC00;
  border: none; border-radius: 8px; cursor: pointer;
  font-size: 0.9rem; font-weight: 700;
}
.btn-guardar:hover { background: #333; }

/* ── Vista de impresión ── */
.vista-impresion-overlay {
  position: fixed; inset: 0; z-index: 600;
  background: #F5F5F0; overflow-y: auto;
  padding: 0;
}
.vista-impresion-toolbar {
  display: flex; gap: 0.75rem; align-items: center;
  padding: 0.75rem 1.25rem;
  background: #1A1A1A; position: sticky; top: 0; z-index: 10;
}
.btn-volver-impresion {
  background: transparent; border: 1px solid #FFCC00;
  color: #FFCC00; border-radius: 6px;
  padding: 0.4rem 0.9rem; font-weight: 700;
  font-size: 0.85rem; cursor: pointer;
}
.btn-volver-impresion:hover { background: #FFCC0033; }
.btn-imprimir-ahora {
  background: #FFCC00; color: #1A1A1A; border: none;
  border-radius: 6px; padding: 0.4rem 1rem;
  font-weight: 700; font-size: 0.85rem; cursor: pointer;
}
.btn-imprimir-ahora:hover { background: #e6b800; }
.btn-imprimir-zebra {
  background: #0066CC; color: #FFFFFF; border: none;
  border-radius: 6px; padding: 0.4rem 1rem;
  font-weight: 700; font-size: 0.85rem; cursor: pointer;
}
.btn-imprimir-zebra:hover:not(:disabled) { background: #0052A3; }
.btn-imprimir-zebra:disabled { opacity: 0.6; cursor: not-allowed; }

/* Grid de etiquetas */
.hoja-etiquetas {
  display: flex; flex-wrap: wrap; gap: 0.5rem;
  padding: 1.25rem;
}
.etiqueta-card {
  border: 1px solid #1A1A1A; border-radius: 6px;
  background: #FFFFFF; overflow: hidden;
  page-break-inside: avoid; break-inside: avoid;
  display: flex; flex-direction: column;
}

/* Exhibición: 8 × 5 cm aprox */
.etiqueta-exhibicion {
  width: 220px; min-height: 120px;
  padding: 0.5rem 0.75rem; justify-content: space-between;
}
.etq-nombre {
  font-size: 0.78rem; font-weight: 700;
  color: #1A1A1A; line-height: 1.2;
  margin-bottom: 0.35rem;
}
.etq-precio-basico {
  font-size: 1.6rem; font-weight: 800; color: #1A1A1A;
}
.etq-precio-amazon {
  display: flex; flex-direction: column; gap: 0.2rem;
}
.etq-precio-antes {
  font-size: 0.72rem; color: #888;
}
.etq-precio-ahora {
  font-size: 1.8rem; font-weight: 800; color: #DC2626;
  display: block;
}
.etq-codigo {
  font-size: 0.65rem; color: #888; margin-top: 0.3rem;
  border-top: 1px solid #EEE; padding-top: 0.25rem;
}
.etq-precio-editable {
  display: flex; flex-direction: column;
  gap: 0.3rem;
  padding: 0.3rem 0;
}
.etq-precio-editable .fila-antes,
.etq-precio-editable .fila-ahora {
  display: flex; align-items: center; gap: 0.3rem;
}
.etq-precio-editable label {
  font-size: 0.68rem; color: var(--texto-muted);
  font-weight: 600;
}
.input-precio-etq {
  width: 65px; padding: 0.2rem 0.35rem;
  border: 1px solid #FFCC00; border-radius: 4px;
  font-size: 0.78rem; text-align: right;
}
.input-precio-etq:focus {
  outline: none; border-color: #FF9900;
  background: #FFFDF0;
}
.input-precio-ahora-grande {
  font-size: 1.8rem !important;
  font-weight: 800;
  width: 90px !important;
  padding: 0.3rem 0.4rem !important;
}
.print-only { display: none; }

/* Depósito: 6 × 3.5 cm aprox */
.etiqueta-deposito {
  width: 160px; min-height: 80px;
  padding: 0.5rem 0.6rem; justify-content: center;
  align-items: center; text-align: center; gap: 0.2rem;
}
.etq-codigo-grande {
  font-size: 1.65rem; font-weight: 800;
  color: #1A1A1A; letter-spacing: 0.04em;
}
.etq-nombre-pequeno {
  font-size: 0.975rem; font-weight: 800; color: #555;
  line-height: 1.2; margin-top: 0.2rem;
}

@media print {
  .page-header,
  .etiquetas-filtros,
  .etiquetas-acciones-top,
  .etiquetas-generar-bar,
  .etiquetas-tabla-wrap,
  .vista-impresion-toolbar {
    display: none !important;
  }
  .vista-impresion-overlay {
    position: static !important;
    background: white !important;
    padding: 0 !important;
  }
  .hoja-etiquetas {
    padding: 0 !important;
  }
  .etiqueta-card {
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .no-print { display: none !important; }
  .print-only { display: block !important; }
}
</style>
