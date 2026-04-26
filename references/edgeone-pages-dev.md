# EdgeOne Pages Dev (handoff)

> 与 deploy 同源，参考 `https://github.com/TencentEdgeOne/edgeone-pages-skills`。

## 何时用

- 用户想在推线上前做本地预览
- 调试 Edge Function ↔ Cloud Function 的 `INTERNAL_KEY` 链路
- 验证 KV 数据迁移脚本

## 触发

```
Use the edgeone-pages-dev skill to start a local preview of this project.
```

## 期望行为

dev skill 会：

1. 启动一个本地 KV 模拟器（与生产 KV 协议兼容）
2. 把 `edge-functions/api/[[default]].js` 跑在 `http://localhost:8787`（或
   自动选端口）
3. 把 `cloud-functions/fn/[[default]].py` 通过 uvicorn 跑在
   `http://localhost:8000`
4. 把 `frontend/` 通过 `vite` 跑在 `http://localhost:5173`，并将 `/api/*`
   反向代理到 Edge Function 端口

## 与本 Skill 的差异

`edgeone-mall` **不复制** dev skill 的本地服务，它依赖官方 dev skill 完成
环境编排，仅负责保证模板里的：

- `vite.config.js` 的 `server.proxy` 已正确配置
- `cloud-functions/app/main.py` 默认监听 `0.0.0.0`
- 所有相对路径 `/api/v1/*` 不带域名硬编码

## 调试切入点

| 想看什么 | 怎么做 |
|---|---|
| Edge Function 收到的请求 | 在 `[[default]].js` `addEventListener('fetch', e=>console.log(e.request.url))` |
| Cloud Function 收到的请求 | uvicorn 默认会打 access log |
| KV 当前内容 | 调 `GET /__kv/list` (如果 dev skill 提供) 或在 admin/backup 导出 |
