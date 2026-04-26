import { createApp } from 'vue'
import './style.css'
import './styles/markdown.css'
import App from './App.vue'
import router from './router'

// 小程序 web-view 传入的 token 自动登录
const urlParams = new URLSearchParams(window.location.search)
const mpToken = urlParams.get('mp_token')
if (mpToken) {
  localStorage.setItem('EdgeOneMall_token', mpToken)
  // 标记为小程序环境（隐藏 Navbar 等）
  document.documentElement.classList.add('in-miniprogram')
  localStorage.setItem('EdgeOneMall_mp', '1')
  // 清理 URL 中的 token 参数
  urlParams.delete('mp_token')
  const clean = urlParams.toString()
  const newUrl = window.location.pathname + (clean ? '?' + clean : '') + window.location.hash
  window.history.replaceState({}, '', newUrl)
} else if (localStorage.getItem('EdgeOneMall_mp') === '1') {
  // 页面内跳转也保持小程序标记
  document.documentElement.classList.add('in-miniprogram')
}

const app = createApp(App)
app.use(router)
app.mount('#app')
