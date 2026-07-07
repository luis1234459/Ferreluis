<template>
  <div class="orden-despacho">
    <div class="header">
      <div class="titulo">FERREUTIL</div>
      <div class="subtitulo">DESPACHO</div>
    </div>

    <div class="hr-doble"></div>

    <div v-if="cargando" class="info-basica">Cargando...</div>
    <div v-else-if="error" class="info-basica">{{ error }}</div>

    <template v-else-if="venta">
      <div class="info-basica">
        <div><strong>ORDEN Nº:</strong> {{ numeroOrden }}</div>
        <div><strong>Fecha:</strong> {{ fechaFormato }}</div>
        <div><strong>Hora:</strong> {{ horaFormato }}</div>
        <div><strong>Venta Nº:</strong> V-{{ venta.id }}</div>
        <div><strong>Vendedor:</strong> {{ venta.usuario || '—' }}</div>
        <div><strong>Cliente:</strong> {{ venta.cliente || 'Cliente general' }}</div>
      </div>

      <div class="hr-simple"></div>

      <table class="productos">
        <thead>
          <tr>
            <th class="col-cant">CANT</th>
            <th class="col-desc">DESCRIPCION</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in detalles" :key="d.id">
            <td class="col-cant">{{ d.cantidad }}</td>
            <td class="col-desc">{{ (d.nombre || '').toUpperCase() }}</td>
          </tr>
        </tbody>
      </table>

      <div class="hr-simple"></div>

      <div class="total-bultos">
        TOTAL UNIDADES: {{ totalUnidades }}
      </div>

      <div class="hr-simple"></div>

      <div class="firma">
        <div>FIRMA DESPACHADOR:</div>
        <div class="linea-firma">_________________________</div>
      </div>

      <div class="hr-doble"></div>

      <div class="pie">
        <div>DOCUMENTO DE USO INTERNO</div>
        <div>NO ES VALIDO PARA CLIENTE</div>
        <div>NO SUSTITUYE A LA FACTURA</div>
      </div>
    </template>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'OrdenDespacho',
  props: {
    id: { type: [String, Number], required: true },
  },
  data() {
    return {
      venta:    null,
      detalles: [],
      cargando: true,
      error:    '',
    }
  },
  computed: {
    numeroOrden() {
      return String(this.venta?.id || '').padStart(6, '0')
    },
    fechaFormato() {
      if (!this.venta?.fecha) return ''
      return new Date(this.venta.fecha).toLocaleDateString('es-VE')
    },
    horaFormato() {
      if (!this.venta?.fecha) return ''
      return new Date(this.venta.fecha).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' })
    },
    totalUnidades() {
      return this.detalles.reduce((sum, d) => sum + Number(d.cantidad || 0), 0)
    },
  },
  async mounted() {
    try {
      const res = await axios.get(`/ventas/${this.id}`)
      this.venta    = res.data.venta
      this.detalles = res.data.detalles || []
    } catch (e) {
      this.error = e?.response?.data?.detail || 'Error al cargar la venta'
    } finally {
      this.cargando = false
    }
  },
}
</script>

<style scoped>
.orden-despacho {
  width: 80mm;
  padding: 3mm;
  font-family: 'Courier New', monospace;
  font-size: 10pt;
  color: #000;
  background: #fff;
}
.header {
  text-align: center;
  margin-bottom: 4px;
}
.titulo {
  font-size: 14pt;
  font-weight: bold;
  letter-spacing: 2px;
}
.subtitulo {
  font-size: 11pt;
  font-weight: bold;
  margin-top: 2px;
}
.hr-doble {
  border-top: 2px solid #000;
  border-bottom: 1px solid #000;
  height: 3px;
  margin: 4px 0;
}
.hr-simple {
  border-top: 1px dashed #000;
  margin: 4px 0;
}
.info-basica {
  font-size: 9pt;
  line-height: 1.4;
}
.productos {
  width: 100%;
  border-collapse: collapse;
  font-size: 9pt;
}
.productos th {
  text-align: left;
  padding: 2px 0;
  font-weight: bold;
  border-bottom: 1px solid #000;
}
.productos td {
  padding: 3px 0;
  vertical-align: top;
}
.col-cant {
  width: 15mm;
  text-align: right;
  padding-right: 3mm !important;
  font-weight: bold;
}
.col-desc {
  font-size: 8.5pt;
  line-height: 1.2;
}
.total-bultos {
  text-align: center;
  font-weight: bold;
  font-size: 10pt;
  padding: 3px 0;
}
.firma {
  margin: 8px 0;
  font-size: 9pt;
}
.linea-firma {
  margin-top: 12px;
  text-align: center;
}
.pie {
  text-align: center;
  font-size: 8pt;
  font-weight: bold;
  line-height: 1.4;
  padding: 2px 0;
}

@media print {
  @page {
    size: 80mm auto;
    margin: 0;
  }
  body {
    margin: 0;
  }
  .orden-despacho {
    padding: 2mm;
  }
  .orden-despacho::after {
    content: "";
    display: block;
    height: 15mm;
  }
}
</style>
