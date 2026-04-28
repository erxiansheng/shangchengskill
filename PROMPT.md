# EdgeOne Mall — 纯 Prompt 版（Prompts 赛道投稿）

> **直接把这份 Prompt 原样粘给任意通用 AI 编码 Agent**（ChatGPT / Claude /
> GitHub Copilot Chat / Cursor / Cline / Continue …），让它在腾讯 EdgeOne
> Pages 上从零交付一个完整、生产级、霓虹赛博风格的全栈在线商城。
>
> **无需**配套的 `edgeone-mall` Skill 也不依赖任何模板文件——这份 Prompt
> 自包含全部规格 + 部署流程 + 排错知识。
>
> 与 Skill 版（`SKILL.md` + `templates/`）等效，区别在于：
> - Skill 版：Agent 复制已有模板 → 替换占位符 → 部署（更快、更稳）
> - Prompt 版：Agent 按规格从零生成代码 → 部署（更灵活、更慢）

---

## ⚙️ 启动指令（粘到你的 Agent 里）

```
Install this skill: npx skills add TencentEdgeOne/edgeone-pages-skills,
then deploy to EdgeOne Pages.

按照下面的规格搭建一个完整的全栈在线商城，名字叫 "{{MALL_NAME}}"。
不要自由发挥样式或技术栈——所有约束必须 1:1 严格执行。
所有标 ⛔ 的禁止项一律不准做；所有标 ✅ 的硬性要求一定要满足。
```

把 `{{MALL_NAME}}` 替换成你想要的商城名（如 `NeonShop`、`数字商城`、
`图书商城` 等），其它占位符见后文「Agent 必须一次性问完的参数」一节。

---

## 🎯 交付目标

产出**一个仓库**，包含：

1. **Vue 3 + Vite** 用户端（入口 `index.html`，路由 `/`）
2. Vue 3 前台主应用内置管理模块（路由 `/admin`，组件 `src/views/Admin.vue`，
  复用前台登录态，不再生成独立后台 HTML 子应用）
3. 部署在 EdgeOne Pages 的 **FastAPI Python Cloud Function**
   （`cloud-functions/fn/[[default]].py` 文件系统路由，统一挂载在 `/api/v1`）
4. **Edge Function**（`edge-functions/api/[[default]].js`），代理 KV +
   注入 JWT 校验 + 公共 GET 直读
5. 共享同一套 REST API 的 **微信小程序**（`miniprogram/`）
6. **分块 KV 存储** 作默认（无需 S3，512 KB 切片塞 KV），后台可一键切到 S3

---

## 🧱 技术栈（不可协商）

| 层 | 精确技术 |
|---|---|
| 前端 | Vue 3（`<script setup>`）+ Vite 5 + Pinia + Vue Router 4 |
| 3D | three.js + GLTFLoader + MeshoptDecoder（压缩 GLB） |
| 背景 | 自定义 canvas 粒子系统，60 个粒子，颜色 `#1EE07F`，连线距离 120 |
| 后端 | Python 3.11 + FastAPI + Pydantic v2 + **PyJWT**（⛔ 不要用 python-jose）+ bcrypt |
| 运行时 | EdgeOne Pages Cloud Functions（Python）+ Edge Functions（JS） |
| 存储 | EdgeOne KV（默认 `MY_KV` 绑定）— S3（可选，后台可切换） |
| 鉴权 | 邮箱 / 用户名 + 密码（强制） + 微信 / Apple / Google（可开关） |
| 后台鉴权 | 首个注册用户或 `role=admin` 用户，同一 Bearer 登录态 |
| 小程序 | 原生 WXML/WXSS/JS，复用 `/api/v1/*` 端点 |

---

## 📋 Agent 必须一次性问完的参数（禁止后续追问）

进入实际编码前，Agent **必须** 一次性向用户收齐下列字段并写入
`examples/site-settings.json`：

| 字段 | 类型 | 说明 / 默认 |
|---|---|---|
| `mall_name` | string | 商城名称，如 `数字商城`、`NeonShop`。默认 `数字商城` |
| `theme` | enum | 强制 `dark`，⛔ 不接受浅色主题 |
| `enabled_login_methods` | array | `password` / `email` / `wechat` / `qq` 任意组合，默认全部 |
| `storage_mode` | enum | `kv`（推荐，零配置）/ `s3`（需填 endpoint），默认 `kv` |
| `target_domain` | string\|null | 自定义域名如 `mall.example.com`，可留空 |
| `site_region` | enum | `china` / `global`，默认 `china`。**仅决定站点，不决定是否免域名**。全栈商城必须绑定自定义域名 |

