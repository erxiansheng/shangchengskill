<template>
  <div class="profile-container container">
    <div class="profile-header glass-panel">
      <div class="user-info">
        <div class="avatar-lg">
          <img :src="user?.avatar_url || 'https://api.dicebear.com/7.x/avataaars/svg?seed=Lobster'" alt="User" />
        </div>
        <div class="info-text">
          <h1>{{ user?.nickname || '加载中...' }}
            <span class="badge level admin-badge" v-if="user?.role === 'admin'">🔧 管理员</span>
            <span class="badge level level-badge-wrap" v-else-if="user" @click="showLevelModal = true" style="cursor:pointer">
              {{ userLevelInfo.icon }} {{ userLevelInfo.name }}
              <span class="level-exp">EXP {{ userLevelInfo.exp }}</span>
            </span>
          </h1>
          <p class="bio">{{ user?.bio || '这只龙虾还没有签名' }}</p>
          <div class="meta">
            <span>ID: {{ user?.username || '--' }}</span>
            <span class="dot">•</span>
            <span>加入于 {{ formatDateShort(user?.created_at) || '--' }}</span>
          </div>
        </div>
      </div>

      <div class="stats-cards">
        <div class="stat-card" @click="$router.push('/points')">
          <div class="stat-val text-gradient">{{ user?.points_balance?.toLocaleString() || 0 }}</div>
          <div class="stat-label">积分余额 💰</div>
        </div>
        <div class="stat-card" @click="switchSection('purchased')">
          <div class="stat-val">{{ purchaseCount }}</div>
          <div class="stat-label">已购商品 📦</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">{{ skillsTotal }}</div>
          <div class="stat-label">发布商品 📋</div>
        </div>
      </div>
    </div>

    <div class="profile-layout">
      <!-- Sidebar Menu -->
      <div class="menu-sidebar glass-panel">
        <ul class="profile-menu">
          <li :class="{ active: activeSection === 'skills' }" @click="switchSection('skills')"><span class="icon">📋</span> 我发布的商品</li>
          <li :class="{ active: activeSection === 'favorites' }" @click="switchSection('favorites')"><span class="icon">⭐</span> 我的收藏</li>
          <li :class="{ active: activeSection === 'purchased' }" @click="switchSection('purchased')"><span class="icon">📦</span> 已购商品</li>
          <li :class="{ active: activeSection === 'revenue' }" @click="switchSection('revenue')"><span class="icon">📊</span> 收益统计</li>
          <li class="divider"></li>
          <li :class="{ active: $route.name === 'Points' }" @click="$router.push('/points')"><span class="icon">💳</span> 充值与流水</li>
          <li :class="{ active: $route.name === 'Settings' }" @click="$router.push('/settings')"><span class="icon">⚙️</span> 账号设置</li>
          <li class="divider"></li>
          <li class="danger" @click="handleLogout"><span class="icon">🚪</span> 退出登录</li>
        </ul>
      </div>

      <!-- Main Content Area -->
      <div class="content-panel glass-panel">
        <!-- 我发布的商品 -->
        <template v-if="activeSection === 'skills'">
          <div class="panel-header">
            <h2>我发布的商品 ({{ skillsTotal }})</h2>
            <button class="btn btn-primary btn-sm" @click="$router.push('/upload')">+ 发布新商品</button>
          </div>

          <div v-if="skillsLoading" class="loading-state">
            <div class="loading-spinner"></div>
          </div>

          <div v-else-if="mySkills.length === 0" class="empty-state">
            <p>您还没有发布任何商品，去发布第一个吧！</p>
          </div>

          <div v-else class="my-skills-list">
            <div class="list-item" v-for="skill in mySkills" :key="skill.id" @click="$router.push(`/skill/${skill.id}`)">
              <div class="item-cover" :style="{ background: getVisual(skill.category_name).gradient }">
                <span style="font-size: 24px">{{ getVisual(skill.category_name).icon }}</span>
              </div>
              <div class="item-info">
                <h3>{{ skill.title }}</h3>
                <div class="item-meta">
                  <span>{{ formatDate(skill.updated_at || skill.created_at) }}</span>
                  <span class="status-tag" :class="skill.status">
                    {{ statusMap[skill.status] || skill.status }}
                  </span>
                </div>
                <div v-if="skill.status === 'rejected' && skill.reject_reason" class="reject-reason">
                  {{ skill.reject_reason }}
                </div>
                <div v-if="skill.status === 'offline' && skill.offline_reason" class="reject-reason">
                  下架原因：{{ skill.offline_reason }}
                </div>
              </div>
              <div class="item-actions">
                <div class="action-buttons">
                  <button class="btn-action btn-edit" @click="handleEdit(skill, $event)" title="更新">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </button>
                  <button
                    class="btn-action"
                    :class="skill.status === 'approved' ? 'btn-offline' : 'btn-online'"
                    @click="handleToggleStatus(skill, $event)"
                    :disabled="actionLoading === skill.id"
                    :title="skill.status === 'approved' ? '下架' : '上架'"
                  >
                    <svg v-if="skill.status === 'approved'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/></svg>
                    <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
                  </button>
                  <button class="btn-action btn-delete" @click="handleDeleteClick(skill, $event)" :disabled="actionLoading === skill.id" title="删除">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                  </button>
                </div>
                <div class="stats v-stats">
                  <span>📥 {{ skill.download_count || 0 }}</span>
                  <span>⭐ {{ skill.avg_rating || 0 }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="pagination" v-if="skillsTotalPages > 1">
            <button class="page-btn" :disabled="skillsPage <= 1" @click="changeSkillsPage(skillsPage - 1)">上一页</button>
            <span class="page-info">{{ skillsPage }} / {{ skillsTotalPages }}</span>
            <button class="page-btn" :disabled="skillsPage >= skillsTotalPages" @click="changeSkillsPage(skillsPage + 1)">下一页</button>
          </div>
        </template>

        <!-- 我的收藏 -->
        <template v-else-if="activeSection === 'favorites'">
          <div class="panel-header">
            <h2>我的收藏 ({{ Math.max(favoritesTotal, favorites.length) }})</h2>
          </div>

          <div v-if="favoritesLoading" class="loading-state">
            <div class="loading-spinner"></div>
          </div>

          <div v-else-if="favorites.length === 0" class="empty-state">
            <p>您还没有收藏任何商品</p>
            <button class="btn btn-primary btn-sm" style="margin-top: 12px;" @click="$router.push('/explore')">去探索市场</button>
          </div>

          <div v-else class="my-skills-list">
            <div class="list-item" v-for="item in favorites" :key="item.id" @click="$router.push(`/skill/${item.skill_id || item.id}`)">
              <div class="item-cover" :style="{ background: getVisual(item.category_name).gradient }">
                <span style="font-size: 24px">{{ getVisual(item.category_name).icon }}</span>
              </div>
              <div class="item-info">
                <h3>{{ item.title }}</h3>
                <div class="item-meta">
                  <span>{{ item.category_name || '商品' }}</span>
                  <span v-if="item.price != null" class="price-tag">{{ item.price === 0 ? '免费' : item.price + ' 积分' }}</span>
                </div>
              </div>
              <div class="item-actions">
                <div class="stats v-stats">
                  <span>📥 {{ item.download_count || 0 }}</span>
                  <span>⭐ {{ item.avg_rating || 0 }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="pagination" v-if="favoritesTotalPages > 1">
            <button class="page-btn" :disabled="favoritesPage <= 1" @click="changeFavoritesPage(favoritesPage - 1)">上一页</button>
            <span class="page-info">{{ favoritesPage }} / {{ favoritesTotalPages }}</span>
            <button class="page-btn" :disabled="favoritesPage >= favoritesTotalPages" @click="changeFavoritesPage(favoritesPage + 1)">下一页</button>
          </div>
        </template>

        <!-- 已购商品 -->
        <template v-else-if="activeSection === 'purchased'">
          <div class="panel-header">
            <h2>已购商品 ({{ purchasedTotal }})</h2>
          </div>

          <div v-if="purchasedLoading" class="loading-state">
            <div class="loading-spinner"></div>
          </div>

          <div v-else-if="purchasedList.length === 0" class="empty-state">
            <p>您还没有购买任何商品</p>
            <button class="btn btn-primary btn-sm" style="margin-top: 12px;" @click="$router.push('/explore')">去探索市场</button>
          </div>

          <div v-else class="my-skills-list">
            <div class="list-item" v-for="item in purchasedList" :key="item.id" @click="$router.push(`/skill/${item.skill_id}`)">
              <div class="item-cover" :style="{ background: getVisual(item.category_name).gradient }">
                <span style="font-size: 24px">{{ getVisual(item.category_name).icon }}</span>
              </div>
              <div class="item-info">
                <h3>{{ item.title }}</h3>
                <div class="item-meta">
                  <span>{{ item.category_name || '商品' }}</span>
                  <span>购买于 {{ formatDate(item.purchase_time) }}</span>
                </div>
              </div>
              <div class="item-actions">
                <button class="btn-action btn-download" @click.stop="handleDownload(item.skill_id)" title="下载">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                </button>
              </div>
            </div>
          </div>
          <div class="pagination" v-if="purchasedTotalPages > 1">
            <button class="page-btn" :disabled="purchasedPage <= 1" @click="changePurchasedPage(purchasedPage - 1)">上一页</button>
            <span class="page-info">{{ purchasedPage }} / {{ purchasedTotalPages }}</span>
            <button class="page-btn" :disabled="purchasedPage >= purchasedTotalPages" @click="changePurchasedPage(purchasedPage + 1)">下一页</button>
          </div>
        </template>

        <!-- 收益统计 -->
        <template v-else-if="activeSection === 'revenue'">
          <div class="panel-header">
            <h2>收益统计</h2>
          </div>

          <div class="revenue-stats">
            <div class="rev-stat">
              <span class="rev-label">累计收益</span>
              <span class="rev-val text-gradient">{{ (user?.total_earned || 0).toLocaleString() }}</span>
            </div>
            <div class="rev-stat">
              <span class="rev-label">当前余额</span>
              <span class="rev-val">{{ (user?.points_balance || 0).toLocaleString() }}</span>
            </div>
          </div>

          <div v-if="revenueLoading" class="loading-state">
            <div class="loading-spinner"></div>
          </div>

          <div v-else-if="revenueRecords.length === 0" class="empty-state">
            <p>暂无收益记录</p>
          </div>

          <div v-else class="revenue-list">
            <h3 style="margin-bottom: 16px; font-size: 16px;">收益记录</h3>
            <div class="r-item" v-for="record in revenueRecords" :key="record.id">
              <div class="r-info">
                <div class="r-title">{{ record.description || '收益入账' }}</div>
                <div class="r-time">{{ formatDate(record.created_at) }}</div>
              </div>
              <div class="r-amount">+{{ record.amount }}</div>
            </div>
          </div>
          <div class="pagination" v-if="revenueTotalPages > 1">
            <button class="page-btn" :disabled="revenuePage <= 1" @click="changeRevenuePage(revenuePage - 1)">上一页</button>
            <span class="page-info">{{ revenuePage }} / {{ revenueTotalPages }}</span>
            <button class="page-btn" :disabled="revenuePage >= revenueTotalPages" @click="changeRevenuePage(revenuePage + 1)">下一页</button>
          </div>
        </template>
      </div>
    </div>

    <!-- Delete Confirm Modal -->
    <ConfirmModal
      :visible="showDeleteConfirm"
      title="删除商品"
      :message="'确定要删除商品 &quot;' + (deleteTarget?.title || '') + '&quot; 吗？删除后商品将不再展示。'"
      confirmText="确认删除"
      cancelText="取消"
      type="danger"
      @confirm="confirmDelete"
      @cancel="showDeleteConfirm = false"
    />

    <!-- Level Info Modal -->
    <Teleport to="body">
      <div class="level-modal-overlay" v-if="showLevelModal" @click.self="showLevelModal = false">
        <div class="level-modal glass-panel">
          <div class="level-modal-header">
            <h3>🏆 等级体系</h3>
            <button class="level-modal-close" @click="showLevelModal = false">✕</button>
          </div>
          <div class="level-list">
            <div v-for="lv in allLevels" :key="lv.level"
              class="level-row" :class="{ 'level-current': userLevelInfo.level === lv.level, 'level-locked': userLevelInfo.exp < lv.min_exp }">
              <div class="level-icon-col">
                <span class="level-icon">{{ lv.icon }}</span>
                <div class="level-connector" v-if="lv.level < allLevels.length"></div>
              </div>
              <div class="level-info-col">
                <div class="level-name-row">
                  <span class="level-name">{{ lv.name }}</span>
                  <span class="level-tag current-tag" v-if="userLevelInfo.level === lv.level">当前</span>
                  <span class="level-tag locked-tag" v-else-if="userLevelInfo.exp < lv.min_exp">🔒</span>
                  <span class="level-tag done-tag" v-else>✓</span>
                </div>
                <div class="level-req">{{ lv.min_exp === 0 ? '初始等级' : lv.min_exp + ' 经验值' }}</div>
              </div>
            </div>
          </div>
          <div class="level-progress-section" v-if="userLevelInfo.next_level">
            <div class="progress-label">
              距离 {{ userLevelInfo.next_level.icon }} {{ userLevelInfo.next_level.name }} 还需
              <strong>{{ userLevelInfo.next_level.min_exp - userLevelInfo.exp }}</strong> 经验
            </div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: levelProgress + '%' }"></div>
            </div>
            <div class="progress-nums">
              <span>{{ userLevelInfo.exp }}</span>
              <span>{{ userLevelInfo.next_level.min_exp }}</span>
            </div>
          </div>
          <div class="level-progress-section" v-else>
            <div class="progress-label max-level">🎉 已达最高等级！当前经验 {{ userLevelInfo.exp }}</div>
          </div>
          <div class="exp-ways">
            <div class="exp-ways-title">经验获取方式</div>
            <div class="exp-way-grid">
              <div class="exp-way-item"><span class="exp-way-icon">📤</span><span>发布商品</span><span class="exp-way-val">+{{ expCfg.expPublish }}</span></div>
              <div class="exp-way-item"><span class="exp-way-icon">📥</span><span>被下载</span><span class="exp-way-val">+{{ expCfg.expDownload }}</span></div>
              <div class="exp-way-item"><span class="exp-way-icon">⭐</span><span>被收藏</span><span class="exp-way-val">+{{ expCfg.expFavorite }}</span></div>
              <div class="exp-way-item"><span class="exp-way-icon">💰</span><span>充值</span><span class="exp-way-val">+{{ expCfg.expRechargeYuan }}/元</span></div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getMe } from '../api/user.js'
