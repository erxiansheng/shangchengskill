# Seed Data

`edgeone-mall` 在第一次启动时（`seed:initialized` 不存在）自动注入：

## 1. 管理员账号

Seed 阶段不创建管理员账号。第一个通过 `/api/v1/auth/register` 注册成功的真实用户会自动获得 `role=admin`。

## 2. 演示商品（5 个）

`cloud-functions/app/seed/bootstrap.py::DEMO_PRODUCTS`，覆盖所有销售模式：

| ID | sale_mode | 用途 |
|---|---|---|
| `skill:demo1` | `points` | 纯积分商品 |
| `skill:demo2` | `cash`   | 纯现金商品 |
| `skill:demo3` | `both`   | 双模式商品 |
| `skill:demo4` | `points` | 0 积分（赠品） |
| `skill:demo5` | `cash`   | 优惠券商品 |

每个都打 `_demo: true`，方便后台一键清理。
ID 同步追加到 `skill_approved_listdata`。

## 3. 默认 3D Mascot

首次冷启动时从
`templates/cloud-functions/app/seed/assets/logo_opt.glb`（随函数包一起上传，
由 `edgeone.json` 的 `cloudFunctions.python.includeFiles` 声明）读取字节，
按 512 KB 切片写入 `asset:{id}:chunk:{n}`，并在 `models3d:list` 中启用。
代码见 [`seed_default_3d_model`](../templates/cloud-functions/app/seed/__init__.py)。

替换默认 Mascot 直接覆盖同名文件重新部署；运行时上传更多 GLB 走
`/admin/models3d`。

## 4. 站点设置默认值

`cloud-functions/app/main.py::default_settings`：

```python
default_settings = {
    "storage_mode": "kv",
    "loginMethods": {"password": True, "email": True, "wechat": False, "apple": False, "google": False},
    "points_per_yuan": 10,
    "platform_fee_rate": 0.05,
    "wechat_pay": {"appid": "", "mchid": "", "key": ""},
    "alipay":     {"appid": "", "private_key": "", "public_key": ""},
    "smtp":       {"host": "", "port": 0, "user": "", "pass": ""},
    "s3":         {"endpoint": "", "bucket": "", "access_key": "", "secret_key": ""},
}
```

写入 `site:settings`，且后续启动**不会覆盖**（仅当 key 缺失时合并）。

## 重置

```bash
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://<your-domain>/api/v1/admin/seed/reset
```

会清掉 `seed:initialized` 与所有 `skill:demo*`。**不会**清用户创建的真实数据。
