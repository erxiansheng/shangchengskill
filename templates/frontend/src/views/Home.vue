<template>
  <div class="home-container">
    <!-- ============ Hero Section ============ -->
    <section class="hero">
      <div class="hero-left glass-panel">
        <Logo3D class="hero-3d" />
        <div class="hero-content">
          <div class="hero-badge">
            <span class="badge-dot"></span>
            <span>EdgeOne Mall · 全球极速电商</span>
          </div>
          <h1 class="hero-title">
            <span class="title-line glitch-hover" data-text="发现好物">发现好物</span>
            <span class="title-line"><span class="primary-gradient glitch-hover" data-text="闪电直达">闪电直达</span></span>
          </h1>
          <p class="hero-subtitle">
            千款臻选商品 · 全球边缘加速 · 积分 / 现金双支付
          </p>
          <div class="hero-actions">
            <button class="btn btn-primary btn-lg" @click="$router.push('/explore')">
              立即逛逛 <span class="btn-arrow">→</span>
            </button>
            <button class="btn btn-glass btn-lg" @click="scrollToFlash">
              限时秒杀
            </button>
          </div>
          <div class="hero-stats">
            <div class="stat-item"><div class="stat-num">{{ formatCount(stats.products) }}+</div><div class="stat-label">在售商品</div></div>
            <div class="stat-divider"></div>
            <div class="stat-item"><div class="stat-num">{{ formatCount(stats.users) }}+</div><div class="stat-label">活跃用户</div></div>
            <div class="stat-divider"></div>
            <div class="stat-item"><div class="stat-num">99.9%</div><div class="stat-label">服务可用</div></div>
          </div>

          <!-- 服务承诺标签条（移植自 skilljiaoyi 的 hero-platforms） -->
          <div class="hero-tags">
            <span class="hero-tags-label">SERVICE PROMISE</span>
            <div class="hero-tags-list">
              <span class="hero-tag" v-for="t in promiseTags" :key="t.name">
                <span class="hero-tag-icon" v-html="t.icon"></span>{{ t.name }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 轮播 Banner -->
      <div class="hero-right">
        <div class="banner-carousel glass-panel">
          <div
            v-for="(b, i) in banners"
            :key="i"
            class="banner-slide"
            :class="{ active: activeBanner === i }"
            :style="{ background: b.bg }"
          >
            <div class="banner-content">
              <span class="banner-tag">{{ b.tag }}</span>
              <h3 class="banner-title">{{ b.title }}</h3>
              <p class="banner-desc">{{ b.desc }}</p>
              <button class="btn btn-primary btn-sm" @click="$router.push(b.link)">{{ b.cta }} →</button>
            </div>
            <div class="banner-emoji">{{ b.emoji }}</div>
          </div>
          <div class="banner-dots">
            <span
              v-for="(b, i) in banners"
              :key="i"
              class="dot"
              :class="{ active: activeBanner === i }"
              @click="activeBanner = i"
            ></span>
          </div>
        </div>

        <!-- 服务保障 -->
        <div class="promise-strip">
          <div class="promise-item" v-for="p in promises" :key="p.title">
            <span class="promise-icon">{{ p.icon }}</span>
            <div>
              <div class="promise-title">{{ p.title }}</div>
              <div class="promise-desc">{{ p.desc }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ Flash Sale (紧跟 Hero，对齐 skilljiaoyi 教程位) ============ -->
    <section ref="flashEl" class="flash-section">
      <div class="flash-header glass-panel">
        <div class="flash-title-wrap">
          <span class="flash-icon">⚡</span>
          <h2 class="flash-title">限时秒杀</h2>
          <span class="flash-sub">每日 0 点更新</span>
        </div>
        <div class="flash-timer">
          <span class="timer-label">距结束</span>
          <div class="timer-block">{{ countdown.h }}</div>
          <span class="timer-sep">:</span>
          <div class="timer-block">{{ countdown.m }}</div>
          <span class="timer-sep">:</span>
          <div class="timer-block">{{ countdown.s }}</div>
        </div>
      </div>

      <div v-if="flashSkills.length === 0" class="flash-grid">
        <div v-for="i in 4" :key="'fs-' + i" class="flash-card skel-card"></div>
      </div>
      <div v-else class="flash-grid">
        <div
          v-for="item in flashSkills.slice(0, 4)"
          :key="item.id"
          class="flash-card"
          @click="$router.push(`/skill/${item.id}`)"
        >
          <div class="flash-cover">
            <span class="flash-cover-emoji">{{ pickEmoji(item.id) }}</span>
            <span class="flash-discount">-{{ randomDiscount(item.id) }}%</span>
          </div>
          <div class="flash-body">
            <div class="flash-name">{{ item.title }}</div>
            <div class="flash-price-row">
              <span class="flash-price">¥{{ flashPrice(item) }}</span>
              <span class="flash-original">¥{{ originalPrice(item) }}</span>
            </div>
            <div class="flash-bar">
              <div class="flash-bar-fill" :style="{ width: stockPercent(item.id) + '%' }"></div>
              <span class="flash-bar-label">剩余 {{ 100 - stockPercent(item.id) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ Category Quick Nav ============ -->
    <section class="category-section">
      <div class="section-header">
        <h2 class="section-title">全部分类</h2>
        <a class="section-link" @click="$router.push('/explore')">查看全部 →</a>
      </div>
      <div class="category-grid">
        <div class="cat-tile" @click="goExplore(null)">
          <div class="cat-icon-wrap"><span class="cat-icon">🔥</span></div>
          <div class="cat-name">热门</div>
        </div>
        <div
          v-for="cat in categories.slice(0, 11)"
          :key="cat.id"
          class="cat-tile"
          @click="goExplore(cat.id)"
        >
          <div class="cat-icon-wrap"><span class="cat-icon">{{ cat.icon || '🛍️' }}</span></div>
          <div class="cat-name">{{ cat.name }}</div>
        </div>
      </div>
    </section>

    <!-- ============ New Arrivals ============ -->
    <section class="arrivals-section">
      <div class="section-header">
        <h2 class="section-title">新品上架</h2>
        <a class="section-link" @click="$router.push('/explore?sort=new')">查看更多 →</a>
      </div>
      <div class="arrivals-scroll">
        <template v-if="newSkills.length === 0">
          <div v-for="i in 6" :key="'n-' + i" class="arrival-card skel-card"></div>
        </template>
        <template v-else>
          <div
            v-for="item in newSkills"
            :key="item.id"
            class="arrival-card"
            @click="$router.push(`/skill/${item.id}`)"
          >
            <div class="arrival-cover">
              <span class="arrival-emoji">{{ pickEmoji(item.id) }}</span>
              <span class="arrival-tag-new">NEW</span>
            </div>
            <div class="arrival-name">{{ item.title }}</div>
            <div class="arrival-price">
              <span v-if="item.price === 0 || item.is_free" class="free">免费</span>
              <span v-else>¥{{ item.price }}</span>
            </div>
          </div>
        </template>
      </div>
    </section>

    <!-- ============ Recommended Grid ============ -->
    <section id="market" class="recommend-section">
      <div class="section-header">
        <h2 class="section-title">为你推荐</h2>
        <div class="cat-pills">
          <span
            class="pill"
            :class="{ active: activeCategory === null }"
            @click="activeCategory = null; loadSkills()"
          >全部</span>
          <span
            v-for="cat in categories.slice(0, 6)"
            :key="cat.id"
            class="pill"
            :class="{ active: activeCategory === cat.id }"
            @click="activeCategory = cat.id; loadSkills()"
          >{{ cat.name }}</span>
        </div>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>
      <div v-else-if="skills.length === 0" class="empty-state">
        <p>暂无商品，去发布第一件吧！</p>
      </div>
      <div v-else class="skills-grid">
        <SkillCard
          v-for="skill in skills"
          :key="skill.id"
          :skill="skill"
          @click="$router.push(`/skill/${skill.id}`)"
        />
      </div>
      <div class="see-all-row">
        <button class="btn btn-glass btn-lg" @click="$router.push('/explore')">查看全部商品 →</button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import SkillCard from '../components/SkillCard.vue'
import Logo3D from '../components/Logo3D.vue'
import { getSkills, getCategories } from '../api/skill.js'

const skills = ref([])
const newSkills = ref([])
const flashSkills = ref([])
const categories = ref([])
const activeCategory = ref(null)
const loading = ref(true)
const activeBanner = ref(0)
const flashEl = ref(null)

const stats = reactive({ products: 1280, users: 36500 })

const banners = [
  { tag: '新品首发', title: '夏日新品 · 6.18 大促', desc: '满 199 减 30，限时 3 天', emoji: '🛍️', cta: '立即抢购', link: '/explore?sort=new', bg: 'linear-gradient(135deg, rgba(30,224,127,0.18), rgba(0,240,255,0.10))' },
  { tag: '会员专享', title: '积分商城 · 0 元兑好物', desc: '签到领积分，每日一份惊喜', emoji: '🎁', cta: '查看详情', link: '/points', bg: 'linear-gradient(135deg, rgba(0,240,255,0.18), rgba(30,224,127,0.10))' },
  { tag: '商家入驻', title: '一键上架 · 全球分发', desc: 'EdgeOne 边缘网络全球加速', emoji: '🚀', cta: '去发布', link: '/upload', bg: 'linear-gradient(135deg, rgba(255,184,0,0.16), rgba(255,71,87,0.10))' },
]

const promises = [
  { icon: '✅', title: '正品保障', desc: '官方授权' },
  { icon: '⚡', title: '闪电发货', desc: '边缘加速' },
  { icon: '🔄', title: '七天退换', desc: '无忧购物' },
  { icon: '💬', title: '24h 客服', desc: '在线响应' },
]

// Hero 标签条（移植自 skilljiaoyi 的 hero-platforms）——使用内联 SVG 代替 emoji，更精致
const svg = (path) => `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`
const promiseTags = [
  { icon: svg('<path d="M12 2 4 5v6c0 5 3.5 9.5 8 11 4.5-1.5 8-6 8-11V5l-8-3z"/><path d="m9 12 2 2 4-4"/>'), name: '正品保障' },
  { icon: svg('<polyline points="13 2 4 14 12 14 11 22 20 10 12 10 13 2"/>'), name: '极速发货' },
  { icon: svg('<rect x="1" y="6" width="15" height="12" rx="2"/><path d="M16 10h4l3 4v4h-7z"/><circle cx="6" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>'), name: '全国包邮' },
  { icon: svg('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><polyline points="3 3 3 8 8 8"/>'), name: '七天退换' },
  { icon: svg('<polygon points="12 2 2 9 6 22 18 22 22 9 12 2"/><line x1="12" y1="2" x2="6" y2="9"/><line x1="12" y1="2" x2="18" y2="9"/><line x1="2" y1="9" x2="22" y2="9"/><line x1="6" y1="9" x2="12" y2="22"/><line x1="18" y1="9" x2="12" y2="22"/>'), name: '会员折扣' },
  { icon: svg('<polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7zM12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>'), name: '积分兑换' },
  { icon: svg('<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>'), name: '24h 客服' },
  { icon: svg('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'), name: '安全支付' },
]

const countdown = reactive({ h: '00', m: '00', s: '00' })
let countdownTimer = null
const updateCountdown = () => {
  const now = new Date()
  const end = new Date(now)
  end.setHours(24, 0, 0, 0)
  const diff = Math.max(0, Math.floor((end - now) / 1000))
  const h = Math.floor(diff / 3600)
  const m = Math.floor((diff % 3600) / 60)
  const s = diff % 60
  countdown.h = String(h).padStart(2, '0')
  countdown.m = String(m).padStart(2, '0')
  countdown.s = String(s).padStart(2, '0')
}

let bannerTimer = null
const startBannerLoop = () => {
  bannerTimer = setInterval(() => {
    activeBanner.value = (activeBanner.value + 1) % banners.length
  }, 5000)
}

const formatCount = (n) => {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

// 基于 id 的稳定伪随机，让秒杀折扣 / 进度等数值在不同渲染保持一致
const seed = (id) => {
  const s = String(id || '0')
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h
}
const randomDiscount = (id) => 20 + (seed(id) % 50)
const stockPercent = (id) => 30 + (seed(id) % 60)
const flashPrice = (item) => {
  const p = Number(item.price) || 99
  return Math.max(1, Math.round(p * (1 - randomDiscount(item.id) / 100)))
}
const originalPrice = (item) => Number(item.price) || 99

const emojiPool = ['🛍️', '🎧', '👕', '⌚', '📱', '💄', '🎮', '🍵', '🧴', '👟', '🪞', '🕯️']
const pickEmoji = (id) => emojiPool[seed(id) % emojiPool.length]

const goExplore = (catId) => {
  if (catId) {
    window.location.href = `/explore?category_id=${catId}`
  } else {
    window.location.href = '/explore'
  }
}

const scrollToFlash = () => {
  flashEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const loadSkills = async () => {
  loading.value = true
  try {
    const params = { page: 1, page_size: 8, sort: 'hot' }
    if (activeCategory.value) params.category_id = activeCategory.value
    const res = await getSkills(params)
    if (res.code === 0) skills.value = res.data?.items || []
  } catch (e) {
    console.error('Failed to load skills:', e)
  } finally {
    loading.value = false
  }
}

const loadHomeData = async () => {
  try {
    const [hotRes, newRes] = await Promise.all([
      getSkills({ page: 1, page_size: 4, sort: 'hot' }),
      getSkills({ page: 1, page_size: 8, sort: 'new' }),
    ])
    if (hotRes.code === 0) flashSkills.value = hotRes.data?.items || []
    if (newRes.code === 0) newSkills.value = newRes.data?.items || []
  } catch (e) {
    console.error('Failed to load home data:', e)
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
  loadSkills()
  loadHomeData()
  updateCountdown()
  countdownTimer = setInterval(updateCountdown, 1000)
  startBannerLoop()
})

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
  if (bannerTimer) clearInterval(bannerTimer)
})
</script>

<style scoped>
.home-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 24px 100px;
}

/* ============ Hero ============ */
.hero {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 24px;
  margin-bottom: 56px;
}

.hero-left {
  position: relative;
  padding: 32px 36px;
  overflow: hidden;
  min-height: 310px;
  display: flex;
  align-items: center;
}

.hero-3d {
  position: absolute !important;
  inset: 0;
  z-index: 1;
  opacity: 0.85;
  pointer-events: none;
}

.hero-content {
  position: relative;
  z-index: 2;
  max-width: 100%;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 99px;
  background: rgba(30, 224, 127, 0.12);
  border: 1px solid rgba(30, 224, 127, 0.3);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 20px;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 8px var(--color-primary);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.3); }
}

.hero-title {
  font-family: var(--font-display);
  font-size: 56px;
  font-weight: 800;
  line-height: 1.05;
  margin-bottom: 18px;
  letter-spacing: -1px;
}
.title-line { display: block; }

.primary-gradient {
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

/* ============ Glitch Hover (ported from skilljiaoyi) ============ */
.glitch-hover {
  position: relative;
  display: inline-block;
  transition: var(--transition-smooth);
}
.glitch-hover::before,
.glitch-hover::after {
  content: attr(data-text);
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  pointer-events: none;
  background: transparent;
  -webkit-background-clip: initial;
  background-clip: initial;
  color: var(--text-primary);
}
.primary-gradient.glitch-hover::before,
.primary-gradient.glitch-hover::after {
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.glitch-hover:hover::before {
  left: 4px;
  text-shadow: -2px 0 #ff4757;
  animation: glitch-anim-1 0.4s infinite linear alternate-reverse;
  opacity: 1;
}
.glitch-hover:hover::after {
  left: -4px;
  text-shadow: 2px 0 var(--color-accent, #00f0ff);
  animation: glitch-anim-2 0.5s infinite linear alternate-reverse;
  opacity: 1;
}
@keyframes glitch-anim-1 {
  0%   { clip-path: inset(20% 0 80% 0); transform: translateX(-4px); }
  20%  { clip-path: inset(10% 0 60% 0); transform: translateX(-6px); }
  40%  { clip-path: inset(30% 0 40% 0); transform: translateX(-4px); }
  60%  { clip-path: inset(5% 0 80% 0);  transform: translateX(-8px); }
  80%  { clip-path: inset(40% 0 50% 0); transform: translateX(-4px); }
  100% { clip-path: inset(60% 0 20% 0); transform: translateX(-6px); }
}
@keyframes glitch-anim-2 {
  0%   { clip-path: inset(10% 0 60% 0); transform: translateX(4px); }
  25%  { clip-path: inset(40% 0 30% 0); transform: translateX(6px); }
  50%  { clip-path: inset(60% 0 10% 0); transform: translateX(4px); }
  75%  { clip-path: inset(5% 0 70% 0);  transform: translateX(-8px); }
  100% { clip-path: inset(30% 0 40% 0); transform: translateX(-4px); }
}

.hero-subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 28px;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  gap: 14px;
  margin-bottom: 32px;
}

.btn-lg { padding: 14px 28px; font-size: 15px; font-weight: 600; }
.btn-sm { padding: 8px 16px; font-size: 13px; font-weight: 600; }
.btn-arrow {
  display: inline-block;
  margin-left: 4px;
  transition: transform 0.25s;
}
.btn-primary:hover .btn-arrow { transform: translateX(4px); }

.hero-stats {
  display: flex;
  align-items: center;
  gap: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--border-glass);
}

.stat-item { text-align: left; }
.stat-num {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
}
.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
}
.stat-divider {
  width: 1px;
  height: 28px;
  background: var(--border-glass);
}

/* Hero Tags Strip — ported & adapted from skilljiaoyi `hero-platforms` */
.hero-tags {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-glass);
}
.hero-tags-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-tertiary);
  letter-spacing: 1.6px;
  margin-bottom: 12px;
}
.hero-tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
  transition: all 0.25s ease;
  cursor: default;
}
.hero-tag:hover {
  background: rgba(30, 224, 127, 0.10);
  border-color: var(--color-primary, #1ee07f);
  color: var(--text-primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(30,224,127,0.18);
}
.hero-tag-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--color-primary, #1ee07f);
}
.hero-tag-icon svg {
  width: 14px;
  height: 14px;
  display: block;
  transition: transform 0.25s ease;
}
.hero-tag:hover .hero-tag-icon svg {
  transform: scale(1.15) rotate(-6deg);
}

/* Hero Right */
.hero-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.banner-carousel {
  position: relative;
  flex: 1;
  min-height: 215px;
  overflow: hidden;
  padding: 0;
}

.banner-slide {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 36px 40px;
  opacity: 0;
  transform: translateX(20px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.banner-slide.active {
  opacity: 1;
  transform: translateX(0);
}

.banner-content { max-width: 65%; }
.banner-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.1);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 14px;
  letter-spacing: 0.5px;
}
.banner-title {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--text-primary);
}
.banner-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 18px;
}
.banner-emoji {
  font-size: 96px;
  filter: drop-shadow(0 8px 20px rgba(30, 224, 127, 0.35));
  animation: bannerFloat 4s ease-in-out infinite;
}
@keyframes bannerFloat {
  0%, 100% { transform: translateY(0) rotate(-3deg); }
  50% { transform: translateY(-10px) rotate(3deg); }
}

