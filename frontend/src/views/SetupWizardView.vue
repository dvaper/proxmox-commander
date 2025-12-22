<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" md="8" lg="6">
        <v-card class="elevation-12">
          <v-toolbar color="primary" dark flat>
            <v-icon class="mr-2">mdi-cog-outline</v-icon>
            <v-toolbar-title>Proxmox Commander - Setup</v-toolbar-title>
          </v-toolbar>

          <v-stepper v-model="step" :items="steps" flat>
            <!-- Schritt 1: Willkommen -->
            <template v-slot:item.1>
              <v-card flat>
                <v-card-text class="text-center py-8">
                  <v-icon size="80" color="primary" class="mb-4">
                    mdi-server-network
                  </v-icon>
                  <h2 class="text-h5 mb-4">Willkommen bei Proxmox Commander</h2>
                  <p class="text-body-1 text-grey-darken-1 mb-6">
                    Dieser Assistent hilft dir bei der Erstkonfiguration.
                    Du benötigst Zugriff auf deinen Proxmox VE Server mit einem API-Token.
                  </p>

                  <v-alert type="info" variant="tonal" class="text-left mb-4">
                    <div class="text-subtitle-2 mb-2">Voraussetzungen:</div>
                    <ul class="pl-4">
                      <li>Proxmox VE Server - unterstützte Formate:
                        <ul class="pl-2 text-body-2">
                          <li><code>192.168.1.100</code> - IP-Adresse (Port 8006 wird automatisch hinzugefügt)</li>
                          <li><code>proxmox.example.com</code> - Hostname (Port 8006 wird automatisch hinzugefügt)</li>
                          <li><code>https://proxmox.example.com</code> - Reverse Proxy (Standard HTTPS Port 443)</li>
                        </ul>
                      </li>
                      <li>API-Token mit entsprechenden Berechtigungen</li>
                      <li>Netzwerkzugriff auf den Proxmox-Server</li>
                    </ul>
                  </v-alert>

                  <v-alert type="warning" variant="tonal" class="text-left">
                    <div class="text-subtitle-2">Noch keinen API-Token?</div>
                    <p class="text-body-2 mb-0">
                      Kein Problem! Im nächsten Schritt findest du eine ausführliche Anleitung
                      zur Erstellung eines API-Tokens in Proxmox.
                    </p>
                  </v-alert>
                </v-card-text>
              </v-card>
            </template>

            <!-- Schritt 2: Proxmox Konfiguration -->
            <template v-slot:item.2>
              <v-card flat>
                <v-card-text>
                  <h3 class="text-h6 mb-4">
                    <v-icon class="mr-2">mdi-server</v-icon>
                    Proxmox Verbindung
                  </h3>

                  <!-- Hilfe-Bereich für Token-Erstellung -->
                  <v-expansion-panels class="mb-4">
                    <v-expansion-panel>
                      <v-expansion-panel-title>
                        <v-icon class="mr-2" size="small" color="info">mdi-help-circle</v-icon>
                        <span class="text-body-2">Anleitung: API-Token in Proxmox erstellen</span>
                      </v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <div class="text-body-2">
                          <p class="font-weight-bold mb-2">Schritt 1: API-Benutzer anlegen (optional)</p>
                          <p class="mb-3">
                            Falls noch kein API-Benutzer existiert:<br>
                            <code>Datacenter</code> &rarr; <code>Permissions</code> &rarr; <code>Users</code> &rarr; <code>Add</code><br>
                            <ul class="pl-4">
                              <li>User name: <code>terraform</code> (oder beliebig)</li>
                              <li>Realm: <code>Proxmox VE authentication server</code> (pve)</li>
                              <li>Ergebnis: <code>terraform@pve</code></li>
                            </ul>
                          </p>

                          <p class="font-weight-bold mb-2">Schritt 2: API-Token erstellen</p>
                          <p class="mb-3">
                            <code>Datacenter</code> &rarr; <code>Permissions</code> &rarr; <code>API Tokens</code> &rarr; <code>Add</code><br>
                            <ul class="pl-4">
                              <li>User: <code>terraform@pve</code></li>
                              <li>Token ID: <code>terraform-token</code> (oder beliebig)</li>
                              <li><strong class="text-error">Privilege Separation: DEAKTIVIEREN!</strong></li>
                            </ul>
                          </p>

                          <v-alert type="warning" variant="tonal" density="compact" class="mb-3">
                            <strong>Wichtig:</strong> Das Token Secret wird nur einmal angezeigt!
                            Kopiere es sofort und speichere es sicher.
                          </v-alert>

                          <p class="font-weight-bold mb-2">Schritt 3: Berechtigungen vergeben</p>
                          <p class="mb-3">
                            <code>Datacenter</code> &rarr; <code>Permissions</code> &rarr; <code>Add</code> &rarr; <code>User Permission</code><br>
                            <ul class="pl-4">
                              <li>Path: <code>/</code> (Root für alle Rechte)</li>
                              <li>User: <code>terraform@pve</code></li>
                              <li>Role: <code>Administrator</code> (oder eingeschränkte Rolle)</li>
                            </ul>
                          </p>

                          <p class="font-weight-bold mb-2">Ergebnis:</p>
                          <ul class="pl-4">
                            <li><strong>Token ID:</strong> <code>terraform@pve!terraform-token</code></li>
                            <li><strong>Token Secret:</strong> <code>xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx</code></li>
                          </ul>
                        </div>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>

                  <v-text-field
                    v-model="config.proxmox_host"
                    label="Proxmox Host"
                    placeholder="192.168.1.100 oder https://proxmox.example.com"
                    prepend-inner-icon="mdi-ip-network"
                    hint="Direkt: IP/Hostname (Port 8006 wird hinzugefügt) | Reverse Proxy: https://hostname"
                    persistent-hint
                    variant="outlined"
                    density="compact"
                    class="mb-4"
                    :error-messages="errors.proxmox_host"
                    @update:model-value="clearError('proxmox_host')"
                  ></v-text-field>

                  <v-text-field
                    v-model="config.proxmox_token_id"
                    label="API Token ID"
                    placeholder="terraform@pve!terraform-token"
                    prepend-inner-icon="mdi-identifier"
                    hint="Format: benutzer@realm!token-name (z.B. terraform@pve!terraform-token)"
                    persistent-hint
                    variant="outlined"
                    density="compact"
                    class="mb-4"
                    :error-messages="errors.proxmox_token_id"
                    @update:model-value="clearError('proxmox_token_id')"
                  ></v-text-field>

                  <v-text-field
                    v-model="config.proxmox_token_secret"
                    label="API Token Secret"
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    prepend-inner-icon="mdi-key"
                    :type="showSecret ? 'text' : 'password'"
                    :append-inner-icon="showSecret ? 'mdi-eye' : 'mdi-eye-off'"
                    @click:append-inner="showSecret = !showSecret"
                    hint="Das UUID-Secret wird beim Erstellen des Tokens einmalig angezeigt"
                    persistent-hint
                    variant="outlined"
                    density="compact"
                    class="mb-4"
                    :error-messages="errors.proxmox_token_secret"
                    @update:model-value="clearError('proxmox_token_secret')"
                  ></v-text-field>

                  <v-checkbox
                    v-model="config.proxmox_verify_ssl"
                    label="SSL-Zertifikat verifizieren"
                    hint="Deaktivieren bei selbstsignierten Zertifikaten oder Verbindungsproblemen"
                    persistent-hint
                    density="compact"
                    class="mb-4"
                  ></v-checkbox>

                  <!-- Verbindungstest - erscheint nur wenn alle Felder ausgefüllt -->
                  <template v-if="canTest">
                    <v-divider class="my-4"></v-divider>

                    <v-btn
                      color="secondary"
                      variant="outlined"
                      :loading="testing"
                      @click="testConnection"
                    >
                      <v-icon left class="mr-2">mdi-connection</v-icon>
                      Verbindung testen
                    </v-btn>
                  </template>

                  <v-alert
                    v-if="testResult"
                    :type="testResult.success ? 'success' : 'error'"
                    variant="tonal"
                    class="mt-4"
                  >
                    <div class="font-weight-bold">{{ testResult.message }}</div>
                    <div v-if="testResult.success && testResult.version" class="text-body-2 mt-1">
                      Proxmox VE {{ testResult.version }}
                      <span v-if="testResult.cluster_name">
                        | Cluster: {{ testResult.cluster_name }}
                      </span>
                      <span v-if="testResult.node_count">
                        | {{ testResult.node_count }} Node(s)
                      </span>
                    </div>
                    <div v-if="testResult.error" class="text-body-2 mt-1">
                      {{ testResult.error }}
                    </div>
                  </v-alert>
                </v-card-text>
              </v-card>
            </template>

            <!-- Schritt 3: Optionale Einstellungen -->
            <template v-slot:item.3>
              <v-card flat>
                <v-card-text>
                  <h3 class="text-h6 mb-4">
                    <v-icon class="mr-2">mdi-tune</v-icon>
                    Optionale Einstellungen
                  </h3>

                  <v-expansion-panels variant="accordion">
                    <!-- SSH/Ansible -->
                    <v-expansion-panel>
                      <v-expansion-panel-title>
                        <v-icon class="mr-2" size="small">mdi-ansible</v-icon>
                        Ansible / SSH
                      </v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <v-text-field
                          v-model="config.ansible_remote_user"
                          label="SSH-Benutzer für Ansible"
                          prepend-inner-icon="mdi-account"
                          hint="Benutzer auf den Ziel-VMs"
                          persistent-hint
                          variant="outlined"
                          density="compact"
                          class="mb-4"
                        ></v-text-field>

                        <v-alert type="info" variant="tonal" density="compact">
                          Der SSH-Key muss unter <code>data/ssh/id_ed25519</code> abgelegt werden.
                          Der Public Key muss auf allen Ziel-VMs hinterlegt sein.
                        </v-alert>
                      </v-expansion-panel-text>
                    </v-expansion-panel>

                    <!-- NetBox -->
                    <v-expansion-panel>
                      <v-expansion-panel-title>
                        <v-icon class="mr-2" size="small">mdi-ip-network-outline</v-icon>
                        NetBox IPAM
                      </v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <v-radio-group v-model="netboxMode" class="mb-4">
                          <v-radio value="integrated" label="Integriertes NetBox (im Container)"></v-radio>
                          <v-radio value="external" label="Externes NetBox (eigene Instanz)"></v-radio>
                          <v-radio value="none" label="NetBox nicht verwenden"></v-radio>
                        </v-radio-group>

                        <!-- Integriertes NetBox -->
                        <div v-if="netboxMode === 'integrated'">
                          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
                            Das integrierte NetBox wird automatisch mit der Applikation gestartet.
                            Konfiguriere hier die Admin-Zugangsdaten.
                          </v-alert>

                          <v-text-field
                            v-model="config.netbox_admin_user"
                            label="Admin-Benutzername"
                            prepend-inner-icon="mdi-account"
                            hint="Standard: admin"
                            persistent-hint
                            variant="outlined"
                            density="compact"
                            class="mb-4"
                          ></v-text-field>

                          <v-text-field
                            v-model="config.netbox_admin_password"
                            label="Admin-Passwort"
                            prepend-inner-icon="mdi-lock"
                            :type="showNetboxPassword ? 'text' : 'password'"
                            :append-inner-icon="showNetboxPassword ? 'mdi-eye' : 'mdi-eye-off'"
                            @click:append-inner="showNetboxPassword = !showNetboxPassword"
                            hint="Mindestens 4 Zeichen"
                            persistent-hint
                            variant="outlined"
                            density="compact"
                            class="mb-4"
                            :rules="[v => !!v || 'Passwort erforderlich', v => (v && v.length >= 4) || 'Min. 4 Zeichen']"
                          ></v-text-field>

                          <v-text-field
                            v-model="config.netbox_admin_email"
                            label="Admin E-Mail"
                            prepend-inner-icon="mdi-email"
                            hint="Optional, aber empfohlen"
                            persistent-hint
                            variant="outlined"
                            density="compact"
                            class="mb-4"
                          ></v-text-field>

                          <v-divider class="my-4"></v-divider>

                          <v-text-field
                            v-model="config.netbox_token"
                            label="NetBox API Token"
                            prepend-inner-icon="mdi-key-variant"
                            hint="Für interne Kommunikation zwischen Commander und NetBox"
                            persistent-hint
                            variant="outlined"
                            density="compact"
                            readonly
                            class="mb-2"
                          >
                            <template v-slot:append>
                              <v-btn
                                icon
                                size="small"
                                variant="text"
                                @click="generateNetboxToken"
                                title="Neuen Token generieren"
                              >
                                <v-icon>mdi-refresh</v-icon>
                              </v-btn>
                            </template>
                          </v-text-field>

                          <v-btn
                            v-if="!config.netbox_token"
                            color="primary"
                            variant="tonal"
                            size="small"
                            @click="generateNetboxToken"
                          >
                            <v-icon left class="mr-2">mdi-key-plus</v-icon>
                            Token generieren
                          </v-btn>
                        </div>

                        <!-- Externes NetBox -->
                        <div v-if="netboxMode === 'external'">
                          <v-alert type="warning" variant="tonal" density="compact" class="mb-4">
                            Bei Verwendung eines externen NetBox wird der integrierte Container nicht genutzt.
                            Die URL muss vom Backend aus erreichbar sein.
                          </v-alert>

                          <v-text-field
                            v-model="config.netbox_url"
                            label="NetBox URL"
                            placeholder="https://netbox.example.com"
                            prepend-inner-icon="mdi-web"
                            hint="Vollständige URL inkl. Protokoll"
                            persistent-hint
                            variant="outlined"
                            density="compact"
                            class="mb-4"
                          ></v-text-field>

                          <v-text-field
                            v-model="config.netbox_token"
                            label="NetBox API Token"
                            prepend-inner-icon="mdi-key-variant"
                            hint="API-Token mit Schreibrechten"
                            persistent-hint
                            variant="outlined"
                            density="compact"
                          ></v-text-field>
                        </div>

                        <!-- Kein NetBox -->
                        <div v-if="netboxMode === 'none'">
                          <v-alert type="info" variant="tonal" density="compact">
                            Ohne NetBox ist keine automatische IP-Adressverwaltung verfügbar.
                            Du kannst NetBox später in den Einstellungen konfigurieren.
                          </v-alert>
                        </div>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>
                </v-card-text>
              </v-card>
            </template>

            <!-- Schritt 4: Zusammenfassung -->
            <template v-slot:item.4>
              <v-card flat>
                <v-card-text>
                  <h3 class="text-h6 mb-4">
                    <v-icon class="mr-2">mdi-check-circle-outline</v-icon>
                    Zusammenfassung
                  </h3>

                  <v-table density="compact">
                    <tbody>
                      <tr>
                        <td class="font-weight-bold">Proxmox Host</td>
                        <td>{{ config.proxmox_host }}</td>
                      </tr>
                      <tr>
                        <td class="font-weight-bold">Token ID</td>
                        <td>{{ config.proxmox_token_id }}</td>
                      </tr>
                      <tr>
                        <td class="font-weight-bold">SSL-Verifizierung</td>
                        <td>{{ config.proxmox_verify_ssl ? 'Aktiviert' : 'Deaktiviert' }}</td>
                      </tr>
                      <tr>
                        <td class="font-weight-bold">Ansible-User</td>
                        <td>{{ config.ansible_remote_user }}</td>
                      </tr>
                      <tr>
                        <td class="font-weight-bold">NetBox</td>
                        <td>
                          <span v-if="netboxMode === 'integrated'">
                            Integriert{{ config.netbox_token ? ' (Token konfiguriert)' : '' }}
                          </span>
                          <span v-else-if="netboxMode === 'external'">
                            Extern: {{ config.netbox_url || 'URL fehlt' }}
                          </span>
                          <span v-else>Deaktiviert</span>
                        </td>
                      </tr>
                      <tr v-if="netboxMode === 'integrated'">
                        <td class="font-weight-bold">NetBox Admin</td>
                        <td>{{ config.netbox_admin_user }} / {{ config.netbox_admin_password ? '******' : '(kein Passwort)' }}</td>
                      </tr>
                    </tbody>
                  </v-table>

                  <v-alert type="warning" variant="tonal" class="mt-4">
                    <v-icon>mdi-restart</v-icon>
                    Nach dem Speichern müssen die Container mit
                    <code>docker compose down && docker compose up -d</code>
                    neu gestartet werden (restart reicht nicht!).
                  </v-alert>
                </v-card-text>
              </v-card>
            </template>

            <!-- Navigation Actions -->
            <template v-slot:actions>
              <v-card-actions class="pa-4">
                <v-btn
                  v-if="step > 1"
                  variant="text"
                  @click="step--"
                  :disabled="saving"
                >
                  <v-icon left>mdi-chevron-left</v-icon>
                  Zurück
                </v-btn>

                <v-spacer></v-spacer>

                <v-btn
                  v-if="step < 4"
                  color="primary"
                  :disabled="!canProceed"
                  @click="nextStep"
                >
                  Weiter
                  <v-icon right>mdi-chevron-right</v-icon>
                </v-btn>

                <v-btn
                  v-else
                  color="success"
                  :loading="saving"
                  :disabled="!canSave"
                  @click="saveConfig"
                >
                  <v-icon left class="mr-2">mdi-content-save</v-icon>
                  Konfiguration speichern
                </v-btn>
              </v-card-actions>
            </template>
          </v-stepper>
        </v-card>

        <!-- Weiterleitung zur Login-Seite -->
        <v-dialog v-model="redirectingToLogin" persistent max-width="400">
          <v-card>
            <v-card-text class="text-center py-8">
              <v-progress-circular
                indeterminate
                color="success"
                size="64"
                class="mb-4"
              ></v-progress-circular>
              <h3 class="text-h6 mb-2">Setup abgeschlossen!</h3>
              <p class="text-body-2 text-grey-darken-1 mb-4">
                Weiterleitung zur Anmeldung...
              </p>
              <v-alert type="info" variant="tonal" density="compact">
                <strong>Standard-Login:</strong> admin / admin
              </v-alert>
            </v-card-text>
          </v-card>
        </v-dialog>

        <!-- Erfolgs-Dialog (Fallback wenn Restart nötig) -->
        <v-dialog v-model="showSuccessDialog" persistent max-width="500">
          <v-card>
            <v-card-title class="text-h5 bg-success text-white">
              <v-icon class="mr-2">mdi-check-circle</v-icon>
              Setup abgeschlossen
            </v-card-title>
            <v-card-text class="pt-4">
              <p>Die Konfiguration wurde erfolgreich gespeichert.</p>
              <p class="font-weight-bold">
                Bitte starte die Container neu, damit die Einstellungen wirksam werden:
              </p>
              <v-code class="d-block pa-3 bg-grey-lighten-4">
                docker compose down && docker compose up -d
              </v-code>
              <p class="mt-4 text-grey-darken-1">
                Nach dem Neustart kannst du dich mit dem Standard-Login anmelden:<br>
                <strong>Benutzername:</strong> admin<br>
                <strong>Passwort:</strong> admin
              </p>
            </v-card-text>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn color="primary" @click="refreshPage">
                Seite neu laden
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

