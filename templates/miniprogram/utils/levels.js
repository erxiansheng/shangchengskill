// 用户等级系统 — 与后端 core/levels.py 保持同步
var LEVELS = [
  { level: 1, name: '新手虾',  icon: '🦐', min_exp: 0 },
  { level: 2, name: '中级龙虾', icon: '🦞', min_exp: 100 },
  { level: 3, name: '高级龙虾', icon: '🦞', min_exp: 500 },
  { level: 4, name: '澳龙',   icon: '🦞', min_exp: 2000 },
  { level: 5, name: '波龙',   icon: '🦞', min_exp: 8000 },
]

function setRemoteLevels(lvs) {
  if (lvs && lvs.length) LEVELS = lvs
}

function getActiveLevels() {
  return LEVELS
}

function getLevelInfo(exp) {
  exp = exp || 0
  var lvs = LEVELS
  var current = lvs[0]
  var nextLevel = lvs[1] || null
  for (var i = 0; i < lvs.length; i++) {
    if (exp >= lvs[i].min_exp) {
      current = lvs[i]
      nextLevel = lvs[i + 1] || null
    }
  }
  return {
    level: current.level,
    name: current.name,
    icon: current.icon,
    exp: exp,
    next_level: nextLevel,
  }
}

module.exports = {
  LEVELS: LEVELS,
  setRemoteLevels: setRemoteLevels,
  getActiveLevels: getActiveLevels,
  getLevelInfo: getLevelInfo,
}
