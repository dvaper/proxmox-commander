<template>
  <v-card>
    <v-toolbar flat density="compact">
      <v-icon class="ml-2 mr-2">mdi-server-network</v-icon>
      <v-toolbar-title class="text-body-1">VM-Konfigurationen</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn
        variant="outlined"
        size="small"
        @click="$emit('import')"
        class="mr-2"
      >
        <v-icon start>mdi-import</v-icon>
        Importieren
      </v-btn>
      <v-btn
        color="primary"
        size="small"
        @click="$emit('create')"
      >
        <v-icon start>mdi-plus</v-icon>
        Neue VM
      </v-btn>
      <v-btn
        icon
        size="small"
        variant="text"
        @click="loadVMs"
        :loading="loading"
        class="ml-2"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
    </v-toolbar>

    <v-data-table
      v-model="selectedVMs"
      :headers="headers"
      :items="vms"
      :loading="loading"
      density="compact"
      :items-per-page="15"
      show-select
      item-value="name"
    >
      <template v-slot:item.name="{ item }">
        <v-chip color="primary" variant="outlined" size="small">
          {{ item.name }}
        </v-chip>
      </template>

      <template v-slot:item.status="{ item }">
        <v-chip :color="getStatusColor(item.status)" size="small">
          <v-icon start size="small">{{ getStatusIcon(item.status) }}</v-icon>
          {{ getStatusLabel(item.status) }}
        </v-chip>
      </template>

      <template v-slot:item.resources="{ item }">
        <span class="text-caption">
          {{ item.cores }} CPU, {{ item.memory_gb }} GB, {{ item.disk_size_gb }} GB
        </span>
      </template>

      <template v-slot:item.ansible_group="{ item }">
        <v-chip
          v-if="item.ansible_group"
          size="x-small"
          color="primary"
          variant="outlined"
        >
          <v-icon start size="x-small">mdi-ansible</v-icon>
          {{ item.ansible_group }}
        </v-chip>
        <span v-else class="text-grey-darken-1 text-caption">-</span>
      </template>

      <template v-slot:item.actions="{ item }">
        <div class="d-flex align-center">
          <!-- Power Controls (nur für deployed VMs) -->
          <template v-if="['deployed', 'running', 'stopped', 'paused'].includes(item.status)">
            <v-btn
              icon
              size="x-small"
              variant="text"
              color="success"
              @click="powerAction(item, 'start')"
              :loading="actionLoading === `power-start-${item.name}`"
              :disabled="item.status === 'running'"
              title="Start"
            >
              <v-icon size="18">mdi-play-circle</v-icon>
            </v-btn>
            <v-btn
              icon
              size="x-small"
              variant="text"
              color="warning"
              @click="powerAction(item, 'shutdown')"
              :loading="actionLoading === `power-shutdown-${item.name}`"
              :disabled="item.status !== 'running'"
              title="Shutdown"
            >
              <v-icon size="18">mdi-stop-circle</v-icon>
            </v-btn>
            <v-btn
              icon
              size="x-small"
              variant="text"
              color="info"
              @click="powerAction(item, 'reboot')"
              :loading="actionLoading === `power-reboot-${item.name}`"
              :disabled="item.status !== 'running'"
              title="Reboot"
            >
              <v-icon size="18">mdi-restart</v-icon>
            </v-btn>
            <!-- Clone - nur für deployed VMs -->
            <v-btn
              icon
              size="x-small"
              variant="text"
              color="primary"
              @click="openCloneDialog(item)"
              title="Klonen"
            >
              <v-icon size="18">mdi-content-copy</v-icon>
            </v-btn>
            <!-- Snapshots - nur für deployed VMs -->
            <v-btn
              icon
              size="x-small"
              variant="text"
              color="secondary"
              @click="openSnapshotManager(item)"
              title="Snapshots"
            >
              <v-icon size="18">mdi-camera</v-icon>
            </v-btn>
            <!-- Migrieren - nur für deployed VMs -->
            <v-btn
              icon
              size="x-small"
              variant="text"
              color="info"
              @click="openMigrateDialog(item)"
              title="Auf anderen Node migrieren"
            >
              <v-icon size="18">mdi-server-network</v-icon>
            </v-btn>
            <v-divider vertical class="mx-1"></v-divider>
          </template>
          <!-- Frontend-URL öffnen (nur wenn URL vorhanden) -->
          <v-btn
            v-if="item.frontend_url"
            icon
            size="x-small"
            variant="text"
            color="primary"
            @click.stop="openFrontendUrl(item.frontend_url)"
            title="Frontend öffnen"
          >
            <v-icon size="18">mdi-open-in-new</v-icon>
          </v-btn>
          <!-- Frontend-URL bearbeiten -->
          <v-btn
            icon
            size="x-small"
            variant="text"
            :color="item.frontend_url ? 'primary' : 'grey'"
            @click.stop="openFrontendUrlDialog(item)"
            :title="item.frontend_url ? 'Frontend-URL bearbeiten' : 'Frontend-URL hinzufügen'"
          >
            <v-icon size="18">mdi-link-variant</v-icon>
          </v-btn>
          <!-- Plan - immer verfügbar -->
          <v-btn
            icon
            size="x-small"
            variant="text"
            color="info"
            @click="planVM(item)"
            :loading="actionLoading === `plan-${item.name}`"
            title="Plan"
          >
            <v-icon size="18">mdi-file-search</v-icon>
          </v-btn>
          <!-- Apply - nur für PLANNED Status -->
          <v-btn
            icon
            size="x-small"
            variant="text"
            color="success"
            @click="applyVM(item)"
            :loading="actionLoading === `apply-${item.name}`"
            :disabled="item.status === 'deployed' || item.status === 'deploying'"
            title="Apply (Deploy)"
          >
            <v-icon size="18">mdi-rocket-launch</v-icon>
          </v-btn>
          <!-- Destroy - nur für DEPLOYED Status -->
          <v-btn
            icon
            size="x-small"
            variant="text"
            color="error"
            @click="confirmDestroy(item)"
            :disabled="item.status === 'planned' || item.status === 'destroying'"
            title="Destroy"
          >
            <v-icon size="18">mdi-delete-alert</v-icon>
          </v-btn>
          <!-- IP freigeben - nur für PLANNED Status -->
          <v-btn
            icon
            size="x-small"
            variant="text"
            color="warning"
            @click="confirmReleaseIP(item)"
            :disabled="item.status !== 'planned'"
            title="IP freigeben"
          >
            <v-icon size="18">mdi-ip-network-outline</v-icon>
          </v-btn>
          <!-- Config löschen -->
          <v-btn
            icon
            size="x-small"
            variant="text"
            @click="confirmDelete(item)"
            :disabled="item.status === 'deploying' || item.status === 'destroying'"
            title="Config löschen"
          >
            <v-icon size="18">mdi-file-remove</v-icon>
          </v-btn>
          <!-- Vollständig löschen -->
          <v-btn
            icon
            size="x-small"
            variant="text"
            color="error"
            @click="confirmDeleteComplete(item)"
            :disabled="item.status === 'deploying' || item.status === 'destroying'"
            title="Vollständig löschen (alle Systeme)"
          >
            <v-icon size="18">mdi-delete-forever</v-icon>
          </v-btn>
        </div>
      </template>

      <template v-slot:no-data>
        <div class="text-center py-8">
          <v-icon size="64" color="grey-lighten-1">mdi-server-off</v-icon>
          <div class="text-grey mt-2">Keine VM-Konfigurationen vorhanden</div>
          <v-btn
            color="primary"
            variant="tonal"
            class="mt-4"
            @click="$emit('create')"
          >
            <v-icon start>mdi-plus</v-icon>
            Erste VM erstellen
          </v-btn>
        </div>
      </template>
    </v-data-table>

    <!-- Destroy Bestätigung -->
    <v-dialog v-model="destroyDialog" max-width="400">
      <v-card>
        <v-card-title class="text-error">
          <v-icon start color="error">mdi-alert</v-icon>
          VM zerstören
        </v-card-title>
        <v-card-text>
          <v-alert type="error" variant="tonal" class="mb-4">
            Diese Aktion löscht die VM unwiderruflich aus Proxmox!
          </v-alert>
          <p>
            Möchtest du die VM <strong>{{ selectedVM?.name }}</strong> wirklich zerstören?
          </p>
          <v-text-field
            v-model="destroyConfirm"
            label="Tippe 'DESTROY' zur Bestätigung"
            variant="outlined"
            density="compact"
            class="mt-4"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="destroyDialog = false">Abbrechen</v-btn>
          <v-btn
            color="error"
            :disabled="destroyConfirm !== 'DESTROY'"
            :loading="actionLoading === `destroy-${selectedVM?.name}`"
            @click="destroyVM"
          >
            Destroy
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Config Bestätigung -->
    <v-dialog v-model="deleteDialog" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon start>mdi-file-remove</v-icon>
          Konfiguration löschen
        </v-card-title>
        <v-card-text>
          <!-- Proxmox Status laden -->
          <div v-if="proxmoxCheckLoading" class="text-center py-4">
            <v-progress-circular indeterminate size="24" class="mr-2"></v-progress-circular>
            Prüfe VM-Status in Proxmox...
          </div>

          <template v-else>
            <!-- Proxmox Status Anzeige -->
            <v-alert
              v-if="proxmoxStatus.configured && proxmoxStatus.exists === true"
              type="error"
              variant="tonal"
              class="mb-4"
            >
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-server</v-icon>
                <div>
                  <strong>VM existiert in Proxmox!</strong>
                  <div class="text-caption">
                    Node: {{ proxmoxStatus.node }} |
                    Status: {{ proxmoxStatus.status }} |
                    VMID: {{ proxmoxStatus.vmid }}
                  </div>
                </div>
              </div>
            </v-alert>

            <v-alert
              v-else-if="proxmoxStatus.configured && proxmoxStatus.exists === false"
              type="success"
              variant="tonal"
              class="mb-4"
            >
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-check-circle</v-icon>
                <div>
                  <strong>VM existiert nicht in Proxmox</strong>
                  <div class="text-caption">
                    Die VM wurde bereits gelöscht oder nie deployed.
                  </div>
                </div>
              </div>
            </v-alert>

            <v-alert
              v-else-if="!proxmoxStatus.configured"
              type="warning"
              variant="tonal"
              class="mb-4"
            >
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-alert</v-icon>
                <div>
                  <strong>Proxmox-Prüfung nicht möglich</strong>
                  <div class="text-caption">
                    {{ proxmoxStatus.error || 'Proxmox API nicht konfiguriert' }}
                  </div>
                </div>
              </div>
            </v-alert>

            <v-alert
              v-else-if="proxmoxStatus.error"
              type="warning"
              variant="tonal"
              class="mb-4"
            >
              <div class="d-flex align-center">
                <v-icon class="mr-2">mdi-alert</v-icon>
                <div>
                  <strong>Proxmox-Prüfung fehlgeschlagen</strong>
                  <div class="text-caption">{{ proxmoxStatus.error }}</div>
                </div>
              </div>
            </v-alert>

            <!-- Terraform State Info -->
            <v-alert
              v-if="selectedVM?.status === 'deployed' && proxmoxStatus.exists === false"
              type="info"
              variant="tonal"
              density="compact"
              class="mb-4"
            >
              <strong>Hinweis:</strong> Terraform State zeigt "deployed", aber VM existiert nicht mehr.
              Nur Config-Löschung erforderlich.
            </v-alert>

            <p class="mb-4">
              Möchtest du die Konfiguration für <strong>{{ selectedVM?.name }}</strong> löschen?
            </p>

            <!-- Optionen wenn VM in Proxmox existiert -->
            <v-radio-group
              v-if="vmExistsInProxmox"
              v-model="deleteMode"
              class="mt-2"
            >
              <v-radio value="config_only">
                <template v-slot:label>
                  <div>
                    <strong>Nur Config löschen</strong>
                    <div class="text-caption text-grey">
                      Die VM bleibt in Proxmox erhalten
                    </div>
                  </div>
                </template>
              </v-radio>
              <v-radio value="destroy_and_delete" color="error">
                <template v-slot:label>
                  <div>
                    <strong class="text-error">VM zerstören & Config löschen</strong>
                    <div class="text-caption text-grey">
                      Führt terraform destroy aus und löscht dann die Config
                    </div>
                  </div>
                </template>
              </v-radio>
            </v-radio-group>

            <!-- Bestätigungseingabe wenn VM zerstört werden soll -->
            <v-text-field
              v-if="deleteMode === 'destroy_and_delete' && vmExistsInProxmox"
              v-model="deleteDestroyConfirm"
              label="Tippe 'DESTROY' zur Bestätigung"
              variant="outlined"
              density="compact"
              class="mt-4"
              color="error"
            ></v-text-field>
          </template>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="deleteDialog = false">Abbrechen</v-btn>
          <v-btn
            v-if="!vmExistsInProxmox || deleteMode === 'config_only'"
            color="warning"
            :loading="actionLoading === `delete-${selectedVM?.name}`"
            :disabled="proxmoxCheckLoading"
            @click="deleteVMConfig"
          >
            <v-icon start>mdi-file-remove</v-icon>
            Config löschen
          </v-btn>
          <v-btn
            v-if="deleteMode === 'destroy_and_delete' && vmExistsInProxmox"
            color="error"
            :disabled="deleteDestroyConfirm !== 'DESTROY'"
            :loading="actionLoading === `destroy-delete-${selectedVM?.name}`"
            @click="destroyAndDeleteVM"
          >
            <v-icon start>mdi-delete-alert</v-icon>
            Destroy & Löschen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- IP Freigabe Bestätigung -->
    <v-dialog v-model="releaseIPDialog" max-width="400">
      <v-card>
        <v-card-title class="text-warning">
          <v-icon start color="warning">mdi-ip-network-outline</v-icon>
          IP freigeben
        </v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            Die IP-Adresse wird in NetBox als frei markiert.
          </v-alert>
          <p>
            Möchtest du die IP <strong>{{ selectedVM?.ip_address }}</strong>
            für VM <strong>{{ selectedVM?.name }}</strong> freigeben?
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="releaseIPDialog = false">Abbrechen</v-btn>
          <v-btn
            color="warning"
            :loading="actionLoading === `release-${selectedVM?.name}`"
            @click="releaseIP"
          >
            Freigeben
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Vollständige Löschung Dialog -->
    <v-dialog v-model="deleteCompleteDialog" max-width="600" persistent>
      <v-card>
        <v-card-title class="text-error">
          <v-icon start color="error">mdi-delete-forever</v-icon>
          VM vollständig löschen
        </v-card-title>
        <v-card-text>
          <!-- Bestätigungsphase -->
          <template v-if="!deleteCompleteResult">
            <v-alert type="error" variant="tonal" class="mb-4">
              <strong>ACHTUNG:</strong> Diese Aktion löscht die VM aus allen Systemen!
            </v-alert>

            <v-list density="compact" class="mb-4">
              <v-list-subheader>Folgende Systeme werden bereinigt:</v-list-subheader>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="error">mdi-server</v-icon>
                </template>
                <v-list-item-title>Proxmox</v-list-item-title>
                <v-list-item-subtitle>VM wird gestoppt und gelöscht</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="error">mdi-database</v-icon>
                </template>
                <v-list-item-title>NetBox</v-list-item-title>
                <v-list-item-subtitle>VM-Eintrag und IP-Adresse werden freigegeben</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="error">mdi-terraform</v-icon>
                </template>
                <v-list-item-title>Terraform</v-list-item-title>
                <v-list-item-subtitle>State und Konfigurationsdatei werden entfernt</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="error">mdi-ansible</v-icon>
                </template>
                <v-list-item-title>Ansible</v-list-item-title>
                <v-list-item-subtitle>Host wird aus dem Inventory entfernt</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <p class="mb-4">
              VM: <strong>{{ selectedVM?.name }}</strong> ({{ selectedVM?.ip_address }})
            </p>

            <v-text-field
              v-model="deleteCompleteConfirm"
              label="Tippe 'DELETE' zur Bestätigung"
              variant="outlined"
              density="compact"
              color="error"
            ></v-text-field>
          </template>

          <!-- Ergebnisphase -->
          <template v-else>
            <v-alert
              :type="deleteCompleteResult.success ? 'success' : 'warning'"
              variant="tonal"
              class="mb-4"
            >
              {{ deleteCompleteResult.message }}
            </v-alert>

            <v-list density="compact">
              <v-list-subheader>Ergebnis pro System:</v-list-subheader>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="getResultColor(deleteCompleteResult.proxmox)">
                    {{ getResultIcon(deleteCompleteResult.proxmox) }}
                  </v-icon>
                </template>
                <v-list-item-title>Proxmox</v-list-item-title>
                <v-list-item-subtitle>
                  {{ getResultText(deleteCompleteResult.proxmox) }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="getResultColor(deleteCompleteResult.netbox_vm)">
                    {{ getResultIcon(deleteCompleteResult.netbox_vm) }}
                  </v-icon>
                </template>
                <v-list-item-title>NetBox VM</v-list-item-title>
                <v-list-item-subtitle>
                  {{ getResultText(deleteCompleteResult.netbox_vm) }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="getResultColor(deleteCompleteResult.netbox_ip)">
                    {{ getResultIcon(deleteCompleteResult.netbox_ip) }}
                  </v-icon>
                </template>
                <v-list-item-title>NetBox IP</v-list-item-title>
                <v-list-item-subtitle>
                  {{ getResultText(deleteCompleteResult.netbox_ip) }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="getResultColor(deleteCompleteResult.terraform_state)">
                    {{ getResultIcon(deleteCompleteResult.terraform_state) }}
                  </v-icon>
                </template>
                <v-list-item-title>Terraform State</v-list-item-title>
                <v-list-item-subtitle>
                  {{ getResultText(deleteCompleteResult.terraform_state) }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="getResultColor(deleteCompleteResult.terraform_file)">
                    {{ getResultIcon(deleteCompleteResult.terraform_file) }}
                  </v-icon>
                </template>
                <v-list-item-title>Terraform-Datei</v-list-item-title>
                <v-list-item-subtitle>
                  {{ getResultText(deleteCompleteResult.terraform_file) }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="getResultColor(deleteCompleteResult.ansible_inventory)">
                    {{ getResultIcon(deleteCompleteResult.ansible_inventory) }}
                  </v-icon>
                </template>
                <v-list-item-title>Ansible Inventory</v-list-item-title>
                <v-list-item-subtitle>
                  {{ getResultText(deleteCompleteResult.ansible_inventory) }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </template>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <template v-if="!deleteCompleteResult">
            <v-btn variant="text" @click="closeDeleteCompleteDialog">Abbrechen</v-btn>
            <v-btn
              color="error"
              :disabled="deleteCompleteConfirm !== 'DELETE'"
              :loading="actionLoading === `delete-complete-${selectedVM?.name}`"
              @click="executeDeleteComplete"
            >
              <v-icon start>mdi-delete-forever</v-icon>
              Vollständig löschen
            </v-btn>
          </template>
          <template v-else>
            <v-btn color="primary" @click="closeDeleteCompleteDialog">
              Schließen
            </v-btn>
          </template>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Batch Actions Toolbar -->
    <v-toolbar
      v-if="selectedVMs.length > 0"
      density="compact"
      class="batch-toolbar"
    >
      <v-toolbar-title class="text-body-2">
        {{ selectedVMs.length }} VM(s) ausgewählt
      </v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn
        color="info"
        size="small"
        variant="tonal"
        @click="batchPlan"
        :loading="batchLoading"
        class="mx-1"
      >
        <v-icon start>mdi-file-search</v-icon>
        Alle planen
      </v-btn>
      <v-btn
        color="success"
        size="small"
        variant="tonal"
        @click="batchApply"
        :loading="batchLoading"
        class="mx-1"
      >
        <v-icon start>mdi-play</v-icon>
        Alle deployen
      </v-btn>
      <v-btn
        color="error"
        size="small"
        variant="tonal"
        @click="confirmBatchDestroy"
        :loading="batchLoading"
        class="mx-1"
      >
        <v-icon start>mdi-delete</v-icon>
        Alle zerstören
      </v-btn>
      <v-btn
        icon
        size="small"
        variant="text"
        @click="selectedVMs = []"
        class="ml-2"
      >
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-toolbar>

    <!-- Batch Destroy Bestätigung -->
    <v-dialog v-model="batchDestroyDialog" max-width="500">
      <v-card>
        <v-card-title class="text-error">
          <v-icon start color="error">mdi-alert</v-icon>
          {{ selectedVMs.length }} VMs zerstören
        </v-card-title>
        <v-card-text>
          <v-alert type="error" variant="tonal" class="mb-4">
            Diese Aktion löscht alle ausgewählten VMs unwiderruflich aus Proxmox!
          </v-alert>
          <p class="mb-2">Folgende VMs werden zerstört:</p>
          <v-chip
            v-for="name in selectedVMs"
            :key="name"
            size="small"
            class="ma-1"
            color="error"
            variant="outlined"
          >
            {{ name }}
          </v-chip>
          <v-text-field
            v-model="batchDestroyConfirm"
            label="Tippe 'DESTROY ALL' zur Bestätigung"
            variant="outlined"
            density="compact"
            class="mt-4"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="batchDestroyDialog = false">Abbrechen</v-btn>
          <v-btn
            color="error"
            :disabled="batchDestroyConfirm !== 'DESTROY ALL'"
            :loading="batchLoading"
            @click="batchDestroy"
          >
            Alle zerstören
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Clone Dialog -->
    <VMCloneDialog
      ref="cloneDialogRef"
      @cloned="onVMCloned"
    />

    <!-- Snapshot Manager -->
    <VMSnapshotManager
      ref="snapshotManagerRef"
      @close="loadVMs"
    />

    <!-- Migrate Dialog -->
    <VMMigrateDialog
      ref="migrateDialogRef"
      @migrated="onVMMigrated"
    />

    <!-- Frontend-URL Dialog -->
    <v-dialog v-model="frontendUrlDialog" max-width="500">
      <v-card>
        <v-toolbar color="primary" density="compact">
          <v-icon class="ml-2 mr-2">mdi-link-variant</v-icon>
          <v-toolbar-title>Frontend-URL</v-toolbar-title>
          <v-spacer></v-spacer>
          <v-btn icon size="small" @click="frontendUrlDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>
        <v-card-text class="pt-4">
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            <strong>{{ frontendUrlVm?.name }}</strong>
            <span v-if="frontendUrlVm?.ip_address" class="text-caption ml-2">
              ({{ frontendUrlVm.ip_address }})
            </span>
          </v-alert>
          <v-text-field
            v-model="frontendUrlInput"
            label="URL"
            placeholder="https://app.example.com"
            hint="URL zur Web-Oberfläche (leer lassen zum Entfernen)"
            persistent-hint
            clearable
            :loading="frontendUrlSaving"
            @keyup.enter="saveFrontendUrl"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="frontendUrlDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            :loading="frontendUrlSaving"
            @click="saveFrontendUrl"
          >
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import VMCloneDialog from '@/components/VMCloneDialog.vue'
import VMSnapshotManager from '@/components/VMSnapshotManager.vue'
import VMMigrateDialog from '@/components/VMMigrateDialog.vue'
import { getStatusColor, getStatusIcon } from '@/utils/formatting'

const emit = defineEmits(['create'])
const router = useRouter()
const showSnackbar = inject('showSnackbar')

const loading = ref(false)
const actionLoading = ref(null)
const vms = ref([])

const destroyDialog = ref(false)
const deleteDialog = ref(false)
const releaseIPDialog = ref(false)
const destroyConfirm = ref('')
const selectedVM = ref(null)
const deleteMode = ref('config_only')
const deleteDestroyConfirm = ref('')
const proxmoxCheckLoading = ref(false)
const proxmoxStatus = ref({
  exists: null,
  configured: false,
  node: null,
  status: null,
  vmid: null,
  error: null,
})

// Batch operations
const selectedVMs = ref([])
const batchLoading = ref(false)
const batchDestroyDialog = ref(false)
const batchDestroyConfirm = ref('')

// Clone und Snapshot Dialoge
const cloneDialogRef = ref(null)
const snapshotManagerRef = ref(null)
const migrateDialogRef = ref(null)

// Vollständige Löschung
const deleteCompleteDialog = ref(false)
const deleteCompleteConfirm = ref('')
const deleteCompleteResult = ref(null)

// Frontend-URL
const frontendUrlDialog = ref(false)
const frontendUrlInput = ref('')
const frontendUrlVm = ref(null)
const frontendUrlSaving = ref(false)

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'VMID', key: 'vmid', width: '80px' },
  { title: 'IP', key: 'ip_address', width: '140px' },
  { title: 'Node', key: 'target_node', width: '100px' },
  { title: 'Ressourcen', key: 'resources', width: '180px' },
  { title: 'Ansible', key: 'ansible_group', width: '120px' },
  { title: 'Status', key: 'status', width: '120px' },
  { title: '', key: 'actions', sortable: false, width: '340px' },
]

// Computed: VM existiert in Proxmox
const vmExistsInProxmox = computed(() => {
  // Wenn Proxmox-Check erfolgreich und VM existiert
  if (proxmoxStatus.value.configured && proxmoxStatus.value.exists === true) {
    return true
  }
  // Wenn Proxmox nicht konfiguriert, auf Terraform State zurückfallen
  if (!proxmoxStatus.value.configured && selectedVM.value?.status === 'deployed') {
    return true
  }
  return false
})

async function loadVMs() {
  loading.value = true
  try {
    // Cache-Buster um immer frische Daten zu bekommen
    const response = await api.get(`/api/terraform/vms?_t=${Date.now()}`)
    vms.value = response.data
  } catch (e) {
    console.error('VMs laden fehlgeschlagen:', e)
    showSnackbar?.('Laden fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    loading.value = false
  }
}

// Polling bis Status-Änderung (für Power-Aktionen)
async function waitForStatusChange(vmName, expectedStatuses, maxAttempts = 15) {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(resolve => setTimeout(resolve, 2000)) // 2s Intervall
    await loadVMs()
    const vm = vms.value.find(v => v.name === vmName)
    if (vm && expectedStatuses.includes(vm.status)) {
      return true
    }
  }
  return false
}

async function planVM(vm) {
  actionLoading.value = `plan-${vm.name}`
  try {
    const response = await api.post(`/api/terraform/vms/${vm.name}/plan`)
    showSnackbar?.(`Plan für ${vm.name} gestartet`, 'success')
    router.push(`/executions/${response.data.execution_id}`)
  } catch (e) {
    console.error('Plan fehlgeschlagen:', e)
    showSnackbar?.('Plan fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    actionLoading.value = null
  }
}

async function applyVM(vm) {
  actionLoading.value = `apply-${vm.name}`
  try {
    const response = await api.post(`/api/terraform/vms/${vm.name}/apply`)
    showSnackbar?.(`Deploy für ${vm.name} gestartet`, 'success')
    router.push(`/executions/${response.data.execution_id}`)
  } catch (e) {
    console.error('Apply fehlgeschlagen:', e)
    showSnackbar?.('Deploy fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    actionLoading.value = null
  }
}

// Power Actions (Start, Stop, Shutdown, Reboot)
async function powerAction(vm, action) {
  const actionLabels = {
    start: 'Start',
    stop: 'Stop',
    shutdown: 'Shutdown',
    reboot: 'Reboot',
    reset: 'Reset',
  }
  // Erwarteter Status nach der Aktion
  const expectedStatuses = {
    start: ['running'],
    stop: ['stopped'],
    shutdown: ['stopped'],
    reboot: ['running'],
    reset: ['running'],
  }
  actionLoading.value = `power-${action}-${vm.name}`
  try {
    await api.post(`/api/terraform/vms/${vm.name}/power/${action}`)
    showSnackbar?.(`${actionLabels[action]} für ${vm.name} ausgeführt`, 'success')
    // Polling bis Status sich ändert (max 30 Sekunden)
    waitForStatusChange(vm.name, expectedStatuses[action] || ['running', 'stopped'])
  } catch (e) {
    console.error(`Power ${action} fehlgeschlagen:`, e)
    showSnackbar?.(`${actionLabels[action]} fehlgeschlagen: ` + (e.response?.data?.detail || e.message), 'error')
  } finally {
    actionLoading.value = null
  }
}

// Clone Dialog
function openCloneDialog(vm) {
  cloneDialogRef.value?.open(vm)
}

function onVMCloned(result) {
  showSnackbar?.(`VM '${result.target_name}' wird geklont (IP: ${result.target_ip})`, 'success')
  loadVMs()
}

// Snapshot Manager
function openSnapshotManager(vm) {
  snapshotManagerRef.value?.open(vm)
}

// Migrate Dialog
function openMigrateDialog(vm) {
  migrateDialogRef.value?.open(vm)
}

function onVMMigrated(result) {
  showSnackbar?.(`VM '${result.vm_name}' nach ${result.target_node} migriert`, 'success')
  loadVMs()
}

// Frontend-URL Funktionen
function openFrontendUrl(url) {
  window.open(url, '_blank')
}

function openFrontendUrlDialog(vm) {
  frontendUrlVm.value = vm
  frontendUrlInput.value = vm.frontend_url || ''
  frontendUrlDialog.value = true
}

async function saveFrontendUrl() {
  if (!frontendUrlVm.value) return
  frontendUrlSaving.value = true
  try {
    await api.patch(`/api/terraform/vms/${frontendUrlVm.value.name}/frontend-url`, {
      frontend_url: frontendUrlInput.value || null
    })
    showSnackbar?.(
      frontendUrlInput.value
        ? 'Frontend-URL gespeichert'
        : 'Frontend-URL entfernt',
      'success'
    )
    frontendUrlDialog.value = false
    loadVMs()
  } catch (e) {
    console.error('Frontend-URL speichern fehlgeschlagen:', e)
    showSnackbar?.('Fehler: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    frontendUrlSaving.value = false
  }
}

function confirmDestroy(vm) {
  selectedVM.value = vm
  destroyConfirm.value = ''
  destroyDialog.value = true
}

async function destroyVM() {
  if (!selectedVM.value) return
  actionLoading.value = `destroy-${selectedVM.value.name}`
  try {
    const response = await api.post(`/api/terraform/vms/${selectedVM.value.name}/destroy`)
    showSnackbar?.(`Destroy für ${selectedVM.value.name} gestartet`, 'success')
    destroyDialog.value = false
    router.push(`/executions/${response.data.execution_id}`)
  } catch (e) {
    console.error('Destroy fehlgeschlagen:', e)
    showSnackbar?.('Destroy fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    actionLoading.value = null
  }
}

async function confirmDelete(vm) {
  selectedVM.value = vm
  deleteMode.value = 'config_only'
  deleteDestroyConfirm.value = ''
  proxmoxStatus.value = {
    exists: null,
    configured: false,
    node: null,
    status: null,
    vmid: null,
    error: null,
  }
  deleteDialog.value = true

  // Proxmox-Status prüfen
  if (vm.vmid) {
    proxmoxCheckLoading.value = true
    try {
      const response = await api.get(`/api/terraform/proxmox/vm/${vm.vmid}`, {
        params: { node: vm.target_node }
      })
      proxmoxStatus.value = response.data
    } catch (e) {
      console.error('Proxmox-Check fehlgeschlagen:', e)
      proxmoxStatus.value = {
        exists: null,
        configured: false,
        error: e.response?.data?.detail || 'Verbindung fehlgeschlagen',
      }
    } finally {
      proxmoxCheckLoading.value = false
    }
  }
}

async function deleteVMConfig() {
  if (!selectedVM.value) return
  actionLoading.value = `delete-${selectedVM.value.name}`
  try {
    await api.delete(`/api/terraform/vms/${selectedVM.value.name}`)
    showSnackbar?.(`Konfiguration für ${selectedVM.value.name} gelöscht`, 'success')
    deleteDialog.value = false
    loadVMs()
  } catch (e) {
    console.error('Löschen fehlgeschlagen:', e)
    showSnackbar?.('Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    actionLoading.value = null
  }
}

async function destroyAndDeleteVM() {
  if (!selectedVM.value) return
  const vmName = selectedVM.value.name
  actionLoading.value = `destroy-delete-${vmName}`
  try {
    // Schritt 1: Terraform Destroy ausführen
    showSnackbar?.(`Destroy für ${vmName} wird gestartet...`, 'info')
    const destroyResponse = await api.post(`/api/terraform/vms/${vmName}/destroy`)

    // Polling für Destroy-Abschluss
    const executionId = destroyResponse.data.execution_id
    let destroyComplete = false
    let destroySuccess = false

    while (!destroyComplete) {
      await new Promise(resolve => setTimeout(resolve, 2000)) // 2 Sekunden warten
      try {
        const statusResponse = await api.get(`/api/executions/${executionId}`)
        const status = statusResponse.data.status
        if (status === 'success') {
          destroyComplete = true
          destroySuccess = true
        } else if (status === 'failed' || status === 'error') {
          destroyComplete = true
          destroySuccess = false
        }
        // Bei 'running' oder 'pending' weiterwarten
      } catch (e) {
        // Polling-Fehler ignorieren und weitermachen
        console.warn('Status-Abfrage fehlgeschlagen:', e)
      }
    }

    if (!destroySuccess) {
      showSnackbar?.(`Destroy für ${vmName} fehlgeschlagen - Config wird nicht gelöscht`, 'error')
      deleteDialog.value = false
      return
    }

    // Schritt 2: Config löschen nach erfolgreichem Destroy
    await api.delete(`/api/terraform/vms/${vmName}`)
    showSnackbar?.(`VM ${vmName} zerstört und Config gelöscht`, 'success')
    deleteDialog.value = false
    loadVMs()
  } catch (e) {
    console.error('Destroy & Löschen fehlgeschlagen:', e)
    showSnackbar?.('Destroy & Löschen fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    actionLoading.value = null
  }
}

// Vollständige Löschung
function confirmDeleteComplete(vm) {
  selectedVM.value = vm
  deleteCompleteConfirm.value = ''
  deleteCompleteResult.value = null
  deleteCompleteDialog.value = true
}

function closeDeleteCompleteDialog() {
  deleteCompleteDialog.value = false
  if (deleteCompleteResult.value?.success) {
    loadVMs()
  }
}

async function executeDeleteComplete() {
  if (!selectedVM.value) return
  const vmName = selectedVM.value.name
  actionLoading.value = `delete-complete-${vmName}`

  try {
    const response = await api.delete(`/api/terraform/vms/${vmName}/complete`)
    deleteCompleteResult.value = response.data
    showSnackbar?.(
      response.data.success
        ? `VM ${vmName} vollständig gelöscht`
        : `VM ${vmName} teilweise gelöscht - siehe Details`,
      response.data.success ? 'success' : 'warning'
    )
  } catch (e) {
    console.error('Vollständige Löschung fehlgeschlagen:', e)
    showSnackbar?.('Löschung fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
    deleteCompleteDialog.value = false
  } finally {
    actionLoading.value = null
  }
}

// Hilfsfunktionen für Ergebnisanzeige
function getResultColor(result) {
  if (!result) return 'grey'
  if (result.success) return 'success'
  if (result.skipped) return 'grey'
  if (result.error) return 'error'
  return 'grey'
}

function getResultIcon(result) {
  if (!result) return 'mdi-help-circle'
  if (result.success && !result.skipped) return 'mdi-check-circle'
  if (result.skipped) return 'mdi-minus-circle'
  if (result.error) return 'mdi-alert-circle'
  return 'mdi-help-circle'
}

function getResultText(result) {
  if (!result) return 'Unbekannt'
  if (result.error) return `Fehler: ${result.error}`
  if (result.skipped) return 'Übersprungen (nicht vorhanden)'
  if (result.success) return 'Erfolgreich gelöscht'
  return 'Unbekannt'
}

// IP Freigabe
function confirmReleaseIP(vm) {
  selectedVM.value = vm
  releaseIPDialog.value = true
}

async function releaseIP() {
  if (!selectedVM.value) return
  actionLoading.value = `release-${selectedVM.value.name}`
  try {
    await api.post(`/api/terraform/vms/${selectedVM.value.name}/release-ip`)
    showSnackbar?.(`IP ${selectedVM.value.ip_address} freigegeben`, 'success')
    releaseIPDialog.value = false
    loadVMs()
  } catch (e) {
    console.error('IP-Freigabe fehlgeschlagen:', e)
    showSnackbar?.('IP-Freigabe fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    actionLoading.value = null
  }
}

// Batch Operations
async function batchPlan() {
  batchLoading.value = true
  try {
    const response = await api.post('/api/terraform/vms/batch/plan', {
      vm_names: selectedVMs.value
    })
    const { successful, failed } = response.data
    if (successful.length > 0) {
      showSnackbar?.(`Plan für ${successful.length} VM(s) gestartet`, 'success')
    }
    if (failed.length > 0) {
      showSnackbar?.(`${failed.length} VM(s) fehlgeschlagen`, 'error')
    }
    selectedVMs.value = []
    loadVMs()
  } catch (e) {
    console.error('Batch Plan fehlgeschlagen:', e)
    showSnackbar?.('Batch Plan fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    batchLoading.value = false
  }
}

async function batchApply() {
  batchLoading.value = true
  try {
    const response = await api.post('/api/terraform/vms/batch/apply', {
      vm_names: selectedVMs.value
    })
    const { successful, failed } = response.data
    if (successful.length > 0) {
      showSnackbar?.(`Deploy für ${successful.length} VM(s) gestartet`, 'success')
    }
    if (failed.length > 0) {
      const failedNames = failed.map(f => `${f.name}: ${f.error}`).join(', ')
      showSnackbar?.(`${failed.length} VM(s) fehlgeschlagen: ${failedNames}`, 'error')
    }
    selectedVMs.value = []
    loadVMs()
  } catch (e) {
    console.error('Batch Apply fehlgeschlagen:', e)
    showSnackbar?.('Batch Apply fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    batchLoading.value = false
  }
}

function confirmBatchDestroy() {
  batchDestroyConfirm.value = ''
  batchDestroyDialog.value = true
}

async function batchDestroy() {
  batchLoading.value = true
  try {
    const response = await api.post('/api/terraform/vms/batch/destroy', {
      vm_names: selectedVMs.value
    })
    const { successful, failed } = response.data
    if (successful.length > 0) {
      showSnackbar?.(`Destroy für ${successful.length} VM(s) gestartet`, 'success')
    }
    if (failed.length > 0) {
      showSnackbar?.(`${failed.length} VM(s) fehlgeschlagen`, 'error')
    }
    batchDestroyDialog.value = false
    selectedVMs.value = []
    loadVMs()
  } catch (e) {
    console.error('Batch Destroy fehlgeschlagen:', e)
    showSnackbar?.('Batch Destroy fehlgeschlagen: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    batchLoading.value = false
  }
}

function getStatusLabel(status) {
  const labels = {
    planned: 'Geplant',
    deploying: 'Deploying...',
    deployed: 'Deployed',
    failed: 'Fehler',
    destroying: 'Destroying...',
    // Proxmox Live-Status
    running: 'Running',
    stopped: 'Stopped',
    paused: 'Paused',
  }
  return labels[status] || status
}

// Expose reload für Parent
defineExpose({ loadVMs })

onMounted(loadVMs)
</script>