// Stepper State
const step = ref(1)
const steps = [
  { title: 'Willkommen', value: 1 },
  { title: 'Proxmox', value: 2 },
  { title: 'Optionen', value: 3 },
  { title: 'Fertig', value: 4 },
]

// Config State
const config = ref({
  proxmox_host: '',
  proxmox_token_id: '',
  proxmox_token_secret: '',
  proxmox_verify_ssl: false,
  ansible_remote_user: 'ansible',
  default_ssh_user: 'ansible',
  netbox_token: '',
  netbox_url: '',
  // NetBox Admin Credentials
  netbox_admin_user: 'admin',
  netbox_admin_password: '',
  netbox_admin_email: 'admin@example.com',
})

// NetBox Mode: 'integrated', 'external', 'none'
const netboxMode = ref('integrated')

// UI State
const showSecret = ref(false)
const showNetboxPassword = ref(false)
const testing = ref(false)
const saving = ref(false)
const testResult = ref(null)
const showSuccessDialog = ref(false)
const redirectingToLogin = ref(false)

// Validation Errors
const errors = ref({
  proxmox_host: '',
  proxmox_token_id: '',
  proxmox_token_secret: '',
})

// Computed
const canTest = computed(() => {
  return config.value.proxmox_host &&
         config.value.proxmox_token_id &&
         config.value.proxmox_token_secret
})

