---
name: pages-mall14
description: |
  使用本 Skill 在腾讯 EdgeOne Pages 上从零搭建并部署一个生产级、霓虹赛博风格的
  在线商城（用户端 + 后台 + 小程序 + Cloud Function API）。触发关键词：
  "搭建商城 / 电商 / 在线商店"、"在 EdgeOne 上部署商城"、"edgeone mall"、
  "做一个支持积分 + 现金双支付的市场"。Skill 内置 Vue 3 + Vite 用户端、独立的
  /admin Vue 控制台、FastAPI Python Cloud Function、微信小程序，以及一套
  分块 KV 资产存储（无需 S3，但 S3 仍作为可切换后端保留）。真正的云端部署
  动作交给官方 edgeone-pages-deploy / edgeone-pages-dev Skill 完成。
version: 0.2.0
author: Dasbclaw / edgeone-mall
license: MIT
argument-hint: 简要的品牌描述，例如 "深色霓虹绿色调的桌游周边商城，名字叫 NeonGoods"
user-invocable: true
allowed-tools: read_file, write, edit, run_in_terminal, fetch_webpage
---

# edgeone-mall — EdgeOne Pages 上的霓虹赛博风在线商城

## 何时使用本 Skill

当用户提出以下任意需求时启用：

- 一个完整的商城 / 电商 / 在线商店 / marketplace / shop / mall
- 部署到腾讯 EdgeOne Pages 的全栈电商
- 一个带积分 + 现金双支付、3D 首页、毛玻璃 UI 的商城模板
- 同时承接**数字商品**（ZIP 文件下载）与**实体商品**（收货地址 + 物流，支持微信/支付宝扫码支付）
- 复刻 OpenClaw 风格的深色霓虹 UI（Inter + Orbitron 字体 / `#1EE07F` 主色 /
  粒子背景 / 倾斜玻璃卡）

**不要**在以下场景使用：

- 单页静态站点（用 `edgeone-pages-deploy` 即可）
- 纯 API / 无前端项目
- 已存在 React/Next 工程的迁移（本 Skill 强制 Vue 3 + Vite）

---

## 你能得到什么

| 表面 | 路径 | 说明 |
|---|---|---|
| 用户端 Web | `templates/frontend/`（入口 `index.html`） | Vue 3 + Vite + Pinia + Vue-Router 4，含粒子背景、3D 自走 Logo、首页/广场/详情/上架/收藏/已购/积分/收益/公开主页/设置 等 18+ 页面 |
| 后台管理 Web | `templates/frontend/admin/`（入口 `admin/index.html`） | 完全独立的 Vue 子应用，自带路由 + 鉴权，11 个面板（仪表盘 / 用户 / 商品 / 审核 / 订单 / 充值 / 提现 / 评论 / 3D 模型 / 设置 / 数据备份） |
| Cloud Function (API) | `templates/cloud-functions/` | EdgeOne Python 运行时上的 FastAPI，文件路由 `fn/[[default]].py`，30+ 端点 |
| Edge Function (代理) | `templates/edge-functions/api/[[default]].js` | KV 透传 + JWT 校验 + 静态降级 |
| 微信小程序 | `templates/miniprogram/` | 与 Web 共用 API，含首页 / 广场 / 详情 / 我的 / 发布 |
| 种子脚本 | `templates/seed/` + `cloud-functions/app/seed/` | 首次启动注入演示商品、默认管理员、3D 模型 |

视觉风格（**1:1 复刻，禁止改色**）：

- 主色 `--color-primary: #1EE07F`（霓虹绿）+ 强调色 `--color-accent: #00F0FF`（赛博青）
- 显示字体 `Orbitron` + 正文 `Inter` + 等宽 `JetBrains Mono`
- 全局粒子 canvas 背景（`ParticlesBackground.vue`，密度 60，色 `#1EE07F`）
- 卡片：`background: var(--bg-glass)` + `backdrop-filter: blur(12px)` +
  `transform: rotateY(2deg) rotateX(1deg)` 悬浮
- 首页中央 GLB 3D 模型自由漂浮（`Logo3D.vue`，从 `/api/v1/models3d/active`
  动态获取）

---

## Skill 执行步骤（必须严格按序）

### 步骤 1 — 收集参数

向用户询问（或从 prompt 中推断）。**所有需要用户输入的项一次性问完，后续步骤禁止再弹问框**：

