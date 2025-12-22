<template>
  <v-app>
    <!-- Navigation (nur wenn eingeloggt) -->
    <v-navigation-drawer v-if="authStore.isAuthenticated" v-model="drawer" app>
      <v-list-item prepend-icon="mdi-server-network">
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

        <!-- Verwaltung (nur für Super-Admin) -->
        <template v-if="authStore.isSuperAdmin">
          <v-list-subheader class="mt-2">VERWALTUNG</v-list-subheader>
          <v-list-item
            to="/users"
            prepend-icon="mdi-account-group"
            title="Benutzer"
            subtitle="Benutzer & Rollen"
          ></v-list-item>
        </template>
      </v-list>

    </v-navigation-drawer>

    <!-- App Bar (nur wenn eingeloggt) -->
    <v-app-bar v-if="authStore.isAuthenticated" app elevation="1">
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
      <v-toolbar-title>{{ currentPageTitle }}</v-toolbar-title>
      <v-spacer></v-spacer>

      <!-- Git Sync Button -->
      <v-tooltip location="bottom">
        <template v-slot:activator="{ props }">
          <v-btn
            icon
            v-bind="props"
            @click="syncGit"
            :loading="gitSyncing"
            :disabled="gitSyncing"
          >
            <v-badge
              v-if="gitStatus.commits_behind > 0"
              :content="gitStatus.commits_behind"
              color="warning"
              offset-x="-2"
              offset-y="-2"
            >
              <v-icon>mdi-source-branch-sync</v-icon>
            </v-badge>
            <v-icon v-else>mdi-source-branch-sync</v-icon>
          </v-btn>
        </template>
        <span v-if="gitStatus.commits_behind > 0">
          {{ gitStatus.commits_behind }} Update(s) verfügbar - Klicken zum Sync
        </span>
        <span v-else-if="gitStatus.branch">
          Git: {{ gitStatus.branch }} (aktuell)
        </span>
        <span v-else>Git synchronisieren</span>
      </v-tooltip>

      <!-- User Menu (wie in Responsibilities) -->
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
import { ref, computed, provide, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ProfileDialog from '@/components/ProfileDialog.vue'
import changelog from '@/data/changelog.json'
import api from '@/api/client'

const appVersion = __APP_VERSION__

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const drawer = ref(true)
const profileDialog = ref(null)
const showChangelog = ref(false)

// Git Sync State
const gitSyncing = ref(false)
const gitStatus = ref({
  branch: null,
  commits_behind: 0,
  commits_ahead: 0,
})

// Mapping für Seitentitel
const pageTitles = {
  '/': 'Dashboard',
  '/terraform': 'Terraform',
  '/playbooks': 'Playbooks',
  '/inventory': 'Inventory',
  '/executions': 'Ausführungen',
  '/users': 'Benutzer',
}

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

// Git Sync Functions
const fetchGitStatus = async () => {
  if (!authStore.isAuthenticated) return
  try {
    const response = await api.get('/api/git/status')
    gitStatus.value = {
      branch: response.data.branch,
      commits_behind: response.data.commits_behind || 0,
      commits_ahead: response.data.commits_ahead || 0,
    }
  } catch (error) {
    console.warn('Git status fetch failed:', error)
  }
}

const syncGit = async () => {
  if (!authStore.isSuperAdmin) {
    showSnackbar('Nur Admins können synchronisieren', 'warning')
    return
  }

  gitSyncing.value = true
  try {
    const response = await api.post('/api/git/sync')
    if (response.data.success) {
      showSnackbar(response.data.message || 'Git synchronisiert', 'success')
      // Status aktualisieren
      await fetchGitStatus()
    } else {
      showSnackbar(response.data.error || 'Sync fehlgeschlagen', 'error')
    }
  } catch (error) {
    showSnackbar(error.response?.data?.detail || 'Sync fehlgeschlagen', 'error')
  } finally {
    gitSyncing.value = false
  }
}

// Git Status beim Login und periodisch aktualisieren
watch(() => authStore.isAuthenticated, (isAuth) => {
  if (isAuth) {
    fetchGitStatus()
  }
}, { immediate: true })

// Periodisch Git Status prüfen (alle 5 Minuten)
onMounted(() => {
  if (authStore.isAuthenticated) {
    fetchGitStatus()
  }
  setInterval(() => {
    if (authStore.isAuthenticated) {
      fetchGitStatus()
    }
  }, 5 * 60 * 1000)
})
</script>

<style>
html {
  overflow-y: auto !important;
}
</style>
