# EdgeOne Pages Deploy (handoff)

> **Source of truth**：本文件**不**复制官方 Skill 的全部内容，请始终通过
> `https://github.com/TencentEdgeOne/edgeone-pages-skills` 获取最新版本。

## 触发方式

在用户的 agent 中，执行：

```
Install this skill: https://github.com/TencentEdgeOne/edgeone-pages-skills, then deploy to EdgeOne Pages.
```

## 我们对 deploy skill 的输入约定

`edgeone-mall` 准备好的产物布局正好匹配官方 deploy skill 的预期：

```
<project-root>/
├── frontend/dist/                 # 静态资源根
│   ├── index.html                 # storefront 入口
│   └── admin/index.html           # admin 入口
├── cloud-functions/
│   └── fn/[[default]].py          # 自动注册为 Python Cloud Function
├── edge-functions/
│   └── api/[[default]].js         # 自动注册为 Edge Function
└── edgeone.json                   # （由 deploy skill 生成）
```

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
| `ADMIN_INIT_USERNAME` | 默认管理员账号 |
| `ADMIN_INIT_PASSWORD` | 默认管理员密码（≥12 位） |
| `ADMIN_PASSWORD` | 后台二次验证密码，由部署者手动输入，AI 不要代填 |
| `STORAGE_MODE` | 默认 `kv` |

## 部署后必做

1. 访问 `https://<your-domain>/api/v1/` → 应返回 `EdgeOne Mall API is running`
2. 访问 `/admin` → 重定向到 `/admin/login`，用 init 凭证登录
3. 在 `/admin/settings` **立即修改密码**
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
