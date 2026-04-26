import { reactive } from 'vue'
import { setToken, setRefreshToken, clearTokens } from '../api/request.js'

export const userStore = reactive({
    isLoggedIn: !!localStorage.getItem('EdgeOneMall_token'),
    user: JSON.parse(localStorage.getItem('EdgeOneMall_user') || 'null'),
    unreadCount: 0,

    setUser(data) {
        this.user = data.user
        this.isLoggedIn = true
        setToken(data.access_token)
        setRefreshToken(data.refresh_token)
        localStorage.setItem('EdgeOneMall_user', JSON.stringify(data.user))
    },

    updateUser(user) {
        this.user = { ...this.user, ...user }
        localStorage.setItem('EdgeOneMall_user', JSON.stringify(this.user))
    },

    logout() {
        this.user = null
        this.isLoggedIn = false
        this.unreadCount = 0
        clearTokens()
    },

    setUnreadCount(count) {
        this.unreadCount = count
    }
})
