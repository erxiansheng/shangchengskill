App({
  globalData: {
    userInfo: null,
    token: '',
  },

  onLaunch() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
  },

  /** 微信登录 */
  wxLogin() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (res) => {
          if (!res.code) return reject(new Error('wx.login 失败'))
          const api = require('./utils/api')
          api.post('/auth/wechat/miniprogram', { code: res.code })
            .then(data => {
              this.globalData.token = data.access_token
              this.globalData.userInfo = data.user
              wx.setStorageSync('token', data.access_token)
              wx.setStorageSync('userInfo', data.user)
              resolve(data)
            })
            .catch(reject)
        },
        fail: reject,
      })
    })
  },

  logout() {
    this.globalData.token = ''
    this.globalData.userInfo = null
    wx.removeStorageSync('token')
    wx.removeStorageSync('userInfo')
  },

  isLoggedIn() {
    return !!this.globalData.token
  },
})