✅ **首次注册账号 = 管理员**：本商城后端必须把 **第一个通过
`/auth/register` 注册成功的用户** 自动设为管理员（`role=admin`），
其账号密码同时可用于前台和 `/admin` 后台。
Agent 完工时要明确告诉用户：「第一个打开站点完成注册的人就是站长，
建议立刻自己抢注」。不要预置默认管理员账号，不要要求后台二次验证密码；备份和导入只要求管理员登录态。

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

- 全屏粒子背景 canvas，置于一切之后（`z-index: -1`）
- 中央悬浮一个 **3D 自走 GLB 模型**，在边界内自由漂移，每 2-4 秒切换方向
  - GLB 源 URL **必须** 运行时从 `GET /api/v1/models3d/active` 拉取（取列表第一项）
  - 仅当 API 失败时降级到 `/logo_opt.glb`
- 毛玻璃卡片：`backdrop-filter: blur(12px)`，hover 时
  `transform: rotateY(2deg) rotateX(1deg)` 微微倾斜
- 所有标题用 `Orbitron`；所有正文用 `Inter`；金额 / 数字徽标用 `JetBrains Mono`
- **首页结构 / 顺序固定**（自上而下）：
  1. **Hero** 区：左 `glass-panel` 玻璃卡（含 3D Logo + 标题 + 副标题 + 操作按钮 + stats + 8 个服务承诺标签 `hero-tags`），右 banner 轮播 + 4 项 promise-strip
     - 标题主词使用 `glitch-hover` 类：hover 时红 / 青双轨道故障动画
     - hero-left `min-height: 310px`，banner-carousel `min-height: 215px`（不要做太高）
  2. **Flash Sale** 限时秒杀（紧跟 Hero，提示「每日 0 点更新」+ 倒计时）
  3. **11 个分类网格** `category-grid`：6 列、`gap: 18px`，每个 `cat-tile` 高 130px，
     `cat-icon-wrap` 用 `position: absolute; inset: 0` 填满整张卡片做背景，
     emoji 字号 48px 居中，`cat-name` 浮在底部 12px。6 色循环主题（红/青/橙/紫/绿/粉）
  4. **新品 / 推荐** 横向滚动卡片
  5. **服务承诺标签** 8 项使用 **内联 SVG 图标**，⛔ 不要用 emoji
     （盾牌/闪电/货车/循环/宝石/礼盒/对话气泡/锁），`stroke="currentColor"` 着色

---

## 🗺️ 路由 / 页面结构

### 用户端（Vue，入口 `/`）

| 路由 | 用途 |
|---|---|
| `/` | 首页（结构如上） |
| `/explore` | 商品广场（筛选 + 分类联动 + 排序 + 分页） |
| `/product/:id`（兼容 `/skill/:id`） | 商品详情（图集 + Markdown 描述 + 评论 + 购买区） |
| `/login` | 登录（多 tab：账号密码 / 邮箱 / 微信 / QQ） |
| `/register` | 注册（首位 = 管理员） |
| `/upload` | 商家上架（销售模式：积分 / 现金 / 双模式） |
| `/profile` / `/u/:uid` | 私人 / 公开主页 |
| `/favorites` `/purchased` `/points` `/revenue` `/settings` | 用户中心 |

### 后台（主 Vue SPA 内置路由 `/admin`）

| 路由 | 用途 |
|---|---|
| `/admin` | 内置管理控制台（仪表盘 / 用户 / 商品 / 审核 / 订单 / 充值 / 提现 / 评论 / 3D 模型 / 设置 / 数据备份） |
| `/admin/audit` | 待审核商品 |
| `/admin/orders` | 订单（积分 / 现金分流） |
| `/admin/recharges` | 现金充值订单 |
| `/admin/withdrawals` | 提现审批 |
| `/admin/reviews` | 评论 / 举报 |
| `/admin/models3d` | 上传 / 启用 / 调参 GLB，**最多同时启用 5 个** |
| `/admin/settings` | 站点配置（storage_mode 开关、登录方式开关、第三方 Key、汇率） |
| `/admin/backup` | KV 数据导出 / 导入 |

### 11 个默认分类（`seed/bootstrap.py` 必须包含）

