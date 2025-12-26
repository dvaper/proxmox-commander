<template>
  <v-app>
    <!-- Navigation (nur wenn eingeloggt und nicht im Setup) -->
    <v-navigation-drawer v-if="authStore.isAuthenticated && !isSetupRoute" v-model="drawer" app>
      <!-- Sidebar Header: Icon oder Banner Variante -->
      <v-list-item v-if="authStore.currentSidebarLogo === 'icon'">
        <template v-slot:prepend>
          <AppLogo variant="icon" size="md" class="mr-3" />
        </template>
        <v-list-item-title>Proxmox Commander</v-list-item-title>
        <v-list-item-subtitle>
          v{{ appVersion }}
          <v-btn
            icon
            variant="text"
            size="x-small"
            class="ml-1"
            @click.stop="showChangelog = true"
          >
            <v-icon size="14">mdi-information-outline</v-icon>
            <v-tooltip activator="parent" location="right">Changelog anzeigen</v-tooltip>
          </v-btn>
        </v-list-item-subtitle>
      </v-list-item>

      <div v-else class="sidebar-banner-header">
        <v-tooltip location="right" content-class="logo-tooltip">
          <template v-slot:activator="{ props }">
            <div v-bind="props" class="sidebar-banner-logo-wrapper">
              <AppLogo variant="banner" size="md" class="sidebar-banner-logo" />
            </div>
          </template>
          <AppLogo variant="banner" size="xl" />
        </v-tooltip>
        <div class="sidebar-banner-version">
          v{{ appVersion }}
          <v-btn
            icon
            variant="text"
            size="x-small"
            class="ml-1"
            @click.stop="showChangelog = true"
          >
            <v-icon size="14">mdi-information-outline</v-icon>
            <v-tooltip activator="parent" location="right">Changelog anzeigen</v-tooltip>
          </v-btn>
        </div>
      </div>

      <v-divider></v-divider>

      <v-list nav density="compact">
        <!-- Dashboard -->
        <v-list-item
          to="/"
          prepend-icon="mdi-view-dashboard"
          title="Dashboard"
        ></v-list-item>

        <!-- Infrastruktur -->
        <v-list-subheader class="mt-2">INFRASTRUKTUR</v-list-subheader>
        <v-list-item
          to="/terraform"
          prepend-icon="mdi-server-plus"
          title="Terraform"
          subtitle="VMs erstellen & verwalten"
        ></v-list-item>

        <!-- Netzwerk -->
        <v-list-subheader class="mt-2">NETZWERK</v-list-subheader>
        <v-list-item
          to="/netbox"
          prepend-icon="mdi-ip-network"
          title="NetBox"
          subtitle="IPAM & DCIM"
        ></v-list-item>

        <!-- Ansible -->
        <v-list-subheader class="mt-2">ANSIBLE</v-list-subheader>
        <v-list-item
          to="/playbooks"
          prepend-icon="mdi-script-text"
          title="Playbooks"
          subtitle="Verfügbare Playbooks"
        ></v-list-item>
        <v-list-item
          to="/inventory"
          prepend-icon="mdi-server-network"
          title="Inventory"
          subtitle="Hosts & Gruppen"
        ></v-list-item>
        <v-list-item
          to="/executions"
          prepend-icon="mdi-history"
          title="Ausführungen"
          subtitle="Execution History"
        ></v-list-item>

        <!-- Einstellungen (nur für Super-Admin) -->
        <template v-if="authStore.isSuperAdmin">
          <v-list-subheader class="mt-2">EINSTELLUNGEN</v-list-subheader>

          <!-- Proxmox (Untermenü) -->
          <v-list-group value="proxmox">
            <template v-slot:activator="{ props }">
              <v-list-item
                v-bind="props"
                prepend-icon="mdi-server"
                title="Proxmox"
              ></v-list-item>
            </template>
            <v-list-item
              to="/settings/proxmox"
              prepend-icon="mdi-connection"
              title="Verbindung"
            ></v-list-item>
            <v-list-item
              to="/users"
              prepend-icon="mdi-account-multiple"
              title="Benutzer"
            ></v-list-item>
          </v-list-group>

          <!-- NetBox (Untermenü) -->
          <v-list-group value="netbox">
            <template v-slot:activator="{ props }">
              <v-list-item
                v-bind="props"
                prepend-icon="mdi-ip-network"
                title="NetBox"
              ></v-list-item>
            </template>
            <v-list-item
              to="/settings/netbox"
              prepend-icon="mdi-connection"
              title="Verbindung"
            ></v-list-item>
            <v-list-item
              to="/settings/netbox-users"
              prepend-icon="mdi-account-multiple"
              title="Benutzer"
            ></v-list-item>
          </v-list-group>

          <!-- Ansible (Untermenü) -->
          <v-list-group value="ansible">
            <template v-slot:activator="{ props }">
              <v-list-item
                v-bind="props"
                prepend-icon="mdi-ansible"
                title="Ansible"
              ></v-list-item>
            </template>
            <v-list-item
              to="/settings/ssh"
              prepend-icon="mdi-key-chain"
              title="SSH-Keys"
            ></v-list-item>
          </v-list-group>

          <v-list-item
            to="/settings/cloud-init"
            prepend-icon="mdi-cloud-upload"
            title="Cloud-Init"
            subtitle="SSH-Keys, Admin-User"
          ></v-list-item>
          <v-list-item
            to="/settings/notifications"
            prepend-icon="mdi-bell-cog"
            title="Benachrichtigungen"
            subtitle="E-Mail, Gotify, Webhooks"
          ></v-list-item>
          <v-list-item
            to="/settings/backup"
            prepend-icon="mdi-backup-restore"
            title="Backup & Restore"
            subtitle="Datensicherung"
          ></v-list-item>
        </template>
      </v-list>

    </v-navigation-drawer>

    <!-- App Bar (nur wenn eingeloggt und nicht im Setup) -->
    <v-app-bar v-if="authStore.isAuthenticated && !isSetupRoute" app elevation="1">
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
      <v-toolbar-title>{{ currentPageTitle }}</v-toolbar-title>
      <v-spacer></v-spacer>

      <!-- Service Status Badge -->
      <v-chip
        :color="healthStatus.color"
        size="small"
        variant="tonal"
        class="mr-2"
        @click="showHealthDetails = true"
      >
        <v-icon start size="small">{{ healthStatus.icon }}</v-icon>
        {{ healthStatus.label }}
      </v-chip>

      <!-- User Menu -->
      <v-menu>
        <template v-slot:activator="{ props }">
          <v-btn icon v-bind="props">
            <v-avatar size="32" :color="authStore.isSuperAdmin ? 'warning' : 'primary'">
              <v-icon size="20">{{ authStore.isSuperAdmin ? 'mdi-shield-crown' : 'mdi-account' }}</v-icon>
            </v-avatar>
          </v-btn>
        </template>
        <v-list>
          <v-list-item>
            <template v-slot:prepend>
              <v-avatar size="40" :color="authStore.isSuperAdmin ? 'warning' : 'primary'" class="mr-3">
                <v-icon size="24">{{ authStore.isSuperAdmin ? 'mdi-shield-crown' : 'mdi-account' }}</v-icon>
              </v-avatar>
            </template>
            <v-list-item-title>{{ authStore.user?.username }}</v-list-item-title>
            <v-list-item-subtitle>{{ authStore.isSuperAdmin ? 'Super-Admin' : 'Benutzer' }}</v-list-item-subtitle>
          </v-list-item>
          <v-divider></v-divider>
          <v-list-item @click="openProfile">
            <template v-slot:prepend>
              <v-icon>mdi-account-cog</v-icon>
            </template>
            <v-list-item-title>Mein Profil</v-list-item-title>
          </v-list-item>
          <v-list-item @click="logout">
            <template v-slot:prepend>
              <v-icon>mdi-logout</v-icon>
            </template>
            <v-list-item-title>Abmelden</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>

    <!-- Main Content -->
    <v-main>
      <router-view />
    </v-main>

    <!-- Profile Dialog -->
    <ProfileDialog ref="profileDialog" />

    <!-- Snackbar für Benachrichtigungen -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
    >
      {{ snackbar.text }}
    </v-snackbar>

    <!-- Health Status Dialog -->
    <v-dialog v-model="showHealthDetails" max-width="400">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" :color="healthStatus.color">{{ healthStatus.icon }}</v-icon>
          Service Status
        </v-card-title>
        <v-card-text>
          <v-list density="compact">
            <v-list-item v-for="(service, name) in healthData.services" :key="name">
              <template v-slot:prepend>
                <v-icon :color="getServiceColor(service.status)" size="small">
                  {{ getServiceIcon(service.status) }}
                </v-icon>
              </template>
              <v-list-item-title>{{ name.toUpperCase() }}</v-list-item-title>
              <v-list-item-subtitle>{{ service.message }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
          <v-alert v-if="healthData.status === 'starting'" type="info" variant="tonal" density="compact" class="mt-2">
            Services werden gestartet. Dies kann einige Minuten dauern...
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="fetchHealth">Aktualisieren</v-btn>
          <v-btn color="primary" @click="showHealthDetails = false">Schließen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Changelog Dialog -->
    <v-dialog v-model="showChangelog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-history</v-icon>
          Changelog
        </v-card-title>
        <v-card-text>
          <div v-for="release in changelog" :key="release.version" class="mb-4">
            <div class="text-h6 mb-2">{{ release.version }} <span class="text-caption text-grey">({{ release.date }})</span></div>
            <div v-for="(items, category) in release.changes" :key="category" class="mb-2">
              <div class="font-weight-medium text-primary">{{ category }}</div>
              <ul class="pl-4">
                <li v-for="item in items" :key="item" class="text-body-2">{{ item }}</li>
              </ul>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showChangelog = false">Schließen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-app>
</template>

<script setup>
import { ref, computed, provide, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useAuthStore } from '@/stores/auth'
import ProfileDialog from '@/components/ProfileDialog.vue'
import AppLogo from '@/components/AppLogo.vue'
import changelog from '@/data/changelog.json'
import axios from 'axios'

const appVersion = __APP_VERSION__

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const theme = useTheme()

const drawer = ref(true)

// Theme bei Aenderung anwenden (kombiniert Farbschema + Dark Mode)
watch([() => authStore.currentTheme, () => authStore.currentDarkMode], ([newTheme, newDarkMode]) => {
  if (!newTheme) return

  // Dark Mode bestimmen
  let isDark = true
  if (newDarkMode === 'light') {
    isDark = false
  } else if (newDarkMode === 'system') {
    isDark = authStore.systemPrefersDark
  }

  // Vuetify Theme-Name zusammensetzen
  const vuetifyThemeName = newTheme + (isDark ? 'Dark' : 'Light')

  if (theme.global.name.value !== vuetifyThemeName) {
    theme.global.name.value = vuetifyThemeName
  }
}, { immediate: true })
const profileDialog = ref(null)
const showChangelog = ref(false)
const showHealthDetails = ref(false)

// Health Status
const healthData = ref({
  status: 'unknown',
  services: {}
})

let healthInterval = null

const fetchHealth = async () => {
  try {
    const response = await axios.get('/api/health')
    healthData.value = response.data
  } catch (e) {
    healthData.value = {
      status: 'error',
      services: { api: { status: 'error', message: 'API not reachable' } }
    }
  }
}

const healthStatus = computed(() => {
  const status = healthData.value.status
  const statusMap = {
    healthy: { color: 'success', icon: 'mdi-check-circle', label: 'Services: Online' },
    starting: { color: 'warning', icon: 'mdi-loading mdi-spin', label: 'Services: Starting...' },
    degraded: { color: 'warning', icon: 'mdi-alert-circle', label: 'Services: Degraded' },
    error: { color: 'error', icon: 'mdi-close-circle', label: 'Services: Error' },
    unknown: { color: 'grey', icon: 'mdi-help-circle', label: 'Services: Unknown' },
  }
  return statusMap[status] || statusMap.unknown
})

const getServiceColor = (status) => {
  const colors = { healthy: 'success', starting: 'warning', degraded: 'warning', error: 'error' }
  return colors[status] || 'grey'
}

const getServiceIcon = (status) => {
  const icons = {
    healthy: 'mdi-check-circle',
    starting: 'mdi-loading mdi-spin',
    degraded: 'mdi-alert-circle',
    error: 'mdi-close-circle'
  }
  return icons[status] || 'mdi-help-circle'
}

onMounted(() => {
  fetchHealth()
  // Alle 30 Sekunden aktualisieren
  healthInterval = setInterval(fetchHealth, 30000)
})

onUnmounted(() => {
  if (healthInterval) clearInterval(healthInterval)
})

// Mapping für Seitentitel
const pageTitles = {
  '/': 'Dashboard',
  '/terraform': 'Terraform',
  '/netbox': 'NetBox',
  '/playbooks': 'Playbooks',
  '/inventory': 'Inventory',
  '/executions': 'Ausführungen',
  '/users': 'Benutzer',
  '/settings/proxmox': 'Proxmox-Verbindung',
  '/settings/netbox': 'NetBox-Verbindung',
  '/settings/netbox-users': 'NetBox-Benutzer',
  '/settings/ssh': 'SSH-Keys',
  '/settings/cloud-init': 'Cloud-Init',
  '/settings/notifications': 'Benachrichtigungen',
  '/settings/backup': 'Backup & Restore',
}

// Setup-Route erkennen (keine Navigation anzeigen)
const isSetupRoute = computed(() => route.path === '/setup')

const currentPageTitle = computed(() => {
  // Prüfe auf exakte Übereinstimmung
  if (pageTitles[route.path]) {
    return pageTitles[route.path]
  }
  // Prüfe auf Präfix (z.B. /executions/123)
  for (const [path, title] of Object.entries(pageTitles)) {
    if (path !== '/' && route.path.startsWith(path)) {
      return title
    }
  }
  return 'Proxmox Commander'
})

// Snackbar
const snackbar = ref({
  show: false,
  text: '',
  color: 'success',
})

const showSnackbar = (text, color = 'success') => {
  snackbar.value = { show: true, text, color }
}

provide('showSnackbar', showSnackbar)

// Profile
const openProfile = () => {
  profileDialog.value.open()
}

// Logout
const logout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style>
html {
  overflow-y: auto !important;
}

/* Sidebar Banner Header Styles */
.sidebar-banner-header {
  padding: 12px 16px;
  text-align: center;
}

.sidebar-banner-logo-wrapper {
  cursor: pointer;
}

.sidebar-banner-logo {
  max-width: 100%;
  height: auto;
}

.sidebar-banner-version {
  margin-top: 4px;
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Logo Tooltip Styles */
.logo-tooltip {
  background: rgba(var(--v-theme-surface), 0.98) !important;
  padding: 16px !important;
  border-radius: 8px !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
}
</style>
