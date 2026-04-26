# EdgeOne Mall — 纯 Prompt 版

> **直接把这份 Prompt 原样粘给任意通用 AI 编码 Agent**，让它在腾讯 EdgeOne
> Pages 上交付一个完整的、霓虹赛博风格的在线商城——**无需**配套的
> `edgeone-mall` Skill。

---

## ⚙️ 启动指令（粘到你的 Agent 里）

```
Install this skill: npx skills add TencentEdgeOne/edgeone-pages-skills,
then deploy to EdgeOne Pages.

按照下面的规格搭建一个完整的全栈在线商城，名字叫 "{{MALL_NAME}}"。
不要自由发挥样式或技术栈——所有约束必须 1:1 严格执行。
```

---

## 🎯 目标

产出**一个仓库**，包含：

1. 一个 **Vue 3 + Vite** 用户端（入口 `/index.html`）。
2. 一个 **独立** 的 Vue 3 后台控制台（入口 `/admin/index.html`，**不是**
   主应用里的 tab——必须是完全分离的子应用，挂载在 `/admin/*` 下）。
3. 一个部署在 EdgeOne Pages 的 **FastAPI** Python Cloud Function
   （`fn/[[default]].py` 文件系统路由，统一挂载在 `/api/v1` 下）。
4. 一个 **Edge Function**（`api/[[default]].js`），代理到 KV 并注入 JWT 校验。
5. 一个共享同一套 REST API 的 **微信小程序**。
6. **分块 KV 存储**作为默认存储（不需要 S3），后台可开关切换到 S3。

---

## 🧱 技术栈（不可协商）

| 层 | 精确技术 |
|---|---|
| 前端 | Vue 3（`<script setup>`）+ Vite 5 + Pinia + Vue Router 4 |
| 3D | three.js + GLTFLoader + MeshoptDecoder（压缩 GLB） |
| 背景 | 自定义 canvas 粒子系统，60 个粒子，颜色 `#1EE07F`，连线距离 120 |
| 后端 | Python 3.11 + FastAPI + Pydantic v2 + python-jose（JWT）+ bcrypt |
| 运行时 | EdgeOne Pages Cloud Functions（Python）+ Edge Functions（JS） |
| 存储 | EdgeOne KV（默认）—— S3（可选，后台可切换） |
| 鉴权 | 邮箱 + 密码（强制）+ 微信 / Apple / Google（可开关） |
| 后台鉴权 | **独立** JWT scope（`scope:"admin"`），独立路由，独立 UI |
| 小程序 | 原生 WXML/WXSS/JS，共享 API |

---

## 🎨 品牌与视觉签名（1:1，禁止偏离）

```css
/* 原样粘进 src/style.css 的 :root */
--color-primary:   #1EE07F; /* 霓虹绿 */
--color-accent:    #00F0FF; /* 赛博青 */
--color-warning:   #FFB800;
--color-danger:    #FF4757;
--bg-deep:         #0A0A0E;
--bg-surface:      #14141A;
--bg-glass:        rgba(20, 20, 26, 0.65);
--border-glass:    rgba(255, 255, 255, 0.08);
--text-primary:    #FFFFFF;
--text-secondary:  rgba(255, 255, 255, 0.65);
--text-tertiary:   rgba(255, 255, 255, 0.4);
--font-display:    'Orbitron', system-ui, sans-serif;
--font-body:       'Inter', system-ui, sans-serif;
--font-mono:       'JetBrains Mono', Menlo, monospace;
--transition-smooth: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
--shadow-neon:     0 0 24px rgba(30, 224, 127, 0.35);
```

**首页**必备视觉元素：

- 全屏粒子背景 canvas，置于一切之后（`z-index: -1`）。
- 中央悬浮一个 **3D 自走 GLB 模型**，在边界内自由漂移，每 2-4 秒切换方向。
  GLB 源 URL 必须运行时从 `GET /api/v1/models3d/active` 拉取（取列表第一项）；
  仅当 API 失败时降级到 `/logo_opt.glb`。
- 毛玻璃卡片：`backdrop-filter: blur(12px)` 并在 hover 时
  `transform: rotateY(2deg) rotateX(1deg)` 微微倾斜。
- 所有标题用 `Orbitron`。所有正文用 `Inter`。金额/数字徽标用 `JetBrains Mono`。

---

## 🗺️ 布局与页面结构

### 用户端（Vue，入口 `/`）

| 路由 | 用途 |
|---|---|
| `/` | 首页（3D Logo + 推荐商品轮播 + 分类入口） |
| `/explore` | 商品广场（筛选 + 排序 + 分页） |
| `/skill/:id`（保留向后兼容）or `/product/:id` | 商品详情（图集 + Markdown 描述 + 评论 + 购买区） |
| `/login` | 登录（多 tab：账号密码 / 邮箱 / 微信 / Apple / Google） |
| `/register` | 注册（账号密码 + 可选邮箱） |
| `/upload` | 商家上架商品（销售模式：积分 / 现金 / 两者皆可） |
| `/profile` / `/u/:uid` | 私人 / 公开主页 |
| `/favorites` `/purchased` `/points` `/revenue` `/settings` | 用户中心 |

### 后台（Vue，入口 `/admin/`）

