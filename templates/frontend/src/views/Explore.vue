<template>
  <div class="explore-container container">
    <div class="page-header">
      <h1 class="page-title">探索所有商品</h1>
      <p class="page-subtitle">浏览 EdgeOneMall 市场中所有的顶尖AI商品，找到属于你的生产力核武器。</p>
    </div>

    <!-- Mobile filter toggle button -->
    <button class="mobile-filter-btn" @click="showMobileFilter = true">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="6" x2="20" y2="6"/><line x1="8" y1="12" x2="20" y2="12"/><line x1="12" y1="18" x2="20" y2="18"/><circle cx="5" cy="12" r="1.5" fill="currentColor"/><circle cx="9" cy="18" r="1.5" fill="currentColor"/></svg>
      筛选
      <span class="filter-count" v-if="activeFilterCount">{{ activeFilterCount }}</span>
    </button>

    <!-- Mobile filter drawer overlay -->
    <Teleport to="body">
      <Transition name="drawer">
        <div v-if="showMobileFilter" class="filter-drawer-overlay" @click.self="showMobileFilter = false">
          <div class="filter-drawer">
            <div class="filter-drawer-header">
              <h3>筛选条件</h3>
              <button class="filter-drawer-close" @click="showMobileFilter = false">✕</button>
            </div>
            <div class="filter-drawer-body">
              <div class="filter-group">
                <h3>分类</h3>
                <ul class="filter-list">
                  <li :class="{ active: !filters.category_id }" @click="setCategory(null); showMobileFilter = false">全部内容</li>
                  <li v-for="cat in categories" :key="cat.id" :class="{ active: filters.category_id === cat.id }" @click="setCategory(cat.id); showMobileFilter = false">{{ cat.icon }} {{ cat.name }}</li>
                </ul>
              </div>
              <div class="filter-group">
                <h3>星级</h3>
                <ul class="filter-list">
                  <li :class="{ active: !filters.min_rating }" @click="setRating(null); showMobileFilter = false">全部星级</li>
                  <li :class="{ active: filters.min_rating === 5 }" @click="setRating(5); showMobileFilter = false">⭐⭐⭐⭐⭐ 平台精选</li>
                  <li :class="{ active: filters.min_rating === 4 }" @click="setRating(4); showMobileFilter = false">⭐⭐⭐⭐ 评分精选</li>
                </ul>
              </div>
              <div class="filter-group">
                <h3>价格区间</h3>
                <ul class="filter-list">
                  <li :class="{ active: !filters.is_free && !filters.price_max }" @click="setPriceRange(null); showMobileFilter = false">不限</li>
                  <li :class="{ active: filters.is_free === true }" @click="setPriceRange('free'); showMobileFilter = false">免费商品</li>
                  <li :class="{ active: filters.price_min === 1 && filters.price_max === 100 }" @click="setPriceRange('low'); showMobileFilter = false">< 100 积分</li>
                  <li :class="{ active: filters.price_min === 100 && filters.price_max === 500 }" @click="setPriceRange('mid'); showMobileFilter = false">100 - 500 积分</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <div class="explore-layout">
      <!-- Left Sidebar Filters (desktop only) -->
      <aside class="filter-sidebar glass-panel">
        <div class="filter-group">
          <h3>分类</h3>
          <ul class="filter-list">
            <li :class="{ active: !filters.category_id }" @click="setCategory(null)">全部内容</li>
            <li
              v-for="cat in categories"
              :key="cat.id"
              :class="{ active: filters.category_id === cat.id }"
              @click="setCategory(cat.id)"
            >{{ cat.icon }} {{ cat.name }}</li>
          </ul>
        </div>

        <div class="filter-group">
          <h3>星级</h3>
          <ul class="filter-list">
            <li :class="{ active: !filters.min_rating }" @click="setRating(null)">全部星级</li>
            <li :class="{ active: filters.min_rating === 5 }" @click="setRating(5)">⭐⭐⭐⭐⭐ 平台精选</li>
            <li :class="{ active: filters.min_rating === 4 }" @click="setRating(4)">⭐⭐⭐⭐ 评分精选</li>
          </ul>
        </div>

        <div class="filter-group">
          <h3>价格区间</h3>
          <ul class="filter-list">
            <li :class="{ active: !filters.is_free && !filters.price_max }" @click="setPriceRange(null)">不限</li>
            <li :class="{ active: filters.is_free === true }" @click="setPriceRange('free')">免费商品</li>
            <li :class="{ active: filters.price_min === 1 && filters.price_max === 100 }" @click="setPriceRange('low')">&lt; 100 积分</li>
            <li :class="{ active: filters.price_min === 100 && filters.price_max === 500 }" @click="setPriceRange('mid')">100 - 500 积分</li>
          </ul>
        </div>
      </aside>

      <!-- Right Main Content -->
      <main class="explore-main">
        <div class="filter-bar glass-panel">
          <div class="search-wrap">
            <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input
              type="text"
              placeholder="搜索商品名称、描述或作者..."
              class="filter-input"
              v-model="filters.keyword"
              @keyup.enter="loadSkills(1)"
            />
          </div>

          <div class="sort-actions">
            <span class="sort-item" :class="{ active: filters.sort === 'newest' }" @click="setSort('newest')">最新上架</span>
            <span class="sort-item" :class="{ active: filters.sort === 'hot' }" @click="setSort('hot')">综合排序</span>
            <span class="sort-item" :class="{ active: filters.sort === 'rating' }" @click="setSort('rating')">最高评分</span>
          </div>
        </div>

        <div v-if="loading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>加载中...</p>
        </div>

        <div v-else-if="skills.length === 0" class="empty-state">
          <p>没有找到匹配的商品</p>
        </div>

        <div v-else class="skills-grid">
          <SkillCard
            v-for="skill in skills"
            :key="skill.id"
            :skill="skill"
            @click="$router.push(`/skill/${skill.id}`)"
          />
        </div>

        <!-- Pagination -->
        <div class="pagination" v-if="totalPages > 1">
          <button class="page-btn" :disabled="currentPage <= 1" @click="loadSkills(currentPage - 1)">&larr;</button>
          <button
            v-for="p in displayPages"
            :key="p"
            class="page-btn"
            :class="{ active: p === currentPage, dots: p === '...' }"
            :disabled="p === '...'"
            @click="p !== '...' && loadSkills(p)"
          >{{ p }}</button>
          <button class="page-btn" :disabled="currentPage >= totalPages" @click="loadSkills(currentPage + 1)">&rarr;</button>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SkillCard from '../components/SkillCard.vue'
