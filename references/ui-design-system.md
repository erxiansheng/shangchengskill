# UI Design System

> **目标：1:1 复刻 OpenClaw / Skill 交易项目的视觉风格。** 任何变更必须通过站点设置（site:settings.theme.*）而非硬编码。

## CSS 变量（强制原文照抄到 `templates/frontend/src/style.css :root`）

```css
:root {
  /* 主色 */
  --color-primary:   #1EE07F;            /* 霓虹绿 */
  --color-accent:    #00F0FF;            /* 赛博青 */
  --color-warning:   #FFB800;
  --color-danger:    #FF4757;

  /* 背景 */
  --bg-deep:         #0A0A0E;
  --bg-surface:      #14141A;
  --bg-elevated:     #1C1C24;
  --bg-glass:        rgba(20, 20, 26, 0.65);

  /* 文本 */
  --text-primary:    #FFFFFF;
  --text-secondary:  rgba(255, 255, 255, 0.65);
  --text-tertiary:   rgba(255, 255, 255, 0.40);

  /* 描边 / 阴影 */
  --border-glass:    rgba(255, 255, 255, 0.08);
  --shadow-card:     0 10px 30px rgba(0, 0, 0, 0.35);
  --shadow-neon:     0 0 24px rgba(30, 224, 127, 0.35);

  /* 字体 */
  --font-display:    'Orbitron', system-ui, sans-serif;
  --font-body:       'Inter', system-ui, sans-serif;
  --font-mono:       'JetBrains Mono', Menlo, monospace;

  /* 动效 */
  --transition-smooth: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-bounce: 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

浅色主题（可通过 `[data-theme="light"]` 覆盖，但不是默认）：

```css
[data-theme="light"] {
  --bg-deep:    #F6F7FB;
  --bg-surface: #FFFFFF;
  --bg-glass:   rgba(255, 255, 255, 0.7);
  --text-primary:   #0A0A0E;
  --text-secondary: rgba(10, 10, 14, 0.7);
  --text-tertiary:  rgba(10, 10, 14, 0.45);
  --border-glass:   rgba(0, 0, 0, 0.08);
}
```

## 组件骨架（Tailwind 不参与，纯 CSS）

```css
.glass-panel {
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 16px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: var(--shadow-card);
  transition: var(--transition-smooth);
}
.glass-panel:hover {
  transform: rotateY(2deg) rotateX(1deg) translateY(-2px);
  box-shadow: var(--shadow-neon);
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #000;
  font-weight: 600;
  padding: 10px 18px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  transition: var(--transition-smooth);
}
.btn-primary:hover { box-shadow: var(--shadow-neon); transform: translateY(-1px); }
```

## 字体加载

`index.html` 顶部：

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Orbitron:wght@500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
```

## 粒子背景

`templates/frontend/src/components/ParticlesBackground.vue` 使用纯 canvas，
60 个点，链接距离 120，颜色 `#1EE07F33`。**全局挂载**在 `App.vue` 第一层，
`position: fixed; inset: 0; z-index: -1; pointer-events: none`。

## 3D Logo 默认参数（与 Logo3D.vue 一致）

| 参数 | 值 |
|---|---|
| `scale` (auto-derived) | `targetSize / maxDim`，`targetSize` 桌面 2.5 / 平板 2 / 移动 1.5 |
| `velX/velY/velZ` 初始 | `1.2/0.6/0.3` + 随机 |
| `boundsX` (桌面) | `[-3.5, 3.5]` |
| `boundsY` | `[0.3, 3.5]` |
| `boundsZ` | `[-2.0, 1.5]` |
| 渲染器 | `WebGLRenderer({ alpha:true, antialias:true })` + `ACESFilmicToneMapping`，曝光 1.8 |

后台可通过 `/admin/models3d` 上传新 GLB 并修改这些参数，前端自动从
`/api/v1/models3d/active` 拉取。

## 响应式断点

| 名称 | 阈值 |
|---|---|
| `mobile` | `<= 768px` |
| `tablet` | `<= 1024px` |
| `desktop` | `> 1024px` |

不要使用 Tailwind 断点别名 — 项目无 Tailwind。
