/**
 * Proxmox Commander - Vue.js Entry Point
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

import App from './App.vue'
import router from './router'

// Vuetify Theme mit benutzerdefinierten Farbthemes
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'blue',
    themes: {
      // Standard-Theme (wie Ansible Commander)
      blue: {
        dark: true,
        colors: {
          primary: '#1976D2',
          secondary: '#424242',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107',
          background: '#121212',
          surface: '#1E1E1E',
        },
      },
      // Proxmox-aehnlich
      orange: {
        dark: true,
        colors: {
          primary: '#FF9800',
          secondary: '#5D4037',
          accent: '#FFAB40',
          error: '#FF5252',
          info: '#FF9800',
          success: '#4CAF50',
          warning: '#FFC107',
          background: '#121212',
          surface: '#1E1E1E',
        },
      },
      // Frisch/Modern
      green: {
        dark: true,
        colors: {
          primary: '#4CAF50',
          secondary: '#2E7D32',
          accent: '#69F0AE',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107',
          background: '#121212',
          surface: '#1E1E1E',
        },
      },
      // Unterscheidbar
      purple: {
        dark: true,
        colors: {
          primary: '#9C27B0',
          secondary: '#6A1B9A',
          accent: '#E040FB',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107',
          background: '#121212',
          surface: '#1E1E1E',
        },
      },
      // Professionell
      teal: {
        dark: true,
        colors: {
          primary: '#009688',
          secondary: '#00695C',
          accent: '#64FFDA',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107',
          background: '#121212',
          surface: '#1E1E1E',
        },
      },
      // Light-Theme (Fallback)
      light: {
        dark: false,
        colors: {
          primary: '#1976D2',
          secondary: '#424242',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107',
        },
      },
    },
  },
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)

app.mount('#app')
