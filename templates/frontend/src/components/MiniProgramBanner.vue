<template>
  <Teleport to="body">
    <!-- 底部浮动条 -->
    <div v-if="visible && !expanded" class="mp-bar" @click="expanded = true">
      <img src="/xcx.jpg" class="mp-bar-icon" alt="" />
      <span class="mp-bar-text">使用微信小程序体验更佳</span>
      <span class="mp-bar-action">打开 ›</span>
      <button class="mp-bar-close" @click.stop="dismiss">✕</button>
    </div>

    <!-- 展开弹窗 -->
    <div v-if="expanded" class="mp-overlay" @click.self="expanded = false">
      <div class="mp-modal glass-panel">
        <button class="mp-modal-close" @click="expanded = false">✕</button>
        <h3>打开微信小程序</h3>
        <p class="mp-modal-hint">长按识别下方小程序码，获得更流畅的移动端体验</p>
        <div class="mp-qr-wrap">
          <img src="/xcx.jpg" alt="小程序码" class="mp-qr-img" />
        </div>
        <p class="mp-modal-sub">微信扫一扫 或 长按识别</p>
        <button class="btn btn-glass" @click="dismiss" style="margin-top: 12px; width: 100%;">
          不再提示
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const visible = ref(false)
const expanded = ref(false)

const DISMISS_KEY = 'mp_banner_dismissed'

onMounted(() => {
  // 仅在手机浏览器 + 非小程序内展示
  const ua = navigator.userAgent
  const isMobile = /android|iphone|ipad|ipod|mobile/i.test(ua)
  const isInMiniProgram = document.documentElement.classList.contains('in-miniprogram')
  const dismissed = localStorage.getItem(DISMISS_KEY)
  if (isMobile && !isInMiniProgram && !dismissed) {
    visible.value = true
  }
})

function dismiss() {
  visible.value = false
  expanded.value = false
  localStorage.setItem(DISMISS_KEY, '1')
}
</script>

<style scoped>
/* 底部浮动条 */
.mp-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 900;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--bg-glass);
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--border-glass);
  cursor: pointer;
}

.mp-bar-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  object-fit: cover;
}

.mp-bar-text {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.mp-bar-action {
  font-size: 13px;
  color: var(--color-primary);
  font-weight: 600;
  white-space: nowrap;
}

.mp-bar-close {
  background: none;
  border: none;
  color: var(--text-tertiary);
  font-size: 16px;
  padding: 4px 8px;
  cursor: pointer;
}

/* 弹窗遮罩 */
.mp-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.mp-modal {
  position: relative;
  width: 100%;
  max-width: 320px;
  padding: 28px 24px;
  text-align: center;
  border-radius: 20px;
}

.mp-modal-close {
  position: absolute;
  top: 12px;
  right: 12px;
  background: none;
  border: none;
  color: var(--text-tertiary);
  font-size: 18px;
  cursor: pointer;
}

.mp-modal h3 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 8px;
}

.mp-modal-hint {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 20px;
  line-height: 1.5;
}

.mp-qr-wrap {
  width: 200px;
  height: 200px;
  margin: 0 auto 12px;
  background: white;
  border-radius: 16px;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mp-qr-img {
  width: 184px;
  height: 184px;
  border-radius: 8px;
  object-fit: cover;
}

.mp-modal-sub {
  font-size: 13px;
  color: var(--text-tertiary);
}
</style>
