<template>
  <div class="layout">
    <AppSidebar />

    <main class="contenido">
      <div class="top-bar">
        <h1>Importar inventario</h1>
        <router-link to="/inventario" class="btn-nuevo">← Volver a Inventario</router-link>
      </div>

      <div class="contenido-inner">

        <!-- Instrucciones -->
        <div class="instrucciones">
          <p class="inst-titulo">Formato esperado del archivo (.xlsx o .csv)</p>
          <p class="inst-desc">El archivo debe tener una fila de encabezados con estas columnas (el orden no importa):</p>
          <div class="columnas-grid">
            <span class="col-tag obligatorio">nombre *</span>
            <span class="col-tag">categoria</span>
            <span class="col-tag">departamento</span>
            <span class="col-tag">proveedor</span>
            <span class="col-tag">costo_usd</span>
            <span class="col-tag">margen_pct</span>
            <span class="col-tag">stock</span>
            <span class="col-tag">es_producto_clave</span>
            <span class="col-tag">descripcion</span>
          </div>
          <p class="inst-nota">* El <strong>departamento</strong> debe coincidir exactamente con un departamento existente en el sistema. Los productos con departamento no encontrado se omiten.</p>
        </div>

        <!-- Área de carga -->
        <div class="upload-area"
          :class="{ 'drag-over': arrastrando }"
          @dragover.prevent="arrastrando = true"
          @dragleave.prevent="arrastrando = false"
          @drop.prevent="onDrop"
          @click="$refs.fileInput.click()">
          <input ref="fileInput" type="file" accept=".xlsx,.xls,.csv" style="display:none" @change="onFileChange" />
          <div v-if="!archivo" class="upload-placeholder">
            <span class="upload-icono">📂</span>
            <p class="upload-texto">Arrastra tu archivo aquí o <strong>haz clic para seleccionar</strong></p>
            <p class="upload-hint">.xlsx · .xls · .csv</p>
          </div>
          <div v-else class="archivo-seleccionado">
            <span class="archivo-icono">📄</span>
            <span class="archivo-nombre">{{ archivo.name }}</span>
            <span class="archivo-size">{{ (archivo.size / 1024).toFixed(1) }} KB</span>
            <button class="btn-quitar-archivo" @click.stop="archivo = null">✕</button>
          </div>
        </div>

        <!-- Botón procesar -->
        <button class="btn-procesar" :disabled="!archivo || procesando" @click="procesar">
          <span v-if="procesando" class="spinner"></span>
          {{ procesando ? 'Importando productos...' : 'Procesar importación' }}
        </button>

        <p class="msg-error" v-if="errorGeneral">{{ errorGeneral }}</p>

        <!-- Resultado -->
        <div v-if="resultado" class="resultado">

          <!-- Resumen -->
          <div class="resumen-cards">
            <div class="res-card res-verde">
              <p class="res-num">{{ resultado.importados }}</p>
              <p class="res-label">Importados</p>
            </div>
            <div class="res-card" :class="resultado.omitidos > 0 ? 'res-amarillo' : 'res-muted'">
              <p class="res-num">{{ resultado.omitidos }}</p>
              <p class="res-label">Omitidos</p>
            </div>
          </div>

          <p v-if="resultado.importados > 0 && resultado.errores.length === 0" class="msg-exito-grande">
            ✓ Todos los productos se importaron correctamente.
          </p>
          <p v-else-if="resultado.importados > 0 && resultado.errores.length > 0" class="msg-parcial">
            ⚠ Importación parcial. Revisa las filas omitidas abajo.
          </p>
          <p v-else-if="resultado.importados === 0" class="msg-error">
            No se importó ningún producto. Revisa el archivo y los errores.
          </p>

          <!-- Tabla de errores -->
          <div v-if="resultado.errores.length > 0" class="errores-box">
            <p class="errores-titulo">Filas omitidas ({{ resultado.errores.length }})</p>
            <div class="tabla-container">
              <table>
                <thead>
                  <tr>
                    <th>Fila</th>
                    <th>Nombre</th>
                    <th>Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="e in resultado.errores" :key="e.fila">
                    <td class="txt-muted">{{ e.fila }}</td>
                    <td style="font-weight:600">{{ e.nombre }}</td>
                    <td class="txt-motivo">{{ e.motivo }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <button class="btn-nueva-importacion" @click="reset">+ Nueva importación</button>
        </div>

      </div>
    </main>
  </div>
</template>

<script>
import AppSidebar from '../components/AppSidebar.vue'
import axios from 'axios'

export default {
  components: { AppSidebar },
  name: 'ImportarInventario',
  data() {
    return {
      archivo:      null,
      arrastrando:  false,
      procesando:   false,
      errorGeneral: '',
      resultado:    null,
    }
  },
  methods: {
    onFileChange(e) {
      const f = e.target.files[0]
      if (f) { this.archivo = f; this.resultado = null; this.errorGeneral = '' }
    },
    onDrop(e) {
      this.arrastrando = false
      const f = e.dataTransfer.files[0]
      if (f) { this.archivo = f; this.resultado = null; this.errorGeneral = '' }
    },
    async procesar() {
      if (!this.archivo) return
      this.procesando   = true
      this.errorGeneral = ''
      this.resultado    = null
      try {
        const form = new FormData()
        form.append('archivo', this.archivo)
        const res = await axios.post('/productos/importar-masivo', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        this.resultado = res.data
      } catch (e) {
        this.errorGeneral = e?.response?.data?.detail || 'Error al procesar el archivo'
      } finally {
        this.procesando = false
      }
    },
    reset() {
      this.archivo      = null
      this.resultado    = null
      this.errorGeneral = ''
      if (this.$refs.fileInput) this.$refs.fileInput.value = ''
    },
  },
}
</script>

<style scoped>
.instrucciones {
  background: #FFFFFF;
  border: 1px solid var(--borde);
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}
.inst-titulo { font-weight: 700; color: var(--texto-principal); margin: 0 0 0.4rem; font-size: 0.9rem; }
.inst-desc   { color: var(--texto-sec); font-size: 0.85rem; margin: 0 0 0.75rem; }
.inst-nota   { color: var(--texto-muted); font-size: 0.82rem; margin: 0.75rem 0 0; }

.columnas-grid { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.col-tag { background: #F5F5F0; border: 1px solid var(--borde); border-radius: 4px; padding: 0.2rem 0.6rem; font-size: 0.78rem; font-weight: 600; color: var(--texto-sec); font-family: monospace; }
.col-tag.obligatorio { background: #FFCC0033; border-color: #FFCC00; color: #996600; }

/* Área de carga */
.upload-area {
  border: 2px dashed var(--borde);
  border-radius: 12px;
  padding: 2.5rem;
  text-align: center;
  cursor: pointer;
  background: #FFFFFF;
  transition: border-color 0.15s, background 0.15s;
  margin-bottom: 1.25rem;
}
.upload-area:hover, .upload-area.drag-over {
  border-color: var(--amarillo);
  background: #FFFDE7;
}
.upload-icono  { font-size: 2.5rem; display: block; margin-bottom: 0.75rem; }
.upload-texto  { color: var(--texto-principal); font-size: 0.95rem; margin: 0 0 0.3rem; }
.upload-hint   { color: var(--texto-muted); font-size: 0.82rem; margin: 0; }

.archivo-seleccionado { display: flex; align-items: center; gap: 0.75rem; justify-content: center; }
.archivo-icono  { font-size: 1.5rem; }
.archivo-nombre { font-weight: 600; color: var(--texto-principal); }
.archivo-size   { color: var(--texto-muted); font-size: 0.82rem; }
.btn-quitar-archivo { background: transparent; border: none; color: var(--texto-muted); font-size: 1rem; cursor: pointer; padding: 0.2rem 0.4rem; }
.btn-quitar-archivo:hover { color: var(--danger); }

/* Botón procesar */
.btn-procesar {
  display: flex; align-items: center; gap: 0.6rem;
  background: #1A1A1A; color: #FFCC00;
  border: none; padding: 0.75rem 2rem;
  border-radius: 8px; cursor: pointer;
  font-size: 1rem; font-weight: 700;
  margin-bottom: 1.5rem;
}
.btn-procesar:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-procesar:not(:disabled):hover { background: #333; }

.spinner {
  width: 16px; height: 16px;
  border: 2px solid #FFCC0055;
  border-top-color: #FFCC00;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Resultado */
.resultado { margin-top: 0.5rem; }

.resumen-cards { display: flex; gap: 1rem; margin-bottom: 1.25rem; }
.res-card { background: #FFFFFF; border: 1px solid var(--borde); border-radius: 10px; padding: 1.2rem 2rem; text-align: center; min-width: 120px; }
.res-num  { font-size: 2.2rem; font-weight: 800; margin: 0; }
.res-label{ font-size: 0.78rem; font-weight: 700; text-transform: uppercase; color: var(--texto-muted); margin: 0.25rem 0 0; letter-spacing: 0.04em; }
.res-verde   .res-num { color: #16A34A; }
.res-amarillo .res-num { color: #996600; }
.res-muted   .res-num { color: var(--texto-muted); }

.msg-exito-grande { color: #16A34A; font-weight: 700; font-size: 1rem; margin: 0 0 1rem; }
.msg-parcial      { color: #996600; font-weight: 600; font-size: 0.95rem; margin: 0 0 1rem; }

.errores-box { margin-bottom: 1.5rem; }
.errores-titulo { font-weight: 700; color: var(--texto-principal); font-size: 0.88rem; margin: 0 0 0.6rem; }
.txt-motivo { color: #DC2626; font-size: 0.85rem; }

.btn-nueva-importacion {
  background: transparent; color: var(--texto-principal);
  border: 1px solid var(--borde); padding: 0.55rem 1.2rem;
  border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}
.btn-nueva-importacion:hover { background: var(--borde-suave); }
</style>
