<template>
  <div class="layout">
    <AppSidebar />
    <main class="contenido">
      <div class="contenido-inner">
        <div class="chuito-wrap">

          <!-- Avatar Chuito -->
          <div class="chuito-avatar-wrap">
            <div class="chuito-avatar" :class="estadoAvatar">
              <img src="/img/chuito.png"
                   alt="Chuito"
                   class="chuito-img"
                   :class="{
                     'chuito-hablando': estadoAvatar === 'hablando',
                     'chuito-feliz':    estadoAvatar === 'feliz'
                   }"
              />
            </div>
            <div class="chuito-nombre">Chuito 🔧</div>
            <div class="chuito-status">● En línea</div>
          </div>

          <!-- Chat -->
          <div class="chuito-chat" ref="chatBox">
            <div v-for="(msg, i) in conversacion" :key="i"
              :class="['burbuja', msg.tipo === 'chuito' ? 'burbuja-chuito' : 'burbuja-user']">
              <span v-html="msg.texto"></span>
            </div>
            <div v-if="escribiendo" class="burbuja burbuja-chuito typing">
              <span></span><span></span><span></span>
            </div>
          </div>

          <!-- Botones rápidos -->
          <div class="chuito-acciones" v-if="mostrarBotones">
            <button class="btn-chuito btn-rojo" @click="iniciarFlujo('venta_perdida')">
              🔴 Perdí una venta
            </button>
            <button class="btn-chuito btn-naranja" @click="iniciarFlujo('falta_producto')">
              📦 Falta un producto
            </button>
            <button class="btn-chuito btn-verde" @click="iniciarFlujo('logro')">
              ⭐ ¡Vendí bien hoy!
            </button>
            <button class="btn-chuito btn-gris" @click="iniciarFlujo('mensaje_jefe')">
              💬 Mensaje para el jefe
            </button>
          </div>

          <!-- Input de texto -->
          <div class="chuito-input-wrap" v-if="esperandoRespuesta">
            <input
              v-model="respuestaUsuario"
              @keyup.enter="enviarRespuesta"
              :placeholder="placeholderInput"
              class="chuito-input"
              ref="inputChuito"
            />
            <button @click="enviarRespuesta" class="btn-enviar-chuito">
              Enviar ➤
            </button>
          </div>

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
  name: 'Chuito',
  data() {
    return {
      usuario:             JSON.parse(localStorage.getItem('usuario') || '{}'),
      conversacion:        [],
      escribiendo:         false,
      mostrarBotones:      true,
      esperandoRespuesta:  false,
      respuestaUsuario:    '',
      placeholderInput:    'Escribe aquí...',
      estadoAvatar:        'normal',
      flujoActual:         null,
      pasoFlujo:           0,
      datosReporte:        {},
    }
  },
  mounted() {
    this.saludar()
  },
  methods: {
    async saludar() {
      await this.chuito('¡Eeepa mi llave! Soy Chuito, aquí a la orden 🔧', 800)
      await this.chuito('Hablame hermanito... si tenéis algo que contarme, decime 😄', 600)
    },

    async chuito(texto, delay = 1000) {
      this.escribiendo  = true
      this.estadoAvatar = 'hablando'
      await this.esperar(delay)
      this.escribiendo  = false
      this.estadoAvatar = 'normal'
      this.conversacion.push({ tipo: 'chuito', texto })
      this.$nextTick(() => this.scrollAbajo())
    },

    yo(texto) {
      this.conversacion.push({ tipo: 'user', texto })
      this.$nextTick(() => this.scrollAbajo())
    },

    async iniciarFlujo(tipo) {
      this.mostrarBotones = false
      this.flujoActual    = tipo
      this.pasoFlujo      = 0
      this.datosReporte   = { tipo }

      if (tipo === 'venta_perdida') {
        await this.chuito('¡Ah broma mi llave! ¿Qué producto te ganaron?')
        this.esperarInput('Nombre del producto...')
      } else if (tipo === 'falta_producto') {
        await this.chuito('Hermanito, ¿qué producto te pidieron y no tenemos?')
        this.esperarInput('Nombre del producto...')
      } else if (tipo === 'logro') {
        this.estadoAvatar = 'feliz'
        await this.chuito('¡Hermano vos sois un duro! 🔥 ¡Eso está fino! Cuéntame, ¿qué pasó?')
        this.esperarInput('Cuéntame lo que pasó...')
      } else if (tipo === 'mensaje_jefe') {
        await this.chuito('Dale hermanito, escribe tu mensaje que yo se lo hago llegar al jefe...')
        this.esperarInput('Tu mensaje...')
      }
    },

    esperarInput(placeholder) {
      this.esperandoRespuesta = true
      this.placeholderInput   = placeholder
      this.$nextTick(() => this.$refs.inputChuito?.focus())
    },

    async enviarRespuesta() {
      if (!this.respuestaUsuario.trim()) return
      const resp = this.respuestaUsuario.trim()
      this.yo(resp)
      this.respuestaUsuario      = ''
      this.esperandoRespuesta    = false
      await this.procesarRespuesta(resp)
    },

    async procesarRespuesta(resp) {
      const tipo = this.flujoActual

      if (tipo === 'venta_perdida') {
        if (this.pasoFlujo === 0) {
          this.datosReporte.producto = resp
          this.pasoFlujo++
          await this.chuito('¿Y cuánto lo conseguían más barato, hermanito? Dime el precio...')
          this.esperarInput('Precio de la competencia...')
        } else if (this.pasoFlujo === 1) {
          this.datosReporte.precio_competencia = resp
          this.pasoFlujo++
          await this.chuito('¿Dónde lo consiguieron más barato? ¿En cuál ferretería o tienda?')
          this.esperarInput('Nombre del lugar...')
        } else if (this.pasoFlujo === 2) {
          this.datosReporte.competidor = resp
          await this.enviarReporte(
            `Venta perdida: ${this.datosReporte.producto} a $${this.datosReporte.precio_competencia} en ${resp}`
          )
        }
      } else if (tipo === 'falta_producto') {
        if (this.pasoFlujo === 0) {
          this.datosReporte.producto = resp
          this.pasoFlujo++
          await this.chuito('¿Cuántos clientes lo han pedido más o menos?')
          this.esperarInput('Número aproximado...')
        } else if (this.pasoFlujo === 1) {
          this.datosReporte.clientes = resp
          await this.enviarReporte(
            `Falta producto: ${this.datosReporte.producto} — ${resp} clientes lo pidieron`
          )
        }
      } else if (tipo === 'logro' || tipo === 'mensaje_jefe') {
        await this.enviarReporte(resp)
      }
    },

    async enviarReporte(mensaje) {
      try {
        await axios.post('/chuito/mensaje', {
          tipo:     this.flujoActual,
          vendedor: this.usuario.usuario || this.usuario.nombre || 'vendedor',
          mensaje,
          detalle:  this.datosReporte,
        })
        this.estadoAvatar = 'feliz'
        if (this.flujoActual === 'logro') {
          await this.chuito('¡Hermano vos sois un duro! 🔥 ¡Eso está fino! El jefe se va a poner contento mi llave...')
        } else {
          await this.chuito('¡Listo hermanito! Ya le avisé al jefe. Tranquilo que esto no se queda así 💪')
        }
        await this.esperar(1500)
        this.estadoAvatar = 'normal'
        await this.chuito('¿Hay algo más que quieras contarme, mi llave?')
        this.mostrarBotones = true
        this.flujoActual    = null
        this.pasoFlujo      = 0
        this.datosReporte   = {}
      } catch {
        await this.chuito('Ah broma... algo falló hermanito. Intenta de nuevo 😅')
      }
    },

    esperar(ms) { return new Promise(r => setTimeout(r, ms)) },

    scrollAbajo() {
      const box = this.$refs.chatBox
      if (box) box.scrollTop = box.scrollHeight
    },
  },
}
</script>

