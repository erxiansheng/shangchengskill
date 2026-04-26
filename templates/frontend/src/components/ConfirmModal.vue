<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click.self="$emit('cancel')">
        <div class="modal-dialog glass-panel">
          <div class="modal-icon" :class="type">
            <span v-if="type === 'danger'">⚠️</span>
            <span v-else-if="type === 'warning'">⚡</span>
            <span v-else>ℹ️</span>
          </div>
          <h3 class="modal-title">{{ title }}</h3>
          <p class="modal-message">{{ message }}</p>
          <div class="modal-actions">
            <button class="btn btn-glass" @click="$emit('cancel')">{{ cancelText }}</button>
            <button class="btn" :class="confirmBtnClass" @click="$emit('confirm')">{{ confirmText }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: '确认' },
  cancelText: { type: String, default: '取消' },
  type: { type: String, default: 'info' }, // 'danger' | 'warning' | 'info'
})

defineEmits(['confirm', 'cancel'])

const confirmBtnClass = computed(() => {
  if (props.type === 'danger') return 'btn-danger-solid'
  return 'btn-primary'
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal-dialog {
  width: 100%;
  max-width: 420px;
  padding: 36px;
  border-radius: 20px;
  text-align: center;
  animation: modalIn 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes modalIn {
  from { opacity: 0; transform: scale(0.9) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-icon {
  font-size: 40px;
  margin-bottom: 16px;
}

.modal-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.modal-message {
  font-size: 15px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 28px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.modal-actions .btn {
  min-width: 100px;
  padding: 10px 24px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-glass {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text-secondary);
}

.btn-glass:hover {
  background: rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
}

.btn-danger-solid {
  background: linear-gradient(135deg, #FF3B30, #FF453A);
  border: none;
  color: white;
  box-shadow: 0 4px 16px rgba(255, 59, 48, 0.3);
}

.btn-danger-solid:hover {
  box-shadow: 0 6px 24px rgba(255, 59, 48, 0.5);
  transform: translateY(-1px);
}

/* Transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
