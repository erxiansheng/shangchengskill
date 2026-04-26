<template>
  <div class="login-wrapper">
    <div class="login-container glass-panel">
      <!-- Decorative Elements -->
      <div class="glow-orb orb-1"></div>
      <div class="glow-orb orb-2"></div>

      <div class="login-content">
        <div class="brand">
          <img src="/logo.svg" class="logo-icon-img" alt="Logo" />
          <h1 class="logo-text">Dasb<span class="primary-gradient">Claw</span></h1>
          <p class="tagline">欢迎回到 2026 最强的商城</p>
        </div>

        <!-- Login Method Tabs -->
        <div class="login-tabs">
          <button class="login-tab" :class="{ active: loginMethod === 'account' }" @click="loginMethod = 'account'">👤 账号</button>
          <button class="login-tab" :class="{ active: loginMethod === 'wechat' }" @click="loginMethod = 'wechat'">💬 微信登录</button>
          <button class="login-tab" :class="{ active: loginMethod === 'qq' }" @click="loginMethod = 'qq'">🐧 QQ 登录</button>
        </div>

        <div class="error-msg" v-if="errorMsg">{{ errorMsg }}</div>

        <!-- Account Login / Register -->
        <div v-if="loginMethod === 'account'" class="account-section">
          <div class="account-mode-tabs">
            <button class="mode-tab" :class="{ active: accountMode === 'login' }" @click="switchMode('login')">登录</button>
            <button class="mode-tab" :class="{ active: accountMode === 'register' }" @click="switchMode('register')">注册</button>
          </div>
          <form class="account-form" @submit.prevent="submitAccount">
            <input
              v-model.trim="form.username"
              class="form-input"
              type="text"
              placeholder="账号（4-32 位字母 / 数字 / 下划线）"
              autocomplete="username"
              required
              minlength="4"
              maxlength="32"
            />
            <input
              v-if="accountMode === 'register'"
              v-model.trim="form.nickname"
              class="form-input"
              type="text"
              placeholder="昵称（显示名）"
              required
              maxlength="32"
            />
            <input
              v-model="form.password"
              class="form-input"
              type="password"
              :placeholder="accountMode === 'register' ? '设置密码（≥ 6 位）' : '密码'"
              :autocomplete="accountMode === 'register' ? 'new-password' : 'current-password'"
              required
              minlength="6"
              maxlength="64"
            />
            <input
              v-if="accountMode === 'register'"
              v-model.trim="form.email"
              class="form-input"
              type="email"
              placeholder="邮箱（可选）"
              maxlength="128"
            />
            <button type="submit" class="btn-account" :disabled="submitting">
              <span v-if="submitting">处理中…</span>
              <span v-else>{{ accountMode === 'register' ? '注册并登录' : '登录' }}</span>
            </button>
          </form>
        </div>

        <!-- WeChat Login -->
        <div v-if="loginMethod === 'wechat'" class="qr-section">
          <!-- 扫码登录（所有端统一） -->
          <div v-if="wxLoading" class="qr-loading">
            <div class="loading-spinner"></div>
            <p>正在加载微信二维码...</p>
          </div>
          <div v-else-if="wxError" class="qr-error">
            <p>{{ wxError }}</p>
            <button class="btn btn-glass btn-sm" @click="loadWxQr" style="margin-top:12px">重试</button>
          </div>
          <div v-else class="qr-frame" id="wx-qr-container"></div>
          <p class="qr-hint">请使用微信扫一扫登录</p>
        </div>

        <!-- QQ Login -->
        <div v-if="loginMethod === 'qq'" class="qr-section">
          <div class="qr-placeholder">
            <button class="s-btn qq" @click="handleQQLogin">
              <span class="icon">🐧</span> 前往 QQ 授权登录
            </button>
          </div>
          <p class="qr-hint">点击按钮将跳转到 QQ 授权页面</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { userStore } from '../stores/user.js'
import { get } from '../api/request.js'
import { login as apiLogin, register as apiRegister } from '../api/auth.js'

const router = useRouter()

const loginMethod = ref('account')
const errorMsg = ref('')

// --- 账号登录 / 注册 ---
const accountMode = ref('login') // 'login' | 'register'
const submitting = ref(false)
const form = reactive({
  username: '',
  password: '',
  nickname: '',
  email: '',
})

function switchMode(mode) {
  accountMode.value = mode
  errorMsg.value = ''
}

