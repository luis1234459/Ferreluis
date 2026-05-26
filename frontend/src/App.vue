<template>
  <div>
    <router-view />

    <!-- Modal avisos bloqueante para gestionador -->
    <div v-if="modalAvisos && avisosGestionador.length > 0"
         class="aviso-overlay">
      <div class="aviso-modal">
        <div class="aviso-header">
          <h2>📢 Aviso importante</h2>
          <span class="aviso-contador">
            {{ avisoActualIdx + 1 }} / {{ avisosGestionador.length }}
          </span>
        </div>
        <div class="aviso-body">
          <h3>{{ avisosGestionador[avisoActualIdx]?.titulo }}</h3>
          <p>{{ avisosGestionador[avisoActualIdx]?.mensaje }}</p>
          <small class="aviso-fecha">
            {{ formatFecha(avisosGestionador[avisoActualIdx]?.fecha) }}
          </small>
        </div>
        <div class="aviso-footer">
          <button class="btn-confirmar-aviso" @click="confirmarAviso">
            ✓ Leído — Continuar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
export default {
  name: 'App',
  data() {
    return {
      modalAvisos:       false,
      avisosGestionador: [],
      avisoActualIdx:    0,
    }
  },
  async mounted() {
    const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
    if (usuario.rol === 'gestionador') {
      await this.cargarAvisos(usuario)
    }
  },
  methods: {
    async cargarAvisos(usuario) {
      try {
        const res = await axios.get('/notificaciones/avisos/pendientes', {
          headers: {
            'x-usuario-nombre': usuario.usuario || usuario.nombre || '',
            'x-usuario-rol':    usuario.rol || '',
          },
        })
        if (res.data.length > 0) {
          this.avisosGestionador = res.data
          this.avisoActualIdx    = 0
          this.modalAvisos       = true
        }
      } catch {}
    },
    async confirmarAviso() {
      const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
      const aviso   = this.avisosGestionador[this.avisoActualIdx]
      try {
        await axios.post(`/notificaciones/avisos/${aviso.id}/leer`, {}, {
          headers: {
            'x-usuario-nombre': usuario.usuario || usuario.nombre || '',
          },
        })
      } catch {}
      if (this.avisoActualIdx < this.avisosGestionador.length - 1) {
        this.avisoActualIdx++
      } else {
        this.modalAvisos = false
      }
    },
    formatFecha(iso) {
      if (!iso) return ''
      return new Date(iso).toLocaleDateString('es-VE', {
        day: '2-digit', month: 'long', year: 'numeric',
      })
    },
  },
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: 'Segoe UI', sans-serif;
  background: #FAFAF7;
  color: #1A1A1A;
}

.aviso-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.75);
  z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}
.aviso-modal {
  background: #1A1A1A; color: #FFFFFF;
  border-radius: 12px; width: 100%;
  max-width: 480px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  border: 1px solid #333;
}
.aviso-header {
  display: flex; justify-content: space-between;
  align-items: center; padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #333;
}
.aviso-header h2 {
  margin: 0; font-size: 1rem;
  color: #FFCC00; font-weight: 700;
}
.aviso-contador {
  font-size: 0.78rem; color: #888;
}
.aviso-body {
  padding: 1.5rem;
}
.aviso-body h3 {
  margin: 0 0 0.75rem;
  font-size: 1.1rem; color: #FFFFFF; font-weight: 700;
}
.aviso-body p {
  color: #C7C5BE; line-height: 1.6;
  font-size: 0.95rem; margin: 0;
}
.aviso-fecha {
  display: block; margin-top: 1rem;
  color: #666; font-size: 0.78rem;
}
.aviso-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #333;
}
.btn-confirmar-aviso {
  width: 100%; background: #FFCC00;
  color: #1A1A1A; border: none;
  padding: 0.75rem; border-radius: 8px;
  font-weight: 700; font-size: 0.95rem;
  cursor: pointer;
}
.btn-confirmar-aviso:hover { background: #E6B800; }
</style>
