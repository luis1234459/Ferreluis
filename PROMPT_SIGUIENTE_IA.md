# PROMPT PARA CLAUDE CODE — FERREUTIL
# Sistema Administrativo de Ferretería — Implementación Completa

---

## ROL Y CONTEXTO

Eres un desarrollador senior encargado de completar e implementar en producción el sistema administrativo **Ferreutil** para una ferretería en Venezuela. El proyecto ya tiene una base funcional. Tu trabajo es:

1. Leer y entender el código existente en su totalidad.
2. Implementar todos los módulos y mejoras descritos en este documento.
3. No romper ninguna funcionalidad ya existente.
4. Seguir las convenciones de código del proyecto (descritas abajo).

**Lee primero `FERREUTIL_STATUS.md` para entender el estado actual completo del sistema antes de tocar cualquier archivo.**

---

## STACK TECNOLÓGICO

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 · FastAPI · SQLAlchemy ORM |
| Base de datos (dev) | SQLite — `backend/ferreteria.db` |
| Base de datos (prod) | Supabase (PostgreSQL) vía `DATABASE_URL` |
| Frontend | Vue.js 3 (Options API) · Vite · Axios · PrimeVue 4 |
| IA escaneo facturas | Anthropic Claude API (`claude-opus-4-6`) |
| Deploy | Railway (backend + frontend como servicio estático) |

**Rutas del proyecto:**
```
C:\ferreteria\
├── backend\
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── rutas\
│       ├── productos.py
│       ├── ventas.py
│       ├── usuarios.py
│       ├── tasa.py
│       ├── cierres.py
│       └── facturas.py
└── frontend\
    └── src\
        ├── router\index.js
        └── views\
            ├── Login.vue
            ├── Dashboard.vue
            ├── Inventario.vue
            ├── Ventas.vue
            ├── CierreCaja.vue
            ├── Tasa.vue
            └── Facturas.vue
```

---

## CONVENCIONES DE CÓDIGO — OBLIGATORIAS

- **Backend:** snake_case en todo. Helpers internos con prefijo `_`. Sin lógica de negocio en `main.py`.
- **Frontend:** Vue 3 Options API exclusivamente. No usar Composition API ni `<script setup>`. camelCase en `data()` y `methods`.
- **Monedas:** siempre explícitas como string `"USD"` o `"Bs"`, nunca asumidas.
- **Snapshots de precio:** los precios se guardan al momento de la venta. Nunca recalcular post-venta.
- **Factor cambiario:** siempre `factor = tasa_binance / tasa_bcv`. Nunca un valor fijo.
- **Tolerancia flotantes:** `TOLERANCIA = 0.01` para comparaciones de montos.
- **Archivos completos:** entregar siempre el archivo completo, no fragmentos.

---

## ARQUITECTURA DE DATOS EXISTENTE (NO modificar estructura, solo extender si se indica)

**Producto**
```python
id, nombre, descripcion, categoria, stock, foto_url
costo_usd   # precio de compra
margen      # decimal: 0.30 = 30%
# Precios calculados en runtime (NO en BD):
# precio_base_usd        = costo_usd * (1 + margen)
# factor                 = tasa_binance / tasa_bcv
# precio_referencial_usd = precio_base_usd * factor
# precio_bs              = precio_base_usd * tasa_binance
```

**TasaCambio:** `id, tasa (BCV), tasa_binance (paralelo), fecha`

**Venta:** `id, fecha, usuario, moneda_venta, tipo_precio_usado, subtotal, descuento, total, tasa_bcv, tasa_binance, factor_cambio, total_abonado, saldo_pendiente, exceso, estado, observacion`

**PagoVenta:** `id, venta_id, metodo_pago, moneda_pago, monto_original, tasa_cambio, monto_equivalente, moneda_venta, referencia, fecha_hora, usuario`

**DetalleVenta:** `id, venta_id, producto_id, cantidad, tipo_precio_usado, precio_base_snap, precio_referencial_snap, precio_unitario, subtotal`

