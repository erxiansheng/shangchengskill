// Category visual mapping for skills without cover images
const categoryVisuals = {
  'AI助手': { gradient: 'linear-gradient(135deg, #FF3B30, #5E5CE6)', icon: '🤖' },
  '数据处理': { gradient: 'linear-gradient(135deg, #32D74B, #0A84FF)', icon: '📊' },
  '开发工具': { gradient: 'linear-gradient(135deg, #5E5CE6, #BF5AF2)', icon: '🛠️' },
  '创意生成': { gradient: 'linear-gradient(135deg, #FF9500, #FF2D55)', icon: '🎨' },
  '效率办公': { gradient: 'linear-gradient(135deg, #FFD60A, #FF3B30)', icon: '⚡' },
  '网络工具': { gradient: 'linear-gradient(135deg, #0A84FF, #5E5CE6)', icon: '🔗' },
  '游戏娱乐': { gradient: 'linear-gradient(135deg, #FF2D55, #FF9500)', icon: '🎮' },
  '文档写作': { gradient: 'linear-gradient(135deg, #30D158, #32D74B)', icon: '📝' },
}

const defaultVisual = { gradient: 'linear-gradient(135deg, #666, #999)', icon: '📦' }

export function getSkillVisual(categoryName) {
  return categoryVisuals[categoryName] || defaultVisual
}

export function formatDownloads(count) {
  if (count >= 10000) return (count / 10000).toFixed(1) + 'w'
  if (count >= 1000) return (count / 1000).toFixed(1) + 'k'
  return String(count || 0)
}

export function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  // Force Beijing time (UTC+8)
  const bj = new Date(d.getTime() + 8 * 3600000)
  const y = bj.getUTCFullYear()
  const m = String(bj.getUTCMonth() + 1).padStart(2, '0')
  const day = String(bj.getUTCDate()).padStart(2, '0')
  const h = String(bj.getUTCHours()).padStart(2, '0')
  const min = String(bj.getUTCMinutes()).padStart(2, '0')
  const sec = String(bj.getUTCSeconds()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}:${sec}`
}

export function formatDateShort(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const bj = new Date(d.getTime() + 8 * 3600000)
  const y = bj.getUTCFullYear()
  const m = String(bj.getUTCMonth() + 1).padStart(2, '0')
  const day = String(bj.getUTCDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
