<template>
  <v-container fluid>
    <!-- Header mit Aktionen -->
    <v-row class="mb-2" align="center">
      <v-col>
        <div class="d-flex align-center">
          <v-icon class="mr-2" color="primary">mdi-ip-network</v-icon>
          <span class="text-h6">NetBox IPAM</span>
        </div>
      </v-col>
      <v-col cols="auto">
        <v-btn
          color="primary"
          variant="outlined"
          size="small"
          :href="netboxUrl"
          target="_blank"
        >
          <v-icon start>mdi-open-in-new</v-icon>
          NetBox oeffnen
        </v-btn>
      </v-col>
    </v-row>

    <!-- Tabs -->
    <v-card>
      <v-tabs v-model="activeTab" color="primary">
        <v-tab value="vlans">
          <v-icon start>mdi-lan</v-icon>
          VLANs
        </v-tab>
        <v-tab value="prefixes">
          <v-icon start>mdi-ip</v-icon>
          Prefixes
        </v-tab>
        <v-tab value="import">
          <v-icon start>mdi-import</v-icon>
          Import
        </v-tab>
      </v-tabs>

      <v-divider></v-divider>

      <v-window v-model="activeTab">
        <!-- Tab: VLANs -->
        <v-window-item value="vlans">
          <v-card-text>
            <v-data-table
              :headers="vlanHeaders"
              :items="vlans"
              :loading="loadingVlans"
              density="compact"
              :items-per-page="15"
            >
              <template v-slot:top>
                <v-toolbar flat density="compact">
                  <v-toolbar-title class="text-body-1">VLANs aus NetBox</v-toolbar-title>
                  <v-spacer></v-spacer>
                  <v-btn icon variant="text" size="small" @click="loadVlans" :loading="loadingVlans">
                    <v-icon size="small">mdi-refresh</v-icon>
                  </v-btn>
                </v-toolbar>
              </template>

              <template v-slot:item.id="{ item }">
                <v-chip size="small" color="primary" variant="flat">
                  {{ item.id }}
                </v-chip>
              </template>

              <template v-slot:item.bridge="{ item }">
                <code>{{ item.bridge }}</code>
              </template>

              <template v-slot:item.prefix="{ item }">
                <code>{{ item.prefix || '-' }}</code>
              </template>
            </v-data-table>
          </v-card-text>
        </v-window-item>

        <!-- Tab: Prefixes -->
        <v-window-item value="prefixes">
          <v-card-text>
            <v-data-table
              :headers="prefixHeaders"
              :items="prefixes"
              :loading="loadingPrefixes"
              density="compact"
              :items-per-page="15"
            >
              <template v-slot:top>
                <v-toolbar flat density="compact">
                  <v-toolbar-title class="text-body-1">IP-Prefixes aus NetBox</v-toolbar-title>
                  <v-spacer></v-spacer>
                  <v-btn icon variant="text" size="small" @click="loadPrefixes" :loading="loadingPrefixes">
                    <v-icon size="small">mdi-refresh</v-icon>
                  </v-btn>
                </v-toolbar>
              </template>

              <template v-slot:item.prefix="{ item }">
                <code>{{ item.prefix }}</code>
              </template>

              <template v-slot:item.vlan="{ item }">
                <v-chip v-if="item.vlan" size="small" color="primary" variant="outlined">
                  VLAN {{ item.vlan }}
                </v-chip>
                <span v-else class="text-grey">-</span>
              </template>

              <template v-slot:item.utilization="{ item }">
                <v-progress-linear
                  :model-value="item.utilization || 0"
                  height="8"
                  rounded
                  :color="item.utilization > 80 ? 'error' : item.utilization > 50 ? 'warning' : 'success'"
                >
                </v-progress-linear>
                <span class="text-caption">{{ item.utilization || 0 }}%</span>
              </template>
            </v-data-table>
          </v-card-text>
        </v-window-item>

        <!-- Tab: Import -->
        <v-window-item value="import">
          <v-card-text>
            <v-alert type="info" variant="tonal" class="mb-4">
              <v-icon start>mdi-information</v-icon>
              Scanne Proxmox-Cluster nach VLANs und importiere sie nach NetBox.
            </v-alert>

            <v-btn
              color="primary"
              @click="scanProxmox"
              :loading="scanning"
              class="mb-4"
            >
              <v-icon start>mdi-magnify-scan</v-icon>
              Proxmox scannen
            </v-btn>

            <!-- Scan-Ergebnisse -->
            <v-data-table
              v-if="proxmoxVlans.length > 0"
              v-model="selectedVlans"
              :headers="importHeaders"
              :items="proxmoxVlans"
              show-select
              density="compact"
              :items-per-page="15"
              item-value="vlan_id"
            >
              <template v-slot:item.vlan_id="{ item }">
                <v-chip size="small" color="primary" variant="flat">
                  {{ item.vlan_id }}
                </v-chip>
              </template>

              <template v-slot:item.bridge="{ item }">
                <code>{{ item.bridge }}</code>
              </template>

              <template v-slot:item.nodes="{ item }">
                <v-chip
                  v-for="node in item.nodes"
                  :key="node"
                  size="x-small"
                  class="mr-1"
                  variant="outlined"
                >
                  {{ node }}
                </v-chip>
              </template>

              <template v-slot:item.exists_in_netbox="{ item }">
                <v-icon v-if="item.exists_in_netbox" color="success">mdi-check-circle</v-icon>
                <v-icon v-else color="warning">mdi-alert-circle-outline</v-icon>
              </template>

              <template v-slot:item.prefix="{ item }">
                <v-text-field
                  v-model="item.prefix"
                  variant="outlined"
                  density="compact"
                  hide-details
                  :placeholder="`192.168.${item.vlan_id}.0/24`"
                  style="min-width: 180px"
                  :disabled="item.exists_in_netbox"
                ></v-text-field>
              </template>
            </v-data-table>

            <!-- Import Button -->
            <v-btn
              v-if="proxmoxVlans.length > 0"
              color="success"
              @click="importVlans"
              :loading="importing"
              :disabled="selectedVlans.length === 0"
              class="mt-4"
            >
              <v-icon start>mdi-import</v-icon>
              {{ selectedVlans.length }} VLANs importieren
            </v-btn>

            <!-- Import-Ergebnis -->
            <v-alert
              v-if="importResult"
              :type="importResult.errors?.length > 0 ? 'warning' : 'success'"
              variant="tonal"
              class="mt-4"
              closable
              @click:close="importResult = null"
            >
              <div v-if="importResult.imported?.length > 0">
                <strong>Importiert:</strong> VLANs {{ importResult.imported.join(', ') }}
              </div>
              <div v-if="importResult.skipped?.length > 0">
                <strong>Uebersprungen:</strong> VLANs {{ importResult.skipped.join(', ') }} (bereits vorhanden)
              </div>
              <div v-if="importResult.errors?.length > 0">
                <strong>Fehler:</strong>
                <ul>
                  <li v-for="(error, i) in importResult.errors" :key="i">{{ error }}</li>
                </ul>
              </div>
            </v-alert>
          </v-card-text>
        </v-window-item>
      </v-window>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

