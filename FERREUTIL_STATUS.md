# FERREUTIL — Estado del Sistema
**Última actualización:** 2026-04-06  
**Actualizado por:** Claude Sonnet 4.6 (sesión de trabajo)

---

## 1. Descripción general

Sistema administrativo interno (no fiscal) para una ferretería ubicada en **Ciudad Ojeda, Zulia, Venezuela**. Gestionado de forma remota desde Valera. El sistema maneja inventario, ventas en múltiples monedas, cobro con 8 métodos de pago, cierre de caja diario, escaneo de facturas con IA y control de tasas de cambio.

---

## 2. Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 · FastAPI · SQLAlchemy ORM |
| Base de datos (dev) | SQLite (`backend/ferreteria.db`) |
| Base de datos (prod) | Supabase (pendiente configurar) |
| Frontend | Vue.js 3 (Options API) · Vite · Axios |
| IA escaneo | Anthropic Claude API (`claude-opus-4-6`) |
| Deploy futuro | Railway |

**Rutas de instalación (Windows local):**
- Backend: `C:\ferreteria\backend\`
- Frontend: `C:\ferreteria\frontend\`

**Comandos para arrancar:**
```bash
# Backend (en C:\ferreteria\backend)
uvicorn main:app --port 8000

# Frontend (en C:\ferreteria\frontend)
npm run dev   → http://localhost:5173
```

---

## 3. Estructura de archivos

```
C:\ferreteria\
├── backend\
│   ├── config.py          # DATABASE_URL + ANTHROPIC_API_KEY (env vars)
│   ├── database.py        # SQLAlchemy engine + sesión
│   ├── main.py            # FastAPI app + CORS + routers
│   ├── models.py          # Todos los modelos ORM (ver sección 4)
│   └── rutas\
│       ├── productos.py   # CRUD productos con precios computados
│       ├── ventas.py      # Registro de ventas con lógica de precios
│       ├── usuarios.py    # CRUD usuarios + login
│       ├── tasa.py        # Tasas BCV y Binance
│       ├── cierres.py     # Cierre de caja por turno
│       └── facturas.py    # Escaneo de facturas con Claude AI
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

## 4. Modelos de datos (models.py)

### `Producto`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | — |
| nombre | String | — |
| descripcion | String | opcional |
| categoria | String | opcional |
| stock | Integer | unidades disponibles |
| foto_url | String | opcional |
| costo_usd | Float | precio de compra en USD |
| margen | Float | decimal, ej: 0.30 = 30% |

**Precios calculados (NO guardados en BD):**
```
precio_base_usd        = costo_usd × (1 + margen)
factor                 = tasa_binance ÷ tasa_bcv
precio_referencial_usd = precio_base_usd × factor
precio_bs              = precio_base_usd × tasa_binance
```
El endpoint `GET /productos/` retorna estos campos calculados con las tasas vigentes.

---

### `TasaCambio`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | — |
| tasa | Float | tasa BCV (Bs por USD) |
| tasa_binance | Float nullable | tasa mercado paralelo (Bs por USD) |
| fecha | DateTime | auto |

---

### `Venta`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | — |
| fecha | DateTime | — |
| usuario | String | nombre del cajero |
| moneda_venta | String | "USD" o "Bs" |
| tipo_precio_usado | String | "base" / "referencial" / "mixto" |
| subtotal | Float | en moneda_venta |
| descuento | Float | en moneda_venta |
| total | Float | en moneda_venta |
| tasa_bcv | Float | snapshot al momento de la venta |
| tasa_binance | Float | snapshot |
| factor_cambio | Float | tasa_binance ÷ tasa_bcv al momento |
| total_abonado | Float | en moneda_venta |
| saldo_pendiente | Float | en moneda_venta |
| exceso | Float | vuelto en moneda_venta |
| estado | String | "pagado" / "anulado" |
| observacion | String | opcional |

---

### `PagoVenta`
Cada abono individual de una venta.
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | — |
| venta_id | Integer FK | — |
| metodo_pago | String | ver métodos en sección 5 |
| moneda_pago | String | "USD" o "Bs" |
| monto_original | Float | en moneda_pago (moneda nativa) |
| tasa_cambio | Float | tasa BCV usada |
| monto_equivalente | Float | convertido a moneda_venta |
| moneda_venta | String | moneda del documento |
| referencia | String | número de transacción, opcional |
| fecha_hora | DateTime | — |
| usuario | String | — |

---

### `DetalleVenta`
Línea de producto por venta.
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | — |
| venta_id | Integer FK | — |
| producto_id | Integer FK | — |
| cantidad | Integer | — |
| tipo_precio_usado | String | "base" o "referencial" |
| precio_base_snap | Float | costo×(1+margen) al momento |
| precio_referencial_snap | Float | base×factor al momento |
| precio_unitario | Float | precio efectivamente cobrado (USD) |
| subtotal | Float | en moneda_venta |

---

