<template>
  <v-container fluid>
    <v-tabs v-model="tab" color="primary">
      <v-tab value="vms">
        <v-icon start>mdi-server-network</v-icon>
        VMs
      </v-tab>
      <v-tab value="templates">
        <v-icon start>mdi-file-document-multiple</v-icon>
        Vorlagen
      </v-tab>
      <v-tab value="state">
        <v-icon start>mdi-database-eye</v-icon>
        State
      </v-tab>
      <v-tab value="actions">
        <v-icon start>mdi-terraform</v-icon>
        Aktionen
      </v-tab>
      <v-tab value="capacity">
        <v-icon start>mdi-chart-box</v-icon>
        Kapazität
      </v-tab>
      <v-tab value="history">
        <v-icon start>mdi-history</v-icon>
        History
      </v-tab>
    </v-tabs>

    <v-tabs-window v-model="tab" class="mt-4">
      <!-- Tab: VMs -->
      <v-tabs-window-item value="vms">
        <VMList ref="vmListRef" @create="openWizard" @import="openImportDialog" />
      </v-tabs-window-item>

      <!-- Tab: Vorlagen -->
      <v-tabs-window-item value="templates">
        <VMTemplateManager ref="templateManagerRef" />
      </v-tabs-window-item>

      <!-- Tab: State -->
      <v-tabs-window-item value="state">
        <TerraformStateViewer ref="stateViewerRef" />
      </v-tabs-window-item>

      <!-- Tab: Aktionen -->
      <v-tabs-window-item value="actions">
        <v-row>
          <!-- Aktionen -->
          <v-col cols="12" md="4">
            <v-card>
              <v-card-title>
                <v-icon start color="purple">mdi-terraform</v-icon>
                Terraform Aktionen
              </v-card-title>

              <v-card-text>
                <v-btn
                  block
                  color="info"
                  class="mb-2"
                  @click="runTerraform('plan')"
                  :loading="loading"
                >
                  <v-icon start>mdi-file-search</v-icon>
                  Plan
                </v-btn>

                <v-btn
                  block
                  color="success"
                  class="mb-2"
                  @click="runTerraform('apply')"
                  :loading="loading"
                >
                  <v-icon start>mdi-check</v-icon>
                  Apply
                </v-btn>

                <v-btn
                  block
                  color="error"
                  @click="confirmDestroy"
                  :loading="loading"
                >
                  <v-icon start>mdi-delete</v-icon>
                  Destroy
                </v-btn>
              </v-card-text>
            </v-card>

            <!-- Modul-Auswahl -->
            <v-card class="mt-4">
              <v-card-title>
                <v-icon start>mdi-puzzle</v-icon>
                Module
              </v-card-title>

              <v-card-text>
                <v-radio-group v-model="selectedModule">
                  <v-radio label="Alle Module" value=""></v-radio>
                  <v-radio
                    v-for="mod in modules"
                    :key="mod.name"
                    :label="mod.name"
                    :value="mod.name"
                  ></v-radio>
                </v-radio-group>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Info-Bereich -->
          <v-col cols="12" md="8">
            <v-card>
              <v-card-title>
                <v-icon start>mdi-information</v-icon>
                Hinweise
              </v-card-title>
              <v-card-text>
                <v-alert type="info" variant="tonal" class="mb-4">
                  <strong>Plan:</strong> Zeigt welche Änderungen vorgenommen werden, ohne sie auszuführen.
                </v-alert>
                <v-alert type="success" variant="tonal" class="mb-4">
                  <strong>Apply:</strong> Führt die geplanten Änderungen aus und erstellt/ändert Ressourcen.
                </v-alert>
                <v-alert type="error" variant="tonal">
                  <strong>Destroy:</strong> Löscht alle Ressourcen (erfordert Bestätigung).
                </v-alert>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-tabs-window-item>

      <!-- Tab: Kapazität -->
      <v-tabs-window-item value="capacity">
        <CapacityDashboard />
      </v-tabs-window-item>

      <!-- Tab: History -->
      <v-tabs-window-item value="history">
        <v-tabs v-model="historySubTab" density="compact" color="secondary" class="mb-4">
          <v-tab value="vm-history">
            <v-icon start size="small">mdi-server-network</v-icon>
            VM-Änderungen
          </v-tab>
          <v-tab value="executions">
            <v-icon start size="small">mdi-console</v-icon>
            Executions
          </v-tab>
          <v-tab value="cloud-init">
            <v-icon start size="small">mdi-cloud-check</v-icon>
            Cloud-Init
          </v-tab>
        </v-tabs>

        <v-tabs-window v-model="historySubTab">
          <!-- VM-History -->
          <v-tabs-window-item value="vm-history">
            <VMHistoryViewer ref="historyViewerRef" @rollback="onHistoryRollback" />
          </v-tabs-window-item>

          <!-- Executions -->
          <v-tabs-window-item value="executions">
            <v-card>
              <v-toolbar flat density="compact">
                <v-icon class="ml-2 mr-2">mdi-console</v-icon>
                <v-toolbar-title class="text-body-1">Terraform Executions</v-toolbar-title>
                <v-spacer></v-spacer>
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  @click="loadExecutions"
                  :loading="tableLoading"
                >
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </v-toolbar>

              <v-data-table
                :headers="headers"
                :items="executions"
                :loading="tableLoading"
                density="compact"
                :items-per-page="15"
              >
                <template v-slot:item.status="{ item }">
                  <v-chip :color="getStatusColor(item.status)" size="small">
                    {{ item.status }}
                  </v-chip>
                </template>

                <template v-slot:item.tf_action="{ item }">
                  <v-chip
                    :color="getActionColor(item.tf_action)"
                    size="small"
                    variant="outlined"
                  >
                    {{ item.tf_action }}
                  </v-chip>
                </template>

                <template v-slot:item.created_at="{ item }">
                  {{ formatDate(item.created_at) }}
                </template>

                <template v-slot:item.actions="{ item }">
                  <v-btn
                    icon
                    size="small"
                    variant="text"
                    :to="`/executions/${item.id}`"
                  >
                    <v-icon>mdi-eye</v-icon>
                  </v-btn>
                </template>
              </v-data-table>
            </v-card>
          </v-tabs-window-item>

          <!-- Cloud-Init Callbacks -->
          <v-tabs-window-item value="cloud-init">
            <CloudInitCallbacks ref="cloudInitCallbacksRef" />
          </v-tabs-window-item>
        </v-tabs-window>
      </v-tabs-window-item>
    </v-tabs-window>

    <!-- Destroy Bestätigung -->
    <v-dialog v-model="destroyDialog" max-width="400">
      <v-card>
        <v-card-title class="text-error">
          <v-icon start color="error">mdi-alert</v-icon>
          Terraform Destroy
        </v-card-title>
        <v-card-text>
          <v-alert type="error" variant="tonal" class="mb-4">
            Diese Aktion zerstört Infrastruktur-Ressourcen!
          </v-alert>
          <p>
            Möchtest du wirklich <strong>terraform destroy</strong> ausführen?
            {{ selectedModule ? `(Modul: ${selectedModule})` : '(Alle Module)' }}
          </p>
          <v-text-field
            v-model="destroyConfirm"
            label="Tippe 'DESTROY' zur Bestätigung"
            variant="outlined"
            class="mt-4"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="destroyDialog = false">Abbrechen</v-btn>
          <v-btn
            color="error"
            :disabled="destroyConfirm !== 'DESTROY'"
            @click="executeDestroy"
          >
            Destroy
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- VM Deployment Wizard -->
    <VMDeploymentWizard ref="wizardRef" @created="onVMCreated" />

    <!-- VM Import Dialog -->
    <VMImportDialog ref="importDialogRef" @imported="onVMImported" />
  </v-container>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '@/api/client'