import { getMySkills, deleteSkill, offlineSkill, onlineSkill } from '../api/skill.js'
import { getPurchases, downloadSkill, getRecords } from '../api/points.js'
import { getFavorites } from '../api/social.js'
import { userStore } from '../stores/user.js'
import { getSkillVisual, formatDateShort, formatDate } from '../utils.js'
import ConfirmModal from '../components/ConfirmModal.vue'
import { useToast, KV_SYNC_HINT } from '../composables/useToast.js'
import { getLevelInfo, getActiveLevels, getExpConfig } from '../utils/levels.js'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const user = computed(() => userStore.user)
const userLevelInfo = computed(() => {
  const info = user.value?.level_info
  if (info && info.name) return info
  return getLevelInfo(user.value?.exp || 0)
})
const showLevelModal = ref(false)
const allLevels = computed(() => getActiveLevels())
const expCfg = computed(() => getExpConfig())
const levelProgress = computed(() => {
  const info = userLevelInfo.value
  if (!info.next_level) return 100
  const prev = getActiveLevels().find(l => l.level === info.level)?.min_exp || 0
  const next = info.next_level.min_exp
  return Math.min(100, Math.round((info.exp - prev) / (next - prev) * 100))
})
const activeSection = ref('skills')
const mySkills = ref([])
const purchaseCount = ref(0)
const skillsLoading = ref(true)
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)
const actionLoading = ref(null)

