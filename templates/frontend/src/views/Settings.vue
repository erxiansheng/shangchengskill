<template>
  <div class="settings-container container">
    <h1 class="settings-title">账号设置</h1>

    <div class="settings-card glass-panel">
      <!-- 基本信息 -->
      <div class="section">
        <h3 class="section-title">基本信息</h3>
        <div class="compact-row">
          <label>昵称</label>
          <input type="text" class="form-control" v-model="nickname" />
        </div>
        <div class="compact-row">
          <label>个人签名</label>
          <textarea class="form-control" v-model="bio" rows="2"></textarea>
        </div>
        <div class="compact-row">
          <label>头像</label>
          <div class="avatar-picker">
            <div class="avatar-current">
              <img :src="avatarUrl || defaultAvatar" class="avatar-preview" alt="" />
              <span v-if="isOAuthAvatar" class="avatar-source-tag">OAuth 头像</span>
            </div>
            <div class="avatar-grid">
              <div
                v-for="av in builtinAvatars"
                :key="av.seed"
                class="avatar-option"
                :class="{ selected: avatarUrl === av.url }"
                @click="avatarUrl = av.url"
              >
                <img :src="av.url" :alt="av.seed" />
              </div>
            </div>
          </div>
        </div>
        <div class="save-row">
          <span v-if="errorMsg" class="inline-error">{{ errorMsg }}</span>
          <span v-if="successMsg" class="inline-success">{{ successMsg }}</span>
          <button class="btn btn-primary btn-sm" @click="handleSave" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>

      <div class="section-divider"></div>

      <!-- 邮箱 -->
      <div class="section">
        <h3 class="section-title">邮箱绑定</h3>
        <div class="compact-row" v-if="currentEmail && !showEmailBind">
          <label>已绑定</label>
          <div class="email-display">
            <span>{{ currentEmail }}</span>
            <button class="btn btn-glass btn-xs" @click="showEmailBind = true">更换</button>
          </div>
        </div>
        <template v-if="showEmailBind || !currentEmail">
          <div class="compact-row">
            <label>邮箱</label>
            <input type="email" class="form-control" v-model="bindEmail" placeholder="输入邮箱地址" />
          </div>
          <div class="compact-row">
            <label>验证码</label>
            <div class="code-input-group">
              <input type="text" class="form-control" v-model="emailCode" placeholder="6位验证码" maxlength="6" />
              <button class="btn btn-glass btn-xs" @click="handleSendCode" :disabled="codeCooldown > 0 || sendingCode">
                {{ sendingCode ? '发送...' : (codeCooldown > 0 ? `${codeCooldown}s` : '发送') }}
              </button>
            </div>
          </div>
          <div class="save-row">
            <span v-if="emailError" class="inline-error">{{ emailError }}</span>
            <span v-if="emailSuccess" class="inline-success">{{ emailSuccess }}</span>
            <button v-if="showEmailBind && currentEmail" class="btn btn-glass btn-xs" @click="showEmailBind = false">取消</button>
            <button class="btn btn-primary btn-sm" @click="handleBindEmail" :disabled="!bindEmail || !emailCode || bindingEmail">
              {{ bindingEmail ? '绑定中...' : '绑定' }}
            </button>
          </div>
        </template>
      </div>

      <div class="section-divider"></div>

      <!-- API 密钥 -->
      <div class="section">
        <div class="section-header">
          <h3 class="section-title">API 密钥</h3>
          <button class="btn btn-primary btn-xs" @click="showCreateModal = true">+ 新建</button>
        </div>

        <div v-if="tokensLoading" class="loading-state"><div class="loading-spinner"></div></div>

        <div v-else-if="tokens.length === 0" class="empty-hint">暂无密钥</div>

        <div v-else class="token-list">
          <div v-for="token in tokens" :key="token.id" class="token-card">
            <div class="token-info">
              <span class="token-name">{{ token.name }}</span>
              <span class="token-status" :class="token.is_active ? 'active' : 'inactive'">{{ token.is_active ? '启用' : '停用' }}</span>
              <span class="token-scope-count">{{ (token.scopes || []).length }} 项权限</span>
              <span class="token-date">{{ formatDate(token.created_at) }}</span>
            </div>
            <div class="token-actions">
              <label class="toggle-switch" :title="token.is_active ? '停用' : '启用'">
                <input type="checkbox" :checked="token.is_active" @change="handleToggle(token)" />
                <span class="toggle-slider"></span>
              </label>
              <button class="btn-icon-danger" @click="handleRevoke(token)" title="删除">🗑️</button>
            </div>
          </div>
        </div>

        <div v-if="newTokenValue" class="new-token-alert">
          <div class="alert-header">⚠️ 请立即保存此密钥</div>
          <div class="new-token-value" @click="copyToken">
            <code>{{ newTokenValue }}</code>
            <button class="copy-btn" :class="{ copied: tokenCopied }">{{ tokenCopied ? '✅' : '📋' }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Token Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-dialog glass-panel">
        <h3>创建新密钥</h3>
        <div class="form-group">
          <label>密钥名称</label>
          <input type="text" class="form-control" v-model="newTokenName" placeholder="例如：生产环境密钥" />
        </div>
        <div class="form-group">
          <label>有效期（天）</label>
          <input type="number" class="form-control" v-model.number="newTokenExpiry" placeholder="留空为永不过期" />
        </div>
        <div class="form-group">
          <label>权限范围</label>
          <div class="scope-list">
            <label v-for="s in availableScopes" :key="s.key" class="scope-item">
              <input type="checkbox" :value="s.key" v-model="newTokenScopes" />
              <span>{{ s.label }}</span>
            </label>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-glass" @click="showCreateModal = false">取消</button>
          <button class="btn btn-primary" @click="handleCreate" :disabled="!newTokenName.trim() || newTokenScopes.length === 0">创建</button>
        </div>
      </div>
    </div>

    <ConfirmModal
      :visible="showRevokeConfirm"
      title="删除密钥"
      :message="'确定要删除密钥 &quot;' + (revokeTarget?.name || '') + '&quot; 吗？此操作不可撤销。'"
      confirmText="确认删除"
      cancelText="取消"
      type="danger"
      @confirm="confirmRevoke"
      @cancel="showRevokeConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMe, updateProfile } from '../api/user.js'
import { post } from '../api/request.js'
import { getTokens, createToken, toggleToken, revokeToken } from '../api/tokens.js'
import { userStore } from '../stores/user.js'
import { useToast, KV_SYNC_HINT } from '../composables/useToast.js'
import ConfirmModal from '../components/ConfirmModal.vue'

const toast = useToast()

const router = useRouter()

const nickname = ref('')
const bio = ref('')
const avatarUrl = ref('')
const saving = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

// Built-in avatar options
const avatarSeeds = [
  'Lobster', 'Felix', 'Misty', 'Shadow', 'Lucky', 'Pepper',
  'Buddy', 'Tiger', 'Smokey', 'Whiskers', 'Socks', 'Bella',
  'Oscar', 'Cleo', 'Max', 'Luna', 'Rocky', 'Daisy',
]
const builtinAvatars = avatarSeeds.map(seed => ({
  seed,
  url: `https://api.dicebear.com/7.x/avataaars/svg?seed=${seed}`,
}))
const defaultAvatar = 'https://api.dicebear.com/7.x/avataaars/svg?seed=Lobster'
const isOAuthAvatar = computed(() => {
  if (!avatarUrl.value) return false
  return !avatarUrl.value.includes('dicebear.com')
})

// Email binding state
const currentEmail = ref('')
const showEmailBind = ref(false)
const bindEmail = ref('')
const emailCode = ref('')
const codeCooldown = ref(0)
const sendingCode = ref(false)
const bindingEmail = ref(false)
const emailError = ref('')
const emailSuccess = ref('')

// Tokens state
const tokens = ref([])
const tokensLoading = ref(true)
const showCreateModal = ref(false)
const newTokenName = ref('')
const newTokenExpiry = ref(90)
const newTokenValue = ref('')
const availableScopes = [
  { key: 'skill:read', label: '浏览商品市场' },
  { key: 'skill:publish', label: '发布新商品' },
  { key: 'skill:update', label: '更新/删除商品' },
  { key: 'skill:purchase', label: '购买商品' },
  { key: 'skill:download', label: '下载商品包' },
]
const newTokenScopes = ref(['skill:read', 'skill:purchase', 'skill:download'])
const tokenCopied = ref(false)
const showRevokeConfirm = ref(false)
const revokeTarget = ref(null)

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

const handleSave = async () => {
  errorMsg.value = ''
  successMsg.value = ''
  saving.value = true

  try {
    const data = {}
    if (nickname.value.trim()) data.nickname = nickname.value.trim()
    if (bio.value !== undefined) data.bio = bio.value
    if (avatarUrl.value) data.avatar_url = avatarUrl.value

    const res = await updateProfile(data)
    if (res.code === 0) {
      successMsg.value = '保存成功。' + KV_SYNC_HINT
      userStore.updateUser(data)
    } else {
      errorMsg.value = res.message || '保存失败'
    }
  } catch (e) {
    errorMsg.value = '网络错误'
  } finally {
    saving.value = false
  }
}

const handleSendCode = async () => {
  emailError.value = ''
  emailSuccess.value = ''
  if (!bindEmail.value) {
    emailError.value = '请输入邮箱地址'
    return
  }
  sendingCode.value = true
  try {
    const res = await post('/users/me/email/send-code', { email: bindEmail.value })
    if (res.code === 0) {
      emailSuccess.value = '验证码已发送，请查收邮箱'
      codeCooldown.value = 60
      const timer = setInterval(() => {
        codeCooldown.value--
        if (codeCooldown.value <= 0) clearInterval(timer)
      }, 1000)
    } else {
      emailError.value = res.message || '发送失败'
    }
  } catch (e) {
    emailError.value = '网络错误'
  } finally {
    sendingCode.value = false
  }
}

const handleBindEmail = async () => {
  emailError.value = ''
  emailSuccess.value = ''
  bindingEmail.value = true
  try {
    const res = await post('/users/me/email/bind', { email: bindEmail.value, code: emailCode.value })
    if (res.code === 0) {
      currentEmail.value = res.data.email
      showEmailBind.value = false
      bindEmail.value = ''
      emailCode.value = ''
      emailSuccess.value = '邮箱绑定成功。' + KV_SYNC_HINT
    } else {
      emailError.value = res.message || '绑定失败'
    }
  } catch (e) {
    emailError.value = '网络错误'
  } finally {
    bindingEmail.value = false
  }
}

const loadTokens = async () => {
  tokensLoading.value = true
  try {
    const res = await getTokens()
    if (res.code === 0) {
      tokens.value = res.data || []
    }
  } catch (e) {
    console.error('Failed to load tokens:', e)
  } finally {
    tokensLoading.value = false
  }
}

const handleCreate = async () => {
  try {
    const data = {
      name: newTokenName.value.trim(),
      scopes: [...newTokenScopes.value],
    }
    if (newTokenExpiry.value) data.expires_in_days = newTokenExpiry.value

    const res = await createToken(data)
    if (res.code === 0) {
      newTokenValue.value = res.data.token
      // Add new token to local state directly (avoid KV eventual consistency delay)
      tokens.value.unshift({
        id: res.data.id,
        name: res.data.name,
        scopes: res.data.scopes,
        is_active: res.data.is_active,
        created_at: res.data.created_at,
        expires_at: res.data.expires_at,
        last_used: res.data.last_used,
      })
      showCreateModal.value = false
      newTokenName.value = ''
      newTokenExpiry.value = 90
      newTokenScopes.value = ['skill:read', 'skill:purchase', 'skill:download']
    }
  } catch (e) {
    console.error('Failed to create token:', e)
  }
}

const handleToggle = async (token) => {
  try {
    const res = await toggleToken(token.id)
    if (res.code === 0) {
      const idx = tokens.value.findIndex(t => t.id === token.id)
      if (idx >= 0) {
        tokens.value[idx] = { ...tokens.value[idx], is_active: res.data.is_active }
      }
      toast.success(res.data.is_active ? '密钥已启用' : '密钥已停用')
    } else {
      toast.error(res.message || '操作失败')
    }
  } catch (e) {
    console.error('Failed to toggle token:', e)
    toast.error('网络错误，请重试')
  }
}

const handleRevoke = async (token) => {
  revokeTarget.value = token
  showRevokeConfirm.value = true
}

const confirmRevoke = async () => {
  showRevokeConfirm.value = false
  if (!revokeTarget.value) return
  try {
    const res = await revokeToken(revokeTarget.value.id)
    if (res.code === 0) {
      tokens.value = tokens.value.filter(t => t.id !== revokeTarget.value.id)
    }
  } catch (e) {
    console.error('Failed to delete token:', e)
  } finally {
    revokeTarget.value = null
  }
}

const copyToken = async () => {
  try {
    await navigator.clipboard.writeText(newTokenValue.value)
    tokenCopied.value = true
    setTimeout(() => { tokenCopied.value = false }, 2000)
  } catch (e) {
    const ta = document.createElement('textarea')
    ta.value = newTokenValue.value
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    tokenCopied.value = true
    setTimeout(() => { tokenCopied.value = false }, 2000)
  }
}

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }

  try {
    const res = await getMe()
    if (res.code === 0) {
      nickname.value = res.data?.nickname || ''
      bio.value = res.data?.bio || ''
      avatarUrl.value = res.data?.avatar_url || ''
      currentEmail.value = res.data?.email || ''
      userStore.updateUser(res.data)
    }
  } catch (e) { /* use existing store data */ }

  if (!nickname.value && userStore.user) {
    nickname.value = userStore.user.nickname || ''
    bio.value = userStore.user.bio || ''
    avatarUrl.value = userStore.user.avatar_url || ''
  }

  loadTokens()
})
</script>

