import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/skill/:id',
    name: 'SkillDetail',
    component: () => import('../views/SkillDetail.vue')
  },
  {
    path: '/upload',
    name: 'SkillUpload',
    component: () => import('../views/SkillUpload.vue')
  },
  {
    path: '/skill/:id/edit',
    name: 'SkillEdit',
    component: () => import('../views/SkillUpload.vue')
  },
  {
    path: '/profile',
    name: 'UserProfile',
    component: () => import('../views/UserProfile.vue')
  },
  {
    path: '/user/:id',
    name: 'PublicProfile',
    component: () => import('../views/PublicProfile.vue')
  },
  {
    path: '/purchased',
    name: 'Purchased',
    component: () => import('../views/Purchased.vue')
  },
  {
    path: '/points',
    name: 'Points',
    component: () => import('../views/Points.vue')
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/login/oauth-callback',
    name: 'OAuthCallback',
    component: () => import('../views/OAuthCallback.vue')
  },
  {
    path: '/favorites',
    name: 'Favorites',
    component: () => import('../views/Favorites.vue')
  },
  {
    path: '/revenue',
    name: 'Revenue',
    component: () => import('../views/Revenue.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue')
  },
  {
    path: '/about',
    name: 'About',
    component: () => import('../views/About.vue')
  },
  {
    path: '/explore',
    name: 'Explore',
    component: () => import('../views/Explore.vue')
  },
  {
    path: '/admin',
    alias: '/admin/',
    name: 'Admin',
    component: () => import('../views/Admin.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  }
})

export default router
