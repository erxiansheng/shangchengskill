<template>
  <div class="favorites-container container">
    <div class="page-header">
      <h1 class="page-title">我的收藏</h1>
      <p class="page-subtitle">您关注的所有商品都在这里。</p>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="favorites.length === 0" class="empty-state glass-panel">
      <p>您还没有收藏任何商品</p>
      <button class="btn btn-primary" style="margin-top: 16px;" @click="$router.push('/explore')">去探索市场</button>
    </div>

    <template v-else>
      <div class="skills-grid">
        <SkillCard
          v-for="skill in favorites"
          :key="skill.id"
          :skill="skill"
          @click="$router.push(`/skill/${skill.skill_id || skill.id}`)"
        />
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
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SkillCard from '../components/SkillCard.vue'
import { getFavorites } from '../api/social.js'
import { userStore } from '../stores/user.js'

const router = useRouter()
const route = useRoute()
const favorites = ref([])
const loading = ref(true)
const page = ref(1)
const totalPages = ref(1)
const PAGE_SIZE = 10

const loadData = async () => {
  loading.value = true
  try {
    const res = await getFavorites({ page: page.value, page_size: PAGE_SIZE })
    if (res.code === 0) {
      favorites.value = res.data?.items || []
      totalPages.value = res.data?.total_pages || 1
    }
  } catch (e) {
    console.error('Failed to load favorites:', e)
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

onMounted(() => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  page.value = parseInt(route.query.page) || 1
  loadData()
})
</script>

<style scoped>
.favorites-container { padding: 40px 24px 100px; max-width: 1280px; }
.page-header { margin-bottom: 32px; }
.page-title { font-size: 32px; font-weight: 800; margin-bottom: 8px; }
.page-subtitle { color: var(--text-secondary); }
.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

.loading-state, .empty-state { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
.loading-spinner {
  width: 40px; height: 40px; border: 3px solid var(--border-glass);
  border-top-color: var(--color-primary); border-radius: 50%;
  animation: spin 0.8s linear infinite; margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }

.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 32px; }
.page-btn {
  background: var(--bg-glass); border: 1px solid var(--border-glass); color: var(--text-primary);
  padding: 8px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; transition: var(--transition-smooth);
}
.page-btn:hover:not(:disabled) { background: var(--bg-surface-hover); border-color: var(--color-primary); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: 14px; color: var(--text-secondary); }

@media (max-width: 600px) {
  .favorites-container { padding: 20px 12px 60px; }
  .page-title { font-size: 24px; }
  .skills-grid { grid-template-columns: 1fr; gap: 16px; }
}
</style>
