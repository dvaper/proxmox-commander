<template>
  <v-container fluid>
    <!-- Ausführungs-Dialog - Neues Layout -->
    <v-dialog v-model="showWizard" max-width="750">
      <v-card>
        <v-toolbar color="primary" density="compact">
          <v-toolbar-title>Playbook ausführen</v-toolbar-title>
          <v-spacer></v-spacer>
          <v-btn icon size="small" @click="showWizard = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>

        <v-card-text class="pa-4">
          <!-- Playbook-Auswahl -->
          <v-select
            v-model="selectedPlaybook"
            :items="playbooks"
            item-title="name"
            item-value="name"
            label="Playbook auswählen"
            prepend-inner-icon="mdi-script-text"
            density="compact"
            variant="outlined"
            hide-details
            :menu-props="{ maxHeight: 300 }"
          >
            <template v-slot:item="{ item, props }">
              <v-list-item v-bind="props" density="compact">
                <template v-slot:subtitle>
                  {{ item.raw.description || item.raw.path }}
                </template>
              </v-list-item>
            </template>
          </v-select>

          <!-- Zwei-Spalten Layout für Gruppen und Hosts -->
          <v-row class="mt-4">
            <!-- Gruppen-Spalte -->
            <v-col cols="6">
              <div class="text-subtitle-2 mb-2">
                <v-icon size="small" class="mr-1">mdi-folder-multiple</v-icon>
                Gruppen
                <v-chip v-if="selectedGroups.length" size="x-small" color="primary" class="ml-2">
                  {{ selectedGroups.length }}
                </v-chip>
              </div>
              <v-card variant="outlined" class="selection-list">
                <v-text-field
                  v-model="groupSearch"
                  placeholder="Suchen..."
                  prepend-inner-icon="mdi-magnify"
                  density="compact"
                  variant="plain"
                  hide-details
                  class="px-2"
                ></v-text-field>
                <v-divider></v-divider>
                <v-list density="compact">
                  <v-list-item
                    v-for="group in filteredGroups"
                    :key="group.name"
                    :value="group.name"
                    density="compact"
                    @click="toggleGroup(group.name)"
                  >
                    <template v-slot:prepend>
                      <v-checkbox-btn
                        :model-value="selectedGroups.includes(group.name)"
                        density="compact"
                        @click.stop="toggleGroup(group.name)"
                      ></v-checkbox-btn>
                    </template>
                    <v-list-item-title class="text-body-2">{{ group.name }}</v-list-item-title>
                    <template v-slot:append>
                      <v-chip size="x-small" variant="text">{{ group.total_hosts_count }}</v-chip>
                    </template>
                  </v-list-item>
                </v-list>
              </v-card>
            </v-col>

            <!-- Hosts-Spalte -->
            <v-col cols="6">
              <div class="text-subtitle-2 mb-2">
                <v-icon size="small" class="mr-1">mdi-server</v-icon>
                Einzelne Hosts <span class="text-grey">(optional)</span>
                <v-chip v-if="selectedHosts.length" size="x-small" color="secondary" class="ml-2">
                  {{ selectedHosts.length }}
                </v-chip>
              </div>
              <v-card variant="outlined" class="selection-list">
                <v-text-field
                  v-model="hostSearch"
                  placeholder="Suchen..."
                  prepend-inner-icon="mdi-magnify"
                  density="compact"
                  variant="plain"
                  hide-details
                  class="px-2"
                ></v-text-field>
                <v-divider></v-divider>
                <v-list density="compact">
                  <v-list-item
                    v-for="host in filteredHosts"
                    :key="host.name"
                    :value="host.name"
                    density="compact"
                    @click="toggleHost(host.name)"
                  >
                    <template v-slot:prepend>
                      <v-checkbox-btn
                        :model-value="selectedHosts.includes(host.name)"
                        density="compact"
                        @click.stop="toggleHost(host.name)"
                      ></v-checkbox-btn>
                    </template>
                    <v-list-item-title class="text-body-2">{{ host.name }}</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-card>
            </v-col>
          </v-row>

          <!-- Status-Hinweis -->
          <v-alert
            v-if="!selectedPlaybook"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            Wähle ein Playbook aus
          </v-alert>
          <v-alert
            v-else-if="!selectedGroups.length && !selectedHosts.length"
            type="warning"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            Wähle mindestens eine Gruppe oder einen Host
          </v-alert>
          <v-alert
            v-else
            type="success"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            <strong>{{ selectedPlaybook }}</strong> auf
            <span v-if="selectedGroups.length">{{ selectedGroups.length }} Gruppe(n)</span>
            <span v-if="selectedGroups.length && selectedHosts.length"> + </span>
            <span v-if="selectedHosts.length">{{ selectedHosts.length }} Host(s)</span>
          </v-alert>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showWizard = false">Abbrechen</v-btn>
          <v-btn
            color="success"
            variant="flat"
            @click="executePlaybook"
            :loading="executing"
            :disabled="!canExecute"
          >
            <v-icon start>mdi-play</v-icon>
            Ausführen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Lösch-Bestätigung Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>{{ deleteAllMode ? 'Alle Ausführungen löschen' : 'Ausführung löschen' }}</v-card-title>
        <v-card-text>
          <span v-if="deleteAllMode">
            Möchtest du wirklich <strong>alle {{ executions.length }} Ausführungen</strong> löschen?
          </span>
          <span v-else>
            Möchtest du die Ausführung <strong>#{{ deleteTarget?.id }}</strong> wirklich löschen?
          </span>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDeleteDialog = false">Abbrechen</v-btn>
          <v-btn color="error" variant="flat" @click="confirmDelete" :loading="deleting">
            Löschen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Header -->
    <v-row class="mb-4" align="center">
      <v-col>
        <v-btn color="primary" @click="openWizard()">
          <v-icon start>mdi-play</v-icon>
          Neue Ausführung
        </v-btn>
      </v-col>
      <v-col cols="auto">
        <v-btn
          v-if="executions.length > 0"
          color="error"
          variant="outlined"
          size="small"
          @click="openDeleteAll"
        >
          <v-icon start>mdi-delete-sweep</v-icon>
          Alle löschen
        </v-btn>
      </v-col>
    </v-row>

    <!-- Tabelle -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="executions"
        :loading="loading"
        :items-per-page="20"
        class="elevation-1"
      >
        <template v-slot:item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small">
            <v-icon start size="small">{{ getStatusIcon(item.status) }}</v-icon>
            {{ item.status }}
          </v-chip>
        </template>

        <template v-slot:item.execution_type="{ item }">
          <v-chip
            :color="item.execution_type === 'ansible' ? 'primary' : 'secondary'"
            size="small"
            variant="outlined"
          >
            {{ item.execution_type }}
          </v-chip>
        </template>

        <template v-slot:item.created_at="{ item }">
          <span class="text-no-wrap">{{ formatDate(item.created_at) }}</span>
        </template>

        <template v-slot:item.targets="{ item }">
          <span v-if="item.execution_type === 'ansible'">
            <v-tooltip v-if="parseTargets(item.target_groups).length" location="top">
              <template v-slot:activator="{ props }">
                <span v-bind="props" class="cursor-pointer">
                  <v-icon size="x-small" class="mr-1">mdi-folder-multiple</v-icon>
                  {{ parseTargets(item.target_groups).join(', ') }}
                </span>
              </template>
              <div class="text-caption">
                <template v-for="(group, gIdx) in parseTargets(item.target_groups)" :key="group">
                  <div class="font-weight-bold" :class="{ 'mt-2': gIdx > 0 }">{{ group }}</div>
                  <div v-if="groupHostsMap[group]?.length" class="ml-2">
                    <div v-for="host in groupHostsMap[group]" :key="host">
                      {{ host }} <span class="text-medium-emphasis">{{ hostIpMap[host] }}</span>
                    </div>
                  </div>
                  <div v-else class="ml-2 text-grey-lighten-1">(keine Hosts)</div>
                </template>
              </div>
            </v-tooltip>
            <span v-if="parseTargets(item.target_groups).length && parseTargets(item.target_hosts).length"> + </span>
            <span v-if="parseTargets(item.target_hosts).length">
              <v-icon size="x-small" class="mr-1">mdi-server</v-icon>
              {{ parseTargets(item.target_hosts).join(', ') }}
            </span>
            <span v-if="!parseTargets(item.target_groups).length && !parseTargets(item.target_hosts).length" class="text-grey">-</span>
          </span>
          <span v-else class="text-grey">-</span>
        </template>

        <template v-slot:item.duration_seconds="{ item }">
          {{ formatDuration(item.duration_seconds) }}
        </template>

        <template v-slot:item.actions="{ item }">
          <div class="d-flex flex-nowrap">
          <v-btn
            icon
            size="small"
            variant="text"
            :to="`/executions/${item.id}`"
            title="Details anzeigen"
          >
            <v-icon>mdi-eye</v-icon>
          </v-btn>
          <v-btn
            icon
            size="small"
            variant="text"
            color="primary"
            @click="rerunExecution(item)"
            title="Erneut ausführen"
            :disabled="item.execution_type !== 'ansible'"
          >
            <v-icon>mdi-replay</v-icon>
          </v-btn>
          <v-btn
            icon
            size="small"
            variant="text"
            color="error"
            @click="openDeleteSingle(item)"
            title="Löschen"
          >
            <v-icon>mdi-delete</v-icon>
          </v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useExecutionStore } from '@/stores/execution'
