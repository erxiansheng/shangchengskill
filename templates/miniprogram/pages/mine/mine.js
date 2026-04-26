const api = require('../../utils/api')
const levels = require('../../utils/levels')
const app = getApp()

Page({
  data: {
    logged: false,
    agreedPolicy: false,
    user: null,
    balance: 0,
    totalEarned: 0,
    totalSpent: 0,
    // Section switching (matches UserProfile.vue sidebar)
    activeSection: 'skills',
    mySkills: [],
    mySkillsTotal: 0,
    favorites: [],
    purchases: [],
    revenueRecords: [],
    sectionLoading: false,
    purchaseCount: 0,
    favoritesTotal: 0,
    statusMap: { pending: '审核中', approved: '已上架', rejected: '已驳回', offline: '已下架' },
    // Pagination
    pageSize: 10,
    skillsPage: 1, skillsTotalPages: 1,
    favoritesPage: 1, favoritesTotalPages: 1,
    purchasedPage: 1, purchasedTotalPages: 1,
    revenuePage: 1, revenueTotalPages: 1,
    recordsPage: 1, recordsTotalPages: 1,
    // Points (充值与流水)
    packages: [],
    records: [],
    selectedPkg: 2,
    paying: false,
    rechargeEnabled: true,
    // Tokens (秘钥管理)
    tokens: [],
    showCreateToken: false,
    newTokenName: '',
    newTokenScopes: ['skill:read', 'skill:purchase', 'skill:download'],
    scopeSelected: {
      'skill:read': true,
      'skill:publish': false,
      'skill:update': false,
      'skill:purchase': true,
      'skill:download': true,
    },
    createdToken: '',
    availableScopes: [
      { key: 'skill:read', label: '浏览商品市场' },
      { key: 'skill:publish', label: '发布新商品' },
      { key: 'skill:update', label: '更新/删除商品' },
      { key: 'skill:purchase', label: '购买商品' },
      { key: 'skill:download', label: '下载商品包' },
    ],
    // 个人信息编辑
    showEditProfile: false,
    editNickname: '',
    editBio: '',
    editAvatarUrl: '',
    savingProfile: false,
    levelInfo: null,
    showLevelPopup: false,
    levelList: levels.LEVELS || [],
    levelProgressPct: 0,
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      const tabBar = this.getTabBar()
      const idx = (tabBar.data.list || []).findIndex(t => t.text === '我的')
      tabBar.setData({ selected: idx >= 0 ? idx : 3 })
    }
    // 同步 storage 与 globalData（401 时 storage 已被清除）
    const tokenInStorage = wx.getStorageSync('token')
    if (!tokenInStorage && app.globalData.token) {
      app.globalData.token = ''
      app.globalData.userInfo = null
    }
    this.setData({ logged: app.isLoggedIn() })
    this.loadRechargeConfig()
    if (app.isLoggedIn()) {
      this.loadProfile()
      this.loadBalance()
      this.loadStatsSummary()
      this.loadSection()
    }
  },

  onPullDownRefresh() {
    if (app.isLoggedIn()) {
      this.loadProfile()
      this.loadBalance()
      this.loadStatsSummary()
      this.loadSection()
    }
    wx.stopPullDownRefresh()
  },

  togglePolicy() {
    this.setData({ agreedPolicy: !this.data.agreedPolicy })
  },

  openPrivacyContract() {
    wx.openPrivacyContract({
      success: () => {
        console.log('openPrivacyContract success')
      },
      fail: (err) => {
        console.error('openPrivacyContract fail', err)
      }
    })
  },

  async doLogin() {
    if (!this.data.agreedPolicy) {
      wx.showToast({ title: '请先阅读并同意用户隐私保护指引', icon: 'none' })
      return
    }
    wx.showLoading({ title: '登录中...' })
    try {
      await app.wxLogin()
      this.setData({ logged: true })
      this.loadProfile()
      this.loadBalance()
      this.loadSection()
      wx.hideLoading()
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '登录失败', icon: 'none' })
    }
  },

  async loadRechargeConfig() {
    try {
      const res = await api.get('/points/config')
      const d = res.data || res
      this.setData({ rechargeEnabled: d.rechargeEnabled !== false })
      // 加载远程等级配置
      if (d.levels && d.levels.length) {
        levels.setRemoteLevels(d.levels)
        this.setData({ levelList: d.levels })
      }
    } catch (e) { /* default true */ }
  },

  async loadProfile() {
    try {
      const user = await api.get('/users/me')
      app.globalData.userInfo = user
      wx.setStorageSync('userInfo', user)
      // Compute level info
      const levelInfo = user.level_info || levels.getLevelInfo(user.exp || 0)
      this.setData({ user, levelInfo })
    } catch (e) {
      if (e && e.code === 401) {
        this.setData({ logged: false, user: null })
      }
    }
  },

  async loadBalance() {
    try {
      const res = await api.get('/points/balance')
      this.setData({
        balance: res.balance || 0,
        totalEarned: res.total_earned || 0,
        totalSpent: res.total_spent || 0,
      })
    } catch (e) { /* ignore */ }
  },

  // 加载顶部 stats 汇总（发布商品数、已购商品数、收藏数），与具体 section 无关
  async loadStatsSummary() {
    try {
      const [skillsRes, purRes, favRes] = await Promise.all([
        api.get('/skills/my?page=1&page_size=1').catch(() => ({})),
        api.get('/purchases?page=1&page_size=1').catch(() => ({})),
        api.get('/favorites?page=1&page_size=1').catch(() => ({})),
      ])
      this.setData({
        mySkillsTotal: skillsRes.total || this.data.mySkillsTotal || 0,
        purchaseCount: purRes.total || this.data.purchaseCount || 0,
        favoritesTotal: favRes.total || this.data.favoritesTotal || 0,
      })
    } catch (e) { /* ignore */ }
  },

  switchSection(e) {
    const section = e.currentTarget.dataset.section
    if (section === this.data.activeSection) return
    // Reset page number for new section
    const resetMap = { skills: 'skillsPage', favorites: 'favoritesPage', purchased: 'purchasedPage', revenue: 'revenuePage', points: 'recordsPage' }
    const key = resetMap[section]
    this.setData({ activeSection: section, ...(key ? { [key]: 1 } : {}) })
    this.loadSection()
  },

  async loadSection() {
    const section = this.data.activeSection
    this.setData({ sectionLoading: true })
    const ps = this.data.pageSize
    try {
      if (section === 'skills') {
        const p = this.data.skillsPage
        const res = await api.get(`/skills/my?page=${p}&page_size=${ps}`)
        this.setData({
          mySkills: res.items || res || [],
          mySkillsTotal: res.total || 0,
          skillsTotalPages: res.total_pages || 1,
        })
      } else if (section === 'favorites') {
        const p = this.data.favoritesPage
        const res = await api.get(`/favorites?page=${p}&page_size=${ps}`)
        this.setData({ favorites: res.items || res || [], favoritesTotal: res.total || 0, favoritesTotalPages: res.total_pages || 1 })
      } else if (section === 'purchased') {
        const p = this.data.purchasedPage
        const res = await api.get(`/purchases?page=${p}&page_size=${ps}`)
        const items = res.items || res || []
        this.setData({ purchases: items, purchaseCount: res.total || items.length, purchasedTotalPages: res.total_pages || 1 })
      } else if (section === 'revenue') {
        const p = this.data.revenuePage
        const res = await api.get(`/points/records?type=earning&page=${p}&page_size=${ps}`)
        const items = (res.items || res || []).map(r => ({ ...r, created_at: api.formatDate(r.created_at) }))
        this.setData({ revenueRecords: items, revenueTotalPages: res.total_pages || 1 })
      } else if (section === 'points') {
        const p = this.data.recordsPage
        const [pkgRes, recRes] = await Promise.all([
          api.get('/points/packages').catch(() => ({ data: [] })),
          api.get(`/points/records?page=${p}&page_size=${ps}`).catch(() => ({ items: [] })),
        ])
        this.setData({
          packages: pkgRes.packages || pkgRes.data || pkgRes || [],
          records: (recRes.items || recRes || []).map(r => ({ ...r, created_at: api.formatDate(r.created_at) })),
          recordsTotalPages: recRes.total_pages || 1,
        })
      } else if (section === 'tokens') {
        const res = await api.get('/tokens')
        const tokens = (res.data || res || []).map(t => ({ ...t, created_at: api.formatDate(t.created_at) }))
        this.setData({ tokens, createdToken: '' })
      }
    } catch (e) { console.error('loadSection', e) }
    this.setData({ sectionLoading: false })
  },

  prevPage() {
    const section = this.data.activeSection
    const keyMap = { skills: 'skillsPage', favorites: 'favoritesPage', purchased: 'purchasedPage', revenue: 'revenuePage', points: 'recordsPage' }
    const key = keyMap[section]
    if (!key || this.data[key] <= 1) return
    this.setData({ [key]: this.data[key] - 1 })
    this.loadSection()
  },

  nextPage() {
    const section = this.data.activeSection
    const keyMap = { skills: 'skillsPage', favorites: 'favoritesPage', purchased: 'purchasedPage', revenue: 'revenuePage', points: 'recordsPage' }
    const tpMap = { skills: 'skillsTotalPages', favorites: 'favoritesTotalPages', purchased: 'purchasedTotalPages', revenue: 'revenueTotalPages', points: 'recordsTotalPages' }
    const key = keyMap[section]
    const tpKey = tpMap[section]
    if (!key || this.data[key] >= this.data[tpKey]) return
    this.setData({ [key]: this.data[key] + 1 })
    this.loadSection()
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}` })
  },

  goPublish() {
    wx.switchTab({ url: '/pages/publish/publish' })
  },

  goExplore() {
    wx.switchTab({ url: '/pages/explore/explore' })
  },

  goPoints() {
    this.setData({ activeSection: 'points' })
    this.loadSection()
  },

  selectPkg(e) {
    this.setData({ selectedPkg: e.currentTarget.dataset.idx })
  },

  async handlePay() {
    const pkg = this.data.packages[this.data.selectedPkg]
    if (!pkg || this.data.paying) return
    this.setData({ paying: true })
    try {
      const res = await api.post('/points/recharge', {
        amount_yuan: pkg.amount_yuan,
        payment_method: 'wechat',
        client_type: 'miniprogram',
      })
      const d = res.data || res
      if (d.points_added) {
        wx.showToast({ title: `充值成功！+${d.points_added} 积分\n` + api.KV_SYNC_HINT, icon: 'none', duration: 3000 })
        this.loadBalance()
        this.loadSection()
      } else if (d.pay_type === 'jsapi' && d.jsapi_params) {
        // Mini-program JSAPI payment
        const params = d.jsapi_params
        const orderNo = d.order_no
        wx.requestPayment({
          timeStamp: params.timeStamp,
          nonceStr: params.nonceStr,
          package: params.package,
          signType: params.signType,
          paySign: params.paySign,
          success: () => {
            wx.showToast({ title: '支付成功，积分到账中...', icon: 'none', duration: 3000 })
            // Poll for payment confirmation
            this._pollPaymentStatus(orderNo)
          },
          fail: (err) => {
            if (err.errMsg && err.errMsg.indexOf('cancel') >= 0) {
              wx.showToast({ title: '已取消支付', icon: 'none' })
            } else {
              wx.showToast({ title: '支付失败', icon: 'none' })
            }
          },
        })
      } else if (d.qr_url) {
        wx.showToast({ title: '请在网页端扫码完成支付', icon: 'none' })
      }
    } catch (e) {
      wx.showToast({ title: e.message || '充值失败', icon: 'none' })
    }
    this.setData({ paying: false })
  },

  _pollPaymentStatus(orderNo, retries = 0) {
    if (retries >= 10) {
      wx.showToast({ title: '积分稍后到账，请刷新查看', icon: 'none' })
      return
    }
    setTimeout(async () => {
      try {
        const res = await api.get(`/points/recharge/${orderNo}/status`)
        const d = res.data || res
        if (d.status === 'paid') {
          wx.showToast({ title: `充值成功！+${d.points_amount} 积分`, icon: 'none', duration: 3000 })
          this.loadBalance()
          this.loadSection()
        } else {
          this._pollPaymentStatus(orderNo, retries + 1)
        }
      } catch (e) {
        this._pollPaymentStatus(orderNo, retries + 1)
      }
    }, 2000)
  },

  // ---- Token management ----
  toggleCreateToken() {
    const defaults = ['skill:read', 'skill:purchase', 'skill:download']
    const defaultMap = {
      'skill:read': true, 'skill:publish': false, 'skill:update': false,
      'skill:purchase': true, 'skill:download': true,
    }
    this.setData({
      showCreateToken: !this.data.showCreateToken,
      createdToken: '',
      newTokenName: '',
      newTokenScopes: defaults,
      scopeSelected: defaultMap,
    })
  },

  onTokenNameInput(e) {
    this.setData({ newTokenName: e.detail.value })
  },

  toggleScope(e) {
    const scope = e.currentTarget.dataset.scope
    const scopes = [...this.data.newTokenScopes]
    const map = Object.assign({}, this.data.scopeSelected)
    const idx = scopes.indexOf(scope)
    if (idx >= 0) {
      scopes.splice(idx, 1)
      map[scope] = false
    } else {
      scopes.push(scope)
      map[scope] = true
    }
    this.setData({ newTokenScopes: scopes, scopeSelected: map })
  },

  async createToken() {
    if (!this.data.newTokenName.trim()) {
      return wx.showToast({ title: '请输入令牌名称', icon: 'none' })
    }
    if (this.data.newTokenScopes.length === 0) {
      return wx.showToast({ title: '至少选择一个权限', icon: 'none' })
    }
    try {
      const res = await api.post('/tokens', {
        name: this.data.newTokenName.trim(),
        scopes: this.data.newTokenScopes,
        expires_in_days: 90,
      })
      const d = res.data || res
      // Add to local state directly to avoid KV eventual consistency delay
      const newToken = {
        id: d.id, name: d.name, scopes: d.scopes,
        is_active: d.is_active, created_at: api.formatDate(d.created_at),
        expires_at: d.expires_at, last_used: d.last_used,
      }
      const tokens = [newToken, ...this.data.tokens]
      this.setData({
        createdToken: d.token || '',
        showCreateToken: false,
        newTokenName: '',
        newTokenScopes: ['skill:read', 'skill:purchase', 'skill:download'],
        scopeSelected: {
          'skill:read': true, 'skill:publish': false, 'skill:update': false,
          'skill:purchase': true, 'skill:download': true,
        },
        tokens,
      })
    } catch (e) {
      wx.showToast({ title: '创建失败', icon: 'none' })
    }
  },

  copyToken() {
    wx.setClipboardData({
      data: this.data.createdToken,
      success: () => wx.showToast({ title: '已复制', icon: 'success' }),
    })
  },

  async toggleToken(e) {
    const id = e.currentTarget.dataset.id
    try {
      const res = await api.patch(`/tokens/${id}/toggle`)
      const d = res.data || res
      const tokens = this.data.tokens.map(t =>
        t.id === id ? { ...t, is_active: d.is_active } : t
      )
      this.setData({ tokens })
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  revokeToken(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认删除',
      content: '删除后无法恢复，确定删除此令牌？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.del(`/tokens/${id}`)
            const tokens = this.data.tokens.filter(t => t.id !== id)
            this.setData({ tokens })
          } catch (e) {
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      },
    })
  },

  async handleDownload(e) {
    const skillId = e.currentTarget.dataset.skillid
    try {
      const res = await api.get(`/purchases/${skillId}/download`)
      if (res.download_url) {
        wx.downloadFile({
          url: res.download_url,
          success: (dlRes) => {
            wx.openDocument({ filePath: dlRes.tempFilePath })
          }
        })
      }
    } catch (e) {
      wx.showToast({ title: '下载失败', icon: 'none' })
    }
  },

  // ---- 等级说明 ----
  showLevelTip() {
    const info = this.data.levelInfo || levels.getLevelInfo(0)
    let pct = 0
    if (info.next_level) {
      const activeLvs = levels.getActiveLevels()
      const prev = activeLvs.find(l => l.level === info.level)
      const prevExp = prev ? prev.min_exp : 0
      pct = Math.min(100, Math.round((info.exp - prevExp) / (info.next_level.min_exp - prevExp) * 100))
    } else {
      pct = 100
    }
    this.setData({ showLevelPopup: true, levelProgressPct: pct })
  },

  closeLevelPopup() {
    this.setData({ showLevelPopup: false })
  },

  // ---- 个人信息编辑 ----
  openEditProfile() {
    const user = this.data.user || {}
    this.setData({
      showEditProfile: true,
      editNickname: user.nickname || '',
      editBio: user.bio || '',
      editAvatarUrl: user.avatar_url || '',
    })
  },

  closeEditProfile() {
    this.setData({ showEditProfile: false })
  },

  onEditNicknameInput(e) {
    this.setData({ editNickname: e.detail.value })
  },

  onEditBioInput(e) {
    this.setData({ editBio: e.detail.value })
  },

  onChooseAvatar(e) {
    const avatarUrl = e.detail.avatarUrl
    if (avatarUrl) {
      this.setData({ editAvatarUrl: avatarUrl })
    }
  },

  chooseAvatarFromAlbum() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFiles[0].tempFilePath
        this.setData({ editAvatarUrl: tempFilePath })
      },
    })
  },

  async uploadAvatarFile(filePath) {
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: api.BASE_URL + '/upload/image',
        filePath: filePath,
        name: 'file',
        header: { 'Authorization': 'Bearer ' + api.getToken() },
        success: (res) => {
          try {
            const body = JSON.parse(res.data)
            if (body && body.code === 0 && body.data && body.data.url) {
              resolve(body.data.url)
            } else {
              reject(new Error(body.message || '上传失败'))
            }
          } catch (e) {
            reject(new Error('解析上传结果失败'))
          }
        },
        fail: reject,
      })
    })
  },

  async saveProfile() {
    if (this.data.savingProfile) return
    this.setData({ savingProfile: true })
    try {
      let avatarUrl = this.data.editAvatarUrl
      // 如果是临时文件路径（来自chooseAvatar或chooseMedia），先上传
      if (avatarUrl && (avatarUrl.startsWith('wxfile://') || avatarUrl.startsWith('http://tmp') || avatarUrl.startsWith('/tmp'))) {
        wx.showLoading({ title: '上传头像...' })
        avatarUrl = await this.uploadAvatarFile(avatarUrl)
        wx.hideLoading()
      }
      const updateData = {
        nickname: this.data.editNickname.trim() || undefined,
        bio: this.data.editBio.trim(),
        avatar_url: avatarUrl || undefined,
      }
      const user = await api.put('/users/me', updateData)
      app.globalData.userInfo = user
      wx.setStorageSync('userInfo', user)
      this.setData({ user, showEditProfile: false })
      wx.showToast({ title: '保存成功', icon: 'success' })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: e.message || '保存失败', icon: 'none' })
    }
    this.setData({ savingProfile: false })
  },

  // 头像区域点击
  onAvatarTap() {
    if (!app.isLoggedIn()) {
      this.doLogin()
      return
    }
    this.openEditProfile()
  },

  onAvatarLoadError() {
    // 头像加载失败时清除 avatar_url 以显示占位符
    const user = this.data.user
    if (user) {
      this.setData({ 'user.avatar_url': '' })
    }
  },

  doLogout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          app.logout()
          this.setData({
            logged: false, user: null, balance: 0,
            mySkills: [], favorites: [], purchases: [], revenueRecords: [],
          })
        }
      },
    })
  },

  formatDate(ts) {
    if (!ts) return '--'
    const d = new Date(typeof ts === 'number' ? ts * 1000 : ts)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
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
