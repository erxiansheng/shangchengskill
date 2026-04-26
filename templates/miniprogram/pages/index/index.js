const api = require('../../utils/api')

Page({
  data: {
    // Hero
    platforms: [
      { icon: '🦞', name: 'EdgeOneMall' },
      { icon: '🐉', name: 'QClaw' },
      { icon: '⛵', name: 'ArkClaw' },
      { icon: '🐾', name: 'CoPaw' },
      { icon: '🦁', name: 'MaxClaw' },
      { icon: '⚡', name: 'AutoClaw' },
      { icon: '📜', name: 'JVSClaw' },
      { icon: '🤖', name: 'LobsterAI' },
      { icon: '🎯', name: 'EasyClaw' },
    ],
    // Rankings
    hotFreeSkills: [],
    hotPaidSkills: [],
    // Categories
    categories: [],
    activeCategory: '',
    // Skills
    skills: [],
    loading: false,
  },

  onLoad() {
    this.loadRankings()
    this.loadCategories()
    this.loadSkills()
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 })
    }
  },

  onPullDownRefresh() {
    this.loadRankings()
    this.loadSkills()
    wx.stopPullDownRefresh()
  },

  async loadRankings() {
    try {
      const freeRes = await api.get('/skills?sort=hot&is_free=1&page_size=5')
      const paidRes = await api.get('/skills?sort=hot&is_free=0&page_size=5')
      this.setData({
        hotFreeSkills: (freeRes.items || freeRes || []).slice(0, 5),
        hotPaidSkills: (paidRes.items || paidRes || []).slice(0, 5),
      })
    } catch (e) { console.error('loadRankings', e) }
  },

  async loadCategories() {
    try {
      const cats = await api.get('/categories')
      const flat = (cats || []).filter(c => !c.parent_id).map(c => ({
        id: c.id, name: c.name, icon: c.icon || '📦'
      }))
      this.setData({ categories: flat })
    } catch (e) { console.error('loadCategories', e) }
  },

  async loadSkills() {
    this.setData({ loading: true })
    try {
      const params = { page: 1, page_size: 8, sort: 'hot' }
      if (this.data.activeCategory) params.category_id = this.data.activeCategory
      const res = await api.get('/skills', params)
      this.setData({ skills: res.items || res || [], loading: false })
    } catch (e) {
      this.setData({ loading: false })
    }
  },

  selectCat(e) {
    const id = e.currentTarget.dataset.id || ''
    this.setData({ activeCategory: id })
    this.loadSkills()
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}` })
  },

  goExplore() {
    wx.switchTab({ url: '/pages/explore/explore' })
  },

  goPublish() {
    wx.switchTab({ url: '/pages/publish/publish' })
  },

  copyInstruction() {
    const text = '请阅读 EdgeOneMall 商品市场的安装说明（https://YOUR_DOMAIN_HERE/skill.md），按照说明安装EdgeOneMall商品市场，并帮我下载或发布商品'
    wx.setClipboardData({
      data: text,
      success: () => wx.showToast({ title: '已复制', icon: 'success' })
    })
  },

  /** 分享给朋友 */
  onShareAppMessage() {
    return {
      title: '大聪明商品市场 — 发现、下载、交易 AI 商品',
      path: '/pages/index/index',
    }
  },

  /** 分享到朋友圈 */
  onShareTimeline() {
    return {
      title: '大聪明商品市场 — 发现、下载、交易 AI 商品',
      query: '',
    }
  },
})
