<template>
  <div class="app-wrapper">
    <ParticlesBackground />
    <Navbar v-if="!isAuthPage" />
    
    <main class="main-content" :class="{ 'no-nav': isAuthPage }">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <footer v-if="(siteIcp || sitePolice) && !isAuthPage" class="site-footer">
      <div class="footer-inner">
        <a v-if="siteIcp" href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">{{ siteIcp }}</a>
        <span v-if="siteIcp && sitePolice" class="divider">|</span>
        <span v-if="sitePolice">{{ sitePolice }}</span>
      </div>
    </footer>

    <ToastNotification />
    <MiniProgramBanner />

    <!-- Announcement Popup — Envelope Style -->
    <div v-if="showBetaPopup" class="announce-overlay" @click.self="closeBetaPopup">
      <div class="envelope">
        <div class="envelope-flap-open"></div>
        <div class="envelope-back"></div>
        <div class="letter">
          <div class="letter-seal">📮</div>
          <div class="letter-header">
            <div class="letter-deco-line"></div>
            <h2 class="letter-title">{{ announcementTitle || '站点公告' }}</h2>
            <div class="letter-deco-line"></div>
          </div>
          <div class="letter-content" v-if="announcementContent">
            <p v-for="(line, i) in announcementContent.split('\n')" :key="i">{{ line || '\u00A0' }}</p>
          </div>
          <div class="letter-content letter-empty" v-else>
            <p>暂无公告内容</p>
          </div>
          <div class="letter-footer">
            <span class="letter-date">{{ new Date().toLocaleDateString('zh-CN') }}</span>
          </div>
          <button class="letter-btn" @click="closeBetaPopup">知道了</button>
        </div>
        <div class="envelope-front-left"></div>
        <div class="envelope-front-right"></div>
        <div class="envelope-front-bottom"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import Navbar from './components/Navbar.vue'
import ParticlesBackground from './components/ParticlesBackground.vue'
import ToastNotification from './components/ToastNotification.vue'
import MiniProgramBanner from './components/MiniProgramBanner.vue'
import { themeStore } from './stores/theme.js'
import { get } from './api/request.js'
import { setRemoteLevels, setExpConfig } from './utils/levels.js'

const route = useRoute()
const isAuthPage = computed(() => ['Login', 'OAuthCallback'].includes(route.name))

const siteIcp = ref('')
const sitePolice = ref('')
const showBetaPopup = ref(false)
const announcementTitle = ref('')
const announcementContent = ref('')

const closeBetaPopup = () => {
  showBetaPopup.value = false
  sessionStorage.setItem('betaPopupDismissed', '1')
}

onMounted(async () => {
  themeStore.init()
  // 加载远程等级配置
  try {
    const cfgRes = await get('/points/config')
    if (cfgRes.code === 0 && cfgRes.data?.levels) {
      setRemoteLevels(cfgRes.data.levels)
      setExpConfig({
        expPublish: cfgRes.data.expPublish,
        expDownload: cfgRes.data.expDownload,
        expFavorite: cfgRes.data.expFavorite,
        expRechargeYuan: cfgRes.data.expRechargeYuan,
      })
    }
  } catch (e) { /* ignore */ }
  try {
    const res = await get('/site/public-settings')
    if (res.code === 0 && res.data) {
      siteIcp.value = res.data.icp || ''
      sitePolice.value = res.data.police || ''
      // Show announcement if enabled and not dismissed this session
      if (res.data.betaAnnouncement && !sessionStorage.getItem('betaPopupDismissed')) {
        announcementTitle.value = res.data.announcementTitle || '站点公告'
        announcementContent.value = res.data.announcementContent || ''
        showBetaPopup.value = true
      }
    }
  } catch (e) {
    // Settings not available, skip footer
  }
})
</script>

<style>
.app-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  padding-top: 72px; /* Navbar height */
  width: 100%;
}

.main-content.no-nav {
  padding-top: 0;
}

/* Page Transition Animations */
.page-enter-active,
.page-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.page-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

.site-footer {
  text-align: center;
  padding: 20px 16px;
  font-size: 13px;
  color: var(--text-tertiary);
  border-top: 1px solid var(--border-glass);
}
.site-footer .footer-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}
.site-footer a {
  color: var(--text-tertiary);
  text-decoration: none;
  transition: color 0.2s;
}
.site-footer a:hover {
  color: var(--text-secondary);
}
.site-footer .divider {
  color: var(--border-glass);
}

