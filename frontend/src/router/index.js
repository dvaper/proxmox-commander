/**
 * Vue Router Konfiguration
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import axios from 'axios'

// Setup-Status Cache (wird beim ersten Aufruf geladen)
let setupStatusCache = null
let setupStatusLoading = null

async function checkSetupStatus() {
  // Cache verwenden wenn vorhanden
  if (setupStatusCache !== null) {
    return setupStatusCache
  }

  // Wenn bereits eine Anfrage laeuft, darauf warten
  if (setupStatusLoading) {
    return setupStatusLoading
  }

  // Status vom Backend abrufen
  setupStatusLoading = axios.get('/api/setup/status')
    .then(response => {
      setupStatusCache = response.data.setup_complete
      return setupStatusCache
    })
    .catch(() => {
      // Bei Fehler annehmen dass Setup abgeschlossen ist
      // (Backend nicht erreichbar = andere Probleme)
      return true
    })
    .finally(() => {
      setupStatusLoading = null
    })

  return setupStatusLoading
}

// Cache invalidieren (z.B. nach Setup)
export function invalidateSetupCache() {
  setupStatusCache = null
}

const routes = [
  {
    path: '/setup',
    name: 'Setup',
    component: () => import('@/views/SetupWizardView.vue'),
    meta: { requiresAuth: false, isSetupPage: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/ForgotPasswordView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('@/views/ResetPasswordView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/executions',
    name: 'Executions',
    component: () => import('@/views/ExecutionsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/executions/:id',
    name: 'ExecutionDetail',
    component: () => import('@/views/ExecutionDetailView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/playbooks',
    name: 'Playbooks',
    component: () => import('@/views/PlaybooksView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/inventory',
    name: 'Inventory',
    component: () => import('@/views/InventoryView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/terraform',
    name: 'Terraform',
    component: () => import('@/views/TerraformView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/netbox',
    name: 'NetBox',
    component: () => import('@/views/NetBoxView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('@/views/UsersView.vue'),
    meta: { requiresAuth: true, requiresSuperAdmin: true },
  },
  {
    path: '/settings/notifications',
    name: 'NotificationSettings',
    component: () => import('@/views/NotificationSettingsView.vue'),
    meta: { requiresAuth: true, requiresSuperAdmin: true },
  },
  {
    path: '/settings/cloud-init',
    name: 'CloudInitSettings',
    component: () => import('@/views/CloudInitSettingsView.vue'),
    meta: { requiresAuth: true, requiresSuperAdmin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation Guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Setup-Status pruefen (ausser auf der Setup-Seite selbst)
  if (!to.meta.isSetupPage) {
    const setupComplete = await checkSetupStatus()

    if (!setupComplete) {
      // Setup nicht abgeschlossen -> zur Setup-Seite
      next('/setup')
      return
    }
  }

  // Auf Setup-Seite aber Setup bereits abgeschlossen
  // HINWEIS: Setup-Seite ist immer erreichbar fuer erneutes Setup (Testing)
  // Der Backend-Endpoint verwendet ?force=true um das zu erlauben
  if (to.meta.isSetupPage) {
    // Setup-Seite immer erlauben - Backend regelt den Rest
    // Cache invalidieren damit der neue Status geladen wird
    invalidateSetupCache()
  }

  // Pruefen ob Authentifizierung erforderlich
  if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
    next('/login')
    return
  }

  // Pruefen ob Super-Admin erforderlich
  if (to.meta.requiresSuperAdmin && !authStore.isSuperAdmin) {
    next('/')
    return
  }

  // Login-Seite wenn bereits eingeloggt
  if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
    return
  }

  next()
})

export default router
