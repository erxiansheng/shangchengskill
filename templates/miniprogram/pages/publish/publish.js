const api = require('../../utils/api')
const { markdownToHtml } = require('../../utils/markdown')
const app = getApp()

const ERROR_SKILL_TITLE_DUPLICATE = 3005
const ERROR_PUBLISH_LIMIT_EXCEEDED = 3008

Page({
  data: {
    loggedIn: false,
    categories: [],
    form: {
      title: '',
      category_id: '',
      price: 0,
      version: '1.0.0',
      tags: '',
      subtitle: '',
      description: '',
    },
    // Upload states
    packageFile: null,
    packageFileName: '',
    packageUploaded: false,
    uploadingPackage: false,
    screenshots: [],       // temp file paths from wx.chooseImage
    screenshotUrls: [],    // uploaded URLs
    uploadingImages: false,
    submitting: false,
    previewDesc: false,
    descHtml: '',
    submitError: '',
    titleError: '',
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 })
    }
    const loggedIn = app.isLoggedIn()
    this.setData({ loggedIn })
    if (loggedIn && this.data.categories.length === 0) {
      this.loadCategories()
    }
  },

  doLogin() {
    app.wxLogin(() => {
      this.setData({ loggedIn: true })
      this.loadCategories()
    })
  },

  async loadCategories() {
    try {
      const cats = await api.get('/categories')
      const flat = (cats || []).filter(c => !c.parent_id).map(c => ({
        id: c.id, name: c.name
      }))
      this.setData({ categories: flat })
    } catch (e) { console.error('loadCats', e) }
  },

  onCategoryChange(e) {
    const idx = e.detail.value
    const cat = this.data.categories[idx]
    if (cat) this.setData({ 'form.category_id': cat.id })
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    const nextData = { [`form.${field}`]: e.detail.value }
    if (field === 'title') {
      nextData.titleError = ''
      if ((this.data.submitError || '').includes('名称')) {
        nextData.submitError = ''
      }
    }
    this.setData(nextData)
  },

  onPriceInput(e) {
    this.setData({ 'form.price': Number(e.detail.value) || 0 })
  },

  // Choose ZIP file
  chooseFile() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['zip'],
      success: (res) => {
        const file = res.tempFiles[0]
        this.setData({
          packageFile: file,
          packageFileName: file.name,
          packageUploaded: false,
        })
        this.uploadPackage(file)
      }
    })
  },

  async uploadPackage(file) {
    this.setData({ uploadingPackage: true })
    try {
      const token = wx.getStorageSync('token')
      const uploadRes = await new Promise((resolve, reject) => {
        wx.uploadFile({
          url: 'https://YOUR_DOMAIN_HERE/api/v1/upload/skill-package',
          filePath: file.path,
          name: 'file',
          header: { 'Authorization': `Bearer ${token}` },
          success: (res) => resolve(JSON.parse(res.data)),
          fail: reject,
        })
      })
      if (uploadRes.data && uploadRes.data.file_url) {
        this.setData({
          packageUploaded: true,
          uploadingPackage: false,
          'form.file_url': uploadRes.data.file_url,
          'form.file_size': uploadRes.data.file_size || file.size,
          'form.file_hash': uploadRes.data.file_hash || '',
          'form.file_tree': uploadRes.data.file_tree || [],
          'form.original_filename': file.name || '',
        })
        // Auto-fill from parsed SKILL.md if available
        if (uploadRes.data.parsed) {
          const p = uploadRes.data.parsed
          if (p.title) this.setData({ 'form.title': p.title })
          if (p.description) this.setData({ 'form.subtitle': p.description })
          if (p.version) this.setData({ 'form.version': p.version })
          if (p.tags) this.setData({ 'form.tags': p.tags.join(', ') })
        }
        wx.showToast({ title: '上传成功', icon: 'success' })
      } else {
        throw new Error(uploadRes.message || '上传失败')
      }
    } catch (e) {
      console.error('uploadPackage', e)
      this.setData({ uploadingPackage: false })
      wx.showToast({ title: '上传失败', icon: 'none' })
    }
  },

  // Choose screenshots
  chooseImages() {
    const remaining = 6 - this.data.screenshots.length
    if (remaining <= 0) return wx.showToast({ title: '最多6张', icon: 'none' })
    wx.chooseImage({
      count: remaining,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const paths = this.data.screenshots.concat(res.tempFilePaths)
        this.setData({ screenshots: paths })
      }
    })
  },

  removeScreenshot(e) {
    const idx = e.currentTarget.dataset.idx
    const arr = this.data.screenshots.slice()
    arr.splice(idx, 1)
    this.setData({ screenshots: arr })
  },

  async uploadScreenshots() {
    const token = wx.getStorageSync('token')
    const urls = []
    for (const path of this.data.screenshots) {
      try {
        const res = await new Promise((resolve, reject) => {
          wx.uploadFile({
            url: 'https://YOUR_DOMAIN_HERE/api/v1/upload/image',
            filePath: path,
            name: 'file',
            header: { 'Authorization': `Bearer ${token}` },
            success: (r) => resolve(JSON.parse(r.data)),
            fail: reject,
          })
        })
        if (res.data && res.data.url) urls.push(res.data.url)
      } catch (e) { console.error('uploadImg', e) }
    }
    return urls
  },

  async handleSubmit() {
    const { form } = this.data
    if (!form.title) return wx.showToast({ title: '请填写商品名称', icon: 'none' })
    if (!form.category_id) return wx.showToast({ title: '请选择分类', icon: 'none' })
    if (!this.data.packageUploaded) return wx.showToast({ title: '请先上传商品包', icon: 'none' })

    this.setData({ submitting: true, submitError: '', titleError: '' })
    try {
      // Upload screenshots if any
      let screenshotUrls = []
      if (this.data.screenshots.length > 0) {
        this.setData({ uploadingImages: true })
        screenshotUrls = await this.uploadScreenshots()
        this.setData({ uploadingImages: false })
      }

      const payload = {
        title: form.title,
        category_id: form.category_id,
        price: form.price || 0,
        version: form.version || '1.0.0',
        tags: form.tags ? form.tags.split(/[,，]/).map(t => t.trim()).filter(Boolean) : [],
        subtitle: form.subtitle || '',
        description: form.description || '',
        file_url: form.file_url,
        file_size: form.file_size,
        file_hash: form.file_hash || '',
        file_tree: form.file_tree || [],
        original_filename: form.original_filename || '',
        screenshots: screenshotUrls,
      }

      await api.post('/skills', payload)
      this.setData({ submitError: '', titleError: '' })
      wx.showToast({ title: '提交成功\n' + api.KV_SYNC_HINT, icon: 'none', duration: 3000 })
      setTimeout(() => {
        this.resetForm()
      }, 1500)
    } catch (e) {
      console.error('submit', e)
      const submitError = this.resolveSubmitError(e)
      this.setData({
        submitError: submitError.message,
        titleError: submitError.titleError || '',
      })
      if (submitError.showModal) {
        wx.showModal({
          title: submitError.modalTitle,
          content: submitError.modalContent,
          showCancel: false,
        })
      } else {
        wx.showToast({ title: submitError.toastMessage, icon: 'none' })
      }
    } finally {
      this.setData({ submitting: false })
    }
  },

  resolveSubmitError(error) {
    const code = Number(error && error.code ? error.code : 0)
    const rawMessage = (error && error.message ? error.message : '提交失败，请稍后重试').trim()

    if (code === ERROR_SKILL_TITLE_DUPLICATE) {
      return {
        message: rawMessage,
        titleError: '这个名称已被待审核或已上架商品占用，请换一个更具体的名称。',
        showModal: true,
        modalTitle: '商品名称重复',
        modalContent: `${rawMessage}\n\n建议在名称里补充作者名、版本号或适用场景后再提交。`,
        toastMessage: '商品名称重复',
      }
    }

    if (code === ERROR_PUBLISH_LIMIT_EXCEEDED) {
      return {
        message: rawMessage,
        showModal: true,
        modalTitle: '已达发布上限',
        modalContent: `${rawMessage}\n\n当前账号最多保留 200 个未删除商品，请先删除不需要的商品再提交。`,
        toastMessage: '已达发布上限',
      }
    }

    if (code === 9999) {
      return {
        message: rawMessage,
        showModal: false,
        toastMessage: '服务器处理失败，请稍后重试',
      }
    }

    return {
      message: rawMessage,
      showModal: false,
      toastMessage: rawMessage || '提交失败',
    }
  },

  toggleDescPreview() {
    const preview = !this.data.previewDesc
    if (preview) {
      this.setData({ previewDesc: true, descHtml: markdownToHtml(this.data.form.description || '') })
    } else {
      this.setData({ previewDesc: false })
    }
  },

  resetForm() {
    this.setData({
      form: { title: '', category_id: '', price: 0, version: '1.0.0', tags: '', subtitle: '', description: '' },
      packageFile: null, packageFileName: '', packageUploaded: false,
      screenshots: [], screenshotUrls: [],
      submitError: '', titleError: '',
    })
  },

  /** 分享给朋友 */
  onShareAppMessage() {
    return {
      title: '来大聪明商品市场发布你的 AI 商品',
      path: '/pages/index/index',
    }
  },

  /** 分享到朋友圈 */
  onShareTimeline() {
    return {
      title: '来大聪明商品市场发布你的 AI 商品',
      query: '',
    }
  },
})
