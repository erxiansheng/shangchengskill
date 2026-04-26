import { reactive } from 'vue'

function getTimeBasedTheme() {
    const hour = new Date().getHours()
    // 白天 7:00-18:59 使用亮色主题，其余时间使用暗色主题
    return (hour >= 7 && hour < 19) ? 'light' : 'dark'
}

export const themeStore = reactive({
    // 如果用户从未手动切换过主题，则根据时间自动决定
    theme: localStorage.getItem('EdgeOneMall_theme') || getTimeBasedTheme(),

    get isDark() {
        return this.theme === 'dark'
    },

    toggle() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark'
        localStorage.setItem('EdgeOneMall_theme', this.theme)
        this.apply()
    },

    apply() {
        document.documentElement.setAttribute('data-theme', this.theme)
    },

    init() {
        // 如果没有手动设置，每次初始化时根据时间重新判断
        if (!localStorage.getItem('EdgeOneMall_theme')) {
            this.theme = getTimeBasedTheme()
        }
        this.apply()
    }
})

// Apply theme IMMEDIATELY at module load to prevent flash
themeStore.apply()