import { getSkills, getCategories } from '../api/skill.js'

const route = useRoute()
const router = useRouter()

const skills = ref([])
const categories = ref([])
const loading = ref(true)
const currentPage = ref(1)
const totalPages = ref(1)
const total = ref(0)
const showMobileFilter = ref(false)

const filters = reactive({
  keyword: route.query.keyword || '',
  category_id: null,
  sort: 'hot',
  is_free: null,
  price_min: null,
  price_max: null,
  min_rating: null
})

const displayPages = computed(() => {
  const pages = []
  const tp = totalPages.value
  const cp = currentPage.value

  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (cp > 3) pages.push('...')
    const start = Math.max(2, cp - 1)
    const end = Math.min(tp - 1, cp + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (cp < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
})

const activeFilterCount = computed(() => {
  let count = 0
  if (filters.category_id) count++
  if (filters.min_rating) count++
  if (filters.is_free || filters.price_max) count++
  return count
})

const setCategory = (id) => {
  filters.category_id = id
  loadSkills(1)
}

const setRating = (rating) => {
  filters.min_rating = rating
  loadSkills(1)
}

const setPriceRange = (range) => {
  filters.is_free = null
  filters.price_min = null
  filters.price_max = null
  if (range === 'free') filters.is_free = true
  else if (range === 'low') { filters.price_min = 1; filters.price_max = 100 }
  else if (range === 'mid') { filters.price_min = 100; filters.price_max = 500 }
  loadSkills(1)
}

const setSort = (sort) => {
  filters.sort = sort
  loadSkills(1)
}

const loadSkills = async (page = 1) => {
  loading.value = true
  currentPage.value = page
  router.replace({ query: { ...route.query, page: page > 1 ? page : undefined } })
  try {
    const params = {
      page,
      page_size: 9,
      sort: filters.sort,
      keyword: filters.keyword || undefined,
      category_id: filters.category_id || undefined,
      is_free: filters.is_free ?? undefined,
      price_min: filters.price_min ?? undefined,
      price_max: filters.price_max ?? undefined,
      min_rating: filters.min_rating ?? undefined,
    }
    const res = await getSkills(params)
    if (res.code === 0) {
      skills.value = res.data?.items || []
      total.value = res.data?.total || 0
      totalPages.value = res.data?.total_pages || 1
    }
  } catch (e) {
    console.error('Failed to load skills:', e)
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    const res = await getCategories()
    if (res.code === 0) {
      categories.value = res.data?.categories || res.data?.items || []
    }
  } catch (e) {
    console.error('Failed to load categories:', e)
  }
}

onMounted(() => {
  loadCategories()
  const initPage = parseInt(route.query.page) || 1
  loadSkills(initPage)
})
</script>

<style scoped>
.explore-container {
  padding: 40px 24px 100px;
  max-width: 1360px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 36px;
  font-weight: 800;
  margin-bottom: 8px;
}

.page-subtitle {
  color: var(--text-secondary);
}

.explore-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 32px;
  align-items: start;
}

/* Sidebar */
.filter-sidebar {
  padding: 24px;
}

.filter-group {
  margin-bottom: 32px;
}
.filter-group:last-child {
  margin-bottom: 0;
}

.filter-group h3 {
  font-size: 14px;
  color: var(--text-tertiary);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.filter-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.filter-list li {
  padding: 10px 16px;
  font-size: 14px;
  color: var(--text-secondary);
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: var(--transition-smooth);
}

.filter-list li:hover {
  background: rgba(255,255,255,0.05);
  color: var(--text-primary);
}

.filter-list li.active {
  background: var(--color-primary);
  color: #000;
  font-weight: 600;
}

/* Main */
.explore-main {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-radius: 12px;
  flex-wrap: wrap;
  gap: 16px;
}

.search-wrap {
  position: relative;
  width: 320px;
}

.search-wrap .search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-tertiary);
  pointer-events: none;
  transition: color 0.2s;
}

