import { createRouter, createWebHistory } from 'vue-router'

import Login     from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import Inventario from '../views/Inventario.vue'
import Ventas    from '../views/Ventas.vue'
import CierreCaja from '../views/CierreCaja.vue'
import Facturas  from '../views/Facturas.vue'
import Tasa      from '../views/Tasa.vue'
import Depositos from '../views/Depositos.vue'
import Reportes       from '../views/Reportes.vue'
import OrdenesCompra       from '../views/compras/OrdenesCompra.vue'
import CuentasBancarias    from '../views/bancos/CuentasBancarias.vue'
import MovimientosBancarios from '../views/bancos/MovimientosBancarios.vue'
import PagosProveedores    from '../views/bancos/PagosProveedores.vue'
import RecibirCompra  from '../views/compras/RecibirCompra.vue'
import Proveedores    from '../views/compras/Proveedores.vue'
import Clientes       from '../views/Clientes.vue'
import Fidelidad      from '../views/Fidelidad.vue'
import Vendedores     from '../views/Vendedores.vue'
import MiComision     from '../views/MiComision.vue'
import Ajustes        from '../views/Ajustes.vue'
import Usuarios       from '../views/Usuarios.vue'
import Presupuestos   from '../views/Presupuestos.vue'
import Devoluciones   from '../views/Devoluciones.vue'

const routes = [
  { path: '/',          redirect: '/login' },
  { path: '/login',     name: 'Login',     component: Login },
  { path: '/dashboard', name: 'Dashboard', component: Dashboard },

  // Rutas con permiso de módulo (accesibles a no-admin según permisos)
  { path: '/ventas',    name: 'Ventas',    component: Ventas,    meta: { permiso: 'ventas' } },
  { path: '/cierre',    name: 'CierreCaja',component: CierreCaja,meta: { permiso: 'cierre' } },
  { path: '/tasa',      name: 'Tasa',      component: Tasa,      meta: { permiso: 'tasa' } },
  { path: '/depositos', name: 'Depositos', component: Depositos, meta: { permiso: 'depositos' } },
  { path: '/facturas',  name: 'Facturas',  component: Facturas,  meta: { permiso: 'facturas' } },
  { path: '/reportes',  name: 'Reportes',  component: Reportes,  meta: { permiso: 'reportes' } },
  { path: '/clientes',  name: 'Clientes',  component: Clientes,  meta: { permiso: 'clientes' } },
  { path: '/fidelidad', name: 'Fidelidad', component: Fidelidad, meta: { permiso: 'fidelidad' } },
  { path: '/mi-comision',    name: 'MiComision',   component: MiComision,   meta: { permiso: 'mi_comision' } },
  { path: '/presupuestos',  name: 'Presupuestos', component: Presupuestos, meta: { permiso: 'presupuestos' } },
  { path: '/devoluciones',  name: 'Devoluciones', component: Devoluciones, meta: { permiso: 'devoluciones' } },
  { path: '/compras/ordenes',      name: 'OrdenesCompra', component: OrdenesCompra, meta: { permiso: 'compras' } },
  { path: '/compras/recibir',      name: 'RecibirCompra', component: RecibirCompra, meta: { permiso: 'compras' } },
  { path: '/compras/proveedores',  name: 'Proveedores',   component: Proveedores,   meta: { permiso: 'proveedores' } },

  // Rutas solo admin (no delegables)
  { path: '/inventario',           name: 'Inventario',          component: Inventario,          meta: { soloAdmin: true } },
  { path: '/ajustes',              name: 'Ajustes',             component: Ajustes,             meta: { soloAdmin: true } },
  { path: '/vendedores',           name: 'Vendedores',          component: Vendedores,          meta: { soloAdmin: true } },
  { path: '/bancos/cuentas',       name: 'CuentasBancarias',    component: CuentasBancarias,    meta: { soloAdmin: true } },
  { path: '/bancos/movimientos',   name: 'MovimientosBancarios',component: MovimientosBancarios,meta: { soloAdmin: true } },
  { path: '/bancos/proveedores',   name: 'PagosProveedores',    component: PagosProveedores,    meta: { soloAdmin: true } },
  { path: '/usuarios',             name: 'Usuarios',            component: Usuarios,            meta: { soloAdmin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const raw = localStorage.getItem('usuario')
  if (to.path !== '/login' && !raw) return next('/login')
  if (!raw) return next()

  try {
    const u = JSON.parse(raw)

    // Rutas exclusivas de admin
    if (to.meta.soloAdmin && u.rol !== 'admin') return next('/dashboard')

    // Rutas con permiso de módulo
    if (to.meta.permiso && u.rol !== 'admin') {
      // permisos null = sin restricciones (backwards compat)
      if (u.permisos != null) {
        const lista = Array.isArray(u.permisos) ? u.permisos : []
        if (!lista.includes(to.meta.permiso)) return next('/dashboard')
      }
    }

    next()
  } catch {
    return next('/login')
  }
})

export default router