const canProceed = computed(() => {
  if (step.value === 2) {
    // Proxmox-Schritt: Verbindung muss erfolgreich getestet sein
    return testResult.value?.success === true
  }
  return true
})

const canSave = computed(() => {
  return testResult.value?.success === true
})

// Methods
function clearError(field) {
  errors.value[field] = ''
}

function generateNetboxToken() {
  // Generiere einen 40-Zeichen hex Token (NetBox Standard-Format)
  const array = new Uint8Array(20)
  crypto.getRandomValues(array)
  config.value.netbox_token = Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('')
}

function validateProxmoxFields() {
  let valid = true

  if (!config.value.proxmox_host) {
    errors.value.proxmox_host = 'Proxmox Host ist erforderlich'
    valid = false
  }

  if (!config.value.proxmox_token_id) {
    errors.value.proxmox_token_id = 'Token ID ist erforderlich'
    valid = false
  } else if (!config.value.proxmox_token_id.includes('!')) {
    errors.value.proxmox_token_id = 'Token ID muss das Format user@realm!token-name haben'
    valid = false
  }

  if (!config.value.proxmox_token_secret) {
    errors.value.proxmox_token_secret = 'Token Secret ist erforderlich'
    valid = false
  }

  return valid
}

async function testConnection() {
  if (!validateProxmoxFields()) {
    return
  }

  testing.value = true
  testResult.value = null

  try {
    const response = await axios.post('/api/setup/validate/proxmox', {
      host: config.value.proxmox_host,
      token_id: config.value.proxmox_token_id,
      token_secret: config.value.proxmox_token_secret,
      verify_ssl: config.value.proxmox_verify_ssl,
    })

    testResult.value = response.data
  } catch (error) {
    testResult.value = {
      success: false,
      message: 'Verbindungstest fehlgeschlagen',
      error: error.response?.data?.detail || error.message,
    }
  } finally {
    testing.value = false
  }
}