**Usuario:** `id, nombre, email, password, rol ("admin"/"cajero")`

**Configuracion:** `id, clave_autorizacion`

**ExcepcionVenta:** `motivo, venta_id, usuario, precio_original, precio_aplicado, descuento`

**CierreCaja:** `fecha_desde, fecha_hasta, cantidad_ventas, total_ventas_usd, esp_[metodo]×8, cnt_[metodo]×8, observacion`

### Constantes en models.py
```python
METODOS_USD     = {"efectivo_usd", "zelle", "binance"}
METODOS_BS      = {"efectivo_bs", "transferencia_bs", "pago_movil", "punto_banesco", "punto_provincial"}
METODOS_VALIDOS = METODOS_USD | METODOS_BS
TOLERANCIA      = 0.01
DECIMALES_USD   = 2
DECIMALES_BS    = 2
```

---

## LÓGICA DE NEGOCIO EXISTENTE (NO cambiar)

### Sistema de precios venezolano
```
precio_base_usd    = costo_usd × (1 + margen)
precio_referencial = precio_base × factor
precio_bs          = precio_base × tasa_binance
factor             = tasa_binance ÷ tasa_bcv
```

### Tipo de precio en ventas
- `"referencial"` (default): para pagos en Bs o mixtos.
- `"base"`: cliente paga TODO en USD. Requiere clave de autorización.
- `"mixto"`: auto-detectado al mezclar métodos USD y Bs.

### Regla de vuelto
Solo `efectivo_usd` y `efectivo_bs` pueden tener exceso. Digitales ≤ saldo pendiente.

### Conversión (siempre por tasa BCV)
```
Pago Bs en venta USD → equivalente_usd = monto_bs / tasa_bcv
Pago USD en venta Bs → equivalente_bs  = monto_usd × tasa_bcv
```

### Autorización requerida para:
- Precio base (descuento divisa) · sin stock · descuento manual · descuento global

---

## ENDPOINTS YA IMPLEMENTADOS (NO duplicar)

```
GET/POST/PUT/DELETE  /productos/
GET/POST             /ventas/
GET/POST             /tasa/
POST                 /tasa/actualizar-bcv
POST                 /tasa/actualizar-manual
GET/POST/DELETE      /usuarios/
POST                 /usuarios/login
POST                 /usuarios/config/clave-autorizacion
GET/POST             /cierres/
GET                  /cierres/resumen
POST                 /facturas/escanear
```

---

## TAREAS A IMPLEMENTAR

### TAREA 1 — Hash de contraseñas (SEGURIDAD — ALTA PRIORIDAD)

- Instalar `passlib[bcrypt]` → `requirements.txt`.
- Funciones `hash_password(plain)` y `verify_password(plain, hashed)` en `usuarios.py`.
- `POST /usuarios/` guarda siempre hasheada. `POST /usuarios/login` verifica con `verify_password`.
- Migración automática al arrancar si contraseña sin prefijo `$2b$`.

---

### TAREA 2 — Restricciones de roles

**Backend:** dependencia `require_admin`. Solo admin: CRUD productos, gestionar usuarios, reportes.  
**Frontend:** ocultar Inventario, Usuarios y Reportes para cajero. Guard del router extendido.

---

### TAREA 3 — Módulo de Reportes

**Backend — `rutas/reportes.py`:**
```
GET /reportes/ventas              → lista + resumen (total_usd, total_bs, cantidad, promedio)
GET /reportes/ventas/por-metodo   → montos por cada uno de los 8 métodos
GET /reportes/inventario          → stock + valor + alerta si stock < 5
GET /reportes/productos/top       → top N por cantidad y monto
GET /reportes/cierre/comparativo  → esperado vs contado por período
```

**Frontend — `views/Reportes.vue`:** tabs, filtros de fecha, gráfica de barras, alertas stock bajo, exportar PDF. Ruta `/reportes` — solo admin.

---

### TAREA 4 — Módulo de Depósitos y Transferencias

