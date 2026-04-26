// 用户等级系统 — 与后端 core/levels.py 保持同步
export const LEVELS = [
  { level: 1, name: '新手虾',  icon: '🦐', min_exp: 0 },
  { level: 2, name: '中级龙虾', icon: '🦞', min_exp: 100 },
  { level: 3, name: '高级龙虾', icon: '🦞', min_exp: 500 },
  { level: 4, name: '澳龙',   icon: '🦞', min_exp: 2000 },
  { level: 5, name: '波龙',   icon: '🦞', min_exp: 8000 },
]

// 远程配置的等级列表（由 loadRemoteLevels 设置）
let remoteLevels = null
let expConfig = { expPublish: 20, expDownload: 2, expFavorite: 3, expRechargeYuan: 1 }

export function setRemoteLevels(levels) {
  if (Array.isArray(levels) && levels.length) remoteLevels = levels
}

export function setExpConfig(cfg) {
  if (cfg) expConfig = { ...expConfig, ...cfg }
}

export function getExpConfig() {
  return expConfig
}

export function getActiveLevels() {
  return remoteLevels || LEVELS
}

export function getLevelInfo(exp = 0) {
  const lvs = getActiveLevels()
  let current = lvs[0]
  let nextLevel = lvs[1] || null
  for (let i = 0; i < lvs.length; i++) {
    if (exp >= lvs[i].min_exp) {
      current = lvs[i]
      nextLevel = lvs[i + 1] || null
    }
  }
  return { ...current, exp, next_level: nextLevel }
}

export function getLevelFromInfo(levelInfo) {
  // Accept backend level_info object or compute from exp
  if (levelInfo && levelInfo.name) return levelInfo
  return getLevelInfo(0)
}

export const LEVEL_DESCRIPTION = `等级说明：
• 🦐 新手虾 — 初始等级
• 🦞 中级龙虾 — 100 经验值
• 🦞 高级龙虾 — 500 经验值
• 🦞 澳龙 — 2000 经验值
• 🦞 波龙 — 8000 经验值

经验值获取方式：
• 发布商品被审核通过 +20
• 商品被下载 +2
• 商品被收藏 +3
• 充值 +1/元`