const favorites = ref([])
const favoritesLoading = ref(false)
const favoritesLoaded = ref(false)
const purchasedList = ref([])
const purchasedLoading = ref(false)
const purchasedLoaded = ref(false)
const revenueRecords = ref([])
const revenueLoading = ref(false)
const revenueLoaded = ref(false)

const PAGE_SIZE = 10
const skillsPage = ref(1)
const skillsTotalPages = ref(1)
const skillsTotal = ref(0)
const favoritesPage = ref(1)
const favoritesTotalPages = ref(1)
const favoritesTotal = ref(0)
const purchasedPage = ref(1)
const purchasedTotalPages = ref(1)
const purchasedTotal = ref(0)
const revenuePage = ref(1)
const revenueTotalPages = ref(1)

const statusMap = {
  approved: '✅ 已上架',
  pending: '⏳ 审核中',
  rejected: '❌ 已拒绝',
  offline: '📴 已下架',
  deleted: '🗑️ 已删除',
}

const getVisual = (categoryName) => getSkillVisual(categoryName)

const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}

const handleEdit = (skill, e) => {
  e.stopPropagation()
  router.push(`/skill/${skill.id}/edit`)
}

const handleToggleStatus = async (skill, e) => {
  e.stopPropagation()
  actionLoading.value = skill.id
  try {
    if (skill.status === 'approved') {
      const res = await offlineSkill(skill.id)
      if (res.code === 0) {
        skill.status = 'offline'
        toast.success('商品已下架。' + KV_SYNC_HINT, '下架成功')
      } else {
        toast.error(res.message || '下架失败，请重试')
      }
    } else {
      const res = await onlineSkill(skill.id)
      if (res.code === 0) {
        const newStatus = res.data?.status || 'pending'
        skill.status = newStatus
        skill.reject_reason = res.data?.reject_reason || null
        if (newStatus === 'approved') {
          toast.success('审核通过，商品已上架。' + KV_SYNC_HINT, '审核通过')
        } else if (newStatus === 'rejected') {
          const reason = res.data?.reject_reason
          const isRateLimit = reason && reason.includes('频率限制')
          toast.error(isRateLimit ? '审核频率超限，请稍后再试点击上架' : (reason || '审核未通过，请修改后重新提交'), '审核未通过')
        } else {
          toast.warning('商品已提交审核。' + KV_SYNC_HINT, '审核中')
        }
      } else {
        toast.error(res.message || '上架失败，请重试')
      }
    }
  } catch (err) {
    toast.error('操作失败，请重试')
    console.error('Failed to toggle skill status:', err)
  } finally {
    actionLoading.value = null
  }
}