<style scoped>
.settings-container { padding: 40px 24px 100px; max-width: 640px; }
.settings-title { font-size: 24px; font-weight: 700; margin-bottom: 20px; }

.settings-card { padding: 0; overflow: hidden; }

.section { padding: 20px 24px; }
.section-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 14px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.section-header .section-title { margin-bottom: 0; }
.section-divider { height: 1px; background: var(--border-glass); }

label { display: block; font-size: 13px; color: var(--text-secondary); margin-bottom: 0; white-space: nowrap; min-width: 35px; }

.form-control {
  width: 100%; background: var(--bg-glass); border: 1px solid var(--border-glass);
  border-radius: 6px; padding: 8px 12px; color: var(--text-primary); font-family: inherit;
  font-size: 14px; transition: var(--transition-smooth); outline: none;
}
.form-control:focus { border-color: var(--color-primary); box-shadow: 0 0 0 2px var(--color-primary-glow); }
textarea.form-control { resize: vertical; }

.compact-row { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
.compact-row label { padding-top: 9px; }
.compact-row .form-control { flex: 1; }

.avatar-row { display: flex; align-items: center; gap: 10px; flex: 1; }
.avatar-mini { width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--border-glass); flex-shrink: 0; }

/* Avatar Picker */
.avatar-picker { flex: 1; min-width: 0; }
.avatar-current { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.avatar-preview { width: 48px; height: 48px; border-radius: 50%; border: 2px solid var(--border-glass); flex-shrink: 0; background: rgba(255,255,255,0.05); }
.avatar-source-tag { font-size: 11px; color: var(--text-tertiary); background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 4px; }
.avatar-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(36px, 1fr)); gap: 6px; }
.avatar-option {
  width: 36px; height: 36px; border-radius: 50%; overflow: hidden; cursor: pointer;
  border: 2px solid transparent; transition: all 0.2s; background: rgba(255,255,255,0.05);
}
.avatar-option img { width: 100%; height: 100%; }
.avatar-option:hover { border-color: rgba(30, 224, 127, 0.4); transform: scale(1.1); }
.avatar-option.selected { border-color: var(--color-primary); box-shadow: 0 0 0 2px var(--color-primary-glow); }