import api from '@/api/client'
import { formatDate, formatDuration, getStatusColor, getStatusIcon } from '@/utils/formatting'

const route = useRoute()
const router = useRouter()
const executionStore = useExecutionStore()
const showSnackbar = inject('showSnackbar')

const loading = ref(false)
const executions = ref([])
const showWizard = ref(false)
const executing = ref(false)

// Lösch-Dialog State
const showDeleteDialog = ref(false)
const deleteAllMode = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// Wizard-Daten
const hosts = ref([])
const groups = ref([])
const playbooks = ref([])

// Gruppen-Hosts-Map und Host-IP-Map für Tooltips
const groupHostsMap = ref({})
const hostIpMap = ref({})
const selectedHosts = ref([])
const selectedGroups = ref([])
const selectedPlaybook = ref(null)
const hostSearch = ref('')
const groupSearch = ref('')

// Computed: Gefilterte Gruppen für Suche
const filteredGroups = computed(() => {
  if (!groupSearch.value) return groups.value
  const search = groupSearch.value.toLowerCase()
  return groups.value.filter(g => g.name.toLowerCase().includes(search))
})

// Computed: Gefilterte Hosts für Suche
const filteredHosts = computed(() => {
  if (!hostSearch.value) return hosts.value
  const search = hostSearch.value.toLowerCase()
  return hosts.value.filter(h => h.name.toLowerCase().includes(search))
})

