<template>
  <div class="login-page">
    <div class="login-card glass-panel">
      <h1 class="login-title">EdgeOne Mall<br /><span>后台管理</span></h1>
      <form @submit.prevent="submit">
        <input v-model="username" placeholder="管理员账号" autocomplete="username" required />
        <input v-model="password" type="password" placeholder="密码" autocomplete="current-password" required />
        <button type="submit" :disabled="loading">{{ loading ? '登录中…' : '登 录' }}</button>
      </form>
      <p v-if="error" class="error">{{ error }}</p>
      <p class="hint">默认管理员由 <code>ADMIN_INIT_USERNAME</code> / <code>ADMIN_INIT_PASSWORD</code> 环境变量在首次部署时注入。首次登录后请立即修改密码。</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/v1/admin/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value }),
    })
    const json = await res.json()
    if (json.code !== 0) throw new Error(json.message || '登录失败')
    localStorage.setItem('edgeone_mall_admin_token', json.data.access_token)
    if (json.data.must_change_password) {
      // TODO: redirect to a forced change-password page
      router.push('/admin/settings')
    } else {
      router.push('/admin/dashboard')
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: grid; place-items: center; padding: 24px;
  background: radial-gradient(circle at 30% 20%, rgba(30,224,127,.1), transparent 50%),
              radial-gradient(circle at 70% 80%, rgba(0,240,255,.08), transparent 50%); }
.login-card { width: 100%; max-width: 380px; padding: 36px 28px; }
.login-title { font-family: var(--font-display); margin: 0 0 24px; line-height: 1.2; }
.login-title span { font-size: .8rem; color: var(--text-secondary); font-weight: 400; }
form { display: flex; flex-direction: column; gap: 12px; }
input { padding: 12px 14px; border-radius: 8px; border: 1px solid var(--border-glass);
  background: var(--bg-surface); color: var(--text-primary); font-size: .95rem; }
button { padding: 12px; border: none; border-radius: 8px; cursor: pointer;
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #000; font-weight: 600; }
button:disabled { opacity: .6; cursor: wait; }
.error { color: var(--color-danger); font-size: .85rem; margin-top: 12px; }
.hint { color: var(--text-tertiary); font-size: .78rem; line-height: 1.5; margin-top: 20px; }
.hint code { background: var(--bg-surface); padding: 1px 6px; border-radius: 4px; }
</style>