const handleDeleteClick = (skill, e) => {
  e.stopPropagation()
  deleteTarget.value = skill
  showDeleteConfirm.value = true
}

const switchSection = async (section) => {
  activeSection.value = section
  router.replace({ query: { tab: section !== 'skills' ? section : undefined } })
  if (section === 'favorites') {
    // 每次进入收藏 tab 都强制刷新，避免新增/取消收藏后计数不同步
    favoritesLoading.value = true
    try {
      const res = await getFavorites({ page: favoritesPage.value, page_size: PAGE_SIZE })
      if (res.code === 0) {
        favorites.value = res.data?.items || []
        favoritesTotalPages.value = res.data?.total_pages || 1
        // 服务端 total 与本页 items 取较大者，防御服务端 total 计算异常时仍能显示真实条数
        favoritesTotal.value = Math.max(res.data?.total || 0, (res.data?.items || []).length)
      }
      favoritesLoaded.value = true
    } catch (e) {
      console.error('Failed to load favorites:', e)
    } finally {
      favoritesLoading.value = false
    }
  }
  if (section === 'purchased' && !purchasedLoaded.value) {
    purchasedLoading.value = true
    try {
      const res = await getPurchases({ page: purchasedPage.value, page_size: PAGE_SIZE })
      if (res.code === 0) {
        purchasedList.value = res.data?.items || []
        purchaseCount.value = res.data?.total || 0
        purchasedTotalPages.value = res.data?.total_pages || 1
        purchasedTotal.value = res.data?.total || 0
      }
      purchasedLoaded.value = true
    } catch (e) {
      console.error('Failed to load purchases:', e)
    } finally {
      purchasedLoading.value = false
    }
  }
  if (section === 'revenue' && !revenueLoaded.value) {
    revenueLoading.value = true
    try {
      const res = await getRecords({ page: revenuePage.value, page_size: PAGE_SIZE, type: 'earning' })
      if (res.code === 0) {
        revenueRecords.value = (res.data?.items || []).filter(r => r.amount > 0)
        revenueTotalPages.value = res.data?.total_pages || 1
      }
      revenueLoaded.value = true
    } catch (e) {
      console.error('Failed to load revenue:', e)
    } finally {
      revenueLoading.value = false
    }
  }
}

