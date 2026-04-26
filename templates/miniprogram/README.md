# EdgeOneMall 微信小程序

基于 web-view 方案的微信小程序，内嵌现有 Web 应用。

## 使用方式

1. 下载安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开微信开发者工具，导入 `miniprogram/` 目录作为项目
3. 在 `project.config.json` 中填入你的小程序 AppID

## 后台配置

在管理后台「站点设置」中添加以下配置：

| 配置项 | 说明 |
|--------|------|
| `wxMiniAppId` | 微信小程序 AppID |
| `wxMiniAppSecret` | 微信小程序 AppSecret |

## 域名配置

在微信小程序管理后台 → 开发管理 → 开发设置 → 服务器域名中配置：

- **request 合法域名**: `https://YOUR_DOMAIN_HERE`
- **业务域名（web-view）**: `https://YOUR_DOMAIN_HERE`

> 业务域名验证：需要将微信提供的验证文件放到网站根目录。

## 工作原理

- **首页** (`pages/index/index`)：原生小程序页面，提供微信一键登录
- **web-view** (`pages/webview/webview`)：登录后通过 web-view 加载完整的 Web 应用
- 登录 token 通过 URL 参数 `mp_token` 传递给 web-view 内的页面
- Web 端自动检测 `mp_token` 并存入 localStorage 完成登录态同步

## 后续优化建议

如需更原生的小程序体验，可考虑使用 [uni-app](https://uniapp.dcloud.io/) 或 [Taro](https://taro.jd.com/) 重写前端。
