<template>
  <v-container fluid>
    <!-- Statistik-Karten (unverändert) -->
    <v-row>
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
              <div class="text-subtitle-1">Ausfuehrungen</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Neues 2-spaltiges Layout -->
    <v-row>
      <!-- Linke Spalte: Schnellzugriff + Letzte Ausfuehrungen -->
      <v-col cols="12" md="6">
        <!-- Schnellzugriff -->
        <v-card class="mb-4">
          <v-card-title>
            <v-icon start>mdi-lightning-bolt</v-icon>
            Schnellzugriff
          </v-card-title>
          <v-card-text class="pt-0">
            <v-list density="compact">
              <v-list-item
                v-for="action in quickActions"
                :key="action.title"
                :prepend-icon="action.icon"
                :title="action.title"
                :subtitle="action.subtitle"
                @click="action.action"
              >
                <template v-slot:append v-if="action.isNew">
                  <v-chip size="x-small" color="success" variant="flat">NEU</v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <!-- Letzte Ausfuehrungen -->
        <v-card>
          <v-card-title>
            <v-icon start>mdi-history</v-icon>
            Letzte Ausfuehrungen
          </v-card-title>
          <v-card-text class="pt-0">
            <v-list v-if="recentExecutions.length" density="compact">
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
              Keine Ausfuehrungen vorhanden
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Rechte Spalte: Externe Dienste -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-open-in-new</v-icon>
            Externe Dienste
          </v-card-title>
          <v-card-text class="pt-0">
            <!-- Proxmox Cluster -->
            <div class="text-overline text-grey mb-1">PROXMOX {{ proxmoxNodes.length > 1 ? 'CLUSTER' : '' }}</div>
            <v-list density="compact">
              <v-list-item
                v-for="node in proxmoxNodes"
                :key="node.name"
                :href="`https://${node.ip}:8006`"
                target="_blank"
              >
                <template v-slot:prepend>
                  <v-icon :color="getNodeStatusColor(node.status)" size="small">
                    mdi-server
                  </v-icon>
                </template>
                <v-list-item-title class="d-flex align-center">
                  {{ node.name }}
                  <v-chip
                    v-if="node.status === 'online'"
                    size="x-small"
                    color="success"
                    variant="tonal"
                    class="ml-2"
                  >online</v-chip>
                  <v-chip
                    v-else-if="node.status === 'offline'"
                    size="x-small"
                    color="error"
                    variant="tonal"
                    class="ml-2"
                  >offline</v-chip>
                </v-list-item-title>
                <v-list-item-subtitle>
                  {{ node.ip }} | {{ node.cpus }} CPU | {{ node.ram_gb }} GB RAM
                </v-list-item-subtitle>
                <template v-slot:append>
                  <v-icon size="small">mdi-open-in-new</v-icon>
                </template>
              </v-list-item>
            </v-list>

            <v-divider class="my-3"></v-divider>

            <!-- Weitere Dienste -->
            <div class="text-overline text-grey mb-1">WEITERE DIENSTE</div>
            <v-list density="compact">
              <v-list-item
                v-if="netboxUrl"
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
              <v-list-item
                v-else
                prepend-icon="mdi-ip-network-outline"
                title="NetBox IPAM"
                subtitle="URL nicht konfiguriert"
                disabled
              >
                <template v-slot:append>
                  <v-chip size="x-small" color="warning" variant="tonal">Setup</v-chip>
                </template>
              </v-list-item>
            </v-list>

            <v-alert type="info" variant="tonal" density="compact" class="mt-3">
              <div class="text-caption">
                <strong>Proxmox:</strong> terraform@pve Token-Auth<br>
                <strong>NetBox:</strong> Wie im Setup konfiguriert
              </div>
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { formatDate, getStatusColor, getStatusIcon } from '@/utils/formatting'

const router = useRouter()

// NetBox URL: wird aus Settings geladen
const netboxUrl = ref(null)

const stats = ref({
  hosts: 0,
  groups: 0,
  playbooks: 0,
  executions: 0,
})

const recentExecutions = ref([])
const proxmoxNodes = ref([])

// Schnellzugriff-Aktionen (erweitert)
const quickActions = [
  {
    icon: 'mdi-server-plus',
    title: 'Neue VM erstellen',
    subtitle: 'Terraform VM-Deployment starten',
    action: () => router.push('/terraform?action=create'),
  },
  {
    icon: 'mdi-play',
    title: 'Playbook ausfuehren',
    subtitle: 'Ansible-Playbook auf Hosts ausfuehren',
    action: () => router.push('/executions?new=1'),
  },
  {
    icon: 'mdi-file-plus',
    title: 'Playbook erstellen',
    subtitle: 'Neues Ansible-Playbook anlegen',
    action: () => router.push('/playbooks?new=1'),
    isNew: true,
  },
  {
    icon: 'mdi-server-network',
    title: 'Inventory anzeigen',
    subtitle: 'Hosts & Gruppen verwalten',
    action: () => router.push('/inventory'),
  },
  {
    icon: 'mdi-sync',
    title: 'Mit Proxmox abgleichen',
    subtitle: 'IPs von VMs nach NetBox sync',
    action: () => router.push('/netbox?tab=prefixes'),
    isNew: true,
  },
  {
    icon: 'mdi-refresh',
    title: 'Inventory neu laden',
    subtitle: 'hosts.yml neu einlesen',
    action: reloadInventory,
  },
  {
    icon: 'mdi-cog-sync',
    title: 'Terraform tfvars regenerieren',
    subtitle: 'Proxmox-Credentials neu schreiben',
    action: regenerateTfvars,
  },
]

function getNodeStatusColor(status) {
  if (status === 'online') return 'success'
  if (status === 'offline') return 'error'
  return 'grey'
}

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

async function loadProxmoxNodes() {
  try {
    // Statische Node-Infos laden
    const nodesResponse = await api.get('/api/terraform/nodes')
    const nodes = nodesResponse.data

    // Live-Stats laden fuer Status
    try {
      const statsResponse = await api.get('/api/terraform/nodes/stats')
      const nodeStats = statsResponse.data

      // Stats mit Node-Infos mergen
      proxmoxNodes.value = nodes.map(node => {
        const stats = nodeStats.find(s => s.name === node.name)
        return {
          ...node,
          status: stats?.status || 'unknown',
          cpu_usage: stats?.cpu_usage || 0,
          memory_percent: stats?.memory_percent || 0,
        }
      })
    } catch (e) {
      // Falls Stats nicht verfuegbar, nur statische Infos anzeigen
      proxmoxNodes.value = nodes.map(node => ({
        ...node,
        status: 'unknown',
      }))
    }
  } catch (e) {
    console.error('Proxmox Nodes laden fehlgeschlagen:', e)
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

async function regenerateTfvars() {
  try {
    const response = await api.post('/api/terraform/regenerate-tfvars')
    if (response.data.success) {
      alert('terraform.tfvars erfolgreich regeneriert!')
    }
  } catch (e) {
    console.error('tfvars Regenerierung fehlgeschlagen:', e)
    alert('Fehler: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadNetboxUrl() {
  try {
    const response = await api.get('/api/settings/netbox-url')
    netboxUrl.value = response.data.url
  } catch (e) {
    console.error('NetBox URL laden fehlgeschlagen:', e)
  }
}

onMounted(() => {
  loadStats()
  loadProxmoxNodes()
  loadNetboxUrl()
})
</script>
