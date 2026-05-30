<template>
  <div>
    <router-view />

    <!-- Chuito flotante (gestionador) -->
    <div v-if="!modalAvisos"
      class="chuito-flotante"
      :class="estadoChuito === 'alerta' ? 'chuito-alerta' : 'chuito-atento'"
      @click="estadoChuito === 'alerta' ? modalAvisos = true : $router.push('/chuito')">
      <div class="chuito-img-wrap">
        <img src="/chuito.png" alt="Chuito" class="chuito-flotante-img"/>
        <span v-if="estadoChuito === 'atento'" class="chuito-carpeta">📋</span>
        <span v-if="estadoChuito === 'alerta'" class="chuito-flotante-badge">
          {{ avisosGestionador.length }}
        </span>
      </div>
      <div class="chuito-flotante-burbuja">
        <span v-if="estadoChuito === 'atento'">Hermanito, cualquier falla me decís... 📋</span>
        <span v-else>{{ burbujas[burbujaIdx] }}</span>
      </div>
    </div>

    <!-- Modal avisos mejorado (gestionador) -->
    <div v-if="modalAvisos && avisosGestionador.length > 0"
      class="aviso-overlay"
      @click.self="modalAvisos = false">
      <div class="aviso-card">
        <div class="aviso-card-header">
          <img src="/chuito.png" class="aviso-header-img"/>
          <div class="aviso-card-meta">
            <span class="aviso-card-label">CHUITO</span>
            <span class="aviso-card-fecha">{{ formatFecha(avisosGestionador[avisoActualIdx]?.fecha) }}</span>
          </div>
          <span class="aviso-card-contador">{{ avisoActualIdx + 1 }}/{{ avisosGestionador.length }}</span>
        </div>
        <div class="aviso-card-body">
          <h2 class="aviso-card-titulo">{{ avisosGestionador[avisoActualIdx]?.titulo }}</h2>
          <p class="aviso-card-mensaje">{{ avisosGestionador[avisoActualIdx]?.mensaje }}</p>
        </div>
        <div class="aviso-card-footer">
          <button class="btn-leer-aviso" @click="confirmarAviso">✓ Entendido, mi llave</button>
          <small class="aviso-card-hint" v-if="avisosGestionador.length > 1">
            {{ avisosGestionador.length - avisoActualIdx - 1 }} mensaje(s) más
          </small>
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
      estadoChuito:      'atento',
      burbujas: ['¡Hablame hermanito! 💬', '¿Qué pasó mi llave? 👀', '¡Chuito al servicio! 🔧', '¿Todo bien por allá? 😄'],
      burbujaIdx:        0,
      _burbujaTimer:     null,
    }
  },
  async mounted() {
    const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
    if (usuario.rol === 'gestionador') {
      await this.cargarAvisos(usuario)
    }
    this._burbujaTimer = setInterval(() => {
      if (this.estadoChuito === 'alerta') {
        this.burbujaIdx = (this.burbujaIdx + 1) % this.burbujas.length
      }
    }, 3000)
  },
  beforeUnmount() {
    clearInterval(this._burbujaTimer)
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
          this.estadoChuito      = 'alerta'
          this.avisosGestionador = res.data
          this.avisoActualIdx    = 0
          this.modalAvisos       = true
        } else {
          this.estadoChuito = 'atento'
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

.chuito-flotante {
  position: fixed; bottom: 2rem; right: 2rem;
  z-index: 9998; cursor: pointer;
  display: flex; flex-direction: column; align-items: center;
  animation: flotarChuito 3s ease-in-out infinite;
}
@keyframes flotarChuito {
  0%, 100% { transform: translateY(0px); }
  50%      { transform: translateY(-8px); }
}
.chuito-img-wrap { position: relative; display: inline-block; }
.chuito-flotante-img {
  object-fit: contain;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.3));
  transition: transform 0.2s;
}
.chuito-flotante:hover .chuito-flotante-img { transform: scale(1.1); }
.chuito-atento .chuito-flotante-img { width: 65px; height: 65px; filter: grayscale(40%) opacity(0.85); }
.chuito-alerta .chuito-flotante-img { width: 80px; height: 80px; filter: none; }
.chuito-atento .chuito-flotante-burbuja { background: #555; color: #DDD; font-size: 0.7rem; }
.chuito-alerta .chuito-flotante-burbuja { background: #1A1A1A; color: #FFCC00; font-size: 0.75rem; }
.chuito-carpeta { position: absolute; bottom: -4px; right: -4px; font-size: 1.1rem; animation: flotarChuito 3s ease-in-out infinite; }
.chuito-flotante-badge {
  position: absolute; top: -4px; right: -4px;
  background: #DC2626; color: white;
  font-size: 0.7rem; font-weight: 800;
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  animation: pulso 1.5s infinite; border: 2px solid white;
}
@keyframes pulso {
  0%, 100% { transform: scale(1); }
  50%      { transform: scale(1.2); }
}
.chuito-flotante-burbuja {
  background: #1A1A1A; color: #FFCC00;
  font-size: 0.72rem; font-weight: 700;
  padding: 0.3rem 0.6rem; border-radius: 10px;
  margin-top: 0.3rem; white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.aviso-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.7);
  z-index: 9999;
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(3px);
}
.aviso-card {
  background: #1A1A1A; border-radius: 20px;
  width: 100%; max-width: 400px; overflow: hidden;
  box-shadow: 0 25px 60px rgba(0,0,0,0.5);
  animation: entradaAviso 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  border: 1px solid #333; margin: 1rem;
}
@keyframes entradaAviso {
  from { transform: scale(0.8) translateY(20px); opacity: 0; }
  to   { transform: scale(1) translateY(0); opacity: 1; }
}
.aviso-card-header {
  background: linear-gradient(135deg, #FFCC00, #FF9900);
  padding: 1rem 1.25rem;
  display: flex; align-items: center; gap: 0.75rem;
}
.aviso-header-img {
  width: 50px; height: 50px; object-fit: contain;
  animation: flotarChuito 3s ease-in-out infinite;
}
.aviso-card-meta { flex: 1; display: flex; flex-direction: column; gap: 0.1rem; }
.aviso-card-label { font-size: 0.65rem; font-weight: 800; color: rgba(0,0,0,0.6); letter-spacing: 0.08em; }
.aviso-card-fecha { font-size: 0.78rem; font-weight: 600; color: rgba(0,0,0,0.7); }
.aviso-card-contador { font-size: 0.72rem; font-weight: 700; background: rgba(0,0,0,0.15); padding: 0.2rem 0.5rem; border-radius: 10px; color: rgba(0,0,0,0.7); }
.aviso-card-body { padding: 1.5rem 1.25rem 1rem; }
.aviso-card-titulo { font-size: 1.1rem; font-weight: 800; color: #FFFFFF; margin: 0 0 0.65rem; line-height: 1.3; }
.aviso-card-mensaje { font-size: 0.9rem; color: #C7C5BE; line-height: 1.6; margin: 0; }
.aviso-card-footer { padding: 0.75rem 1.25rem 1.25rem; display: flex; flex-direction: column; gap: 0.4rem; }
.btn-leer-aviso {
  background: linear-gradient(135deg, #FFCC00, #FF9900);
  color: #1A1A1A; border: none; padding: 0.8rem;
  border-radius: 12px; font-weight: 800; font-size: 0.95rem;
  cursor: pointer; width: 100%;
  box-shadow: 0 4px 15px rgba(255,204,0,0.3); transition: transform 0.15s;
}
.btn-leer-aviso:hover { transform: translateY(-2px); }
.aviso-card-hint { text-align: center; color: #666; font-size: 0.72rem; }
</style>
