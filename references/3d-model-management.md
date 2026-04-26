# 3D Model Management

首页中央漂浮的 GLB 模型由后台管理，**不再**写死在 `public/logo_opt.glb`。

## 限制

| 项 | 值 |
|---|---|
| 单个 GLB 上限 | 8 MB（`MAX_MODEL_BYTES`） |
| 同时启用上限 | **5 个**（`MAX_ENABLED`） |
| 超出 enabled 上限 | 返回 HTTP 409 + `{ "code": 4090, "message": "max 5 enabled models" }` |

## 后端（`cloud-functions/app/api/v1/models3d.py`）

```
admin_router  -> /admin/models3d
  GET    list
  POST   upload (multipart: file, name, params...)
  PUT    /{id}    update params/enabled
  DELETE /{id}

public_router -> /models3d
  GET /active  -> enabled 列表，按 created_at 升序
```

`upload` 内部走 `chunked_kv.put_asset(file.bytes, "model/gltf-binary")`，
拿到 `asset_id` 后写 `models3d:item:{id}`，再 `models3d:list.append(id)`。

## ModelParams（Pydantic）

```python
class ModelParams(BaseModel):
    scale: float = Field(1.0, gt=0, le=20)
    speed_xyz: tuple[float, float, float] = (1.2, 0.6, 0.3)
    bounds_xyz: tuple[tuple[float,float], tuple[float,float], tuple[float,float]] = (
        (-3.5, 3.5), (0.3, 3.5), (-2.0, 1.5)
    )
    enabled: bool = True
```

## 前端（`templates/frontend/src/components/Logo3D.vue`）

```js
async function resolveModelUrl() {
  try {
    const res = await fetch('/api/v1/models3d/active', { headers: {'cache-control':'no-cache'} })
    if (res.ok) {
      const json = await res.json()
      const list = json?.data || []
      if (list.length > 0 && list[0].asset_url) return list[0].asset_url
    }
  } catch (e) { /* fall through */ }
  return '/logo_opt.glb'   // 最终降级
}
```

只取 `data[0]`，因为同时只有一个模型作为「首页主角」。其余启用的 4 个模型可
被其他页面（例如商品分类导览）按 `tags` 选用——目前模板尚未实现，留作扩展点。

## 默认 3D Mascot 的注入方式

GLB 随 Cloud Function 一起打包（路径：
`templates/cloud-functions/app/seed/assets/logo_opt.glb`，由 `edgeone.json` 的
`cloudFunctions.python.includeFiles` 声明）。首次冷启动时
[`seed_default_3d_model`](../templates/cloud-functions/app/seed/__init__.py)
会：

1. 检查 `models3d:list` 是否为空（幂等）
2. 从 `app/seed/assets/logo_opt.glb` 读取字节
3. 调 `chunked_kv.put_asset` 按 512 KB 切片写入 `asset:{id}:chunk:{n}`
4. 写入 `models3d:item:{id}` 并追加到 `models3d:list`，`enabled: True`

要替换默认 Mascot，直接覆盖同名文件并重新部署即可。随后也可在
`/admin/models3d` 上传更多 GLB（同时启用上限 5 个）。

## 后台面板（`/admin/models3d`）

- 列表显示缩略图（GLB 缩略图自动用 three.js 截图，未实现时回退到通用立方体图标）
- 拖动滑块调整 `scale`、`speed_xyz`，实时预览
- 「启用」复选框：第 6 个尝试启用时弹「最多 5 个」提示
- 删除时同步清理 `asset:{asset_id}:*` 所有 chunks
