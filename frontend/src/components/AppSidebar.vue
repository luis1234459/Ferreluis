<template>
  <button class="btn-menu-movil" @click="abrirMenu">☰</button>
  <div class="sidebar-overlay" :class="{ visible: menuAbierto }" @click="cerrarMenu"></div>
  <aside class="sidebar" :class="{ abierto: menuAbierto }">
    <div class="logo"><h2>Ferreutil</h2></div>
    <nav>

      <!-- Dashboard — siempre visible, sin grupo -->
      <router-link to="/dashboard">Dashboard</router-link>

      <!-- Grupos colapsables -->
      <div v-for="g in gruposVisibles" :key="g.key" class="nav-grupo">
        <button type="button" class="grupo-header" @click="toggleGrupo(g.key)">
          <span class="grupo-icono">{{ g.icono }}</span>
          <span class="grupo-nombre">{{ g.nombre }}</span>
          <span class="grupo-flecha">{{ abiertos[g.key] ? '▼' : '▶' }}</span>
        </button>
        <div
          class="grupo-links"
          :style="{ maxHeight: abiertos[g.key] ? '400px' : '0px' }"
        >
          <router-link
            v-for="item in itemsVisibles(g)"
            :key="item.ruta"
            :to="item.ruta"
            @click="cerrarMenu"
          >{{ item.label }}</router-link>
        </div>
      </div>

    </nav>
    <div class="user-info">
      <p>{{ usuario.usuario }}</p>
      <span>{{ usuario.rol }}</span>
      <button @click="salir">Salir</button>
    </div>
  </aside>
</template>

<script>
const GRUPOS = [
  {
    key: 'inventario',
    icono: '📦',
    nombre: 'Inventario',
    rutas: ['/inventario', '/ajustes'],
    items: [
      { ruta: '/inventario',          label: 'Inventario',     permiso: 'inventario' },
      { ruta: '/inventario/importar', label: 'Importar Excel', soloAdmin: true },
      { ruta: '/ajustes',             label: 'Ajustes',        soloAdmin: true },
    ],
  },
  {
    key: 'ventas',
    icono: '💰',
    nombre: 'Ventas',
    rutas: ['/ventas', '/presupuestos', '/devoluciones', '/cierre', '/tasa'],
    items: [
      { ruta: '/ventas',       label: 'Ventas',         siempre: true },
      { ruta: '/presupuestos', label: 'Presupuestos',   permiso: 'presupuestos' },
      { ruta: '/devoluciones', label: 'Devoluciones',   permiso: 'devoluciones' },
      { ruta: '/cierre',       label: 'Cierre de caja', permiso: 'cierre' },
      { ruta: '/tasa',         label: 'Tasa BCV',        siempre: true },
    ],
  },
  {
    key: 'depositos',
    icono: '🧾',
    nombre: 'Facturación',
    rutas: ['/depositos'],
    items: [
      { ruta: '/depositos', label: 'Depósitos', soloAdmin: true },
    ],
  },
  {
    key: 'clientes',
    icono: '👥',
    nombre: 'Clientes',
    rutas: ['/clientes', '/fidelidad', '/creditos'],
    items: [
      { ruta: '/clientes',  label: 'Clientes',  siempre: true },
      { ruta: '/fidelidad', label: 'Fidelidad', siempre: true },
      { ruta: '/creditos',  label: 'Créditos',  permiso: 'creditos' },
    ],
  },
  {
    key: 'compras',
    icono: '🛒',
    nombre: 'Compras',
    rutas: ['/compras', '/compras/escanear', '/compras/catalogo', '/compras/ordenes', '/compras/recibir', '/compras/proveedores'],
    items: [
      { ruta: '/compras',              label: 'Compras',      permiso: 'compras'      },
      { ruta: '/compras/escanear',     label: 'Factura IA',   permiso: 'compras'      },
      { ruta: '/compras/catalogo',     label: 'Catálogo IA',  permiso: 'compras'      },
      { ruta: '/compras/ordenes',      label: 'Órdenes',      permiso: 'compras'      },
      { ruta: '/compras/recibir',      label: 'Recibir',      permiso: 'compras'      },
      { ruta: '/compras/proveedores',  label: 'Proveedores',  permiso: 'proveedores'  },
    ],
  },
  {
    key: 'vendedores',
    icono: '👨‍💼',
    nombre: 'Vendedores',
    rutas: ['/vendedores', '/mi-comision'],
    items: [
      { ruta: '/vendedores',  label: 'Comisiones',  permiso: 'vendedores' },
      { ruta: '/mi-comision', label: 'Mi Comisión', siempre: true },
    ],
  },
  {
    key: 'finanzas',
    icono: '🏦',
    nombre: 'Finanzas',
    rutas: ['/bancos/cuentas', '/bancos/movimientos', '/bancos/proveedores'],
    items: [
      { ruta: '/bancos/cuentas',     label: 'Cuentas y Saldos', soloAdmin: true },
      { ruta: '/bancos/movimientos', label: 'Movimientos',       soloAdmin: true },
      { ruta: '/bancos/proveedores', label: 'Pagos Proveedores', soloAdmin: true },
    ],
  },
  {
    key: 'reportes',
    icono: '📊',
    nombre: 'Reportes',
    rutas: ['/reportes'],
    items: [
      { ruta: '/reportes', label: 'Reportes', soloAdmin: true },
    ],
  },
  {
    key: 'comunicacion',
    icono: '📢',
    nombre: 'Comunicación',
    rutas: ['/avisos'],
    items: [
      { ruta: '/avisos', label: 'Avisos', siempre: true },
    ],
  },
  {
    key: 'admin',
    icono: '⚙️',
    nombre: 'Admin',
    rutas: ['/usuarios', '/configuracion', '/radar-demanda'],
    items: [
      { ruta: '/usuarios',                       label: 'Usuarios',       soloAdmin: true },
      { ruta: '/radar-demanda',                  label: 'Radar Demanda',  soloAdmin: true },
      { ruta: '/configuracion/claves',          label: 'Claves Auth',    soloAdmin: true },
      { ruta: '/configuracion/garantias',       label: 'Garantías',      soloAdmin: true },
      { ruta: '/configuracion/mantenimiento',   label: 'Mantenimiento',  soloAdmin: true },
    ],
  },
]

