<template>
  <div class="repo-tabla-wrap">
    <!-- Selector de departamento — obligatorio, nunca se navega el catálogo completo -->
    <div class="repo-selector-depto">
      <div class="field">
        <label>Departamento *</label>
        <select v-model="deptoSeleccionVModel" :class="{ 'select-resaltado': !deptoActivoId }">
          <option :value="null">— Elegí un departamento —</option>
          <option v-for="d in deptos" :key="d.id" :value="d.id">
            {{ d.nombre }} ({{ d.total_productos }} productos{{ d.total_productos ? ' · ' + d.fichas_cargadas + '/' + d.total_productos + ' · ' + pctFichas(d) + '%' : '' }} · {{ formatMoney(d.ingreso_90d) }})
          </option>
        </select>
      </div>
      <div class="field" v-if="categoriasDelDeptoActivo.length">
        <label>Categoría</label>
        <select v-model="categoriaSeleccionVModel">
          <option :value="null">Todas las categorías</option>
          <option v-for="c in categoriasDelDeptoActivo" :key="c.id" :value="c.id">{{ c.nombre }}</option>
        </select>
      </div>
      <button class="btn-panel-proveedores" @click="panelAbierto = !panelAbierto">
        {{ panelAbierto ? '✕ Ocultar proveedores' : '📋 Ver proveedores' }}
      </button>
      <button class="btn-agregar-planificado" :disabled="!deptoActivoId"
        :title="!deptoActivoId ? 'Elegí un departamento primero' : 'Crear un producto planificado (sin existencia todavía)'"
        @click="abrirModalNuevoProducto">
        + Agregar producto
      </button>
    </div>

    <!-- Estado vacío: sin departamento elegido -->
    <div v-if="!deptoActivoId" class="repo-vacio-inicial">
      <div class="repo-vacio-icono">📦</div>
      <h2>Elegí un departamento para empezar</h2>
      <p>La tabla de reposición se carga por departamento — nunca se muestra el catálogo completo de una sola vez.</p>
    </div>

    <template v-else>
      <div class="repo-tabla-layout">
        <div class="repo-tabla-main">
          <!-- Filtros secundarios -->
          <div class="repo-filtros">
            <input v-model="busqueda" placeholder="Buscar por código o descripción..." class="repo-buscador" />
            <select v-model="filtroEstado">
              <option value="todos">Todos</option>
              <option value="con_ficha">Con ficha cargada</option>
              <option value="sin_ficha">Sin ficha cargada</option>
              <option value="rojo">🔴 Semáforo rojo</option>
              <option value="amarillo">🟡 Semáforo amarillo</option>
              <option value="gris">⚪ Sin stock (proveedor)</option>
            </select>
            <select v-model="orden">
              <option value="ventas_desc">Ordenar: ventas 90d ↓</option>
              <option value="codigo">Ordenar: código</option>
              <option value="descripcion">Ordenar: descripción</option>
              <option value="existencia">Ordenar: existencia</option>
            </select>
            <span class="repo-contador">{{ productosFiltrados.length }} de {{ productos.length }}</span>
          </div>

          <!-- Barra de guardado -->
          <div class="repo-barra-guardado">
            <button class="btn-guardar-lote" :disabled="filasModificadas.size === 0 || guardando" @click="guardarCambios">
              {{ guardando ? 'Guardando...' : '✓ Guardar cambios' }}
              <span v-if="filasModificadas.size > 0 && !guardando" class="badge-pendientes">{{ filasModificadas.size }}</span>
            </button>
            <button class="btn-descartar-lote" :disabled="filasModificadas.size === 0 || guardando" @click="descartarCambios">
              ✕ Descartar cambios
            </button>
            <button class="btn-autonumerar" :disabled="seleccionados.size === 0" @click="abrirAutonumerar">
              # Autonumerar selección
              <span v-if="seleccionados.size > 0" class="badge-pendientes">{{ seleccionados.size }}</span>
            </button>
            <span v-if="errorGuardado" class="repo-error-guardado">{{ errorGuardado }}</span>
          </div>

          <div v-if="cargandoTabla" class="repo-cargando">Cargando productos del departamento...</div>

          <div v-else class="repo-tabla-scroll">
            <table class="repo-tabla">
              <thead>
                <tr>
                  <th class="repo-celda-check">
                    <input type="checkbox" :checked="todosVisiblesSeleccionados" @change="toggleSeleccionarTodos"
                      title="Seleccionar todos los visibles" />
                  </th>
                  <th>Código</th>
                  <th>Descripción</th>
                  <th title="Existencia en stock">Exist.</th>
                  <th title="Proveedor principal">P1</th>
                  <th title="Costo de compra al proveedor principal en USD">Costo</th>
                  <th title="Crédito (días) — placeholder es el default del proveedor">Cred</th>
                  <th title="Lead time (días) — placeholder es el default del proveedor">LT</th>
                  <th title="Mínimo de compra">Min</th>
                  <th title="Proveedor alternativo">P2</th>
                  <th title="Crédito (días) del alternativo">Cred2</th>
                  <th title="Lead time (días) del alternativo">LT2</th>
                  <th title="Mínimo de compra del alternativo">Min2</th>
                  <th title="Modo de reposición">Modo</th>
                  <th title="Stock Mínimo Objetivo">SMin</th>
                  <th title="Stock Máximo Objetivo">SMax</th>
                  <th title="Unidades en exhibición (se excluyen del disponible)">Exh</th>
                  <th title="Colchón de días extra sobre el lead time">Col</th>
                  <th title="Semáforo de reposición">🚦</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="fila in productosFiltrados" :key="fila.producto_id"
                    :data-producto-id="fila.producto_id"
                    :class="{ 'repo-fila-modificada': filasModificadas.has(fila.producto_id) }">
                  <td class="repo-celda-check">
                    <input type="checkbox" :checked="seleccionados.has(fila.producto_id)"
                      @change="toggleSeleccion(fila.producto_id)" />
                  </td>
                  <td class="repo-celda-codigo" :class="{ 'repo-celda-planificada': esPlanificado(fila), 'repo-celda-codigo-error': erroresCodigoPorFila[fila.producto_id] }"
                      :title="esPlanificado(fila) ? 'Producto planificado, sin existencia aún' : ''">
                    <span v-if="esPlanificado(fila)" class="repo-icono-planificado">🧭</span>
                    <input class="repo-input-codigo"
                      v-model="borrador[fila.producto_id].codigo"
                      @input="marcarModificado(fila.producto_id); erroresCodigoPorFila[fila.producto_id] && delete erroresCodigoPorFila[fila.producto_id]"
                      @keydown.enter.prevent="bajarFila($event)"
                      :title="erroresCodigoPorFila[fila.producto_id] || ''"
                      placeholder="—" />
                  </td>
                  <td class="repo-celda-desc" :title="fila.producto_descripcion">{{ fila.producto_descripcion }}</td>
                  <td class="repo-celda-num">{{ fila.existencia }}</td>

                  <!-- P1 -->
                  <td class="repo-celda-autocomplete">
                    <input class="repo-input-prov"
                      :value="textoProveedor(fila.producto_id, 'p1')"
                      @input="onInputAutocomplete(fila.producto_id, 'p1', $event)"
                      @focus="abrirAutocomplete(fila.producto_id, 'p1')"
                      @keydown.enter.prevent="onEnterAutocomplete(fila.producto_id, 'p1', $event)"
                      @blur="onBlurAutocomplete(fila.producto_id, 'p1')"
                      placeholder="código o nombre" />
                    <ul v-if="autocompleteAbierto && autocompleteAbierto.productoId === fila.producto_id && autocompleteAbierto.slot === 'p1'"
                        class="repo-autocomplete-lista">
                      <li v-for="p in sugerenciasProveedor" :key="p.id" @mousedown.prevent="seleccionarProveedor(fila.producto_id, 'p1', p)">
                        {{ p.codigo || '???' }} — {{ p.nombre }}
                      </li>
                      <li v-if="sugerenciasProveedor.length === 0" class="repo-autocomplete-vacio">Sin coincidencias</li>
                    </ul>
                  </td>
                  <td><input class="repo-input-sm" type="number" min="0" step="0.01"
                    v-model.number="borrador[fila.producto_id].p1.precio_actual_usd"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>
                  <td><input class="repo-input-sm" type="number" min="0"
                    v-model.number="borrador[fila.producto_id].p1.credito_dias"
                    :placeholder="String(defaultCreditoProveedor(borrador[fila.producto_id].p1.proveedor_id))"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>
                  <td><input class="repo-input-sm" type="number" min="0"
                    v-model.number="borrador[fila.producto_id].p1.lead_time_dias"
                    :placeholder="String(defaultLeadTimeProveedor(borrador[fila.producto_id].p1.proveedor_id))"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>
                  <td><input class="repo-input-sm" type="number" min="0"
                    v-model.number="borrador[fila.producto_id].p1.minimo_compra"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>

                  <!-- P2 -->
                  <td class="repo-celda-autocomplete">
                    <input class="repo-input-prov"
                      :value="textoProveedor(fila.producto_id, 'p2')"
                      @input="onInputAutocomplete(fila.producto_id, 'p2', $event)"
                      @focus="abrirAutocomplete(fila.producto_id, 'p2')"
                      @keydown.enter.prevent="onEnterAutocomplete(fila.producto_id, 'p2', $event)"
                      @blur="onBlurAutocomplete(fila.producto_id, 'p2')"
                      placeholder="código o nombre" />
                    <ul v-if="autocompleteAbierto && autocompleteAbierto.productoId === fila.producto_id && autocompleteAbierto.slot === 'p2'"
                        class="repo-autocomplete-lista">
                      <li v-for="p in sugerenciasProveedor" :key="p.id" @mousedown.prevent="seleccionarProveedor(fila.producto_id, 'p2', p)">
                        {{ p.codigo || '???' }} — {{ p.nombre }}
                      </li>
                      <li v-if="sugerenciasProveedor.length === 0" class="repo-autocomplete-vacio">Sin coincidencias</li>
                    </ul>
                  </td>
                  <td><input class="repo-input-sm" type="number" min="0"
                    v-model.number="borrador[fila.producto_id].p2.credito_dias"
                    :placeholder="String(defaultCreditoProveedor(borrador[fila.producto_id].p2.proveedor_id))"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>
                  <td><input class="repo-input-sm" type="number" min="0"
                    v-model.number="borrador[fila.producto_id].p2.lead_time_dias"
                    :placeholder="String(defaultLeadTimeProveedor(borrador[fila.producto_id].p2.proveedor_id))"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>
                  <td><input class="repo-input-sm" type="number" min="0"
                    v-model.number="borrador[fila.producto_id].p2.minimo_compra"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>

                  <!-- Parámetros -->
                  <td>
                    <select class="repo-input-modo" v-model="borrador[fila.producto_id].modo_reposicion"
                      :title="modoNombreCompleto(borrador[fila.producto_id].modo_reposicion)"
                      @change="marcarFichaModificada(fila.producto_id)">
                      <option value="stock_continuo">SCO</option>
                      <option value="pedido_bajo_demanda">PBD</option>
                      <option value="lote_grande">LG</option>
                      <option value="stock_estrategico_descuento">SED</option>
                    </select>
                  </td>
                  <td><input class="repo-input-sm" type="number" min="0"
                    v-model.number="borrador[fila.producto_id].stock_min_objetivo"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>
                  <td><input class="repo-input-sm" type="number" min="0"
                    v-model.number="borrador[fila.producto_id].stock_max_objetivo"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>
                  <td><input class="repo-input-sm" type="number" min="0"
                    v-model.number="borrador[fila.producto_id].unidades_exhibicion"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>
                  <td><input class="repo-input-sm" type="number" min="0"
                    v-model.number="borrador[fila.producto_id].colchon_dias"
                    @input="marcarFichaModificada(fila.producto_id)" @keydown.enter.prevent="bajarFila($event)" /></td>

                  <!-- Semáforo -->
                  <td class="repo-celda-semaforo">
                    <span v-if="fila.ficha_cargada" class="repo-punto" :class="'repo-punto--' + fila.estado_semaforo"
                          :title="semaforoTooltip(fila)">
                      {{ semaforoIcono(fila.estado_semaforo) }}
                    </span>
                    <span v-else class="repo-punto repo-punto--nulo" title="Sin ficha cargada todavía">—</span>
                  </td>
                </tr>
                <tr v-if="productosFiltrados.length === 0">
                  <td colspan="19" class="repo-sin-datos">Sin productos que coincidan con los filtros</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Panel lateral de referencia -->
        <div v-if="panelAbierto" class="repo-panel-lateral">
          <h3>Proveedores registrados</h3>
          <div class="repo-panel-lista">
            <div v-for="p in proveedoresOrdenados" :key="p.id" class="repo-panel-item">
              <strong>{{ p.codigo || '— sin código —' }}</strong> {{ p.nombre }}
              <div class="repo-panel-sub">
                {{ p.dias_credito || 0 }}d crédito · {{ p.lead_time_dias_default || 0 }}d lead time
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Modal: agregar producto planificado -->
    <div class="overlay" v-if="modalNuevoProducto" @click.self="cerrarModalNuevoProducto">
      <div class="modal modal-nuevo-planificado">
        <div class="modal-header">
          <h2>Agregar producto planificado</h2>
          <button class="btn-cerrar-modal" @click="cerrarModalNuevoProducto">✕</button>
        </div>
        <p class="repo-modal-hint">
          Para planificar el catálogo ideal del departamento: creá el producto con existencia 0
          y cargá su ficha de reposición en la misma tabla, sin cambiar de pantalla.
        </p>
        <div class="grid-form">
          <div class="field">
            <label>Código</label>
            <input v-model="formNuevoProducto.codigo" placeholder="Opcional — se autogenera si lo dejás vacío" />
          </div>
          <div class="field field-wide">
            <label>Descripción *</label>
            <input v-model="formNuevoProducto.descripcion" placeholder="Nombre del producto" />
          </div>
          <div class="field">
            <label>Departamento</label>
            <select v-model="formNuevoProducto.departamento_id" @change="formNuevoProducto.categoria_id = null">
              <option :value="null">— Sin departamento —</option>
              <option v-for="d in deptos" :key="d.id" :value="d.id">{{ d.nombre }}</option>
            </select>
          </div>
          <div class="field">
            <label>Categoría</label>
            <select v-model="formNuevoProducto.categoria_id">
              <option :value="null">— Sin categoría —</option>
              <option v-for="c in categoriasParaNuevoProducto" :key="c.id" :value="c.id">{{ c.nombre }}</option>
            </select>
          </div>
          <div class="field">
            <label>Costo USD</label>
            <input v-model.number="formNuevoProducto.costo_usd" type="number" min="0" step="0.01" placeholder="0.00" />
          </div>
          <div class="field">
            <label>Precio de venta USD</label>
            <input v-model.number="formNuevoProducto.precio_venta_usd" type="number" min="0" step="0.01" placeholder="0.00" />
          </div>
          <div class="field">
            <label>Existencia inicial</label>
            <input v-model.number="formNuevoProducto.stock" type="number" min="0" placeholder="0" />
          </div>
        </div>
        <p class="msg-error" v-if="errorNuevoProducto">{{ errorNuevoProducto }}</p>
        <div class="form-botones">
          <button class="btn-cancelar" @click="cerrarModalNuevoProducto">Cancelar</button>
          <button class="btn-guardar" :disabled="guardandoNuevoProducto" @click="crearProductoPlanificado">
            {{ guardandoNuevoProducto ? 'Creando...' : 'Crear producto' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: autonumerar selección -->
    <div class="overlay" v-if="modalAutonumerar" @click.self="cerrarAutonumerar">
      <div class="modal modal-autonumerar">
        <div class="modal-header">
          <h2>Autonumerar selección ({{ seleccionados.size }} producto{{ seleccionados.size !== 1 ? 's' : '' }})</h2>
          <button class="btn-cerrar-modal" @click="cerrarAutonumerar">✕</button>
        </div>
        <div class="grid-form">
          <div class="field">
            <label>Prefijo (2 a 6 caracteres)</label>
            <input v-model="autonumerarForm.prefijo" maxlength="6" placeholder="Ej: LPCO" />
          </div>
          <div class="field">
            <label>Número inicial</label>
            <input v-model.number="autonumerarForm.numeroInicial" type="number" min="1" />
          </div>
          <div class="field">
            <label>Padding de ceros</label>
            <input v-model.number="autonumerarForm.padding" type="number" min="1" max="6" />
          </div>
        </div>
        <p v-if="!prefijoValidoAutonumerar" class="msg-error">El prefijo debe tener entre 2 y 6 caracteres.</p>
        <div class="repo-preview-autonumerar" v-else>
          <strong>Preview:</strong>
          <span v-for="c in previewAutonumerar" :key="c" class="repo-preview-codigo">{{ c }}</span>
          <span v-if="seleccionados.size > 3">… (+{{ seleccionados.size - 3 }} más)</span>
        </div>
        <div class="form-botones">
          <button class="btn-cancelar" @click="cerrarAutonumerar">Cancelar</button>
          <button class="btn-guardar" :disabled="!prefijoValidoAutonumerar" @click="confirmarAutonumerar">
            Asignar {{ seleccionados.size }} código{{ seleccionados.size !== 1 ? 's' : '' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

const MODOS_NOMBRES = {
  stock_continuo:               'Stock continuo',
  pedido_bajo_demanda:          'Pedido bajo demanda',
  lote_grande:                  'Lote grande',
  stock_estrategico_descuento:  'Stock estratégico (descuento)',
}

const LS_KEY_DEPTO = 'reposicion_depto_activo'

export default {
  name: 'ReposicionTabla',
  data() {
    return {
      deptos:           [],
      deptoActivoId:    null,
      categoriaActivaId: null,
      cargandoTabla:    false,
      productos:        [],
      borrador:         {},
      filasModificadas: new Set(),
      filasFichaTocada: new Set(),   // subconjunto de filasModificadas: cambio de campo de ficha (no solo codigo)
      erroresCodigoPorFila: {},      // producto_id -> mensaje, cuando el UNIQUE de codigo choca al guardar
      guardando:        false,
      errorGuardado:    '',
      seleccionados:    new Set(),
      modalAutonumerar: false,
      autonumerarForm:  { prefijo: '', numeroInicial: 1, padding: 3 },
      busqueda:         '',
      filtroEstado:     'todos',
      orden:            'ventas_desc',
      proveedores:      [],
      panelAbierto:     false,
      autocompleteAbierto: null,   // { productoId, slot }
      autocompleteTextoLibre: {},  // texto crudo mientras el usuario tipea, key `${id}_${slot}`
      modalNuevoProducto:     false,
      guardandoNuevoProducto: false,
      errorNuevoProducto:     '',
      formNuevoProducto: { codigo: '', descripcion: '', departamento_id: null, categoria_id: null, costo_usd: 0, precio_venta_usd: 0, stock: 0 },
    }
  },
  computed: {
    deptoSeleccionVModel: {
      get() { return this.deptoActivoId },
      set(id) { this.elegirDepto(id) },
    },
    categoriaSeleccionVModel: {
      get() { return this.categoriaActivaId },
      set(id) { this.categoriaActivaId = id; this.cargarTabla() },
    },
    deptoActivoObj() {
      return this.deptos.find(d => d.id === this.deptoActivoId) || null
    },
    categoriasDelDeptoActivo() {
      return this.deptoActivoObj?.categorias || []
    },
    todosVisiblesSeleccionados() {
      return this.productosFiltrados.length > 0
        && this.productosFiltrados.every(f => this.seleccionados.has(f.producto_id))
    },
    prefijoValidoAutonumerar() {
      const p = (this.autonumerarForm.prefijo || '').trim()
      return p.length >= 2 && p.length <= 6
    },
    previewAutonumerar() {
      if (!this.prefijoValidoAutonumerar) return []
      const prefijo = this.autonumerarForm.prefijo.trim().toUpperCase()
      const padding = Math.max(1, Number(this.autonumerarForm.padding) || 3)
      const inicio  = Math.max(1, Number(this.autonumerarForm.numeroInicial) || 1)
      const cantidad = Math.min(3, this.seleccionados.size)
      const codigos = []
      for (let i = 0; i < cantidad; i++) {
        codigos.push(`${prefijo}-${String(inicio + i).padStart(padding, '0')}`)
      }
      return codigos
    },
    proveedoresOrdenados() {
      return [...this.proveedores].sort((a, b) => a.nombre.localeCompare(b.nombre))
    },
    categoriasParaNuevoProducto() {
      const d = this.deptos.find(x => x.id === this.formNuevoProducto.departamento_id)
      return d?.categorias || []
    },
    sugerenciasProveedor() {
      if (!this.autocompleteAbierto) return []
      const key = `${this.autocompleteAbierto.productoId}_${this.autocompleteAbierto.slot}`
      const texto = (this.autocompleteTextoLibre[key] || '').trim().toLowerCase()
      if (!texto) return this.proveedoresOrdenados.slice(0, 8)
      return this.proveedoresOrdenados.filter(p =>
        (p.codigo || '').toLowerCase().includes(texto) || p.nombre.toLowerCase().includes(texto)
      ).slice(0, 8)
    },
    productosFiltrados() {
      let lista = this.productos.filter(fila => {
        if (this.busqueda) {
          const t = this.busqueda.toLowerCase()
          const enCodigo = (fila.producto_codigo || '').toLowerCase().includes(t)
          const enDesc   = (fila.producto_descripcion || '').toLowerCase().includes(t)
          if (!enCodigo && !enDesc) return false
        }
        if (this.filtroEstado === 'con_ficha') return fila.ficha_cargada
        if (this.filtroEstado === 'sin_ficha') return !fila.ficha_cargada
        if (['rojo', 'amarillo', 'gris'].includes(this.filtroEstado)) {
          return fila.ficha_cargada && fila.estado_semaforo === this.filtroEstado
        }
        return true
      })
      const cmp = {
        ventas_desc: (a, b) => (b.venta_diaria_90d || 0) - (a.venta_diaria_90d || 0),
        codigo:      (a, b) => (a.producto_codigo || '').localeCompare(b.producto_codigo || ''),
        descripcion: (a, b) => (a.producto_descripcion || '').localeCompare(b.producto_descripcion || ''),
        existencia:  (a, b) => (b.existencia || 0) - (a.existencia || 0),
      }[this.orden]
      return [...lista].sort(cmp)
    },
  },
  async mounted() {
    await Promise.all([this.cargarDeptos(), this.cargarProveedoresGlobal()])
    const guardado = Number(localStorage.getItem(LS_KEY_DEPTO))
    if (guardado && this.deptos.some(d => d.id === guardado)) {
      this.deptoActivoId = guardado
      await this.cargarTabla()
    }
  },
  methods: {
    async cargarDeptos() {
      const res = await axios.get('/productos/reposicion/departamentos-resumen')
      this.deptos = res.data
    },
    async cargarProveedoresGlobal() {
      const res = await axios.get('/compras/proveedores/')
      this.proveedores = res.data
    },
    pctFichas(d) {
      if (!d.total_productos) return 0
      return Math.round((d.fichas_cargadas / d.total_productos) * 100)
    },
    formatMoney(n) {
      return '$' + Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })
    },
    elegirDepto(id) {
      if (this.filasModificadas.size > 0) {
        const ok = confirm(`Tenés ${this.filasModificadas.size} producto(s) sin guardar. Si cambiás de departamento, se pierden. ¿Continuar?`)
        if (!ok) return
      }
      this.deptoActivoId     = id
      this.categoriaActivaId = null
      this.filasModificadas  = new Set()
      this.filasFichaTocada  = new Set()
      this.erroresCodigoPorFila = {}
      this.seleccionados     = new Set()
      this.errorGuardado     = ''
      if (id) localStorage.setItem(LS_KEY_DEPTO, String(id))
      else localStorage.removeItem(LS_KEY_DEPTO)
      this.cargarTabla()
    },
    async cargarTabla() {
      if (!this.deptoActivoId) { this.productos = []; this.borrador = {}; return }
      this.cargandoTabla = true
      try {
        const params = { departamento_id: this.deptoActivoId }
        if (this.categoriaActivaId) params.categoria_id = this.categoriaActivaId
        const res = await axios.get('/productos/reposicion/tabla', { params })
        this.productos = res.data.productos
        this.reconstruirBorrador()
        this.filasModificadas = new Set()
        this.filasFichaTocada = new Set()
        this.erroresCodigoPorFila = {}
        this.seleccionados = new Set()
      } finally {
        this.cargandoTabla = false
      }
    },
    reconstruirBorrador() {
      const nuevo = {}
      for (const fila of this.productos) {
        nuevo[fila.producto_id] = this.construirFilaBorrador(fila)
      }
      this.borrador = nuevo
    },
    construirFilaBorrador(fila) {
      const proveedoresPorPrioridad = {}
      for (const pp of (fila.proveedores || [])) {
        proveedoresPorPrioridad[pp.prioridad] = pp
      }
      const slot = (pp) => ({
        proveedor_id:         pp?.proveedor_id ?? null,
        precio_actual_usd:    pp?.precio_actual_usd ?? null,
        credito_dias:         pp?.credito_dias ?? null,
        lead_time_dias:       pp?.lead_time_dias ?? null,
        minimo_compra:        pp?.minimo_compra ?? null,
        // no editable en esta tabla, se preserva tal cual para no perderlo al guardar
        sin_stock_declarado:  pp?.sin_stock_declarado ?? false,
        sin_stock_fecha:      pp?.sin_stock_fecha ?? null,
      })
      return {
        codigo:              fila.producto_codigo     ?? '',
        modo_reposicion:     fila.modo_reposicion     ?? 'stock_continuo',
        stock_min_objetivo:  fila.stock_min_objetivo  ?? 0,
        stock_max_objetivo:  fila.stock_max_objetivo  ?? 0,
        unidades_exhibicion: fila.unidades_exhibicion ?? 0,
        colchon_dias:        fila.colchon_dias        ?? 3,
        activo:              fila.activo              ?? true,
        p1: slot(proveedoresPorPrioridad[1]),
        p2: slot(proveedoresPorPrioridad[2]),
        // proveedor 3 (si existía, cargado desde la pestaña del modal) no es
        // editable acá pero se reenvía tal cual para no borrarlo al guardar.
        p3Passthrough: proveedoresPorPrioridad[3] || null,
      }
    },
    marcarModificado(id) {
      this.filasModificadas = new Set([...this.filasModificadas, id])
    },
    // Distinto de marcarModificado: además de marcar la fila como "sucia"
    // (borde amarillo, contador, botón guardar), registra que lo que cambió
    // es un campo de FICHA — así, si lo único que cambió en una fila sin
    // ficha_cargada es el código, guardarCambios() no la manda al bulk y no
    // crea una ficha vacía sin que nadie la haya pedido.
    marcarFichaModificada(id) {
      this.marcarModificado(id)
      this.filasFichaTocada = new Set([...this.filasFichaTocada, id])
    },
    toggleSeleccion(id) {
      const nuevo = new Set(this.seleccionados)
      if (nuevo.has(id)) nuevo.delete(id)
      else nuevo.add(id)
      this.seleccionados = nuevo
    },
    toggleSeleccionarTodos() {
      this.seleccionados = this.todosVisiblesSeleccionados
        ? new Set()
        : new Set(this.productosFiltrados.map(f => f.producto_id))
    },
    sugerirPrefijoDepartamento(nombre) {
      const STOPWORDS = new Set(['y', 'de', 'en', 'para', 'o', 'del', 'la', 'los', 'las', 'el'])
      const letras = (p) => (p.match(/[a-zA-Z]/g) || []).map(c => c.toUpperCase())
      const palabras = (nombre || '').trim().split(/\s+/).filter(Boolean)
      if (palabras.length === 0) return ''
      const l1 = letras(palabras[0])[0] || ''
      const segunda = palabras.slice(1).find(p => !STOPWORDS.has(p.toLowerCase()) && letras(p).length > 0)
      let l2
      if (segunda) {
        l2 = letras(segunda)[0]
      } else {
        const letrasPrimera = letras(palabras[0])
        l2 = letrasPrimera.length > 1 ? letrasPrimera[1] : 'X'
      }
      // Sugerencia simple, sin resolucion de colisiones entre departamentos
      // (eso solo lo resuelve el script offline de recodificacion masiva) —
      // el usuario siempre ve el preview y puede editar el prefijo antes de confirmar.
      return l1 + l2
    },
    abrirAutonumerar() {
      if (this.seleccionados.size === 0) return
      const sugerido = this.deptoActivoObj ? this.sugerirPrefijoDepartamento(this.deptoActivoObj.nombre) : ''
      this.autonumerarForm = { prefijo: sugerido, numeroInicial: 1, padding: 3 }
      this.modalAutonumerar = true
    },
    cerrarAutonumerar() {
      this.modalAutonumerar = false
    },
    confirmarAutonumerar() {
      if (!this.prefijoValidoAutonumerar) return
      const prefijo = this.autonumerarForm.prefijo.trim().toUpperCase()
      const padding = Math.max(1, Number(this.autonumerarForm.padding) || 3)
      let numero = Math.max(1, Number(this.autonumerarForm.numeroInicial) || 1)
      const idsEnOrden = this.productosFiltrados.map(f => f.producto_id).filter(id => this.seleccionados.has(id))
      for (const id of idsEnOrden) {
        this.borrador[id].codigo = `${prefijo}-${String(numero).padStart(padding, '0')}`
        numero++
        this.marcarModificado(id)
        delete this.erroresCodigoPorFila[id]
      }
      this.modalAutonumerar = false
      this.seleccionados = new Set()
    },
    textoProveedor(productoId, slot) {
      const key = `${productoId}_${slot}`
      if (this.autocompleteAbierto && this.autocompleteAbierto.productoId === productoId && this.autocompleteAbierto.slot === slot
          && key in this.autocompleteTextoLibre) {
        return this.autocompleteTextoLibre[key]
      }
      const provId = this.borrador[productoId]?.[slot]?.proveedor_id
      if (!provId) return ''
      const p = this.proveedores.find(x => x.id === provId)
      return p ? `${p.codigo || '???'} — ${p.nombre}` : ''
    },
    abrirAutocomplete(productoId, slot) {
      this.autocompleteAbierto = { productoId, slot }
      const key = `${productoId}_${slot}`
      this.autocompleteTextoLibre[key] = ''
    },
    onInputAutocomplete(productoId, slot, event) {
      const key = `${productoId}_${slot}`
      this.autocompleteTextoLibre[key] = event.target.value
    },
    onEnterAutocomplete(productoId, slot, event) {
      if (this.sugerenciasProveedor.length > 0) {
        this.seleccionarProveedor(productoId, slot, this.sugerenciasProveedor[0])
      } else {
        event.target.blur()
      }
    },
    onBlurAutocomplete(productoId, slot) {
      // pequeño delay para que el click en <li> (mousedown.prevent) alcance a resolverse antes de cerrar
      setTimeout(() => {
        this.autocompleteAbierto = null
        delete this.autocompleteTextoLibre[`${productoId}_${slot}`]
      }, 120)
    },
    seleccionarProveedor(productoId, slot, proveedor) {
      this.borrador[productoId][slot].proveedor_id = proveedor.id
      this.autocompleteAbierto = null
      delete this.autocompleteTextoLibre[`${productoId}_${slot}`]
      this.marcarFichaModificada(productoId)
    },
    defaultCreditoProveedor(proveedorId) {
      const p = this.proveedores.find(x => x.id === proveedorId)
      return p?.dias_credito || 0
    },
    defaultLeadTimeProveedor(proveedorId) {
      const p = this.proveedores.find(x => x.id === proveedorId)
      return p?.lead_time_dias_default || 0
    },
    esPlanificado(fila) {
      return (fila.existencia || 0) === 0 && (fila.stock_min_objetivo || 0) > 0
    },
    abrirModalNuevoProducto() {
      if (!this.deptoActivoId) return
      this.formNuevoProducto = {
        codigo: '', descripcion: '',
        departamento_id: this.deptoActivoId,
        categoria_id:    this.categoriaActivaId || null,
        costo_usd: 0, precio_venta_usd: 0, stock: 0,
      }
      this.errorNuevoProducto = ''
      this.modalNuevoProducto = true
    },
    cerrarModalNuevoProducto() {
      this.modalNuevoProducto = false
      this.errorNuevoProducto = ''
    },
    async crearProductoPlanificado() {
      if (!this.formNuevoProducto.descripcion.trim()) {
        this.errorNuevoProducto = 'La descripción es obligatoria'
        return
      }
      this.guardandoNuevoProducto = true
      this.errorNuevoProducto = ''
      try {
        const costo  = Number(this.formNuevoProducto.costo_usd) || 0
        const precio = Number(this.formNuevoProducto.precio_venta_usd) || 0
        const margen = costo > 0 ? (precio / costo - 1) : 0.30
        const res = await axios.post('/productos/', {
          nombre:          this.formNuevoProducto.descripcion,
          codigo:          this.formNuevoProducto.codigo || null,
          departamento_id: this.formNuevoProducto.departamento_id,
          categoria_id:    this.formNuevoProducto.categoria_id,
          costo_usd:       costo,
          margen,
          stock:           Number(this.formNuevoProducto.stock) || 0,
        })
        const nuevoId = res.data.id
        this.modalNuevoProducto = false
        // Limpiar filtros secundarios para garantizar que la fila nueva se vea
        // (un producto recién creado, sin ficha, puede no calzar con "con ficha"
        // o un semáforo puntual, aunque sí pertenezca al depto/categoría activos).
        this.busqueda     = ''
        this.filtroEstado = 'todos'
        await this.cargarTabla()
        await this.$nextTick()
        this.enfocarFilaNueva(nuevoId)
      } catch (e) {
        this.errorNuevoProducto = e?.response?.data?.detail || 'Error al crear el producto'
      } finally {
        this.guardandoNuevoProducto = false
      }
    },
    enfocarFilaNueva(productoId) {
      const input = this.$el.querySelector(`tr[data-producto-id="${productoId}"] .repo-input-prov`)
      if (input) {
        input.scrollIntoView({ block: 'nearest' })
        input.focus()
      }
    },
    bajarFila(event) {
      const cell = event.target.closest('td')
      const row  = event.target.closest('tr')
      if (!cell || !row) return
      const nextRow = row.nextElementSibling
      if (!nextRow) return
      const colIndex = Array.prototype.indexOf.call(row.children, cell)
      const nextCell = nextRow.children[colIndex]
      const nextInput = nextCell?.querySelector('input, select')
      if (nextInput) nextInput.focus()
    },
    modoAbrev(modo) {
      return { stock_continuo: 'SCO', pedido_bajo_demanda: 'PBD', lote_grande: 'LG', stock_estrategico_descuento: 'SED' }[modo] || modo
    },
    modoNombreCompleto(modo) {
      return MODOS_NOMBRES[modo] || modo
    },
    semaforoIcono(estado) {
      return { verde: '🟢', amarillo: '🟡', rojo: '🔴', gris: '⚪' }[estado] || '—'
    },
    semaforoTooltip(fila) {
      const nombres = { verde: 'Verde', amarillo: 'Amarillo', rojo: 'Rojo', gris: 'Proveedor sin stock' }
      const base = nombres[fila.estado_semaforo] || fila.estado_semaforo
      const rec  = fila.recomendacion_pedido?.texto || ''
      return `${base}${fila.estado_semaforo === 'gris' ? '' : ''} — ${rec}`
    },
    descartarCambios() {
      if (!confirm(`¿Descartar ${this.filasModificadas.size} cambio(s) sin guardar?`)) return
      this.reconstruirBorrador()
      this.filasModificadas = new Set()
      this.filasFichaTocada = new Set()
      this.erroresCodigoPorFila = {}
      this.errorGuardado = ''
    },
    async guardarCambios() {
      if (this.filasModificadas.size === 0) return
      this.guardando = true
      this.errorGuardado = ''

      // 1) Código: PUT individual por fila (mismo endpoint que Inventario clásico
      // ya usa, valida UNIQUE). Aislado a propósito — si uno choca, no bloquea
      // ni el resto de los códigos ni el guardado de fichas.
      const idsConCodigoCambiado = [...this.filasModificadas].filter(id => {
        const original = this.productos.find(p => p.producto_id === id)
        return original && (this.borrador[id].codigo || '') !== (original.producto_codigo || '')
      })
      const resultadosCodigo = await Promise.allSettled(
        idsConCodigoCambiado.map(id =>
          axios.put(`/productos/${id}/codigo`, { codigo: this.borrador[id].codigo || null })
        )
      )
      resultadosCodigo.forEach((resultado, i) => {
        const id = idsConCodigoCambiado[i]
        if (resultado.status === 'fulfilled') {
          delete this.erroresCodigoPorFila[id]
          const prod = this.productos.find(p => p.producto_id === id)
          if (prod) prod.producto_codigo = resultado.value.data.codigo
        } else {
          this.erroresCodigoPorFila[id] = resultado.reason?.response?.data?.detail || 'Error al guardar el código'
        }
      })

      // 2) Ficha: bulk transaccional, solo para filas donde cambió de verdad
      // algo de la ficha (no las que solo tocaron el código — si no, una fila
      // sin ficha_cargada terminaría creando una ficha vacía sin que nadie
      // la haya pedido, solo por renombrar su código).
      const idsFicha = [...this.filasFichaTocada]
      let fichaOk = true
      if (idsFicha.length > 0) {
        try {
          const fichas = idsFicha.map(id => {
            const b = this.borrador[id]
            const proveedores = []
            if (b.p1.proveedor_id) proveedores.push({ prioridad: 1, ...this._limpiarSlot(b.p1) })
            if (b.p2.proveedor_id) proveedores.push({ prioridad: 2, ...this._limpiarSlot(b.p2) })
            if (b.p3Passthrough) {
              proveedores.push({
                prioridad: 3,
                proveedor_id: b.p3Passthrough.proveedor_id,
                precio_actual_usd: b.p3Passthrough.precio_actual_usd,
                credito_dias: b.p3Passthrough.credito_dias,
                lead_time_dias: b.p3Passthrough.lead_time_dias,
                minimo_compra: b.p3Passthrough.minimo_compra,
                sin_stock_declarado: b.p3Passthrough.sin_stock_declarado,
                sin_stock_fecha: b.p3Passthrough.sin_stock_fecha,
              })
            }
            return {
              producto_id:         id,
              modo_reposicion:     b.modo_reposicion,
              stock_min_objetivo:  Number(b.stock_min_objetivo) || 0,
              stock_max_objetivo:  Number(b.stock_max_objetivo) || 0,
              unidades_exhibicion: Number(b.unidades_exhibicion) || 0,
              colchon_dias:        Number(b.colchon_dias) || 0,
              activo:              b.activo,
              proveedores,
            }
          })
          const res = await axios.put('/productos/reposicion/bulk', { fichas })
          const actualizadas = res.data.actualizadas
          const idsActualizados = new Set()
          for (const fichaActualizada of actualizadas) {
            const idx = this.productos.findIndex(p => p.producto_id === fichaActualizada.producto_id)
            if (idx !== -1) {
              // el bulk no toca el codigo — preservar el que ya quedo en this.productos
              const conCodigoPreservado = { ...fichaActualizada, producto_codigo: this.productos[idx].producto_codigo }
              this.productos.splice(idx, 1, conCodigoPreservado)
              this.borrador[fichaActualizada.producto_id] = this.construirFilaBorrador(conCodigoPreservado)
            }
            idsActualizados.add(fichaActualizada.producto_id)
          }
          this.filasFichaTocada = new Set([...this.filasFichaTocada].filter(id => !idsActualizados.has(id)))
        } catch (e) {
          fichaOk = false
          const detail = e?.response?.data?.detail
          if (detail && detail.errores) {
            this.errorGuardado = detail.errores.map(er => `Producto ${er.producto_id}: ${er.detail}`).join(' · ')
          } else {
            this.errorGuardado = detail || 'Error al guardar los cambios'
          }
        }
      }

      // 3) Una fila sigue "modificada" solo si le quedó pendiente un error de
      // código, o (si el bulk de fichas falló entero) su cambio de ficha.
      const nuevasModificadas = new Set()
      for (const id of this.filasModificadas) {
        const tieneErrorCodigo    = id in this.erroresCodigoPorFila
        const tieneFichaPendiente = !fichaOk && this.filasFichaTocada.has(id)
        if (tieneErrorCodigo || tieneFichaPendiente) nuevasModificadas.add(id)
      }
      this.filasModificadas = nuevasModificadas

      this.guardando = false
    },
    _limpiarSlot(slot) {
      return {
        proveedor_id:         slot.proveedor_id,
        precio_actual_usd:    slot.precio_actual_usd,
        credito_dias:         slot.credito_dias,
        lead_time_dias:       slot.lead_time_dias,
        minimo_compra:        slot.minimo_compra,
        sin_stock_declarado:  slot.sin_stock_declarado,
        sin_stock_fecha:      slot.sin_stock_fecha,
      }
    },
  },
}
</script>

<style scoped>
.repo-tabla-wrap { display: flex; flex-direction: column; gap: 1rem; }

.repo-selector-depto { display: flex; align-items: flex-end; gap: 1rem; flex-wrap: wrap; }
.repo-selector-depto .field { display: flex; flex-direction: column; gap: 0.3rem; min-width: 280px; }
.repo-selector-depto label { font-size: 0.78rem; font-weight: 700; color: var(--texto-secundario); }
.select-resaltado { border: 2px solid #FFCC00 !important; box-shadow: 0 0 0 3px #FFCC0033; }

.btn-panel-proveedores {
  background: transparent; color: var(--texto-principal); border: 1px solid var(--borde);
  padding: 0.55rem 1rem; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.85rem;
}
.btn-agregar-planificado {
  background: #1A1A1A; color: #FFCC00; border: none;
  padding: 0.55rem 1rem; border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 0.85rem;
}
.btn-agregar-planificado:disabled { opacity: 0.4; cursor: not-allowed; }

.modal-nuevo-planificado { max-width: 620px; }
.repo-modal-hint { font-size: 0.82rem; color: var(--texto-secundario); margin: -0.25rem 0 1rem; }
.modal-autonumerar { max-width: 460px; }
.repo-preview-autonumerar { font-size: 0.85rem; margin: 0.75rem 0; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.repo-preview-codigo { background: #FFCC0033; padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 700; font-family: monospace; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; }
.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }

.repo-vacio-inicial {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 4rem 2rem; text-align: center; color: var(--texto-secundario);
}
.repo-vacio-icono { font-size: 3rem; margin-bottom: 0.75rem; }
.repo-vacio-inicial h2 { color: var(--texto-principal); margin: 0 0 0.5rem; font-size: 1.3rem; }
.repo-vacio-inicial p { max-width: 420px; margin: 0; font-size: 0.9rem; }

.repo-tabla-layout { display: flex; gap: 1rem; align-items: flex-start; }
.repo-tabla-main { flex: 1; min-width: 0; }

.repo-filtros { display: flex; gap: 0.6rem; flex-wrap: wrap; align-items: center; margin-bottom: 0.75rem; }
.repo-buscador { flex: 1; min-width: 220px; padding: 0.5rem 0.75rem; border: 1px solid var(--borde); border-radius: 8px; }
.repo-contador { font-size: 0.8rem; color: var(--texto-secundario); margin-left: auto; }

.repo-barra-guardado { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.75rem; }
.btn-guardar-lote { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; font-weight: 700; position: relative; }
.btn-guardar-lote:disabled { opacity: 0.4; cursor: not-allowed; }
.badge-pendientes { background: #DC2626; color: white; border-radius: 999px; padding: 0.05rem 0.45rem; font-size: 0.72rem; margin-left: 0.4rem; }
.btn-descartar-lote { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-descartar-lote:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-autonumerar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.6rem 1.2rem; border-radius: 8px; cursor: pointer; font-weight: 600; position: relative; }
.btn-autonumerar:disabled { opacity: 0.4; cursor: not-allowed; }
.repo-error-guardado { color: var(--danger); font-size: 0.82rem; font-weight: 600; }

.repo-cargando { padding: 2rem; text-align: center; color: var(--texto-secundario); }

.repo-tabla-scroll { overflow-x: auto; border: 1px solid var(--borde); border-radius: 8px; }
.repo-tabla { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.repo-tabla th { background: #1A1A1A; color: #FFCC00; padding: 0.5rem 0.4rem; text-align: left; white-space: nowrap; position: sticky; top: 0; cursor: default; }
.repo-tabla td { padding: 0.3rem 0.4rem; border-bottom: 1px solid var(--borde); white-space: nowrap; }
.repo-fila-modificada { box-shadow: inset 3px 0 0 #FFCC00; background: #FFCC0011; }
.repo-celda-codigo { font-weight: 700; font-size: 0.78rem; }
.repo-celda-planificada { border-left: 3px dashed #9CA3AF; padding-left: 0.3rem; cursor: help; }
.repo-celda-codigo-error { box-shadow: inset 3px 0 0 var(--danger); }
.repo-icono-planificado { margin-right: 0.15rem; }
.repo-input-codigo { width: 78px; font-weight: 700; }
.repo-celda-codigo-error .repo-input-codigo { border-color: var(--danger) !important; background: #DC262611; }
.repo-celda-check { text-align: center; width: 28px; }
.repo-celda-desc { max-width: 220px; overflow: hidden; text-overflow: ellipsis; }
.repo-celda-num { text-align: right; }
.repo-sin-datos { text-align: center; color: var(--texto-secundario); padding: 1.5rem; }

.repo-tabla input, .repo-tabla select { border: 1px solid var(--borde); border-radius: 4px; padding: 0.2rem 0.3rem; font-size: 0.8rem; background: var(--fondo); color: var(--texto-principal); }
.repo-input-sm { width: 52px; }
.repo-input-prov { width: 130px; }
.repo-input-modo { width: 62px; }

.repo-celda-autocomplete { position: relative; }
.repo-autocomplete-lista {
  position: absolute; z-index: 20; top: 100%; left: 0; min-width: 220px; max-height: 200px; overflow-y: auto;
  background: var(--fondo); border: 1px solid var(--borde); border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  list-style: none; margin: 2px 0 0; padding: 0.25rem 0;
}
.repo-autocomplete-lista li { padding: 0.35rem 0.6rem; cursor: pointer; font-size: 0.8rem; white-space: nowrap; }
.repo-autocomplete-lista li:hover { background: #FFCC0033; }
.repo-autocomplete-vacio { color: var(--texto-secundario); cursor: default !important; }
.repo-autocomplete-vacio:hover { background: transparent !important; }

.repo-celda-semaforo { text-align: center; }
.repo-punto { cursor: help; font-size: 0.95rem; }
.repo-punto--nulo { color: var(--texto-secundario); }

.repo-panel-lateral { width: 280px; flex-shrink: 0; border: 1px solid var(--borde); border-radius: 8px; padding: 0.75rem; max-height: 70vh; overflow-y: auto; }
.repo-panel-lateral h3 { margin: 0 0 0.6rem; font-size: 0.9rem; color: var(--texto-principal); }
.repo-panel-item { padding: 0.4rem 0; border-bottom: 1px solid var(--borde); font-size: 0.8rem; }
.repo-panel-item:last-child { border-bottom: none; }
.repo-panel-sub { color: var(--texto-secundario); font-size: 0.72rem; margin-top: 0.1rem; }
</style>
