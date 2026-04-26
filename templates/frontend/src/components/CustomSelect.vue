<template>
  <div class="custom-select" ref="selectRef" :class="{ open: isOpen }">
    <div class="select-trigger form-control" @click="toggleOpen" :class="{ 'has-value': modelValue }">
      <span class="select-icon" v-if="selectedOption?.icon">{{ selectedOption.icon }}</span>
      <span class="select-text">{{ selectedOption ? selectedOption.label : placeholder }}</span>
      <span class="select-arrow">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
    </div>

    <Transition name="dropdown">
      <div v-if="isOpen" class="select-dropdown glass-panel">
        <div
          v-for="(opt, idx) in options"
          :key="opt.value"
          class="select-option"
          :class="{ active: opt.value === modelValue, focused: idx === focusedIndex }"
          @click.stop="selectOption(opt)"
          @mouseenter="focusedIndex = idx"
        >
          <span class="option-icon" v-if="opt.icon">{{ opt.icon }}</span>
          <span class="option-label">{{ opt.label }}</span>
          <span class="option-check" v-if="opt.value === modelValue">✓</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number, null], default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '请选择...' },
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const focusedIndex = ref(-1)
const selectRef = ref(null)

const selectedOption = computed(() => props.options.find(o => o.value === props.modelValue) || null)

const toggleOpen = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    focusedIndex.value = props.options.findIndex(o => o.value === props.modelValue)
  }
}

const selectOption = (opt) => {
  emit('update:modelValue', opt.value)
  isOpen.value = false
}

const handleClickOutside = (e) => {
  if (selectRef.value && !selectRef.value.contains(e.target)) {
    isOpen.value = false
  }
}

const handleKeydown = (e) => {
  if (!isOpen.value) return

  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      focusedIndex.value = Math.min(focusedIndex.value + 1, props.options.length - 1)
      break
    case 'ArrowUp':
      e.preventDefault()
      focusedIndex.value = Math.max(focusedIndex.value - 1, 0)
      break
    case 'Enter':
      e.preventDefault()
      if (focusedIndex.value >= 0 && focusedIndex.value < props.options.length) {
        selectOption(props.options[focusedIndex.value])
      }
      break
    case 'Escape':
      isOpen.value = false
      break
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.custom-select {
  position: relative;
  width: 100%;
}

.select-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
}

.select-trigger:not(.has-value) .select-text {
  color: var(--text-tertiary);
}

.select-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.select-icon {
  flex-shrink: 0;
}

.select-arrow {
  flex-shrink: 0;
  color: var(--text-tertiary);
  transition: transform 0.2s;
  display: flex;
  align-items: center;
}

.custom-select.open .select-arrow {
  transform: rotate(180deg);
}

.custom-select.open .select-trigger {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-glow);
}

.select-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 1000;
  padding: 6px;
  border-radius: 12px;
  max-height: 240px;
  overflow-y: auto;
  background: rgba(20, 20, 30, 0.95);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
}

.select-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 14px;
  color: var(--text-secondary);
}

.select-option:hover,
.select-option.focused {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
}

.select-option.active {
  color: var(--color-primary);
  font-weight: 600;
}

.option-icon {
  flex-shrink: 0;
  font-size: 16px;
}

.option-label {
  flex: 1;
}

.option-check {
  color: var(--color-primary);
  font-weight: 700;
  font-size: 13px;
}

/* Scrollbar */
.select-dropdown::-webkit-scrollbar {
  width: 4px;
}
.select-dropdown::-webkit-scrollbar-track {
  background: transparent;
}
.select-dropdown::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 4px;
}

/* Transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

/* Light theme overrides */
:global([data-theme="light"]) .select-dropdown {
  background: rgba(255, 255, 255, 0.96) !important;
  border-color: rgba(0, 0, 0, 0.1) !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12) !important;
}
:global([data-theme="light"]) .select-option {
  color: #333 !important;
}
:global([data-theme="light"]) .select-option:hover,
:global([data-theme="light"]) .select-option.focused {
  background: rgba(0, 0, 0, 0.05) !important;
  color: #111 !important;
}
:global([data-theme="light"]) .select-option.active {
  color: var(--color-primary) !important;
}
</style>