export default {
  name: 'AppSidebar',
  data() {
    const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
    const saved   = JSON.parse(localStorage.getItem('sidebar_grupos') || '{}')
    const ruta    = window.location.pathname
    const abiertos = {}
    for (const g of GRUPOS) {
      const tieneActiva = g.rutas.some(r => ruta === r || ruta.startsWith(r + '/'))
      abiertos[g.key] = tieneActiva
        ? true
        : (saved[g.key] !== undefined ? saved[g.key] : false)
    }
    return { usuario, abiertos, menuAbierto: false }
  },
  computed: {
    esAdmin() {
      return this.usuario.rol === 'admin'
    },
    gruposVisibles() {
      return GRUPOS.filter(g => this.itemsVisibles(g).length > 0)
    },
  },
  watch: {
    $route(to) {
      this.menuAbierto = false
      for (const g of GRUPOS) {
        const tieneActiva = g.rutas.some(r => to.path === r || to.path.startsWith(r + '/'))
        if (tieneActiva && !this.abiertos[g.key]) {
          this.abiertos[g.key] = true
          this._guardar()
        }
      }
    },
  },
  methods: {
    tienePermiso(modulo) {
      if (this.esAdmin) return true
      const p = this.usuario.permisos
      if (p == null) return true
      return Array.isArray(p) ? p.includes(modulo) : true
    },
    itemVisible(item) {
      if (item.soloAdmin) return this.esAdmin
      if (item.siempre)   return true
      if (item.permiso)   return this.tienePermiso(item.permiso)
      return true
    },
    itemsVisibles(grupo) {
      return grupo.items.filter(i => this.itemVisible(i))
    },
    toggleGrupo(key) {
      this.abiertos[key] = !this.abiertos[key]
      this._guardar()
    },
    _guardar() {
      localStorage.setItem('sidebar_grupos', JSON.stringify({ ...this.abiertos }))
    },
    abrirMenu()  { this.menuAbierto = true },
    cerrarMenu() { this.menuAbierto = false },
    salir() {
      localStorage.removeItem('usuario')
      this.$router.push('/login')
    },
  },
}
</script>

<style scoped>
/* Grupos colapsables */
.nav-grupo {
  display: flex;
  flex-direction: column;
}

.grupo-header {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 0.85rem;
  background: transparent;
  border: none;
  cursor: pointer;
  width: 100%;
  text-align: left;
  border-radius: 6px;
  transition: background 0.15s;
}
.grupo-header:hover {
  background: #EBEBEB;
}

.grupo-icono {
  font-size: 0.88rem;
  flex-shrink: 0;
  line-height: 1;
}
.grupo-nombre {
  flex: 1;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--texto-muted);
  letter-spacing: 0.04em;
}
.grupo-flecha {
  font-size: 0.65rem;
  color: var(--texto-muted);
  margin-left: auto;
}

/* Contenedor de links — transición max-height */
.grupo-links {
  overflow: hidden;
  transition: max-height 0.25s ease;
  display: flex;
  flex-direction: column;
}

/* Links dentro del grupo — indentación */
.grupo-links a {
  padding-left: 2.1rem !important;
  border-radius: 6px;
}
</style>