// NetBox URL (gleicher Host, Port 8081)
const netboxUrl = computed(() => {
  const host = window.location.hostname
  return `http://${host}:8081`
})

// Aktiver Tab
const activeTab = ref('vlans')

// VLANs Tab
const vlans = ref([])
const loadingVlans = ref(false)
const vlanHeaders = [
  { title: 'VLAN ID', key: 'id', width: '100px' },
  { title: 'Name', key: 'name' },
  { title: 'Prefix', key: 'prefix' },
  { title: 'Bridge', key: 'bridge', width: '120px' },
]

// Prefixes Tab
const prefixes = ref([])
const loadingPrefixes = ref(false)
const prefixHeaders = [
  { title: 'Prefix', key: 'prefix' },
  { title: 'VLAN', key: 'vlan', width: '120px' },
  { title: 'Beschreibung', key: 'description' },
  { title: 'Auslastung', key: 'utilization', width: '150px' },
]

// Import Tab
const proxmoxVlans = ref([])
const selectedVlans = ref([])
const scanning = ref(false)
const importing = ref(false)
const importResult = ref(null)
const importHeaders = [
  { title: 'VLAN ID', key: 'vlan_id', width: '100px' },
  { title: 'Bridge', key: 'bridge', width: '120px' },
  { title: 'Nodes', key: 'nodes' },
  { title: 'In NetBox', key: 'exists_in_netbox', width: '100px' },
  { title: 'Prefix (editierbar)', key: 'prefix', width: '200px' },
]

// VLANs laden
async function loadVlans() {
  loadingVlans.value = true
  try {
    const response = await api.get('/api/netbox/vlans')
    vlans.value = response.data
  } catch (error) {
    console.error('Fehler beim Laden der VLANs:', error)
  } finally {
    loadingVlans.value = false
  }
}

// Prefixes laden
async function loadPrefixes() {
  loadingPrefixes.value = true
  try {
    const response = await api.get('/api/netbox/prefixes')
    prefixes.value = response.data
  } catch (error) {
    console.error('Fehler beim Laden der Prefixes:', error)
  } finally {
    loadingPrefixes.value = false
  }
}

// Proxmox scannen
async function scanProxmox() {
  scanning.value = true
  importResult.value = null
  try {
    const response = await api.get('/api/netbox/proxmox-vlans')
    proxmoxVlans.value = response.data.map(v => ({
      ...v,
      prefix: v.exists_in_netbox ? '' : `192.168.${v.vlan_id}.0/24`
    }))
    // Nur VLANs auswaehlen, die noch nicht in NetBox sind
    selectedVlans.value = proxmoxVlans.value
      .filter(v => !v.exists_in_netbox)
      .map(v => v.vlan_id)
  } catch (error) {
    console.error('Fehler beim Scannen:', error)
  } finally {
    scanning.value = false
  }
}

// VLANs importieren
async function importVlans() {
  importing.value = true
  try {
    const vlansToImport = proxmoxVlans.value
      .filter(v => selectedVlans.value.includes(v.vlan_id))
      .map(v => ({
        vlan_id: v.vlan_id,
        prefix: v.prefix || null
      }))

    const response = await api.post('/api/netbox/import-vlans', {
      vlans: vlansToImport
    })
    importResult.value = response.data

    // VLANs und Prefixes neu laden
    await loadVlans()
    await loadPrefixes()

    // Scan-Ergebnisse aktualisieren
    await scanProxmox()
  } catch (error) {
    console.error('Fehler beim Import:', error)
    importResult.value = {
      imported: [],
      skipped: [],
      errors: [error.response?.data?.detail || 'Unbekannter Fehler']
    }
  } finally {
    importing.value = false
  }
}

// Beim Laden der Komponente
onMounted(() => {
  loadVlans()
  loadPrefixes()
})
</script>