// Computed: Kann ausgeführt werden?
const canExecute = computed(() => {
  return selectedPlaybook.value && (selectedGroups.value.length > 0 || selectedHosts.value.length > 0)
})

// Toggle-Funktionen für Auswahl
function toggleGroup(groupName) {
  const index = selectedGroups.value.indexOf(groupName)
  if (index === -1) {
    selectedGroups.value.push(groupName)
  } else {
    selectedGroups.value.splice(index, 1)
  }
}

function toggleHost(hostName) {
  const index = selectedHosts.value.indexOf(hostName)
  if (index === -1) {
    selectedHosts.value.push(hostName)
  } else {
    selectedHosts.value.splice(index, 1)
  }
}

const headers = [
  { title: 'ID', key: 'id', width: '60px' },
  { title: 'Typ', key: 'execution_type', width: '90px' },
  { title: 'Status', key: 'status', width: '110px' },
  { title: 'Playbook/Aktion', key: 'playbook_name' },
  { title: 'Ziel', key: 'targets', width: '200px' },
  { title: 'Erstellt', key: 'created_at', width: '160px' },
  { title: 'Dauer', key: 'duration_seconds', width: '80px' },
  { title: 'Aktionen', key: 'actions', width: '150px', sortable: false },
]

async function loadData() {
  loading.value = true
  try {
    const [execResponse, groupsResponse, hostsResponse] = await Promise.all([
      api.get('/api/executions?page_size=50'),
      api.get('/api/inventory/groups'),
      api.get('/api/inventory/hosts'),
    ])
    executions.value = execResponse.data.items

    // Gruppen-Hosts-Map aufbauen
    const gMap = {}
    for (const group of groupsResponse.data) {
      gMap[group.name] = group.hosts || []
    }
    groupHostsMap.value = gMap

    // Host-IP-Map aufbauen
    const hMap = {}
    for (const host of hostsResponse.data) {
      hMap[host.name] = host.ansible_host || host.ip || ''
    }
    hostIpMap.value = hMap
  } catch (e) {
    console.error('Laden fehlgeschlagen:', e)
  } finally {
    loading.value = false
  }
}

