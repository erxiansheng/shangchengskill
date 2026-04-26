const api = require('../../utils/api')

Page({
  data: {
    keyword: '',
    categories: [],
    activeCat: '',
    sortBy: 'hot',
    priceFilter: '',
    ratingFilter: '',
    skills: [],
    loading: false,
    noMore: false,
    page: 1,
    pageSize: 10,
    showFilter: false,
  },

  onLoad(options) {
    if (options.keyword) this.setData({ keyword: options.keyword })
    this.loadCategories()
    this.loadSkills()
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 })
    }
  },

  onReachBottom() {
    if (!this.data.noMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 })
      this.loadSkills(true)
    }
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

  async loadSkills(append) {
    if (this.data.loading) return
    this.setData({ loading: true })
    try {
      const params = {
        page: this.data.page,
        page_size: this.data.pageSize,
        sort: this.data.sortBy,
      }
      if (this.data.keyword) params.keyword = this.data.keyword
      if (this.data.activeCat) params.category_id = this.data.activeCat
      if (this.data.priceFilter === 'free') params.is_free = 1
      if (this.data.priceFilter === 'paid') params.is_free = 0
      if (this.data.priceFilter === 'low') { params.price_min = 1; params.price_max = 100 }
      if (this.data.priceFilter === 'mid') { params.price_min = 100; params.price_max = 500 }
      if (this.data.ratingFilter === '5') params.min_rating = 5
      if (this.data.ratingFilter === '4') params.min_rating = 4

      const res = await api.get('/skills', params)
      const items = res.items || res || []
      const newSkills = append ? this.data.skills.concat(items) : items
      this.setData({
        skills: newSkills,
        noMore: items.length < this.data.pageSize,
        loading: false,
      })
    } catch (e) {
      console.error('loadSkills', e)
      this.setData({ loading: false })
    }
  },

  resetAndLoad() {
    this.setData({ page: 1, noMore: false, skills: [] })
    this.loadSkills()
  },

  onSearchInput(e) { this.setData({ keyword: e.detail.value }) },
  doSearch() { this.resetAndLoad() },
  clearSearch() { this.setData({ keyword: '' }); this.resetAndLoad() },

  selectCat(e) {
    const id = e.currentTarget.dataset.id || ''
    this.setData({ activeCat: id, showFilter: false })
    this.resetAndLoad()
  },

  setSort(e) {
    this.setData({ sortBy: e.currentTarget.dataset.sort })
    this.resetAndLoad()
  },

  setPrice(e) {
    this.setData({ priceFilter: e.currentTarget.dataset.price || '', showFilter: false })
    this.resetAndLoad()
  },

  setRating(e) {
    this.setData({ ratingFilter: e.currentTarget.dataset.rating || '', showFilter: false })
    this.resetAndLoad()
  },

  toggleFilter() { this.setData({ showFilter: !this.data.showFilter }) },
  closeFilter() { this.setData({ showFilter: false }) },

  goDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}` })
  },

  /** 分享给朋友 */
  onShareAppMessage() {
    return {
      title: '探索 AI 商品 — 大聪明商品市场',
      path: '/pages/explore/explore',
    }
  },

  /** 分享到朋友圈 */
  onShareTimeline() {
    return {
      title: '探索 AI 商品 — 大聪明商品市场',
      query: '',
    }
  },
})
