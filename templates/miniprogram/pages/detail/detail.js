const api = require('../../utils/api')
const { markdownToHtml } = require('../../utils/markdown')
const app = getApp()

/**
 * 将 ISO 8601 时间字符串转为北京时间友好格式
 * 例: 2026-04-12T11:03:59.091109+00:00 → 2026-04-12 19:03
 */
function formatTimeToBJ(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  if (isNaN(d.getTime())) return isoStr
  // 转 UTC+8
  const utc8 = new Date(d.getTime() + 8 * 3600 * 1000)
  const pad = n => String(n).padStart(2, '0')
  const year = utc8.getUTCFullYear()
  const month = pad(utc8.getUTCMonth() + 1)
  const day = pad(utc8.getUTCDate())
  const hour = pad(utc8.getUTCHours())
  const minute = pad(utc8.getUTCMinutes())
  return `${year}-${month}-${day} ${hour}:${minute}`
}

Page({
  data: {
    skill: null,
    reviews: [],
    versions: [],
    loading: true,
    purchased: false,
    favorited: false,
    isOwner: false,
    isFreeSkill: false,
    reviewPage: 1,
    reviewEnd: false,
    reviewLoading: false,
    previewImages: [],
    fileSizeText: '',
    // Content tabs (matching SkillDetail.vue)
    activeTab: 'intro',
    hasScreenshots: false,
    descHtml: '',
    // Review input
    showReviewInput: false,
    reviewRating: 5,
    reviewContent: '',
    submitting: false,
  },

  onLoad(opts) {
    this.skillId = opts.id
    this.loadDetail()
    if (app.isLoggedIn()) {
      this.checkPurchase()
      this.checkFavorite()
    }
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
    if (tab === 'reviews' && this.data.reviews.length === 0) {
      this.loadReviews()
    }
    if (tab === 'changelog' && this.data.versions.length === 0) {
      this.loadVersions()
    }
    if (tab === 'files' && !this.data.fileTree) {
      this.loadFileTree()
    }
  },

  async loadFileTree() {
    try {
      const res = await api.get(`/skills/${this.skillId}/file-tree`)
      if (res && Array.isArray(res)) {
        // flat rendering calculation
        const tree = res.map(item => {
          const parts = item.name.split('/').filter(Boolean)
          const depth = item.is_dir ? parts.length - 1 : parts.length - 1
          const basename = parts[parts.length - 1] || item.name
          let sizeText = ''
          if (!item.is_dir && item.size) {
            if (item.size < 1024) sizeText = item.size + ' B'
            else if (item.size < 1024 * 1024) sizeText = (item.size / 1024).toFixed(1) + ' KB'
            else sizeText = (item.size / 1024 / 1024).toFixed(1) + ' MB'
          }
          return { ...item, depth: Math.max(0, depth), basename, sizeText, path: item.name }
        })
        tree.sort((a,b) => a.name.localeCompare(b.name))
        this.setData({ fileTree: tree })
      } else {
        this.setData({ fileTree: [] })
      }
    } catch (e) {
      this.setData({ fileTree: [] })
    }
  },

  async loadDetail() {
    try {
      const skill = await api.get(`/skills/${this.skillId}`)
      const previewImages = []
      if (skill.screenshots) {
        skill.screenshots.forEach(s => {
          if (typeof s === 'string') previewImages.push(s)
          else if (s.url) previewImages.push(s.url)
        })
      }
      if (skill.images) {
        skill.images.forEach(s => {
          if (typeof s === 'string') previewImages.push(s)
          else if (s.url) previewImages.push(s.url)
        })
      }
      let fileSizeText = ''
      if (skill.file_size) {
        fileSizeText = skill.file_size > 1048576
          ? (skill.file_size / 1048576).toFixed(1) + ' MB'
          : Math.round(skill.file_size / 1024) + ' KB'
      }
      const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo')
      const isOwner = userInfo && String(userInfo.id) === String(skill.author_id)
      const isFreeSkill = skill.is_free || skill.price === 0
      const descHtml = markdownToHtml(skill.description || '')
      this.setData({
        skill, previewImages, fileSizeText, loading: false,
        hasScreenshots: previewImages.length > 0,
        isOwner, isFreeSkill, descHtml,
      })
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  async loadVersions() {
    try {
      const res = await api.get(`/skills/${this.skillId}/versions`)
      const list = res.items || res || []
      list.forEach(v => { v.created_at = formatTimeToBJ(v.created_at) })
      this.setData({ versions: list })
    } catch (e) { /* ignore */ }
  },

  async loadReviews(append) {
    if (this.data.reviewLoading || this.data.reviewEnd) return
    this.setData({ reviewLoading: true })
    try {
      const page = append ? this.data.reviewPage : 1
      const res = await api.get(`/skills/${this.skillId}/reviews?page=${page}&page_size=10`)
      const list = res.items || res || []
      list.forEach(r => { r.created_at = formatTimeToBJ(r.created_at) })
      this.setData({
        reviews: append ? this.data.reviews.concat(list) : list,
        reviewPage: page + 1,
        reviewEnd: list.length < 10,
        reviewLoading: false,
      })
    } catch (e) {
      this.setData({ reviewLoading: false })
    }
  },

  async checkPurchase() {
    try {
      const res = await api.get(`/purchases/${this.skillId}/check`)
      this.setData({ purchased: !!res.purchased })
    } catch (e) { /* ignore */ }
  },

  async checkFavorite() {
    try {
      const res = await api.get('/favorites?page=1&page_size=100')
      const list = res.items || res || []
      const found = list.some(f => String(f.skill_id) === String(this.skillId))
      this.setData({ favorited: found })
    } catch (e) { /* ignore */ }
  },

  previewImage(e) {
    const idx = e.currentTarget.dataset.idx
    wx.previewImage({
      current: this.data.previewImages[idx],
      urls: this.data.previewImages,
    })
  },

  async onPurchase() {
    if (!app.isLoggedIn()) await app.wxLogin()
    try {
      this.setData({ submitting: true })
      await api.post('/purchases', { skill_id: String(this.skillId) })
      wx.showToast({ title: '购买成功\n' + api.KV_SYNC_HINT, icon: 'none', duration: 3000 })
      this.setData({ purchased: true, submitting: false })
    } catch (e) {
      this.setData({ submitting: false })
      wx.showToast({ title: e.message || '购买失败', icon: 'none' })
    }
  },

  async onDownload() {
    wx.showLoading({ title: '准备下载...' })
    try {
      const res = await api.get(`/purchases/${this.skillId}/download`)
      const url = res.download_url || res.url
      if (url) {
        wx.downloadFile({
          url,
          success(r) {
            wx.hideLoading()
            if (r.statusCode === 200) {
              wx.openDocument({ filePath: r.tempFilePath, showMenu: true })
            }
          },
          fail() { wx.hideLoading(); wx.showToast({ title: '下载失败', icon: 'none' }) },
        })
      } else {
        wx.hideLoading()
        wx.showToast({ title: '暂无下载链接', icon: 'none' })
      }
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: e.message || '获取下载链接失败', icon: 'none' })
    }
  },

  async toggleFavorite() {
    if (!app.isLoggedIn()) await app.wxLogin()
    try {
      if (this.data.favorited) {
        await api.del(`/favorites/${this.skillId}`)
        this.setData({ favorited: false })
        wx.showToast({ title: '已取消收藏', icon: 'none' })
      } else {
        await api.post('/favorites', { skill_id: String(this.skillId) })
        this.setData({ favorited: true })
        wx.showToast({ title: '已收藏', icon: 'none' })
      }
    } catch (e) {
      wx.showToast({ title: e.message || '操作失败', icon: 'none' })
    }
  },

  handleInstallTabClick() {
    if (!this.data.purchased && !this.data.isOwner && !this.data.isFreeSkill) {
      wx.showToast({ title: '购买后查看安装方式', icon: 'none' })
      return
    }
    this.setData({ activeTab: 'install' })
  },

  showReview() {
    if (!app.isLoggedIn()) {
      app.wxLogin().then(() => this.setData({ showReviewInput: true }))
      return
    }
    this.setData({ showReviewInput: true })
  },

  setRating(e) { this.setData({ reviewRating: e.currentTarget.dataset.val }) },
  onReviewInput(e) { this.setData({ reviewContent: e.detail.value }) },
  cancelReview() { this.setData({ showReviewInput: false, reviewContent: '', reviewRating: 5 }) },

  async submitReview() {
    const { reviewRating, reviewContent } = this.data
    if (!reviewContent.trim()) return wx.showToast({ title: '请输入评论内容', icon: 'none' })
    this.setData({ submitting: true })
    try {
      await api.post(`/skills/${this.skillId}/reviews`, { rating: reviewRating, content: reviewContent.trim() })
      wx.showToast({ title: '评论成功\n' + api.KV_SYNC_HINT, icon: 'none', duration: 3000 })
      this.setData({ showReviewInput: false, reviewContent: '', reviewRating: 5, submitting: false })
      this.setData({ reviewPage: 1, reviewEnd: false, reviews: [] })
      this.loadReviews()
      this.loadDetail()
    } catch (e) {
      this.setData({ submitting: false })
      wx.showToast({ title: e.message || '评论失败', icon: 'none' })
    }
  },

  copyInstallCmd() {
    const s = this.data.skill
    const cmd = `请阅读 EdgeOneMall 商品市场的安装说明（https://YOUR_DOMAIN_HERE/skill.md），按照说明安装EdgeOneMall商品市场，并帮我下载或发布商品「${s.title}」(ID: ${s.id})。`
    wx.setClipboardData({
      data: cmd,
      success: () => wx.showToast({ title: '已复制安装指令', icon: 'success' })
    })
  },

  goBack() { wx.navigateBack() },

  /** 分享给朋友 */
  onShareAppMessage() {
    const s = this.data.skill
    if (s) {
      return {
        title: s.title + (s.subtitle ? ` — ${s.subtitle}` : ''),
        path: `/pages/detail/detail?id=${this.skillId}`,
        imageUrl: (this.data.previewImages && this.data.previewImages[0]) || '',
      }
    }
    return {
      title: '大聪明商品市场 — 发现精品 AI 商品',
      path: `/pages/detail/detail?id=${this.skillId}`,
    }
  },

  /** 分享到朋友圈 */
  onShareTimeline() {
    const s = this.data.skill
    return {
      title: s ? s.title + (s.subtitle ? ` — ${s.subtitle}` : '') : '大聪明商品市场',
      query: `id=${this.skillId}`,
      imageUrl: (this.data.previewImages && this.data.previewImages[0]) || '',
    }
  },
})
