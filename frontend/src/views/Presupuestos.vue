<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Presupuestos</h1>
        <button class="btn-nuevo" @click="abrirNuevo">+ Nuevo presupuesto</button>
      </div>

      <div class="contenido-inner">

        <!-- Filtro estado -->
        <div class="filtros">
          <select v-model="filtroEstado" @change="cargar" class="select-filtro">
            <option value="">Todos</option>
            <option value="pendiente">Pendientes</option>
            <option value="aprobado">Aprobados</option>
            <option value="vencido">Vencidos</option>
            <option value="convertido">Convertidos</option>
          </select>
        </div>

        <!-- Tabla -->
        <div class="tabla-container">
          <table>
            <thead>
              <tr>
                <th>Número</th>
                <th>Cliente</th>
                <th>Fecha</th>
                <th>Vence</th>
                <th>Total</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in presupuestos" :key="p.id" :class="p.estado === 'vencido' ? 'fila-vencida' : ''">
                <td class="txt-mono">{{ p.numero }}</td>
                <td>{{ p.cliente_nombre || '— Consumidor Final —' }}</td>
                <td>{{ formatFecha(p.fecha) }}</td>
                <td>{{ formatFecha(p.fecha_vencimiento) }}</td>
                <td class="txt-verde">${{ p.total.toFixed(2) }}</td>
                <td><span :class="['badge-estado', 'badge-' + p.estado]">{{ p.estado }}</span></td>
                <td class="acciones-celda">
                  <button class="btn-ver" @click="verDetalle(p)">Ver</button>
                  <button v-if="p.estado === 'pendiente'" class="btn-aprobar" @click="aprobar(p.id)">Aprobar</button>
                  <button v-if="['pendiente','aprobado'].includes(p.estado)" class="btn-convertir" @click="convertir(p)">→ Venta</button>
                  <button v-if="p.cliente_telefono" class="btn-whatsapp" @click="enviarWhatsapp(p)" title="Enviar por WhatsApp">💬</button>
                </td>
              </tr>
              <tr v-if="presupuestos.length === 0">
                <td colspan="7" class="sin-datos">No hay presupuestos</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Modal nuevo presupuesto -->
        <div class="overlay" v-if="mostrarForm">
          <div class="dialog dialog-grande">
            <h2>Nuevo presupuesto</h2>

            <!-- Cliente -->
            <div class="seccion-form">
              <h3 class="seccion-titulo">Cliente (opcional)</h3>
              <div class="busq-cliente">
                <input v-model="busqCliente" placeholder="Buscar cliente por nombre o teléfono..."
                  @input="buscarClientes" class="inp-full" />
                <div v-if="clientesSugeridos.length" class="sugerencias">
                  <div v-for="c in clientesSugeridos" :key="c.id" class="sugerencia-item"
                    @click="seleccionarCliente(c)">
                    {{ c.nombre }} — {{ c.telefono }}
                  </div>
                </div>
              </div>
              <div v-if="form.cliente_nombre" class="cliente-sel">
                <span>{{ form.cliente_nombre }} ({{ form.cliente_telefono }})</span>
                <button class="btn-quitar-cliente" @click="quitarCliente">✕</button>
              </div>
            </div>

            <!-- Productos -->
            <div class="seccion-form">
              <h3 class="seccion-titulo">Agregar productos</h3>
              <div class="busq-prod">
                <input v-model="busqProducto" placeholder="Buscar producto..." @input="buscarProductos" class="inp-full" />
                <div v-if="productosSugeridos.length" class="sugerencias">
                  <div v-for="p in productosSugeridos" :key="p.id" class="sugerencia-item"
                    @click="agregarProducto(p)">
                    {{ p.nombre }} — ${{ precioProducto(p).toFixed(2) }} (stock: {{ p.stock }})
                  </div>
                </div>
              </div>
            </div>

            <!-- Carrito -->
            <div v-if="carrito.length" class="seccion-form">
              <h3 class="seccion-titulo">Productos</h3>
              <table class="tabla-carrito">
                <thead>
                  <tr><th>Producto</th><th>Precio</th><th>Cant.</th><th>Subtotal</th><th></th></tr>
                </thead>
                <tbody>
                  <tr v-for="(item, i) in carrito" :key="i">
                    <td>{{ item.nombre_producto }}</td>
                    <td>
                      <input class="inp-tabla inp-numero" type="number" min="0" step="0.01"
                        v-model.number="item.precio_unitario" @input="recalcular" />
                    </td>
                    <td>
                      <input class="inp-tabla inp-numero" type="number" min="1" step="1"
                        v-model.number="item.cantidad" @input="recalcular" />
                    </td>
                    <td class="txt-verde">${{ (item.precio_unitario * item.cantidad).toFixed(2) }}</td>
                    <td><button class="btn-quitar" @click="quitarItem(i)">✕</button></td>
                  </tr>
                </tbody>
              </table>

              <div class="totales-form">
                <div class="total-row">
                  <span>Subtotal:</span><span>${{ subtotalForm.toFixed(2) }}</span>
                </div>
                <div class="total-row">
                  <span>Descuento:</span>
                  <input class="inp-tabla inp-numero" type="number" min="0" step="0.01"
                    v-model.number="form.descuento" @input="recalcular" />
                </div>
                <div class="total-row total-final">
                  <span>Total:</span><span>${{ totalForm.toFixed(2) }}</span>
                </div>
              </div>
            </div>

            <!-- Moneda y observación -->
            <div class="grid-form">
              <div class="field">
                <label>Moneda</label>
                <select v-model="form.moneda">
                  <option value="USD">USD</option>
                  <option value="Bs">Bolívares</option>
                </select>
              </div>
              <div class="field full">
                <label>Observación</label>
                <input v-model="form.observacion" placeholder="Opcional..." />
              </div>
            </div>

            <div class="form-botones">
              <button class="btn-cancelar" @click="cerrarForm">Cancelar</button>
              <button class="btn-guardar" @click="guardar" :disabled="carrito.length === 0">Guardar presupuesto</button>
            </div>
          </div>
        </div>

        <!-- Modal detalle -->
        <div class="overlay" v-if="detalle">
          <div class="dialog dialog-grande">
            <div class="detalle-header">
              <div>
                <h2>{{ detalle.numero }}</h2>
                <p class="detalle-sub">
                  Cliente: {{ detalle.cliente_nombre || 'Consumidor Final' }}
                  &nbsp;·&nbsp; {{ formatFecha(detalle.fecha) }}
                  &nbsp;·&nbsp; Vence: {{ formatFecha(detalle.fecha_vencimiento) }}
                </p>
              </div>
              <span :class="['badge-estado', 'badge-' + detalle.estado]">{{ detalle.estado }}</span>
              <button class="btn-cerrar-x" @click="detalle = null">✕</button>
            </div>

            <table class="tabla-carrito">
              <thead>
                <tr><th>Producto</th><th>Cant.</th><th>Precio</th><th>Subtotal</th></tr>
              </thead>
              <tbody>
                <tr v-for="(p, i) in detalle.productos" :key="i">
                  <td>{{ p.nombre_producto }}</td>
                  <td>{{ p.cantidad }}</td>
                  <td>${{ p.precio_unitario.toFixed(2) }}</td>
                  <td class="txt-verde">${{ p.subtotal.toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>

            <div class="totales-form">
              <div class="total-row"><span>Subtotal:</span><span>${{ detalle.subtotal.toFixed(2) }}</span></div>
              <div class="total-row"><span>Descuento:</span><span>${{ detalle.descuento.toFixed(2) }}</span></div>
              <div class="total-row total-final"><span>Total:</span><span>${{ detalle.total.toFixed(2) }}</span></div>
            </div>

            <div v-if="detalle.observacion" class="obs-box">{{ detalle.observacion }}</div>

            <div class="form-botones">
              <button class="btn-cancelar" @click="detalle = null">Cerrar</button>
              <button v-if="detalle.cliente_telefono" class="btn-whatsapp" @click="enviarWhatsapp(detalle)">💬 WhatsApp</button>
            </div>
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
  name: 'Presupuestos',
  data() {
    return {
      usuario:            JSON.parse(localStorage.getItem('usuario') || '{}'),
      presupuestos:       [],
      filtroEstado:       '',
      mostrarForm:        false,
      detalle:            null,
      error:              '',
      busqCliente:        '',
      clientesSugeridos:  [],
      busqProducto:       '',
      productosSugeridos: [],
      carrito:            [],
      form: {
        cliente_id:       null,
        cliente_nombre:   '',
        cliente_telefono: '',
        descuento:        0,
        moneda:           'USD',
        observacion:      '',
      },
    }
  },
  computed: {
    esAdmin()      { return this.usuario.rol === 'admin' },
    tienePermiso() {
      return (modulo) => {
        if (this.usuario.rol === 'admin') return true
        const p = this.usuario.permisos
        if (p == null) return true
        return Array.isArray(p) ? p.includes(modulo) : true
      }
    },
    subtotalForm() {
      return this.carrito.reduce((s, i) => s + i.precio_unitario * i.cantidad, 0)
    },
    totalForm() {
      return Math.max(0, this.subtotalForm - (this.form.descuento || 0))
    },
  },
  async mounted() {
    await this.cargar()
  },
  methods: {
    async cargar() {
      try {
        const params = {}
        if (this.filtroEstado) params.estado = this.filtroEstado
        const res = await axios.get('/presupuestos/', { params })
        this.presupuestos = res.data
      } catch (e) {
        this.error = 'Error al cargar presupuestos'
      }
    },

    abrirNuevo() {
      this.carrito            = []
      this.busqCliente        = ''
      this.busqProducto       = ''
      this.clientesSugeridos  = []
      this.productosSugeridos = []
      this.form = { cliente_id: null, cliente_nombre: '', cliente_telefono: '', descuento: 0, moneda: 'USD', observacion: '' }
      this.mostrarForm = true
    },
    cerrarForm() { this.mostrarForm = false },

    async buscarClientes() {
      if (!this.busqCliente || this.busqCliente.length < 2) { this.clientesSugeridos = []; return }
      const res = await axios.get('/clientes/', { params: { buscar: this.busqCliente } })
      this.clientesSugeridos = res.data.slice(0, 6)
    },
    seleccionarCliente(c) {
      this.form.cliente_id       = c.id
      this.form.cliente_nombre   = c.nombre
      this.form.cliente_telefono = c.telefono
      this.busqCliente           = ''
      this.clientesSugeridos     = []
    },
    quitarCliente() {
      this.form.cliente_id = null; this.form.cliente_nombre = ''; this.form.cliente_telefono = ''
    },

    async buscarProductos() {
      if (!this.busqProducto || this.busqProducto.length < 2) { this.productosSugeridos = []; return }
      const res = await axios.get('/productos/', { params: { busqueda: this.busqProducto, limit: 8 } })
      this.productosSugeridos = Array.isArray(res.data) ? res.data : (res.data.productos || [])
    },
    precioProducto(p) {
      return parseFloat(p.costo_usd || 0) * (1 + parseFloat(p.margen || 0.30))
    },
    agregarProducto(p) {
      const existe = this.carrito.find(i => i.producto_id === p.id)
      if (existe) { existe.cantidad++; } else {
        this.carrito.push({
          producto_id:     p.id,
          nombre_producto: p.nombre,
          precio_unitario: parseFloat(this.precioProducto(p).toFixed(2)),
          cantidad:        1,
        })
      }
      this.busqProducto       = ''
      this.productosSugeridos = []
    },
    quitarItem(i)  { this.carrito.splice(i, 1) },
    recalcular()   { /* reactivo via computed */ },

    async guardar() {
      if (!this.carrito.length) return
      this.error = ''
      try {
        await axios.post('/presupuestos/', {
          ...this.form,
          usuario:   this.usuario.usuario || 'admin',
          productos: this.carrito,
        })
        this.cerrarForm()
        await this.cargar()
      } catch (e) {
        this.error = e?.response?.data?.detail || 'Error al guardar'
      }
    },

    async aprobar(id) {
      try {
        await axios.put(`/presupuestos/${id}/aprobar`)
        await this.cargar()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al aprobar')
      }
    },

    async convertir(p) {
      if (!confirm(`¿Convertir ${p.numero} a venta?`)) return
      try {
        const res = await axios.post(`/presupuestos/${p.id}/convertir`, {
          usuario: this.usuario.usuario || 'admin',
        })
        alert(`Venta creada con ID: ${res.data.venta_id}`)
        await this.cargar()
      } catch (e) {
        alert(e?.response?.data?.detail || 'Error al convertir')
      }
    },

    verDetalle(p) { this.detalle = p },

    enviarWhatsapp(p) {
      const numero   = (p.cliente_telefono || '').replace(/\D/g, '')
      const intl     = '58' + numero.slice(1)
      const lista    = p.productos.map(i => `• ${i.nombre_producto} x${i.cantidad} = $${i.subtotal.toFixed(2)}`).join('\n')
      const mensaje  = `Estimado/a ${p.cliente_nombre || 'cliente'}, le enviamos su presupuesto *${p.numero}* por un total de *$${p.total.toFixed(2)} ${p.moneda}*, válido por 24 horas.\n\n${lista}\n\nGracias por preferirnos — Ferreutil`
      window.open(`https://wa.me/${intl}?text=${encodeURIComponent(mensaje)}`, '_blank')
    },

    formatFecha(iso) {
      if (!iso) return '—'
      return new Date(iso).toLocaleString('es-VE', { dateStyle: 'short', timeStyle: 'short' })
    },
    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    },
  },
}
</script>

