<template>
  <div class="revenue-container container">
    <div class="page-header">
      <h1 class="page-title">收益统计</h1>
      <p class="page-subtitle">让每一行代码都为您创造价值。</p>
    </div>

    <div class="stats-panel glass-panel">
      <div class="stat-main">
        <span>累计收益 (积分)</span>
        <div class="amount text-gradient">{{ totalEarned.toLocaleString() }}</div>
      </div>
      <div class="stat-sub">
        <div class="item"><span>当前余额</span><strong>{{ balance.toLocaleString() }}</strong></div>
        <div class="item"><span>已发布商品</span><strong>{{ skillCount }}</strong></div>
      </div>
    </div>

    <div class="records-section glass-panel" v-if="records.length > 0">
      <h2>收益记录</h2>
      <div class="revenue-list">
        <div class="r-item" v-for="record in records" :key="record.id">
          <div class="r-info">
            <div class="r-title">{{ record.description || '收益入账' }}</div>
            <div class="r-time">{{ formatDate(record.created_at) }}</div>
          </div>
          <div class="r-amount positive">+{{ record.amount }}</div>
        </div>
      </div>
      <div class="pagination" v-if="totalPages > 1">
        <button class="page-btn" :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
        <span class="page-info">{{ page }} / {{ totalPages }}</span>
        <button class="page-btn" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getMe } from '../api/user.js'
import { getRecords } from '../api/points.js'
import { getMySkills } from '../api/skill.js'
import { userStore } from '../stores/user.js'
import { formatDate } from '../utils.js'

const router = useRouter()
const route = useRoute()

const totalEarned = ref(0)
const balance = ref(0)
const skillCount = ref(0)
const records = ref([])
const page = ref(1)
const totalPages = ref(1)
const PAGE_SIZE = 10

const loadRecords = async () => {
  try {
    const recordsRes = await getRecords({ page: page.value, page_size: PAGE_SIZE, type: 'earning' })
    if (recordsRes.code === 0) {
      records.value = (recordsRes.data?.items || []).filter(r => r.amount > 0)
      totalPages.value = recordsRes.data?.total_pages || 1
    }
  } catch (e) {
    console.error('Failed to load records:', e)
  }
}

const changePage = (p) => {
  page.value = p
  router.replace({ query: { ...route.query, page: p > 1 ? p : undefined } })
  loadRecords()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }

  try {
    const [meRes, skillsRes] = await Promise.all([
      getMe(),
      getMySkills({ page: 1, page_size: 1 })
    ])

    if (meRes.code === 0) {
      totalEarned.value = meRes.data?.total_earned || 0
      balance.value = meRes.data?.points_balance || 0
      userStore.updateUser(meRes.data)
    }

    if (skillsRes.code === 0) {
      skillCount.value = skillsRes.data?.total || 0
    }
  } catch (e) {
    console.error('Failed to load revenue data:', e)
  }

  page.value = parseInt(route.query.page) || 1
  loadRecords()
})
</script>

<style scoped>
.revenue-container { padding: 40px 24px 100px; max-width: 800px; }
.page-header { margin-bottom: 32px; }
.page-title { font-size: 32px; font-weight: 800; margin-bottom: 8px; }
.page-subtitle { color: var(--text-secondary); }

.stats-panel { padding: 40px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
.stat-main span { color: var(--text-secondary); }
.stat-main .amount { font-size: 48px; font-weight: 800; font-family: var(--font-display); }
.stat-sub { display: flex; gap: 32px; }
.item { display: flex; flex-direction: column; gap: 4px; }
.item span { color: var(--text-tertiary); font-size: 14px; }
.item strong { color: var(--color-primary); font-size: 24px; font-family: var(--font-display); }

.records-section { padding: 32px; }
.records-section h2 { font-size: 20px; margin-bottom: 24px; }

.revenue-list { display: flex; flex-direction: column; gap: 16px; }
.r-item { display: flex; justify-content: space-between; align-items: center; padding: 16px; border: 1px solid var(--border-glass); border-radius: 8px; }
.r-title { font-size: 15px; color: var(--text-primary); margin-bottom: 4px; }
.r-time { font-size: 12px; color: var(--text-tertiary); font-family: monospace; }
.r-amount { font-weight: 700; font-size: 18px; }
.r-amount.positive { color: #34C759; }

.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 24px; }
.page-btn {
  background: var(--bg-glass); border: 1px solid var(--border-glass); color: var(--text-primary);
  padding: 8px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; transition: var(--transition-smooth);
}
.page-btn:hover:not(:disabled) { background: var(--bg-surface-hover); border-color: var(--color-primary); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: 14px; color: var(--text-secondary); }

@media (max-width: 600px) {
  .revenue-container { padding: 20px 12px 60px; }
  .page-title { font-size: 24px; }
  .stats-panel { flex-direction: column; align-items: flex-start; gap: 20px; padding: 24px; }
  .stat-main .amount { font-size: 32px; }
  .stat-sub { gap: 20px; flex-wrap: wrap; }
  .item strong { font-size: 18px; }
  .records-section { padding: 20px; }
}
</style>
