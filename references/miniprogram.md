# WeChat Miniprogram

`templates/miniprogram/` 是与 Web 端**共用 REST API** 的原生小程序实现。

## 关键文件

| 文件 | 说明 |
|---|---|
| `app.json` | 全局路由（5 主页 tab：首页/广场/发布/我的/购物车） |
| `app.miniapp.json` | 多端编译模式配置 |
| `utils/api.js` | 包装 `wx.request`，统一加 token + base url |
| `utils/levels.js` | 与 Web 端 `src/utils/levels.js` 同源 |
| `pages/` | index / explore / detail / mine / publish / webview |
| `custom-tab-bar/` | 与 Web 风格一致的霓虹 tab bar |

## API base 配置

`utils/api.js` 顶部：

```js
const BASE_URL = 'https://YOUR_DOMAIN_HERE/api/v1'
```

部署后必须替换为真实域名。Token 复用 `wx.getStorageSync('edgeone_mall_user_token')`。

## 不实现的能力

- **不实现**小程序版的后台管理（后台只有 Web）
- **不实现**3D 模型展示（小程序 webview 体验差，首页用静态封面替代）
- **不实现**OAuth 三方登录跳转（小程序原生用 `wx.login` 获取 code 调
  `/auth/oauth/wechat`）

## webview 兜底

`pages/webview/` 用于嵌入文章 / 帮助中心等纯 H5 页面，URL 必须配置在小程序后台
「业务域名」白名单中。
