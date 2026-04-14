<template>
  <div class="login-container">
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
      cargando: false
    }
  },
  methods: {
    async login() {
      this.cargando = true
      this.error = ''
      try {
        const res = await axios.post('/usuarios/login', {
          email: this.email,
          password: this.password
        })
        localStorage.setItem('usuario', JSON.stringify(res.data))
        this.$router.push('/dashboard')
      } catch (e) {
        this.error = 'Correo o contraseña incorrectos'
      } finally {
        this.cargando = false
      }
    }
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
</style>
