<template>
  <img
    :src="logoSrc"
    :alt="alt"
    :class="logoClass"
    :style="customStyle"
  />
</template>

<script setup>
import { computed } from 'vue'
import { useTheme } from 'vuetify'

// Logo Assets
import logoIcon from '@/assets/logo.svg'
import logoBannerLight from '@/assets/logo-banner-light.svg'
import logoBannerDark from '@/assets/logo-banner-dark.svg'

const props = defineProps({
  // 'icon' = nur das grafische Logo, 'banner' = komplettes Banner mit Text
  variant: {
    type: String,
    default: 'icon',
    validator: (value) => ['icon', 'banner'].includes(value)
  },
  // Groesse: 'xs', 'sm', 'md', 'lg', 'xl' oder custom via style
  size: {
    type: String,
    default: 'md'
  },
  // Alt-Text
  alt: {
    type: String,
    default: 'Proxmox Commander Logo'
  },
  // Custom inline styles
  customStyle: {
    type: Object,
    default: () => ({})
  }
})

const theme = useTheme()

// Ist Dark Mode aktiv?
const isDark = computed(() => {
  const themeName = theme.global.name.value
  return themeName.endsWith('Dark')
})

// Logo-Quelle basierend auf Variante und Theme
const logoSrc = computed(() => {
  if (props.variant === 'icon') {
    // Icon funktioniert auf beiden Themes (hat eigenen Hintergrund)
    return logoIcon
  }
  // Banner: Theme-abhaengig
  return isDark.value ? logoBannerDark : logoBannerLight
})

// CSS-Klassen basierend auf Groesse und Variante
const logoClass = computed(() => {
  const classes = ['app-logo']
  classes.push(`app-logo--${props.variant}`)
  classes.push(`app-logo--${props.size}`)
  return classes
})
</script>

<style scoped>
.app-logo {
  display: block;
  object-fit: contain;
}

/* Icon Variante */
.app-logo--icon.app-logo--xs {
  width: 24px;
  height: 24px;
}

.app-logo--icon.app-logo--sm {
  width: 32px;
  height: 32px;
}

.app-logo--icon.app-logo--md {
  width: 40px;
  height: 40px;
}

.app-logo--icon.app-logo--lg {
  width: 56px;
  height: 56px;
}

.app-logo--icon.app-logo--xl {
  width: 80px;
  height: 80px;
}

/* Banner Variante */
.app-logo--banner.app-logo--xs {
  height: 40px;
  width: auto;
}

.app-logo--banner.app-logo--sm {
  height: 60px;
  width: auto;
}

.app-logo--banner.app-logo--md {
  height: 80px;
  width: auto;
}

.app-logo--banner.app-logo--lg {
  height: 120px;
  width: auto;
}

.app-logo--banner.app-logo--xl {
  height: 160px;
  width: auto;
}
</style>