.banner-dots {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  z-index: 3;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  cursor: pointer;
  transition: all 0.3s;
}
.dot.active {
  width: 24px;
  border-radius: 4px;
  background: var(--color-primary);
}

/* Promise Strip */
.promise-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 16px 12px;
}
.promise-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
}
.promise-icon { font-size: 22px; }
.promise-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.promise-desc { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }

/* ============ Section Header ============ */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}
.section-title {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.section-link {
  font-size: 14px;
  color: var(--color-primary);
  cursor: pointer;
  font-weight: 500;
  transition: color 0.2s;
}
.section-link:hover { color: var(--color-accent); }

/* ============ Category Grid ============ */
.category-section { margin-bottom: 56px; }
.category-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 18px;
}
.cat-tile {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 0;
  padding: 0;
  min-height: 130px;
  background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  border: 1px solid var(--border-glass);
  backdrop-filter: blur(16px);
  border-radius: 18px;
  cursor: pointer;
  transition: var(--transition-smooth);
  overflow: hidden;
  isolation: isolate;
}
.cat-tile::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 0%, var(--cat-glow, rgba(30,224,127,0.25)), transparent 70%);
  opacity: 0;
  transition: opacity 0.4s ease;
  z-index: -1;
}
.cat-tile:hover {
  transform: translateY(-6px) scale(1.03);
  border-color: var(--cat-border, rgba(30,224,127,0.55));
  box-shadow: 0 12px 32px var(--cat-shadow, rgba(30,224,127,0.22));
}
.cat-tile:hover::before { opacity: 1; }
.cat-tile:hover .cat-icon { transform: scale(1.18) rotate(-6deg); }
.cat-tile:hover .cat-name { color: var(--text-primary); }

