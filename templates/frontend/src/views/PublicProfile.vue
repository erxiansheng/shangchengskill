<template>
  <div class="public-profile-container container">
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
    </div>

    <div v-else-if="!profile" class="empty-state glass-panel">
      <p>用户不存在</p>
      <button class="btn btn-primary btn-sm" style="margin-top: 12px" @click="$router.push('/')">返回首页</button>
    </div>

    <template v-else>
      <!-- Profile Header -->
      <div class="profile-card glass-panel">
        <div class="profile-top">
          <div class="avatar-lg">
            <img :src="profile.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${profile.id}`" alt="avatar" />
          </div>
          <div class="profile-info">
            <h1>{{ profile.nickname || '匿名用户' }}
              <span class="badge level admin-badge" v-if="profile.role === 'admin'">🔧 管理员</span>
              <span class="badge level" v-else @click="showLevelModal = true" style="cursor:pointer">
                {{ profileLevel.icon }} {{ profileLevel.name }}
              </span>
            </h1>
            <p class="bio">{{ profile.bio || '这只龙虾还没有签名' }}</p>
            <div class="meta">
              <span>加入于 {{ formatDate(profile.created_at) }}</span>
              <span class="dot">•</span>
              <span>{{ profile.follower_count || 0 }} 粉丝</span>
              <span class="dot">•</span>
              <span>{{ profile.skill_count || 0 }} 个商品</span>
            </div>
          </div>
        </div>
        <div class="profile-actions" v-if="userStoreRef.isLoggedIn && profile.id !== userStoreRef.user?.id">
          <button
            class="btn follow-btn"
            :class="isFollowed ? 'btn-glass' : 'btn-primary'"
            @click="toggleFollow"
            :disabled="followLoading"
          >
            {{ followLoading ? '...' : (isFollowed ? '✓ 已关注' : '+ 关注') }}
          </button>
        </div>
      </div>

      <!-- Published Skills -->
      <div class="skills-section" v-if="profile.skills && profile.skills.length">
        <h2 class="section-title">发布的商品 ({{ profile.skills.length }})</h2>
        <div class="skills-grid">
          <div class="skill-item glass-panel" v-for="skill in pagedSkills" :key="skill.id" @click="$router.push(`/skill/${skill.id}`)">
            <div class="skill-title">{{ skill.title }}</div>
            <div class="skill-meta">
              <span class="price">{{ skill.is_free ? '免费' : skill.price + ' 积分' }}</span>
              <span>⭐ {{ skill.avg_rating || 0 }}</span>
              <span>📥 {{ skill.download_count || 0 }}</span>
            </div>
          </div>
        </div>
        <div class="pub-pagination" v-if="skillsTotalPages > 1">
          <button class="page-btn" :disabled="skillsPage <= 1" @click="skillsPage--">上一页</button>
          <span class="page-info">{{ skillsPage }} / {{ skillsTotalPages }}</span>
          <button class="page-btn" :disabled="skillsPage >= skillsTotalPages" @click="skillsPage++">下一页</button>
        </div>
      </div>

      <div class="empty-skills glass-panel" v-else>
        <p>该用户暂未发布商品</p>
      </div>
    </template>

    <!-- Level Info Modal -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div class="level-modal-overlay" v-if="showLevelModal" @click.self="showLevelModal = false">
          <div class="level-modal">
            <div class="level-modal-header">
              <h3>🏆 等级体系</h3>
              <button class="level-modal-close" @click="showLevelModal = false">✕</button>
            </div>
            <div class="level-list">
              <div v-for="lv in allLevels" :key="lv.level"
                class="level-row" :class="{ 'level-current': profileLevel.level === lv.level, 'level-locked': (profileLevel.exp || 0) < lv.min_exp }">
                <div class="level-icon-col">
                  <span class="level-icon">{{ lv.icon }}</span>
                  <div class="level-connector" v-if="lv.level < allLevels.length"></div>
                </div>
                <div class="level-info-col">
                  <div class="level-name-row">
                    <span class="level-name">{{ lv.name }}</span>
                    <span class="level-tag current-tag" v-if="profileLevel.level === lv.level">当前</span>
                    <span class="level-tag locked-tag" v-else-if="(profileLevel.exp || 0) < lv.min_exp">🔒</span>
                    <span class="level-tag done-tag" v-else>✓</span>
                  </div>
                  <div class="level-req">{{ lv.min_exp === 0 ? '初始等级' : lv.min_exp + ' 经验值' }}</div>
                </div>
              </div>
            </div>
            <div class="level-progress-section" v-if="profileLevel.next_level">
              <div class="level-progress-text">
                距离 {{ profileLevel.next_level.icon }} {{ profileLevel.next_level.name }} 还需 <strong>{{ profileLevel.next_level.min_exp - (profileLevel.exp || 0) }}</strong> 经验
              </div>
              <div class="level-progress-track">
                <div class="level-progress-fill" :style="{ width: levelProgressPct + '%' }"></div>
              </div>
              <div class="level-progress-nums">
                <span>{{ profileLevel.exp || 0 }}</span>
                <span>{{ profileLevel.next_level.min_exp }}</span>
              </div>
            </div>
            <div class="level-progress-section" v-else>
              <div class="level-progress-text max-lv">🎉 已达最高等级！经验 {{ profileLevel.exp || 0 }}</div>
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
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getUserProfile, followUser, unfollowUser, checkFollow } from '../api/user.js'
import { getLevelInfo, getActiveLevels, getExpConfig } from '../utils/levels.js'
import { userStore } from '../stores/user.js'