const changeSkillsPage = async (p) => {
  skillsPage.value = p
  router.replace({ query: { ...route.query, page: p > 1 ? p : undefined } })
  skillsLoading.value = true
  try {
    const res = await getMySkills({ page: p, page_size: PAGE_SIZE })
    if (res.code === 0) {
      mySkills.value = res.data?.items || []
      skillsTotalPages.value = res.data?.total_pages || 1
      skillsTotal.value = res.data?.total || 0
    }
  } catch (e) { console.error(e) }
  finally { skillsLoading.value = false }
}

const changeFavoritesPage = async (p) => {
  favoritesPage.value = p
  router.replace({ query: { ...route.query, page: p > 1 ? p : undefined } })
  favoritesLoading.value = true
  try {
    const res = await getFavorites({ page: p, page_size: PAGE_SIZE })
    if (res.code === 0) {
      favorites.value = res.data?.items || []
      favoritesTotalPages.value = res.data?.total_pages || 1
      favoritesTotal.value = res.data?.total || 0
    }
  } catch (e) { console.error(e) }
  finally { favoritesLoading.value = false }
}

const changePurchasedPage = async (p) => {
  purchasedPage.value = p
  router.replace({ query: { ...route.query, page: p > 1 ? p : undefined } })
  purchasedLoading.value = true
  try {
    const res = await getPurchases({ page: p, page_size: PAGE_SIZE })
    if (res.code === 0) {
      purchasedList.value = res.data?.items || []
      purchasedTotalPages.value = res.data?.total_pages || 1
      purchasedTotal.value = res.data?.total || 0
    }
  } catch (e) { console.error(e) }
  finally { purchasedLoading.value = false }
}

const changeRevenuePage = async (p) => {
  revenuePage.value = p
  router.replace({ query: { ...route.query, page: p > 1 ? p : undefined } })
  revenueLoading.value = true
  try {
    const res = await getRecords({ page: p, page_size: PAGE_SIZE, type: 'earning' })
    if (res.code === 0) {
      revenueRecords.value = (res.data?.items || []).filter(r => r.amount > 0)
      revenueTotalPages.value = res.data?.total_pages || 1
    }
  } catch (e) { console.error(e) }
  finally { revenueLoading.value = false }
}

