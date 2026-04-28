# Admin Console Guide

后台是主 Vue SPA 内置管理模块，挂载在 `/admin`，与 storefront 使用同一套路由、登录态和组件体系。

## 入口

- 路由：`templates/frontend/src/router/index.js` 中的 `/admin`
- 组件：`templates/frontend/src/views/Admin.vue`
- 构建产物：主 SPA `dist/index.html`

## 鉴权

- 使用前台登录态（`EdgeOneMall_token`）访问 `/admin`
- 未登录会跳转 `/login`
- 用户必须是首个注册用户（`id=1`）或 `role=admin`；后台、前台管理模块、备份和导入均不需要二次密码

## 管理员产生方式

不要预置管理员账号。第一个通过 `/api/v1/auth/register` 注册成功的真实用户会自动获得 `role=admin`，
这个账号就是站长账号。

## 11 个面板

| Path | 调用 endpoint | 关键能力 |
|---|---|---|
| `/admin` 内仪表盘 | `GET /admin/stats` | 总用户/总订单/今日 GMV/积分流水折线 |
| `/admin` 内用户管理 | `GET /admin/users`、`PATCH /admin/users/{uid}` | 角色切换、封禁、积分调整 |
| `/admin` 内商品管理 | `GET/PATCH/DELETE /admin/skills/...` | 全量商品 CRUD、强制下架 |
| `/admin` 内审核 | `GET /admin/skills/pending`、`POST .../approve|reject` | 待审核商品流水线 |
| `/admin` 内订单/充值/提现/评论 | `GET /admin/orders` 等 | 列表、筛选、审批与删除 |
| `/admin` 内 3D 模型 | `GET/POST/PUT/DELETE /admin/models3d` | GLB 上传、参数调整、启用/禁用（≤5 同时启用）|
| `/admin` 内设置 | `GET/PATCH /admin/settings` | storage_mode、登录方式开关、第三方 Key、汇率 |
| `/admin` 内备份 | `POST /admin/backup` `/admin/backup/chunk` `/admin/restore` | KV 全量 dump/restore |

## 一致性约束

后台所有面板**禁止**直接读写 KV——必须经过 `/api/v1/admin/*` REST 端点，
否则会跳过审计日志（`audit:log:*`）。

## 主题

后台沿用 storefront 的 CSS 变量；通过 `localStorage["edgeone_mall_theme"]`
切换 `dark` / `light`。**不允许**为了「专业感」改成纯灰白，霓虹绿是品牌识别。
