<template>
  <v-dialog v-model="dialog" max-width="800" persistent>
    <v-card>
      <v-toolbar flat density="compact" color="primary">
        <v-icon class="ml-2 mr-2">mdi-import</v-icon>
        <v-toolbar-title>VM importieren</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon @click="close" :disabled="importing">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-4">
        <!-- Schritt 1: VM auswählen -->
        <template v-if="!selectedVM">
          <v-alert type="info" variant="tonal" class="mb-4">
            Wähle eine nicht-verwaltete VM aus Proxmox zum Importieren in Terraform.
          </v-alert>

          <!-- Filter und Suche -->
          <v-row class="mb-4" dense>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="searchQuery"
                prepend-inner-icon="mdi-magnify"
                label="Suchen..."
                hide-details
                density="compact"
                variant="outlined"
                clearable
              />
            </v-col>
            <v-col cols="12" md="3">
              <v-select
                v-model="filterNode"
                :items="nodeOptions"
                label="Node"
                hide-details
                density="compact"
                variant="outlined"
                clearable
              />
            </v-col>
            <v-col cols="12" md="3">
              <v-btn
                block
                variant="outlined"
                @click="loadUnmanagedVMs"
                :loading="loading"
              >
                <v-icon start>mdi-refresh</v-icon>
                Aktualisieren
              </v-btn>
            </v-col>
          </v-row>

          <!-- VM-Liste -->
          <v-data-table
            :headers="headers"
            :items="filteredVMs"
            :loading="loading"
            density="compact"
            :items-per-page="10"
            class="elevation-1"
            @click:row="selectVM"
            hover
          >
            <template v-slot:item.status="{ item }">
              <v-chip
                :color="item.status === 'running' ? 'success' : 'grey'"
                size="small"
              >
                {{ item.status }}
              </v-chip>
            </template>

            <template v-slot:item.maxmem="{ item }">
              {{ formatMemory(item.maxmem) }}
            </template>

            <template v-slot:item.maxdisk="{ item }">
              {{ formatDisk(item.maxdisk) }}
            </template>

            <template v-slot:item.actions="{ item }">
              <v-btn
                icon
                size="small"
                variant="text"
                color="primary"
                @click.stop="selectVM(null, { item })"
              >
                <v-icon>mdi-chevron-right</v-icon>
              </v-btn>
            </template>

            <template v-slot:no-data>
              <div class="text-center pa-4">
                <v-icon size="48" color="grey">mdi-check-circle-outline</v-icon>
                <p class="mt-2">Alle VMs werden bereits von Terraform verwaltet.</p>
              </div>
            </template>
          </v-data-table>
        </template>

        <!-- Schritt 2: Import-Konfiguration -->
        <template v-else>
          <v-btn
            variant="text"
            size="small"
            class="mb-4"
            @click="selectedVM = null"
            :disabled="importing"
          >
            <v-icon start>mdi-arrow-left</v-icon>
            Zurück zur Auswahl
          </v-btn>

          <v-row>
            <v-col cols="12" md="6">
              <v-card variant="outlined">
                <v-card-title class="text-body-1">
                  <v-icon start size="small">mdi-server</v-icon>
                  Ausgewählte VM
                </v-card-title>
                <v-card-text>
                  <v-table density="compact">
                    <tbody>
                      <tr>
                        <td class="text-grey">VMID</td>
                        <td>{{ selectedVM.vmid }}</td>
                      </tr>
                      <tr>
                        <td class="text-grey">Name</td>
                        <td>{{ selectedVM.name }}</td>
                      </tr>
                      <tr>
                        <td class="text-grey">Node</td>
                        <td>{{ selectedVM.node }}</td>
                      </tr>
                      <tr>
                        <td class="text-grey">Status</td>
                        <td>
                          <v-chip
                            :color="selectedVM.status === 'running' ? 'success' : 'grey'"
                            size="small"
                          >
                            {{ selectedVM.status }}
                          </v-chip>
                        </td>
                      </tr>
                      <tr>
                        <td class="text-grey">CPU</td>
                        <td>{{ selectedVM.maxcpu }} Kerne</td>
                      </tr>
                      <tr>
                        <td class="text-grey">RAM</td>
                        <td>{{ formatMemory(selectedVM.maxmem) }}</td>
                      </tr>
                      <tr>
                        <td class="text-grey">Disk</td>
                        <td>{{ formatDisk(selectedVM.maxdisk) }}</td>
                      </tr>
                    </tbody>
                  </v-table>
                </v-card-text>
              </v-card>
            </v-col>

            <v-col cols="12" md="6">
              <v-card variant="outlined">
                <v-card-title class="text-body-1">
                  <v-icon start size="small">mdi-cog</v-icon>
                  Import-Einstellungen
                </v-card-title>
                <v-card-text>
                  <v-text-field
                    v-model="importConfig.vm_name"
                    label="VM-Name (Terraform)"
                    hint="Name für die Terraform-Verwaltung"
                    persistent-hint
                    :rules="nameRules"
                    variant="outlined"
                    density="compact"
                    class="mb-3"
                  />

                  <v-select
                    v-model="importConfig.ansible_group"
                    :items="ansibleGroups"
                    label="Ansible-Gruppe"
                    hint="Optional: In Ansible-Inventory aufnehmen"
                    persistent-hint
                    variant="outlined"
                    density="compact"
                    clearable
                    class="mb-3"
                  />

                  <v-checkbox
                    v-model="importConfig.register_netbox"
                    label="IP in NetBox registrieren"
                    hide-details
                    density="compact"
                  />
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <v-alert v-if="importError" type="error" variant="tonal" class="mt-4">
            {{ importError }}
          </v-alert>

          <v-alert v-if="importSuccess" type="success" variant="tonal" class="mt-4">
            <strong>Import erfolgreich!</strong><br>
            VM {{ importSuccess.vm_name }} ({{ importSuccess.ip_address }}) wurde importiert.
          </v-alert>
        </template>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="close" :disabled="importing">
          {{ importSuccess ? 'Schließen' : 'Abbrechen' }}
        </v-btn>
        <v-btn
          v-if="selectedVM && !importSuccess"
          color="primary"
          variant="flat"
          @click="executeImport"
          :loading="importing"
          :disabled="!isValidConfig"
        >
          <v-icon start>mdi-import</v-icon>
          Importieren
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, inject, watch } from 'vue'
import api from '@/api/client'