.save-row { display: flex; align-items: center; gap: 8px; justify-content: flex-end; margin-top: 4px; }

.inline-error { font-size: 12px; color: #FF453A; }
.inline-success { font-size: 12px; color: #34C759; }

.email-display { display: flex; align-items: center; gap: 10px; flex: 1; color: var(--text-primary); font-size: 14px; }

.code-input-group { display: flex; gap: 8px; flex: 1; }
.code-input-group .form-control { flex: 1; }

.btn-xs { padding: 5px 12px; font-size: 12px; border-radius: 6px; }
.btn-sm { padding: 7px 14px; font-size: 13px; border-radius: 6px; }

/* Token List */
.token-list { display: flex; flex-direction: column; gap: 8px; }

.token-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-glass); border-radius: 8px;
  transition: var(--transition-smooth); gap: 12px;
}
.token-card:hover { background: rgba(255, 255, 255, 0.06); }

.token-info { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; flex-wrap: wrap; }
.token-name { font-weight: 600; font-size: 13px; color: var(--text-primary); }
.token-status { font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 99px; }
.token-status.active { background: rgba(52, 199, 89, 0.15); color: #34C759; }
.token-status.inactive { background: rgba(255, 69, 58, 0.15); color: #FF453A; }
.token-date { font-size: 11px; color: var(--text-tertiary); }
.token-scope-count { font-size: 10px; color: var(--text-secondary); background: rgba(128,128,128,0.1); padding: 1px 6px; border-radius: 99px; }

.token-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

.toggle-switch { position: relative; display: inline-block; width: 36px; height: 20px; cursor: pointer; flex-shrink: 0; }
.toggle-switch input { opacity: 0; width: 0; height: 0; position: absolute; }
.toggle-slider { position: absolute; inset: 0; background: rgba(120, 120, 128, 0.3); border-radius: 20px; transition: 0.3s; }
.toggle-slider::before { content: ''; position: absolute; width: 14px; height: 14px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.3s; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
.toggle-switch input:checked + .toggle-slider { background: var(--color-primary); }
.toggle-switch input:checked + .toggle-slider::before { transform: translateX(16px); }

.btn-icon-danger {
  background: none; border: none; cursor: pointer; font-size: 13px;
  padding: 4px; border-radius: 4px; transition: var(--transition-smooth);
}
.btn-icon-danger:hover { background: rgba(255, 69, 58, 0.15); }

.empty-hint { text-align: center; padding: 20px; color: var(--text-tertiary); font-size: 13px; }

/* New Token Alert */
.new-token-alert { margin-top: 12px; padding: 12px; background: rgba(255, 149, 0, 0.08); border: 1px solid rgba(255, 149, 0, 0.3); border-radius: 8px; }
.alert-header { font-size: 12px; font-weight: 600; color: #FF9500; margin-bottom: 8px; }
.new-token-value { position: relative; background: rgba(0, 0, 0, 0.5); border: 1px solid var(--border-glass); border-radius: 6px; padding: 10px 12px; cursor: pointer; }
.new-token-value code { font-family: 'Fira Code', monospace; font-size: 12px; color: #a6e22e; word-break: break-all; display: block; padding-right: 40px; }
.copy-btn { position: absolute; top: 8px; right: 8px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: var(--text-secondary); font-size: 11px; padding: 2px 8px; border-radius: 4px; cursor: pointer; transition: 0.2s; }
.copy-btn:hover { background: var(--color-primary); color: white; }
.copy-btn.copied { background: rgba(52, 199, 89, 0.2); color: #34C759; }

/* Loading */
.loading-state { text-align: center; padding: 20px; }
.loading-spinner { width: 20px; height: 20px; border: 2px solid var(--border-glass); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 24px; }
.modal-dialog { width: 100%; max-width: 400px; padding: 24px; border-radius: 16px; }
.modal-dialog h3 { font-size: 18px; font-weight: 700; margin-bottom: 20px; }
.modal-dialog .form-group { margin-bottom: 14px; }
.modal-dialog .form-group label { margin-bottom: 6px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.scope-list { display: flex; flex-direction: column; gap: 8px; }
.scope-item { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px; }
.scope-item input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }
</style>