<style scoped>
.chuito-wrap {
  max-width: 480px; margin: 0 auto;
  display: flex; flex-direction: column;
  height: calc(100vh - 120px);
  background: #FAFAF7;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}
.chuito-avatar-wrap {
  background: linear-gradient(135deg, #1A1A1A, #333);
  padding: 1.25rem;
  display: flex; flex-direction: column;
  align-items: center; gap: 0.25rem;
}
.chuito-avatar { display: flex; justify-content: center; }
.chuito-nombre { color: #FFCC00; font-weight: 800; font-size: 1.1rem; letter-spacing: 0.03em; }
.chuito-status  { color: #16A34A; font-size: 0.75rem; font-weight: 600; }
.chuito-img {
  width: 120px; height: 120px;
  object-fit: contain;
  animation: flotar 3s ease-in-out infinite;
}
@keyframes flotar {
  0%, 100% { transform: translateY(0px); }
  50%      { transform: translateY(-6px); }
}
.chuito-hablando {
  animation: hablar 0.3s ease-in-out infinite alternate;
}
@keyframes hablar {
  from { transform: translateY(0px) scale(1); }
  to   { transform: translateY(-3px) scale(1.05); }
}
.chuito-feliz {
  animation: celebrar 0.5s ease-in-out infinite alternate;
}
@keyframes celebrar {
  from { transform: translateY(0px) rotate(-3deg); }
  to   { transform: translateY(-8px) rotate(3deg); }
}

.chuito-chat {
  flex: 1; overflow-y: auto;
  padding: 1rem; display: flex;
  flex-direction: column; gap: 0.5rem;
}
.burbuja {
  max-width: 80%; padding: 0.6rem 0.9rem;
  border-radius: 12px; font-size: 0.9rem;
  line-height: 1.4; word-break: break-word;
}
.burbuja-chuito {
  background: #1A1A1A; color: #FFFFFF;
  border-radius: 4px 12px 12px 12px;
  align-self: flex-start;
}
.burbuja-user {
  background: #FFCC00; color: #1A1A1A;
  border-radius: 12px 4px 12px 12px;
  align-self: flex-end; font-weight: 600;
}
.typing { display: flex; gap: 4px; align-items: center; }
.typing span {
  width: 8px; height: 8px;
  background: #FFCC00; border-radius: 50%;
  animation: bounce 1.2s infinite;
}
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30%           { transform: translateY(-8px); }
}

.chuito-acciones {
  padding: 0.75rem;
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  border-top: 1px solid var(--borde);
  background: #FFFFFF;
}
.btn-chuito {
  padding: 0.65rem 0.5rem;
  border-radius: 10px; border: none;
  font-size: 0.82rem; font-weight: 700;
  cursor: pointer; text-align: center;
  transition: transform 0.15s;
}
.btn-chuito:hover { transform: scale(1.03); }
.btn-rojo    { background: #FEE2E2; color: #DC2626; }
.btn-naranja { background: #FEF3C7; color: #D97706; }
.btn-verde   { background: #DCFCE7; color: #15803D; }
.btn-gris    { background: #F1F5F9; color: #475569; }

.chuito-input-wrap {
  padding: 0.75rem;
  display: flex; gap: 0.5rem;
  border-top: 1px solid var(--borde);
  background: #FFFFFF;
}
.chuito-input {
  flex: 1; border: 1px solid var(--borde);
  border-radius: 20px; padding: 0.5rem 1rem;
  font-size: 0.9rem; outline: none;
}
.chuito-input:focus { border-color: #FFCC00; }
.btn-enviar-chuito {
  background: #FFCC00; color: #1A1A1A;
  border: none; border-radius: 20px;
  padding: 0.5rem 1rem; font-weight: 700;
  cursor: pointer; font-size: 0.85rem;
  white-space: nowrap;
}
</style>
