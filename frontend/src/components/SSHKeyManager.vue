<template>
  <div class="ssh-key-manager">
    <!-- SSH-Benutzer -->
    <v-text-field
      v-model="sshUser"
      label="SSH-Benutzer fuer Ansible"
      prepend-inner-icon="mdi-account"
      :hint="userHint"
      persistent-hint
      variant="outlined"
      density="compact"
      class="mb-4"
      @update:model-value="emit('update:user', sshUser)"
    ></v-text-field>

    <v-alert v-if="showWarnings" type="warning" variant="tonal" density="compact" class="mb-4">
      <v-icon start size="small">mdi-alert</v-icon>
      Dieser Benutzer muss auf den Ziel-VMs existieren und SSH-Zugang haben.
    </v-alert>

    <!-- Aktueller Key Status (nur wenn Key existiert) -->
    <v-card v-if="currentConfig?.has_key" variant="outlined" class="mb-4">
      <v-card-title class="text-subtitle-1">
        <v-icon start size="small" color="success">mdi-check-circle</v-icon>
        Aktueller SSH-Key
      </v-card-title>
      <v-card-text class="pt-0">
        <v-list density="compact">
          <v-list-item>
            <template v-slot:prepend>
              <v-icon size="small">mdi-key</v-icon>
            </template>
            <v-list-item-title>Typ</v-list-item-title>
            <v-list-item-subtitle>{{ currentConfig.key_type?.toUpperCase() || 'Unbekannt' }}</v-list-item-subtitle>
          </v-list-item>
          <v-list-item v-if="currentConfig.key_fingerprint">
            <template v-slot:prepend>
              <v-icon size="small">mdi-fingerprint</v-icon>
            </template>
            <v-list-item-title>Fingerprint</v-list-item-title>
            <v-list-item-subtitle class="text-mono">{{ currentConfig.key_fingerprint }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <!-- Public Key anzeigen -->
        <div v-if="currentConfig.public_key" class="mt-2">
          <div class="text-caption text-grey mb-1">Public Key:</div>
          <v-textarea
            :model-value="currentConfig.public_key"
            readonly
            rows="2"
            variant="outlined"
            density="compact"
            class="text-mono"
            hide-details
          ></v-textarea>
          <v-btn
            size="small"
            variant="text"
            class="mt-1"
            @click="copyPublicKey(currentConfig.public_key)"
          >
            <v-icon start size="small">mdi-content-copy</v-icon>
            Kopieren
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- Key-Modus Auswahl -->
    <div class="text-subtitle-2 mb-2">
      <v-icon start size="small">mdi-key-variant</v-icon>
      SSH-Key {{ currentConfig?.has_key ? 'aendern' : 'einrichten' }}
    </div>

    <v-radio-group v-model="keyMode" class="mb-4" hide-details>
      <v-radio
        v-if="availableKeys.length > 0"
        value="import"
        label="Bestehenden Key importieren"
      ></v-radio>
      <v-radio value="upload" label="Key hochladen (Copy/Paste)"></v-radio>
      <v-radio value="generate" label="Neuen Key generieren"></v-radio>
    </v-radio-group>

    <!-- Import-Modus -->
    <div v-if="keyMode === 'import'" class="mb-4">
      <v-select
        v-model="selectedKey"
        :items="availableKeys"
        :item-title="item => `${item.name} (${item.type?.toUpperCase()})`"
        :item-value="item => item"
        label="Verfuegbarer Key"
        prepend-inner-icon="mdi-key"
        variant="outlined"
        density="compact"
        :hint="selectedKey?.fingerprint || 'Key auswaehlen'"
        persistent-hint
        return-object
      ></v-select>

      <v-alert v-if="!availableKeys.length" type="info" variant="tonal" density="compact" class="mt-2">
        Keine Keys im Host-SSH-Verzeichnis gefunden.
        Mounten Sie ~/.ssh nach /host-ssh im Container.
      </v-alert>

      <v-btn
        v-if="selectedKey"
        color="primary"
        variant="outlined"
        class="mt-3"
        :loading="importing"
        @click="importKey"
      >
        <v-icon start>mdi-import</v-icon>
        Key importieren
      </v-btn>
    </div>

    <!-- Upload-Modus -->
    <div v-if="keyMode === 'upload'" class="mb-4">
      <v-textarea
        v-model="uploadPrivateKey"
        label="Private Key"
        placeholder="-----BEGIN OPENSSH PRIVATE KEY-----&#10;...&#10;-----END OPENSSH PRIVATE KEY-----"
        prepend-inner-icon="mdi-key-chain"
        variant="outlined"
        density="compact"
        rows="6"
        class="text-mono"
        :hint="uploadPrivateKey ? 'Key erkannt' : 'Private Key einfuegen'"
        persistent-hint
      ></v-textarea>

      <v-alert type="warning" variant="tonal" density="compact" class="mt-2 mb-3">
        <v-icon start size="small">mdi-shield-alert</v-icon>
        Private Keys niemals teilen oder in unsichere Systeme eingeben!
      </v-alert>

      <v-btn
        color="primary"
        variant="outlined"
        :loading="uploading"
        :disabled="!uploadPrivateKey"
        @click="uploadKey"
      >
        <v-icon start>mdi-upload</v-icon>
        Key speichern
      </v-btn>
    </div>

    <!-- Generate-Modus -->
    <div v-if="keyMode === 'generate'" class="mb-4">
      <v-select
        v-model="generateKeyType"
        :items="[
          { value: 'ed25519', title: 'ED25519 (empfohlen)' },
          { value: 'rsa', title: 'RSA (4096 bit)' },
        ]"
        item-title="title"
        item-value="value"
        label="Key-Typ"
        prepend-inner-icon="mdi-key-plus"
        variant="outlined"
        density="compact"
        hint="ED25519 ist moderner und sicherer"
        persistent-hint
      ></v-select>

      <v-btn
        color="primary"
        variant="outlined"
        class="mt-3"
        :loading="generating"
        @click="generateKey"
      >
        <v-icon start>mdi-key-plus</v-icon>
        Neuen Key generieren
      </v-btn>

      <!-- Generierter Public Key -->
      <v-card v-if="generatedPublicKey" variant="outlined" class="mt-4" color="success">
        <v-card-title class="text-subtitle-1">
          <v-icon start color="success">mdi-check-circle</v-icon>
          Key erfolgreich generiert!
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            Kopiere diesen Public Key auf alle Ziel-VMs in die Datei
            <code>~/.ssh/authorized_keys</code> des SSH-Benutzers.
          </v-alert>
          <v-textarea
            :model-value="generatedPublicKey"
            readonly
            rows="3"
            variant="outlined"
            density="compact"
            class="text-mono"
            hide-details
          ></v-textarea>
          <v-btn
            size="small"
            color="primary"
            variant="text"
            class="mt-2"
            @click="copyPublicKey(generatedPublicKey)"
          >
            <v-icon start size="small">mdi-content-copy</v-icon>
            Public Key kopieren
          </v-btn>
        </v-card-text>
      </v-card>
    </div>

    <v-divider class="my-4"></v-divider>

    <!-- Verbindungstest -->
    <div class="text-subtitle-2 mb-2">
      <v-icon start size="small">mdi-connection</v-icon>
      Verbindungstest
    </div>

    <v-row>
      <v-col cols="12" sm="8">
        <v-combobox
          v-model="testHost"
          :items="inventoryHosts"
          :item-title="item => typeof item === 'string' ? item : `${item.name} (${item.ip})`"
          :item-value="item => typeof item === 'string' ? item : item.ip"
          label="Host"
          placeholder="IP-Adresse oder Hostname"
          prepend-inner-icon="mdi-server"
          variant="outlined"
          density="compact"
          :hint="showInventoryHint ? 'Aus Inventory oder manuell eingeben' : ''"
          persistent-hint
          clearable
        ></v-combobox>
      </v-col>
      <v-col cols="12" sm="4">
        <v-btn
          color="secondary"
          variant="outlined"
          :loading="testing"
          :disabled="!testHostValue"
          block
          @click="testConnection"
        >
          <v-icon start>mdi-lan-connect</v-icon>
          Testen
        </v-btn>
      </v-col>
    </v-row>

    <!-- Test-Ergebnis -->
    <v-alert
      v-if="testResult"
      :type="testResult.success ? 'success' : 'error'"
      variant="tonal"
      class="mt-3"
    >
      <div class="font-weight-bold">{{ testResult.message }}</div>
      <div v-if="testResult.success && testResult.remote_hostname" class="text-body-2 mt-1">
        Verbunden mit: {{ testResult.remote_hostname }}
      </div>
      <div v-if="testResult.error_details" class="text-body-2 mt-1">
        {{ testResult.error_details }}
      </div>
    </v-alert>

    <!-- Snackbar fuer Feedback -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  // Initialer SSH-Benutzer
  initialUser: {
    type: String,
    default: '',
  },
  // Warnungen anzeigen (fuer Settings-Kontext)
  showWarnings: {
    type: Boolean,
    default: false,
  },
  // API-Prefix (/api/setup oder /api/settings/ssh)
  apiPrefix: {
    type: String,
    default: '/api/setup',
  },
  // Inventory-Hosts fuer Verbindungstest
  inventoryHosts: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:user', 'key-changed', 'config-loaded'])