const handleDownload = async (skillId) => {
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
      toast.error(res.message || '获取下载链接失败')
    }
  } catch (e) {
    toast.error('网络错误')
  }
}

const confirmDelete = async () => {
  showDeleteConfirm.value = false
  if (!deleteTarget.value) return
  actionLoading.value = deleteTarget.value.id
  try {
    const res = await deleteSkill(deleteTarget.value.id)
    if (res.code === 0) {
      mySkills.value = mySkills.value.filter(s => s.id !== deleteTarget.value.id)
      toast.success('商品已删除。' + KV_SYNC_HINT, '删除成功')
    } else {
      toast.error(res.message || '删除失败，请重试')
    }
  } catch (err) {
    toast.error('网络错误，删除失败')
    console.error('Failed to delete skill:', err)
  } finally {
    actionLoading.value = null
    deleteTarget.value = null
  }
}

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }

  // Handle ?tab= and ?page= query parameters
  const tab = route.query.tab
  const initPage = parseInt(route.query.page) || 1
  if (tab === 'favorites' || tab === 'purchased' || tab === 'revenue') {
    if (tab === 'favorites') favoritesPage.value = initPage
    else if (tab === 'purchased') purchasedPage.value = initPage
    else if (tab === 'revenue') revenuePage.value = initPage
    switchSection(tab)
  } else {
    skillsPage.value = initPage
  }

  try {
    const [meRes, skillsRes, purchasesRes, favoritesRes] = await Promise.all([
      getMe(),
      getMySkills({ page: skillsPage.value, page_size: PAGE_SIZE }),
      getPurchases({ page: 1, page_size: 1 }),
      getFavorites({ page: 1, page_size: 1 })
    ])

    if (meRes.code === 0) userStore.updateUser(meRes.data)
    if (skillsRes.code === 0) {
      mySkills.value = skillsRes.data?.items || []
      skillsTotalPages.value = skillsRes.data?.total_pages || 1
      skillsTotal.value = skillsRes.data?.total || 0
    }
    if (purchasesRes.code === 0) purchaseCount.value = purchasesRes.data?.total || 0
    // 预加载收藏总数，避免"我的收藏 (0)"在用户切换 tab 前显示为 0
    if (favoritesRes.code === 0) favoritesTotal.value = favoritesRes.data?.total || 0
  } catch (e) {
    console.error('Failed to load profile:', e)
  } finally {
    skillsLoading.value = false
  }
})
</script>

<style scoped>
.profile-container {
  padding: 40px 24px 100px;
  max-width: 1080px;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 40px;
  margin-bottom: 24px;
}

.user-info { display: flex; align-items: center; gap: 24px; }

.avatar-lg {
  width: 96px; height: 96px; border-radius: 50%;
  background: var(--bg-surface); position: relative; overflow: hidden;
  cursor: pointer; border: 2px solid var(--border-glass);
}
.avatar-lg img { width: 100%; height: 100%; object-fit: cover; }
.edit-overlay {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: rgba(0,0,0,0.6); color: white; text-align: center;
  padding: 4px 0; font-size: 12px; opacity: 0; transition: var(--transition-smooth);
}
.avatar-lg:hover .edit-overlay { opacity: 1; }

.info-text h1 {
  font-size: 28px; font-weight: 700; margin-bottom: 8px;
  display: flex; align-items: center; gap: 12px;
}