async function submitAccount() {
  if (submitting.value) return
  errorMsg.value = ''
  submitting.value = true
  try {
    let res
    if (accountMode.value === 'register') {
      const payload = {
        username: form.username,
        password: form.password,
        nickname: form.nickname || form.username,
      }
      if (form.email) payload.email = form.email
      res = await apiRegister(payload)
    } else {
      res = await apiLogin(form.username, form.password)
    }
    if (res && res.code === 0 && res.data && res.data.access_token) {
      userStore.setUser(res.data)
      router.push('/')
    } else {
      errorMsg.value = (res && res.message) || '请求失败，请重试'
    }
  } catch (e) {
    errorMsg.value = (e && e.message) || '网络错误，请稍后重试'
  } finally {
    submitting.value = false
  }
}

// --- 平台检测 ---
const ua = navigator.userAgent.toLowerCase()
const isMobile = /android|iphone|ipad|ipod|mobile/i.test(ua)
const isWeChatBrowser = /micromessenger/i.test(ua)

// --- PC 扫码相关 ---
const wxLoading = ref(true)
const wxError = ref('')
let wxAppId = ''
let wxRedirectUri = ''

// --- H5 授权相关（已移除，统一使用扫码） ---

const handleQQLogin = () => {
  window.location.href = '/api/v1/auth/qq/login'
}

// --- PC 扫码相关方法 ---
const loadWxConfig = async () => {
  try {
    const res = await get('/auth/wechat/login', { debug: '1' })
    if (res.code === 0 && res.data) {
      wxAppId = res.data.params?.appid || ''
      wxRedirectUri = res.data.params?.redirect_uri || ''
    } else {
      wxError.value = res.message || '微信登录未配置'
    }
  } catch (e) {
    wxError.value = '获取微信配置失败'
  }
}

const loadWxQr = async () => {
  wxLoading.value = true
  wxError.value = ''
  await loadWxConfig()
  if (!wxAppId || !wxRedirectUri) {
    wxLoading.value = false
    if (!wxError.value) wxError.value = '微信登录未配置，请联系管理员'
    return
  }
  wxLoading.value = false
  await nextTick()
  renderWxQr()
}

const renderWxQr = () => {
  const container = document.getElementById('wx-qr-container')
  if (!container) return
  container.innerHTML = ''

  // 使用微信开放平台 JS SDK 内嵌二维码
  // https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
  if (typeof WxLogin !== 'undefined') {
    new WxLogin({
      self_redirect: false,
      id: 'wx-qr-container',
      appid: wxAppId,
      scope: 'snsapi_login',
      redirect_uri: encodeURIComponent(wxRedirectUri),
      state: 'EdgeOneMall_wx',
      style: 'black',
      href: '',
    })
  } else {
    // 如果 SDK 未加载，使用 iframe 方式
    const src = `https://open.weixin.qq.com/connect/qrconnect?appid=${wxAppId}&redirect_uri=${encodeURIComponent(wxRedirectUri)}&response_type=code&scope=snsapi_login&state=EdgeOneMall_wx#wechat_redirect`
    const iframe = document.createElement('iframe')
    iframe.src = src
    iframe.frameBorder = '0'
    iframe.scrolling = 'no'
    iframe.width = '300'
    iframe.height = '420'
    iframe.style.border = 'none'
    container.appendChild(iframe)
  }
}

