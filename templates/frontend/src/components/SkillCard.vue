<template>
  <div class="skill-card" @mousemove="handleMouseMove" @mouseleave="handleMouseLeave" ref="cardRef">
    <div class="card-inner" :style="cardTransform">
      <div class="card-glow" :style="glowStyle"></div>
      <div class="category-tag" v-if="skill.category_name || skill.category">{{ skill.category_name || skill.category }}</div>

      <div class="card-content">
        <div class="card-header">
          <h3 class="skill-title">{{ skill.title }}</h3>
          <div class="price-tag" :class="{'is-free': skill.price === 0 || skill.is_free}">
            {{ (skill.price === 0 || skill.is_free) ? '免费' : skill.price }}
            <span v-if="skill.price > 0 && !skill.is_free" class="coin">💰</span>
          </div>
        </div>

        <p class="skill-desc">{{ skill.subtitle || skill.description }}</p>

        <div class="card-footer">
          <div class="author">
            <img :src="authorAvatar" alt="Author" class="author-avatar" />
            <span class="author-name">{{ skill.author_name || skill.author || '' }}</span>
            <span class="author-badge admin-badge" v-if="skill.author_role === 'admin'">🔧 管理员</span>
            <span class="author-badge level-badge" v-else-if="skill.author_level_info">{{ skill.author_level_info.icon }} {{ skill.author_level_info.name }}</span>
          </div>

          <div class="stats">
            <span class="rating">
              ⭐{{ skill.avg_rating ?? skill.rating ?? 0 }}
            </span>
            <span class="downloads">
              📥{{ formattedDownloads }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { formatDownloads } from '../utils.js'

const props = defineProps({
  skill: {
    type: Object,
    required: true
  }
})

const authorAvatar = computed(() => {
  return props.skill.author_avatar || props.skill.authorAvatar || 'https://api.dicebear.com/7.x/avataaars/svg?seed=default'
})

const formattedDownloads = computed(() => {
  const count = props.skill.download_count ?? props.skill.downloads
  if (typeof count === 'string') return count
  return formatDownloads(count)
})

const cardRef = ref(null)
const mousePos = ref({ x: 0, y: 0, isHovering: false })

const handleMouseMove = (e) => {
  if (!cardRef.value) return
  const rect = cardRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  mousePos.value = { x, y, isHovering: true }
}

const handleMouseLeave = () => {
  mousePos.value.isHovering = false
}

// 3D Tilt effect
const cardTransform = computed(() => {
  if (!mousePos.value.isHovering || !cardRef.value) return 'transform: perspective(1000px) rotateX(0) rotateY(0) scale3d(1, 1, 1)'

  const width = cardRef.value.offsetWidth
  const height = cardRef.value.offsetHeight

  const rotateY = ((mousePos.value.x / width) - 0.5) * 10
  const rotateX = ((mousePos.value.y / height) - 0.5) * -10

  return `transform: perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`
})

// Dynamic glow effect that follows mouse
const glowStyle = computed(() => {
  if (!mousePos.value.isHovering) return 'opacity: 0'
  return `
    background: radial-gradient(
      circle at ${mousePos.value.x}px ${mousePos.value.y}px,
      rgba(255, 255, 255, 0.15) 0%,
      transparent 80%
    );
    opacity: 1;
  `
})
</script>

<style scoped>
.skill-card {
  perspective: 1000px;
  cursor: pointer;
  height: 100%;
}

.card-inner {
  position: relative;
  background: rgba(15, 15, 22, 0.6);
  border: 1px solid var(--border-glass);
  border-radius: 20px;
  overflow: hidden;
  transition: transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.2s;
  height: 100%;
  display: flex;
  flex-direction: column;
  transform: translateZ(0);
  -webkit-transform: translateZ(0);
  -webkit-mask-image: -webkit-radial-gradient(white, black);
}

.skill-card:hover .card-inner {
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.2);
  z-index: 10;
}

.card-glow {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 2;
  transition: opacity 0.3s;
}

.category-tag {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 4;
  display: inline-block;
  background: rgba(30, 224, 127, 0.12);
  backdrop-filter: blur(12px);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-primary);
  border: 1px solid rgba(30, 224, 127, 0.18);
  white-space: nowrap;
  line-height: 1.4;
}

.card-content {
  padding: 40px 20px 20px;
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  position: relative;
  z-index: 3;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.skill-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  line-height: 1.3;
  color: var(--text-primary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.price-tag {
  background: rgba(255, 149, 0, 0.15);
  color: var(--color-accent);
  padding: 4px 8px;
  border-radius: 6px;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: 12px;
}

.price-tag.is-free {
  background: rgba(52, 199, 89, 0.15);
  color: #34C759;
}

.skill-desc {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 20px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex-grow: 1;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.author {
  display: flex;
  align-items: center;
  gap: 8px;
}

.author-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--border-glass);
}

.author-name {
  font-size: 13px;
  color: var(--text-tertiary);
  font-weight: 500;
}

.author-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 600;
  line-height: 1.4;
}
.admin-badge {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
}
.level-badge {
  background: rgba(30, 224, 127, 0.12);
  color: #1ee07f;
}

.stats {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.rating {
  color: #FFD60A;
}
</style>