1. **mall_name**（例如 `数字商城、图书商城、素材商城`,默认`数字商城`）
2. **theme**（强制 `dark`；不接受浅色）
3. **enabled_login_methods**（`password`、`邮箱`、`微信`、`QQ` 、任意组合,默认`全部`）
4. **storage_mode**（`kv`（推荐，零配置）或 `s3`，可在后台后续切换,默认`kv`）
5. **default_admin_username**（默认管理员账号名，建议 `admin`,默认`admin`）
6. **default_admin_password**（管理员**初始登录密码**，至少 12 位,默认`admin123456`）
7. **admin_panel_password**（**后台二次验证密码**，调用任何 `/admin/*` API 时
   必须携带 `X-Admin-Password` 头；与上面登录密码**不同**；未填则后台 API 全部 503,默认`admin654321`）
8. **target_domain**（部署后想绑定的域名，可留空,默认`部署后绑定`）
9. **全部默认**（可以选择使用全部默认值,但一定要把每项默认值告诉用户是什么）
将这些参数持久化到 `examples/site-settings.json` 以便之后复用。
密码字段标记为 `secret`，**绝对不要**回显或写进 git。

### 步骤 2 — 复制模板

把整个 `templates/` 目录复制到用户选定的项目目录（例如 `./my-mall/`）。
**不要**修改文件结构。运行一次全局文本替换：

| 占位符 | 替换为 |
|---|---|
| `EdgeOneMall` | 用户的 `mall_name`（PascalCase） |
| `edgeone-mall`（在 `package.json` 的 `name` 中） | kebab-case 商城名 |
| `YOUR_DOMAIN_HERE` | 目标域名或 `localhost:5173` |
| `__JWT_SECRET__` | `python -c "import secrets;print(secrets.token_hex(32))"` |
| `__INTERNAL_KEY__` | 第二次执行 `secrets.token_hex(32)` |

> ⚠️ **Windows 编码**：禁止用 `Set-Content -Encoding UTF8`（PowerShell 5.1
> 写入 BOM 会让 Vite/PostCSS 解析 `package.json` 失败）。请用
> `Set-Content -Encoding utf8NoBOM`（PS 7+），或
> `[System.IO.File]::WriteAllText($p, $text, [System.Text.UTF8Encoding]::new($false))`。
> 详细批量去 BOM 脚本见 [`references/edgeone-pages-deploy.md`](references/edgeone-pages-deploy.md)。

### 步骤 3 — secret 管理

**不要**生成 `.env`。所有 secret 在步骤 4.3 由 agent 写入
`cloud-functions/app/core/_secrets.py` 与 `edge-functions/api/[[default]].js`
顶部常量，部署时随包上传。

### 步骤 4 — 部署到 EdgeOne Pages（顺序严格）

> 关键流程：**先 deploy 创建项目 → 在控制台绑 KV → 写 secret → 再 deploy 一次让两者生效**。
> 这个顺序不能颠倒。第一次没 deploy 的话，控制台里根本看不到这个 Pages 项目，
> 也就无从绑 KV。

#### 4.1 首次部署：创建 EdgeOne Pages 项目

调用官方 `edgeone-pages-deploy` Skill（仓库：
<https://github.com/TencentEdgeOne/edgeone-pages-skills>）执行**首次** deploy。
它会：装 / 升级 CLI（≥ 1.2.30）→ `edgeone login --site china|global` →
`edgeone pages deploy -n <project-name>` → 输出 `EDGEONE_DEPLOY_URL`。

```powershell
cd <项目根>
edgeone whoami                       # 1) 非交互检查登录
edgeone login --site china           # 2) 未登录才调，必须带 --site
edgeone pages deploy -n <project-name>   # 3) 首次部署，自动创建 edgeone.json
```

⚠️ **不要调 `edgeone pages init`**（交互式，子 shell 会卡死）。  
⚠️ **`--site` 仅 `edgeone login` 接受**，`deploy` / `env *` 都不接。  
⚠️ **不存在 `edgeone pages project list`**，要查项目去控制台。

首次 deploy 成功后会拿到 `EDGEONE_DEPLOY_URL`，但此时访问 API 会 500 /
`MY_KV is not defined` —— 这是预期的，继续 4.2。

#### 4.2 在控制台创建 + 绑定 KV 命名空间（项目已存在，可以绑了）

