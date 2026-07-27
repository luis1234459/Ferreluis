<template>
  <div class="pant-wrap">
    <div v-if="!slideActual" class="pant-vacio">
      <p>{{ cargado ? 'Sin contenido para mostrar todavía.' : 'Cargando...' }}</p>
    </div>

    <template v-else>
      <!-- Slide producto -->
      <div v-if="slideActual.tipo === 'producto'" class="pant-slide pant-producto">
        <img :src="slideActual.foto_url" class="pant-foto" />
        <div class="pant-info">
          <h1 class="pant-nombre">{{ slideActual.nombre }}</h1>
          <div class="pant-precio">${{ Number(slideActual.precio_usd).toFixed(2) }}</div>
          <div v-if="slideActual.codigo" class="pant-codigo">{{ slideActual.codigo }}</div>
        </div>
      </div>

      <!-- Slide oferta -->
      <div v-else-if="slideActual.tipo === 'oferta'" class="pant-slide pant-oferta">
        <span class="pant-badge-oferta">OFERTA</span>
        <img :src="slideActual.foto_url" class="pant-foto" />
        <div class="pant-info">
          <h1 class="pant-nombre">{{ slideActual.nombre }}</h1>
          <div class="pant-precios">
            <span class="pant-precio-base">${{ Number(slideActual.precio_base_usd).toFixed(2) }}</span>
            <span class="pant-precio-oferta">${{ Number(slideActual.precio_usd).toFixed(2) }}</span>
          </div>
          <div v-if="slideActual.codigo" class="pant-codigo">{{ slideActual.codigo }}</div>
        </div>
      </div>

      <!-- Slide marca -->
      <div v-else class="pant-slide pant-marca">
        <img :src="slideActual.foto_url" class="pant-foto-marca" />
        <h1 v-if="slideActual.titulo" class="pant-titulo-marca">{{ slideActual.titulo }}</h1>
      </div>
    </template>
  </div>
</template>

<script>
import axios from 'axios'

const REFRESCO_COLA_MS = 5 * 60 * 1000 // recargar contenido cada 5 minutos

export default {
  name: 'PantallaReproductor',
  data() {
    return {
      cargado:    false,
      slides:     [],
      indice:     0,
      _timerSlide:   null,
      _timerRefresco: null,
    }
  },
  computed: {
    slideActual() {
      return this.slides[this.indice] || null
    },
  },
  async mounted() {
    await this.cargarCola()
    this._timerRefresco = setInterval(this.cargarCola, REFRESCO_COLA_MS)
  },
  beforeUnmount() {
    clearTimeout(this._timerSlide)
    clearInterval(this._timerRefresco)
  },
  methods: {
    async cargarCola() {
      try {
        const id  = this.$route.params.id
        const res = await axios.get(`/pantallas/${id}/cola`)
        this.slides  = res.data.slides || []
        this.cargado = true
        if (this.indice >= this.slides.length) this.indice = 0
        if (!this._timerSlide) this.avanzar()
      } catch {
        this.cargado = true
      }
    },
    avanzar() {
      clearTimeout(this._timerSlide)
      if (!this.slides.length) return
      const segundos = this.slideActual?.segundos || 8
      this._timerSlide = setTimeout(() => {
        this.indice = (this.indice + 1) % this.slides.length
        this.avanzar()
      }, segundos * 1000)
    },
  },
}
</script>

<style scoped>
.pant-wrap {
  position: fixed; inset: 0;
  background: #000;
  color: #fff;
  overflow: hidden;
  font-family: 'Segoe UI', sans-serif;
}
.pant-vacio {
  height: 100%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem;
  color: #888;
}

.pant-slide {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
}

.pant-foto {
  max-width: 90vw;
  max-height: 62vh;
  object-fit: contain;
  border-radius: 16px;
  box-shadow: 0 20px 80px rgba(0,0,0,0.6);
}

.pant-info { text-align: center; margin-top: 2.5rem; }
.pant-nombre {
  font-size: 3.2rem;
  font-weight: 800;
  margin: 0 0 1rem;
  text-shadow: 0 2px 10px rgba(0,0,0,0.5);
}
.pant-precio {
  font-size: 5rem;
  font-weight: 900;
  color: #FFCC00;
}
.pant-precios { display: flex; align-items: baseline; justify-content: center; gap: 1.5rem; }
.pant-precio-base {
  font-size: 2.4rem;
  color: #999;
  text-decoration: line-through;
}
.pant-precio-oferta {
  font-size: 5.5rem;
  font-weight: 900;
  color: #16A34A;
}
.pant-codigo {
  margin-top: 1rem;
  font-size: 1.4rem;
  color: #ccc;
  font-family: monospace;
  letter-spacing: 0.05em;
}

.pant-badge-oferta {
  position: absolute;
  top: 3rem; right: 4rem;
  background: #DC2626;
  color: #fff;
  font-weight: 900;
  font-size: 1.6rem;
  padding: 0.6rem 1.8rem;
  border-radius: 50px;
  box-shadow: 0 8px 30px rgba(220,38,38,0.5);
  letter-spacing: 0.05em;
}

.pant-marca { padding: 0; }
.pant-foto-marca {
  width: 100%;
  height: 100%;
  object-fit: cover;
  position: absolute;
  inset: 0;
}
.pant-titulo-marca {
  position: relative;
  z-index: 1;
  font-size: 3rem;
  font-weight: 800;
  background: rgba(0,0,0,0.55);
  padding: 1rem 2.5rem;
  border-radius: 16px;
  text-shadow: 0 2px 10px rgba(0,0,0,0.5);
}
</style>
