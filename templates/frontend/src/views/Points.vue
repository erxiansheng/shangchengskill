<template>
  <div class="points-container container">
    <div class="points-header glass-panel">
      <div class="balance-wrap">
        <p class="b-label">当前可用积分</p>
        <div class="b-amount text-gradient">
          <span class="coin">💰</span> {{ balance.balance?.toLocaleString() || 0 }}
        </div>
      </div>
      <div class="balance-stats">
        <div class="s-item" v-if="balance.points_locked > 0">
          <span>锁定中</span>
          <strong style="color: #FF9F0A">{{ (balance.points_locked || 0).toLocaleString() }}</strong>
        </div>
        <div class="s-item">
          <span>累计充值</span>
          <strong>{{ (balance.total_earned || 0).toLocaleString() }}</strong>
        </div>
        <div class="s-item">
          <span>累计消耗</span>
          <strong>{{ (balance.total_spent || 0).toLocaleString() }}</strong>
        </div>
      </div>
    </div>

    <div class="two-col-layout">
      <!-- Left: Recharge -->
      <div class="recharge-panel glass-panel">
        <h2>积分充值</h2>
        <p class="subtitle">选择适合您的套餐，开启AI超能力。</p>

        <div v-if="packagesLoading" class="loading-state">
          <div class="loading-spinner"></div>
        </div>

        <div v-else class="package-grid">
          <div
            class="pack-card"
            v-for="(pkg, idx) in packages"
            :key="idx"
            :class="{ active: selectedPkg === idx }"
            @click="selectPackage(idx)"
          >
            <div class="pack-tag" v-if="idx === 2" style="background: #FF3B30">最受欢迎</div>
            <div class="pack-tag" v-else-if="idx === 3" style="background: #FF9500">超值推荐</div>
            <div class="pack-points">
              💰 {{ pkg.points }}
            </div>
            <div class="pack-price">¥ {{ pkg.amount_yuan }}</div>
          </div>
          <div
            class="pack-card custom-pack"
            :class="{ active: selectedPkg === -1 }"
            @click="selectCustom"
          >
            <div class="pack-tag" style="background: #5856D6">自定义</div>
            <div class="custom-input-wrap" v-if="selectedPkg === -1">
              <span class="custom-prefix">¥</span>
              <input
                type="number"
                v-model.number="customAmount"
                :min="1"
                step="1"
                placeholder="输入金额"
                class="custom-amount-input"
                @click.stop
              />
            </div>
            <div class="pack-points" v-else>自定义金额</div>
            <div class="pack-price">最低 ¥ 1</div>
          </div>
        </div>

        <div class="payment-method" v-if="enabledPayMethods.length > 0">
          <h3>选择支付方式</h3>
          <div class="methods">
            <div v-if="enabledPayMethods.includes('wechat')" class="pm-card" :class="{ active: payMethod === 'wechat' }" @click="payMethod = 'wechat'">
              <span class="icon" style="color:#09B83E">💬</span> 微信支付
            </div>
            <div v-if="enabledPayMethods.includes('alipay')" class="pm-card" :class="{ active: payMethod === 'alipay' }" @click="payMethod = 'alipay'">
              <span class="icon" style="color:#1677FF">💳</span> 支付宝
            </div>
          </div>
        </div>
        <div class="payment-method" v-else>
          <h3>选择支付方式</h3>
          <p style="color: var(--text-tertiary); text-align: center; padding: 12px;">暂无可用的支付方式</p>
        </div>

        <div class="checkout-bar">
          <div class="total">
            应付金额: <span>¥ {{ checkoutAmount }}</span>
            <span class="checkout-points">(可获 {{ checkoutPoints }} 积分)</span>
          </div>
          <button class="btn btn-primary btn-lg" @click="handlePay" :disabled="paying || !checkoutValid">
            {{ paying ? '处理中...' : '立即支付' }}
          </button>
        </div>

        <!-- Payment QR Code Modal -->
        <div v-if="showPayQr" class="pay-qr-overlay" @click.self="cancelPay">
          <div class="pay-qr-modal glass-panel">
            <h3>扫码支付</h3>
            <p class="qr-amount">¥ {{ pendingOrder?.amount_yuan }}</p>
            <p class="qr-hint">{{ pendingOrder?.payment_method === 'wechat' ? '请使用微信扫码支付' : '请使用支付宝扫码支付' }}</p>
            <div class="qr-wrap">
              <img :src="qrImageUrl" alt="支付二维码" v-if="qrImageUrl" />
              <div v-else class="qr-placeholder">二维码生成中...</div>
            </div>
            <p class="qr-status">{{ payStatusText }}</p>
            <button class="btn btn-glass" @click="cancelPay">取消支付</button>
          </div>
        </div>
      </div>

      <!-- Right: Records -->
      <div class="records-panel glass-panel">
        <div class="records-header">
          <h2>最近流水</h2>
        </div>

        <div v-if="recordsLoading" class="loading-state">
          <div class="loading-spinner"></div>
        </div>

        <div v-else-if="records.length === 0" class="empty-state">
          <p>暂无流水记录</p>
        </div>

        <template v-else>
          <div class="timeline">
            <div class="t-item" v-for="record in records" :key="record.id">
              <div class="t-icon" :class="record.amount > 0 ? 'in' : 'out'">
                {{ record.amount > 0 ? '📥' : '📤' }}
              </div>
              <div class="t-content">
                <div class="t-title">{{ record.description || record.type }}</div>
                <div class="t-time">{{ formatDate(record.created_at) }}</div>
              </div>
              <div class="t-amount" :class="record.amount > 0 ? 'positive' : 'negative'">
                {{ record.amount > 0 ? '+' : '' }}{{ record.amount }}
              </div>
            </div>
          </div>
          <div class="pagination" v-if="recordsTotalPages > 1">
            <button class="page-btn" :disabled="recordsPage <= 1" @click="changeRecordsPage(recordsPage - 1)">上一页</button>
            <span class="page-info">{{ recordsPage }} / {{ recordsTotalPages }}</span>
            <button class="page-btn" :disabled="recordsPage >= recordsTotalPages" @click="changeRecordsPage(recordsPage + 1)">下一页</button>
          </div>
        </template>
      </div>

      <!-- Withdrawal Section -->
      <div class="withdraw-section glass-panel">
        <h2>积分提现</h2>
      <p class="subtitle">提现收取 4% 手续费，最低 1040 积分起提（到账 ¥100），提现至支付宝账户，人工审核转账。发起后积分将被锁定，审核通过扣减，不通过自动退回。</p>

      <div class="withdraw-form">
        <div class="form-row">
          <label>提现积分</label>
          <input type="number" v-model.number="withdrawAmount" :min="1040" :max="balance.balance" placeholder="最低 1040 积分" class="form-input" />
          <div class="withdraw-calc" v-if="withdrawAmount >= 1040">
            <span>手续费: ¥{{ withdrawFee }}</span>
            <span class="sep">|</span>
            <span>实际到账: <strong>¥{{ withdrawActual }}</strong></span>
          </div>
        </div>
        <div class="form-row">
          <label>支付宝账号</label>
          <input type="text" v-model="withdrawAlipay" placeholder="收款支付宝账号" class="form-input" />
        </div>
        <div class="form-row">
          <label>真实姓名</label>
          <input type="text" v-model="withdrawName" placeholder="与支付宝一致的真实姓名" class="form-input" />
        </div>
        <button class="btn btn-primary" @click="handleWithdraw" :disabled="withdrawing">
          {{ withdrawing ? '提交中...' : '申请提现' }}
        </button>
      </div>

      <div v-if="withdrawals.length > 0" class="withdraw-history">
        <h3>提现记录</h3>
        <div class="wd-item" v-for="wd in withdrawals" :key="wd.id">
          <div class="wd-info">
            <div class="wd-amount">{{ wd.amount }} 积分 <span v-if="wd.actual_yuan" class="wd-yuan">→ ¥{{ wd.actual_yuan }}</span></div>
            <div class="wd-meta">{{ wd.alipay_account }} · {{ formatDate(wd.created_at) }}<span v-if="wd.fee_yuan"> · 手续费 ¥{{ wd.fee_yuan }}</span></div>
            <div v-if="wd.status === 'rejected' && wd.reject_reason" class="wd-reason">拒绝原因：{{ wd.reject_reason }}</div>
          </div>
          <span class="wd-status" :class="wd.status">{{ wdStatusMap[wd.status] || wd.status }}</span>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getBalance, getRecords, getPackages, createRecharge, checkRechargeStatus, requestWithdrawal, getWithdrawals } from '../api/points.js'