.search-wrap:focus-within .search-icon {
  color: var(--color-primary);
}

.filter-input {
  width: 100%;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 99px;
  padding: 11px 16px 11px 42px;
  color: var(--text-primary);
  outline: none;
  font-family: inherit;
  font-size: 14px;
  transition: var(--transition-smooth);
  backdrop-filter: blur(8px);
}

.filter-input::placeholder {
  color: var(--text-tertiary);
}

.filter-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-glow);
  background: var(--bg-surface);
}

.sort-actions {
  display: flex;
  gap: 20px;
  font-size: 14px;
}

.sort-item {
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-smooth);
  font-weight: 500;
}

.sort-item:hover {
  color: var(--text-primary);
}

.sort-item.active {
  color: var(--color-primary);
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

/* Loading & Empty */
.loading-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-glass);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 40px;
}

.page-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-surface);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: var(--font-display);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  background: rgba(30, 224, 127, 0.1);
  color: var(--color-primary);
}

.page-btn.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #000;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-btn.dots {
  border: none;
  background: transparent;
  cursor: default;
  color: var(--text-secondary);
}

/* Mobile Filter Button */
.mobile-filter-btn {
  display: none;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border-glass);
  border-radius: 99px;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 16px;
  transition: var(--transition-smooth);
}

.mobile-filter-btn:hover {
  border-color: var(--color-primary);
  background: rgba(30, 224, 127, 0.08);
}

.mobile-filter-btn svg {
  flex-shrink: 0;
}

.filter-count {
  background: var(--color-primary);
  color: #000;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 99px;
  min-width: 18px;
  text-align: center;
}

/* Filter Drawer (mobile) */
.filter-drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.filter-drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 300px;
  max-width: 85vw;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-glass);
  display: flex;
  flex-direction: column;
  z-index: 1001;
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.4);
}

.filter-drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-glass);
}

.filter-drawer-header h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.filter-drawer-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.filter-drawer-close:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.filter-drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}

.filter-drawer-body .filter-group {
  margin-bottom: 28px;
}

.filter-drawer-body .filter-group:last-child {
  margin-bottom: 0;
}

.filter-drawer-body .filter-group h3 {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.filter-drawer-body .filter-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.filter-drawer-body .filter-list li {
  padding: 10px 16px;
  font-size: 14px;
  color: var(--text-secondary);
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: var(--transition-smooth);
}

.filter-drawer-body .filter-list li:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.filter-drawer-body .filter-list li.active {
  background: var(--color-primary);
  color: #000;
  font-weight: 600;
}

/* Drawer transition */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.25s ease;
}

.drawer-enter-active .filter-drawer,
.drawer-leave-active .filter-drawer {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .filter-drawer,
.drawer-leave-to .filter-drawer {
  transform: translateX(100%);
}

@media (max-width: 992px) {
  .explore-layout {
    grid-template-columns: 1fr;
  }
  .filter-sidebar {
    display: none;
  }
  .mobile-filter-btn {
    display: inline-flex;
  }
}

@media (max-width: 600px) {
  .skills-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .search-wrap {
    width: 100%;
  }
  .toolbar {
    padding: 12px 16px;
    gap: 12px;
  }
  .sort-actions {
    gap: 14px;
    font-size: 13px;
  }
}
</style>