/* per-tile theme via nth-child cycling */
.cat-tile:nth-child(6n+1) { --cat-glow: rgba(255,71,87,0.30);  --cat-border: rgba(255,71,87,0.55);  --cat-shadow: rgba(255,71,87,0.25); }
.cat-tile:nth-child(6n+2) { --cat-glow: rgba(0,240,255,0.30);  --cat-border: rgba(0,240,255,0.55);  --cat-shadow: rgba(0,240,255,0.22); }
.cat-tile:nth-child(6n+3) { --cat-glow: rgba(255,184,0,0.30);  --cat-border: rgba(255,184,0,0.55);  --cat-shadow: rgba(255,184,0,0.22); }
.cat-tile:nth-child(6n+4) { --cat-glow: rgba(190,120,255,0.30);--cat-border: rgba(190,120,255,0.55);--cat-shadow: rgba(190,120,255,0.22); }
.cat-tile:nth-child(6n+5) { --cat-glow: rgba(30,224,127,0.30); --cat-border: rgba(30,224,127,0.55); --cat-shadow: rgba(30,224,127,0.22); }
.cat-tile:nth-child(6n)   { --cat-glow: rgba(255,120,180,0.30);--cat-border: rgba(255,120,180,0.55);--cat-shadow: rgba(255,120,180,0.22); }