> ⚠️ `edgeone.json` 没有 `kvNamespaces` / `bindings` 字段，`edgeone` CLI 也
> 不支持创建 / 绑定 KV。**只能** 在控制台手动绑。

提示用户按下列顺序操作：

1. 打开 EdgeOne Pages 控制台
   - 国内站：<https://console.cloud.tencent.com/edgeone/pages?tab=kv>
   - 国际站：<https://console.intl.cloud.tencent.com/edgeone/pages?tab=kv>
2. **Pages → KV 存储 → 创建命名空间**，名字建议 `mall_kv`。
3. 进入 4.1 创建好的 Pages 项目 → **设置 → 环境变量与绑定 → KV 绑定 → 添加绑定**：
   - **Binding Name 必须是 `MY_KV`**（与 `edge-functions/api/[[default]].js`
     里引用的全局变量一致，**不要改名**）
   - 命名空间选中上一步创建的 `mall_kv`
4. 保存即可，**这里不要**点重新部署 —— 让 4.4 一次性触发。

> 环境变量（`ADMIN_PASSWORD`、`JWT_SECRET` 等）**不要**在控制台手动添加，
> 由 4.3 接管。

#### 4.3 由本 Skill 把 secret 写进项目代码（agent 必做，不要停）

> 背景：`edgeone.json` 的官方 schema **没有** `env` 字段，运行时不读；
> `edgeone pages env add` 又要让用户跑去控制台逐项确认。
> 本 Skill 的方案是 **agent 直接把 secret 写进项目里两处文件**，4.4 重新
> deploy 时随包一起上传 → Cloud / Edge Function 启动立即可见，
> **零控制台动作、零额外提问**。

⚠️ **`.gitignore` 已预置这两个 secret 文件**，agent 必须确认项目根
`.gitignore` 包含以下两行（模板已自带）；缺失则追加：

```
cloud-functions/app/core/_secrets.py
edge-functions/api/_secrets.local.js
```

Agent 必须**在 4.2 之后立刻执行**下列流程，**禁止**再次弹问用户密码
（步骤 1 已经一次性收齐 `default_admin_username` / `default_admin_password` /
`admin_panel_password`，直接复用）：

1. **本地生成两个机器 secret**（每次部署都要新生成，不要复用旧值）：

   ```bash
   python -c "import secrets;print(secrets.token_hex(32))"   # JWT_SECRET
   python -c "import secrets;print(secrets.token_hex(32))"   # INTERNAL_KEY
   ```

2. **写 Cloud Function 端 secret 文件**：覆写
   `cloud-functions/app/core/_secrets.py`：

   ```python
   # AUTO-GENERATED at deploy time. Do NOT commit.
   JWT_SECRET          = "<第 1 步生成>"
   INTERNAL_KEY        = "<第 1 步生成>"
   ADMIN_INIT_USERNAME = "<步骤 1 default_admin_username>"
   ADMIN_INIT_PASSWORD = "<步骤 1 default_admin_password>"
   ADMIN_PASSWORD      = "<步骤 1 admin_panel_password>"
   KV_NAMESPACE        = "mall_kv"   # 与 4.2 控制台绑定一致
   STORAGE_MODE        = "kv"
   # 可选（启用 S3 时取消注释）：
   # S3_ENDPOINT  = "..."
   # S3_BUCKET    = "..."
   # S3_ACCESS_KEY = "..."
   # S3_SECRET_KEY = "..."
   # BACKUP_PASSWORD = "..."
   ```

   `app/core/config.py` 启动时会自动 import 这个文件并把所有键
   `os.environ.setdefault(...)` 注入进程环境，FastAPI 各模块（`storage/kv.py`、
   `admin_auth.py`、`deps.py`）通过 `os.environ.get` 全部能读到。

3. **写 Edge Function 端 secret**：把第 1 步生成的 `INTERNAL_KEY` /
   `JWT_SECRET` 直接 inline 替换 `edge-functions/api/[[default]].js`
   顶部的两行（**不要新建文件**，EdgeOne edge runtime 不支持 import）：

   ```js
   // 在 [[default]].js 顶部找到这两行（默认值）：
   let INTERNAL_KEY = 'EdgeOneMall_internal_2026';
   let JWT_SECRET = '';

   // 替换为：
   let INTERNAL_KEY = '<第 1 步生成的 INTERNAL_KEY>';
   let JWT_SECRET   = '<第 1 步生成的 JWT_SECRET>';
   ```

   两端 `INTERNAL_KEY` / `JWT_SECRET` 必须严格一致，否则 Edge ↔ Cloud
   互调会全部 401。

