/**
 * API 请求封装
 */
const BASE_URL = 'https://YOUR_DOMAIN_HERE/api/v1'

function getToken() {
  return wx.getStorageSync('token') || ''
}

function request(method, path, data) {
  return new Promise((resolve, reject) => {
    const header = { 'Content-Type': 'application/json' }
    const token = getToken()
    if (token) header['Authorization'] = `Bearer ${token}`

    wx.request({
      url: BASE_URL + path,
      method,
      data,
      header,
      success(res) {
        if (res.statusCode === 401) {
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          const app = getApp()
          if (app) {
            app.globalData.token = ''
            app.globalData.userInfo = null
          }
          wx.showToast({ title: '登录已过期', icon: 'none' })
          return reject({ code: 401, message: '未登录' })
        }
        const body = res.data
        if (body && body.code === 0) {
          resolve(body.data)
        } else {
          reject(body || { message: '请求失败' })
        }
      },
      fail(err) {
        reject({ message: err.errMsg || '网络错误' })
      }
    })
  })
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  var s = String(dateStr)
  // Always use regex to extract date components — avoids new Date(string) inconsistencies across WeChat JS engines
  var m = s.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/)
  if (!m) return dateStr
  // Backend uses datetime.now(timezone.utc), so timestamps are always UTC
  var utcMs = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6])
  // Convert to Beijing time (UTC+8)
  var bj = new Date(utcMs + 8 * 3600000)
  var pad = function(n) { return n < 10 ? '0' + n : '' + n }
  return bj.getUTCFullYear() + '-' + pad(bj.getUTCMonth() + 1) + '-' + pad(bj.getUTCDate()) + ' ' + pad(bj.getUTCHours()) + ':' + pad(bj.getUTCMinutes())
}

/** KV 数据同步延迟提示 */
const KV_SYNC_HINT = '数据同步可能有 1~60 秒延迟，请勿重复提交'

module.exports = {
  get: (path, data) => request('GET', path, data),
  post: (path, data) => request('POST', path, data),
  put: (path, data) => request('PUT', path, data),
  patch: (path, data) => request('PATCH', path, data),
  del: (path, data) => request('DELETE', path, data),
  getToken,
  formatDate,
  BASE_URL,
  KV_SYNC_HINT,
}
