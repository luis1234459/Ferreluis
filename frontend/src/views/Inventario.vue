<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Inventario</h1>
        <div class="top-acciones">
          <button class="btn-deptos" @click="mostrarDeptos = true">Departamentos</button>
          <button class="btn-nuevo" @click="abrirNuevoProducto">+ Nuevo producto</button>
        </div>
      </div>

      <div class="contenido-inner">

        <!-- Tasas actuales -->
        <div class="tasas-bar" v-if="tasaBcv">
          <span>BCV: <strong>Bs. {{ tasaBcv.toFixed(2) }}</strong></span>
          <span>Binance: <strong>Bs. {{ tasaBinance.toFixed(2) }}</strong></span>
          <span>Factor: <strong>{{ factor.toFixed(4) }}</strong></span>
        </div>

        <!-- Tabs -->
        <div class="tabs-nav">
          <button :class="['tab-btn', tabActivo === 'productos' ? 'tab-activo' : '']"
            @click="tabActivo = 'productos'">Productos</button>
          <button :class="['tab-btn', tabActivo === 'ofertas' ? 'tab-activo' : '']"
            @click="cambiarTabOfertas">
            Ofertas
            <span v-if="ofertas.length" class="tab-badge">{{ ofertas.length }}</span>
          </button>
        </div>

        <!-- ══════════════════════════════════════════════════════════ -->
        <!-- Tab: Productos                                            -->
        <!-- ══════════════════════════════════════════════════════════ -->
        <div v-show="tabActivo === 'productos'">

          <!-- Filtros -->
          <div class="filtros">
            <input v-model="busqueda" placeholder="Buscar producto..." class="buscador" />
            <select v-model="filtroDepartamento">
              <option value="">Todos los departamentos</option>
              <option v-for="d in departamentos" :key="d.id" :value="d.id">{{ d.nombre }}</option>
            </select>
            <select v-model="filtroTipo">
              <option value="">Todos los tipos</option>
              <option value="clave">Solo productos clave</option>
              <option value="compuesto">Solo productos compuestos</option>
            </select>
            <button v-if="esAdmin"
              :class="['btn-toggle-inactivos', mostrarInactivos ? 'activo' : '']"
              @click="toggleInactivos">
              {{ mostrarInactivos ? '👁 Ocultando inactivos' : '👁 Mostrar inactivos' }}
            </button>
          </div>

          <!-- Tabla -->
          <div class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Nombre</th>
                  <th>Depto.</th>
                  <th>Categoría</th>
                  <th>Costo</th>
                  <th>Margen</th>
                  <th>P. Base</th>
                  <th>P. Ref.</th>
                  <th>Bs</th>
                  <th>Stock</th>
                  <th>Ubic.</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in productosFiltrados" :key="p.id"
                  :class="{ 'fila-stock-bajo': p.stock < 5 }">
                  <td class="celda-codigo">
                    <span v-if="codigoEditando !== p.id" class="codigo-tag" @click="iniciarEditCodigo(p)" title="Clic para editar código">
                      {{ p.codigo || '—' }}
                    </span>
                    <span v-else class="codigo-edit-wrap">
                      <input v-model="codigoTemp" class="input-codigo" @keyup.enter="guardarCodigo(p)" @keyup.escape="codigoEditando = null" placeholder="Ej: HRR-001" />
                      <button class="btn-ok-codigo" @click="guardarCodigo(p)">✓</button>
                      <button class="btn-cancel-codigo" @click="codigoEditando = null">✕</button>
                    </span>
                  </td>
                  <td>
                    <span class="prod-nombre">{{ p.nombre }}</span>
                    <span v-if="p.es_producto_clave"     class="badge-clave">CLAVE</span>
                    <span v-if="p.es_producto_compuesto" class="badge-comp">COMPUESTO</span>
                    <span v-if="!p.activo"               class="badge-inactivo">INACTIVO</span>
                  </td>
                  <td class="txt-muted">{{ nombreDepartamento(p.departamento_id) }}</td>
                  <td class="txt-muted">{{ p.categoria || '—' }}</td>
                  <td>${{ Number(p.costo_usd).toFixed(2) }}</td>
                  <td>{{ (Number(p.margen) * 100).toFixed(0) }}%</td>
                  <td>${{ Number(p.precio_base_usd).toFixed(2) }}</td>
                  <td class="txt-usd">${{ Number(p.precio_referencial_usd).toFixed(2) }}</td>
                  <td style="color:#996600;font-weight:600">Bs. {{ Number(p.precio_bs).toFixed(2) }}</td>
                  <td :class="{ 'txt-rojo': p.stock < 5 }">{{ p.stock }}</td>
                  <td>
                    <button class="btn-ubicar" @click="abrirUbicaciones(p)" title="Ubicaciones físicas">📍</button>
                  </td>
                  <td class="acciones">
                    <button class="btn-editar"    @click="editar(p)">Editar</button>
                    <button class="btn-variantes" @click="abrirVariantes(p)">Variantes</button>
                    <button v-if="p.es_producto_compuesto" class="btn-comp" @click="abrirComponentes(p)">Componentes</button>
                    <button v-if="esAdmin && p.activo"  class="btn-desactivar" @click="cambiarEstado(p, false)">Desactivar</button>
                    <button v-if="esAdmin && !p.activo" class="btn-activar"    @click="cambiarEstado(p, true)">Activar</button>
                    <button class="btn-eliminar"  @click="eliminar(p.id)">Eliminar</button>
                  </td>
                </tr>
                <tr v-if="productosFiltrados.length === 0">
                  <td colspan="12" class="sin-datos">No hay productos registrados</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════ -->
        <!-- Tab: Ofertas                                              -->
        <!-- ══════════════════════════════════════════════════════════ -->
        <div v-show="tabActivo === 'ofertas'">
          <div class="ofertas-header">
            <span class="ofertas-desc">Descuentos y precios especiales por producto</span>
            <button class="btn-nuevo" @click="abrirNuevaOferta">+ Nueva oferta</button>
          </div>

          <div class="tabla-container">
            <table>
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Tipo</th>
                  <th>Valor</th>
                  <th>Precio efectivo</th>
                  <th>Vigencia</th>
                  <th>Uso</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="o in ofertas" :key="o.id">
                  <td style="font-weight:600">{{ o.nombre_producto }}</td>
                  <td>
                    <span :class="'badge-tipo-' + o.tipo_precio">
                      {{ o.tipo_precio === 'porcentaje' ? '% Descuento' : 'Precio directo' }}
                    </span>
                  </td>
                  <td>{{ o.tipo_precio === 'porcentaje' ? o.valor + '%' : '$' + Number(o.valor).toFixed(2) }}</td>
                  <td class="txt-verde">
                    {{ o.precio_efectivo_usd != null ? '$' + Number(o.precio_efectivo_usd).toFixed(2) : '—' }}
                  </td>
                  <td class="txt-muted">
                    {{ formatFecha(o.fecha_inicio) }}
                    <span v-if="o.fecha_fin"> → {{ formatFecha(o.fecha_fin) }}</span>
                    <span v-else> (sin fin)</span>
                  </td>
                  <td>
                    <span v-if="o.cantidad_limite">{{ o.cantidad_usada }} / {{ o.cantidad_limite }}</span>
                    <span v-else class="txt-muted">—</span>
                  </td>
                  <td>
                    <span :class="o.activo ? 'badge-activa' : 'badge-inactiva'">
                      {{ o.activo ? 'Activa' : 'Inactiva' }}
                    </span>
                  </td>
                  <td class="acciones">
                    <button class="btn-editar"   @click="editarOferta(o)">Editar</button>
                    <button class="btn-eliminar" @click="eliminarOferta(o.id)">Eliminar</button>
                  </td>
                </tr>
                <tr v-if="ofertas.length === 0">
                  <td colspan="8" class="sin-datos">No hay ofertas registradas</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════ -->
        <!-- Modal: Nuevo / Editar Producto                           -->
        <!-- ══════════════════════════════════════════════════════════ -->
        <div class="overlay" v-if="mostrarForm" @click.self="cancelar">
          <div class="modal modal-form">
            <div class="modal-header">
              <h2>{{ editando ? 'Editar producto' : 'Nuevo producto' }}</h2>
              <button class="btn-cerrar-modal" @click="cancelar">✕</button>
            </div>

            <div class="grid-form">
              <div class="field field-wide">
                <label>Nombre *</label>
                <input v-model="form.nombre" placeholder="Ej: Martillo 16oz" />
              </div>
              <div class="field">
                <label>Código</label>
                <input v-model="form.codigo" placeholder="Ej: HRR-001 (opcional)" />
              </div>
              <div class="field">
                <label>Departamento</label>
                <select v-model="form.departamento_id">
                  <option :value="null">— Sin departamento —</option>
                  <option v-for="d in departamentos" :key="d.id" :value="d.id">{{ d.nombre }}</option>
                </select>
              </div>
              <div class="field">
                <label>Categoría</label>
                <input v-model="form.categoria" placeholder="Ej: Herramientas" />
              </div>
              <div class="field">
                <label>Proveedor principal</label>
                <select v-model="form.proveedor_id">
                  <option :value="null">— Sin proveedor —</option>
                  <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                </select>
              </div>
              <div class="field">
                <label>Costo USD</label>
                <input v-model.number="form.costo_usd" type="number" min="0" step="0.01" placeholder="0.00" />
              </div>
              <div class="field">
                <label>Margen (%)</label>
                <input v-model.number="form.margen_pct" type="number" min="0" max="999" step="1"
                  placeholder="Ej: 30" @input="actualizarMargen" />
              </div>
              <div class="field">
                <label>Stock</label>
                <input v-model.number="form.stock" type="number" min="0" placeholder="0" />
              </div>
              <div class="field">
                <label>Descripción</label>
                <input v-model="form.descripcion" placeholder="Descripción opcional" />
              </div>
            </div>

            <!-- Opciones especiales -->
            <div class="opciones-especiales">
              <label class="check-opt">
                <input type="checkbox" v-model="form.es_producto_clave" />
                <span class="check-label">
                  <strong>Producto clave (Pareto)</strong>
                  <small>Prioridad alta en reportes y reposición</small>
                </span>
              </label>
              <label class="check-opt">
                <input type="checkbox" v-model="form.es_producto_compuesto" />
                <span class="check-label">
                  <strong>Producto compuesto</strong>
                  <small>Se arma a partir de otros productos del inventario</small>
                </span>
              </label>
              <div class="field field-dto" v-if="form.es_producto_compuesto">
                <label>Descuento al vender como compuesto (%) <small>Solo admin</small></label>
                <input v-model.number="form.descuento_compuesto_pct"
                  type="number" min="0" max="100" step="0.1" placeholder="0" />
              </div>
            </div>

            <!-- Preview precios -->
            <div class="preview-precios" v-if="form.costo_usd > 0 && form.margen > 0">
              <p class="preview-titulo">Vista previa de precios</p>
              <div class="preview-row">
                <span>Precio base (USD):</span>
                <strong class="txt-usd">${{ precioBaseForm.toFixed(2) }}</strong>
              </div>
              <div class="preview-row" v-if="tasaBcv">
                <span>Precio referencial (USD):</span>
                <strong class="txt-usd">${{ precioRefForm.toFixed(2) }}</strong>
              </div>
              <div class="preview-row" v-if="tasaBinance">
                <span>Precio en Bs:</span>
                <strong>Bs. {{ precioBsForm.toFixed(2) }}</strong>
              </div>
            </div>

            <div class="form-botones">
              <button class="btn-cancelar" @click="cancelar">Cancelar</button>
              <button class="btn-guardar"  @click="guardar" :disabled="guardando">
                {{ guardando ? 'Guardando...' : 'Guardar' }}
              </button>
            </div>
            <p class="msg-error" v-if="error">{{ error }}</p>
          </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════ -->
        <!-- Modal: Variantes                                         -->
        <!-- ══════════════════════════════════════════════════════════ -->
        <div class="overlay" v-if="modalVariantes" @click.self="cerrarVariantes">
          <div class="modal modal-variantes">
            <div class="modal-header">
              <h2>Variantes — {{ modalVariantes.nombre }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarVariantes">✕</button>
            </div>

            <table v-if="variantes.length > 0">
              <thead>
                <tr><th>Clase</th><th>Color</th><th>Stock</th><th>Precio override</th><th>Estado</th><th></th></tr>
              </thead>
              <tbody>
                <tr v-for="v in variantes" :key="v.id">
                  <td style="font-weight:600">{{ v.clase }}</td>
                  <td>{{ v.color || '—' }}</td>
                  <td>{{ v.stock }}</td>
                  <td>{{ v.precio_override_usd != null ? '$' + Number(v.precio_override_usd).toFixed(2) : 'Del producto' }}</td>
                  <td><span :class="v.activo ? 'badge-activa' : 'badge-inactiva'">{{ v.activo ? 'Activa' : 'Inactiva' }}</span></td>
                  <td class="acciones">
                    <button class="btn-editar"   @click="editarVariante(v)">Editar</button>
                    <button class="btn-eliminar" @click="eliminarVariante(v.id)">✕</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="sin-datos" style="margin: 0.75rem 0">Sin variantes registradas</p>

            <!-- Formulario variante -->
            <div class="subform" v-if="mostrarFormVariante">
              <h3 class="subtitulo-subform">{{ editandoVarianteId ? 'Editar variante' : 'Nueva variante' }}</h3>
              <div class="grid-form-sm">
                <div class="field">
                  <label>Clase *</label>
                  <input v-model="formVariante.clase" placeholder="Ej: Clase A" />
                </div>
                <div class="field">
                  <label>Color</label>
                  <input v-model="formVariante.color" placeholder="Ej: Rojo" />
                </div>
                <div class="field">
                  <label>Stock</label>
                  <input v-model.number="formVariante.stock" type="number" min="0" />
                </div>
                <div class="field">
                  <label>Precio USD <small>(vacío = usa precio del producto)</small></label>
                  <input v-model="formVariante.precio_override_str" type="number" min="0" step="0.01"
                    placeholder="Precio del producto" />
                </div>
              </div>
              <label class="check-opt" style="margin-top:0.5rem">
                <input type="checkbox" v-model="formVariante.activo" />
                <span class="check-label"><strong>Variante activa</strong></span>
              </label>
              <div class="form-botones" style="margin-top:0.75rem">
                <button class="btn-cancelar" @click="cancelarVariante">Cancelar</button>
                <button class="btn-guardar"  @click="guardarVariante" :disabled="guardando">
                  {{ guardando ? 'Guardando...' : 'Guardar variante' }}
                </button>
              </div>
            </div>

            <button v-if="!mostrarFormVariante" class="btn-agregar-linea" @click="abrirFormVariante">
              + Agregar variante
            </button>
          </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════ -->
        <!-- Modal: Componentes                                        -->
        <!-- ══════════════════════════════════════════════════════════ -->
        <div class="overlay" v-if="modalComponentes" @click.self="cerrarComponentes">
          <div class="modal modal-variantes">
            <div class="modal-header">
              <h2>Componentes — {{ modalComponentes.nombre }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarComponentes">✕</button>
            </div>
            <p class="desc-comp">Este producto se arma a partir de los siguientes componentes:</p>

            <table v-if="componentes.length > 0">
              <thead>
                <tr><th>Componente</th><th>Cantidad</th><th>P. Base USD</th><th></th></tr>
              </thead>
              <tbody>
                <tr v-for="c in componentes" :key="c.id">
                  <td style="font-weight:600">{{ c.nombre_componente }}</td>
                  <td>{{ c.cantidad }}</td>
                  <td class="txt-usd">${{ Number(c.precio_base_usd).toFixed(2) }}</td>
                  <td><button class="btn-eliminar" @click="eliminarComponente(c.id)">✕</button></td>
                </tr>
              </tbody>
            </table>
            <p v-else class="sin-datos" style="margin: 0.75rem 0">Sin componentes registrados</p>

            <div class="subform" style="margin-top:1rem">
              <h3 class="subtitulo-subform">Agregar componente</h3>
              <div class="grid-form-sm">
                <div class="field">
                  <label>Producto componente</label>
                  <select v-model="formComponente.producto_componente_id">
                    <option value="">— Seleccionar —</option>
                    <option v-for="p in productosDisponiblesComp" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                  </select>
                </div>
                <div class="field">
                  <label>Cantidad</label>
                  <input v-model.number="formComponente.cantidad" type="number" min="0.01" step="0.01" />
                </div>
              </div>
              <div class="form-botones" style="margin-top:0.75rem">
                <button class="btn-guardar" @click="guardarComponente" :disabled="guardando">
                  {{ guardando ? 'Agregando...' : '+ Agregar' }}
                </button>
              </div>
              <p class="msg-error" v-if="errorComp">{{ errorComp }}</p>
            </div>
          </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════ -->
        <!-- Modal: Nueva / Editar Oferta                             -->
        <!-- ══════════════════════════════════════════════════════════ -->
        <div class="overlay" v-if="mostrarFormOferta" @click.self="cerrarOferta">
          <div class="modal modal-sm">
            <div class="modal-header">
              <h2>{{ editandoOfertaId ? 'Editar oferta' : 'Nueva oferta' }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarOferta">✕</button>
            </div>
            <div class="grid-form">
              <div class="field field-wide">
                <label>Producto *</label>
                <select v-model="formOferta.producto_id">
                  <option value="">— Seleccionar —</option>
                  <option v-for="p in productos" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                </select>
              </div>
              <div class="field">
                <label>Tipo de oferta</label>
                <select v-model="formOferta.tipo_precio">
                  <option value="porcentaje">% Descuento sobre precio base</option>
                  <option value="directo">Precio directo en USD</option>
                </select>
              </div>
              <div class="field">
                <label>{{ formOferta.tipo_precio === 'porcentaje' ? 'Porcentaje (%)' : 'Precio en USD' }}</label>
                <input v-model.number="formOferta.valor" type="number" min="0" step="0.01" placeholder="0" />
              </div>
              <div class="field">
                <label>Fecha inicio *</label>
                <input type="date" v-model="formOferta.fecha_inicio" />
              </div>
              <div class="field">
                <label>Fecha fin <small>(vacío = sin límite)</small></label>
                <input type="date" v-model="formOferta.fecha_fin" />
              </div>
              <div class="field">
                <label>Cantidad límite <small>(vacío = ilimitada)</small></label>
                <input v-model="formOferta.cantidad_limite_str" type="number" min="1" step="1" placeholder="Ilimitada" />
              </div>
            </div>

            <label class="check-opt" style="margin: 0.5rem 0">
              <input type="checkbox" v-model="formOferta.activo" />
              <span class="check-label"><strong>Oferta activa</strong></span>
            </label>

            <!-- Preview precio efectivo -->
            <div class="preview-oferta" v-if="formOferta.producto_id && formOferta.valor > 0">
              <span class="preview-titulo">Precio efectivo:</span>
              <strong class="txt-verde">${{ precioEfectivoOferta.toFixed(2) }}</strong>
              <span class="txt-muted" v-if="formOferta.tipo_precio === 'porcentaje'">
                ({{ formOferta.valor }}% dto. sobre ${{ precioBaseProductoOferta.toFixed(2) }})
              </span>
            </div>

            <div class="form-botones" style="margin-top:1rem">
              <button class="btn-cancelar" @click="cerrarOferta">Cancelar</button>
              <button class="btn-guardar"  @click="guardarOferta" :disabled="guardando">
                {{ guardando ? 'Guardando...' : 'Guardar oferta' }}
              </button>
            </div>
            <p class="msg-error" v-if="errorOferta">{{ errorOferta }}</p>
          </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════ -->
        <!-- Modal: Gestionar Departamentos                           -->
        <!-- ══════════════════════════════════════════════════════════ -->
        <div class="overlay" v-if="mostrarDeptos" @click.self="mostrarDeptos = false">
          <div class="modal modal-sm">
            <div class="modal-header">
              <h2>Departamentos</h2>
              <button class="btn-cerrar-modal" @click="mostrarDeptos = false">✕</button>
            </div>

            <div v-for="d in departamentos" :key="d.id" class="depto-row">
              <span v-if="editandoDeptoId !== d.id" class="depto-nombre">{{ d.nombre }}</span>
              <input v-else v-model="formDepto.nombre" class="depto-input" @keydown.enter="guardarDepto" />
              <div class="depto-acciones">
                <template v-if="editandoDeptoId !== d.id">
                  <button class="btn-editar"   @click="editarDepto(d)">Editar</button>
                  <button class="btn-eliminar" @click="eliminarDepto(d.id)">✕</button>
                </template>
                <template v-else>
                  <button class="btn-guardar-sm"   @click="guardarDepto">✓</button>
                  <button class="btn-cancelar-sm"  @click="editandoDeptoId = null">✕</button>
                </template>
              </div>
            </div>

            <p v-if="departamentos.length === 0" class="sin-datos" style="padding: 0.75rem 0">
              Sin departamentos registrados
            </p>

            <div class="depto-nuevo">
              <input v-model="nuevoDeptoNombre" placeholder="Nombre del departamento..."
                class="depto-input-nuevo" @keydown.enter="crearDepto" />
              <button class="btn-guardar-sm" @click="crearDepto" :disabled="!nuevoDeptoNombre.trim()">
                + Agregar
              </button>
            </div>
          </div>
        </div>

        <!-- ══════════════════════════════════════════════════════════ -->
        <!-- Modal: Ubicaciones físicas                               -->
        <!-- ══════════════════════════════════════════════════════════ -->
        <div class="overlay" v-if="modalUbicaciones" @click.self="cerrarUbicaciones">
          <div class="modal modal-ubicaciones">
            <div class="modal-header">
              <h2>Ubicaciones — {{ modalUbicaciones.nombre }}</h2>
              <button class="btn-cerrar-modal" @click="cerrarUbicaciones">✕</button>
            </div>

            <!-- Tabs del modal -->
            <div class="ubic-tabs">
              <button :class="['ubic-tab', tabUbicacion === 'ubicaciones' ? 'ubic-tab-activo' : '']"
                @click="tabUbicacion = 'ubicaciones'">Ubicaciones del producto</button>
              <button :class="['ubic-tab', tabUbicacion === 'estructura' ? 'ubic-tab-activo' : '']"
                @click="tabUbicacion = 'estructura'">Gestionar estructura</button>
            </div>

            <!-- Tab: Ubicaciones del producto -->
            <div v-if="tabUbicacion === 'ubicaciones'">
              <table v-if="ubicaciones.length > 0" style="margin-bottom:1rem">
                <thead>
                  <tr><th>Área</th><th>Pasillo</th><th>Estante</th><th>Nivel</th><th>Cantidad</th><th></th></tr>
                </thead>
                <tbody>
                  <tr v-for="u in ubicaciones" :key="u.id">
                    <td style="font-weight:600">{{ u.area_nombre }}</td>
                    <td>P{{ u.pasillo_num }}</td>
                    <td>E{{ u.estante_num }}</td>
                    <td>{{ u.nivel }}</td>
                    <td>{{ u.cantidad }}</td>
                    <td><button class="btn-eliminar" @click="eliminarUbicacion(u.id)">✕</button></td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="sin-datos" style="margin:0.75rem 0">Sin ubicaciones asignadas</p>

              <!-- Formulario nueva ubicación -->
              <div class="subform">
                <h3 class="subtitulo-subform">Agregar ubicación</h3>
                <div class="grid-form-ubic">
                  <div class="field">
                    <label>Área</label>
                    <select v-model="formUbicacion.area_id" @change="onAreaChange">
                      <option value="">— Seleccionar —</option>
                      <option v-for="a in areas" :key="a.id" :value="a.id">{{ a.nombre }}</option>
                    </select>
                  </div>
                  <div class="field">
                    <label>Pasillo</label>
                    <select v-model="formUbicacion.pasillo_id" @change="onPasilloChange" :disabled="!formUbicacion.area_id">
                      <option value="">— Seleccionar —</option>
                      <option v-for="p in pasillosFiltrados" :key="p.id" :value="p.id">Pasillo {{ p.numero }}</option>
                    </select>
                  </div>
                  <div class="field">
                    <label>Estante</label>
                    <select v-model="formUbicacion.estante_id" :disabled="!formUbicacion.pasillo_id">
                      <option value="">— Seleccionar —</option>
                      <option v-for="e in estandesFiltrados" :key="e.id" :value="e.id">Estante {{ e.numero }}</option>
                    </select>
                  </div>
                  <div class="field">
                    <label>Nivel</label>
                    <input v-model.number="formUbicacion.nivel" type="number" min="1" placeholder="1" />
                  </div>
                  <div class="field">
                    <label>Cantidad</label>
                    <input v-model.number="formUbicacion.cantidad" type="number" min="0" step="0.01" placeholder="0" />
                  </div>
                </div>
                <div class="form-botones" style="margin-top:0.75rem">
                  <button class="btn-guardar" @click="agregarUbicacion" :disabled="guardando">
                    {{ guardando ? 'Guardando...' : '+ Agregar' }}
                  </button>
                </div>
                <p class="msg-error" v-if="errorUbicacion">{{ errorUbicacion }}</p>
              </div>
            </div>

            <!-- Tab: Estructura -->
            <div v-if="tabUbicacion === 'estructura'">

              <!-- Áreas -->
              <div class="estructura-seccion">
                <h3 class="subtitulo-subform">Áreas</h3>
                <div v-for="a in areas" :key="a.id" class="depto-row">
                  <span class="depto-nombre">{{ a.nombre }}</span>
                  <button class="btn-eliminar" @click="eliminarArea(a.id)" style="font-size:0.75rem;padding:0.2rem 0.5rem">✕</button>
                </div>
                <p v-if="areas.length === 0" class="sin-datos" style="padding:0.5rem 0;font-size:0.85rem">Sin áreas</p>
                <div class="depto-nuevo" style="margin-top:0.6rem">
                  <input v-model="formArea.nombre" placeholder="Nombre del área..." class="depto-input-nuevo"
                    @keydown.enter="crearArea" />
                  <button class="btn-guardar-sm" @click="crearArea" :disabled="!formArea.nombre.trim()">+ Agregar</button>
                </div>
              </div>

              <!-- Pasillos -->
              <div class="estructura-seccion">
                <h3 class="subtitulo-subform">Pasillos</h3>
                <div v-for="p in pasillos" :key="p.id" class="depto-row">
                  <span class="depto-nombre">Pasillo {{ p.numero }} — {{ nombreArea(p.area_id) }}</span>
                  <button class="btn-eliminar" @click="eliminarPasillo(p.id)" style="font-size:0.75rem;padding:0.2rem 0.5rem">✕</button>
                </div>
                <p v-if="pasillos.length === 0" class="sin-datos" style="padding:0.5rem 0;font-size:0.85rem">Sin pasillos</p>
                <div class="depto-nuevo" style="margin-top:0.6rem">
                  <select v-model="formPasillo.area_id" style="flex:1">
                    <option value="">— Área —</option>
                    <option v-for="a in areas" :key="a.id" :value="a.id">{{ a.nombre }}</option>
                  </select>
                  <input v-model.number="formPasillo.numero" type="number" min="1" placeholder="N°"
                    class="depto-input-nuevo" style="max-width:80px" @keydown.enter="crearPasillo" />
                  <button class="btn-guardar-sm" @click="crearPasillo" :disabled="!formPasillo.area_id || !formPasillo.numero">+ Agregar</button>
                </div>
              </div>

              <!-- Estantes -->
              <div class="estructura-seccion">
                <h3 class="subtitulo-subform">Estantes</h3>
                <div v-for="e in estantes" :key="e.id" class="depto-row">
                  <span class="depto-nombre">Estante {{ e.numero }} — Pasillo {{ numeroPasillo(e.pasillo_id) }}</span>
                  <button class="btn-eliminar" @click="eliminarEstante(e.id)" style="font-size:0.75rem;padding:0.2rem 0.5rem">✕</button>
                </div>
                <p v-if="estantes.length === 0" class="sin-datos" style="padding:0.5rem 0;font-size:0.85rem">Sin estantes</p>
                <div class="depto-nuevo" style="margin-top:0.6rem">
                  <select v-model="formEstante.pasillo_id" style="flex:1">
                    <option value="">— Pasillo —</option>
                    <option v-for="p in pasillos" :key="p.id" :value="p.id">Pasillo {{ p.numero }} ({{ nombreArea(p.area_id) }})</option>
                  </select>
                  <input v-model.number="formEstante.numero" type="number" min="1" placeholder="N°"
                    class="depto-input-nuevo" style="max-width:80px" @keydown.enter="crearEstante" />
                  <button class="btn-guardar-sm" @click="crearEstante" :disabled="!formEstante.pasillo_id || !formEstante.numero">+ Agregar</button>
                </div>
              </div>

            </div>
          </div>
        </div>

      </div><!-- /contenido-inner -->
    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'Inventario',
  data() {
    return {
      usuario:       JSON.parse(localStorage.getItem('usuario') || '{}'),
      productos:     [],
      departamentos: [],
      proveedores:   [],
      tasaBcv:       null,
      tasaBinance:   null,
      factor:        1,

      // Filtros
      busqueda:           '',
      filtroDepartamento: '',
      filtroTipo:         '',

      // Tab
      tabActivo: 'productos',

      // Ofertas
      ofertas: [],

      // Modal producto
      mostrarForm: false,
      editando:    false,
      guardando:   false,
      error:       '',
      form: {
        id: null, nombre: '', categoria: '',
        departamento_id: null, proveedor_id: null,
        costo_usd: 0, margen: 0.30, margen_pct: 30,
        stock: 0, descripcion: '', foto_url: '',
        es_producto_clave: false, es_producto_compuesto: false,
        descuento_compuesto_pct: 0,
      },

      // Modal variantes
      modalVariantes:      null,
      variantes:           [],
      mostrarFormVariante: false,
      editandoVarianteId:  null,
      formVariante: { clase: '', color: '', stock: 0, precio_override_str: '', activo: true },

      // Modal componentes
      modalComponentes: null,
      componentes:       [],
      formComponente:    { producto_componente_id: '', cantidad: 1 },
      errorComp:         '',

      // Modal oferta
      mostrarFormOferta: false,
      editandoOfertaId:  null,
      errorOferta:       '',
      formOferta: {
        producto_id: '', tipo_precio: 'porcentaje',
        valor: 0, fecha_inicio: '', fecha_fin: '',
        cantidad_limite_str: '', activo: true,
      },

      // Modal departamentos
      mostrarDeptos:    false,
      editandoDeptoId:  null,
      formDepto:        { nombre: '', descripcion: '', activo: true },
      nuevoDeptoNombre: '',

      // Modal ubicaciones
      modalUbicaciones: null,
      tabUbicacion:     'ubicaciones',
      ubicaciones:      [],
      areas:            [],
      pasillos:         [],
      estantes:         [],
      errorUbicacion:   '',
      formUbicacion: { area_id: '', pasillo_id: '', estante_id: '', nivel: 1, cantidad: 0 },
      formArea:    { nombre: '' },
      formPasillo: { area_id: '', numero: null },
      formEstante: { pasillo_id: '', numero: null },

      // Edición inline de código
      codigoEditando: null,
      codigoTemp:     '',

      // Visibilidad de inactivos (solo admin)
      mostrarInactivos: false,
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

    productosFiltrados() {
      return this.productos.filter(p => {
        const q           = this.busqueda.toLowerCase()
        const matchTexto  = p.nombre.toLowerCase().includes(q) ||
                            (p.categoria && p.categoria.toLowerCase().includes(q))
        const matchDepto  = !this.filtroDepartamento ||
                            p.departamento_id === this.filtroDepartamento
        const matchTipo   = !this.filtroTipo ||
                            (this.filtroTipo === 'clave'     && p.es_producto_clave)     ||
                            (this.filtroTipo === 'compuesto' && p.es_producto_compuesto)
        return matchTexto && matchDepto && matchTipo
      })
    },

    precioBaseForm() {
      return Number(this.form.costo_usd || 0) * (1 + Number(this.form.margen || 0))
    },
    precioRefForm() { return this.precioBaseForm * this.factor },
    precioBsForm()  { return this.precioBaseForm * (this.tasaBinance || 0) },

    productosDisponiblesComp() {
      if (!this.modalComponentes) return this.productos
      return this.productos.filter(p => p.id !== this.modalComponentes.id)
    },

    precioBaseProductoOferta() {
      const p = this.productos.find(x => x.id === this.formOferta.producto_id)
      return p ? Number(p.precio_base_usd) : 0
    },
    precioEfectivoOferta() {
      const base = this.precioBaseProductoOferta
      if (!base) return 0
      if (this.formOferta.tipo_precio === 'porcentaje')
        return base * (1 - Number(this.formOferta.valor || 0) / 100)
      return Number(this.formOferta.valor || 0)
    },

    pasillosFiltrados() {
      if (!this.formUbicacion.area_id) return []
      return this.pasillos.filter(p => p.area_id === Number(this.formUbicacion.area_id))
    },
    estandesFiltrados() {
      if (!this.formUbicacion.pasillo_id) return []
      return this.estantes.filter(e => e.pasillo_id === Number(this.formUbicacion.pasillo_id))
    },
  },

  async mounted() {
    await Promise.all([
      this.cargarProductos(),
      this.cargarTasa(),
      this.cargarDepartamentos(),
      this.cargarProveedores(),
    ])
  },

  methods: {
    // ── Carga inicial ─────────────────────────────────────────────────────────
    async cargarTasa() {
      const r = await axios.get('/tasa/')
      this.tasaBcv     = r.data.tasa
      this.tasaBinance = r.data.tasa_binance
      this.factor      = r.data.factor || 1
    },
    async cargarProductos() {
      const params = {}
      if (this.esAdmin && this.mostrarInactivos) params.incluir_inactivos = true
      const res = await axios.get('/productos/', { params })
      this.productos = res.data
    },
    async cargarDepartamentos() {
      const res = await axios.get('/productos/departamentos')
      this.departamentos = res.data
    },
    async cargarProveedores() {
      try {
        const res = await axios.get('/compras/proveedores/')
        this.proveedores = res.data
      } catch { /* módulo aún no configurado */ }
    },
    async cargarOfertas() {
      const res = await axios.get('/productos/ofertas')
      this.ofertas = res.data
    },

    // ── Utilidades ────────────────────────────────────────────────────────────
    nombreDepartamento(id) {
      if (!id) return '—'
      const d = this.departamentos.find(x => x.id === id)
      return d ? d.nombre : '—'
    },
    actualizarMargen() {
      this.form.margen = Number(this.form.margen_pct || 0) / 100
    },
    formatFecha(s) {
      if (!s) return '—'
      return new Date(s + 'T00:00:00').toLocaleDateString('es-VE')
    },

    // ── Tabs ──────────────────────────────────────────────────────────────────
    async cambiarTabOfertas() {
      this.tabActivo = 'ofertas'
      await this.cargarOfertas()
    },

    // ── CRUD Productos ────────────────────────────────────────────────────────
    abrirNuevoProducto() {
      this.editando    = false
      this.error       = ''
      this.form = {
        id: null, nombre: '', categoria: '', codigo: '',
        departamento_id: null, proveedor_id: null,
        costo_usd: 0, margen: 0.30, margen_pct: 30,
        stock: 0, descripcion: '', foto_url: '',
        es_producto_clave: false, es_producto_compuesto: false,
        descuento_compuesto_pct: 0,
      }
      this.mostrarForm = true
    },
    editar(p) {
      this.form = {
        ...p,
        margen_pct:              Math.round(Number(p.margen) * 100),
        departamento_id:         p.departamento_id         ?? null,
        proveedor_id:            p.proveedor_id            ?? null,
        es_producto_clave:       p.es_producto_clave       ?? false,
        es_producto_compuesto:   p.es_producto_compuesto   ?? false,
        descuento_compuesto_pct: p.descuento_compuesto_pct ?? 0,
      }
      this.editando    = true
      this.error       = ''
      this.mostrarForm = true
    },
    async guardar() {
      if (!this.form.nombre.trim()) { this.error = 'El nombre es obligatorio'; return }
      this.guardando = true; this.error = ''
      try {
        const payload = {
          nombre:                  this.form.nombre,
          categoria:               this.form.categoria      || null,
          descripcion:             this.form.descripcion    || null,
          foto_url:                this.form.foto_url       || '',
          costo_usd:               Number(this.form.costo_usd),
          margen:                  Number(this.form.margen),
          stock:                   Number(this.form.stock),
          departamento_id:         this.form.departamento_id  || null,
          proveedor_id:            this.form.proveedor_id     || null,
          es_producto_clave:       Boolean(this.form.es_producto_clave),
          es_producto_compuesto:   Boolean(this.form.es_producto_compuesto),
          descuento_compuesto_pct: Number(this.form.descuento_compuesto_pct || 0),
          codigo:                  this.form.codigo          || null,
        }
        if (this.editando) {
          await axios.put(`/productos/${this.form.id}`, payload)
        } else {
          await axios.post('/productos/', payload)
        }
        await this.cargarProductos()
        this.cancelar()
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al guardar el producto'
      } finally {
        this.guardando = false
      }
    },
    async eliminar(id) {
      if (!confirm('¿Eliminar este producto?')) return
      try {
        await axios.delete(`/productos/${id}`)
        await this.cargarProductos()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al eliminar')
      }
    },
    cancelar() {
      this.mostrarForm = false
      this.editando    = false
      this.error       = ''
    },

    // ── Estado activo/inactivo ────────────────────────────────────────────────
    async toggleInactivos() {
      this.mostrarInactivos = !this.mostrarInactivos
      await this.cargarProductos()
    },
    async cambiarEstado(producto, estado) {
      const accion = estado ? 'activar' : 'desactivar'
      if (!confirm(`¿${accion.charAt(0).toUpperCase() + accion.slice(1)} "${producto.nombre}"?`)) return
      try {
        await axios.put(`/productos/${producto.id}/estado`, { activo: estado })
        await this.cargarProductos()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al cambiar estado')
      }
    },

    // ── Edición inline de código ─────────────────────────────────────────────
    iniciarEditCodigo(p) {
      if (!this.esAdmin) return
      this.codigoEditando = p.id
      this.codigoTemp     = p.codigo || ''
    },
    async guardarCodigo(p) {
      try {
        await axios.put(`/productos/${p.id}/codigo`, { codigo: this.codigoTemp || null })
        p.codigo = this.codigoTemp || null
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al guardar código')
      } finally {
        this.codigoEditando = null
      }
    },

    // ── CRUD Variantes ────────────────────────────────────────────────────────
    async abrirVariantes(p) {
      this.modalVariantes      = p
      this.mostrarFormVariante = false
      this.editandoVarianteId  = null
      const res = await axios.get(`/productos/${p.id}/variantes`)
      this.variantes = res.data
    },
    cerrarVariantes() {
      this.modalVariantes      = null
      this.mostrarFormVariante = false
      this.editandoVarianteId  = null
    },
    abrirFormVariante() {
      this.editandoVarianteId = null
      this.formVariante = { clase: '', color: '', stock: 0, precio_override_str: '', activo: true }
      this.mostrarFormVariante = true
    },
    editarVariante(v) {
      this.editandoVarianteId = v.id
      this.formVariante = {
        clase:               v.clase,
        color:               v.color || '',
        stock:               v.stock,
        precio_override_str: v.precio_override_usd != null ? String(v.precio_override_usd) : '',
        activo:              v.activo,
      }
      this.mostrarFormVariante = true
    },
    cancelarVariante() {
      this.mostrarFormVariante = false
      this.editandoVarianteId  = null
    },
    async guardarVariante() {
      if (!this.formVariante.clase.trim()) return
      this.guardando = true
      try {
        const payload = {
          clase:               this.formVariante.clase,
          color:               this.formVariante.color || null,
          stock:               Number(this.formVariante.stock || 0),
          precio_override_usd: this.formVariante.precio_override_str
                                 ? Number(this.formVariante.precio_override_str)
                                 : null,
          activo: this.formVariante.activo,
        }
        if (this.editandoVarianteId) {
          await axios.put(`/productos/variantes/${this.editandoVarianteId}`, payload)
        } else {
          await axios.post(`/productos/${this.modalVariantes.id}/variantes`, payload)
        }
        const res = await axios.get(`/productos/${this.modalVariantes.id}/variantes`)
        this.variantes = res.data
        this.cancelarVariante()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al guardar variante')
      } finally {
        this.guardando = false
      }
    },
    async eliminarVariante(id) {
      if (!confirm('¿Eliminar esta variante?')) return
      await axios.delete(`/productos/variantes/${id}`)
      const res = await axios.get(`/productos/${this.modalVariantes.id}/variantes`)
      this.variantes = res.data
    },

    // ── CRUD Componentes ──────────────────────────────────────────────────────
    async abrirComponentes(p) {
      this.modalComponentes = p
      this.formComponente   = { producto_componente_id: '', cantidad: 1 }
      this.errorComp        = ''
      const res = await axios.get(`/productos/${p.id}/componentes`)
      this.componentes = res.data
    },
    cerrarComponentes() {
      this.modalComponentes = null
      this.errorComp        = ''
    },
    async guardarComponente() {
      if (!this.formComponente.producto_componente_id) {
        this.errorComp = 'Selecciona un componente'; return
      }
      this.guardando = true; this.errorComp = ''
      try {
        await axios.post(`/productos/${this.modalComponentes.id}/componentes`, {
          producto_componente_id: Number(this.formComponente.producto_componente_id),
          cantidad:               Number(this.formComponente.cantidad),
        })
        const res = await axios.get(`/productos/${this.modalComponentes.id}/componentes`)
        this.componentes = res.data
        this.formComponente = { producto_componente_id: '', cantidad: 1 }
      } catch (e) {
        this.errorComp = e?.response?.data?.detail || 'Error al agregar componente'
      } finally {
        this.guardando = false
      }
    },
    async eliminarComponente(id) {
      if (!confirm('¿Quitar este componente?')) return
      await axios.delete(`/productos/componentes/${id}`)
      const res = await axios.get(`/productos/${this.modalComponentes.id}/componentes`)
      this.componentes = res.data
    },

    // ── CRUD Ofertas ──────────────────────────────────────────────────────────
    abrirNuevaOferta() {
      this.editandoOfertaId = null
      this.errorOferta      = ''
      const hoy = new Date().toISOString().split('T')[0]
      this.formOferta = {
        producto_id: '', tipo_precio: 'porcentaje',
        valor: 0, fecha_inicio: hoy, fecha_fin: '',
        cantidad_limite_str: '', activo: true,
      }
      this.mostrarFormOferta = true
    },
    editarOferta(o) {
      this.editandoOfertaId = o.id
      this.errorOferta      = ''
      this.formOferta = {
        producto_id:         o.producto_id,
        tipo_precio:         o.tipo_precio,
        valor:               o.valor,
        fecha_inicio:        o.fecha_inicio || '',
        fecha_fin:           o.fecha_fin    || '',
        cantidad_limite_str: o.cantidad_limite != null ? String(o.cantidad_limite) : '',
        activo:              o.activo,
      }
      this.mostrarFormOferta = true
    },
    cerrarOferta() {
      this.mostrarFormOferta = false
      this.editandoOfertaId  = null
      this.errorOferta       = ''
    },
    async guardarOferta() {
      if (!this.formOferta.producto_id)  { this.errorOferta = 'Selecciona un producto'; return }
      if (!this.formOferta.fecha_inicio) { this.errorOferta = 'La fecha de inicio es obligatoria'; return }
      this.guardando = true; this.errorOferta = ''
      try {
        const payload = {
          producto_id:     Number(this.formOferta.producto_id),
          tipo_precio:     this.formOferta.tipo_precio,
          valor:           Number(this.formOferta.valor),
          fecha_inicio:    this.formOferta.fecha_inicio,
          fecha_fin:       this.formOferta.fecha_fin           || null,
          cantidad_limite: this.formOferta.cantidad_limite_str
                             ? Number(this.formOferta.cantidad_limite_str)
                             : null,
          activo: this.formOferta.activo,
        }
        if (this.editandoOfertaId) {
          await axios.put(`/productos/ofertas/${this.editandoOfertaId}`, payload)
        } else {
          await axios.post('/productos/ofertas', payload)
        }
        await this.cargarOfertas()
        this.cerrarOferta()
      } catch (e) {
        this.errorOferta = e?.response?.data?.detail || 'Error al guardar la oferta'
      } finally {
        this.guardando = false
      }
    },
    async eliminarOferta(id) {
      if (!confirm('¿Eliminar esta oferta?')) return
      await axios.delete(`/productos/ofertas/${id}`)
      await this.cargarOfertas()
    },

    // ── CRUD Departamentos ────────────────────────────────────────────────────
    editarDepto(d) {
      this.editandoDeptoId = d.id
      this.formDepto = { nombre: d.nombre, descripcion: d.descripcion || '', activo: d.activo }
    },
    async guardarDepto() {
      if (!this.formDepto.nombre.trim()) return
      await axios.put(`/productos/departamentos/${this.editandoDeptoId}`, this.formDepto)
      await this.cargarDepartamentos()
      this.editandoDeptoId = null
    },
    async crearDepto() {
      if (!this.nuevoDeptoNombre.trim()) return
      await axios.post('/productos/departamentos', { nombre: this.nuevoDeptoNombre, activo: true })
      await this.cargarDepartamentos()
      this.nuevoDeptoNombre = ''
    },
    async eliminarDepto(id) {
      if (!confirm('¿Eliminar este departamento?')) return
      try {
        await axios.delete(`/productos/departamentos/${id}`)
        await this.cargarDepartamentos()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al eliminar')
      }
    },

    // ── Ubicaciones físicas ───────────────────────────────────────────────────
    async abrirUbicaciones(p) {
      this.modalUbicaciones = p
      this.tabUbicacion     = 'ubicaciones'
      this.errorUbicacion   = ''
      this.formUbicacion    = { area_id: '', pasillo_id: '', estante_id: '', nivel: 1, cantidad: 0 }
      await Promise.all([
        this.cargarUbicaciones(p.id),
        this.cargarEstructura(),
      ])
    },
    cerrarUbicaciones() {
      this.modalUbicaciones = null
    },
    async cargarUbicaciones(productoId) {
      const res = await axios.get(`/ubicaciones/producto/${productoId}`)
      this.ubicaciones = res.data
    },
    async cargarEstructura() {
      const [ra, rp, re] = await Promise.all([
        axios.get('/ubicaciones/areas'),
        axios.get('/ubicaciones/pasillos'),
        axios.get('/ubicaciones/estantes'),
      ])
      this.areas    = ra.data
      this.pasillos = rp.data
      this.estantes = re.data
    },
    onAreaChange() {
      this.formUbicacion.pasillo_id = ''
      this.formUbicacion.estante_id = ''
    },
    onPasilloChange() {
      this.formUbicacion.estante_id = ''
    },
    async agregarUbicacion() {
      const f = this.formUbicacion
      if (!f.area_id || !f.pasillo_id || !f.estante_id) {
        this.errorUbicacion = 'Selecciona área, pasillo y estante'; return
      }
      this.guardando = true; this.errorUbicacion = ''
      try {
        await axios.post('/ubicaciones/producto', {
          producto_id: this.modalUbicaciones.id,
          area_id:     Number(f.area_id),
          pasillo_id:  Number(f.pasillo_id),
          estante_id:  Number(f.estante_id),
          nivel:       Number(f.nivel) || 1,
          cantidad:    Number(f.cantidad) || 0,
        })
        await this.cargarUbicaciones(this.modalUbicaciones.id)
        this.formUbicacion = { area_id: '', pasillo_id: '', estante_id: '', nivel: 1, cantidad: 0 }
      } catch (e) {
        this.errorUbicacion = e?.response?.data?.detail || 'Error al agregar ubicación'
      } finally {
        this.guardando = false
      }
    },
    async eliminarUbicacion(id) {
      if (!confirm('¿Quitar esta ubicación?')) return
      await axios.delete(`/ubicaciones/producto/${id}`)
      await this.cargarUbicaciones(this.modalUbicaciones.id)
    },

    // Estructura — áreas
    async crearArea() {
      if (!this.formArea.nombre.trim()) return
      await axios.post('/ubicaciones/areas', { nombre: this.formArea.nombre.trim() })
      this.formArea.nombre = ''
      await this.cargarEstructura()
    },
    async eliminarArea(id) {
      if (!confirm('¿Eliminar esta área?')) return
      await axios.delete(`/ubicaciones/areas/${id}`)
      await this.cargarEstructura()
    },

    // Estructura — pasillos
    async crearPasillo() {
      if (!this.formPasillo.area_id || !this.formPasillo.numero) return
      await axios.post('/ubicaciones/pasillos', { area_id: Number(this.formPasillo.area_id), numero: Number(this.formPasillo.numero) })
      this.formPasillo = { area_id: '', numero: null }
      await this.cargarEstructura()
    },
    async eliminarPasillo(id) {
      if (!confirm('¿Eliminar este pasillo?')) return
      await axios.delete(`/ubicaciones/pasillos/${id}`)
      await this.cargarEstructura()
    },

    // Estructura — estantes
    async crearEstante() {
      if (!this.formEstante.pasillo_id || !this.formEstante.numero) return
      await axios.post('/ubicaciones/estantes', { pasillo_id: Number(this.formEstante.pasillo_id), numero: Number(this.formEstante.numero) })
      this.formEstante = { pasillo_id: '', numero: null }
      await this.cargarEstructura()
    },
    async eliminarEstante(id) {
      if (!confirm('¿Eliminar este estante?')) return
      await axios.delete(`/ubicaciones/estantes/${id}`)
      await this.cargarEstructura()
    },

    // Helpers de nombre
    nombreArea(id) {
      const a = this.areas.find(x => x.id === id)
      return a ? a.nombre : '—'
    },
    numeroPasillo(id) {
      const p = this.pasillos.find(x => x.id === id)
      return p ? p.numero : '—'
    },

    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    },
  },
}
</script>

<style scoped>
/* ── Top bar ── */
.top-acciones { display: flex; gap: 0.6rem; align-items: center; }
.btn-deptos   { background: var(--fondo-sidebar); color: var(--texto-sec); border: 1px solid var(--borde); padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; font-size: 0.88rem; }
.btn-deptos:hover { border-color: var(--amarillo); }

/* ── Tasas bar ── */
.tasas-bar {
  display: flex; gap: 1.5rem; margin-bottom: 1.25rem;
  background: var(--borde-suave); padding: 0.6rem 1.2rem;
  border-radius: 8px; color: var(--texto-sec); font-size: 0.88rem; flex-wrap: wrap;
}
.tasas-bar strong { color: var(--success); font-weight: 700; }

/* ── Tabs ── */
.tabs-nav { display: flex; gap: 0.25rem; margin-bottom: 1.25rem; border-bottom: 2px solid var(--borde); }
.tab-btn  { padding: 0.6rem 1.4rem; background: transparent; color: var(--texto-sec); border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; font-size: 0.9rem; display: flex; align-items: center; gap: 0.4rem; }
.tab-btn:hover { color: var(--texto-principal); }
.tab-activo { color: var(--texto-principal) !important; border-bottom-color: #1A1A1A !important; font-weight: 700; }
.tab-badge { background: var(--amarillo); color: #1A1A1A; font-size: 0.72rem; font-weight: 700; padding: 0.1rem 0.45rem; border-radius: 10px; }

/* ── Filtros ── */
.filtros { display: flex; gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap; }
.buscador { flex: 1; min-width: 200px; }
.filtros select { min-width: 180px; width: auto; }

/* ── Badges en tabla ── */
.prod-nombre { font-weight: 600; margin-right: 0.35rem; }
.badge-clave { background: #FFCC0033; color: #996600; font-size: 0.68rem; font-weight: 800; padding: 0.1rem 0.45rem; border-radius: 4px; margin-right: 0.25rem; text-transform: uppercase; }
.badge-comp  { background: #8888881A; color: #555555; font-size: 0.68rem; font-weight: 800; padding: 0.1rem 0.45rem; border-radius: 4px; text-transform: uppercase; }
.txt-muted   { color: var(--texto-muted); }
.txt-usd     { color: #16A34A; font-weight: 600; }
.txt-rojo    { color: var(--danger); font-weight: 600; }

/* ── Acciones tabla ── */
.acciones     { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.btn-editar   { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.btn-variantes{ background: #1A1A1A; color: #FFCC00; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.btn-comp     { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.btn-eliminar { background: var(--danger);  color: white; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.fila-stock-bajo td { background: #DC262608; }

/* ── Toggle inactivos y estado ── */
.btn-toggle-inactivos { background: var(--fondo-sidebar); color: var(--texto-sec); border: 1px solid var(--borde); padding: 0.45rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; }
.btn-toggle-inactivos.activo { background: #1A1A1A; color: #FFCC00; border-color: #1A1A1A; }
.btn-desactivar { background: #DC26261A; color: #DC2626; border: 1px solid #DC2626; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.btn-activar    { background: #16A34A1A; color: #16A34A; border: 1px solid #16A34A; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.badge-inactivo { background: #DC26261A; color: #DC2626; font-size: 0.68rem; font-weight: 800; padding: 0.1rem 0.45rem; border-radius: 4px; text-transform: uppercase; margin-left: 0.25rem; }

/* ── Código inline ── */
.celda-codigo { min-width: 90px; }
.codigo-tag { font-size: 0.8rem; font-weight: 700; color: #1A1A1A; background: #FFCC0033; padding: 0.15rem 0.45rem; border-radius: 4px; cursor: pointer; white-space: nowrap; }
.codigo-tag:hover { background: var(--amarillo); }
.codigo-edit-wrap { display: flex; align-items: center; gap: 0.25rem; }
.input-codigo { width: 90px; padding: 0.2rem 0.4rem; font-size: 0.8rem; border: 1px solid var(--amarillo); border-radius: 4px; }
.btn-ok-codigo     { background: #16A34A; color: white; border: none; border-radius: 4px; padding: 0.15rem 0.35rem; cursor: pointer; font-size: 0.8rem; }
.btn-cancel-codigo { background: #888; color: white; border: none; border-radius: 4px; padding: 0.15rem 0.35rem; cursor: pointer; font-size: 0.8rem; }

/* ── Modal form producto ── */
.modal-form { max-width: 660px; }
.modal-sm   { max-width: 500px; }

.opciones-especiales { display: flex; flex-direction: column; gap: 0.6rem; margin: 1rem 0; padding: 0.85rem 1rem; background: var(--borde-suave); border-radius: 10px; border: 1px solid var(--borde); }
.check-opt  { display: flex; align-items: flex-start; gap: 0.6rem; cursor: pointer; }
.check-opt input[type="checkbox"] { margin-top: 0.2rem; width: 15px; height: 15px; flex-shrink: 0; accent-color: #1A1A1A; }
.check-label        { display: flex; flex-direction: column; gap: 0.1rem; }
.check-label strong { color: var(--texto-principal); font-size: 0.9rem; }
.check-label small  { color: var(--texto-muted); font-size: 0.8rem; }
.field-dto  { max-width: 260px; margin-top: 0.25rem; }
.field-wide { grid-column: 1 / -1; }

.preview-precios { background: var(--borde-suave); border-radius: 8px; padding: 0.75rem 1rem; margin-top: 1rem; }
.preview-titulo  { color: var(--texto-muted); font-size: 0.8rem; margin: 0 0 0.5rem; font-weight: 600; }
.preview-row     { display: flex; justify-content: space-between; color: var(--texto-sec); font-size: 0.9rem; padding: 0.15rem 0; }

.btn-guardar  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.55rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: 600; }
.btn-guardar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancelar { background: transparent; color: var(--texto-principal); border: 1px solid var(--borde); padding: 0.55rem 1.2rem; border-radius: 6px; cursor: pointer; }

/* ── Modal variantes / componentes ── */
.modal-variantes { max-width: 680px; }
.subform         { background: var(--borde-suave); border-radius: 10px; padding: 1rem; margin-top: 1rem; border: 1px solid var(--borde); }
.subtitulo-subform { color: var(--texto-principal); font-size: 0.88rem; font-weight: 700; margin: 0 0 0.75rem; }
.grid-form-sm  { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.desc-comp     { color: var(--texto-sec); font-size: 0.88rem; margin-bottom: 0.75rem; }

.badge-activa  { background: #16A34A1A; color: #16A34A;  font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 10px; }
.badge-inactiva{ background: #8888881A; color: #555555;  font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: 10px; }

.btn-agregar-linea { background: transparent; border: 1px dashed var(--borde); color: var(--texto-sec); padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; margin-top: 0.75rem; font-size: 0.88rem; width: 100%; }
.btn-agregar-linea:hover { border-color: var(--amarillo); background: #FFCC0011; }

/* ── Tab ofertas ── */
.ofertas-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; }
.ofertas-desc   { color: var(--texto-sec); font-size: 0.88rem; }
.badge-tipo-porcentaje { background: #2563EB1A; color: #2563EB; font-size: 0.75rem; padding: 0.15rem 0.55rem; border-radius: 10px; font-weight: 600; }
.badge-tipo-directo    { background: #16A34A1A; color: #16A34A; font-size: 0.75rem; padding: 0.15rem 0.55rem; border-radius: 10px; font-weight: 600; }

.preview-oferta { display: flex; gap: 0.75rem; align-items: center; background: var(--borde-suave); border-radius: 8px; padding: 0.6rem 0.9rem; margin-top: 0.75rem; flex-wrap: wrap; }
.preview-oferta .preview-titulo { color: var(--texto-sec); font-size: 0.85rem; font-weight: 600; margin: 0; }

/* ── Modal departamentos ── */
.depto-row     { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid var(--borde-suave); gap: 0.75rem; }
.depto-nombre  { color: var(--texto-principal); font-size: 0.9rem; font-weight: 500; }
.depto-input   { flex: 1; padding: 0.35rem 0.6rem; background: #FFFFFF; border: 1px solid var(--amarillo); color: var(--texto-principal); border-radius: 6px; font-size: 0.9rem; }
.depto-acciones{ display: flex; gap: 0.3rem; }
.depto-nuevo   { display: flex; gap: 0.5rem; margin-top: 1rem; }
.depto-input-nuevo { flex: 1; padding: 0.45rem 0.75rem; background: #FFFFFF; border: 1px solid #CCCCCC; color: var(--texto-principal); border-radius: 8px; font-size: 0.9rem; }
.btn-guardar-sm  { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.35rem 0.75rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; font-weight: 700; }
.btn-guardar-sm:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-cancelar-sm { background: transparent; color: var(--danger); border: 1px solid var(--danger); padding: 0.35rem 0.6rem; border-radius: 6px; cursor: pointer; font-size: 0.82rem; }
.txt-verde { color: #16A34A; font-weight: 600; }

/* ── Botón ubicar ── */
.btn-ubicar { background: transparent; border: none; cursor: pointer; font-size: 1rem; padding: 0.15rem 0.3rem; border-radius: 4px; }
.btn-ubicar:hover { background: #FFCC0033; }

/* ── Modal ubicaciones ── */
.modal-ubicaciones { max-width: 700px; }

.ubic-tabs { display: flex; gap: 0.25rem; border-bottom: 2px solid var(--borde); margin-bottom: 1rem; }
.ubic-tab  { padding: 0.5rem 1.1rem; background: transparent; color: var(--texto-sec); border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; font-size: 0.88rem; border-radius: 6px 6px 0 0; }
.ubic-tab:hover { color: var(--texto-principal); }
.ubic-tab-activo { color: var(--texto-principal) !important; border-bottom-color: #1A1A1A !important; font-weight: 700; }

.grid-form-ubic { display: grid; grid-template-columns: 1fr 1fr 1fr 80px 100px; gap: 0.75rem; }

.estructura-seccion { margin-bottom: 1.25rem; padding-bottom: 1rem; border-bottom: 1px solid var(--borde-suave); }
.estructura-seccion:last-child { border-bottom: none; margin-bottom: 0; }
</style>