**Backend — modelo `Deposito`:** `id, fecha, tipo, banco_origen, banco_destino, monto, moneda, referencia, concepto, usuario, comprobante_url`

**Endpoints `rutas/depositos.py`:** CRUD + `GET /depositos/resumen`

**Frontend — `views/Depositos.vue`:** formulario + historial filtrable + totales por moneda.

---

### TAREA 5 — Deploy en Railway con Supabase

- `config.py`: agregar `SECRET_KEY`, `ENVIRONMENT`.
- `database.py`: omitir `check_same_thread` si PostgreSQL. Instalar `psycopg2-binary`.
- Crear `Procfile` y `railway.toml`.
- CORS en producción: restringir `allow_origins` al dominio del frontend.
- Frontend: `VITE_API_URL` en `.env.development` y `.env.production`. Reemplazar URLs hardcodeadas. `vite.config.js` con `base: './'`.

---

### TAREA 6 — Exportar Facturas en PDF

- Instalar `jspdf` + `jspdf-autotable`.
- Función `exportarFacturaPDF(ventaId)`: encabezado FERREUTIL, tabla productos, sección pagos, totales, pie "Documento no fiscal".
- Verificar que `GET /ventas/{id}` retorne nombre del producto en cada detalle.
- Botón "Imprimir / PDF" al finalizar venta y en historial.

---

### TAREA 7 — Módulo de Compras

#### Flujo completo
```
Proveedor → Orden de Compra (borrador) → Aprobada → Recepción → Cerrada
```

#### Nuevos modelos en `models.py`

**Proveedor:** `id, nombre, rif, telefono, email, direccion, contacto, activo, fecha_registro`

**CatalogoProveedor:** `id, proveedor_id, producto_id (nullable), nombre_producto, codigo_proveedor, precio_referencia_usd`

**OrdenCompra:**
```python
id, numero ("OC-0001"), proveedor_id, fecha_creacion, fecha_aprobacion, fecha_esperada
estado  # "borrador" / "aprobada" / "recibida_parcial" / "cerrada" / "anulada"
creado_por, aprobado_por, moneda ("USD"), subtotal, descuento, total, observacion
```

**DetalleOrdenCompra:**
```python
id, orden_id, producto_id (nullable), nombre_producto, codigo_proveedor
cantidad_pedida, precio_unitario_usd, subtotal, es_producto_nuevo (Boolean)
```

**RecepcionCompra:** `id, orden_id, fecha_recepcion, recibido_por, observacion, total_recibido`

**DetalleRecepcion:**
```python
id, recepcion_id, detalle_orden_id, producto_id (obligatorio al recibir)
cantidad_recibida, precio_unitario_real_usd, subtotal
actualizo_costo (Boolean), costo_anterior (Float nullable)
```

#### Reglas de negocio

**Numeración:** auto-correlativo `OC-XXXX`, nunca reutilizado.

**Transiciones de estado:**
```
borrador → aprobada (solo admin)
aprobada → recibida_parcial / cerrada (al recibir)
recibida_parcial → cerrada (al recibir el resto)
borrador/aprobada → anulada (admin; cajero solo su borrador)
cerrada → [inmutable]
```

**Productos nuevos:** si `es_producto_nuevo = True`, bloquear recepción y retornar error indicando qué productos registrar primero. Al reintentar, vincular automáticamente por nombre.

**Al confirmar recepción:**
1. `Producto.stock += cantidad_recibida`
2. Si `precio_real ≠ precio_pedido` (diff > 0.01): actualizar `Producto.costo_usd`, guardar `costo_anterior`.
3. Registrar en auditoría.

**Recepción parcial:** orden pasa a `recibida_parcial`. Se permite segunda recepción.

#### Endpoints — `rutas/compras.py`

