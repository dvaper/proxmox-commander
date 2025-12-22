<template>
  <v-card>
    <v-toolbar flat density="compact">
      <v-icon class="ml-2 mr-2">mdi-database-eye</v-icon>
      <v-toolbar-title class="text-body-1">Terraform State</v-toolbar-title>
      <v-spacer></v-spacer>

      <v-text-field
        v-model="searchQuery"
        prepend-inner-icon="mdi-magnify"
        label="Suchen..."
        single-line
        hide-details
        density="compact"
        variant="outlined"
        style="max-width: 250px"
        class="mr-2"
        clearable
      />

      <v-btn
        icon
        size="small"
        variant="text"
        @click="refreshState"
        :loading="refreshing"
        :disabled="loading"
        title="State aktualisieren"
      >
        <v-icon>mdi-cloud-sync</v-icon>
      </v-btn>

      <v-btn
        icon
        size="small"
        variant="text"
        @click="loadResources"
        :loading="loading"
        title="Neu laden"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
    </v-toolbar>

    <v-row no-gutters>
      <!-- Ressourcen-Liste (links) -->
      <v-col cols="12" md="5" lg="4">
        <v-list
          density="compact"
          class="resource-list"
          :style="{ maxHeight: '600px', overflowY: 'auto' }"
        >
          <v-list-subheader v-if="groupedResources.length > 0">
            {{ filteredResources.length }} Ressourcen
          </v-list-subheader>

          <template v-if="loading">
            <v-skeleton-loader type="list-item" v-for="n in 5" :key="n" />
          </template>

          <template v-else-if="groupedResources.length === 0">
            <v-list-item>
              <v-list-item-title class="text-grey">
                Keine Ressourcen im State
              </v-list-item-title>
            </v-list-item>
          </template>

          <template v-else>
            <v-list-group
              v-for="group in groupedResources"
              :key="group.module || '__root__'"
              :value="group.module || '__root__'"
            >
              <template v-slot:activator="{ props }">
                <v-list-item v-bind="props">
                  <template v-slot:prepend>
                    <v-icon size="small">mdi-puzzle</v-icon>
                  </template>
                  <v-list-item-title>
                    {{ group.module || '(Root)' }}
                    <v-chip size="x-small" class="ml-2">{{ group.resources.length }}</v-chip>
                  </v-list-item-title>
                </v-list-item>
              </template>

              <v-list-item
                v-for="resource in group.resources"
                :key="resource.address"
                :active="selectedResource?.address === resource.address"
                @click="selectResource(resource)"
                density="compact"
              >
                <template v-slot:prepend>
                  <v-icon size="small" :color="getResourceTypeColor(resource.type)">
                    {{ getResourceTypeIcon(resource.type) }}
                  </v-icon>
                </template>
                <v-list-item-title class="text-body-2">
                  {{ resource.name || resource.type }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  {{ resource.type }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list-group>
          </template>
        </v-list>
      </v-col>

      <!-- Details (rechts) -->
      <v-col cols="12" md="7" lg="8">
        <v-sheet class="pa-4" :style="{ maxHeight: '600px', overflowY: 'auto' }">
          <template v-if="!selectedResource">
            <v-alert type="info" variant="tonal">
              Wähle eine Ressource aus der Liste, um Details anzuzeigen.
            </v-alert>
          </template>

          <template v-else-if="loadingDetails">
            <v-skeleton-loader type="article" />
          </template>

          <template v-else-if="resourceDetails">
            <div class="d-flex align-center mb-4">
              <div>
                <h3 class="text-h6">{{ selectedResource.name || selectedResource.type }}</h3>
                <code class="text-caption text-grey">{{ selectedResource.address }}</code>
              </div>
              <v-spacer></v-spacer>
              <v-btn
                v-if="isAdmin"
                color="error"
                variant="outlined"
                size="small"
                @click="confirmRemove"
                :loading="removing"
              >
                <v-icon start size="small">mdi-database-remove</v-icon>
                Aus State entfernen
              </v-btn>
            </div>

            <v-divider class="mb-4" />

            <!-- Ressourcen-Typ-spezifische Anzeige -->
            <template v-if="resourceDetails.data">
              <!-- VM-spezifische Infos -->
              <v-card v-if="isVMResource" variant="outlined" class="mb-4">
                <v-card-title class="text-body-1">
                  <v-icon start size="small">mdi-server</v-icon>
                  VM-Informationen
                </v-card-title>
                <v-card-text>
                  <v-table density="compact">
                    <tbody>
                      <tr v-if="vmInfo.name">
                        <td class="text-grey" width="150">Name</td>
                        <td>{{ vmInfo.name }}</td>
                      </tr>
                      <tr v-if="vmInfo.vmid">
                        <td class="text-grey">VMID</td>
                        <td>{{ vmInfo.vmid }}</td>
                      </tr>
                      <tr v-if="vmInfo.node">
                        <td class="text-grey">Node</td>
                        <td>{{ vmInfo.node }}</td>
                      </tr>
                      <tr v-if="vmInfo.ip">
                        <td class="text-grey">IP-Adresse</td>
                        <td><code>{{ vmInfo.ip }}</code></td>
                      </tr>
                      <tr v-if="vmInfo.cores">
                        <td class="text-grey">CPUs</td>
                        <td>{{ vmInfo.cores }} Kerne</td>
                      </tr>
                      <tr v-if="vmInfo.memory">
                        <td class="text-grey">RAM</td>
                        <td>{{ formatMemory(vmInfo.memory) }}</td>
                      </tr>
                    </tbody>
                  </v-table>
                </v-card-text>
              </v-card>

              <!-- Raw JSON -->
              <v-expansion-panels variant="accordion">
                <v-expansion-panel title="Raw State Data">
                  <v-expansion-panel-text>
                    <pre class="state-json text-caption">{{ formatJson(resourceDetails.data) }}</pre>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </template>

            <!-- Raw output fallback -->
            <template v-else-if="resourceDetails.raw">
              <pre class="state-json text-caption">{{ resourceDetails.raw }}</pre>
            </template>

            <!-- Error -->
            <template v-else-if="resourceDetails.error">
              <v-alert type="error" variant="tonal">
                {{ resourceDetails.error }}
              </v-alert>
            </template>
          </template>
        </v-sheet>
      </v-col>
    </v-row>

    <!-- Entfernen-Dialog -->
    <v-dialog v-model="removeDialog" max-width="500">
      <v-card>
        <v-card-title class="text-error">
          <v-icon start color="error">mdi-database-remove</v-icon>
          Ressource aus State entfernen
        </v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            Die Ressource wird nur aus dem Terraform State entfernt,
            <strong>nicht</strong> aus der Infrastruktur!
          </v-alert>
          <p class="mb-2">Ressource:</p>
          <code class="d-block pa-2 bg-grey-darken-3 rounded">{{ selectedResource?.address }}</code>
          <p class="mt-4 text-body-2 text-grey">
            Nach dem Entfernen wird Terraform diese Ressource nicht mehr verwalten.
            Bei einem erneuten Apply wird sie als "neu" erkannt.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="removeDialog = false">Abbrechen</v-btn>
          <v-btn
            color="error"
            variant="flat"
            @click="removeResource"
            :loading="removing"
          >
            Entfernen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const showSnackbar = inject('showSnackbar')
const authStore = useAuthStore()

const loading = ref(false)
const loadingDetails = ref(false)
const refreshing = ref(false)
const removing = ref(false)
const resources = ref([])
const selectedResource = ref(null)
const resourceDetails = ref(null)
const searchQuery = ref('')
const removeDialog = ref(false)

const isAdmin = computed(() => authStore.isSuperAdmin)

// Ressourcen nach Modulen gruppieren
const groupedResources = computed(() => {
  const groups = {}

  for (const resource of filteredResources.value) {
    const key = resource.module || '__root__'
    if (!groups[key]) {
      groups[key] = {
        module: resource.module,
        resources: []
      }
    }
    groups[key].resources.push(resource)
  }

  // Nach Modul-Name sortieren
  return Object.values(groups).sort((a, b) => {
    if (!a.module) return -1
    if (!b.module) return 1
    return a.module.localeCompare(b.module)
  })
})

// Gefilterte Ressourcen
const filteredResources = computed(() => {
  if (!searchQuery.value) return resources.value

  const query = searchQuery.value.toLowerCase()
  return resources.value.filter(r =>
    r.address.toLowerCase().includes(query) ||
    r.module?.toLowerCase().includes(query) ||
    r.type?.toLowerCase().includes(query) ||
    r.name?.toLowerCase().includes(query)
  )
})

// Prüfen ob VM-Ressource
const isVMResource = computed(() => {
  if (!selectedResource.value) return false
  return selectedResource.value.type?.includes('vm') ||
         selectedResource.value.type?.includes('virtual_environment')
})

// VM-Informationen extrahieren
const vmInfo = computed(() => {
  if (!resourceDetails.value?.data) return {}

  const data = resourceDetails.value.data
  const values = data.values || data

  return {
    name: values.name || values.vm_name,
    vmid: values.vm_id || values.vmid,
    node: values.node_name || values.target_node,
    ip: extractIP(values),
    cores: values.cpu?.cores || values.cores,
    memory: values.memory?.dedicated || values.memory,
  }
})

function extractIP(values) {
  // IP aus verschiedenen möglichen Stellen extrahieren
  if (values.initialization?.ip_config?.ipv4?.address) {
    return values.initialization.ip_config.ipv4.address.split('/')[0]
  }
  if (values.ipconfig0) {
    const match = values.ipconfig0.match(/ip=([^/,]+)/)
    return match ? match[1] : null
  }
  return null
}

async function loadResources() {
  loading.value = true
  try {
    const response = await api.get('/api/terraform/state')
    resources.value = response.data
    selectedResource.value = null
    resourceDetails.value = null
  } catch (e) {
    console.error('State laden fehlgeschlagen:', e)
    showSnackbar?.('State konnte nicht geladen werden', 'error')
  } finally {
    loading.value = false
  }
}

async function selectResource(resource) {
  selectedResource.value = resource
  loadingDetails.value = true
  resourceDetails.value = null

  try {
    const encodedAddress = encodeURIComponent(resource.address)
    const response = await api.get(`/api/terraform/state/${encodedAddress}`)
    resourceDetails.value = response.data
  } catch (e) {
    console.error('Details laden fehlgeschlagen:', e)
    resourceDetails.value = { error: e.response?.data?.detail || 'Fehler beim Laden' }
  } finally {
    loadingDetails.value = false
  }
}

async function refreshState() {
  refreshing.value = true
  try {
    await api.post('/api/terraform/state/refresh')
    showSnackbar?.('State aktualisiert', 'success')
    await loadResources()
  } catch (e) {
    console.error('Refresh fehlgeschlagen:', e)
    showSnackbar?.('State-Refresh fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    refreshing.value = false
  }
}

function confirmRemove() {
  removeDialog.value = true
}

async function removeResource() {
  if (!selectedResource.value) return

  removing.value = true
  try {
    const encodedAddress = encodeURIComponent(selectedResource.value.address)
    await api.delete(`/api/terraform/state/${encodedAddress}`)
    showSnackbar?.('Ressource aus State entfernt', 'success')
    removeDialog.value = false
    selectedResource.value = null
    resourceDetails.value = null
    await loadResources()
  } catch (e) {
    console.error('Entfernen fehlgeschlagen:', e)
    showSnackbar?.('Entfernen fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    removing.value = false
  }
}

function getResourceTypeIcon(type) {
  if (!type) return 'mdi-cube-outline'

  if (type.includes('vm') || type.includes('virtual')) return 'mdi-server'
  if (type.includes('network') || type.includes('vlan')) return 'mdi-lan'
  if (type.includes('disk') || type.includes('storage')) return 'mdi-harddisk'
  if (type.includes('firewall')) return 'mdi-shield'
  if (type.includes('dns')) return 'mdi-dns'

  return 'mdi-cube-outline'
}

function getResourceTypeColor(type) {
  if (!type) return 'grey'

  if (type.includes('vm') || type.includes('virtual')) return 'primary'
  if (type.includes('network')) return 'orange'
  if (type.includes('disk')) return 'cyan'
  if (type.includes('firewall')) return 'error'

  return 'grey'
}

function formatJson(obj) {
  return JSON.stringify(obj, null, 2)
}

function formatMemory(mb) {
  if (!mb) return '-'
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(1)} GB`
  }
  return `${mb} MB`
}

onMounted(() => {
  loadResources()
})

// Expose für Parent-Komponente
defineExpose({
  loadResources,
  refreshState
})
</script>

<style scoped>
.resource-list {
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.state-json {
  background: rgba(0, 0, 0, 0.2);
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  max-height: 400px;
  overflow-y: auto;
}
</style>
