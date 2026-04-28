# EdgeOne Pages Deploy (handoff)

> **Source of truth**：本文件**不**复制官方 Skill 的全部内容，请始终通过
> `https://github.com/TencentEdgeOne/edgeone-pages-skills` 获取最新版本。

## 触发方式

在用户的 agent 中，执行：

```
Install this skill: https://github.com/TencentEdgeOne/edgeone-pages-skills, then deploy to EdgeOne Pages.
```

## 我们对 deploy skill 的输入约定

`edgeone-mall` 准备好的源码布局正好匹配官方 deploy skill 的预期：

```
<project-root>/
├── frontend/                      # Vue 3 + Vite 源码；deploy 时自动安装依赖并 build
│   └── index.html                 # storefront 入口，内置 /admin 管理模块
├── cloud-functions/
│   └── fn/[[default]].py          # 自动注册为 Python Cloud Function
├── edge-functions/
│   └── api/[[default]].js         # 自动注册为 Edge Function
└── edgeone.json                   # 模板自带 buildCommand / outputDirectory / rewrites
```

## 自动构建与依赖安装边界

- 前端依赖：不要让 agent 预先本地执行 `npm install` / `npm run build`。模板的
   `edgeone.json` 已写入 `buildCommand: "cd frontend && npm install && npm run build"`、
   `installCommand: "echo skip-root-install"`、`outputDirectory: "frontend/dist"`，
   `edgeone pages deploy` 会在部署构建流程中生成 `frontend/dist`。
- Python 依赖：只维护 `cloud-functions/requirements.txt`。EdgeOne Pages 构建
   Python Cloud Function 时会自动读取并安装，不要把 `.venv`、`site-packages` 或
   `.python_packages` vendor 进项目。
- `edgeone.json` 的 `rewrites.source` 可使用 `*`，例如 `/skill/*`，
   但 `rewrites.destination` 必须是具体文件路径。不要使用 Vercel / Next 风格
   `:path*`，也不要配置 `{"source":"/api/*","destination":"/api/*"}` 这类 no-op rewrite。

## 部署前必做的人工动作（CLI / skill 都做不了）

KV 命名空间的**创建与绑定** `edgeone.json` 不支持、CLI 也不支持，必须在
EdgeOne Pages 控制台手动完成：

1. **Pages → KV 存储 → 创建命名空间**，名字记下来（例如 `mall_kv`）。
2. 项目 **设置 → 环境变量与绑定 → KV 绑定 → 添加绑定**：
   - **Binding Name 必须填 `MY_KV`**（与
     `templates/edge-functions/api/[[default]].js` 引用一致，不要改）
   - 命名空间选第 1 步创建的那个
3. 保存后让 deploy skill 再跑一次 `deploy` 让绑定生效。

## 必须传给 deploy skill 的环境变量

| Key | 说明 |
|---|---|
| `KV_NAMESPACE` | 上一步在控制台创建的命名空间名（例如 `mall_kv`） |
| `JWT_SECRET` | 32 字节十六进制 |
| `INTERNAL_KEY` | Edge ↔ Cloud 内部认证 |
| `STORAGE_MODE` | 默认 `kv` |

## 部署后必做

1. 访问 `https://<your-domain>/api/v1/` → 应返回 `EdgeOne Mall API is running`
2. 打开站点注册第一个账号 → 自动成为管理员
3. 使用第一个注册账号登录前台，访问 `/admin` 进入内置管理模块
4. （可选）如需替换首页默认 3D Mascot，覆盖
   `templates/cloud-functions/app/seed/assets/logo_opt.glb` 重新部署。首次
   冷启动 seed 会自动写入 KV，无需运行额外脚本。
5. （可选）打开 `/admin/settings` 切换 `storage_mode` 到 `s3`，并填入 S3 凭证

## 与 dev skill 的关系

如果用户想本地预览，转用 `edgeone-pages-dev`：

```
Use the edgeone-pages-dev skill to start a local preview of this project.
```

它会启动 wrangler 等价的本地 KV 模拟器 + Edge Function dev server，
storefront 和 admin 同域名挂载。

## 故障排查

| 现象 | 处理 |
|---|---|
| Deploy 后 `/api/v1/*` 502 | 检查 Cloud Function 日志，多半是 `requirements.txt` 缺包 |
| `MY_KV is not defined` (Edge) | KV namespace 未绑定，重新跑 `wrangler kv namespace create` 等价命令 |
| 首页显示 fallback Logo 一直加载失败 | Cloud Function 首次 seed 失败（看控制台日志中 `[Seed]` 行），或者后台手动删了 mascot；在 `/admin/models3d` 重新上传 GLB 即可 |
