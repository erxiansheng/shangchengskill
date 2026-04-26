# API Specification

所有端点统一走 `/api/v1`，响应格式：

```json
{ "code": 0, "message": "ok", "data": { ... } }
```

`code != 0` 即业务失败。HTTP 状态码主要用 200 / 401 / 403 / 404 / 409 / 422。

## 鉴权

- 用户 token：`Authorization: Bearer <jwt>` (scope=`user`, 7d TTL)
- 管理员 token：同 header，但 JWT payload `scope: "admin"` (8h TTL)
- Edge Function 间内调：`X-Internal-Key: <INTERNAL_KEY>`

## 完整端点表

### 公开

| Method | Path | 说明 |
|---|---|---|
| GET | `/` | 健康检查，返回 `EdgeOne Mall API is running` |
| GET | `/assets/{id}` | 流式返回 chunked KV 中的二进制资产 |
| GET | `/models3d/active` | 启用中的 3D 模型列表（无需登录） |
| GET | `/skills` | 商品广场，分页 + 排序 + 分类筛选 |
| GET | `/skills/{id}` | 商品详情 |

### 用户

| Method | Path | 说明 |
|---|---|---|
| POST | `/auth/register` | 账号 + 密码注册（必开） |
| POST | `/auth/login` | 账号 / 邮箱 + 密码登录 |
| POST | `/auth/oauth/{provider}` | 第三方登录（wechat/apple/google），按设置开关启用 |
| GET | `/users/me` | 个人信息 |
| PATCH | `/users/me` | 更新昵称 / 头像 / 简介 |
| GET | `/users/{uid}/profile` | 公开主页 |
| POST | `/upload/image` | 上传图片（按 storage_mode 落 KV 或 S3） |
| POST | `/upload/skill_package` | 上传商品附件 |
| POST | `/skills` | 上架商品 |
| PATCH | `/skills/{id}` | 修改商品 |
| DELETE | `/skills/{id}` | 下架 |
| POST | `/skills/{id}/purchase` | 购买（积分 / 现金 / 双模式） |
| POST | `/skills/{id}/favorite` | 收藏 |
| GET | `/me/favorites` `/me/purchased` `/me/published` | 个人列表 |
| GET | `/points/balance` | 积分余额 |
| POST | `/points/recharge` | 现金充值积分 |
| POST | `/withdrawals` | 提现申请 |
| POST | `/skills/{id}/reviews` | 发表评论 |

### 管理员（需 `scope:"admin"`）

| Method | Path | 说明 |
|---|---|---|
| POST | `/admin/auth/login` | 后台登录 |
| POST | `/admin/auth/change-password` | 强制改密 |
| GET | `/admin/auth/me` | 当前管理员 |
| GET | `/admin/stats` | 仪表盘聚合 |
| GET | `/admin/users` | 用户列表 |
| PATCH | `/admin/users/{uid}` | 角色 / 封禁 |
| GET/PATCH/DELETE | `/admin/skills/...` | 商品管理 |
| GET | `/admin/skills/pending` | 待审核 |
| POST | `/admin/skills/{id}/approve` `/reject` | 审核 |
| GET | `/admin/orders` `/recharges` `/withdrawals` `/reviews` | 列表 + 操作 |
| GET/POST/PUT/DELETE | `/admin/models3d` | 3D 模型管理 |
| GET/PATCH | `/admin/settings` | 站点设置（含 `storage_mode`） |
| POST | `/admin/backup/export` `/import` | KV 全量备份 |

详见各 `cloud-functions/app/api/v1/*.py` 路由源代码。
