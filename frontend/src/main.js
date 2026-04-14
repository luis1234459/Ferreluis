import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import 'primeicons/primeicons.css'
import './assets/theme.css'
import axios from 'axios'

axios.defaults.baseURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

// Inyectar header X-Usuario-Rol en cada request según el usuario logueado
axios.interceptors.request.use(config => {
  const raw = localStorage.getItem('usuario')
  if (raw) {
    try {
      const u = JSON.parse(raw)
      if (u.rol)     config.headers['X-Usuario-Rol']     = u.rol
      if (u.id)      config.headers['X-Usuario-Id']      = u.id
      if (u.usuario) config.headers['X-Usuario-Nombre']  = u.usuario
    } catch { /* ignorar */ }
  }
  return config
})

const app = createApp(App)
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
  }
})
app.mount('#app')