// State
const sshUser = ref(props.initialUser || 'ansible')
const keyMode = ref('upload')
const currentConfig = ref(null)
const availableKeys = ref([])
const selectedKey = ref(null)
const uploadPrivateKey = ref('')
const generateKeyType = ref('ed25519')
const generatedPublicKey = ref('')
const testHost = ref('')
const testResult = ref(null)

// Loading States
const loading = ref(false)
const importing = ref(false)
const uploading = ref(false)
const generating = ref(false)
const testing = ref(false)

// Snackbar
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

// Computed
const userHint = computed(() => {
  if (currentConfig.value?.ssh_user) {
    return `Aktuell: ${currentConfig.value.ssh_user}`
  }
  return 'Benutzer auf den Ziel-VMs'
})

const showInventoryHint = computed(() => props.inventoryHosts.length > 0)

const testHostValue = computed(() => {
  if (!testHost.value) return ''
  if (typeof testHost.value === 'string') return testHost.value
  return testHost.value.ip || testHost.value.name
})

// Methoden
function showMessage(text, color = 'success') {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

async function copyPublicKey(key) {
  try {
    await navigator.clipboard.writeText(key)
    showMessage('Public Key kopiert!')
  } catch (e) {
    showMessage('Kopieren fehlgeschlagen', 'error')
  }
}

async function loadConfig() {
  loading.value = true
  try {
    // Verfuegbare Keys laden
    const keysResponse = await axios.get(`${props.apiPrefix}/ssh-keys`)
    availableKeys.value = keysResponse.data.keys || []
    currentConfig.value = {
      has_key: !!keysResponse.data.current_key,
      key_type: keysResponse.data.current_key?.type,
      key_fingerprint: keysResponse.data.current_key?.fingerprint,
      public_key: null, // Wird separat geladen wenn noetig
      ssh_user: keysResponse.data.default_user,
    }

    // Default-User setzen wenn noch nicht gesetzt
    if (!sshUser.value || sshUser.value === 'ansible') {
      sshUser.value = keysResponse.data.default_user || 'ansible'
      emit('update:user', sshUser.value)
    }

    // Key-Modus setzen
    if (availableKeys.value.length > 0) {
      keyMode.value = 'import'
    }

    emit('config-loaded', currentConfig.value)
  } catch (e) {
    console.error('Fehler beim Laden der SSH-Konfiguration:', e)
  } finally {
    loading.value = false
  }
}

async function importKey() {
  if (!selectedKey.value) return

  importing.value = true
  try {
    const response = await axios.post(`${props.apiPrefix}/ssh-import`, {
      source_path: selectedKey.value.path,
    })

    if (response.data.success) {
      showMessage('SSH-Key erfolgreich importiert!')
      emit('key-changed', response.data)
      await loadConfig()
    } else {
      showMessage(response.data.message, 'error')
    }
  } catch (e) {
    showMessage(e.response?.data?.detail || 'Import fehlgeschlagen', 'error')
  } finally {
    importing.value = false
  }
}

async function uploadKey() {
  if (!uploadPrivateKey.value) return

  uploading.value = true
  try {
    const response = await axios.post(`${props.apiPrefix}/ssh-upload`, {
      private_key: uploadPrivateKey.value,
    })

    if (response.data.success) {
      showMessage('SSH-Key erfolgreich gespeichert!')
      uploadPrivateKey.value = ''
      if (response.data.public_key) {
        generatedPublicKey.value = response.data.public_key
      }
      emit('key-changed', response.data)
      await loadConfig()
    } else {
      showMessage(response.data.message, 'error')
    }
  } catch (e) {
    showMessage(e.response?.data?.detail || 'Upload fehlgeschlagen', 'error')
  } finally {
    uploading.value = false
  }
}

async function generateKey() {
  generating.value = true
  try {
    const response = await axios.post(`${props.apiPrefix}/ssh-generate`, {
      key_type: generateKeyType.value,
      comment: `${sshUser.value}@proxmox-commander`,
    })

    if (response.data.success) {
      showMessage('SSH-Key erfolgreich generiert!')
      generatedPublicKey.value = response.data.public_key
      emit('key-changed', response.data)
      await loadConfig()
    } else {
      showMessage(response.data.message, 'error')
    }
  } catch (e) {
    showMessage(e.response?.data?.detail || 'Generierung fehlgeschlagen', 'error')
  } finally {
    generating.value = false
  }
}

async function testConnection() {
  if (!testHostValue.value) return

  testing.value = true
  testResult.value = null
  try {
    const response = await axios.post(`${props.apiPrefix}/ssh-test`, {
      host: testHostValue.value,
      user: sshUser.value,
    })

    testResult.value = response.data
  } catch (e) {
    testResult.value = {
      success: false,
      message: 'Verbindungstest fehlgeschlagen',
      error_details: e.response?.data?.detail || e.message,
    }
  } finally {
    testing.value = false
  }
}

// Watch fuer initialen User
watch(() => props.initialUser, (newUser) => {
  if (newUser && newUser !== sshUser.value) {
    sshUser.value = newUser
  }
})

// Lifecycle
onMounted(() => {
  loadConfig()
})

// Public API
defineExpose({
  loadConfig,
  getSshUser: () => sshUser.value,
  hasKey: () => currentConfig.value?.has_key || false,
})
</script>

<style scoped>
.text-mono {
  font-family: 'Roboto Mono', monospace;
  font-size: 0.85rem;
}
</style>