import { userStore } from '../stores/user.js'
import { formatDate } from '../utils.js'
import { useToast, KV_SYNC_HINT } from '../composables/useToast.js'
import { get } from '../api/request.js'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const balance = reactive({ balance: 0, points_locked: 0, total_earned: 0, total_spent: 0 })
const packages = ref([])
const records = ref([])
const sitePayConfig = reactive({ wechatEnabled: false, alipayEnabled: false })

const enabledPayMethods = computed(() => {
  const methods = []
  if (sitePayConfig.wechatEnabled) methods.push('wechat')
  if (sitePayConfig.alipayEnabled) methods.push('alipay')
  return methods
})
const selectedPkg = ref(2)
const customAmount = ref(10)
const payMethod = ref('wechat')
const paying = ref(false)
const packagesLoading = ref(true)
const recordsLoading = ref(true)
const recordsPage = ref(1)
const recordsTotalPages = ref(1)
const RECORDS_PAGE_SIZE = 10

// Payment QR code state
const showPayQr = ref(false)
const qrImageUrl = ref('')
const pendingOrder = ref(null)
const payStatusText = ref('等待支付...')
let pollTimer = null

// Withdrawal state
const withdrawAmount = ref(1040)
const withdrawAlipay = ref('')
const withdrawName = ref('')
const withdrawing = ref(false)
const withdrawals = ref([])
const wdStatusMap = { pending: '⏳ 处理中', completed: '✅ 已完成', rejected: '❌ 已拒绝' }

