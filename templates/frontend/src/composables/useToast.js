import { ref } from 'vue'

const toasts = ref([])
let nextId = 0

/** KV 数据同步延迟提示文案，写入操作成功后附加 */
export const KV_SYNC_HINT = '数据同步可能有 1~60 秒延迟，请勿重复提交'

export function useToast() {
  const addToast = (message, type = 'info', title = '', duration = 3000) => {
    const id = ++nextId
    toasts.value.push({ id, message, type, title })
    if (duration > 0) {
      setTimeout(() => removeToast(id), duration)
    }
    return id
  }

  const removeToast = (id) => {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  const success = (message, title = '') => addToast(message, 'success', title)
  const error = (message, title = '') => addToast(message, 'error', title)
  const warning = (message, title = '') => addToast(message, 'warning', title)
  const info = (message, title = '') => addToast(message, 'info', title)

  return { toasts, addToast, removeToast, success, error, warning, info }
}