const emit = defineEmits(['imported'])
const showSnackbar = inject('showSnackbar')

const dialog = ref(false)
const loading = ref(false)
const importing = ref(false)
const unmanagedVMs = ref([])
const selectedVM = ref(null)
const searchQuery = ref('')
const filterNode = ref(null)
const importError = ref(null)
const importSuccess = ref(null)
const ansibleGroups = ref([])

const importConfig = ref({
  vm_name: '',
  ansible_group: '',
  register_netbox: true,
})

const headers = [
  { title: 'VMID', key: 'vmid', width: '80px' },
  { title: 'Name', key: 'name' },
  { title: 'Node', key: 'node', width: '100px' },
  { title: 'Status', key: 'status', width: '100px' },
  { title: 'CPU', key: 'maxcpu', width: '60px' },
  { title: 'RAM', key: 'maxmem', width: '80px' },
  { title: 'Disk', key: 'maxdisk', width: '80px' },
  { title: '', key: 'actions', sortable: false, width: '50px' },
]

const nameRules = [
  v => !!v || 'Name ist erforderlich',
  v => /^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/.test(v) || 'Nur Kleinbuchstaben, Zahlen und Bindestriche',
]

const nodeOptions = computed(() => {
  const nodes = new Set(unmanagedVMs.value.map(vm => vm.node))
  return Array.from(nodes).sort()
})

const filteredVMs = computed(() => {
  let vms = unmanagedVMs.value

  if (filterNode.value) {
    vms = vms.filter(vm => vm.node === filterNode.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    vms = vms.filter(vm =>
      vm.name.toLowerCase().includes(query) ||
      String(vm.vmid).includes(query) ||
      vm.node.toLowerCase().includes(query)
    )
  }

  return vms
})

const isValidConfig = computed(() => {
  if (!importConfig.value.vm_name) return false
  return /^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/.test(importConfig.value.vm_name)
})

async function loadUnmanagedVMs() {
  loading.value = true
  try {
    const response = await api.get('/api/terraform/proxmox/vms/unmanaged')
    unmanagedVMs.value = response.data
  } catch (e) {
    console.error('VMs laden fehlgeschlagen:', e)
    showSnackbar?.('VMs konnten nicht geladen werden', 'error')
  } finally {
    loading.value = false
  }
}

async function loadAnsibleGroups() {
  try {
    const response = await api.get('/api/terraform/ansible-groups')
    ansibleGroups.value = response.data
      .filter(g => g.value) // Leere Gruppe ausfiltern
      .map(g => ({ title: g.label, value: g.value }))
  } catch (e) {
    console.error('Ansible-Gruppen laden fehlgeschlagen:', e)
  }
}

function selectVM(event, { item }) {
  selectedVM.value = item
  // Name vorschlagen (bereinigt)
  importConfig.value.vm_name = item.name
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
  importError.value = null
  importSuccess.value = null
}

async function executeImport() {
  if (!selectedVM.value || !isValidConfig.value) return

  importing.value = true
  importError.value = null

  try {
    const response = await api.post('/api/terraform/import', {
      vmid: selectedVM.value.vmid,
      node: selectedVM.value.node,
      vm_name: importConfig.value.vm_name,
      ansible_group: importConfig.value.ansible_group || '',
      register_netbox: importConfig.value.register_netbox,
    })

    importSuccess.value = response.data
    showSnackbar?.(`VM '${response.data.vm_name}' erfolgreich importiert`, 'success')
    emit('imported', response.data)
  } catch (e) {
    console.error('Import fehlgeschlagen:', e)
    importError.value = e.response?.data?.detail || 'Import fehlgeschlagen'
  } finally {
    importing.value = false
  }
}

function formatMemory(bytes) {
  if (!bytes) return '-'
  const gb = bytes / (1024 * 1024 * 1024)
  if (gb >= 1) return `${gb.toFixed(1)} GB`
  const mb = bytes / (1024 * 1024)
  return `${mb.toFixed(0)} MB`
}

function formatDisk(bytes) {
  if (!bytes) return '-'
  const gb = bytes / (1024 * 1024 * 1024)
  return `${gb.toFixed(0)} GB`
}

function open() {
  dialog.value = true
  selectedVM.value = null
  importError.value = null
  importSuccess.value = null
  importConfig.value = {
    vm_name: '',
    ansible_group: '',
    register_netbox: true,
  }
  loadUnmanagedVMs()
  loadAnsibleGroups()
}

function close() {
  dialog.value = false
}

defineExpose({ open, close })
</script>