// Load WeChat JS SDK
const loadWxSdk = () => {
  return new Promise((resolve) => {
    if (typeof WxLogin !== 'undefined') {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = 'https://res.wx.qq.com/connect/zh_CN/htmledition/js/wxLogin.js'
    script.onload = resolve
    script.onerror = resolve // Resolve anyway, fallback to iframe
    document.head.appendChild(script)
  })
}

watch(loginMethod, async (val) => {
  errorMsg.value = ''
  if (val === 'wechat' && wxAppId) {
    await nextTick()
    renderWxQr()
  }
})

onMounted(async () => {
  // 账号登录为默认 tab，不需要提前加载 WX SDK。
  // 如果用户切换到 wechat tab，这里主动加载一次。
  if (loginMethod.value === 'wechat') {
    await loadWxSdk()
    loadWxQr()
  }
})
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login-container {
  width: 100%;
  max-width: 440px;
  padding: 48px;
  position: relative;
  overflow: hidden;
  border-radius: 24px;
  box-shadow: 0 32px 64px rgba(0,0,0,0.5), inset 0 0 0 1px rgba(255,255,255,0.05);
}

.glow-orb {
  position: absolute;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  filter: blur(80px);
  z-index: 0;
  pointer-events: none;
}

.orb-1 {
  background: rgba(255, 59, 48, 0.4);
  top: -100px;
  right: -50px;
}

.orb-2 {
  background: rgba(10, 132, 255, 0.3);
  bottom: -100px;
  left: -50px;
}

.login-content {
  position: relative;
  z-index: 2;
}

.brand {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon-img {
  height: 80px;
  width: auto;
  margin-bottom: 16px;
  filter: drop-shadow(0 0 20px var(--color-primary-glow));
}

.logo-text {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -1px;
  margin-bottom: 8px;
}

.tagline {
  color: var(--text-secondary);
  font-size: 14px;
}

/* Login Tabs */
.login-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.login-tab {
  flex: 1;
  padding: 12px 16px;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border-glass);
  border-radius: 12px;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.login-tab:hover {
  background: rgba(255,255,255,0.1);
}

.login-tab.active {
  background: rgba(var(--color-primary-rgb, 255,59,48), 0.15);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.error-msg {
  color: #FF453A;
  font-size: 14px;
  text-align: center;
  padding: 8px 12px;
  background: rgba(255, 69, 58, 0.1);
  border-radius: 8px;
  border: 1px solid rgba(255, 69, 58, 0.2);
  margin-bottom: 16px;
}

/* QR Section */
.qr-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
}

.qr-frame {
  width: 300px;
  height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 12px;
}

.qr-frame :deep(iframe) {
  border: none !important;
  border-radius: 12px;
}

.qr-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 48px 0;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-glass);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.qr-error {
  text-align: center;
  padding: 32px 0;
  color: #FF453A;
  font-size: 14px;
}

.qr-placeholder {
  padding: 32px 0;
  width: 100%;
}

.qr-hint {
  color: var(--text-tertiary);
  font-size: 13px;
  margin-top: 16px;
  text-align: center;
}

.s-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: rgba(9, 184, 62, 0.1);
  border: 1px solid rgba(9, 184, 62, 0.3);
  color: #09B83E;
  padding: 14px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.s-btn:hover {
  background: rgba(9, 184, 62, 0.2);
}

.s-btn.qq {
  background: rgba(18, 183, 245, 0.1);
  border: 1px solid rgba(18, 183, 245, 0.3);
  color: #12B7F5;
}
.s-btn.qq:hover {
  background: rgba(18, 183, 245, 0.2);
}

.s-btn.wechat {
  background: rgba(9, 184, 62, 0.1);
  border: 1px solid rgba(9, 184, 62, 0.3);
  color: #09B83E;
}
.s-btn.wechat:hover {
  background: rgba(9, 184, 62, 0.2);
}

.btn-sm {
  padding: 8px 20px;
  font-size: 13px;
}

/* Mobile WeChat Tip */
.mobile-wx-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
  text-align: center;
}

.tip-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.tip-text {
  font-size: 15px;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.tip-sub {
  font-size: 13px;
  color: var(--text-tertiary);
}

@media (max-width: 768px) {
  .login-wrapper { padding: 16px; }
  .login-container { padding: 28px 20px; border-radius: 16px; }
  .logo-icon-img { height: 60px; margin-bottom: 10px; }
  .logo-text { font-size: 26px; }
  .brand { margin-bottom: 24px; }
  .login-tab { padding: 10px 12px; font-size: 13px; }
  .qr-frame { width: 280px; height: 400px; }
  .s-btn { padding: 12px; font-size: 14px; }
}

/* Account Login / Register Section */
.account-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.account-mode-tabs {
  display: flex;
  gap: 6px;
  padding: 4px;
  background: rgba(255,255,255,0.04);
  border-radius: 10px;
  border: 1px solid var(--border-glass);
}

.mode-tab {
  flex: 1;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.mode-tab:hover { color: var(--text-primary); }

.mode-tab.active {
  background: rgba(var(--color-primary-rgb, 255,59,48), 0.15);
  color: var(--color-primary);
}

.account-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-input {
  width: 100%;
  padding: 12px 14px;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border-glass);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: var(--transition-smooth);
  box-sizing: border-box;
}

.form-input::placeholder { color: var(--text-tertiary); }

.form-input:focus {
  border-color: var(--color-primary);
  background: rgba(255,255,255,0.08);
  box-shadow: 0 0 0 3px rgba(var(--color-primary-rgb, 255,59,48), 0.15);
}

.btn-account {
  width: 100%;
  padding: 13px;
  margin-top: 4px;
  background: var(--color-primary, #FF3B30);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.btn-account:hover:not(:disabled) {
  filter: brightness(1.1);
  box-shadow: 0 8px 24px rgba(var(--color-primary-rgb, 255,59,48), 0.3);
}

.btn-account:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
