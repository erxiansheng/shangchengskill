import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import '../src/style.css'
import '../src/styles/markdown.css'

// Independent router for the /admin sub-app. Each panel that originally
// lived as a tab inside the monolithic Admin.vue is now its own page so
// the management surface can be deep-linked, bookmarked and code-split.
const routes = [
  { path: '/admin/login',         component: () => import('./views/AdminLogin.vue') },
  { path: '/admin',               redirect: '/admin/dashboard' },
  { path: '/admin/dashboard',     component: () => import('./views/Dashboard.vue') },
  { path: '/admin/users',         component: () => import('./views/Users.vue') },
  { path: '/admin/products',      component: () => import('./views/Products.vue') },
  { path: '/admin/audit',         component: () => import('./views/Audit.vue') },
  { path: '/admin/reviews',       component: () => import('./views/Reviews.vue') },
  { path: '/admin/orders',        component: () => import('./views/Orders.vue') },
  { path: '/admin/recharges',     component: () => import('./views/Recharges.vue') },
  { path: '/admin/withdrawals',   component: () => import('./views/Withdrawals.vue') },
  { path: '/admin/models3d',      component: () => import('./views/Models3D.vue') },
  { path: '/admin/settings',      component: () => import('./views/Settings.vue') },
  { path: '/admin/backup',        component: () => import('./views/Backup.vue') },
]

const router = createRouter({ history: createWebHistory(), routes })

// Auth guard: every route except /admin/login requires a stored admin
// token (separate scope from the storefront user token).
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('edgeone_mall_admin_token')
  if (to.path !== '/admin/login' && !token) return next('/admin/login')
  if (to.path === '/admin/login' && token) return next('/admin/dashboard')
  next()
})

createApp(App).use(router).mount('#admin-app')
