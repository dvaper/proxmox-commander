<template>
  <v-dialog v-model="dialog" max-width="600" persistent>
    <v-card>
      <v-toolbar color="primary" dark flat>
        <v-toolbar-title>Mein Profil</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text>
        <v-tabs v-model="tab" bg-color="transparent">
          <v-tab value="profile">Profil</v-tab>
          <v-tab value="notifications">Benachrichtigungen</v-tab>
          <v-tab value="access">Berechtigungen</v-tab>
          <v-tab value="password">Passwort</v-tab>
        </v-tabs>

        <v-window v-model="tab" class="mt-4">
          <!-- Tab: Profil -->
          <v-window-item value="profile">
            <v-list density="comfortable">
              <v-list-item>
                <template v-slot:prepend>
                  <v-avatar color="primary" size="48">
                    <v-icon>mdi-account</v-icon>
                  </v-avatar>
                </template>
                <v-list-item-title class="text-h6">
                  {{ authStore.user?.username }}
                </v-list-item-title>
                <v-list-item-subtitle>
                  <v-chip
                    size="small"
                    :color="authStore.isSuperAdmin ? 'warning' : 'grey'"
                    class="mt-1"
                  >
                    {{ authStore.isSuperAdmin ? 'Super-Admin' : 'Benutzer' }}
                  </v-chip>
                </v-list-item-subtitle>
              </v-list-item>

              <v-divider class="my-3"></v-divider>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-email</v-icon>
                </template>
                <v-list-item-title>E-Mail</v-list-item-title>
                <v-list-item-subtitle>
                  {{ authStore.user?.email || 'Nicht angegeben' }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-calendar</v-icon>
                </template>
                <v-list-item-title>Erstellt am</v-list-item-title>
                <v-list-item-subtitle>
                  {{ formatDate(authStore.user?.created_at) }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-login</v-icon>
                </template>
                <v-list-item-title>Letzter Login</v-list-item-title>
                <v-list-item-subtitle>
                  {{ formatDate(authStore.user?.last_login) || 'Unbekannt' }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <!-- Theme-Auswahl -->
            <v-divider class="my-4"></v-divider>
            <div class="text-subtitle-1 mb-3">
              <v-icon start>mdi-palette</v-icon>
              Farbschema
            </div>
            <div class="d-flex flex-wrap ga-2">
              <v-btn
                v-for="theme in themes"
                :key="theme.name"
                :color="theme.color"
                :variant="authStore.currentTheme === theme.name ? 'elevated' : 'outlined'"
                size="small"
                :loading="savingPrefs && selectedTheme === theme.name"
                @click="selectTheme(theme.name)"
              >
                <v-icon v-if="authStore.currentTheme === theme.name" start size="small">mdi-check</v-icon>
                {{ theme.label }}
              </v-btn>
            </div>

            <!-- Dark Mode Auswahl -->
            <div class="text-subtitle-1 mb-3 mt-5">
              <v-icon start>mdi-theme-light-dark</v-icon>
              Erscheinungsbild
            </div>
            <div class="d-flex flex-wrap ga-2">
              <v-btn
                v-for="mode in darkModes"
                :key="mode.value"
                :variant="authStore.currentDarkMode === mode.value ? 'elevated' : 'outlined'"
                :color="authStore.currentDarkMode === mode.value ? 'primary' : undefined"
                size="small"
                :loading="savingPrefs && selectedDarkMode === mode.value"
                @click="selectDarkMode(mode.value)"
              >
                <v-icon start size="small">{{ mode.icon }}</v-icon>
                {{ mode.label }}
              </v-btn>
            </div>

            <!-- Sidebar Logo Auswahl -->
            <div class="text-subtitle-1 mb-3 mt-5">
              <v-icon start>mdi-image-size-select-large</v-icon>
              Sidebar-Logo
            </div>
            <div class="d-flex flex-wrap ga-2">
              <v-btn
                v-for="logo in sidebarLogos"
                :key="logo.value"
                :variant="authStore.currentSidebarLogo === logo.value ? 'elevated' : 'outlined'"
                :color="authStore.currentSidebarLogo === logo.value ? 'primary' : undefined"
                size="small"
                :loading="savingPrefs && selectedSidebarLogo === logo.value"
                @click="selectSidebarLogo(logo.value)"
              >
                <v-icon start size="small">{{ logo.icon }}</v-icon>
                {{ logo.label }}
              </v-btn>
            </div>
            <div class="text-caption text-grey mt-2">
              Einstellungen werden sofort angewendet und gespeichert.
            </div>
          </v-window-item>

          <!-- Tab: Benachrichtigungen -->
          <v-window-item value="notifications">
            <div v-if="loadingNotifPrefs" class="text-center py-4">
              <v-progress-circular indeterminate size="32"></v-progress-circular>
            </div>

            <template v-else>
              <!-- Kanaele -->
              <div class="text-subtitle-1 mb-3">
                <v-icon start>mdi-broadcast</v-icon>
                Kanaele
              </div>

              <v-switch
                v-model="notifPrefs.email_enabled"
                label="E-Mail-Benachrichtigungen"
                :hint="authStore.user?.email || 'Keine E-Mail hinterlegt'"
                persistent-hint
                density="compact"
                color="primary"
                class="mb-2"
                @update:model-value="saveNotifPrefs"
              ></v-switch>

              <v-switch
                v-model="notifPrefs.gotify_enabled"
                label="Gotify Push-Benachrichtigungen"
                hint="Erfordert globale Gotify-Konfiguration durch Admin"
                persistent-hint
                density="compact"
                color="primary"
                class="mb-4"
                @update:model-value="saveNotifPrefs"
              ></v-switch>

              <v-divider class="my-4"></v-divider>

              <!-- Ereignisse -->
              <div class="text-subtitle-1 mb-3">
                <v-icon start>mdi-bell</v-icon>
                Ereignisse
              </div>

              <v-row>
                <v-col cols="12" sm="6">
                  <div class="text-caption text-grey mb-2">VMs</div>
                  <v-checkbox
                    v-model="notifPrefs.notify_vm_created"
                    label="VM erstellt"
                    density="compact"
                    hide-details
                    @update:model-value="saveNotifPrefs"
                  ></v-checkbox>
                  <v-checkbox
                    v-model="notifPrefs.notify_vm_deleted"
                    label="VM geloescht"
                    density="compact"
                    hide-details
                    @update:model-value="saveNotifPrefs"
                  ></v-checkbox>
                  <v-checkbox
                    v-model="notifPrefs.notify_vm_state_change"
                    label="VM Status-Aenderung"
                    density="compact"
                    hide-details
                    @update:model-value="saveNotifPrefs"
                  ></v-checkbox>
                </v-col>
                <v-col cols="12" sm="6">
                  <div class="text-caption text-grey mb-2">Ansible & System</div>
                  <v-checkbox
                    v-model="notifPrefs.notify_ansible_completed"
                    label="Playbook erfolgreich"
                    density="compact"
                    hide-details
                    @update:model-value="saveNotifPrefs"
                  ></v-checkbox>
                  <v-checkbox
                    v-model="notifPrefs.notify_ansible_failed"
                    label="Playbook fehlgeschlagen"
                    density="compact"
                    hide-details
                    @update:model-value="saveNotifPrefs"
                  ></v-checkbox>
                  <v-checkbox
                    v-model="notifPrefs.notify_system_alerts"
                    label="System-Warnungen"
                    density="compact"
                    hide-details
                    @update:model-value="saveNotifPrefs"
                  ></v-checkbox>
                </v-col>
              </v-row>

              <v-alert
                v-if="notifPrefsSaved"
                type="success"
                variant="tonal"
                density="compact"
                class="mt-4"
              >
                Einstellungen gespeichert
              </v-alert>
            </template>
          </v-window-item>

          <!-- Tab: Berechtigungen -->
          <v-window-item value="access">
            <v-alert
              v-if="authStore.isSuperAdmin"
              type="success"
              variant="tonal"
              class="mb-4"
            >
              <v-icon start>mdi-shield-crown</v-icon>
              Als Super-Admin haben Sie Zugriff auf alle Ressourcen.
            </v-alert>

            <template v-else>
              <div class="text-subtitle-1 mb-2">
                <v-icon start>mdi-folder-multiple</v-icon>
                Freigegebene Gruppen
              </div>
              <div v-if="authStore.accessibleGroups.length" class="mb-4">
                <v-chip
                  v-for="group in authStore.accessibleGroups"
                  :key="group"
                  size="small"
                  class="mr-1 mb-1"
                  color="primary"
                  variant="outlined"
                >
                  {{ group }}
                </v-chip>
              </div>
              <v-alert v-else type="info" variant="tonal" density="compact" class="mb-4">
                Keine Gruppen freigegeben.
              </v-alert>

              <div class="text-subtitle-1 mb-2">
                <v-icon start>mdi-script-text</v-icon>
                Freigegebene Playbooks
              </div>
              <div v-if="authStore.accessiblePlaybooks.length">
                <v-chip
                  v-for="playbook in authStore.accessiblePlaybooks"
                  :key="playbook"
                  size="small"
                  class="mr-1 mb-1"
                  color="success"
                  variant="outlined"
                >
                  {{ playbook }}
                </v-chip>
              </div>
              <v-alert v-else type="info" variant="tonal" density="compact">
                Keine Playbooks freigegeben.
              </v-alert>
            </template>
          </v-window-item>

          <!-- Tab: Passwort ändern -->
          <v-window-item value="password">
            <v-form ref="passwordForm" @submit.prevent="changePassword">
              <v-text-field
                v-model="passwordData.currentPassword"
                label="Aktuelles Passwort"
                type="password"
                :rules="[v => !!v || 'Pflichtfeld']"
                prepend-icon="mdi-lock"
              ></v-text-field>

              <v-text-field
                v-model="passwordData.newPassword"
                label="Neues Passwort"
                type="password"
                :rules="[
                  v => !!v || 'Pflichtfeld',
                  v => v.length >= 8 || 'Mindestens 8 Zeichen'
                ]"
                prepend-icon="mdi-lock-plus"
              ></v-text-field>

              <v-text-field
                v-model="passwordData.confirmPassword"
                label="Neues Passwort bestätigen"
                type="password"
                :rules="[
                  v => !!v || 'Pflichtfeld',
                  v => v === passwordData.newPassword || 'Passwörter stimmen nicht überein'
                ]"
                prepend-icon="mdi-lock-check"
              ></v-text-field>

              <v-checkbox
                v-model="passwordData.syncToNetbox"
                label="Passwort auch in NetBox ändern"
                hint="Synchronisiert das Passwort mit Ihrem NetBox-Konto"
                persistent-hint
                density="compact"
                class="mt-2"
              ></v-checkbox>

              <v-btn
                color="primary"
                type="submit"
                :loading="saving"
                block
                class="mt-4"
              >
                Passwort ändern
              </v-btn>
            </v-form>
          </v-window-item>
        </v-window>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="error" variant="text" @click="logout">
          <v-icon start>mdi-logout</v-icon>
          Abmelden
        </v-btn>
        <v-btn @click="dialog = false">Schließen</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, inject, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { formatDate } from '@/utils/formatting'
import axios from 'axios'

const router = useRouter()
const authStore = useAuthStore()
const showSnackbar = inject('showSnackbar')

const dialog = ref(false)
const tab = ref('profile')
const passwordForm = ref(null)
const saving = ref(false)
const savingPrefs = ref(false)
const selectedTheme = ref('')
const selectedDarkMode = ref('')
const selectedSidebarLogo = ref('')

// Benachrichtigungspraeferenzen
const loadingNotifPrefs = ref(false)
const notifPrefsSaved = ref(false)
const notifPrefs = ref({
  email_enabled: true,
  gotify_enabled: false,
  notify_vm_created: true,
  notify_vm_deleted: true,
  notify_vm_state_change: false,
  notify_ansible_completed: true,
  notify_ansible_failed: true,
  notify_system_alerts: true,
})

// Benachrichtigungspraeferenzen laden wenn Tab gewechselt wird
watch(tab, async (newTab) => {
  if (newTab === 'notifications' && !loadingNotifPrefs.value) {
    await loadNotifPrefs()
  }
})

async function loadNotifPrefs() {
  loadingNotifPrefs.value = true
  try {
    const response = await axios.get('/api/notifications/preferences')
    notifPrefs.value = {
      email_enabled: response.data.email_enabled,
      gotify_enabled: response.data.gotify_enabled,
      notify_vm_created: response.data.notify_vm_created,
      notify_vm_deleted: response.data.notify_vm_deleted,
      notify_vm_state_change: response.data.notify_vm_state_change,
      notify_ansible_completed: response.data.notify_ansible_completed,
      notify_ansible_failed: response.data.notify_ansible_failed,
      notify_system_alerts: response.data.notify_system_alerts,
    }
  } catch (e) {
    console.error('Fehler beim Laden der Benachrichtigungspraeferenzen:', e)
  } finally {
    loadingNotifPrefs.value = false
  }
}

async function saveNotifPrefs() {
  try {
    await axios.put('/api/notifications/preferences', notifPrefs.value)
    notifPrefsSaved.value = true
    setTimeout(() => { notifPrefsSaved.value = false }, 2000)
  } catch (e) {
    showSnackbar('Fehler beim Speichern', 'error')
  }
}

// Verfuegbare Themes
const themes = [
  { name: 'blue', label: 'Blau', color: '#1976D2' },
  { name: 'orange', label: 'Orange', color: '#FF9800' },
  { name: 'green', label: 'Gruen', color: '#4CAF50' },
  { name: 'purple', label: 'Lila', color: '#9C27B0' },
  { name: 'teal', label: 'Teal', color: '#009688' },
]

// Dark Mode Optionen
const darkModes = [
  { value: 'system', label: 'System', icon: 'mdi-laptop' },
  { value: 'light', label: 'Hell', icon: 'mdi-white-balance-sunny' },
  { value: 'dark', label: 'Dunkel', icon: 'mdi-weather-night' },
]

// Sidebar Logo Optionen
const sidebarLogos = [
  { value: 'icon', label: 'Icon', icon: 'mdi-image-size-select-small' },
  { value: 'banner', label: 'Banner', icon: 'mdi-image-size-select-large' },
]

const passwordData = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
  syncToNetbox: true,  // Standardmäßig aktiviert
})

