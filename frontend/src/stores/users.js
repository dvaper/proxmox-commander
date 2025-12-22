/**
 * Users Store - Pinia Store für Benutzerverwaltung
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export const useUsersStore = defineStore('users', () => {
  // State
  const users = ref([])
  const totalUsers = ref(0)
  const loading = ref(false)
  const currentUser = ref(null)

  // Getters
  const activeUsers = computed(() => users.value.filter(u => u.is_active))
  const superAdmins = computed(() => users.value.filter(u => u.is_super_admin))

  // Actions - Users CRUD
  async function fetchUsers(options = {}) {
    loading.value = true
    try {
      const params = new URLSearchParams()
      if (options.skip) params.append('skip', options.skip)
      if (options.limit) params.append('limit', options.limit)
      if (options.search) params.append('search', options.search)

      const response = await api.get(`/api/users?${params}`)
      users.value = response.data.items
      totalUsers.value = response.data.total
      return response.data
    } finally {
      loading.value = false
    }
  }

  async function fetchUser(userId) {
    loading.value = true
    try {
      const response = await api.get(`/api/users/${userId}`)
      currentUser.value = response.data
      return response.data
    } finally {
      loading.value = false
    }
  }

  async function createUser(userData) {
    const response = await api.post('/api/users', userData)
    await fetchUsers()
    return response.data
  }

  async function updateUser(userId, userData) {
    const response = await api.put(`/api/users/${userId}`, userData)
    await fetchUsers()
    return response.data
  }

  async function deleteUser(userId) {
    await api.delete(`/api/users/${userId}`)
    await fetchUsers()
  }

  async function resetPassword(userId, newPassword) {
    const response = await api.post(`/api/users/${userId}/reset-password`, {
      new_password: newPassword,
    })
    return response.data
  }

  // Actions - Group Access
  async function setUserGroups(userId, groupNames) {
    const response = await api.put(`/api/users/${userId}/groups`, groupNames)
    return response.data
  }

  async function addUserGroup(userId, groupName) {
    const response = await api.post(`/api/users/${userId}/groups`, {
      group_name: groupName,
    })
    return response.data
  }

  async function removeUserGroup(userId, groupName) {
    await api.delete(`/api/users/${userId}/groups/${groupName}`)
  }

  // Actions - Playbook Access
  async function setUserPlaybooks(userId, playbookNames) {
    const response = await api.put(`/api/users/${userId}/playbooks`, playbookNames)
    return response.data
  }

  async function addUserPlaybook(userId, playbookName) {
    const response = await api.post(`/api/users/${userId}/playbooks`, {
      playbook_name: playbookName,
    })
    return response.data
  }

  async function removeUserPlaybook(userId, playbookName) {
    await api.delete(`/api/users/${userId}/playbooks/${playbookName}`)
  }

  // Actions - Settings
  async function fetchDefaultAccess() {
    const response = await api.get('/api/settings/defaults')
    return response.data
  }

  async function setDefaultAccess(defaults) {
    const response = await api.put('/api/settings/defaults', defaults)
    return response.data
  }

  return {
    // State
    users,
    totalUsers,
    loading,
    currentUser,
    // Getters
    activeUsers,
    superAdmins,
    // Actions - Users
    fetchUsers,
    fetchUser,
    createUser,
    updateUser,
    deleteUser,
    resetPassword,
    // Actions - Groups
    setUserGroups,
    addUserGroup,
    removeUserGroup,
    // Actions - Playbooks
    setUserPlaybooks,
    addUserPlaybook,
    removeUserPlaybook,
    // Actions - Settings
    fetchDefaultAccess,
    setDefaultAccess,
  }
})