import { formatDate, getStatusColor } from '@/utils/formatting'
import VMList from '@/components/VMList.vue'
import VMDeploymentWizard from '@/components/VMDeploymentWizard.vue'
import CapacityDashboard from '@/components/CapacityDashboard.vue'
import VMTemplateManager from '@/components/VMTemplateManager.vue'
import TerraformStateViewer from '@/components/TerraformStateViewer.vue'
import VMImportDialog from '@/components/VMImportDialog.vue'
import VMHistoryViewer from '@/components/VMHistoryViewer.vue'
import CloudInitCallbacks from '@/components/CloudInitCallbacks.vue'

const router = useRouter()
const route = useRoute()
const showSnackbar = inject('showSnackbar')

const tab = ref('vms')
const historySubTab = ref('vm-history')
const loading = ref(false)
const tableLoading = ref(false)
const executions = ref([])
const modules = ref([])
const selectedModule = ref('')
const destroyDialog = ref(false)
const destroyConfirm = ref('')

const vmListRef = ref(null)
const wizardRef = ref(null)
const templateManagerRef = ref(null)
const stateViewerRef = ref(null)
const importDialogRef = ref(null)
const historyViewerRef = ref(null)
const cloudInitCallbacksRef = ref(null)

const headers = [
  { title: 'ID', key: 'id', width: '60px' },
  { title: 'Aktion', key: 'tf_action', width: '100px' },
  { title: 'Status', key: 'status', width: '100px' },
  { title: 'Modul/VM', key: 'tf_module', width: '150px' },
  { title: 'Beschreibung', key: 'playbook_name' },
  { title: 'Erstellt', key: 'created_at', width: '200px' },
  { title: '', key: 'actions', sortable: false, width: '50px' },
]