> Agent **不要**把这些 secret 写进 git、commit message 或对话回显，
> 仅允许停留在 `_secrets.py` / 已 inline 的 `[[default]].js` 与用户本地
> 工作区。

#### 4.4 第二次 deploy（让 KV 绑定 + secret 同时生效）

```powershell
cd <项目根>
edgeone pages deploy
```

> 验证：`Invoke-RestMethod 'https://<EDGEONE_DEPLOY_URL>/api/v1/categories'`
> （PowerShell）或 `curl https://<EDGEONE_DEPLOY_URL>/api/v1/categories`
> （bash）返回包含 7 条默认分类的 JSON 即通过。返回 502/544 →
> 看 4.5 自检表。

> ⚠️ **必须立即 curl 一次 API 触发 seed**。Cloud Function 的 KV 写入是
> "回调" Edge Function 的 HTTP 代理（Python runtime 没有 MY_KV 绑定），
> seed_data 必须等到第一个真实请求经过 Edge Function 才能拿到
> `X-Internal-Origin` 进而写 KV。CLI 部署完成后没有访客 → KV 永远是空。
> 因此 agent 部署成功后**必须调一次**：
>
> ```powershell
> # PowerShell（推荐）
> Invoke-RestMethod 'https://<EDGEONE_DEPLOY_URL>/api/v1/system/bootstrap'
> ```
>
> ```bash
> # macOS / Linux
> curl https://<EDGEONE_DEPLOY_URL>/api/v1/system/bootstrap
> ```
> 临时域名要记得带token
> 这个端点幂等：首次调用执行 seed 并写入 `system:bootstrap_done` 标记，
> 后续调用直接返回 `{"first": false}`。如果以后需要强制重 seed，登录后台
> 调 `POST /api/v1/admin/system/reseed`。

#### 4.5 自检（agent 必做）

> ⚠️ **Windows / PowerShell 不要用 `curl -s`**。PowerShell 5.1 把 `curl`
> 别名成 `Invoke-WebRequest`，不识别 `-s`，且 stderr 会被 CLIXML 序列化
> 成 `#< CLIXML ...` 噪音，agent 会误判为失败而卡死。所有验证 HTTP 请求
> 必须用：
>
> ```powershell
> Invoke-RestMethod -Uri 'https://<EDGEONE_DEPLOY_URL>/api/v1/' -Method GET
> ```
>
> 或 macOS / Linux 上的 `curl https://...`（不带 `-s`，直接看到 body）。

1. `Invoke-RestMethod 'https://<EDGEONE_DEPLOY_URL>/api/v1/'` → 期望
   `{message: 'EdgeOne Mall API is running', ...}`。返回 503 → `ADMIN_PASSWORD`
   漏写；返回 502/544 → Cloud Function 启动失败，看控制台日志。
2. `Invoke-RestMethod 'https://<EDGEONE_DEPLOY_URL>/api/v1/system/bootstrap'`
   → 期望 `{data: {bootstrapped: True, first: True | False, ...}}`。
   `first: True` 表示本次完成首次 seed；`first: False` 表示之前已 seed 过。
3. （可选）`Invoke-RestMethod 'https://<EDGEONE_DEPLOY_URL>/api/v1/skills'`
   返回 `{data: {items: [...]}}`，items 内有 5 个种子商品 → 完全 OK。

如果用户想在部署前先本地预览，改用 `edgeone-pages-dev`。两个 Skill 的核心
指令分别在 `references/edgeone-pages-deploy.md` 和 `references/edgeone-pages-dev.md`
中原文给出。

##### ⚠️ Windows / 非交互终端调用 `edgeone` CLI 的硬性规则

Agent 在 Windows PowerShell（或任何非 TTY 子进程）中跑 `edgeone` 时，必须遵守：

1. **检查登录状态用 `edgeone whoami`，不要用 `edgeone login --check`** ——
   后者在未登录时会强制进入交互菜单（`Choose your login site`），子 shell 没有
   TTY 时箭头键被吞，命令永远不会返回，看起来就是"卡住"。
2. **登录命令必须显式带 `--site china` 或 `--site global`**，否则同样会卡在
   站点选择菜单。
