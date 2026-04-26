<template>
  <div class="oauth-callback">
    <div class="loading-state">
      <div class="loading-spinner"></div>
      <p>{{ message }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { userStore } from '../stores/user.js'

const message = ref('正在登录中...')

onMounted(() => {
  // If already logged in (e.g. page refresh after successful login), go home
  if (userStore.isLoggedIn && localStorage.getItem('EdgeOneMall_token')) {
    window.location.replace('/')
    return
  }

  // Try hash first, then query params as fallback
  let params
  const hash = window.location.hash.slice(1)
  if (hash) {
    params = new URLSearchParams(hash)
  } else {
    params = new URLSearchParams(window.location.search)
  }

  const accessToken = params.get('access_token')
  const refreshToken = params.get('refresh_token')
  const nickname = params.get('nickname')
  const userId = params.get('user_id')
  const role = params.get('role')

  if (!accessToken) {
    message.value = '登录失败：缺少授权信息'
    setTimeout(() => { window.location.href = '/login' }, 2000)
    return
  }

  userStore.setUser({
    access_token: accessToken,
    refresh_token: refreshToken,
    user: {
      id: parseInt(userId) || 0,
      nickname: nickname || '用户',
      role: role || 'user',
    },
  })

  message.value = '登录成功，正在跳转...'
  // Use full page reload to ensure userStore reinitializes from localStorage
  window.location.replace('/')
})
</script>

<style scoped>
.oauth-callback {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.loading-state { text-align: center; color: var(--text-secondary); }
.loading-spinner {
  width: 40px; height: 40px; border: 3px solid var(--border-glass);
  border-top-color: var(--color-primary); border-radius: 50%;
  animation: spin 0.8s linear infinite; margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
