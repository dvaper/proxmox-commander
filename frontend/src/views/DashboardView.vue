<template>
  <v-container fluid>
    <v-row>
      <!-- Statistik-Karten -->
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-icon size="48" color="primary" class="mr-4">mdi-server</v-icon>
            <div>
              <div class="text-h4">{{ stats.hosts }}</div>
              <div class="text-subtitle-1">Hosts</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-icon size="48" color="secondary" class="mr-4">mdi-folder-multiple</v-icon>
            <div>
              <div class="text-h4">{{ stats.groups }}</div>
              <div class="text-subtitle-1">Gruppen</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-icon size="48" color="info" class="mr-4">mdi-script-text</v-icon>
            <div>
              <div class="text-h4">{{ stats.playbooks }}</div>
              <div class="text-subtitle-1">Playbooks</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-icon size="48" color="success" class="mr-4">mdi-play-circle</v-icon>
            <div>
              <div class="text-h4">{{ stats.executions }}</div>
              <div class="text-subtitle-1">Ausführungen</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <!-- Schnellzugriff -->
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-lightning-bolt</v-icon>
            Schnellzugriff
          </v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item
                v-for="action in quickActions"
                :key="action.title"
                :prepend-icon="action.icon"
                :title="action.title"
                :subtitle="action.subtitle"
                @click="action.action"
              ></v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Externe Dienste -->
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-open-in-new</v-icon>
            Externe Dienste
          </v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item
                prepend-icon="mdi-ip-network-outline"
                title="NetBox IPAM"
                subtitle="IP-Adressverwaltung"
                :href="netboxUrl"
                target="_blank"
              >
                <template v-slot:append>
                  <v-icon size="small">mdi-open-in-new</v-icon>
                </template>
              </v-list-item>
            </v-list>
            <v-alert type="info" variant="tonal" density="compact" class="mt-2">
              <div class="text-caption">
                <strong>NetBox Login:</strong> (wie im Setup konfiguriert)
              </div>
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Letzte Ausführungen -->
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-history</v-icon>
            Letzte Ausführungen
          </v-card-title>
          <v-card-text>
            <v-list v-if="recentExecutions.length">
              <v-list-item
                v-for="exec in recentExecutions"
                :key="exec.id"
                :to="`/executions/${exec.id}`"
              >
                <template v-slot:prepend>
                  <v-icon :color="getStatusColor(exec.status)">
                    {{ getStatusIcon(exec.status) }}
                  </v-icon>
                </template>
                <v-list-item-title>
                  {{ exec.playbook_name || exec.tf_action }}
                </v-list-item-title>
                <v-list-item-subtitle>
                  {{ formatDate(exec.created_at) }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
            <div v-else class="text-center text-grey py-4">
              Keine Ausführungen vorhanden
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { formatDate, getStatusColor, getStatusIcon } from '@/utils/formatting'

const router = useRouter()

// NetBox URL: gleicher Host, Port 8081
const netboxUrl = computed(() => {
  const host = window.location.hostname
  return `http://${host}:8081`
})

const stats = ref({
  hosts: 0,
  groups: 0,
  playbooks: 0,
  executions: 0,
})

const recentExecutions = ref([])

const quickActions = [
  {
    icon: 'mdi-server-plus',
    title: 'Neue VM erstellen',
    subtitle: 'Terraform VM-Deployment starten',
    action: () => router.push('/terraform?action=create'),
  },
  {
    icon: 'mdi-play',
    title: 'Playbook ausführen',
    subtitle: 'Ansible-Playbook auf Hosts ausführen',
    action: () => router.push('/executions?new=1'),
  },
  {
    icon: 'mdi-server-network',
    title: 'Inventory anzeigen',
    subtitle: 'Hosts & Gruppen verwalten',
    action: () => router.push('/inventory'),
  },
  {
    icon: 'mdi-refresh',
    title: 'Inventory neu laden',
    subtitle: 'hosts.yml neu einlesen',
    action: reloadInventory,
  },
]

async function loadStats() {
  try {
    const [hosts, groups, playbooks, executions] = await Promise.all([
      api.get('/api/inventory/hosts'),
      api.get('/api/inventory/groups'),
      api.get('/api/playbooks'),
      api.get('/api/executions?page_size=5'),
    ])

    stats.value = {
      hosts: hosts.data.length,
      groups: groups.data.length,
      playbooks: playbooks.data.length,
      executions: executions.data.total,
    }

    recentExecutions.value = executions.data.items
  } catch (e) {
    console.error('Stats laden fehlgeschlagen:', e)
  }
}

async function reloadInventory() {
  try {
    await api.post('/api/inventory/reload')
    await loadStats()
  } catch (e) {
    console.error('Reload fehlgeschlagen:', e)
  }
}

onMounted(loadStats)
</script>
