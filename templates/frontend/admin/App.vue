<template>
  <div class="admin-shell" :class="themeClass">
    <ParticlesBackground v-if="showChrome" />
    <aside v-if="showChrome" class="admin-sidebar glass-panel">
      <div class="admin-brand">
        <span class="admin-brand-logo">⚙️</span>
        <span class="admin-brand-text">EdgeOne Mall · Admin</span>
      </div>
      <nav class="admin-nav">
        <router-link v-for="n in nav" :key="n.path" :to="n.path" class="admin-nav-item">
          <span class="icon">{{ n.icon }}</span>{{ n.label }}
        </router-link>
      </nav>
      <button class="admin-logout" @click="logout">退出登录</button>
    </aside>
    <main class="admin-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ParticlesBackground from '../src/components/ParticlesBackground.vue'

const router = useRouter()
const route = useRoute()

const nav = [
  { path: '/admin/dashboard',   label: '仪表盘',     icon: '📊' },
  { path: '/admin/users',       label: '用户管理',   icon: '👥' },
  { path: '/admin/products',    label: '商品管理',   icon: '📦' },
  { path: '/admin/audit',       label: '商品审核',   icon: '✅' },
  { path: '/admin/orders',      label: '订单管理',   icon: '🧾' },
  { path: '/admin/recharges',   label: '充值订单',   icon: '💳' },
  { path: '/admin/withdrawals', label: '提现管理',   icon: '💸' },
  { path: '/admin/reviews',     label: '评论管理',   icon: '💬' },
  { path: '/admin/models3d',    label: '3D 模型',    icon: '🧊' },
  { path: '/admin/settings',    label: '系统设置',   icon: '⚙️' },
  { path: '/admin/backup',      label: '数据管理',   icon: '🗄️' },
]

const showChrome = computed(() => route.path !== '/admin/login')
const themeClass = computed(() => 'theme-' + (localStorage.getItem('edgeone_mall_theme') || 'dark'))

function logout() {
  localStorage.removeItem('edgeone_mall_admin_token')
  router.push('/admin/login')
}
</script>

<style scoped>
.admin-shell { display: flex; min-height: 100vh; background: var(--bg-deep, #0a0a0e); position: relative; }
.admin-sidebar { width: 240px; padding: 24px 16px; display: flex; flex-direction: column;
  position: sticky; top: 0; height: 100vh; z-index: 2;
  background: var(--bg-glass); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border-right: 1px solid var(--border-glass); box-shadow: var(--shadow-card); }
.admin-brand { display: flex; align-items: center; gap: 10px; font-family: var(--font-display);
  font-size: 1.05rem; padding: 8px 4px 24px; border-bottom: 1px solid var(--border-glass); }
.admin-brand-logo { font-size: 1.4rem; }
.admin-nav { display: flex; flex-direction: column; gap: 4px; padding-top: 16px; flex: 1; }
.admin-nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px;
  border-radius: 8px; color: var(--text-secondary); text-decoration: none;
  transition: var(--transition-smooth); font-size: 0.92rem; }
.admin-nav-item:hover { background: var(--bg-surface); color: var(--text-primary); }
.admin-nav-item.router-link-active {
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #000; font-weight: 600; }
.admin-nav-item .icon { width: 20px; text-align: center; }
.admin-logout { margin-top: 16px; padding: 10px; border-radius: 8px;
  background: transparent; border: 1px solid var(--border-glass);
  color: var(--text-secondary); cursor: pointer; }
.admin-logout:hover { color: var(--color-danger); border-color: var(--color-danger); }
.admin-main { flex: 1; padding: 32px; overflow-x: auto; position: relative; z-index: 2; }
</style>