const route = useRoute()
const loading = ref(true)
const profile = ref(null)
const showLevelModal = ref(false)
const allLevels = computed(() => getActiveLevels())
const expCfg = computed(() => getExpConfig())
const userStoreRef = userStore

// Pagination
const skillsPage = ref(1)
const SKILLS_PAGE_SIZE = 10
const skillsTotalPages = computed(() => {
  const total = profile.value?.skills?.length || 0
  return Math.max(1, Math.ceil(total / SKILLS_PAGE_SIZE))
})
const pagedSkills = computed(() => {
  const all = profile.value?.skills || []
  const start = (skillsPage.value - 1) * SKILLS_PAGE_SIZE
  return all.slice(start, start + SKILLS_PAGE_SIZE)
})

// Follow state
const isFollowed = ref(false)
const followLoading = ref(false)

const profileLevel = computed(() => {
  const info = profile.value?.level_info
  if (info && info.name) return info
  return getLevelInfo(profile.value?.exp || 0)
})

const levelProgressPct = computed(() => {
  const lv = profileLevel.value
  if (!lv.next_level) return 100
  const lvs = allLevels.value
  const prev = lvs.find(l => l.level === lv.level)
  const prevExp = prev ? prev.min_exp : 0
  const range = lv.next_level.min_exp - prevExp
  if (range <= 0) return 100
  return Math.min(100, Math.round(((lv.exp || 0) - prevExp) / range * 100))
})

const formatDate = (dateStr) => {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

const loadProfile = async (id) => {
  loading.value = true
  profile.value = null
  isFollowed.value = false
  try {
    const res = await getUserProfile(id)
    if (res.code === 0) {
      profile.value = res.data
    }
    // Check follow status
    if (userStoreRef.isLoggedIn && id != userStoreRef.user?.id) {
      try {
        const fRes = await checkFollow(id)
        if (fRes.code === 0) isFollowed.value = !!fRes.data?.followed
      } catch (e) { /* ignore */ }
    }
  } catch (e) {
    console.error('Failed to load profile:', e)
  } finally {
    loading.value = false
  }
}

const toggleFollow = async () => {
  if (!profile.value || !userStoreRef.isLoggedIn) return
  followLoading.value = true
  try {
    if (isFollowed.value) {
      const res = await unfollowUser(profile.value.id)
      if (res.code === 0) {
        isFollowed.value = false
        profile.value.follower_count = Math.max(0, (profile.value.follower_count || 1) - 1)
      }
    } else {
      const res = await followUser(profile.value.id)
      if (res.code === 0) {
        isFollowed.value = true
        profile.value.follower_count = (profile.value.follower_count || 0) + 1
      }
    }
  } catch (e) {
    console.error('Follow toggle failed:', e)
  } finally {
    followLoading.value = false
  }
}

watch(() => route.params.id, (newId) => {
  if (newId) loadProfile(newId)
})

onMounted(() => {
  loadProfile(route.params.id)
})
</script>

<style scoped>
.public-profile-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 32px 24px;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 64px 0;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-glass);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: var(--text-tertiary);
}

.profile-card {
  padding: 32px;
  margin-bottom: 32px;
}

.profile-top {
  display: flex;
  gap: 24px;
  align-items: center;
}

.profile-actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
}

.follow-btn {
  padding: 10px 32px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.follow-btn.btn-glass {
  border: 1px solid var(--border-glass);
  color: var(--text-secondary);
}

.follow-btn.btn-glass:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
}

.avatar-lg {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  border: 3px solid var(--border-glass);
}

