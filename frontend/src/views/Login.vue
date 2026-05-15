<template>
  <div class="login-container">

    <!-- ══ Modal inicio de jornada ══════════════════════════════════ -->
    <div v-if="modalVisible" class="jornada-overlay">
      <div class="jornada-modal">
        <p class="jornada-titulo">Inicio de jornada</p>
        <p class="jornada-saludo">Buenos días, {{ usuarioNombre }}</p>
        <p class="jornada-fecha">{{ fechaStr }}</p>
        <p class="jornada-hora">{{ horaStr }}</p>
        <div class="jornada-tasa-wrap">
          <p class="jornada-tasa-label">Tasa BCV hoy</p>
          <p class="jornada-tasa-valor">{{ tasa ? tasa.toFixed(2) : '—' }}</p>
          <p class="jornada-tasa-unit">Bs / $1 USD</p>
        </div>
        <button class="jornada-btn" @click="confirmar">✓ Entendido, comenzar</button>
      </div>
    </div>

    <div class="login-box">
      <div class="login-header">
        <h1>Ferreutil</h1>
        <p>Sistema Administrativo</p>
      </div>
      <div class="login-form">
        <div class="field">
          <label>Correo</label>
          <input v-model="email" type="email" placeholder="tucorreo@email.com" />
        </div>
        <div class="field">
          <label>Contraseña</label>
          <input v-model="password" type="password" placeholder="••••••••" />
        </div>
        <button class="btn-entrar" @click="login" :disabled="cargando">
          {{ cargando ? 'Entrando...' : 'Entrar' }}
        </button>
        <p class="error" v-if="error">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Login',
  data() {
    return {
      email: '',
      password: '',
      error: '',
      cargando: false,
      // Modal inicio jornada
      modalVisible:  false,
      tasa:          null,
      fechaStr:      '',
      horaStr:       '',
      usuarioNombre: '',
      claveHoy:      '',
    }
  },
  methods: {
    async login() {
      this.cargando = true
      this.error = ''
      try {
        const res = await axios.post('/usuarios/login', {
          email: this.email,
          password: this.password,
        })
        const usuario = res.data
        localStorage.setItem('usuario', JSON.stringify(usuario))

        try {
          const tasaRes = await axios.get('/tasa/')
          this.tasa = tasaRes.data.tasa

          const fechaServidor = new Date(tasaRes.headers['date'])
          const ymd     = fechaServidor.toISOString().slice(0, 10)
          const userId  = usuario.id || usuario.usuario
          const clave   = `inicio_dia_${userId}_${ymd}`

          if (!localStorage.getItem(clave)) {
            this.usuarioNombre = usuario.nombre || usuario.usuario || ''
            const fmt = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }
            const raw = fechaServidor.toLocaleDateString('es', fmt)
            this.fechaStr = raw.charAt(0).toUpperCase() + raw.slice(1)
            this.horaStr  = fechaServidor.toLocaleTimeString('en-US', {
              hour: '2-digit', minute: '2-digit', hour12: true,
            })
            this.claveHoy    = clave
            this.modalVisible = true
            return
          }
        } catch { /* si falla la tasa, navegar sin modal */ }

        this.$router.push('/dashboard')
      } catch (e) {
        this.error = 'Correo o contraseña incorrectos'
      } finally {
        this.cargando = false
      }
    },
    confirmar() {
      localStorage.setItem(this.claveHoy, '1')
      this.$router.push('/dashboard')
    },
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F5F5F0;
}

.login-box {
  background: #FFFFFF;
  padding: 2.5rem;
  border-radius: 16px;
  width: 100%;
  max-width: 380px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  border-top: 4px solid #FFCC00;
  border: 1px solid #DDDDDD;
  border-top: 4px solid #FFCC00;
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-header h1 {
  color: #1A1A1A;
  font-size: 2rem;
  font-weight: 800;
  margin: 0;
}

.login-header p {
  color: #888888;
  margin: 0.4rem 0 0;
  font-size: 0.9rem;
}

.field { margin-bottom: 1.2rem; }

.field label {
  display: block;
  color: #555555;
  margin-bottom: 0.4rem;
  font-size: 0.88rem;
  font-weight: 600;
}

.field input {
  width: 100%;
  padding: 0.65rem 1rem;
  background: #FFFFFF;
  border: 1px solid #CCCCCC;
  color: #1A1A1A;
  border-radius: 8px;
  font-size: 0.95rem;
  box-sizing: border-box;
}

.field input:focus {
  outline: none;
  border-color: #FFCC00;
  box-shadow: 0 0 0 2px rgba(255,204,0,0.25);
}

.btn-entrar {
  width: 100%;
  padding: 0.85rem;
  background: #1A1A1A;
  color: #FFCC00;
  font-weight: 700;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  margin-top: 0.5rem;
}

.btn-entrar:hover { background: #333333; }
.btn-entrar:disabled { opacity: 0.55; cursor: not-allowed; }

.error {
  color: #DC2626;
  text-align: center;
  margin-top: 0.75rem;
  font-size: 0.88rem;
}

/* ── Modal inicio jornada ── */
.jornada-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.jornada-modal {
  background: #1A1A1A;
  border-radius: 16px;
  padding: 2.5rem 2rem;
  max-width: 380px;
  width: 90%;
  text-align: center;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);
  border: 1px solid #2D2D2D;
}
.jornada-titulo {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #FFCC00;
  margin: 0 0 1.5rem;
}
.jornada-saludo {
  font-size: 1.35rem;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0 0 0.4rem;
}
.jornada-fecha {
  font-size: 0.9rem;
  color: #FFFFFF;
  margin: 0 0 0.15rem;
}
.jornada-hora {
  font-size: 0.82rem;
  color: #9CA3AF;
  margin: 0 0 2rem;
}
.jornada-tasa-wrap {
  background: #111111;
  border-radius: 12px;
  padding: 1.25rem 1rem;
  margin-bottom: 2rem;
}
.jornada-tasa-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #6B7280;
  margin: 0 0 0.35rem;
}
.jornada-tasa-valor {
  font-size: 3.2rem;
  font-weight: 800;
  color: #FFCC00;
  line-height: 1;
  margin: 0 0 0.3rem;
  letter-spacing: -0.02em;
}
.jornada-tasa-unit {
  font-size: 0.75rem;
  color: #6B7280;
  margin: 0;
}
.jornada-btn {
  width: 100%;
  padding: 0.9rem;
  background: #FFCC00;
  color: #1A1A1A;
  font-weight: 700;
  font-size: 0.95rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 0.15s;
}
.jornada-btn:hover { opacity: 0.88; }
</style>