3. **不要用 `bash -c "edgeone ..."` 包裹**。在 PowerShell 里用 `bash` 包裹会
   丢失 TTY，并把 stderr 序列化成 `#< CLIXML ...` 噪音，误导诊断。直接在
   PowerShell / cmd 里调用 `edgeone`。
4. **不要给 `edgeone` 命令加 `2>&1`**。PowerShell 的 stderr 重定向会触发
   CLIXML 序列化，把正常的彩色提示变成无法解析的 XML。
5. **`edgeone pages init` 是交互式命令，绝不要调**。首次部署用
   `edgeone pages deploy -n <project-name>`，会自动创建 `edgeone.json`。
6. **`--site` 仅 `edgeone login` 接受**。勿加到 `deploy` / `init` / `env`
   / `whoami` 上。
7. **HTTP 自检禁止用 `curl -s`**。PowerShell 5.1 把 `curl` 别名为
   `Invoke-WebRequest`，不识别 `-s` 参数，且 stderr 会被序列化成 `#< CLIXML`
   导致 agent 误判失败。统一用 `Invoke-RestMethod '...'`（PowerShell）
   或在 macOS / Linux 用 `curl https://...`（不带 `-s`）。

如果遇到"已登录但 deploy 仍报 auth 错"或 `whoami` 显示意外账号，是浏览器
session 复用了另一个站点的旧 cookie：让用户在登录页点「使用其他账户登录」，
或先从两个腾讯云控制台都退出后重新 `edgeone login --site <china|global>`。

### 步骤 5 — 首页 3D 模型

首次冷启动 seed 自动写入 KV（GLB 见
[`templates/cloud-functions/app/seed/assets/logo_opt.glb`](templates/cloud-functions/app/seed/assets/logo_opt.glb)，
由 `seed_default_3d_model` 用 `chunked_kv.put_asset` 切片入 KV，并加入
`models3d:list`）。`edgeone.json` 的 `cloudFunctions.python.includeFiles`
已声明 `app/seed/assets/**`，无需额外脚本。要换 Mascot 直接覆盖同名文件再 deploy。

### 步骤 6 — 询问是否启动小程序发布指导

步骤 4.4 自检通过后，主动询问用户（用 IDE 的 ask-question 控件）：

> Web 端 + 后台已上线。是否现在同步发布微信小程序版本？小程序与
Web 端共享同一套 `/api/v1/*` 接口，仅需填微信小程序 AppID 与调试后
上传体验版。
>
> 选项：
> - **是**，agent 立即加载
>   [`references/miniprogram.md`](references/miniprogram.md) 并逐步引导（填 AppID →
>   配置 · `templates/miniprogram/project.config.json` → 修改 `app.js` 中的
>   `apiBase` 为部署域名 → 微信开发者工具预览 → 体验版上传）。
> - **暂不**，仅交付 Web 版本，未来随时在 `/admin` 后台“多端设置”发起。

---

## 错误恢复