.badge.level {
  font-size: 13px; padding: 4px 10px;
  background: linear-gradient(135deg, #FF9500, #FF2D55);
  border-radius: 99px; font-weight: 600;
  box-shadow: 0 2px 8px rgba(255, 149, 0, 0.4);
  cursor: pointer; position: relative;
}
.badge.admin-badge {
  background: linear-gradient(135deg, #5856D6, #AF52DE);
  box-shadow: 0 2px 8px rgba(88, 86, 214, 0.4);
}
.level-exp {
  font-size: 10px; opacity: 0.8; margin-left: 4px;
}

/* Level Modal */
.level-modal-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.6); backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
  animation: fadeIn 0.2s ease;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.level-modal {
  width: 420px; max-width: 92vw; max-height: 85vh; overflow-y: auto;
  padding: 28px; border-radius: 20px;
  background: rgba(28, 28, 34, 0.95);
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 24px 80px rgba(0,0,0,0.5);
  animation: modalSlideUp 0.25s ease;
}
@keyframes modalSlideUp { from { opacity:0; transform: translateY(20px); } to { opacity:1; transform: translateY(0); } }
.level-modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.level-modal-header h3 { margin: 0; font-size: 18px; }
.level-modal-close {
  background: rgba(255,255,255,0.08); border: none; color: var(--text-secondary);
  width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center; transition: background 0.2s;
}
.level-modal-close:hover { background: rgba(255,255,255,0.15); }
.level-list { display: flex; flex-direction: column; gap: 0; margin-bottom: 20px; }
.level-row {
  display: flex; gap: 14px; padding: 10px 0; position: relative;
  transition: opacity 0.2s;
}
.level-row.level-locked { opacity: 0.45; }
.level-row.level-current { opacity: 1; }
.level-icon-col { display: flex; flex-direction: column; align-items: center; width: 40px; flex-shrink: 0; }
.level-icon { font-size: 24px; line-height: 1; z-index: 1; }
.level-connector {
  width: 2px; flex: 1; min-height: 12px;
  background: linear-gradient(to bottom, rgba(255,255,255,0.15), rgba(255,255,255,0.05));
  margin-top: 4px;
}
.level-row.level-current .level-connector { background: linear-gradient(to bottom, #1ee07f, rgba(30,224,127,0.1)); }
.level-info-col { flex: 1; }
.level-name-row { display: flex; align-items: center; gap: 8px; }
.level-name { font-size: 15px; font-weight: 600; color: var(--text-primary, #e8e6e3); }
.level-tag { font-size: 11px; padding: 1px 8px; border-radius: 6px; font-weight: 600; }
.current-tag { background: rgba(30,224,127,0.18); color: #1ee07f; }
.done-tag { background: rgba(255,255,255,0.08); color: #8e8e93; }
.locked-tag { background: rgba(255,255,255,0.04); color: #636366; font-size: 10px; }
.level-req { font-size: 12px; color: var(--text-secondary, #8e8e93); margin-top: 2px; }
.level-progress-section { margin-bottom: 18px; }
.progress-label { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.progress-label strong { color: #1ee07f; }
.progress-label.max-level { text-align: center; font-size: 14px; color: #FFD700; }
.progress-track {
  height: 8px; border-radius: 4px; background: rgba(255,255,255,0.08); overflow: hidden;
}
.progress-fill {
  height: 100%; border-radius: 4px;
  background: linear-gradient(90deg, #1ee07f, #14b866);
  transition: width 0.5s ease;
}
.progress-nums { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-secondary, #8e8e93); margin-top: 4px; }
.exp-ways { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 14px; }
.exp-ways-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }
.exp-way-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.exp-way-item {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: var(--text-secondary);
  padding: 6px 10px; border-radius: 8px;
  background: rgba(255,255,255,0.03);
}
.exp-way-icon { font-size: 16px; }
.exp-way-val { margin-left: auto; font-weight: 600; color: #1ee07f; font-size: 12px; }

.bio { color: var(--text-secondary); font-size: 15px; margin-bottom: 8px; }
.meta { font-size: 13px; color: var(--text-tertiary); display: flex; gap: 8px; }

.stats-cards { display: flex; gap: 16px; }

.stat-card {
  background: rgba(255,255,255,0.03); border: 1px solid var(--border-glass);
  padding: 16px 24px; border-radius: 12px; text-align: center;
  transition: var(--transition-smooth); cursor: pointer;
}
.stat-card:hover { background: rgba(255,255,255,0.06); transform: translateY(-2px); }
.stat-val { font-size: 28px; font-weight: 800; margin-bottom: 4px; }
.stat-label { font-size: 13px; color: var(--text-secondary); }

.profile-layout { display: grid; grid-template-columns: 240px 1fr; gap: 24px; }

.menu-sidebar { padding: 16px 0; align-self: start; }
.profile-menu { list-style: none; margin: 0; padding: 0; }
.profile-menu li {
  padding: 12px 24px; color: var(--text-secondary); font-size: 15px;
  cursor: pointer; transition: var(--transition-smooth);
  display: flex; align-items: center; gap: 12px;
}
.profile-menu li:hover { background: var(--bg-surface-hover); color: var(--text-primary); }
.profile-menu li.active {
  color: var(--color-primary); background: rgba(255, 59, 48, 0.1);
  border-right: 3px solid var(--color-primary);
}
.profile-menu li.danger { color: #FF453A; }
.profile-menu li.divider { height: 1px; background: var(--border-glass); margin: 8px 0; padding: 0; }

.content-panel { padding: 32px; }
.panel-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 24px; border-bottom: 1px solid var(--border-glass); padding-bottom: 20px;
}
.panel-header h2 { font-size: 20px; }

.list-item {
  display: flex; align-items: center; padding: 20px;
  border: 1px solid var(--border-glass); border-radius: 12px;
  margin-bottom: 16px; transition: var(--transition-smooth); cursor: pointer;
}
.list-item:hover { background: rgba(255,255,255,0.02); border-color: rgba(255,255,255,0.2); }

.item-cover {
  width: 64px; height: 64px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; margin-right: 20px;
}

.item-info { flex: 1; }
.item-info h3 { font-size: 18px; margin-bottom: 8px; }
.item-meta { display: flex; align-items: center; gap: 12px; font-size: 13px; color: var(--text-tertiary); }

.status-tag {
  padding: 2px 8px; border-radius: 4px; font-size: 12px; background: rgba(255,255,255,0.1);
}
.status-tag.approved { background: rgba(52, 199, 89, 0.15); color: #34C759; }
.status-tag.pending { background: rgba(255, 149, 0, 0.15); color: #FF9500; }
.status-tag.rejected { background: rgba(255, 69, 58, 0.15); color: #FF453A; }

.reject-reason {
  font-size: 12px;
  color: #FF453A;
  margin-top: 4px;
  padding: 4px 8px;
  background: rgba(255, 69, 58, 0.08);
  border-radius: 4px;
}

.item-actions { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
.action-buttons { display: flex; gap: 6px; }
.btn-action {
  width: 32px; height: 32px; border-radius: 8px;
  border: 1px solid var(--border-glass); background: rgba(255,255,255,0.03);
  cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center;
  transition: var(--transition-smooth);
  color: var(--text-secondary);
}
.btn-action:hover { background: rgba(255,255,255,0.1); color: var(--text-primary); }
.btn-action:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-edit:hover { border-color: var(--color-primary); background: rgba(30, 224, 127, 0.1); color: var(--color-primary); }
.btn-offline:hover { border-color: #FF9500; background: rgba(255, 149, 0, 0.1); color: #FF9500; }
.btn-online:hover { border-color: #34C759; background: rgba(52, 199, 89, 0.1); color: #34C759; }
.btn-delete:hover { border-color: #FF453A; background: rgba(255, 69, 58, 0.1); color: #FF453A; }
.v-stats { display: flex; flex-direction: column; gap: 4px; text-align: right; font-size: 13px; color: var(--text-secondary); }

.price-tag { color: var(--color-primary); font-weight: 600; }
.btn-download { color: var(--color-primary); border-color: var(--color-primary); }
.btn-download:hover { background: rgba(30, 224, 127, 0.1); }

.loading-state, .empty-state { text-align: center; padding: 40px; color: var(--text-secondary); }

.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 24px; }
.page-btn {
  background: var(--bg-glass); border: 1px solid var(--border-glass); color: var(--text-primary);
  padding: 8px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; transition: var(--transition-smooth);
}
.page-btn:hover:not(:disabled) { background: var(--bg-surface-hover); border-color: var(--color-primary); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: 14px; color: var(--text-secondary); }

.revenue-stats {
  display: flex; gap: 24px; margin-bottom: 24px;
}
.rev-stat {
  flex: 1; padding: 20px; border-radius: 12px;
  background: var(--bg-glass); border: 1px solid var(--border-glass);
  display: flex; flex-direction: column; gap: 8px;
}
.rev-label { font-size: 13px; color: var(--text-secondary); }
.rev-val { font-size: 28px; font-weight: 700; }
.revenue-list { display: flex; flex-direction: column; gap: 12px; }
.r-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px; border-radius: 10px;
  background: var(--bg-glass); border: 1px solid var(--border-glass);
}
.r-info { display: flex; flex-direction: column; gap: 4px; }
.r-title { font-size: 14px; font-weight: 500; }
.r-time { font-size: 12px; color: var(--text-secondary); }
.r-amount { font-size: 16px; font-weight: 600; color: #34C759; }
.loading-spinner {
  width: 32px; height: 32px; border: 3px solid var(--border-glass);
  border-top-color: var(--color-primary); border-radius: 50%;
  animation: spin 0.8s linear infinite; margin: 0 auto;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .profile-header { flex-direction: column; text-align: center; gap: 32px; }
  .user-info { flex-direction: column; }
  .profile-layout { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .profile-container { padding: 20px 12px 60px; }
  .stats-cards { flex-wrap: wrap; gap: 10px; }
  .stat-card { flex: 1 1 calc(50% - 10px); min-width: 0; }
  .stat-val { font-size: 22px; }
  .profile-header { padding: 20px; }
  .item-info h3 { font-size: 15px; }
}
</style>