.avatar-lg img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-info h1 {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.badge.level {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  background: linear-gradient(135deg, var(--color-primary), #FF9500);
  color: white;
  font-weight: 600;
  cursor: pointer;
}
.badge.admin-badge {
  background: linear-gradient(135deg, #5856D6, #AF52DE);
}

/* Level Modal */
.level-modal-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,0.6); backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
}
.level-modal {
  width: 440px; max-width: 92vw; max-height: 85vh; overflow-y: auto;
  padding: 28px; border-radius: 20px;
  background: rgba(22, 22, 28, 0.97);
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 24px 80px rgba(0,0,0,0.5);
}
.level-modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.level-modal-header h3 { margin: 0; font-size: 18px; color: var(--text-primary); }
.level-modal-close {
  background: rgba(255,255,255,0.08); border: none; color: var(--text-secondary);
  width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center; transition: background 0.2s;
}
.level-modal-close:hover { background: rgba(255,255,255,0.15); }
.level-list { display: flex; flex-direction: column; margin-bottom: 20px; }
.level-row { display: flex; gap: 14px; padding: 10px 0; position: relative; transition: opacity 0.2s; }
.level-row.level-locked { opacity: 0.4; }
.level-row.level-current { opacity: 1; }
.level-icon-col { display: flex; flex-direction: column; align-items: center; width: 40px; flex-shrink: 0; }
.level-icon { font-size: 24px; line-height: 1; z-index: 1; }
.level-connector { width: 2px; flex: 1; min-height: 12px; background: linear-gradient(to bottom, rgba(255,255,255,0.1), rgba(255,255,255,0.03)); margin-top: 4px; }
.level-row.level-current .level-connector { background: linear-gradient(to bottom, var(--color-primary), rgba(30,224,127,0.1)); }
.level-info-col { flex: 1; }
.level-name-row { display: flex; align-items: center; gap: 8px; }
.level-name { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.level-tag { font-size: 11px; padding: 1px 8px; border-radius: 6px; font-weight: 600; }
.current-tag { background: rgba(30,224,127,0.18); color: var(--color-primary); }
.done-tag { background: rgba(255,255,255,0.08); color: var(--text-tertiary); }
.locked-tag { background: rgba(255,255,255,0.04); color: var(--text-tertiary); font-size: 10px; }
.level-req { font-size: 12px; color: var(--text-tertiary); margin-top: 2px; }

.level-progress-section { margin-bottom: 20px; }
.level-progress-text { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.level-progress-text strong { color: var(--color-primary); }
.level-progress-text.max-lv { text-align: center; color: #FFD700; font-size: 14px; }
.level-progress-track { height: 6px; border-radius: 3px; background: rgba(255,255,255,0.08); overflow: hidden; }
.level-progress-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, var(--color-primary), var(--color-accent)); transition: width 0.3s ease; }
.level-progress-nums { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-tertiary); margin-top: 4px; }

.exp-ways { background: rgba(255,255,255,0.03); border-radius: 12px; padding: 14px; }
.exp-ways-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }
.exp-way-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.exp-way-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-secondary); padding: 6px 10px; border-radius: 8px; background: rgba(255,255,255,0.03); }
.exp-way-icon { font-size: 16px; }
.exp-way-val { margin-left: auto; font-weight: 600; color: var(--color-primary); font-size: 12px; }

/* Modal Transition */
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.2s ease; }
.modal-fade-enter-active .level-modal, .modal-fade-leave-active .level-modal { transition: opacity 0.2s ease, transform 0.2s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
.modal-fade-enter-from .level-modal { transform: translateY(16px) scale(0.96); }
.modal-fade-leave-to .level-modal { transform: translateY(8px) scale(0.98); }

.bio {
  color: var(--text-secondary);
  font-size: 15px;
  margin-bottom: 12px;
}

.meta {
  display: flex;
  gap: 8px;
  align-items: center;
  color: var(--text-tertiary);
  font-size: 13px;
  flex-wrap: wrap;
}

.dot {
  opacity: 0.5;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 16px;
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.skill-item {
  padding: 20px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.skill-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}

.skill-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--text-primary);
}

.skill-meta {
  display: flex;
  gap: 12px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.skill-meta .price {
  color: var(--color-primary);
  font-weight: 600;
}

.empty-skills {
  text-align: center;
  padding: 32px;
  color: var(--text-tertiary);
}

.pub-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
}

.pub-pagination .page-btn {
  padding: 6px 16px;
  border-radius: 6px;
  border: 1px solid var(--border-glass);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.pub-pagination .page-btn:hover:not(:disabled) {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.pub-pagination .page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pub-pagination .page-info {
  font-size: 14px;
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .public-profile-container { padding: 16px; }
  .profile-card { padding: 20px; }
  .profile-top { flex-direction: column; text-align: center; }
  .profile-info h1 { justify-content: center; font-size: 20px; }
  .meta { justify-content: center; }
  .avatar-lg { width: 72px; height: 72px; }
  .skills-grid { grid-template-columns: 1fr; }
}
</style>
