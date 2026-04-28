<template>
  <div class="purchased-container container">
    <div class="page-header">
      <h1 class="page-title">已购商品</h1>
      <p class="page-subtitle">数字商品可下载最新版本，实体商品可查看收货与发货信息。</p>
    </div>

    <div class="filter-bar glass-panel">
      <div class="search-wrap">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" placeholder="搜索已购商品..." class="filter-input" v-model="searchQuery" @keyup.enter="filterPurchases" />
      </div>
      <div class="tags-wrap">
        <button class="filter-tag active">全部 ({{ total }})</button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="filteredPurchases.length === 0" class="empty-state glass-panel">
      <p>{{ searchQuery ? '没有找到匹配的商品' : '您还没有购买任何商品' }}</p>
      <button class="btn btn-primary" style="margin-top: 16px;" @click="$router.push('/explore')">去探索市场</button>
    </div>

    <template v-else>
      <div class="purchased-list">
        <div class="msg-toast" v-if="toastMsg" :class="toastType">{{ toastMsg }}</div>
        <div class="purchased-card glass-panel" v-for="item in filteredPurchases" :key="item.id">
          <div class="card-left">
            <div class="skill-icon" :style="{ background: getVisual(item.category_name).gradient }">
              <span style="font-size: 32px">{{ getVisual(item.category_name).icon }}</span>
            </div>

            <div class="skill-info">
              <div class="skill-meta">
                <span class="tag">{{ item.category_name || '商品' }}</span>
                <span class="version">当前版本: v{{ item.version || '1.0.0' }}</span>
              </div>
              <h3 class="skill-name">{{ item.title }}</h3>
              <p class="purchase-date">购买时间: {{ formatDate(item.purchase_time) }}</p>
              <div class="shipping-info" v-if="item.is_physical && item.shipping_info">
                <span>{{ item.shipping_info.name }} · {{ item.shipping_info.phone }}</span>
                <span>{{ item.shipping_info.address }}</span>
                <span v-if="item.shipping_info.note">备注：{{ item.shipping_info.note }}</span>
              </div>
            </div>
          </div>

          <div class="card-right">
            <button v-if="!item.is_physical" class="btn btn-primary download-btn" @click="handleDownload(item.skill_id)">
              <span class="icon">⬇️</span>
              下载 (.zip)
            </button>
            <div v-else class="physical-status">
              <span class="status-dot"></span>
              {{ formatFulfillmentStatus(item.fulfillment_status) }}
            </div>
            <div class="actions">
              <a href="#" class="action-link text-gradient" @click.prevent="$router.push('/skill/' + item.skill_id)">查看文档</a>
              <span class="separator">|</span>
              <a href="#" class="action-link text-gradient" @click.prevent="$router.push('/skill/' + item.skill_id)">去评价</a>
            </div>
          </div>
        </div>
      </div>
      <div class="pagination" v-if="totalPages > 1">
        <button class="page-btn" :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
        <span class="page-info">{{ page }} / {{ totalPages }}</span>
        <button class="page-btn" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getPurchases, downloadSkill } from '../api/points.js'
import { userStore } from '../stores/user.js'
import { getSkillVisual, formatDate } from '../utils.js'

const router = useRouter()
const route = useRoute()

const purchases = ref([])
const loading = ref(true)
const total = ref(0)
const searchQuery = ref('')
const toastMsg = ref('')
const toastType = ref('error')
const page = ref(1)
const totalPages = ref(1)
const PAGE_SIZE = 10

const showToast = (msg, type = 'error') => {
  toastMsg.value = msg
  toastType.value = type
  setTimeout(() => { toastMsg.value = '' }, 3000)
}

const getVisual = (categoryName) => getSkillVisual(categoryName)

const formatFulfillmentStatus = (status) => {
  const map = {
    pending_shipment: '等待商家发货',
    shipped: '已发货',
    completed: '已完成',
  }
  return map[status] || '等待商家处理'
}

const filteredPurchases = computed(() => {
  if (!searchQuery.value.trim()) return purchases.value
  const q = searchQuery.value.toLowerCase()
  return purchases.value.filter(p => p.title?.toLowerCase().includes(q))
})

const filterPurchases = () => {
  // Computed already handles filtering reactively
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await getPurchases({ page: page.value, page_size: PAGE_SIZE })
    if (res.code === 0) {
      purchases.value = res.data?.items || []
      total.value = res.data?.total || 0
      totalPages.value = res.data?.total_pages || 1
    }
  } catch (e) {
    console.error('Failed to load purchases:', e)
  } finally {
    loading.value = false
  }
}

const changePage = (p) => {
  page.value = p
  router.replace({ query: { ...route.query, page: p > 1 ? p : undefined } })
  loadData()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const handleDownload = async (skillId) => {
  const item = purchases.value.find(p => p.skill_id === skillId)
  if (item?.is_physical) {
    showToast('实体商品无需下载，请等待商家发货', 'success')
    return
  }
  try {
    const res = await downloadSkill(skillId)
    if (res.code === 0 && res.data?.download_url) {
      const a = document.createElement('a')
      a.href = res.data.download_url
      a.download = res.data.filename || 'skill.zip'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } else {
      showToast(res.message || '获取下载链接失败')
    }
  } catch (e) {
    showToast('网络错误')
  }
}

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  page.value = parseInt(route.query.page) || 1
  loadData()
})
</script>

