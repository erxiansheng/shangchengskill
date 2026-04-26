# Admin Console Guide

后台是 **完全独立的 Vue sub-app**，挂载在 `/admin/*`，与 storefront **不共享
任何 token / store / router**。

## 入口

- HTML：`templates/frontend/admin/index.html`
- 启动脚本：`templates/frontend/admin/main.js`
- Vite 多入口：`vite.config.js → rollupOptions.input.admin`
- 构建产物：`dist/admin/index.html`

## 鉴权

- 调 `POST /api/v1/admin/auth/login`
- 成功后 `localStorage["edgeone_mall_admin_token"]` 保存 JWT
- 路由前置守卫（见 `admin/main.js`）：未登录 → `/admin/login`
- JWT 必须含 `scope: "admin"`，普通 storefront token 即使有效也会被
  `get_current_admin` 依赖拒绝（403）

## 默认管理员

由环境变量在第一次启动时种入：

```env
ADMIN_INIT_USERNAME=root
ADMIN_INIT_PASSWORD=ChangeMeNow!2025
```

记录写入 `admin:{username}` 并打 `must_change_password: true` 标记。
登录返回的 `data.must_change_password` 会引导前端弹窗强制改密。

## 11 个面板

| Path | 调用 endpoint | 关键能力 |
|---|---|---|
| `/admin/dashboard` | `GET /admin/stats` | 总用户/总订单/今日 GMV/积分流水折线 |
| `/admin/users` | `GET /admin/users`、`PATCH /admin/users/{uid}` | 角色切换、封禁、积分调整 |
| `/admin/products` | `GET/PATCH/DELETE /admin/skills/...` | 全量商品 CRUD、强制下架 |
| `/admin/audit` | `GET /admin/skills/pending`、`POST .../approve|reject` | 待审核商品流水线 |
| `/admin/orders` | `GET /admin/orders` | 按支付方式/状态过滤 |
| `/admin/recharges` | `GET /admin/recharges` | 现金充值订单 |
| `/admin/withdrawals` | `GET/POST /admin/withdrawals/{id}/(approve|reject)` | 提现审批 |
| `/admin/reviews` | `GET/DELETE /admin/reviews` | 删评论、处理举报 |
| `/admin/models3d` | `GET/POST/PUT/DELETE /admin/models3d` | GLB 上传、参数调整、启用/禁用（≤5 同时启用）|
| `/admin/settings` | `GET/PATCH /admin/settings` | storage_mode、登录方式开关、第三方 Key、汇率 |
| `/admin/backup` | `POST /admin/backup/export|import` | KV 全量 dump/restore |

## 一致性约束

后台所有面板**禁止**直接读写 KV——必须经过 `/api/v1/admin/*` REST 端点，
否则会跳过审计日志（`audit:log:*`）。

## 主题

后台沿用 storefront 的 CSS 变量；通过 `localStorage["edgeone_mall_theme"]`
切换 `dark` / `light`。**不允许**为了「专业感」改成纯灰白，霓虹绿是品牌识别。
