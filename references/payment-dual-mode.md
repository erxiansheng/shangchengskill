# Payment Dual Mode

商品维度三态销售模式：

```
sale_mode ∈ {"points", "cash", "both"}
```

## Schema 校验（`cloud-functions/app/schemas/product.py`）

```python
@model_validator(mode="after")
def _check(self):
    if self.sale_mode in ("cash", "both") and (self.cash_price_yuan or 0) <= 0:
        raise ValueError("cash_price_yuan must be > 0 when sale_mode includes cash")
    if self.sale_mode in ("points", "both") and (self.points_price or 0) <= 0:
        raise ValueError("points_price must be > 0 when sale_mode includes points")
    return self
```

## 前端展示

- `sale_mode == "points"` → 仅显示积分价（`<JetBrainsMono> 100 P </JetBrainsMono>`）
- `sale_mode == "cash"`   → 仅显示现金价 `¥9.90`
- `sale_mode == "both"`   → 同时显示，下方有切换按钮，进入结算页时携带选择

## 结算流程

1. 前端 `POST /api/v1/skills/{id}/purchase` 带 `pay_method`
2. 后端：
   - `pay_method=points`：检查 `points:{uid}` ≥ price → 扣减 → 写 order/`pay_method=points`
   - `pay_method=cash`：创建 `recharge:{id}` 等待第三方支付回调 → 回调成功后写 order
3. 商家结算：`platform_fee_rate`（默认 5%）扣除后入 `user.balance_yuan`，可
   通过 `/withdrawals` 提现

## 第三方支付配置

`site:settings.wechat_pay` / `alipay` 字段，全部默认空字符串。
启用前由管理员在 `/admin/settings` 填入。

> **安全提示**：模板中 `wechat_pay.key`、`alipay.private_key` 必须保留为空
> 字符串。任何 PR 把真实密钥硬编码进 `templates/` 都应被拒绝。