```
1  数码电器  📱     2  服饰鞋包  👕     3  美妆个护  💄
4  食品生鲜  🍎     5  家居家装  🛋️    6  母婴玩具  🧸
7  运动户外  ⚽    8  图书音像  📚     9  虚拟商品  💎
10 积分专区  🎁    11 限时特惠  ⚡
```

⛔ 不要用「AI 智能 / 开发工具 / 效率提升」之类技能交易型名字——本项目是商城。  
✅ Seed 必须 **幂等**：`if not existing_cats` 才写入；但要附带「检测到旧版
skill 主题分类时强制替换」的迁移逻辑，避免老 KV 数据卡住。

### Demo 商品（至少 19 件，覆盖全 11 分类）

涵盖比例建议：数码 3 / 服饰 2 / 美妆 1 / 食品 2 / 家居 2 / 母婴 1 /
运动 2 / 图书 1 / 虚拟 1 / 积分专区 3 / 限时特惠 2。  
其中至少包含：1 件免费、1 件「秒杀 1 元新人专享」、积分 / 现金 / 双模式
混合上架。每件商品 schema 必含 `category_id` 字段绑定到上面 11 个分类之一。

---

## 💾 存储协议

默认 `storage_mode = "kv"`。二进制上传走 `chunked_kv`：

```
asset:{id}:meta       -> JSON {content_type, size, sha256, chunks, created_at}
asset:{id}:chunk:{n}  -> base64 string (size <= 512 KB per chunk)
```

通过 `GET /api/v1/assets/{id}` 流式返回，`Content-Type` 来自 meta，附
`Cache-Control: public, max-age=31536000, immutable`。单资产硬上限 25 MB。

后台把 `storage_mode` 切到 `s3` 时，**未来**的上传走 S3；已有的 KV 资产
仍可通过 `/api/v1/assets/{id}` 访问。S3 凭证字段：`S3_ENDPOINT` /
`S3_BUCKET` / `S3_ACCESS_KEY` / `S3_SECRET_KEY`。

---

## 🔐 鉴权与安全（硬性要求）

| 层级 | 凭证 | TTL / 携带方式 |
|---|---|---|
| 用户端 | access/refresh JWT | `Authorization: Bearer …` |
| 后台 | 首个注册用户或 `role=admin` 用户 | 同一 `Authorization: Bearer …` 登录态；无二次密码 |
| Edge ↔ Cloud 互调 | `INTERNAL_KEY` + `JWT_SECRET` | 两端 inline 写死，⛔ 不入 git |

✅ 密码哈希：bcrypt cost 12  
✅ **第一个 `/auth/register` 成功的账号自动 `role=admin`**  
✅ 即便所有 OAuth 提供方都被关闭，**账号密码注册必须仍可用**  
✅ secret 文件 `cloud-functions/app/core/_secrets.py` 与 inline 化的
`edge-functions/api/[[default]].js` **必须** 在 `.gitignore` 中  
⛔ Agent 不准把 secret 写进 git / commit message / 对话回显

---

## 💰 双支付模式

每件商品都有 `sale_mode ∈ {"points","cash","both"}`：

- `points`：只显示 `price_points`
- `cash`：只显示 `price_cash`（人民币元，走 mock 支付通道占位）
- `both`：两者并排显示，用户在结算时选

如果 `sale_mode in {"cash","both"}` 但 `price_cash <= 0`，必须用
Pydantic `model_validator` 直接拒绝。

---

## 🧊 3D 模型管理

`POST /api/v1/admin/models3d`（multipart）：上传 GLB ≤ 8 MB。Body 参数：

```json
{
  "name": "string",
  "scale": 1.0,
  "speed_xyz": [1.2, 0.6, 0.3],
  "bounds_xyz": [[-3.5, 3.5], [0.3, 3.5], [-2.0, 1.5]],
  "enabled": true
}
```

✅ 同时启用上限 5 个；超过返回 400  
✅ 首次冷启动自动从 `seed/assets/logo_opt.glb` 入 KV，无需手动上传  
✅ `/api/v1/models3d/active` 返回所有 `enabled: true` 的列表，前端取首个

---

## 🐍 Python Cloud Function 依赖管理（最常踩坑的地方）

✅ **正确**：所有依赖名（建议带版本号）写进
`cloud-functions/requirements.txt`：

```txt
fastapi==0.115.4
pydantic==2.9.2
PyJWT==2.9.0
python-multipart==0.0.12
httpx==0.27.2
bcrypt==4.2.0
```

EdgeOne Pages 部署时**会在云端自动执行** `pip install -r requirements.txt`，
能在控制台 → 函数 → 部署日志看到 pip 输出。