<style scoped>
.select-filtro { padding: 0.4rem 0.75rem; border: 1px solid var(--borde); border-radius: 6px; background: #fff; font-size: 0.88rem; }

.txt-mono { font-family: monospace; font-weight: 600; color: var(--texto-principal); }

/* Estado badges */
.badge-estado      { display: inline-block; padding: 0.2rem 0.65rem; border-radius: 20px; font-size: 0.78rem; font-weight: 700; }
.badge-pendiente   { background: #FFCC0033; color: #996600; border: 1px solid #FFCC00; }
.badge-aprobado    { background: #16A34A1A; color: #16A34A; border: 1px solid #16A34A; }
.badge-vencido     { background: #DC26261A; color: #DC2626; border: 1px solid #DC2626; }
.badge-convertido  { background: #8888881A; color: #555555; border: 1px solid #AAAAAA; }

.fila-vencida td { background: #DC262608; }

/* Acciones */
.acciones-celda { display: flex; gap: 0.3rem; align-items: center; flex-wrap: wrap; }
.btn-ver       { background: #F5F5F0; color: #1A1A1A; border: 1px solid #DDD; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.btn-aprobar   { background: #16A34A; color: white; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }
.btn-convertir { background: #1A1A1A; color: #FFCC00; border: none; padding: 0.25rem 0.6rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; font-weight: 700; }
.btn-whatsapp  { background: #25D366; color: white; border: none; padding: 0.25rem 0.55rem; border-radius: 5px; cursor: pointer; font-size: 0.78rem; }

/* Dialog grande */
.dialog-grande { max-width: 740px; }

/* Formulario */
.seccion-form      { margin-bottom: 1.25rem; }
.busq-cliente, .busq-prod { position: relative; }
.inp-full          { width: 100%; padding: 0.45rem 0.75rem; border: 1px solid var(--borde); border-radius: 6px; font-size: 0.88rem; box-sizing: border-box; }
.sugerencias       { position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid var(--borde); border-radius: 6px; z-index: 100; max-height: 200px; overflow-y: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.sugerencia-item   { padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.85rem; color: var(--texto-sec); }
.sugerencia-item:hover { background: #FAFAF7; }
.cliente-sel       { display: flex; align-items: center; gap: 0.5rem; background: #FAFAF7; border: 1px solid var(--borde); border-radius: 6px; padding: 0.45rem 0.75rem; font-size: 0.85rem; color: var(--texto-sec); margin-top: 0.5rem; }
.btn-quitar-cliente{ background: transparent; border: none; color: #DC2626; cursor: pointer; font-size: 1rem; margin-left: auto; }

/* Tabla carrito */
.tabla-carrito     { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 0.5rem; }
.tabla-carrito th  { text-align: left; padding: 0.4rem 0.5rem; color: var(--texto-muted); font-weight: 600; border-bottom: 1px solid var(--borde); }
.tabla-carrito td  { padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--borde-suave); }
.btn-quitar        { background: transparent; border: none; color: #DC2626; cursor: pointer; font-size: 0.9rem; }

/* Totales */
.totales-form  { margin-top: 1rem; display: flex; flex-direction: column; align-items: flex-end; gap: 0.4rem; }
.total-row     { display: flex; gap: 2rem; align-items: center; font-size: 0.88rem; color: var(--texto-sec); }
.total-final   { font-weight: 700; font-size: 1rem; color: var(--texto-principal); }

/* Detalle */
.detalle-header { display: flex; gap: 1rem; align-items: flex-start; margin-bottom: 1.25rem; flex-wrap: wrap; }
.detalle-header h2 { color: var(--texto-principal); margin: 0 0 0.25rem; }
.detalle-sub    { color: var(--texto-muted); font-size: 0.82rem; margin: 0; }
.btn-cerrar-x   { margin-left: auto; background: transparent; color: var(--texto-muted); border: none; font-size: 1.2rem; cursor: pointer; }
.obs-box        { background: #FAFAF7; border: 1px solid var(--borde); border-radius: 6px; padding: 0.6rem 0.9rem; font-size: 0.85rem; color: var(--texto-sec); margin-top: 1rem; }
</style>
