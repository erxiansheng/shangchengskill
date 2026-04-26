# edgeone-mall

> **一个 Anthropic 格式的 Skill，让任意 AI 编码 Agent 在腾讯 EdgeOne Pages
> 上脚手架出一个生产级、霓虹赛博风格的在线商城——Vue 3 用户端 + 独立 Vue
> 后台控制台 + FastAPI Cloud Function + 微信小程序 + 分块 KV 资产存储，
> S3 零配置可选。**

本仓库是面向 **EdgeOne Pages Skills** 比赛的双赛道投稿：

- **Skills 赛道** — `SKILL.md` + `templates/` + `references/`
- **Prompts 赛道** — [`PROMPT.md`](./PROMPT.md)，与 Skill 等效的纯 Prompt
  独立版，无需打包资产即可复现同一产出。

---

## 🚀 快速上手

```bash
# 1. Agent 加载 SKILL.md，问 6 个问题（商城名、主题、登录方式…）。
# 2. Agent 把 templates/ 复制进你的项目，跑全局重命名，安装依赖。
# 3. Agent 移交给官方 edgeone-pages-deploy Skill 完成部署。
# 4. Cloud Function 首次冷启动会自动把内置的 logo_opt.glb 写进 KV，首页
#    3D Mascot 立刻可用 —— 无需再跑任何脚本。
```

如果你的 Agent 还不支持 Skills，把 [`PROMPT.md`](./PROMPT.md) 原样粘到
ChatGPT / Claude / GitHub Copilot Chat 里——它能从零起一份等效的项目。

---

## 🧩 内含什么

```
edgeone-mall/
├── SKILL.md                        ← Anthropic Skill 清单（Agent 入口）
├── PROMPT.md                       ← Prompts 赛道独立版
├── README.md                       ← （你正在看的）
├── LICENSE                         ← MIT
├── references/                     ← 12 份按需加载的深度文档
│   ├── architecture.md
│   ├── ui-design-system.md
│   ├── api-spec.md
│   ├── data-model.md
│   ├── kv-storage.md
│   ├── admin-guide.md
│   ├── payment-dual-mode.md
│   ├── 3d-model-management.md
│   ├── miniprogram.md
│   ├── edgeone-pages-deploy.md
│   ├── edgeone-pages-dev.md
│   └── seed-data.md
├── templates/                      ← Agent 复制的内置资产
│   ├── edgeone.json                ← EdgeOne Pages 项目配置
│   ├── frontend/                   ← Vue 3 用户端 + /admin 子应用（多入口 Vite）
│   ├── cloud-functions/            ← FastAPI 应用、分块 KV、admin 鉴权、3D 模型 API
│   ├── edge-functions/             ← Edge Function 代理 + JWT
│   ├── miniprogram/                ← 微信小程序
│   └── seed/                       ← 部署后 seed CLI
└── scripts/                        ← Skill 打包辅助
```

---

## ✨ 亮点

| 特性 | 说明 |
|---|---|
| 与 OpenClaw / Skill 交易参考项目 1:1 视觉复刻 | 霓虹绿 `#1EE07F` + 赛博青 + 粒子背景 + 倾斜玻璃卡 + Orbitron 标题 |
| **独立的** admin 子应用 | 独立 Vue 入口、独立 JWT scope、可深链的面板 |
| **不依赖 S3** | 默认 `storage_mode=kv`，按 512 KB base64 切片塞 KV |
| **保留 S3 切换** | 后台可随时切回 S3，无需重新部署 |
| **账号密码鉴权始终可用** | 即使所有 OAuth 提供方都关闭 |
| **每件商品双支付模式** | `sale_mode ∈ {points, cash, both}`，schema 层强制 |
| **3D 模型管理** | 后台同时启用 ≤ 5 个 GLB，参数（scale/speed/bounds）可调 |
| **与官方 Skill 串联** | 移交给 `edgeone-pages-deploy` / `edgeone-pages-dev` |

---

## 📦 关于 EdgeOne Pages 部署 & KV

- 项目根有 `templates/edgeone.json`，按官方文档定义了 `buildCommand` /
  `outputDirectory` / `rewrites` / `headers` / `cloudFunctions` 等字段。
- **KV 命名空间无法通过 `edgeone.json` 配置**，必须在 EdgeOne Pages 控制台
  手动创建并绑定为 `MY_KV`。完整步骤已写在 `SKILL.md` 步骤 4.1，由
  `edgeone-pages-deploy` Skill 流程统一引导。
- 部署 CLI：`npm install -g edgeone@latest`（≥ 1.2.30），然后
  `edgeone login` → `edgeone pages init` → `edgeone pages deploy`。

---

## 📜 License

MIT — 见 [LICENSE](./LICENSE)。

`templates/` 内置资产派生自同作者的开源项目 OpenClaw / Skill 交易，
为 Skill 分发重新以 MIT 协议授权。

`references/edgeone-pages-deploy.md` 与 `references/edgeone-pages-dev.md`
摘录自官方 **腾讯 EdgeOne Pages Skills**
(<https://github.com/TencentEdgeOne/edgeone-pages-skills>)，按其原协议
署名引用。