⛔ **错误做法**（agent 做了这些会浪费几十分钟还失败）：
- 在本地跑 `pip install -t cloud-functions/.python_packages/`
- 上传 `site-packages` / `.venv` / `__pycache__`
- 用 `from jose import jwt`（python-jose）但 `requirements.txt` 只装了 `PyJWT`
  → Cloud Function 加载崩 → seed 不运行 → KV 永远空 → 所有 API 544

---

## 🌍 加速区域 / 域名抉择（部署前必须想清楚）

🚨 **EdgeOne Pages 项目的「加速区域」一旦创建后不可修改**。本 Skill 固定使用 `edgeone pages deploy -a global`（默认含全球 + 中国大陆）。

两种站点选择：

| `site_region` | 控制台 | 自定义域名 | 适合 |
|---|---|---|---|
| `china` | console.cloud.tencent.com | **必须**，需 ICP 备案 | 国内正式上线 |
| `global` | console.tencentcloud.com | **必须**，免备案 | 出海 / 海外业务 / demo |

⛔ **不提供免域名方案**。Cloud Function 必须经 Edge Function 回调访问 KV（Python runtime 没有
直接的 KV binding）。preset 临时域名 `*.edgeone.cool` 使用 `?eo_token=...&eo_time=...` 全站鉴权，
会拦截该内部回调 → `/api/v1/*` 全 544。**即使创建为 `-a overseas`（不含中国大陆）**，同样会被拦，
本 Skill 不会引导走该路径。唯一可靠路径是绑定自定义域名。

> 💡 用户手上没可用域名：让他去 Cloudflare Registrar / Namecheap / 腾讯云国际站注一个年费几块钱的 `.xyz` / `.online` / `.top`，拿到后才调本 Skill。

---

## 📋 Agent 部署执行顺序（严格按序）

```bash
# 1. 装 / 升级 CLI
npm install -g edgeone@latest          # ≥ 1.2.30

# 2. 检查登录态
edgeone whoami
edgeone logout                         # 仅当当前站点 ≠ 目标 site_region
edgeone login --site <china|global>    # ⛔ 不要走交互菜单

# 3. 确认 edgeone.json 让部署流程自动构建前端
#    项目根必须包含 edgeone.json，核心字段如下：
#    buildCommand: "cd frontend && npm install && npm run build"
#    installCommand: "echo skip-root-install"
#    outputDirectory: "frontend/dist"
#    rewrites.source 可使用 "*" 通配，例如 "/skill/*"；rewrites.destination 必须是具体文件路径。
#    不要写 ":path*"，也不要写 {"source":"/api/*","destination":"/api/*"} 这类 no-op rewrite。
#    不要因为首次部署前没有 frontend/dist 就在本地手动 npm install / npm run build。
#    edgeone pages deploy 会按 buildCommand 进入 frontend/ 安装依赖并产出 dist。
cd <项目根>

# 4. 首次部署
edgeone pages deploy -a global -n <project-name>
#    输出 EDGEONE_DEPLOY_URL（临时，3hr 过期）——临时域名只能看到静态页，不要拿去调 /api/v1/*。
#    ⚠️ 不要 --dir，会漏掉 cloud / edge functions。
#    ⚠️ -a 默认 global（含全球 + 中国大陆）。本 Skill 固定这样走，不使用 -a overseas。

# 5. 控制台手动 a + b + c（CLI 不支持）
#    a. KV 存储 → 创建命名空间 mall_kv
#       项目设置 → 环境变量与绑定 → 添加绑定，Binding Name = MY_KV
#    b. 项目 → 域名 → 添加自定义域名，加 CNAME，校验生效，申请免费 SSL DV 证书
#    c. 拿着该域名回到对话 → 告诉 Agent，Agent 记录为 <DEPLOY_URL>（后续验证、seed 全走该域名）

# 6. Agent 把 secret 写进项目（注意 .gitignore）
#    cloud-functions/app/core/_secrets.py
#       JWT_SECRET / INTERNAL_KEY
#    edge-functions/api/[[default]].js 顶部
#       INTERNAL_KEY / JWT_SECRET inline 替换

# 7. 二次部署（让 KV 绑定 + secret 同时生效）
edgeone pages deploy

# 8. 触发首次 seed（Cloud Function KV 写入是惰性的）
Invoke-RestMethod 'https://<DEPLOY_URL>/api/v1/system/bootstrap'

# 9. 自检（必做）
Invoke-RestMethod 'https://<DEPLOY_URL>/api/v1/categories'   # 应返 11 个商城分类
Invoke-RestMethod 'https://<DEPLOY_URL>/api/v1/skills'       # 应返 19 件 demo 商品

# 10. 完工汇报
echo "URL: https://<DEPLOY_URL>"
echo "管理后台: https://<DEPLOY_URL>/admin"
echo "⚠️ 第一个完成 /auth/register 注册的人 = 站长，登录后可用同一密码进 /admin"
```

