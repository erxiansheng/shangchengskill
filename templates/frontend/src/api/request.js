const BASE_URL = '/api/v1'

function getToken() {
    return localStorage.getItem('EdgeOneMall_token')
}

export function setToken(token) {
    localStorage.setItem('EdgeOneMall_token', token)
}

export function setRefreshToken(token) {
    localStorage.setItem('EdgeOneMall_refresh_token', token)
}

export function clearTokens() {
    localStorage.removeItem('EdgeOneMall_token')
    localStorage.removeItem('EdgeOneMall_refresh_token')
    localStorage.removeItem('EdgeOneMall_user')
}

export async function request(url, options = {}) {
    const token = getToken()
    const headers = {
        ...(options.headers || {}),
    }

    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }

    // Don't set Content-Type for FormData
    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json'
    }

    let response
    try {
        response = await fetch(`${BASE_URL}${url}`, {
            ...options,
            headers,
        })
    } catch (e) {
        // Network error - backend not running
        console.warn(`[API] 网络错误 ${url}:`, e.message)
        return { code: -1, message: '无法连接到服务器，请确保后端已启动 (npm run dev)', data: null }
    }

    let data
    try {
        data = await response.json()
    } catch (e) {
        return { code: -1, message: `服务器返回非JSON响应 (${response.status})`, data: null }
    }

    // 兼容 FastAPI HTTPException 的 {detail} 格式
    if (!data.hasOwnProperty('code') && data.detail) {
        data = { code: response.status, message: data.detail, data: null }
    }

    if (response.status === 401) {
        // Try refresh
        const refreshToken = localStorage.getItem('EdgeOneMall_refresh_token')
        if (refreshToken && !url.includes('/auth/')) {
            try {
                const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: refreshToken }),
                })
                const refreshData = await refreshRes.json()
                if (refreshData.code === 0) {
                    setToken(refreshData.data.access_token)
                    setRefreshToken(refreshData.data.refresh_token)
                    // Retry original request
                    headers['Authorization'] = `Bearer ${refreshData.data.access_token}`
                    const retryRes = await fetch(`${BASE_URL}${url}`, { ...options, headers })
                    return await retryRes.json()
                }
            } catch (e) {
                // Refresh failed
            }
        }

        // ⚠️ 不要把所有 401 当成"必须登录"。
        // 公共浏览类端点（商品列表/分类/评论/单品详情等）即使后端返回 401（过期 token、
        // 服务侧缓存、token 鉴权拦截），用户也应该能匿名继续浏览，而不是被踢回 /login。
        // 仅在调用受保护的写操作 / 我的资源时，才清 token 并跳登录。
        const PUBLIC_READ_PATTERNS = [
            /^\/skills(\/|\?|$)/,            // GET 商品列表 / 详情
            /^\/categories(\/|\?|$)/,        // GET 分类
            /^\/reviews(\/|\?|$)/,           // GET 评论
            /^\/system\//,                   // GET 系统信息 / bootstrap
            /^\/captcha(\/|\?|$)/,
            /^\/models3d\//,                 // GET 首页 3D 模型
            /^\/site\//,                     // GET 站点设置
        ]
        const isPublicRead = (options.method === undefined || options.method === 'GET')
            && PUBLIC_READ_PATTERNS.some(p => p.test(url))

        if (!isPublicRead) {
            clearTokens()
            // 避免在 /login / /register 页又把自己刷回 /login，造成死循环
            const onAuthPage = /\/(login|register|oauth\/callback)\b/.test(window.location.pathname)
            if (!onAuthPage) {
                window.location.href = '/login'
            }
        }
    }

    return data
}

export function get(url, params = {}) {
    const query = new URLSearchParams()
    for (const [key, val] of Object.entries(params)) {
        if (val !== undefined && val !== null && val !== '') {
            query.append(key, val)
        }
    }
    const qs = query.toString()
    return request(`${url}${qs ? '?' + qs : ''}`)
}

export function post(url, body = {}) {
    if (body instanceof FormData) {
        return request(url, { method: 'POST', body })
    }
    return request(url, { method: 'POST', body: JSON.stringify(body) })
}

export function put(url, body = {}) {
    return request(url, { method: 'PUT', body: JSON.stringify(body) })
}

export function del(url) {
    return request(url, { method: 'DELETE' })
}

// ─── 管理员密码注入 ───
function getAdminPassword() {
    return sessionStorage.getItem('EdgeOneMall_admin_pwd') || ''
}

export function setAdminPassword(pwd) {
    sessionStorage.setItem('EdgeOneMall_admin_pwd', pwd)
}

export function clearAdminPassword() {
    sessionStorage.removeItem('EdgeOneMall_admin_pwd')
}

function adminHeaders() {
    const pwd = getAdminPassword()
    return pwd ? { 'X-Admin-Password': pwd } : {}
}

export function adminGet(url, params = {}) {
    const query = new URLSearchParams()
    for (const [key, val] of Object.entries(params)) {
        if (val !== undefined && val !== null && val !== '') query.append(key, val)
    }
    const qs = query.toString()
    return request(`${url}${qs ? '?' + qs : ''}`, { headers: adminHeaders() })
}

export function adminPost(url, body = {}) {
    if (body instanceof FormData) {
        return request(url, { method: 'POST', body, headers: adminHeaders() })
    }
    return request(url, { method: 'POST', body: JSON.stringify(body), headers: adminHeaders() })
}

export function adminPut(url, body = {}) {
    return request(url, { method: 'PUT', body: JSON.stringify(body), headers: adminHeaders() })
}

export function adminDel(url) {
    return request(url, { method: 'DELETE', headers: adminHeaders() })
}