.cat-icon-wrap {
  position: absolute;
  inset: 0;
  border-radius: 18px;
  background:
    radial-gradient(circle at 50% 38%, rgba(255,255,255,0.12), rgba(255,255,255,0.02) 60%),
    linear-gradient(160deg, rgba(255,255,255,0.08), rgba(255,255,255,0.01));
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.10);
  transition: var(--transition-smooth);
  z-index: 0;
  padding-bottom: 32px;
}
.cat-icon {
  font-size: 48px;
  filter: drop-shadow(0 4px 10px rgba(0,0,0,0.45));
  transition: transform 0.35s cubic-bezier(.34,1.56,.64,1);
}
.cat-name {
  position: relative;
  z-index: 1;
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  letter-spacing: 0.5px;
  padding: 0 8px 12px;
  transition: color 0.3s ease;
}

/* ============ Flash Sale ============ */
.flash-section {
  margin-bottom: 56px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(255, 71, 87, 0.06), rgba(255, 184, 0, 0.04));
  border: 1px solid rgba(255, 71, 87, 0.18);
  border-radius: 24px;
}
.flash-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}
.flash-title-wrap { display: flex; align-items: center; gap: 12px; }
.flash-icon {
  font-size: 28px;
  filter: drop-shadow(0 0 8px rgba(255, 184, 0, 0.6));
  animation: flashPulse 1s ease-in-out infinite;
}
@keyframes flashPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.15); }
}
.flash-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #FFB800, #FF4757);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.flash-sub {
  font-size: 12px;
  color: var(--text-tertiary);
}
.flash-timer { display: flex; align-items: center; gap: 6px; }
.timer-label { font-size: 12px; color: var(--text-secondary); margin-right: 4px; }
.timer-block {
  background: #14141A;
  color: #FFB800;
  padding: 4px 10px;
  border-radius: 6px;
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  min-width: 32px;
  text-align: center;
  border: 1px solid rgba(255, 184, 0, 0.3);
}
.timer-sep { color: #FFB800; font-weight: 700; }

.flash-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.flash-card {
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: var(--transition-smooth);
}
.flash-card:hover {
  transform: translateY(-6px);
  border-color: rgba(255, 184, 0, 0.4);
  box-shadow: 0 12px 28px rgba(255, 184, 0, 0.2);
}
.flash-cover {
  height: 140px;
  background: linear-gradient(135deg, rgba(255,184,0,0.08), rgba(30,224,127,0.06));
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  font-size: 56px;
}
.flash-discount {
  position: absolute;
  top: 10px;
  right: 10px;
  background: linear-gradient(135deg, #FF4757, #FFB800);
  color: white;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 99px;
}
.flash-body { padding: 12px 14px 16px; }
.flash-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 8px;
}
.flash-price-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; }
.flash-price {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  color: #FF4757;
}
.flash-original {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-tertiary);
  text-decoration: line-through;
}
.flash-bar {
  position: relative;
  height: 16px;
  background: rgba(255, 71, 87, 0.12);
  border-radius: 99px;
  overflow: hidden;
}
.flash-bar-fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: linear-gradient(90deg, #FF4757, #FFB800);
  border-radius: 99px;
  transition: width 0.5s;
}
.flash-bar-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  color: white;
}