### `Usuario`
| Campo | Tipo |
|-------|------|
| id | Integer PK |
| nombre | String |
| email | String |
| password | String (plano, pendiente hash) |
| rol | String ("admin" / "cajero") |

---

### `Configuracion`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer PK | — |
| clave_autorizacion | String | clave para operaciones especiales |

---

### `ExcepcionVenta`
Auditoría de operaciones que requirieron autorización.
| Campo | Tipo | Descripción |
|-------|------|-------------|
| motivo | String | descuento_divisa / venta_sin_stock / descuento_producto / descuento_total |
| venta_id | Integer | — |
| usuario | String | — |
| precio_original / precio_aplicado / descuento | Float | contexto |

---

### `CierreCaja`
| Campos | Descripción |
|--------|-------------|
| fecha_desde / fecha_hasta | período del cierre |
| cantidad_ventas | total ventas del período |
| total_ventas_usd | total normalizado a USD |
| esp_[metodo] × 8 | monto esperado por método (sistema) |
| cnt_[metodo] × 8 | monto contado por el cajero |
| observacion | notas del turno |

---

## 5. Lógica de negocio implementada

### 5.1 Métodos de pago (8 total)

| Método | Código | Moneda nativa |
|--------|--------|---------------|
| Efectivo USD | `efectivo_usd` | USD |
| Zelle | `zelle` | USD |
| Binance | `binance` | USD |
| Efectivo Bs | `efectivo_bs` | Bs |
| Transferencia Bs | `transferencia_bs` | Bs |
| Pago Móvil | `pago_movil` | Bs |
| Punto Banesco | `punto_banesco` | Bs |
| Punto Provincial | `punto_provincial` | Bs |

**Regla de exceso:** solo `efectivo_usd` y `efectivo_bs` pueden tener exceso (vuelto). Los métodos digitales deben ser ≤ saldo pendiente.

### 5.2 Sistema de precios (cambiaria venezolana)

```
costo_usd           → almacenado en BD
margen              → almacenado en BD (ej: 0.30 = 30%)

precio_base_usd     = costo_usd × (1 + margen)       ← precio interno, USD puro
factor              = tasa_binance ÷ tasa_bcv          ← protección cambiaria
precio_referencial  = precio_base × factor             ← precio comercial con protección
precio_bs           = precio_base × tasa_binance       ← precio visible al cliente en Bs
```

**tipo_precio en la venta:**
- `"referencial"` (default): se usa precio_referencial_usd. Aplica para pagos en Bs o mixtos.
- `"base"`: solo cuando el cliente paga **todo en USD**. Requiere autorización (descuento_divisa).
- `"mixto"`: auto-detectado cuando se mezclan métodos USD y Bs en el mismo cobro.

### 5.3 Conversión de pagos (tasa BCV)

```
Venta USD + pago Bs  → equivalente_usd = monto_bs / tasa_bcv
Venta Bs  + pago USD → equivalente_bs  = monto_usd × tasa_bcv
Misma moneda         → sin conversión
Tolerancia de cierre → 0.01
```

### 5.4 Autorización requerida para:
- Usar precio base (descuento divisa)
- Vender sin stock suficiente
- Aplicar descuento manual en un producto (precio < precio del tier)
- Aplicar descuento global a la factura

La clave se configura en `POST /usuarios/config/clave-autorizacion`.

---

## 6. API Endpoints

### Productos (`/productos`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/productos/` | Lista con precios computados (base, ref, bs) |
| GET | `/productos/{id}` | Detalle |
| POST | `/productos/` | Crear (`costo_usd`, `margen`) |
| PUT | `/productos/{id}` | Editar |
| DELETE | `/productos/{id}` | Eliminar |

### Ventas (`/ventas`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/ventas/` | Listar todas |
| GET | `/ventas/{id}` | Detalle + pagos + detalles |
| POST | `/ventas/` | Registrar venta (ver payload en sección 7) |

### Tasa (`/tasa`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/tasa/` | Retorna tasa, tasa_binance, factor |
| POST | `/tasa/actualizar-bcv` | Scraping automático bcv.org.ve |
| POST | `/tasa/actualizar-manual` | Manual: `{tasa, tasa_binance}` |

### Usuarios (`/usuarios`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/usuarios/` | Listar |
| POST | `/usuarios/` | Crear `{nombre, email, password, rol}` |
| POST | `/usuarios/login` | Login `{email, password}` → `{usuario, rol, id}` |
| DELETE | `/usuarios/{id}` | Eliminar |
| POST | `/usuarios/config/clave-autorizacion` | Cambiar clave `{clave}` |

### Cierres (`/cierres`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/cierres/resumen` | Totales por método desde último cierre |
| POST | `/cierres/` | Guardar cierre `{usuario, contados{}, observacion}` |
| GET | `/cierres/` | Historial |

### Facturas (`/facturas`)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/facturas/escanear` | Imagen → JSON productos (Claude AI) |

---

## 7. Payload principal: Registrar venta