const WITHDRAW_FEE_RATE = 0.04
const withdrawFee = computed(() => {
  const gross = (withdrawAmount.value || 0) / 10
  return (gross * WITHDRAW_FEE_RATE).toFixed(2)
})
const withdrawActual = computed(() => {
  const gross = (withdrawAmount.value || 0) / 10
  return (gross * (1 - WITHDRAW_FEE_RATE)).toFixed(2)
})

const checkoutAmount = computed(() => {
  if (selectedPkg.value === -1) return customAmount.value || 0
  return packages.value[selectedPkg.value]?.amount_yuan || 0
})
const checkoutPoints = computed(() => Math.floor(checkoutAmount.value * 10))
const checkoutValid = computed(() => checkoutAmount.value >= 1)

const selectPackage = (idx) => { selectedPkg.value = idx }
const selectCustom = () => { selectedPkg.value = -1 }

const handlePay = async () => {
  const amountYuan = checkoutAmount.value
  if (!amountYuan || amountYuan < 1) {
    toast.error('最低充值金额为 1 元')
    return
  }

  paying.value = true
  try {
    const res = await createRecharge({
      amount_yuan: amountYuan,
      payment_method: payMethod.value
    })
    if (res.code === 0) {
      if (res.data?.qr_url) {
        if (res.data.payment_method === 'alipay') {
          // 支付宝：跳转到支付页面
          window.location.href = res.data.qr_url
          return
        }
        // 微信支付：展示二维码
        pendingOrder.value = {
          order_no: res.data.order_no,
          amount_yuan: amountYuan,
          payment_method: payMethod.value,
          points_amount: res.data.points_amount,
        }
        qrImageUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(res.data.qr_url)}`
        showPayQr.value = true
        payStatusText.value = '等待支付...'
        startPolling(res.data.order_no)
      } else {
        // Demo mode: immediately credited
        toast.success(`充值成功！获得 ${res.data.points_added} 积分。${KV_SYNC_HINT}`, '支付成功')
        const balRes = await getBalance()
        if (balRes.code === 0) {
          Object.assign(balance, balRes.data)
          userStore.updateUser({ points_balance: balRes.data.balance })
        }
        loadRecords()
      }
    } else {
      toast.error(res.message || '充值失败')
    }
  } catch (e) {
    toast.error('网络错误')
  } finally {
    paying.value = false
  }
}

const startPolling = (orderNo) => {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const res = await checkRechargeStatus(orderNo)
      if (res.code === 0 && res.data?.status === 'paid') {
        stopPolling()
        payStatusText.value = '支付成功！'
        toast.success(`充值成功！获得 ${res.data.points_amount} 积分。${KV_SYNC_HINT}`, '支付成功')
        showPayQr.value = false
        // Refresh balance
        const balRes = await getBalance()
        if (balRes.code === 0) {
          Object.assign(balance, balRes.data)
          userStore.updateUser({ points_balance: balRes.data.balance })
        }
        loadRecords()
      }
    } catch (e) { /* ignore poll errors */ }
  }, 3000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const cancelPay = () => {
  stopPolling()
  showPayQr.value = false
  pendingOrder.value = null
}

const loadRecords = async () => {
  recordsLoading.value = true
  try {
    const res = await getRecords({ page: recordsPage.value, page_size: RECORDS_PAGE_SIZE })
    if (res.code === 0) {
      records.value = res.data?.items || []
      recordsTotalPages.value = res.data?.total_pages || 1
    }
  } catch (e) {
    console.error('Failed to load records:', e)
  } finally {
    recordsLoading.value = false
  }
}

const changeRecordsPage = (p) => {
  recordsPage.value = p
  loadRecords()
}

const handleWithdraw = async () => {
  if (!withdrawAmount.value || withdrawAmount.value < 1040) {
    toast.error('最低提现额度为 1040 积分')
    return
  }
  if (!withdrawAlipay.value.trim()) {
    toast.error('请填写支付宝账号')
    return
  }
  if (!withdrawName.value.trim()) {
    toast.error('请填写真实姓名')
    return
  }
  withdrawing.value = true
  try {
    const res = await requestWithdrawal({
      amount: withdrawAmount.value,
      alipay_account: withdrawAlipay.value.trim(),
      alipay_name: withdrawName.value.trim(),
    })
    if (res.code === 0) {
      toast.success('提现申请已提交，积分已锁定，请等待管理员审核。' + KV_SYNC_HINT)
      withdrawAmount.value = 1040
      withdrawAlipay.value = ''
      withdrawName.value = ''
      loadWithdrawals()
    } else {
      toast.error(res.message || '提现失败')
    }
  } catch (e) {
    toast.error('网络错误')
  } finally {
    withdrawing.value = false
  }
}

const loadWithdrawals = async () => {
  try {
    const res = await getWithdrawals({ page: 1, page_size: 10 })
    if (res.code === 0) withdrawals.value = res.data?.items || []
  } catch (e) { /* ignore */ }
}

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }

  // 支付宝同步回调：用户支付后跳转回来
  if (route.query.pay_result === 'success') {
    toast.success('支付宝付款完成，积分将在几秒内到账。' + KV_SYNC_HINT, '支付完成')
    // 清除 URL 参数
    router.replace({ path: '/points' })
  }

  try {
    const [balRes, pkgRes] = await Promise.all([
      getBalance(),
      getPackages()
    ])
    if (balRes.code === 0) Object.assign(balance, balRes.data)
    if (pkgRes.code === 0) {
      packages.value = pkgRes.data?.packages || pkgRes.data?.items || []
    }
  } catch (e) {
    console.error('Failed to load points data:', e)
  } finally {
    packagesLoading.value = false
  }

  // Load payment method enabled status
  try {
    const settingsRes = await get('/site/public-settings')
    if (settingsRes.code === 0 && settingsRes.data) {
      sitePayConfig.wechatEnabled = !!settingsRes.data.wechatEnabled
      sitePayConfig.alipayEnabled = !!settingsRes.data.alipayEnabled
      // Auto-select first enabled method
      if (enabledPayMethods.value.length > 0 && !enabledPayMethods.value.includes(payMethod.value)) {
        payMethod.value = enabledPayMethods.value[0]
      }
    }
  } catch (e) { /* ignore */ }

  loadRecords()
  loadWithdrawals()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.points-container { padding: 40px 24px 100px; max-width: 1080px; }

.points-header {
  padding: 40px; display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 32px; border: 1px solid var(--color-primary-glow);
  box-shadow: inset 0 0 40px rgba(255, 59, 48, 0.1);
}

.b-label { font-size: 16px; color: var(--text-secondary); margin-bottom: 8px; }
.b-amount { font-size: 64px; font-weight: 800; line-height: 1; }
.b-amount .coin { font-size: 40px; }

.balance-stats { display: flex; gap: 40px; }
.s-item { display: flex; flex-direction: column; gap: 8px; text-align: right; }
.s-item span { color: var(--text-secondary); font-size: 14px; }
.s-item strong { font-size: 24px; color: var(--text-primary); }

.two-col-layout { display: grid; grid-template-columns: 1fr 360px; grid-template-rows: auto auto; gap: 32px; align-items: start; }
.two-col-layout .recharge-panel { grid-column: 1; grid-row: 1; }
.two-col-layout .records-panel { grid-column: 2; grid-row: 1 / 3; max-height: calc(100vh - 200px); overflow-y: auto; }
.two-col-layout .withdraw-section { grid-column: 1; grid-row: 2; }

.recharge-panel { padding: 32px; }
.recharge-panel h2 { font-size: 24px; margin-bottom: 8px; }
.recharge-panel .subtitle { color: var(--text-secondary); margin-bottom: 32px; }

.package-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px; }

.pack-card {
  position: relative; border: 2px solid var(--border-glass); background: rgba(0,0,0,0.3);
  padding: 24px; border-radius: 12px; text-align: center; cursor: pointer;
  transition: var(--transition-smooth);
}
.pack-card.active {
  border-color: var(--color-primary); background: rgba(255, 59, 48, 0.1);
  box-shadow: 0 0 20px rgba(255, 59, 48, 0.2);
}

.pack-tag {
  position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
  padding: 4px 12px; border-radius: 99px; font-size: 12px; font-weight: 600;
  color: var(--text-primary); white-space: nowrap;
}

.pack-points { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary); }
.pack-price { font-size: 20px; font-weight: 500; color: var(--text-secondary); }
.pack-card.active .pack-price { color: var(--color-primary); font-weight: 700; }

.custom-pack .pack-points { font-size: 16px; font-weight: 500; color: var(--text-secondary); }
.custom-input-wrap {
  display: flex; align-items: center; justify-content: center; gap: 4px; margin-bottom: 8px;
}
.custom-prefix { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.custom-amount-input {
  width: 80px; font-size: 22px; font-weight: 700; text-align: center;
  background: transparent; border: none; border-bottom: 2px solid var(--color-primary);
  color: var(--text-primary); outline: none; padding: 4px 0;
}
.custom-amount-input::-webkit-inner-spin-button,
.custom-amount-input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
.custom-amount-input[type=number] { -moz-appearance: textfield; }

.checkout-points { font-size: 14px; color: var(--text-tertiary); margin-left: 8px; font-weight: 400; }

.payment-method h3 { font-size: 16px; margin-bottom: 16px; }
.methods { display: flex; gap: 16px; margin-bottom: 40px; }

.pm-card {
  flex: 1; padding: 16px; border: 1px solid var(--border-glass); border-radius: 8px;
  display: flex; align-items: center; justify-content: center; gap: 12px;
  cursor: pointer; font-weight: 500; transition: var(--transition-smooth);
  background: rgba(0,0,0,0.3);
}
.pm-card.active { border-color: #34C759; background: rgba(52, 199, 89, 0.1); }
.pm-card .icon { font-size: 20px; }

.checkout-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 24px; border-top: 1px solid var(--border-glass);
}
.checkout-bar .total { font-size: 16px; color: var(--text-secondary); }
.checkout-bar .total span { font-size: 32px; font-weight: 700; color: var(--text-primary); margin-left: 12px; }

.records-panel { padding: 32px; }
.records-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.records-header h2 { font-size: 20px; }

.timeline { display: flex; flex-direction: column; gap: 24px; }
.t-item { display: flex; align-items: center; gap: 16px; }

.t-icon {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; font-size: 18px;
}
.t-icon.in { background: rgba(52, 199, 89, 0.1); }
.t-icon.out { background: rgba(255, 59, 48, 0.1); }

.t-content { flex: 1; }
.t-title { font-size: 15px; margin-bottom: 4px; color: var(--text-primary); }
.t-time { font-size: 12px; color: var(--text-tertiary); font-family: monospace; }

.t-amount { font-weight: 700; font-size: 16px; }
.t-amount.positive { color: #34C759; }
.t-amount.negative { color: var(--text-secondary); }

.loading-state, .empty-state { text-align: center; padding: 30px; color: var(--text-secondary); }
.loading-spinner {
  width: 32px; height: 32px; border: 3px solid var(--border-glass);
  border-top-color: var(--color-primary); border-radius: 50%;
  animation: spin 0.8s linear infinite; margin: 0 auto;
}
@keyframes spin { to { transform: rotate(360deg); } }

.withdraw-calc {
  margin-top: 8px; font-size: 13px; color: var(--text-secondary);
  display: flex; align-items: center; gap: 8px;
}
.withdraw-calc strong { color: var(--color-accent); font-size: 15px; }
.withdraw-calc .sep { color: var(--border-glass); }

@media (max-width: 900px) {
  .points-header { flex-direction: column; align-items: flex-start; gap: 32px; }
  .balance-stats { width: 100%; justify-content: space-between; }
  .s-item { text-align: left; }
  .two-col-layout { grid-template-columns: 1fr; }
}

/* Payment QR Code Modal */
.pay-qr-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}
.pay-qr-modal {
  padding: 40px;
  text-align: center;
  max-width: 380px;
  width: 90%;
}
.pay-qr-modal h3 { font-size: 20px; margin-bottom: 8px; }
.qr-amount { font-size: 28px; font-weight: 800; color: var(--color-primary); margin-bottom: 4px; }
.qr-hint { font-size: 13px; color: var(--text-secondary); margin-bottom: 20px; }
.qr-wrap {
  width: 220px; height: 220px;
  margin: 0 auto 16px;
  background: white;
  border-radius: 12px;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.qr-wrap img { width: 200px; height: 200px; }
.qr-placeholder { color: #999; font-size: 14px; }
.qr-status { font-size: 14px; color: var(--text-secondary); margin-bottom: 16px; }

/* Withdrawal Section */
.withdraw-section { margin-top: 0; padding: 28px; grid-column: 1; }
.withdraw-section h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.withdraw-section .subtitle { font-size: 13px; color: var(--text-secondary); margin-bottom: 20px; }
.withdraw-form { display: flex; flex-direction: column; gap: 16px; max-width: 500px; }
.form-row { display: flex; flex-direction: column; gap: 6px; }
.form-row label { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.form-input {
  padding: 10px 14px; border-radius: 10px; font-size: 14px;
  background: var(--bg-glass); border: 1px solid var(--border-glass);
  color: var(--text-primary);
}
.withdraw-history { margin-top: 28px; }
.withdraw-history h3 { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
.wd-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px; border-radius: 10px; margin-bottom: 8px;
  background: var(--bg-glass); border: 1px solid var(--border-glass);
}
.wd-info { display: flex; flex-direction: column; gap: 4px; }
.wd-amount { font-size: 15px; font-weight: 600; }
.wd-yuan { font-size: 13px; color: var(--color-accent); font-weight: 500; }
.wd-meta { font-size: 12px; color: var(--text-secondary); }
.wd-reason { font-size: 12px; color: #FF453A; margin-top: 2px; }
.wd-status { font-size: 13px; font-weight: 500; white-space: nowrap; }
.wd-status.completed { color: #34C759; }
.wd-status.rejected { color: #FF453A; }
.wd-status.pending { color: #FF9F0A; }

.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 20px; }
.page-btn {
  background: var(--bg-glass); border: 1px solid var(--border-glass); color: var(--text-primary);
  padding: 8px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; transition: var(--transition-smooth);
}
.page-btn:hover:not(:disabled) { background: var(--bg-surface-hover); border-color: var(--color-primary); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: 14px; color: var(--text-secondary); }

@media (max-width: 600px) {
  .points-container { padding: 20px 12px 60px; }
  .b-amount { font-size: 40px; }
  .b-amount .coin { font-size: 28px; }
  .balance-stats { gap: 20px; }
  .s-item strong { font-size: 18px; }
  .package-grid { grid-template-columns: repeat(2, 1fr); }
  .recharge-panel { padding: 20px; }
  .records-panel { padding: 20px; }
  .methods { flex-direction: column; gap: 10px; }
  .checkout-bar .total span { font-size: 24px; }
  .qr-wrap { width: 180px; height: 180px; }
  .qr-wrap img { width: 160px; height: 160px; }
  .pay-qr-modal { padding: 24px; }
}
</style>
