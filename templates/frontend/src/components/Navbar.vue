<template>
  <nav class="navbar" :class="{ 'scrolled': isScrolled }">
    <div class="container nav-container">
      <div class="logo-area" @click="$router.push('/')">
        <img src="/logo.png" class="logo-icon-img" alt="Logo" />
        <span class="logo-text">EdgeOneMall <span class="primary-gradient">Skills</span></span>
      </div>

      <div class="nav-links" :class="{ 'mobile-open': mobileMenuOpen }">
        <router-link to="/" class="nav-link" active-class="active" exact @click="mobileMenuOpen = false">市场</router-link>
        <router-link to="/explore" class="nav-link" active-class="active" @click="mobileMenuOpen = false">探索</router-link>
        <router-link v-if="userStore.isLoggedIn" to="/upload" class="nav-link" active-class="active" @click="mobileMenuOpen = false">发布</router-link>
        <router-link v-if="userStore.user?.role === 'admin' || userStore.user?.id === 1" to="/admin" class="nav-link" active-class="active" @click="mobileMenuOpen = false">管理</router-link>
        <router-link to="/about" class="nav-link" active-class="active" @click="mobileMenuOpen = false">关于</router-link>
      </div>

      <div class="nav-actions">
        <div class="search-bar hide-mobile">
          <span class="search-icon">⌘K</span>
          <input type="text" placeholder="搜索AI商品..." v-model="searchQuery" @keyup.enter="handleSearch" />
        </div>

        <button class="theme-toggle" @click="themeStore.toggle()" :title="themeStore.isDark ? '切换亮色主题' : '切换暗色主题'" id="theme-toggle-btn">
          <span class="theme-icon" :class="{ 'is-light': !themeStore.isDark }">
            {{ themeStore.isDark ? '🌙' : '☀️' }}
          </span>
        </button>

        <template v-if="userStore.isLoggedIn">
          <router-link to="/points" class="points-badge hide-mobile">
            <span class="coin">💰</span>
            <span class="amount">{{ userStore.user?.points_balance?.toLocaleString() || 0 }}</span>
          </router-link>

          <router-link to="/profile" class="user-avatar">
            <img :src="userStore.user?.avatar_url || 'https://api.dicebear.com/7.x/avataaars/svg?seed=Lobster'" alt="User" />
          </router-link>
        </template>

        <template v-else>
          <router-link to="/login" class="btn btn-primary btn-nav-login">登录</router-link>
        </template>

        <button class="mobile-menu-btn" @click="mobileMenuOpen = !mobileMenuOpen">
          <span :class="{ 'open': mobileMenuOpen }">☰</span>
        </button>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { userStore } from '../stores/user.js'
import { themeStore } from '../stores/theme.js'
import { getMe } from '../api/user.js'

const router = useRouter()
const mobileMenuOpen = ref(false)
const isScrolled = ref(false)
const searchQuery = ref('')

const handleScroll = () => {
  isScrolled.value = window.scrollY > 20
}

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    router.push({ path: '/explore', query: { keyword: searchQuery.value.trim() } })
    searchQuery.value = ''
  }
}

// Refresh user data on mount if logged in
const refreshUserData = async () => {
  if (!userStore.isLoggedIn) return
  try {
    const res = await getMe()
    if (res.code === 0) {
      userStore.updateUser(res.data)
    }
  } catch (e) {
    // Silent fail - user data will be stale but not broken
  }
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
  refreshUserData()
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 72px;
  z-index: 100;
  transition: var(--transition-smooth);
  border-bottom: 1px solid transparent;
}

.navbar.scrolled {
  background: rgba(5, 5, 8, 0.7);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-bottom: 1px solid var(--border-glass);
}

.nav-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.logo-icon-img {
  height: 32px;
  width: auto;
  filter: drop-shadow(0 0 8px var(--color-primary-glow));
}

.logo-text {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.nav-links {
  display: flex;
  gap: 32px;
}

.nav-link {
  text-decoration: none;
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 15px;
  transition: var(--transition-smooth);
  position: relative;
}

.nav-link:hover {
  color: var(--text-primary);
}

.nav-link.active {
  color: var(--text-primary);
}

.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--color-primary);
  border-radius: 2px;
  box-shadow: 0 0 8px var(--color-primary);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-bar {
  position: relative;
  display: flex;
  align-items: center;
}

.search-bar input {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-glass);
  border-radius: 99px;
  padding: 8px 16px 8px 36px;
  color: var(--text-primary);
  font-size: 14px;
  width: 200px;
  transition: var(--transition-smooth);
  outline: none;
}

.search-bar input:focus {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-glow);
  width: 240px;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 12px;
  color: var(--text-tertiary);
  pointer-events: none;
}

.points-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 149, 0, 0.1);
  border: 1px solid rgba(255, 149, 0, 0.2);
  padding: 6px 12px;
  border-radius: 99px;
  cursor: pointer;
  transition: var(--transition-smooth);
  text-decoration: none;
}

.points-badge:hover {
  background: rgba(255, 149, 0, 0.15);
  transform: translateY(-1px);
}

.points-badge .amount {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-accent);
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--border-glass);
  padding: 2px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.user-avatar img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.user-avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 0 12px var(--color-primary-glow);
}

.btn-nav-login {
  padding: 8px 20px;
  font-size: 14px;
  border-radius: 99px;
  text-decoration: none;
}
.theme-toggle {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid var(--border-glass);
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-smooth);
  padding: 0;
  flex-shrink: 0;
}

.theme-toggle:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: scale(1.1);
  border-color: var(--color-primary);
  box-shadow: 0 0 16px var(--color-primary-glow);
}

.theme-icon {
  font-size: 18px;
  display: inline-block;
  transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.theme-icon.is-light {
  transform: rotate(360deg);
}

/* Mobile hamburger menu button */
.mobile-menu-btn {
  display: none;
  background: none;
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 20px;
  width: 38px;
  height: 38px;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  transition: var(--transition-smooth);
}
.mobile-menu-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--color-primary);
}

@media (max-width: 768px) {
  .mobile-menu-btn { display: flex; }
  .hide-mobile { display: none !important; }

  .logo-text { font-size: 18px; }
  .logo-icon-img { height: 26px; }

  .nav-links {
    display: none;
    position: absolute;
    top: 72px;
    left: 0;
    right: 0;
    flex-direction: column;
    background: #0a0a0e;
    border-bottom: 1px solid var(--border-glass);
    padding: 12px 0;
    gap: 0;
    z-index: 99;
  }
  .nav-links.mobile-open { display: flex; }
  .nav-links .nav-link {
    padding: 14px 24px;
    font-size: 16px;
    border-bottom: 1px solid var(--border-glass);
  }
  .nav-links .nav-link:last-child { border-bottom: none; }
  .nav-links .nav-link.active::after { display: none; }

  .nav-actions { gap: 8px; }
  .btn-nav-login { padding: 6px 14px; font-size: 13px; }
}
</style>