---

## 🚫 公共读路径白名单（前端 401 拦截器必须排除）

`src/api/request.js` 在 401 时不要清 token + 跳登录页对以下 GET 路径生效：

```js
const PUBLIC_READ_PATTERNS = [
  /^\/skills(\/|\?|$)/,
  /^\/categories(\/|\?|$)/,
  /^\/reviews(\/|\?|$)/,
  /^\/system\//,
  /^\/captcha(\/|\?|$)/,
  /^\/models3d\//,
  /^\/site\//,
]
```

⛔ 否则点击首页分类瞬间 401 → 跳 `/login` → 用户体验崩

---

## 🛠️ 常见排查表（Agent 必须熟读）

| 现象 | 可能原因 | 处理 |
|---|---|---|
| `/api/v1/*` 全 401 / 544 | preset 临时域名 token 拦了 Cloud→Edge 回调 | 必须绑自定义域名后走自定义域名验证，项目是否 `-a overseas` 不影响该拦截 |
| `/admin` 进入空白 | 主应用路由或 rewrite 缺失 | 检查 `frontend/src/router/index.js` 的 `/admin` 路由，以及 `edgeone.json` 的 `/admin -> /index.html` rewrite |
| 上传 413 | KV 单 value 1 MB 上限 | 切到 S3 或确认 `chunked_kv.CHUNK_SIZE = 512*1024` |
| `Logo3D` 一直 fallback | `/api/v1/models3d/active` 返 `[]` | 调 `/api/v1/system/bootstrap` 触发 seed，或后台手动上传 GLB |
| `MY_KV is not defined` | 控制台未绑定，或 Binding Name 不是 `MY_KV` | 重新绑定 |
| 部署后 `ModuleNotFoundError` | `requirements.txt` 漏写或包名错 | 补上重新 deploy；⛔ 不要本地 vendor |
| `/api/v1/admin/auth/login` 544 | `from jose import jwt` 但 `requirements.txt` 只有 `PyJWT` | 改成 `import jwt`（PyJWT），重 deploy |
| `/api/v1/categories` 返回旧分类 | 上一轮演示写入的旧 `cat:all`、`cat:1..7`还在 KV 里 | 新版 `seed/bootstrap.py` 已加迁移逻辑自动检测旧 AI 分类名並清空重建。重新 `Invoke-RestMethod 'https://<DEPLOY_URL>/api/v1/system/bootstrap'`，看返回里 `categories: true` 即迁移成功 |
| 旧后台深链 404 | 独立后台子应用已移除 | 使用主应用内置管理入口 `/admin` |

---

## ✅ 完工验收清单

Agent 在汇报前必须自我核对（任意一项不过都要回去修）：

- [ ] 首页能看到 3D Logo + 粒子背景 + 11 分类网格 + 倒计时秒杀 + 8 SVG 服务承诺
- [ ] `/explore` 点击分类不会跳 `/login`
- [ ] `/auth/register` 第一个成功响应里 `is_admin: true`
- [ ] 首个注册用户登录前台后可进入 `/admin`
- [ ] `/api/v1/categories` 返回 11 个商城分类（不是 7 个 AI 技能分类）
- [ ] `/api/v1/skills` 返回 ≥ 19 件 demo 商品，覆盖所有 11 个分类
- [ ] 后台「分类管理」「商品管理」「3D 模型」三个面板能正常 CRUD
- [ ] `_secrets.py` 与 inline 化的 `[[default]].js` 都在 `.gitignore`
- [ ] 部署日志里能看到云端 `pip install -r requirements.txt` 的输出
- [ ] 没有 `cloud-functions/.python_packages/` 或 `.venv/` 被上传

---

## 📜 License

本 Prompt 以 MIT 协议开放，可自由复制 / 修改 / 商用 / 二次分发。
派生自 [edgeone-mall](https://github.com/openclaw/edgeone-mall) 仓库
（同步维护 Skill 版与 Prompt 版双赛道投稿）。