```json
{
  "usuario": "Admin",
  "moneda_venta": "USD",
  "tipo_precio": "referencial",
  "descuento": 0,
  "observacion": "",
  "autorizacion_clave": "",
  "detalles": [
    {
      "producto_id": 1,
      "cantidad": 2,
      "precio_unitario": 14.03
    }
  ],
  "pagos": [
    { "metodo": "efectivo_usd", "monto": 20.00, "referencia": "" },
    { "metodo": "pago_movil",   "monto": 500.00, "referencia": "PM-001" }
  ]
}
```

**Notas del payload:**
- `precio_unitario` es opcional; si se omite o es 0, el backend usa el precio del `tipo_precio` seleccionado.
- `tipo_precio`: `"referencial"` (default) o `"base"` (requiere `autorizacion_clave`).
- `descuento`: en `moneda_venta`.
- El backend auto-detecta `"mixto"` si se mezclan métodos USD y Bs.

---

## 8. Frontend — Vistas implementadas

| Vista | Ruta | Estado |
|-------|------|--------|
| Login | `/login` | completo |
| Dashboard | `/dashboard` | básico (últimas ventas, KPIs) |
| Inventario | `/inventario` | CRUD + previsualización de precios |
| Ventas | `/ventas` | completo (multi-pago, tipo precio, autorización) |
| Cierre de Caja | `/cierre` | completo (8 métodos, conteo vs sistema) |
| Tasa BCV | `/tasa` | completo (BCV + Binance + factor) |
| Facturas IA | `/facturas` | básico (escaneo imagen → productos) |

**Autenticación:** `localStorage.setItem('usuario', JSON.stringify({usuario, rol, id}))`. Guard en `router.beforeEach`.

**Sidebar:** presente en todas las vistas autenticadas con los 6 links + botón Salir.

---

## 9. Lo que NO está implementado (pendiente)

| Módulo | Prioridad | Notas |
|--------|-----------|-------|
| **Reportes** | Alta | Ventas por período, inventario bajo stock, top productos |
| **Tipos de precio mayor/detal** | Media | Precios diferenciados por tipo de cliente |
| **Gestión de descuentos y ofertas** | Media | Promociones temporales |
| **Registro de depósitos/transferencias** | Media | Control bancario de entradas |
| **Deploy en Railway** | Alta | Variables de entorno: DATABASE_URL (Supabase), ANTHROPIC_API_KEY |
| **Hash de contraseñas** | Alta (seguridad) | Actualmente guardadas en texto plano |
| **Gestión de roles granular** | Baja | Actualmente solo "admin" / "cajero" sin restricciones en rutas |
| **Historial de precios** | Baja | Auditoría de cambios de costo/margen |
| **Multi-sucursal** | Baja | No requerido en diseño actual |

---

## 10. Detalles técnicos importantes

### Variables de entorno (config.py)
```python
DATABASE_URL      = os.environ.get("DATABASE_URL", "sqlite:///./ferreteria.db")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "sk-ant-...")
```

### CORS
Configurado con `allow_origins=["*"]` — adecuado para desarrollo local.  
En producción debe restringirse al dominio del frontend.

### SQLite en desarrollo
`connect_args={"check_same_thread": False}` requerido para SQLite con FastAPI.

### Constantes globales (models.py)
```python
METODOS_USD     = {"efectivo_usd", "zelle", "binance"}
METODOS_BS      = {"efectivo_bs", "transferencia_bs", "pago_movil", "punto_banesco", "punto_provincial"}
METODOS_VALIDOS = METODOS_USD | METODOS_BS
TOLERANCIA      = 0.01
DECIMALES_USD   = 2
DECIMALES_BS    = 2
```

### Frontend — dependencias clave
```json
"axios": "^1.14.0",
"vue": "^3.5.31",
"vue-router": "^5.0.4",
"primevue": "^4.5.4"
```

### URL base API (hardcoded en frontend)
`http://127.0.0.1:8000` — debe cambiarse a variable de entorno para deploy.

---

## 11. Convenciones de código

- **Backend:** snake_case, funciones prefijadas con `_` para helpers internos.
- **Frontend:** Options API (no Composition API), `camelCase` en data/methods.
- **Monedas:** siempre se especifica explícitamente ("USD" / "Bs"), nunca se asume.
- **Snapshots:** los precios se guardan al momento de la venta, nunca se recalculan post-venta.
- **Precios:** nunca valores fijos de factor de protección; siempre `factor = tasa_binance / tasa_bcv`.

---

## 12. Datos de prueba actuales (BD local)

- **Usuario:** `admin@ferreutil.com` / `1234` / rol: admin
- **Clave autorización:** `1234`
- **Tasa BCV:** 92.50 Bs/USD
- **Tasa Binance:** 99.80 Bs/USD
- **Factor:** 1.0789
- **Producto de prueba:** MARTILLO 16oz, costo $10, margen 30% → base $13 / ref $14.03 / Bs. 1,297.40