async function openWizard(preselectedPlaybook = null, preselectedHosts = [], preselectedGroups = []) {
  // Daten laden
  const [hostsRes, groupsRes, playbooksRes] = await Promise.all([
    api.get('/api/inventory/hosts'),
    api.get('/api/inventory/groups'),
    api.get('/api/playbooks'),
  ])

  hosts.value = hostsRes.data
  groups.value = groupsRes.data
  playbooks.value = playbooksRes.data

  // Reset oder Vorauswahl
  selectedHosts.value = preselectedHosts
  selectedGroups.value = preselectedGroups
  selectedPlaybook.value = preselectedPlaybook
  hostSearch.value = ''
  groupSearch.value = ''

  showWizard.value = true
}

async function rerunExecution(execution) {
  // Wizard mit vorausgewähltem Playbook, Hosts und Gruppen öffnen
  if (execution.execution_type === 'ansible' && execution.playbook_name) {
    // JSON-Strings parsen (Backend speichert als JSON)
    let hosts = []
    let groups = []
    try {
      if (execution.target_hosts) {
        hosts = JSON.parse(execution.target_hosts)
      }
      if (execution.target_groups) {
        groups = JSON.parse(execution.target_groups)
      }
    } catch (e) {
      console.warn('Konnte Targets nicht parsen:', e)
    }
    await openWizard(execution.playbook_name, hosts, groups)
  }
}

async function executePlaybook() {
  executing.value = true
  try {
    const result = await executionStore.runAnsible({
      playbook_name: selectedPlaybook.value,
      target_hosts: selectedHosts.value.length ? selectedHosts.value : null,
      target_groups: selectedGroups.value.length ? selectedGroups.value : null,
    })

    showWizard.value = false
    router.push(`/executions/${result.id}`)
  } catch (e) {
    console.error('Ausführung fehlgeschlagen:', e)
    showSnackbar?.('Ausführung fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    executing.value = false
  }
}

// Lösch-Funktionen
function openDeleteSingle(item) {
  deleteTarget.value = item
  deleteAllMode.value = false
  showDeleteDialog.value = true
}

function openDeleteAll() {
  deleteTarget.value = null
  deleteAllMode.value = true
  showDeleteDialog.value = true
}

async function confirmDelete() {
  deleting.value = true
  try {
    if (deleteAllMode.value) {
      await api.delete('/api/executions')
      showSnackbar?.('Alle Ausführungen gelöscht', 'success')
    } else {
      await api.delete(`/api/executions/${deleteTarget.value.id}`)
      showSnackbar?.(`Ausführung #${deleteTarget.value.id} gelöscht`, 'success')
    }
    showDeleteDialog.value = false
    loadData()
  } catch (e) {
    console.error('Löschen fehlgeschlagen:', e)
    showSnackbar?.('Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    deleting.value = false
  }
}

function parseTargets(jsonStr) {
  if (!jsonStr) return []
  try {
    return JSON.parse(jsonStr)
  } catch {
    return []
  }
}

onMounted(() => {
  loadData()
  if (route.query.new === '1') {
    openWizard()
  }
})
</script>

<style scoped>
.selection-list {
  max-height: 250px;
  overflow-y: auto;
}

.selection-list .v-list {
  padding: 0;
}

.selection-list .v-list-item {
  min-height: 36px;
}

.cursor-pointer {
  cursor: pointer;
}
</style>
