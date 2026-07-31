<template>
  <div class="pant-wrap">
    <div v-if="!slideActual" class="pant-vacio">
      <p>{{ cargado ? 'Sin contenido para mostrar todavía.' : 'Cargando...' }}</p>
    </div>

    <template v-else>
      <!-- Slide producto -->
      <div v-if="slideActual.tipo === 'producto'" class="pant-slide pant-producto">
        <div v-if="slideActual.codigo" class="prod-sku">{{ slideActual.codigo }}</div>
        <div class="prod-logo">
          <div class="prod-logo-badge">FERRE·ÚTIL</div>
          <div class="prod-logo-sub">INGENIERÍA FERRETERA</div>
        </div>
        <div class="prod-foto-card">
          <img :src="slideActual.foto_url" class="prod-foto" />
        </div>
        <div class="prod-info">
          <h1 class="prod-nombre">{{ slideActual.nombre }}</h1>
          <div class="prod-precio-tag">
            <span class="prod-precio">${{ Number(slideActual.precio_usd).toFixed(2) }}</span>
          </div>
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

/* ── Slide producto (fondo amarillo) ───────────────────────────────── */
/* Grid de 3 filas fijas: la fila del medio SIEMPRE mide 65% del alto total
   del cuadro, y logo/precio quedan confinados a sus propias filas de 17.5%
   arriba y abajo — así nunca pueden montarse sobre la foto. */
.pant-producto {
  display: grid;
  grid-template-rows: 17.5% 65% 17.5%;
  justify-items: center;
  background: #F5C518;
  box-sizing: border-box;
  padding: 0.8rem 1.5rem;
}

.prod-sku {
  position: absolute;
  top: 1.5rem;
  right: 2.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: #3a3000;
  font-family: monospace;
  letter-spacing: 0.05em;
}

.prod-logo {
  grid-row: 1;
  align-self: center;
  max-height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.prod-logo-badge {
  background: #0E2A47;
  color: #fff;
  font-size: clamp(1.3rem, 3.2vw, 2.3rem);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1;
  padding: 0.4rem 1.3rem;
  border-radius: 10px;
  white-space: nowrap;
}
.prod-logo-sub {
  margin-top: 0.4rem;
  font-size: clamp(0.6rem, 1.1vw, 0.85rem);
  font-weight: 600;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #FF0000;
}

.prod-foto-card {
  grid-row: 2;
  width: calc(100% + 3rem);
  margin: 0 -1.5rem;
  height: 100%;
  box-sizing: border-box;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.25);
  padding: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.prod-foto {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.prod-info {
  grid-row: 3;
  align-self: center;
  max-height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  max-width: 90%;
}
.prod-nombre {
  font-size: 1.8rem;
  font-weight: 800;
  color: #000;
  margin: 0;
  text-align: center;
  line-height: 1.15;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.prod-precio-tag {
  background: #fff;
  border-radius: 12px;
  padding: 0.4rem 1.4rem;
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
  flex-shrink: 0;
}
.prod-precio {
  font-size: 2.4rem;
  font-weight: 900;
  color: #8A5A00;
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