| 路由 | 用途 |
|---|---|
| `/admin/login` | 独立登录页（不复用用户端 token） |
| `/admin/dashboard` | 实时统计 |
| `/admin/users` | 用户列表 + 角色 + 封禁 |
| `/admin/products` | 商品 CRUD |
| `/admin/audit` | 待审核商品 |
| `/admin/orders` | 订单（积分 / 现金分流） |
| `/admin/recharges` | 现金充值订单 |
| `/admin/withdrawals` | 提现审批 |
| `/admin/reviews` | 评论 / 举报 |
| `/admin/models3d` | 上传 / 启用 / 调参 GLB 模型，**最多同时启用 5 个** |
| `/admin/settings` | 站点配置（含 storage_mode 开关、登录方式开关、第三方 Key、汇率） |
| `/admin/backup` | KV 数据导出 / 导入 |

---

## 💾 存储协议

默认 `storage_mode = "kv"`。二进制上传走 `chunked_kv`：

```
asset:{id}:meta   -> JSON {content_type, size, sha256, chunks, created_at}
asset:{id}:chunk:{n} -> base64 string of <= 512 KB
```

通过 `GET /api/v1/assets/{id}` 流式返回，`Content-Type` 来自 meta，附
`Cache-Control: public, max-age=31536000, immutable`。单资产硬上限 25 MB。

后台把 storage 切到 `s3` 时，**未来**的上传走 S3；已有的 KV 资产仍可通过
`/api/v1/assets/{id}` 访问。

---

## 🔐 鉴权要求

- 用户端 token：scope `user`，TTL 7 天。
- 后台 token：scope `admin`，TTL 8 小时，**独立** secret 派生。
- 默认管理员从首次冷启动时的 `ADMIN_INIT_USERNAME` / `ADMIN_INIT_PASSWORD`
  环境变量种入；标志位 `must_change_password: true` 直到首次修改。
- 密码哈希：bcrypt cost 12。
- 即便所有 OAuth 提供方都被关闭，**账号密码注册必须仍可用**（硬性要求）。

---

## 💰 双支付模式

每件商品都有 `sale_mode ∈ {"points","cash","both"}`：

- `points`：只显示 `points_price`。
- `cash`：只显示 `cash_price_yuan`，通过微信支付 / 支付宝结算
  （后台 settings 里有占位）。
- `both`：两者并排显示；用户在结算时选。

如果 `sale_mode in {"cash","both"}` 但 `cash_price_yuan <= 0`，必须用
Pydantic `model_validator` 直接拒绝。

---

## 🧊 3D 模型管理

`POST /api/v1/admin/models3d`（multipart）：上传 GLB ≤ 8 MB。Body 参数：

```json
{
  "name": "string",
  "scale": 1.0,
  "speed_xyz": [1.2, 0.6, 0.3],
  "bounds_xyz": [[ -3.5, 3.5 ], [0.3, 3.5], [-2.0, 1.5]],
  "enabled": true
}
```

服务端强制 `enabled.length <= 5`（否则 HTTP 409）。

`GET /api/v1/models3d/active` 返回有序的启用列表，公开免鉴权。
前端 `Logo3D.vue` 始终取 `data[0]` 作为首页模型。

---

## 🚀 部署

脚手架完成后，给 Agent 下指令：

```
现在调用官方 `edgeone-pages-deploy` Skill（来自
github.com/TencentEdgeOne/edgeone-pages-skills）完成：
  - 创建 EdgeOne Pages 项目，
  - 在控制台手动创建 KV 命名空间 "{{MALL_NAME}}_kv" 并绑定为 MY_KV，
  - 把 fn/[[default]].py 注册为 Python Cloud Function，
  - 把 api/[[default]].js 注册为 Edge Function，
  - 把 dist/ 发布为静态资源源站。
本地预览改用 `edgeone-pages-dev`。
```

> ⚠️ KV 命名空间的**创建与绑定无法通过 `edgeone.json` 自动完成**，必须在
EdgeOne Pages 控制台手动操作（参见 `SKILL.md` 步骤 4.1）。

首页 3D Mascot 随 Cloud Function 首次冷启动自动写入 KV，不需额外脚本。如需替换
Mascot，覆盖
`templates/cloud-functions/app/seed/assets/logo_opt.glb` 重新部署即可。

---

## ✅ 验收标准

构建**完成**的标志是以下**全部**满足：

1. `npm run build` 同时产出 `dist/index.html` 和 `dist/admin/index.html`。
2. `uvicorn app.main:app` 启动，`/api/v1/` 返回 `EdgeOne Mall API is running`。
3. 用种子凭证调 `POST /api/v1/admin/auth/login` 返回的 token，其 JWT
   payload 含 `"scope":"admin"`。
4. 访问 `/` 看到粒子背景 + 漂浮的 3D Logo + 一组毛玻璃商品卡。
5. 访问 `/admin` 重定向到 `/admin/login`；登录后 11 个面板全部能渲染并
   调用各自的端点。
6. 用普通用户身份在 `STORAGE_MODE=kv` 下上传 3 MB 图片成功，返回的
   `/api/v1/assets/{id}` URL 能流式回放，`Content-Type: image/jpeg`。
7. 后台把 `storage_mode` 切到 `s3`，新上传走 S3（或在 S3 变量未配时返回
   有意义的错误）。
8. 首次后台登录出现修改默认密码的提示。
9. 源码里**没有硬编码 secret**——所有 `JWT_SECRET`、`INTERNAL_KEY`、
   admin 密码、第三方 Key 都从 env / KV settings 读取。

任意一项不达标，**停下并修复后再宣布完成**。

---

*本 Prompts 赛道版是 `edgeone-mall` Skill 的独立对应物。两者产出同一份
artifact；Skill 版自带 templates，Agent 不必从散文里重新派生 200+ 个文件。*