```
# Proveedores
GET/POST         /compras/proveedores/
PUT/DELETE       /compras/proveedores/{id}
GET/POST         /compras/proveedores/{id}/catalogo
PUT/DELETE       /compras/proveedores/{id}/catalogo/{item_id}

# Órdenes
GET/POST         /compras/ordenes/
GET/PUT          /compras/ordenes/{id}
POST             /compras/ordenes/{id}/aprobar     (solo admin)
POST             /compras/ordenes/{id}/anular
GET              /compras/ordenes/{id}/pdf

# Recepciones
GET/POST         /compras/ordenes/{id}/recepciones/
GET              /compras/recepciones/{id}

# Reportes
GET              /compras/reportes/por-proveedor
GET              /compras/reportes/ordenes-pendientes
GET              /compras/reportes/variaciones-precio
```

#### Frontend

**`views/compras/Proveedores.vue`:** tabla + Dialog crear/editar + gestión de catálogo. Solo admin.

**`views/compras/OrdenesCompra.vue`:**
- Tabla con filtros por estado/proveedor/fecha. Badge de color por estado.
- Crear/editar orden: selector proveedor, agregar líneas (producto existente o nuevo), totales en tiempo real.
- Botones: aprobar (admin), exportar PDF.

**`views/compras/RecibirCompra.vue`:**
- Seleccionar orden aprobada. Ingresar cantidad recibida y precio real por línea.
- Alerta visual si precio difiere → "Se actualizará costo del producto".
- Bloque rojo si hay productos nuevos sin registrar → enlace a Inventario.
- Resumen al confirmar: stock actualizado + costos modificados.

**PDF de Orden de Compra:** encabezado con datos del proveedor, tabla de productos, total, observaciones, usuario que elaboró, fecha esperada.

#### Sidebar — módulo Compras
```
Admin:   Órdenes → /compras/ordenes  |  Recibir → /compras/recibir  |  Proveedores → /compras/proveedores
Cajero:  Mis borradores → /compras/ordenes (filtrado)
```

#### Integración
- Al recibir: actualizar `stock` y `costo_usd` en `Producto`. Precios se recalculan en runtime.
- Reportes: agregar sección "Compras" con total por proveedor, órdenes pendientes, variaciones de precio.

#### Verificación del módulo
- [ ] Proveedor creado con catálogo de productos.
- [ ] Cajero crea borrador pero no puede aprobar.
- [ ] Admin aprueba y exporta PDF.
- [ ] Recepción con precio diferente actualiza `costo_usd` en inventario.
- [ ] Producto nuevo bloquea recepción hasta estar registrado.
- [ ] Recepción parcial → estado `recibida_parcial` → segunda recepción posible.
- [ ] Stock sube correctamente al confirmar recepción.
- [ ] Orden cerrada es inmutable.

---

## DATOS DE PRUEBA EXISTENTES (respetar)

| Item | Valor |
|------|-------|
| Usuario admin | `admin@ferreutil.com` / `1234` |
| Clave autorización | `1234` |
| Tasa BCV | 92.50 Bs/USD |
| Tasa Binance | 99.80 Bs/USD |
| Producto de prueba | MARTILLO 16oz — costo $10, margen 30% |

---

## ORDEN DE IMPLEMENTACIÓN RECOMENDADO

1. TAREA 1 — Hash de contraseñas
2. TAREA 2 — Restricciones de roles
3. TAREA 5 — Configuración de deploy
4. TAREA 4 — Módulo de Depósitos
5. TAREA 3 — Módulo de Reportes
6. TAREA 7 — Módulo de Compras
7. TAREA 6 — Exportar PDF

---

## VERIFICACIÓN FINAL

- [ ] `uvicorn main:app --port 8000` arranca sin errores
- [ ] `npm run dev` arranca sin errores
- [ ] Login con admin funciona
- [ ] Venta con pago mixto funciona
- [ ] Cierre de caja funciona
- [ ] Tasa BCV se actualiza
- [ ] Reportes y depósitos responden
- [ ] PDF de factura se genera
- [ ] Cajero no accede a inventario ni reportes
- [ ] Módulo de compras completo (órdenes, recepción, stock)
- [ ] `npm run build` genera build sin errores
