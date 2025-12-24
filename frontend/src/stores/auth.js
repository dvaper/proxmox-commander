/**
 * Auth Store - Pinia Store für Authentication und Benutzer-Management
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useTheme } from 'vuetify'
import api from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(null)
  const accessSummary = ref(null)
  const currentTheme = ref(localStorage.getItem('theme') || 'blue')
  const currentDarkMode = ref(localStorage.getItem('darkMode') || 'dark')
  const currentSidebarLogo = ref(localStorage.getItem('sidebarLogo') || 'icon')

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const isSuperAdmin = computed(() => user.value?.is_super_admin ?? false)
  const canManageUsers = computed(() => isSuperAdmin.value)
  const canManageSettings = computed(() => isSuperAdmin.value)
  const accessibleGroups = computed(() => user.value?.accessible_groups ?? [])
  const accessiblePlaybooks = computed(() => user.value?.accessible_playbooks ?? [])

  // Ermittelt ob System Dark-Mode bevorzugt
  const systemPrefersDark = computed(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return true // Default: dark
  })

  // Actions
  async function login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const response = await api.post('/api/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })

    token.value = response.data.access_token
    localStorage.setItem('token', token.value)

    // User-Info laden
    await fetchUser()

    return response.data
  }

  async function fetchUser() {
    if (!token.value) return null

    try {
      const response = await api.get('/api/auth/me')
      user.value = response.data

      // Preferences laden und anwenden
      try {
        const prefsResponse = await api.get('/api/auth/me/preferences')
        applyTheme(prefsResponse.data.theme, prefsResponse.data.dark_mode)
        applySidebarLogo(prefsResponse.data.sidebar_logo)
      } catch {
        // Fallback auf User-Theme
        if (response.data.theme) {
          applyTheme(response.data.theme, 'dark')
        }
      }

      return response.data
    } catch (error) {
      // Token ungültig
      logout()
      throw error
    }
  }

  function applyTheme(themeName, darkMode = null) {
    const validThemes = ['blue', 'orange', 'green', 'purple', 'teal']
    const theme = validThemes.includes(themeName) ? themeName : 'blue'

    // Dark Mode bestimmen
    if (darkMode !== null) {
      currentDarkMode.value = darkMode
      localStorage.setItem('darkMode', darkMode)
    }

    currentTheme.value = theme
    localStorage.setItem('theme', theme)

    // Effektiven Dark-Mode bestimmen (system = System-Praeferenz)
    let isDark = true
    if (currentDarkMode.value === 'light') {
      isDark = false
    } else if (currentDarkMode.value === 'system') {
      isDark = systemPrefersDark.value
    }

    // Vuetify Theme-Name zusammensetzen: z.B. "blueDark" oder "blueLight"
    const vuetifyThemeName = theme + (isDark ? 'Dark' : 'Light')

    // Vuetify Theme setzen
    try {
      const vuetifyTheme = useTheme()
      vuetifyTheme.global.name.value = vuetifyThemeName
    } catch {
      // Vuetify noch nicht verfuegbar (wird spaeter in App.vue gesetzt)
    }
  }

  function applySidebarLogo(logoVariant) {
    const validVariants = ['icon', 'banner']
    const variant = validVariants.includes(logoVariant) ? logoVariant : 'icon'
    currentSidebarLogo.value = variant
    localStorage.setItem('sidebarLogo', variant)
  }

  async function updatePreferences(themeName = null, darkMode = null, sidebarLogo = null) {
    try {
      const payload = {}
      if (themeName !== null) payload.theme = themeName
      if (darkMode !== null) payload.dark_mode = darkMode
      if (sidebarLogo !== null) payload.sidebar_logo = sidebarLogo

      const response = await api.patch('/api/auth/me/preferences', payload)

      applyTheme(response.data.theme, response.data.dark_mode)
      applySidebarLogo(response.data.sidebar_logo)

      // User-Objekt aktualisieren
      if (user.value) {
        user.value.theme = response.data.theme
      }

      return response.data
    } catch (error) {
      console.error('Fehler beim Speichern der Einstellungen:', error)
      throw error
    }
  }

  // Legacy-Funktion fuer Rueckwaertskompatibilitaet
  async function updateTheme(themeName) {
    return updatePreferences(themeName, null)
  }

  async function fetchAccessSummary() {
    if (!token.value) return null

    try {
      const response = await api.get('/api/auth/me/access')
      accessSummary.value = response.data
      return response.data
    } catch (error) {
      console.error('Fehler beim Laden der Berechtigungen:', error)
      throw error
    }
  }

  async function changePassword(currentPassword, newPassword, confirmPassword, syncToNetbox = true) {
    const response = await api.post('/api/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
      sync_to_netbox: syncToNetbox,
    })
    return response.data
  }

  function logout() {
    token.value = null
    user.value = null
    accessSummary.value = null
    localStorage.removeItem('token')
  }

  async function initAdmin() {
    const response = await api.post('/api/auth/init')
    return response.data
  }

  // Berechtigungsprüfungen
  function canAccessGroup(groupName) {
    if (isSuperAdmin.value) return true
    return accessibleGroups.value.includes(groupName)
  }

  function canAccessPlaybook(playbookName) {
    if (isSuperAdmin.value) return true
    return accessiblePlaybooks.value.includes(playbookName)
  }

  // Token bei Start validieren
  if (token.value) {
    fetchUser().catch(() => {})
  }

  return {
    // State
    token,
    user,
    accessSummary,
    currentTheme,
    currentDarkMode,
    currentSidebarLogo,
    // Getters
    isAuthenticated,
    isSuperAdmin,
    canManageUsers,
    canManageSettings,
    accessibleGroups,
    accessiblePlaybooks,
    systemPrefersDark,
    // Actions
    login,
    logout,
    fetchUser,
    fetchAccessSummary,
    changePassword,
    initAdmin,
    canAccessGroup,
    canAccessPlaybook,
    applyTheme,
    applySidebarLogo,
    updateTheme,
    updatePreferences,
  }
})