async function loadExecutions() {
  tableLoading.value = true
  try {
    const response = await api.get('/api/executions?execution_type=terraform&page_size=20')
    executions.value = response.data.items
  } catch (e) {
    console.error('Laden fehlgeschlagen:', e)
  } finally {
    tableLoading.value = false
  }
}

async function runTerraform(action) {
  loading.value = true
  try {
    const response = await api.post('/api/executions/terraform', {
      tf_action: action,
      tf_module: selectedModule.value || null,
    })
    router.push(`/executions/${response.data.id}`)
  } catch (e) {
    console.error('Terraform fehlgeschlagen:', e)
    showSnackbar?.('Fehler: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    loading.value = false
  }
}

function confirmDestroy() {
  destroyConfirm.value = ''
  destroyDialog.value = true
}

async function executeDestroy() {
  destroyDialog.value = false
  await runTerraform('destroy')
}

function openWizard() {
  wizardRef.value?.open()
}

function openImportDialog() {
  importDialogRef.value?.open()
}

function onVMCreated(vm) {
  showSnackbar?.(`VM ${vm.name} erstellt (IP: ${vm.ip_address})`, 'success')
  vmListRef.value?.loadVMs()
}

function onVMImported(vm) {
  showSnackbar?.(`VM ${vm.vm_name} importiert (IP: ${vm.ip_address})`, 'success')
  vmListRef.value?.loadVMs()
  stateViewerRef.value?.loadResources()
}

function onHistoryRollback(data) {
  showSnackbar?.('Rollback erfolgreich - terraform apply erforderlich', 'info')
  vmListRef.value?.loadVMs()
  stateViewerRef.value?.loadResources()
}

function getActionColor(action) {
  const colors = {
    plan: 'info',
    apply: 'success',
    destroy: 'error',
  }
  return colors[action] || 'grey'
}

onMounted(() => {
  loadExecutions()
  // Query-Parameter verarbeiten
  if (route.query.action === 'create') {
    openWizard()
  }
})
</script>