/* Announcement Envelope Popup */
.announce-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(8px);
  animation: fadeIn .3s ease;
}
@keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
@keyframes slideUp { from { opacity: 0; transform: translateY(40px) scale(0.96) } to { opacity: 1; transform: translateY(0) scale(1) } }
@keyframes sealBounce { 0% { transform: rotate(8deg) scale(1) } 50% { transform: rotate(-4deg) scale(1.15) } 100% { transform: rotate(8deg) scale(1) } }

.envelope {
  position: relative;
  width: 420px;
  max-width: 92vw;
  margin-top: 60px;
  animation: slideUp .5s cubic-bezier(.16,1,.3,1);
}
.envelope-flap-open {
  position: absolute;
  top: -59px; left: 0; right: 0; height: 60px;
  background: linear-gradient(180deg, #d4b896 0%, #c4a67a 100%);
  clip-path: polygon(50% 0, 0 100%, 100% 100%);
  z-index: 0;
}
.envelope-back {
  position: absolute;
  top: 0; bottom: 0; left: 0; right: 0;
  background: linear-gradient(180deg, #c4a67a 0%, #a88158 100%);
  border-radius: 0 0 12px 12px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.3);
  z-index: 1;
}
.envelope-front-left {
  position: absolute;
  bottom: 0; left: 0; width: 51%; height: 110px;
  background: linear-gradient(135deg, #efe0c9 0%, #d4b896 100%);
  clip-path: polygon(0 100%, 0 0, 100% 25px, 100% 100%);
  border-radius: 0 0 0 12px;
  z-index: 3;
  pointer-events: none;
}
.envelope-front-right {
  position: absolute;
  bottom: 0; right: 0; width: 51%; height: 110px;
  background: linear-gradient(225deg, #f5ead6 0%, #c4a67a 100%);
  clip-path: polygon(0 25px, 100% 0, 100% 100%, 0 100%);
  border-radius: 0 0 12px 0;
  z-index: 4;
  pointer-events: none;
  border-left: 2px solid rgba(0,0,0,0.06);
}
.envelope-front-bottom {
  position: absolute;
  bottom: 0; left: 0; right: 0; height: 75px;
  background: linear-gradient(0deg, #c8a87a 0%, #e8d5b7 100%);
  clip-path: polygon(0 100%, 50% 0, 100% 100%);
  border-radius: 0 0 12px 12px;
  z-index: 5;
  pointer-events: none;
  filter: drop-shadow(0 -3px 4px rgba(0,0,0,0.06));
}
.letter {
  position: relative;
  z-index: 2;
  background: linear-gradient(180deg, #fffefa 0%, #fdf8ef 100%);
  border-radius: 12px;
  margin: -15px 14px 45px 14px;
  padding: 32px 28px 44px;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0,0,0,0.15);
}
.letter-seal {
  position: absolute;
  top: 14px;
  right: 18px;
  font-size: 32px;
  opacity: 0.85;
  transform: rotate(8deg);
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
  transition: transform 0.3s ease;
  cursor: default;
}
.letter-seal:hover {
  animation: sealBounce 0.5s ease;
}
.letter-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  justify-content: center;
}
.letter-deco-line {
  flex: 1;
  max-width: 50px;
  height: 2px;
  background: linear-gradient(90deg, transparent, #c8a87a, transparent);
  border-radius: 1px;
}
.letter-title {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: #4a3a2a;
  letter-spacing: 1px;
  text-shadow: 0 1px 0 rgba(255,255,255,0.6);
}
.letter-content {
  color: #6b5d4f;
  font-size: 14.5px;
  line-height: 2;
  margin-bottom: 16px;
  text-align: left;
  padding: 16px 16px;
  background: rgba(200, 170, 120, 0.06);
  border-radius: 8px;
  border-left: 3px solid rgba(200, 168, 122, 0.3);
}
.letter-content p {
  margin: 0 0 4px;
}
.letter-content.letter-empty {
  text-align: center;
  color: #a89880;
  font-style: italic;
  border-left-color: transparent;
}
.letter-footer {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}
.letter-date {
  font-size: 12px;
  color: #b3a090;
  font-style: italic;
}
.letter-btn {
  display: inline-block;
  padding: 11px 40px;
  background: linear-gradient(135deg, #c8956c, #a87650);
  color: #fff;
  border: none;
  border-radius: 24px;
  font-size: 14.5px;
  font-weight: 600;
  cursor: pointer;
  transition: transform .15s, box-shadow .15s;
  box-shadow: 0 4px 16px rgba(168,118,80,0.35);
  letter-spacing: 0.5px;
}
.letter-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(168,118,80,0.45);
}
.letter-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(168,118,80,0.3);
}
</style>
