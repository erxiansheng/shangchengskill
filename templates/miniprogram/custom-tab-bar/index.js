const api = require('../utils/api')

Component({
  data: {
    selected: 0,
    publishEnabled: false,
    configLoaded: false,
    fullList: [
      { pagePath: '/pages/index/index', text: '市场' },
      { pagePath: '/pages/explore/explore', text: '探索' },
      { pagePath: '/pages/publish/publish', text: '发布' },
      { pagePath: '/pages/mine/mine', text: '我的' },
    ],
    list: [
      { pagePath: '/pages/index/index', text: '市场' },
      { pagePath: '/pages/explore/explore', text: '探索' },
      { pagePath: '/pages/mine/mine', text: '我的' },
    ]
  },
  lifetimes: {
    attached() {
      this.loadPublishConfig()
    }
  },
  methods: {
    async loadPublishConfig() {
      try {
        const res = await api.get('/points/config')
        const d = res.data || res
        const enabled = d.publishEnabled !== false
        this.setData({ publishEnabled: enabled, configLoaded: true })
        this.updateList(enabled)
      } catch (e) {
        // 请求失败时保持默认（不显示发布按钮）
        this.setData({ configLoaded: true })
      }
    },
    updateList(publishEnabled) {
      const list = publishEnabled
        ? this.data.fullList
        : this.data.fullList.filter(item => item.text !== '发布')
      this.setData({ list })
    },
    switchTab(e) {
      const url = e.currentTarget.dataset.path
      wx.switchTab({ url })
    }
  }
})
