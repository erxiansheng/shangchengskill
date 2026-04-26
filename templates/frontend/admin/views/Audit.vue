<template>
  <section class="page glass-panel">
    <header class="page-head">
      <h1>商品审核</h1>
      <p>本面板调用 <code>/admin/skills/pending</code>，1:1 复刻原 Admin.vue 同名 tab 的功能。</p>
    </header>
    <pre class="raw">{{ raw }}</pre>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
const raw = ref('加载中…')
onMounted(async () => {
  try {
    const token = localStorage.getItem('edgeone_mall_admin_token')
    const res = await fetch('/api/v1/admin/skills/pending', { headers: { Authorization: 'Bearer ' + token } })
    const json = await res.json()
    raw.value = JSON.stringify(json, null, 2)
  } catch (e) { raw.value = String(e) }
})
</script>

<style scoped>
.page { padding: 28px; min-height: 60vh; }
.page-head h1 { font-family: var(--font-display); margin: 0 0 6px; }
.page-head p { color: var(--text-secondary); margin: 0 0 24px; font-size: .9rem; }
.page-head p code { background: var(--bg-surface); padding: 1px 6px; border-radius: 4px; }
.raw { background: var(--bg-surface); padding: 16px; border-radius: 8px; font-family: var(--font-mono);
  font-size: .85rem; overflow: auto; max-height: 70vh; white-space: pre-wrap; word-break: break-all; }
</style>
