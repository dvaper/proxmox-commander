/**
 * Auth Store - Pinia Store für Authentication und Benutzer-Management
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(null)
  const accessSummary = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const isSuperAdmin = computed(() => user.value?.is_super_admin ?? false)
  const canManageUsers = computed(() => isSuperAdmin.value)
  const canManageSettings = computed(() => isSuperAdmin.value)
  const accessibleGroups = computed(() => user.value?.accessible_groups ?? [])
  const accessiblePlaybooks = computed(() => user.value?.accessible_playbooks ?? [])

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
      return response.data
    } catch (error) {
      // Token ungültig
      logout()
      throw error
    }
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

  async function changePassword(currentPassword, newPassword, confirmPassword) {
    const response = await api.post('/api/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
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
    // Getters
    isAuthenticated,
    isSuperAdmin,
    canManageUsers,
    canManageSettings,
    accessibleGroups,
    accessiblePlaybooks,
    // Actions
    login,
    logout,
    fetchUser,
    fetchAccessSummary,
    changePassword,
    initAdmin,
    canAccessGroup,
    canAccessPlaybook,
  }
})