function nextStep() {
  if (step.value === 2 && !validateProxmoxFields()) {
    return
  }
  step.value++
}

async function saveConfig() {
  saving.value = true

  // NetBox-Konfiguration basierend auf Modus
  let netboxToken = null
  let netboxUrl = null
  let netboxAdminUser = 'admin'
  let netboxAdminPassword = 'admin'
  let netboxAdminEmail = 'admin@example.com'

  if (netboxMode.value === 'integrated') {
    netboxToken = config.value.netbox_token || null
    netboxUrl = null  // Verwendet Standard: http://netbox:8080
    netboxAdminUser = config.value.netbox_admin_user || 'admin'
    netboxAdminPassword = config.value.netbox_admin_password || 'admin'
    netboxAdminEmail = config.value.netbox_admin_email || 'admin@example.com'
  } else if (netboxMode.value === 'external') {
    netboxToken = config.value.netbox_token || null
    netboxUrl = config.value.netbox_url || null
  }
  // Bei 'none': beide bleiben null

  try {
    const response = await axios.post('/api/setup/save', {
      proxmox_host: config.value.proxmox_host,
      proxmox_token_id: config.value.proxmox_token_id,
      proxmox_token_secret: config.value.proxmox_token_secret,
      proxmox_verify_ssl: config.value.proxmox_verify_ssl,
      ansible_remote_user: config.value.ansible_remote_user,
      default_ssh_user: config.value.default_ssh_user,
      netbox_token: netboxToken,
      netbox_url: netboxUrl,
      netbox_admin_user: netboxAdminUser,
      netbox_admin_password: netboxAdminPassword,
      netbox_admin_email: netboxAdminEmail,
    })

    // Prüfen ob Konfiguration direkt geladen wurde (kein Restart nötig)
    if (response.data.restart_required === false) {
      // Direkt zur Login-Seite weiterleiten
      redirectingToLogin.value = true
      setTimeout(() => {
        window.location.href = '/login'
      }, 1500)
    } else {
      // Fallback: Restart erforderlich - Dialog anzeigen
      showSuccessDialog.value = true
    }
  } catch (error) {
    testResult.value = {
      success: false,
      message: 'Speichern fehlgeschlagen',
      error: error.response?.data?.detail || error.message,
    }
  } finally {
    saving.value = false
  }
}

function refreshPage() {
  window.location.reload()
}
</script>

<style scoped>
.v-stepper {
  box-shadow: none;
}
</style>
