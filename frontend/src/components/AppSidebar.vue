<template>
  <button class="btn-menu-movil" @click="abrirMenu">☰</button>
  <div class="sidebar-overlay" :class="{ visible: menuAbierto }" @click="cerrarMenu"></div>
  <aside class="sidebar" :class="{ abierto: menuAbierto }">
    <!-- Blueprint background SVG -->
    <svg class="sidebar-blueprint" viewBox="0 0 220 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <pattern id="bp-grid" width="25" height="25" patternUnits="userSpaceOnUse">
          <line x1="25" y1="0" x2="25" y2="25" stroke="#2A5A8C" stroke-width="0.3" opacity="0.3"/>
          <line x1="0" y1="25" x2="25" y2="25" stroke="#2A5A8C" stroke-width="0.3" opacity="0.3"/>
        </pattern>
        <pattern id="bp-sub" width="5" height="5" patternUnits="userSpaceOnUse">
          <line x1="5" y1="0" x2="5" y2="5" stroke="#2A5A8C" stroke-width="0.15" opacity="0.15"/>
          <line x1="0" y1="5" x2="5" y2="5" stroke="#2A5A8C" stroke-width="0.15" opacity="0.15"/>
        </pattern>
      </defs>
      <rect width="220" height="900" fill="url(#bp-sub)"/>
      <rect width="220" height="900" fill="url(#bp-grid)"/>
      <g opacity="0.12">
        <line x1="15" y1="115" x2="55" y2="115" stroke="#5DADE2" stroke-width="0.7"/>
        <line x1="15" y1="115" x2="15" y2="155" stroke="#5DADE2" stroke-width="0.7"/>
        <line x1="55" y1="115" x2="15" y2="155" stroke="#5DADE2" stroke-width="0.7"/>
        <rect x="15" y="107" width="8" height="8" fill="none" stroke="#5DADE2" stroke-width="0.4"/>
        <text x="33" y="112" fill="#5DADE2" font-family="monospace" font-size="6">3</text>
        <text x="6" y="138" fill="#5DADE2" font-family="monospace" font-size="6">4</text>
        <text x="30" y="140" fill="#5DADE2" font-family="monospace" font-size="6">5</text>
      </g>
      <g opacity="0.1">
        <text x="130" y="125" fill="#5DADE2" font-family="monospace" font-size="7">M = F × d</text>
        <text x="130" y="135" fill="#5DADE2" font-family="monospace" font-size="6">σ = F / A</text>
      </g>
      <g opacity="0.12" transform="translate(140,165)">
        <line x1="0" y1="0" x2="40" y2="0" stroke="#5DADE2" stroke-width="1"/>
        <line x1="0" y1="30" x2="40" y2="30" stroke="#5DADE2" stroke-width="1"/>
        <line x1="18" y1="0" x2="18" y2="30" stroke="#5DADE2" stroke-width="0.6"/>
        <line x1="22" y1="0" x2="22" y2="30" stroke="#5DADE2" stroke-width="0.6"/>
        <text x="-3" y="19" fill="#5DADE2" font-family="monospace" font-size="5" text-anchor="end">IPE</text>
        <text x="-3" y="25" fill="#5DADE2" font-family="monospace" font-size="5" text-anchor="end">200</text>
      </g>
      <g opacity="0.12">
        <line x1="15" y1="230" x2="95" y2="230" stroke="#5DADE2" stroke-width="0.5"/>
        <line x1="15" y1="228" x2="15" y2="232" stroke="#5DADE2" stroke-width="0.5"/>
        <line x1="95" y1="228" x2="95" y2="232" stroke="#5DADE2" stroke-width="0.5"/>
        <text x="55" y="227" fill="#5DADE2" font-family="monospace" font-size="6" text-anchor="middle">120.00 ±0.05</text>
      </g>
      <g opacity="0.1">
        <circle cx="50" cy="300" r="22" fill="none" stroke="#5DADE2" stroke-width="0.5"/>
        <circle cx="50" cy="300" r="14" fill="none" stroke="#5DADE2" stroke-width="0.4" stroke-dasharray="2,2"/>
        <line x1="50" y1="278" x2="50" y2="322" stroke="#5DADE2" stroke-width="0.3"/>
        <line x1="28" y1="300" x2="72" y2="300" stroke="#5DADE2" stroke-width="0.3"/>
        <circle cx="50" cy="300" r="1.5" fill="#5DADE2"/>
        <text x="50" y="330" fill="#5DADE2" font-family="monospace" font-size="5.5" text-anchor="middle">R22 / R14</text>
      </g>
      <g opacity="0.1" transform="translate(140,290)">
        <path d="M 0 30 A 30 30 0 0 1 30 0" fill="none" stroke="#5DADE2" stroke-width="0.5"/>
        <line x1="0" y1="30" x2="35" y2="30" stroke="#5DADE2" stroke-width="0.4"/>
        <line x1="0" y1="30" x2="21" y2="9" stroke="#5DADE2" stroke-width="0.4"/>
        <text x="18" y="25" fill="#5DADE2" font-family="monospace" font-size="6">45°</text>
      </g>
      <g opacity="0.12">
        <line x1="15" y1="380" x2="105" y2="380" stroke="#5DADE2" stroke-width="0.5"/>
        <line x1="15" y1="377" x2="15" y2="383" stroke="#5DADE2" stroke-width="0.5"/>
        <line x1="35" y1="377" x2="35" y2="383" stroke="#5DADE2" stroke-width="0.5"/>
        <line x1="55" y1="377" x2="55" y2="383" stroke="#5DADE2" stroke-width="0.5"/>
        <line x1="75" y1="377" x2="75" y2="383" stroke="#5DADE2" stroke-width="0.5"/>
        <line x1="105" y1="377" x2="105" y2="383" stroke="#5DADE2" stroke-width="0.5"/>
        <rect x="15" y="378" width="20" height="4" fill="#5DADE2" opacity="0.3"/>
        <rect x="55" y="378" width="20" height="4" fill="#5DADE2" opacity="0.3"/>
        <text x="15" y="393" fill="#5DADE2" font-family="monospace" font-size="5">0</text>
        <text x="53" y="393" fill="#5DADE2" font-family="monospace" font-size="5">2m</text>
        <text x="93" y="393" fill="#5DADE2" font-family="monospace" font-size="5">4m</text>
      </g>
      <g opacity="0.1">
        <line x1="180" y1="370" x2="180" y2="420" stroke="#5DADE2" stroke-width="0.5" stroke-dasharray="1,2"/>
        <circle cx="180" cy="423" r="3" fill="none" stroke="#5DADE2" stroke-width="0.5"/>
        <circle cx="180" cy="423" r="1" fill="#5DADE2"/>
        <line x1="170" y1="370" x2="190" y2="370" stroke="#5DADE2" stroke-width="0.5"/>
      </g>
      <g opacity="0.1" transform="translate(110,415)">
        <line x1="0" y1="15" x2="15" y2="15" stroke="#5DADE2" stroke-width="0.5"/>
        <circle cx="20" cy="15" r="5" fill="none" stroke="#5DADE2" stroke-width="0.5"/>
        <text x="20" y="17" fill="#5DADE2" font-family="monospace" font-size="5" text-anchor="middle">R</text>
        <line x1="25" y1="15" x2="40" y2="15" stroke="#5DADE2" stroke-width="0.5"/>
        <line x1="40" y1="10" x2="40" y2="20" stroke="#5DADE2" stroke-width="0.5"/>
        <line x1="44" y1="12" x2="44" y2="18" stroke="#5DADE2" stroke-width="0.5"/>
        <text x="27" y="28" fill="#5DADE2" font-family="monospace" font-size="5">V=I×R</text>
      </g>
      <g opacity="0.14">
        <rect x="25" y="490" width="170" height="110" fill="none" stroke="#5DADE2" stroke-width="1"/>
        <line x1="25" y1="540" x2="120" y2="540" stroke="#5DADE2" stroke-width="0.7"/>
        <line x1="120" y1="490" x2="120" y2="600" stroke="#5DADE2" stroke-width="0.7"/>
        <line x1="120" y1="550" x2="195" y2="550" stroke="#5DADE2" stroke-width="0.6"/>
        <line x1="60" y1="600" x2="87" y2="600" stroke="#0C2340" stroke-width="2.5"/>
        <path d="M 60 600 A 27 27 0 0 1 87 600" fill="none" stroke="#5DADE2" stroke-width="0.5" stroke-dasharray="2,2"/>
        <line x1="120" y1="560" x2="120" y2="580" stroke="#0C2340" stroke-width="2"/>
        <path d="M 120 560 A 20 20 0 0 0 140 560" fill="none" stroke="#5DADE2" stroke-width="0.4"/>
        <line x1="120" y1="505" x2="120" y2="525" stroke="#0C2340" stroke-width="2"/>
        <path d="M 120 525 A 20 20 0 0 1 140 525" fill="none" stroke="#5DADE2" stroke-width="0.4"/>
        <rect x="30" y="545" width="18" height="14" rx="1" fill="none" stroke="#5DADE2" stroke-width="0.5"/>
        <circle cx="35" cy="552" r="2.5" fill="none" stroke="#5DADE2" stroke-width="0.3"/>
        <circle cx="42" cy="552" r="2.5" fill="none" stroke="#5DADE2" stroke-width="0.3"/>
        <circle cx="35" cy="556" r="2.5" fill="none" stroke="#5DADE2" stroke-width="0.3"/>
        <circle cx="42" cy="556" r="2.5" fill="none" stroke="#5DADE2" stroke-width="0.3"/>
        <rect x="55" y="546" width="12" height="9" rx="2" fill="none" stroke="#5DADE2" stroke-width="0.4"/>
        <rect x="126" y="495" width="8" height="6" rx="1" fill="none" stroke="#5DADE2" stroke-width="0.4"/>
        <ellipse cx="130" cy="510" rx="5" ry="7" fill="none" stroke="#5DADE2" stroke-width="0.4"/>
        <rect x="155" y="575" width="30" height="5" fill="none" stroke="#5DADE2" stroke-width="0.3" stroke-dasharray="2,1"/>
        <text x="60" y="522" fill="#5DADE2" font-family="monospace" font-size="7" text-anchor="middle">SALA</text>
        <text x="60" y="578" fill="#5DADE2" font-family="monospace" font-size="6" text-anchor="middle">COCINA</text>
        <text x="145" y="518" fill="#5DADE2" font-family="monospace" font-size="6" text-anchor="middle">BAÑO</text>
        <text x="157" y="568" fill="#5DADE2" font-family="monospace" font-size="6" text-anchor="middle">HAB. PPAL</text>
        <line x1="186" y1="608" x2="186" y2="620" stroke="#5DADE2" stroke-width="0.5"/>
        <polygon points="186,604 183,611 189,611" fill="#5DADE2"/>
        <text x="186" y="628" fill="#5DADE2" font-family="monospace" font-size="6" text-anchor="middle">N</text>
        <line x1="25" y1="615" x2="195" y2="615" stroke="#5DADE2" stroke-width="0.4"/>
        <line x1="25" y1="613" x2="25" y2="617" stroke="#5DADE2" stroke-width="0.4"/>
        <line x1="195" y1="613" x2="195" y2="617" stroke="#5DADE2" stroke-width="0.4"/>
        <text x="110" y="625" fill="#5DADE2" font-family="monospace" font-size="6" text-anchor="middle">8.50 m</text>
        <line x1="15" y1="490" x2="15" y2="600" stroke="#5DADE2" stroke-width="0.4"/>
        <line x1="13" y1="490" x2="17" y2="490" stroke="#5DADE2" stroke-width="0.4"/>
        <line x1="13" y1="600" x2="17" y2="600" stroke="#5DADE2" stroke-width="0.4"/>
        <text x="10" y="550" fill="#5DADE2" font-family="monospace" font-size="6" text-anchor="middle" transform="rotate(-90,10,550)">5.80 m</text>
      </g>
      <g opacity="0.15">
        <rect x="20" y="645" width="180" height="32" fill="none" stroke="#5DADE2" stroke-width="0.6"/>
        <line x1="100" y1="645" x2="100" y2="677" stroke="#5DADE2" stroke-width="0.4"/>
        <line x1="20" y1="661" x2="100" y2="661" stroke="#5DADE2" stroke-width="0.4"/>
        <text x="60" y="656" fill="#5DADE2" font-family="monospace" font-size="5.5" text-anchor="middle">PLANTA BAJA</text>
        <text x="60" y="672" fill="#5DADE2" font-family="monospace" font-size="5" text-anchor="middle">ESC 1:75 · ACOT. m</text>
        <text x="150" y="655" fill="#5DADE2" font-family="monospace" font-size="4.5" text-anchor="middle">PROYECTO TIPO</text>
        <text x="150" y="663" fill="#5DADE2" font-family="monospace" font-size="4.5" text-anchor="middle">VIVIENDA UNIFAMILIAR</text>
        <text x="150" y="673" fill="#5DADE2" font-family="monospace" font-size="4.5" text-anchor="middle">REV. 01 · JUN 2026</text>
      </g>
    </svg>
    <div class="logo"><h2>FERRE<span class="logo-dot">·</span>ÚTIL</h2><span class="logo-tag">Ingeniería ferretera</span></div>
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
    rutas: ['/inventario', '/ajustes', '/mapa'],
    items: [
      { ruta: '/inventario',          label: 'Inventario',     soloAdminOGestionadorOVendedor: true },
      { ruta: '/inventario/importar', label: 'Importar Excel', soloAdmin: true },
      { ruta: '/ajustes',             label: 'Ajustes',        soloAdminOGestionador: true },
      { ruta: '/mapa',                label: '🗂 Mapa',         siempre: true },
    ],
  },
  {
    key: 'ventas',
    icono: '💰',
    nombre: 'Ventas',
    rutas: ['/ventas', '/presupuestos', '/devoluciones', '/cierre', '/tasa', '/apartados'],
    items: [
      { ruta: '/ventas',      label: 'Ventas',         siempre: true },
      { ruta: '/apartados',   label: '📦 Apartados',   soloAdminOVendedor: true },
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
      { ruta: '/avisos',  label: 'Avisos',        siempre: true },
      { ruta: '/chuito', label: '🔧 Chuito',      siempre: true },
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
      if (item.soloAdmin)              return this.esAdmin
      if (item.soloAdminOGestionador)  return this.esAdmin || this.usuario.rol === 'gestionador'
      if (item.soloAdminOVendedor)               return this.esAdmin || this.usuario.rol === 'vendedor'
      if (item.soloAdminOGestionadorOVendedor)   return this.esAdmin || ['gestionador', 'vendedor'].includes(this.usuario.rol)
      if (item.siempre)                return true
      if (item.permiso)                return this.tienePermiso(item.permiso)
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
/* Blueprint SVG background */
.sidebar-blueprint {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

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
  background: rgba(255,255,255,0.04);
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
  color: rgba(255,255,255,0.2);
  letter-spacing: 0.04em;
}
.grupo-flecha {
  font-size: 0.65rem;
  color: rgba(255,255,255,0.2);
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

.grupo-header {
  position: relative;
  z-index: 2;
}
</style>