/* ============ New Arrivals ============ */
.arrivals-section { margin-bottom: 56px; }
.arrivals-scroll {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 12px;
  scrollbar-width: thin;
  scrollbar-color: var(--color-primary) transparent;
}
.arrivals-scroll::-webkit-scrollbar { height: 6px; }
.arrivals-scroll::-webkit-scrollbar-thumb { background: var(--color-primary); border-radius: 3px; }

.arrival-card {
  flex: 0 0 180px;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: var(--transition-smooth);
}
.arrival-card:hover {
  transform: translateY(-4px);
  border-color: rgba(30, 224, 127, 0.4);
}
.arrival-cover {
  height: 140px;
  background: linear-gradient(135deg, rgba(30,224,127,0.10), rgba(0,240,255,0.06));
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.arrival-emoji { font-size: 48px; }
.arrival-tag-new {
  position: absolute;
  top: 8px;
  left: 8px;
  background: var(--color-primary);
  color: #0A0A0E;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 4px;
  letter-spacing: 0.5px;
}
.arrival-name {
  padding: 10px 12px 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.arrival-price {
  padding: 0 12px 12px;
  font-family: var(--font-mono);
  font-size: 15px;
  font-weight: 700;
  color: var(--color-primary);
}
.arrival-price .free { color: var(--color-accent); }

/* ============ Recommend Section ============ */
.recommend-section { margin-bottom: 40px; }
.cat-pills { display: flex; gap: 8px; flex-wrap: wrap; }
.pill {
  padding: 6px 14px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-glass);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-smooth);
}
.pill:hover { background: rgba(255, 255, 255, 0.1); color: var(--text-primary); }
.pill.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #0A0A0E;
  font-weight: 600;
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.see-all-row {
  text-align: center;
  margin-top: 16px;
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
@keyframes spin { to { transform: rotate(360deg); } }

.skel-card {
  height: 220px;
  background: linear-gradient(90deg, rgba(255,255,255,0.04), rgba(255,255,255,0.08), rgba(255,255,255,0.04));
  background-size: 200% 100%;
  border-radius: 16px;
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ============ Responsive ============ */
@media (max-width: 992px) {
  .hero {
    grid-template-columns: 1fr;
  }
  .hero-left { padding: 26px 24px; min-height: 255px; }
  .hero-title { font-size: 40px; }
  .category-grid { grid-template-columns: repeat(6, 1fr); }
  .flash-grid { grid-template-columns: repeat(2, 1fr); }
  .promise-strip { grid-template-columns: repeat(4, 1fr); }
}

@media (max-width: 640px) {
  .home-container { padding: 16px 12px 60px; }
  .hero-left { padding: 22px 18px; min-height: 230px; }
  .hero-title { font-size: 32px; }
  .hero-subtitle { font-size: 14px; }
  .hero-actions { flex-direction: column; }
  .hero-actions .btn-lg { width: 100%; }
  .hero-stats { gap: 12px; }
  .stat-num { font-size: 18px; }
  .stat-label { font-size: 11px; }

  .banner-carousel { min-height: 150px; }
  .banner-slide { padding: 20px; }
  .banner-title { font-size: 18px; }
  .banner-emoji { font-size: 60px; }

  .promise-strip { grid-template-columns: repeat(2, 1fr); gap: 10px; }

  .section-title { font-size: 20px; }

  .category-grid { grid-template-columns: repeat(4, 1fr); gap: 10px; }
  .cat-tile { min-height: 96px; }
  .cat-icon-wrap { padding-bottom: 26px; }
  .cat-icon { font-size: 34px; }

  .flash-section { padding: 16px; border-radius: 16px; }
  .flash-header { padding: 12px 16px; }
  .flash-title { font-size: 18px; }
  .flash-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .flash-cover { height: 110px; font-size: 44px; }

  .arrival-card { flex: 0 0 140px; }
  .arrival-cover { height: 110px; }
  .arrival-emoji { font-size: 38px; }

  .skills-grid { grid-template-columns: 1fr 1fr; gap: 12px; }
}
</style>