<style scoped>
.purchased-container { padding: 40px 24px 100px; max-width: 1080px; }

.page-header { margin-bottom: 32px; }
.page-title { font-size: 32px; font-weight: 800; margin-bottom: 8px; }
.page-subtitle { color: var(--text-secondary); }

.filter-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 24px; margin-bottom: 32px; border-radius: 12px;
  flex-wrap: wrap; gap: 16px;
}

.search-wrap { position: relative; width: 320px; }
.search-wrap .search-icon {
  position: absolute; left: 14px; top: 50%; transform: translateY(-50%);
  color: var(--text-tertiary); pointer-events: none; transition: color 0.2s;
}
.search-wrap:focus-within .search-icon { color: var(--color-primary); }

.filter-input {
  width: 100%; background: var(--bg-glass); border: 1px solid var(--border-glass);
  border-radius: 99px; padding: 11px 16px 11px 42px; color: var(--text-primary); outline: none;
  font-family: inherit; font-size: 14px; transition: var(--transition-smooth); backdrop-filter: blur(8px);
}
.filter-input::placeholder { color: var(--text-tertiary); }
.filter-input:focus { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-glow); background: var(--bg-surface); }

.tags-wrap { display: flex; gap: 12px; }
.filter-tag {
  background: var(--color-primary); border: 1px solid transparent;
  padding: 6px 16px; border-radius: 99px; color: white;
  cursor: pointer; font-size: 14px;
}

.purchased-list { display: flex; flex-direction: column; gap: 16px; }

.purchased-card {
  display: flex; justify-content: space-between; align-items: center;
  padding: 24px; border-radius: 16px; transition: transform 0.2s, background 0.2s;
}
.purchased-card:hover { background: rgba(255,255,255,0.05); transform: translateY(-2px); }

.card-left { display: flex; gap: 24px; align-items: center; }
.skill-icon {
  width: 80px; height: 80px; border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 16px rgba(0,0,0,0.3);
}

.skill-info { display: flex; flex-direction: column; justify-content: center; }
.skill-meta { display: flex; gap: 12px; margin-bottom: 8px; align-items: center; }
.tag { background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 4px; font-size: 12px; color: var(--text-secondary); }
.version { font-size: 13px; color: var(--color-accent); font-family: monospace; }
.skill-name { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
.purchase-date { font-size: 13px; color: var(--text-tertiary); }
.shipping-info { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; color: var(--text-secondary); font-size: 13px; line-height: 1.5; }

.card-right { display: flex; flex-direction: column; align-items: flex-end; gap: 16px; }
.download-btn { padding: 10px 24px; display: flex; align-items: center; gap: 8px; font-weight: 600; border-radius: 8px; }
.physical-status { min-width: 140px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 14px; border-radius: 8px; background: rgba(30,224,127,0.12); color: var(--color-primary); border: 1px solid rgba(30,224,127,0.28); font-weight: 600; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-primary); box-shadow: 0 0 10px rgba(30,224,127,0.65); }
.actions { display: flex; gap: 12px; align-items: center; font-size: 14px; }
.action-link { text-decoration: none; font-weight: 500; }
.separator { color: var(--text-tertiary); }

.loading-state, .empty-state { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
.loading-spinner {
  width: 40px; height: 40px; border: 3px solid var(--border-glass);
  border-top-color: var(--color-primary); border-radius: 50%;
  animation: spin 0.8s linear infinite; margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }

.msg-toast {
  padding: 10px 16px; border-radius: 8px; font-size: 14px; text-align: center; margin-bottom: 16px;
}
.msg-toast.error { background: rgba(255, 69, 58, 0.1); color: #FF453A; border: 1px solid rgba(255, 69, 58, 0.2); }
.msg-toast.success { background: rgba(52, 199, 89, 0.1); color: #34C759; border: 1px solid rgba(52, 199, 89, 0.2); }

.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 32px; }
.page-btn {
  background: var(--bg-glass); border: 1px solid var(--border-glass); color: var(--text-primary);
  padding: 8px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; transition: var(--transition-smooth);
}
.page-btn:hover:not(:disabled) { background: var(--bg-surface-hover); border-color: var(--color-primary); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: 14px; color: var(--text-secondary); }

@media (max-width: 768px) {
  .purchased-card { flex-direction: column; align-items: flex-start; gap: 24px; }
  .card-right { width: 100%; flex-direction: row; justify-content: space-between; align-items: center; }
}
@media (max-width: 600px) {
  .purchased-container { padding: 20px 12px 60px; }
  .search-wrap { width: 100%; }
  .page-title { font-size: 24px; }
}
</style>