| 现象 | 可能原因 | 处理 |
|---|---|---|
| `/admin` 进入空白页 | Vite 多入口未配置 | 检查 `templates/frontend/vite.config.js` 是否含 `rollupOptions.input.admin` |
| 上传图片返回 413 | KV 单 value 1MB 上限触发 | 切到 `storage_mode=s3` 或确认 `chunked_kv.CHUNK_SIZE = 512*1024` |
| `Logo3D` 一直显示 fallback | `/api/v1/models3d/active` 返回 `[]` | 跑步骤 6 推模型；或在 `/admin/models3d` 上传 |
| 首次登录提示 `must_change_password` | 这是预期行为 | 跳到 `/admin/settings` 修改密码后续不再提示 |
| Edge Function 报 `INTERNAL_KEY mismatch` | 前后端 secret 不一致 | 重新生成并同时写入 `cloud-functions/app/core/_secrets.py` 与 `edge-functions/api/[[default]].js` 顶部常量 |
| Edge Function 报 `MY_KV is not defined` | KV 命名空间未在控制台绑定，或 Binding Name 不是 `MY_KV` | 回到步骤 4.1 重新绑定后再让官方 Skill 跑一次 `deploy` |
| `/api/v1/admin/auth/login` 返回 `544 Unknown Status` | Cloud Function 模块加载崩溃（常见原因：`admin_auth.py` 里误用了 `from jose import jwt`，但 `requirements.txt` 只装了 PyJWT） | 改回 `import jwt`（PyJWT），重新部署。这条 bug 同时会让 KV 一直为空（seed 中间件因模块崩溃而从未运行） |
| 部署成功但 KV 命名空间一直是空 | 同上：Cloud Function 启动失败导致 seed 中间件未触发 | 先排查 Cloud Function 日志能否正常 import；修好后访问任意 `/api/v1/*` 即会自动 seed |
| 部署 + 启动都正常但 KV 仍为空 | seed 是惰性的——必须有真实流量经 Edge Function 转发并携带 `X-Internal-Origin` 才会触发 | `Invoke-RestMethod 'https://<deploy_url>/api/v1/system/bootstrap'`（PS）或 `curl https://<deploy_url>/api/v1/system/bootstrap`（bash）一次即可；或登录后台 `POST /api/v1/admin/system/reseed` 强制重 seed |
| `/admin/login` 等深链直访 404 | 缺少 `/admin/:path*` 重写规则 | `templates/edgeone.json` 必须包含 `{"source":"/admin/:path*","destination":"/admin/index.html"}` |
| 部署后 Cloud Function 报 `ModuleNotFoundError` | EdgeOne CLI 不会在云端 build，需要本地 vendor | 在项目根 `pip install -r cloud-functions/requirements.txt -t cloud-functions/.python_packages/`，CLI 会随包上传；或改用 EdgeOne 控制台 Git 集成模式让平台代为 build |
| EdgeOne 函数面板出现两条 Python 路由（`/app/main` + `/fn/*`） | `cloud-functions/app/main.py` 顶部定义了模块级 `app = FastAPI(...)`，被 EdgeOne 自动识别为函数入口 | 删掉 `app/main.py` 末尾的 `app = FastAPI(...)` + `configure_app(app)` 块；唯一合法入口是 `fn/[[default]].py` |
| `/api/v1/system/bootstrap` 持续 544 但其他 API 正常 | 你的实际项目目录里的 `system.py` 是旧版本（没有最新 try/except 防御和 `app.seed.bootstrap` 解耦），或者没把 `templates/` 里改过的文件覆盖到部署目录 | 用 `Copy-Item templates\cloud-functions\... <项目>\cloud-functions\... -Force` 覆盖 `system.py` / `seed/bootstrap.py` / `admin.py` / `app/main.py` 后重新 deploy |

---

## 参考文档（按需加载，**不要**预加载）

仅当用户问题落在对应领域时才用 `read_file` 打开。

- `references/architecture.md` — Web ↔ Edge Function ↔ Cloud Function ↔ KV 数据流
- `references/ui-design-system.md` — 完整 CSS 变量、字体、动画曲线、组件骨架
- `references/api-spec.md` — 全部 REST endpoint + 请求/响应 schema
- `references/data-model.md` — KV key 命名约定（`user:*`, `skill:*`, `order:*`, `models3d:*`, `asset:*`, `site:settings`）
- `references/kv-storage.md` — chunked_kv 协议、512 KB 切片、SHA-256 校验
- `references/admin-guide.md` — 11 个后台面板逐个说明
- `references/payment-dual-mode.md` — 积分 / 现金 / 双支付模式三态切换
- `references/3d-model-management.md` — GLB 上传 / 启用 5 件上限 / 参数（scale, speed, bounds）
- `references/miniprogram.md` — 微信小程序适配与 API 复用
- `references/edgeone-pages-deploy.md` — 转发到官方 Skill 的核心指令
- `references/edgeone-pages-dev.md` — 官方本地开发 Skill 摘要
- `references/seed-data.md` — 5 个演示商品 + 默认管理员 + 默认 3D 模型的注入流程

---

## 内置资产（templates/, scripts/）

- `templates/edgeone.json`             — EdgeOne Pages 项目配置（构建命令、路由重写、缓存头）
- `templates/frontend/`                — 完整 Vue 3 用户端 + admin 子应用（1:1 of OpenClaw）
- `templates/cloud-functions/`         — FastAPI 应用 + 分块 KV + 管理鉴权 + 3D 模型 API
- `templates/edge-functions/`          — Edge Function 代理 + JWT 校验
- `templates/cloud-functions/app/seed/assets/logo_opt.glb` — 首页默认 3D Mascot（首次冷启动自动写入分块 KV）
- `templates/miniprogram/`             — 微信小程序工程（步骤 6 可选试发布）

> **不要**提交用户特定的 `.env` / 生成的 secret。每次新项目都要重新生成。
