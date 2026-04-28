# KV Data Model

EdgeOne KV is the **single source of truth**. No relational DB.

## Key naming conventions

| Prefix | Value type | Notes |
|---|---|---|
| `user:{uid}` | JSON | 用户主体 |
| `user:by_email:{email}` | string (uid) | 邮箱反查索引 |
| `user:by_username:{username}` | string (uid) | 账号反查索引 |
| `admin:{username}` | JSON | 管理员主体（独立空间，不与 user 混） |
| `skill:{id}` | JSON | 商品（保留 `skill:` 前缀以兼容历史代码） |
| `skill_approved_listdata` | JSON array | 已审核上架商品 ID 列表 |
| `skill:pending_listdata` | JSON array | 待审核 |
| `order:{id}` | JSON | 订单（含 `pay_method ∈ {points, cash}`） |
| `order:by_user:{uid}` | JSON array | 用户订单索引 |
| `recharge:{id}` | JSON | 充值订单 |
| `withdraw:{id}` | JSON | 提现申请 |
| `review:{skill_id}:{review_id}` | JSON | 评论 |
| `points:{uid}` | int | 积分余额 |
| `points:log:{uid}:{ts}` | JSON | 积分流水 |
| `asset:{id}:meta` | JSON | chunked KV 资产元数据 |
| `asset:{id}:chunk:{n}` | base64 string | 资产分片 |
| `models3d:item:{id}` | JSON | 单个 3D 模型 |
| `models3d:list` | JSON array | 模型 ID 列表 |
| `site:settings` | JSON | 站点设置（storage_mode、登录方式开关、theme、汇率…） |
| `seed:initialized` | string | 首次种子完成标记，避免重复 seed |

## 典型实体 schema

### user

```json
{
  "id": "u_abc123",
  "username": "alice",
  "email": "alice@example.com",
  "password_hash": "$2b$12$...",
  "nickname": "Alice",
  "avatar_url": "/api/v1/assets/asset_xxx",
  "role": "user",                   // user | seller | admin
  "level": 1,
  "exp": 0,
  "balance_yuan": 0,
  "points": 0,
  "created_at": "2025-..."
}
```

### admin

不再单独存储 `admin:*` 账号。管理员身份写在普通 `user:{id}` 记录上：首个注册用户自动获得
`role: "admin"`，后续管理员也通过用户角色授权。

### skill (product)

```json
{
  "id": "skill_xxx",
  "owner_uid": "u_...",
  "title": "...",
  "description": "...markdown...",
  "cover_url": "/api/v1/assets/...",
  "images": ["/api/v1/assets/..."],
  "category": "桌游",
  "tags": ["策略","双人"],
  "sale_mode": "both",              // points | cash | both
  "points_price": 100,
  "cash_price_yuan": 9.9,
  "stock": 100,
  "status": "approved",             // pending | approved | rejected | draft
  "_demo": false                    // 种子商品标记
}
```

### asset:{id}:meta

```json
{
  "content_type": "image/jpeg",
  "size": 1234567,
  "sha256": "abc...",
  "chunks": 3,
  "created_at": "..."
}
```

### models3d:item:{id}

```json
{
  "id": "m_xxx",
  "name": "Default Mascot",
  "asset_id": "asset_xxx",
  "asset_url": "/api/v1/assets/asset_xxx",
  "scale": 1.0,
  "speed_xyz": [1.2, 0.6, 0.3],
  "bounds_xyz": [[-3.5, 3.5], [0.3, 3.5], [-2.0, 1.5]],
  "enabled": true,
  "created_at": "..."
}
```

### site:settings (excerpt)

```json
{
  "storage_mode": "kv",
  "loginMethods": { "password": true, "email": true, "wechat": false, "apple": false, "google": false },
  "points_per_yuan": 10,
  "platform_fee_rate": 0.05,
  "wechat_pay": { "appid": "", "mchid": "", "key": "" },
  "alipay":     { "appid": "", "private_key": "", "public_key": "" },
  "smtp":       { "host": "", "port": 0, "user": "", "pass": "" },
  "s3":         { "endpoint": "", "bucket": "", "access_key": "", "secret_key": "" }
}
```
