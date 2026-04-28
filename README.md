# edgeone-mall

> **一个 Anthropic 格式的 AI Skill：让任意支持 Skills 的编码 Agent（Claude
> Desktop / Continue / Cline / Cursor / GitHub Copilot Chat …）一次对话内，
> 在腾讯 EdgeOne Pages 上脚手架 + 部署一套生产级、霓虹赛博风格的在线商城——
> Vue 3 用户端（内置管理模块）+ FastAPI Cloud Function + Edge Function
> 鉴权层 + 微信小程序 + 分块 KV 资产存储，S3 / R2 / OSS 等对象存储零配置可选。**

本仓库面向 **EdgeOne Pages Skills 比赛** 的双赛道投稿：

- **Skills 赛道** — `SKILL.md` + `templates/` + `references/`（机器执行）
- **Prompts 赛道** — [`PROMPT.md`](./PROMPT.md)：与 Skill 等效的纯 Prompt
  独立版，无需打包资产即可在 ChatGPT / Claude / Copilot Chat 复现同一产出。

---

## 📑 目录

- [✨ 一句话能干什么](#-一句话能干什么)
- [🚀 5 步快速上手（用户视角）](#-5-步快速上手用户视角)
- [🤖 Agent 必读的执行流程](#-agent-必读的执行流程)
- [🧩 仓库结构](#-仓库结构)
- [🏗️ 架构总览](#️-架构总览)
- [🔐 鉴权与安全模型](#-鉴权与安全模型)
- [🌍 站点 / 加速区域 / 域名抉择](#-站点--加速区域--域名抉择)
- [📦 KV 与对象存储](#-kv-与对象存储)
- [💳 商品双支付模式](#-商品双支付模式)
- [👮 后台管理 (`/admin`)](#-后台管理-admin)
- [🐍 Python Cloud Function 依赖管理](#-python-cloud-function-依赖管理)
- [📱 微信小程序](#-微信小程序)
- [🛠️ 常见问题与排查](#️-常见问题与排查)
- [🔄 同步官方 Skill](#-同步官方-skill)
- [📜 License](#-license)

---

## ✨ 一句话能干什么

| 你说 | Agent 干什么 |
|---|---|
| “帮我用 edgeone-mall 起一个数字商品商城叫 NeonShop” | 复制 `templates/` → 全局重命名 → 写 secret → 提示绑 KV / 加速区域 → `edgeone pages deploy` → 给你可访问 URL |
| “演示账号是什么” | **第一个通过 `/auth/register` 完成注册的人 = 站长**，同密码可登录 `/admin` |
| “商品怎么改价” | 引导你打开 `/admin/products` 直接改 `price_points` / `price_cash` / `sale_mode` |
| “首页太单调” | 替换 banners / categories / promiseTags 数据，或编辑 `templates/frontend/src/views/Home.vue` |
| “能跑在小程序里吗？” | 已附 `templates/miniprogram/`，复制到微信开发者工具即可 |

---

## 🚀 5 步快速上手（用户视角）

```bash
# 0. 准备：Node ≥ 18 / Python ≥ 3.10 / 一个腾讯云账号（国内或国际站皆可）
npm install -g edgeone@latest        # CLI ≥ 1.2.30

# 1. 让 Agent 加载本 Skill（或粘 PROMPT.md），告诉它你要建什么样的商城
#    Agent 会一次性问完所有参数：mall_name / theme / 登录方式 / 后台密码 /
#    target_domain / site_region 等

# 2. Agent 自动复制 templates/ 到你的项目目录、跑全局重命名、写 secret
cd ./my-mall
edgeone whoami                       # 检查登录态
edgeone login --site <china|global>  # 与 site_region 一致；不要走交互菜单

# 3. 首次部署（Agent 会执行）
edgeone pages deploy -n my-mall      # 生成 EDGEONE_DEPLOY_URL
# ⚠️ 本 Skill 固定使用 -a global，且必须绑定自定义域名。
#    不提供「选不含中国大陆 + 免域名」方案——preset 临时域名 token 鉴权同样会拦截 Cloud↔Edge 代理。
#    a) KV 存储 → 创建 mall_kv → 项目设置 → 环境变量与绑定 → Binding Name = MY_KV
#    b) 项目 → 域名 → 添加自定义域名 → 加 CNAME → 校验 → 申请免费 SSL DV 证书
#    c) 拿到该域名后告诉 Agent，Agent 记录为 <DEPLOY_URL> 作为后续验证 / seed 触发 URL。
#    如果你打算走「免域名」路线，必须在控制台创建项目时就选
#    走 4.2.b：绑定自定义域名 → 拿到后告诉 Agent 作为 <DEPLOY_URL>

# 4. Agent 引导你到控制台：
#    a. 创建 KV 命名空间 mall_kv → 项目「环境变量与绑定」绑定为 MY_KV
#    b. 二选一让 API 跨过 token 鉴权：
#       必须绑定自定义域名 → 免备案（国际站）/ 需 ICP 备案（国内站）。preset 临时域名不可用。

# 5. 第二次部署 让 KV 绑定 + secret 同时生效
edgeone pages deploy
# 然后浏览器打开 https://<DEPLOY_URL> → 注册第一个账号 → 自动成为站长
```

如果你的 Agent 还不支持 Skills 协议，把 [`PROMPT.md`](./PROMPT.md) 原样粘到
ChatGPT / Claude / Copilot Chat 里，它能从零起一份等效项目。

---

## 🤖 Agent 必读的执行流程

完整 8 步流程在 [`SKILL.md`](./SKILL.md) 里。简版：

1. **收参数**（一次问完，禁止后续追问）：`mall_name` / `theme` / `enabled_login_methods` /
  `storage_mode` / `target_domain` / `site_region`。
2. **复制 `templates/`** 到目标目录，跑占位符替换（`EdgeOneMall` → `mall_name`、
   `YOUR_DOMAIN_HERE` → `target_domain`）。
3. **不要手动本地构建前端**；模板 `edgeone.json` 已配置 `buildCommand: "cd frontend && npm install && npm run build"`，`edgeone pages deploy` 会自动安装前端依赖并输出 `frontend/dist`。
4. **首次 deploy** → 创建 KV → 4.2.b 解决 token 鉴权 → 写 secret → 二次 deploy。
5. **触发首次 seed**：`Invoke-RestMethod 'https://<URL>/api/v1/system/bootstrap'` 一次。
6. **自检**：`/api/v1/categories` 返回 11 个商城分类；`/api/v1/skills` 返回 19 件 demo 商品；
  首个注册用户登录前台后可进入 `/admin`。
7. **3D 模型** 已自带 `seed/assets/logo_opt.glb`，首次冷启动自动入 KV。
8. **完成汇报**：把可访问 URL、admin 入口、首注册账号 = 站长 三件事一次性告诉用户。

详见 SKILL.md 步骤 1-8 + 故障排查表。

---

## 🧩 仓库结构

```
edgeone-mall/
├── SKILL.md                        ← Anthropic Skill 清单（Agent 入口）
├── PROMPT.md                       ← Prompts 赛道独立版
├── README.md                       ← 你正在看的
├── LICENSE                         ← MIT
├── examples/
│   └── site-settings.example.json  ← 步骤 1 收集到的参数样例
├── references/                     ← 12 份按需加载的深度文档
│   ├── architecture.md             ← Web ↔ Edge ↔ Cloud ↔ KV 数据流
│   ├── ui-design-system.md         ← CSS 变量、字体、动画曲线、组件骨架
│   ├── api-spec.md                 ← REST endpoint 全集
│   ├── data-model.md               ← KV key 命名（user:* / skill:* / order:* …）
│   ├── kv-storage.md               ← chunked_kv 协议 / 512KB 切片 / SHA-256
│   ├── admin-guide.md              ← 11 个后台面板说明
│   ├── payment-dual-mode.md        ← 积分/现金/双模式三态
│   ├── 3d-model-management.md      ← GLB 上传、激活、参数调
│   ├── miniprogram.md              ← 微信小程序集成要点
│   ├── seed-data.md                ← 11 分类 + 19 商品 demo 内容
│   ├── edgeone-pages-deploy.md     ← 官方 deploy Skill 摘录
│   └── edgeone-pages-dev.md        ← 官方 dev Skill 摘录
├── templates/                      ← Agent 会原样复制
│   ├── edgeone.json                ← 项目配置（rewrites / headers / cloudFunctions）
│   ├── frontend/                   ← Vue 3 + Vite 主站，内置 /admin 管理模块
│   │   ├── index.html              ← 主入口
│   │   ├── src/views/Home.vue      ← 首页（hero / banner / 11 cat / flash / arrivals）
│   │   ├── src/views/Admin.vue     ← 内置管理模块（/admin）
│   │   ├── src/api/request.js      ← 401 拦截 + 公共读路径白名单
│   │   └── …
│   ├── cloud-functions/            ← FastAPI（EdgeOne Python runtime）
│   │   ├── requirements.txt        ← ★ 唯一依赖清单，云端自动 pip install
│   │   ├── fn/[[default]].py       ← 唯一 HTTP 入口
│   │   └── app/
│   │       ├── api/v1/             ← auth / categories / products / orders / admin / system …
│   │       ├── core/               ← config / security / _secrets.py（部署时由 agent 写入）
│   │       ├── seed/               ← 11 分类 + 19 商品 + logo_opt.glb 自动入 KV
│   │       └── storage/            ← chunked_kv / s3 抽象
│   ├── edge-functions/api/[[default]].js   ← Edge ↔ Cloud 内部代理 + KV 读写
│   └── miniprogram/                ← 微信小程序源码
└── scripts/package_skill.py        ← 把仓库打成 Skill zip
```

---

## 🏗️ 架构总览

```
┌─────────────┐                          ┌──────────────────┐
│  浏览器/小程序 │  ──────────────────────► │ EdgeOne Pages    │
│  Vue 3 App   │                          │ 静态文件 (CDN)    │
└─────────────┘                          └──────────────────┘
       │                                           │
       │  /api/v1/*                                │ rewrite
       ▼                                           ▼
┌──────────────────────────────────────────────────────────┐
│              Edge Function  (api/[[default]].js)          │
│  • 解析 JWT，注入 X-Internal-Origin                        │
│  • 公共 GET 路径直读 MY_KV (categories / skills / models3d) │
│  • 其他请求转发到 Cloud Function                            │
└──────────────────────────────────────────────────────────┘
       │                       ▲
       │ HTTP                  │ HTTP-callback (KV 读写)
       ▼                       │
┌──────────────────────────────────────────────────────────┐
│         Cloud Function   (Python FastAPI / fn/[[default]]) │
│  • Auth / Orders / Admin / Reviews / Seed                 │
│  • 通过 Edge `/api/_internal/kv` 间接访问 KV               │
│  • 启动时自动 seed 11 分类 / 19 商品 / 3D 模型             │
└──────────────────────────────────────────────────────────┘
                              │
                              ▼
                  ┌────────────────────┐
                  │  EdgeOne KV (MY_KV) │
                  │  • user:* / cat:*   │
                  │  • skill:* (商品)   │
                  │  • asset:chunk:*    │
                  └────────────────────┘
```

详见 [`references/architecture.md`](./references/architecture.md)。

---

## 🔐 鉴权与安全模型

| 层级 | 凭证 | 携带方式 |
|---|---|---|
| 普通用户 | `EdgeOneMall_token` (短) + `EdgeOneMall_refresh_token` (长) | `Authorization: Bearer …` |
| 管理员后台 | 首个注册用户或 `role=admin` 用户 | 同一 `Authorization: Bearer …` 登录态 |
| Edge ↔ Cloud 互调 | `INTERNAL_KEY` + `JWT_SECRET`（每次部署随机） | 两端 inline 写死，不入 git |

✅ 第一个通过 `/auth/register` 注册的账号 = 管理员（`role=admin`，同账号密码可登 `/admin`）。  
✅ 后台、前台管理模块、备份、导入均不需要二次密码。  
✅ `_secrets.py` / `_secrets.local.js` 已默认进 `.gitignore`。  
✅ Agent 禁止把 secret 写进 git / commit message / 对话回显。

---

## 🌍 站点 / 加速区域 / 域名抉择

| 选项 | 控制台 | 加速区域 | 自定义域名 | 适合 |
|---|---|---|---|---|
| `china` | <https://console.cloud.tencent.com/edgeone/pages> | 中国 + 全球（`-a global`） | **必须**，需 ICP 备案 | 国内正式上线 |
| `global` | <https://console.tencentcloud.com/edgeone/pages> | 全球（`-a global`） | **必须**，免备案 | 出海 / 海外业务 / demo |

🚨 **加速区域在项目创建后不可修改**。本 Skill 固定使用 CLI `-a global`（默认含全球 + 中国大陆）。

⛔ **不提供免域名方案**。preset 临时域名 `*.edgeone.cool` 带 `?eo_token=...&eo_time=...` 全站鉴权，会拦截 Cloud Function 回调 Edge KV 代理 → `/api/v1/*` 全 544。
即使创建为 `-a overseas`（不含中国大陆），同样会被拦。唯一可靠路径是绑定自定义域名。

💡 不想买域名？到 Cloudflare Registrar / Namecheap / 腾讯云国际站注一个年费几块的 `.xyz` / `.online` / `.top`，拿到后才调本 Skill。

---

## 📦 KV 与对象存储

- **默认 `storage_mode=kv`**：商品图、3D 模型、用户头像通过
  `app/storage/chunked_kv.py` 按 512 KB base64 切片塞进 KV，单 value
  上限 1 MB，分块表挂在 `asset:chunk_index:<sha>`。
- **可选 `storage_mode=s3`**：填 S3_ENDPOINT / BUCKET / KEY / SECRET 后
  自动改走 `app/storage/s3.py`，无需重新部署，后台可一键切换。
- **KV 命名空间必须手动创建**：`edgeone.json` 不支持声明，
  控制台 → KV 存储 → 创建 `mall_kv` → 项目设置 → 绑定为 **`MY_KV`**
  （Binding Name 不可改，Edge Function 里硬编码引用）。

详见 [`references/kv-storage.md`](./references/kv-storage.md)。

---

## 💳 商品双支付模式

每件商品 schema 字段 `sale_mode ∈ {points, cash, both}`：

- `points`：仅积分兑换
- `cash`：仅现金支付（占位，本 demo 默认走 mock 支付通道）
- `both`：用户可任选，前端展示双价格 `price_points` + `price_cash`

可在 `/admin/products` 批量切换，支持「积分专区」「秒杀 1 元」「免费领」混合上架。
详见 [`references/payment-dual-mode.md`](./references/payment-dual-mode.md)。

---

## 👮 后台管理 (`/admin`)

内置在主 Vue SPA 中，路径 `/admin`，复用前台登录态；首个注册用户或 `role=admin` 用户可进入。

| 面板 | 功能 |
|---|---|
| 仪表盘 | 总览：用户 / 订单 / 商品 / 收入 |
| 用户管理 | 列表 / 拉黑 / 改密 / 改积分 |
| 商品管理 | CRUD / 双支付模式 / 上下架 / 排序 |
| 分类管理 | 11 默认分类，可改图标 / 排序 |
| 订单管理 | 状态筛选 / 退款 / 物流 |
| 评价管理 | 审核 / 删除 / 屏蔽 |
| 积分管理 | 发放 / 扣减 / 流水 |
| 3D 模型 | 上传 GLB / 同时启用 ≤ 5 / 调 scale & speed |
| 站点设置 | 主题、Banner、Logo、SEO、storage_mode 切换 |
| 系统 | reseed / 备份 / KV 浏览 |

第一个注册的账号自动获得后台访问权（`role=admin`），前台和 `/admin` 使用同一个账号密码；
备份与导入只要求管理员登录态，不需要额外密码。

详见 [`references/admin-guide.md`](./references/admin-guide.md)。

---

## 🐍 Python Cloud Function 依赖管理

> 这是最常见的部署陷阱，单独抽出来强调。

✅ **正确做法**：把所有 Python 依赖名（建议带版本号）写进
`templates/cloud-functions/requirements.txt`：

```txt
fastapi==0.115.4
pydantic==2.9.2
PyJWT==2.9.0
python-multipart==0.0.12
httpx==0.27.2
```

EdgeOne Pages 部署时**会在云端自动执行** `pip install -r requirements.txt`，
你能在控制台 → 函数 → 部署日志看到完整的 pip 输出。

❌ **错误做法**（agent 做了这些会浪费几十分钟还失败）：
- 在本地 `pip install -r requirements.txt -t cloud-functions/.python_packages/`
- 上传 `site-packages` / `.venv` / `__pycache__`
- 用 `from jose import jwt`（依赖 `python-jose`）但 `requirements.txt` 只装了 `PyJWT`
  → 模块崩溃 → seed 中间件不运行 → KV 永远是空

---

## 📱 微信小程序

`templates/miniprogram/` 是一份完整的微信小程序工程：

- `app.json` 配置 5 个 Tab：首页 / 探索 / 发布 / 订单 / 我的
- `utils/api.js` 复用与 Web 端相同的 `/api/v1/*` 端点
- `pages/webview/` 用于在小程序内打开商品详情 H5（避开 IPv6 / 域名白名单限制）
- 所有图片走 `<image lazy-load>` + KV 切片接口

详见 [`templates/miniprogram/README.md`](./templates/miniprogram/README.md) 和
[`references/miniprogram.md`](./references/miniprogram.md)。

---

## 🛠️ 常见问题与排查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| `/api/v1/*` 全 401 / 544 | preset 临时域名 token 拦了 Cloud→Edge 内部回调 | 必须绑定自定义域名后走该域名验证；`-a overseas` 同样会被拦 |
| `/admin` 进入空白 | 主应用路由或 rewrite 缺失 | 检查 `frontend/src/router/index.js` 的 `/admin` 路由，以及 `edgeone.json` 的 `/admin -> /index.html` rewrite |
| 上传 413 | KV 单 value 1 MB 上限 | 切到 S3 或确认 `chunked_kv.CHUNK_SIZE = 512*1024` |
| `Logo3D` 一直 fallback | `/api/v1/models3d/active` 返 `[]` | 重 seed 或后台手动上传 GLB |
| 注册后无法进后台 | 当前账号不是首个注册用户，也没有 `role=admin` | 使用首个注册账号登录，或由管理员在用户管理中授予管理员角色 |
| `MY_KV is not defined` | 控制台未绑定，或 Binding Name 不是 `MY_KV` | 重新到「环境变量与绑定」绑定 |
| 部署后 `ModuleNotFoundError` | `requirements.txt` 漏写 | 补上重新 deploy，看远端 pip 日志 |
| `/api/v1/categories` 返回旧数据 | seed 是幂等的（`if not existing_cats`） | 后台「分类管理」全删后调 `/api/v1/system/bootstrap` |

完整故障表见 [`SKILL.md`](./SKILL.md) 末尾。

---

## 🔄 同步官方 Skill

本 Skill 不重复实现部署能力，而是在步骤 4 把控制权移交给官方 Skill：

- [`edgeone-pages-deploy`](https://github.com/TencentEdgeOne/edgeone-pages-skills/tree/main/skills/edgeone-pages-deploy)
- [`edgeone-pages-dev`](https://github.com/TencentEdgeOne/edgeone-pages-skills/tree/main/skills/edgeone-pages-dev)

`references/edgeone-pages-deploy.md` 与 `references/edgeone-pages-dev.md`
是上述两个 Skill 的本地摘录，按其原协议署名引用，便于 Agent 离线参阅。

---

## 📜 License

MIT — 见 [LICENSE](./LICENSE)。

`templates/` 内置资产派生自同作者的开源项目 OpenClaw / Skill 交易，
为 Skill 分发重新以 MIT 协议授权。