async function selectTheme(themeName) {
  if (authStore.currentTheme === themeName) return

  savingPrefs.value = true
  selectedTheme.value = themeName
  try {
    await authStore.updatePreferences(themeName, null)
    showSnackbar('Farbschema gespeichert')
  } catch (e) {
    showSnackbar('Fehler beim Speichern', 'error')
  } finally {
    savingPrefs.value = false
    selectedTheme.value = ''
  }
}

async function selectDarkMode(mode) {
  if (authStore.currentDarkMode === mode) return

  savingPrefs.value = true
  selectedDarkMode.value = mode
  try {
    await authStore.updatePreferences(null, mode)
    showSnackbar('Erscheinungsbild gespeichert')
  } catch (e) {
    showSnackbar('Fehler beim Speichern', 'error')
  } finally {
    savingPrefs.value = false
    selectedDarkMode.value = ''
  }
}

async function selectSidebarLogo(logoVariant) {
  if (authStore.currentSidebarLogo === logoVariant) return

  savingPrefs.value = true
  selectedSidebarLogo.value = logoVariant
  try {
    await authStore.updatePreferences(null, null, logoVariant)
    showSnackbar('Sidebar-Logo gespeichert')
  } catch (e) {
    showSnackbar('Fehler beim Speichern', 'error')
  } finally {
    savingPrefs.value = false
    selectedSidebarLogo.value = ''
  }
}

async function changePassword() {
  const { valid } = await passwordForm.value.validate()
  if (!valid) return

  saving.value = true
  try {
    const result = await authStore.changePassword(
      passwordData.value.currentPassword,
      passwordData.value.newPassword,
      passwordData.value.confirmPassword,
      passwordData.value.syncToNetbox
    )
    // Feedback basierend auf NetBox-Sync
    let message = 'Passwort erfolgreich geändert'
    if (result?.netbox_synced) {
      message += ' (auch in NetBox)'
    }
    showSnackbar(message)
    passwordData.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
      syncToNetbox: true,
    }
    tab.value = 'profile'
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Fehler beim Ändern des Passworts', 'error')
  } finally {
    saving.value = false
  }
}

function logout() {
  authStore.logout()
  dialog.value = false
  router.push('/login')
}

// Public API
function open() {
  tab.value = 'profile'
  passwordData.value = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
    syncToNetbox: true,
  }
  dialog.value = true
}

defineExpose({ open })
</script>
