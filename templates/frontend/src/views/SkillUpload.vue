<template>
  <div class="upload-container container">
    <div class="page-header">
      <h1 class="page-title">{{ isEdit ? '更新商品' : '发布新商品' }}</h1>
      <p class="page-subtitle">{{ isEdit ? '更新商品信息后提交保存，将自动生成版本记录。' : '将您的 AI 创意转化为价值。打包上传您的商品，审核通过后即可上架交易。' }}</p>
    </div>

    <div class="upload-layout">
      <div class="form-card glass-panel">
        <form @submit.prevent="handleSubmit">

          <!-- ZIP Upload (TOP) -->
          <div class="form-group" v-if="form.product_type === 'digital'">
            <label>商品包上传 (.zip 格式) <span class="required">*</span></label>
            <div class="upload-box file-upload" :class="{ 'has-file': packageUploaded, 'uploading': uploadingPackage, 'has-tree': packageFileTree.length > 0 }">
              <input type="file" ref="fileInput" accept=".zip" @change="handleFileUpload" style="display:none" />
              <!-- Upload prompt / status header -->
              <div class="upload-content" @click="triggerFileUpload">
                <template v-if="!packageUploaded && !uploadingPackage">
                  <span class="icon">📦</span>
                  <p>点击上传 ZIP 商品包</p>
                  <p class="sub-text">不超过 5MB。上传后自动解析填充表单。</p>
                </template>
                <template v-else-if="uploadingPackage">
                  <span class="icon">⏳</span>
                  <p>正在上传并解析商品包...</p>
                </template>
                <template v-else>
                  <div class="uploaded-header">
                    <span class="icon-sm">✅</span>
                    <div class="uploaded-info">
                      <p class="uploaded-name">{{ packageFileName }}</p>
                      <p class="uploaded-size">{{ formatFileSize(form.file_size) }}</p>
                    </div>
                    <button type="button" class="btn-reupload" @click.stop="triggerFileUpload">重新上传</button>
                  </div>
                </template>
              </div>
              <!-- File tree inside upload box -->
              <div class="file-tree-section" v-if="packageFileTree.length > 0">
                <div class="file-tree-header">
                  <span>Skill 文件</span>
                  <span class="file-tree-count">已选择 {{ packageFileTree.filter(f => !f.is_dir).length }} 个文件，总大小 {{ formatFileSize(packageFileTree.reduce((sum, f) => sum + (f.size || 0), 0)) }}</span>
                </div>
                <div class="file-tree-list">
                  <div v-for="(entry, idx) in packageFileTreeDisplay" :key="idx" class="file-tree-item" :class="{ 'is-dir': entry.is_dir }" :style="{ paddingLeft: entry.depth * 16 + 12 + 'px' }">
                    <span class="file-icon">{{ entry.is_dir ? '📁' : getFileIcon(entry.name) }}</span>
                    <span class="file-name">{{ entry.base_name }}</span>
                    <span class="file-size" v-if="!entry.is_dir">{{ formatFileSize(entry.size) }}</span>
                  </div>
                </div>
              </div>
            </div>
            <p class="field-hint" v-if="skillMdParsed">已从 SKILL.md 自动提取信息并填充表单</p>
          </div>

          <div class="form-group">
            <label>商品名称 <span class="required">*</span></label>
            <input type="text" class="form-control" placeholder="例如：GPT-6 本地微调引擎" v-model="form.title" @input="clearTitleIssue" required />
            <p class="field-error" v-if="titleErrorMsg">{{ titleErrorMsg }}</p>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>商品分类 <span class="required">*</span></label>
              <CustomSelect
                v-model="form.category_id"
                :options="categoryOptions"
                placeholder="请选择类别..."
              />
            </div>

            <div class="form-group" v-if="form.sale_mode === 'points' || form.sale_mode === 'both'">
              <label>价格(积分) <span class="required">*</span></label>
              <div class="input-with-icon">
                <input type="number" class="form-control" placeholder="0 表示免费" v-model.number="form.price" min="0" />
                <span class="input-icon">💰</span>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>版本号</label>
              <input type="text" class="form-control" placeholder="例如：1.0.0" v-model="form.version" />
            </div>

            <div class="form-group">
              <label>标签 (逗号分隔)</label>
              <input type="text" class="form-control" placeholder="例如：AI, 微调, 强化学习" v-model="tagsInput" />
            </div>
          </div>

          <!-- ── 商品类型 & 售卖方式 ── -->
          <div class="form-row">
            <div class="form-group">
              <label>商品类型 <span class="required">*</span></label>
              <select class="form-control" v-model="form.product_type">
                <option value="digital">数字商品（需上传 ZIP）</option>
                <option value="physical">实体商品（无需上传文件，需收货地址）</option>
              </select>
              <p class="field-hint">实体商品发货走管理员后台「订单管理」面板手动处理。</p>
            </div>
            <div class="form-group">
              <label>售卖方式 <span class="required">*</span></label>
              <select class="form-control" v-model="form.sale_mode">
                <option value="points" v-if="form.product_type !== 'physical'">仅积分</option>
                <option value="cash">仅现金（微信/支付宝）</option>
                <option value="both" v-if="form.product_type !== 'physical'">积分 + 现金（用户自选）</option>
              </select>
              <p class="field-hint" v-if="form.product_type === 'physical'">实体商品仅支持现金支付，购买时会要求填写收货信息。</p>
            </div>
          </div>

          <div class="form-row" v-if="form.sale_mode === 'cash' || form.sale_mode === 'both'">
            <div class="form-group">
              <label>现金价格（元） <span class="required">*</span></label>
              <div class="input-with-icon">
                <input type="number" step="0.01" min="0" class="form-control" placeholder="例如 19.90" v-model.number="form.cash_price_yuan" />
                <span class="input-icon">¥</span>
              </div>
            </div>
            <div class="form-group" v-if="form.product_type === 'physical'">
              <label>运费（元）</label>
              <input type="number" step="0.01" min="0" class="form-control" placeholder="0 表示包邮" v-model.number="form.shipping_fee_yuan" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>库存（留空 = 不限）</label>
              <input type="number" min="0" class="form-control" placeholder="留空表示不限制库存" v-model.number="form.stock" />
            </div>
          </div>

          <!-- Short description (subtitle) -->
          <div class="form-group">
            <label>商品介绍</label>
            <textarea class="form-control" rows="2" placeholder="一句话描述您的商品（自动从 SKILL.md 提取，可二次编辑）" v-model="form.subtitle"></textarea>
            <p class="field-hint">显示在商品卡片和搜索结果中</p>
          </div>

          <!-- Screenshots (replaces cover image) -->
          <div class="form-group">
            <label>聊天使用商品的效果图</label>
            <div class="screenshots-area">
              <div class="screenshot-grid" v-if="screenshotPreviews.length > 0">
                <div class="screenshot-item" v-for="(img, idx) in screenshotPreviews" :key="idx">
                  <img :src="img" alt="效果图" />
                  <button type="button" class="screenshot-remove" @click="removeScreenshot(idx)">✕</button>
                </div>
              </div>
              <div class="upload-box image-upload" @click="triggerImageUpload" v-if="screenshotPreviews.length < 6">
                <input type="file" ref="imageInput" accept="image/*" @change="handleImageUpload" style="display:none" multiple />
                <div class="upload-content compact">
                  <span class="icon">🖼️</span>
                  <p>点击添加效果图 (最多6张)</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Detailed description (markdown) -->
          <div class="form-group">
            <label>详细介绍 <span class="required">*</span></label>
            <div class="md-editor glass-panel">
              <div class="editor-tabs">
                <span :class="{ active: descTab === 'edit' }" @click="descTab = 'edit'">✏️ 编辑</span>
                <span :class="{ active: descTab === 'preview' }" @click="descTab = 'preview'">👁️ 预览</span>

                <div class="toolbar" v-show="descTab === 'edit'">
                  <button type="button" @click="insertMd('desc', '**粗体**')" title="粗体"><span style="font-weight: 900">B</span></button>
                  <button type="button" @click="insertMd('desc', '*斜体*')" title="斜体"><span style="font-style: italic">I</span></button>
                  <button type="button" @click="insertMd('desc', '### 标题\n')" title="标题">H</button>
                  <div class="divider"></div>
                  <button type="button" @click="insertMd('desc', '\n- 列表项')" title="无序列表">☰</button>
                  <button type="button" @click="insertMd('desc', '[链接名](https://)')" title="链接">🔗</button>
                  <button type="button" @click="insertMd('desc', '\n```python\n代码\n```\n')" title="代码块">&lt;/&gt;</button>
                </div>
              </div>
              <div class="editor-content">
                <textarea v-if="descTab === 'edit'" ref="descRef" v-model="descriptionText" class="form-control code-font" rows="8" placeholder="使用 Markdown 语法详细描述您的商品功能、特性...（自动从 SKILL.md 提取，可二次编辑）"></textarea>
                <div v-else class="markdown-body preview-area" v-html="renderedDesc || '<p class=\'empty-text\'>空空如也...</p>'"></div>
              </div>
            </div>
          </div>

          <!-- Changelog (only in edit mode) -->
          <div class="form-group" v-if="isEdit">
            <label>变更说明</label>
            <textarea class="form-control" rows="3" placeholder="描述本次更新的内容，例如：修复了 XX 问题，新增了 XX 功能..." v-model="form.changelog"></textarea>
            <p class="field-hint">记录本次修改的变更内容，方便用户了解更新详情</p>
          </div>

          <div class="error-msg" v-if="errorMsg">{{ errorMsg }}</div>
          <div class="error-hint" v-if="submitHelpMsg">{{ submitHelpMsg }}</div>
          <div class="success-msg" v-if="successMsg">{{ successMsg }}</div>

          <div class="form-actions">
            <button type="button" class="btn btn-glass" @click="$router.back()">取消</button>
            <button v-if="isEdit" type="button" class="btn btn-danger" @click="showDeleteConfirm = true" :disabled="submitting">删除商品</button>
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              {{ submitting ? '提交中...' : (isEdit ? '提交更新' : '提交审核') }}
            </button>
          </div>
        </form>
      </div>

      <div class="tips-sidebar">
        <div class="glass-panel tips-panel">
          <h3>📝 发布须知</h3>
          <ul class="tips-list">
            <li>
              <strong>包结构规范</strong>
              数字商品需要上传 ZIP 商品包；实体商品无需上传文件。
            </li>
            <li>
              <strong>自动解析</strong>
              数字商品上传 ZIP 后系统自动读取压缩包。
            </li>
            <li>
              <strong>安全审核</strong>
              数字商品上传后会进行自动安全扫描；实体商品跳过 ZIP 扫描。
            </li>
            <li>
              <strong>知识产权</strong>
              请确保您未侵犯他人的版权或商业机密。
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Delete Confirm Modal -->
    <ConfirmModal
      :visible="showDeleteConfirm"
      title="删除商品"
      message="确定要删除这个商品吗？删除后商品将不再展示。"
      confirmText="确认删除"
      cancelText="取消"
      type="danger"
      @confirm="handleDelete"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { createSkill, updateSkill, getSkillDetail, getCategories, createVersion } from '../api/skill.js'
import { uploadImage, uploadSkillPackage } from '../api/upload.js'
import { userStore } from '../stores/user.js'
import { del } from '../api/request.js'
import ConfirmModal from '../components/ConfirmModal.vue'
import CustomSelect from '../components/CustomSelect.vue'
import { useToast, KV_SYNC_HINT } from '../composables/useToast.js'

const ERROR_SKILL_TITLE_DUPLICATE = 3005
const ERROR_PUBLISH_LIMIT_EXCEEDED = 3008

const router = useRouter()
const route = useRoute()
const toast = useToast()

const isEdit = computed(() => !!route.params.id)

const form = reactive({
  title: '',
  category_id: '',
  price: 0,
  version: '1.0.0',
  description: '',
  subtitle: '',
  cover_image: null,
  screenshots: [],
  file_url: null,
  file_size: null,
  file_hash: null,
  changelog: '',
  // ── Generic-product extensions ──
  product_type: 'digital',     // 'digital' | 'physical'
  sale_mode: 'points',         // 'points' | 'cash' | 'both'
  cash_price_yuan: 0,
  stock: null,                 // null = 不限
  shipping_fee_yuan: 0,
  shipping_required: false,
})

const categories = ref([])
const tagsInput = ref('')
const descriptionText = ref('')
const descTab = ref('edit')
const descRef = ref(null)
const imageInput = ref(null)
const fileInput = ref(null)
const screenshotPreviews = ref([])
const packageFileName = ref('')
const packageUploaded = ref(false)
const uploadingPackage = ref(false)
const skillMdParsed = ref(false)
const submitting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const titleErrorMsg = ref('')
const submitHelpMsg = ref('')
const showDeleteConfirm = ref(false)
const packageFileTree = ref([])
const newFileUploaded = ref(false)
const categoryOptions = computed(() =>
  categories.value.map(cat => ({ value: cat.id, label: cat.name, icon: cat.icon }))
)

const renderedDesc = computed(() => DOMPurify.sanitize(marked.parse(descriptionText.value || '')))

const formatFileSize = (bytes) => {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const triggerImageUpload = () => imageInput.value?.click()
const triggerFileUpload = () => fileInput.value?.click()

const isPointsMode = () => form.sale_mode === 'points' || form.sale_mode === 'both'
const isCashMode = () => form.sale_mode === 'cash' || form.sale_mode === 'both'

const normalizeProductMode = () => {
  if (form.product_type === 'physical') {
    form.sale_mode = 'cash'
    form.price = 0
    form.shipping_required = true
    form.file_url = null
    form.file_size = null
    form.file_hash = null
    packageFileName.value = ''
    packageUploaded.value = false
    packageFileTree.value = []
    newFileUploaded.value = false
    return
  }

  if (!['points', 'cash', 'both'].includes(form.sale_mode)) {
    form.sale_mode = 'points'
  }
}

watch(() => form.product_type, normalizeProductMode)
watch(() => form.sale_mode, () => {
  if (form.product_type === 'physical' && form.sale_mode !== 'cash') {
    form.sale_mode = 'cash'
    return
  }
  if (!isPointsMode()) form.price = 0
  if (!isCashMode()) {
    form.cash_price_yuan = 0
    form.shipping_fee_yuan = 0
  }
})

const clearTitleIssue = () => {
  titleErrorMsg.value = ''
  if (submitHelpMsg.value.includes('名称')) {
    submitHelpMsg.value = ''
  }
}

const resolveSkillSubmitError = (response) => {
  const code = Number(response?.code || 0)
  const rawMessage = (response?.message || '提交失败，请稍后重试').trim()

  if (code === ERROR_SKILL_TITLE_DUPLICATE) {
    return {
      message: rawMessage,
      titleError: '这个名称已被待审核或已上架商品占用，请改成更具体的名称。',
      help: '建议在名称里补充作者名、版本号或适用场景后再提交，例如“XX 工作流 Pro v2”。',
      toastTitle: '名称重复',
      toastMessage: '请修改商品名称后再提交。',
    }
  }

  if (code === ERROR_PUBLISH_LIMIT_EXCEEDED) {
    return {
      message: rawMessage,
      help: '当前账号最多保留 200 个未删除商品。请先删除不需要的商品，再重新提交。',
      toastTitle: '已达发布上限',
      toastMessage: rawMessage,
    }
  }

  if (code === 9999) {
    return {
      message: rawMessage,
      help: '服务器当前处理失败，请稍后重试；如果多次出现，请联系管理员检查日志。',
      toastTitle: '服务器异常',
      toastMessage: '服务器处理失败，请稍后重试。',
    }
  }

  return {
    message: rawMessage,
    help: '',
    toastTitle: '提交失败',
    toastMessage: rawMessage,
  }
}

const getFileIcon = (name) => {
  const ext = (name || '').split('.').pop().toLowerCase()
  const iconMap = { js: '📄', ts: '📄', py: '🐍', md: '📝', json: '📋', yaml: '📋', yml: '📋', txt: '📃', html: '🌐', css: '🎨', sh: '⚙️', bat: '⚙️' }
  return iconMap[ext] || '📄'
}

const packageFileTreeDisplay = computed(() => {
  const raw = Array.isArray(packageFileTree.value) ? packageFileTree.value : []
  if (!raw.length) return []

  const map = new Map()
  raw.forEach((entry) => {
    const name = (entry?.name || '').replace(/\/+/g, '/').replace(/^\/+|\/+$/g, '')
    if (!name) return
    map.set(name, {
      ...entry,
      name,
      base_name: name.split('/').pop(),
      children: [],
    })
  })

  // 保证父目录存在，避免后端漏掉目录节点时渲染错位
  Array.from(map.keys()).forEach((name) => {
    const parts = name.split('/')
    for (let i = 1; i < parts.length; i += 1) {
      const parent = parts.slice(0, i).join('/')
      if (!map.has(parent)) {
        map.set(parent, {
          name: parent,
          base_name: parts[i - 1],
          is_dir: true,
          size: 0,
          children: [],
        })
      }
    }
  })

  const roots = []
  map.forEach((node, name) => {
    const idx = name.lastIndexOf('/')
    const parent = idx > -1 ? name.slice(0, idx) : ''
    if (parent && map.has(parent)) {
      map.get(parent).children.push(node)
    } else {
      roots.push(node)
    }
  })

  const sortNodes = (nodes) => {
    nodes.sort((a, b) => {
      if (!!a.is_dir !== !!b.is_dir) return a.is_dir ? -1 : 1
      return (a.base_name || '').localeCompare((b.base_name || ''), 'zh-CN')
    })
    nodes.forEach((n) => sortNodes(n.children || []))
  }
  sortNodes(roots)

  const flattened = []
  const walk = (nodes, depth) => {
    nodes.forEach((node) => {
      flattened.push({ ...node, depth })
      if (node.is_dir && node.children?.length) {
        walk(node.children, depth + 1)
      }
    })
  }
  walk(roots, 0)
  return flattened
})

const handleImageUpload = async (e) => {
  const files = Array.from(e.target.files || [])
  if (!files.length) return

  for (const file of files) {
    if (screenshotPreviews.value.length >= 6) break

    const localUrl = URL.createObjectURL(file)
    screenshotPreviews.value.push(localUrl)

    try {
      const res = await uploadImage(file)
      if (res.code === 0) {
        const url = res.data?.url || res.data?.file_url
        if (url) {
          form.screenshots.push(url)
          // Replace local preview with remote URL
          const idx = screenshotPreviews.value.indexOf(localUrl)
          if (idx >= 0) screenshotPreviews.value[idx] = url
        }
      } else {
        errorMsg.value = res.message || '图片上传失败'
        // Remove failed preview
        const idx = screenshotPreviews.value.indexOf(localUrl)
        if (idx >= 0) screenshotPreviews.value.splice(idx, 1)
      }
    } catch (err) {
      errorMsg.value = '图片上传失败'
      const idx = screenshotPreviews.value.indexOf(localUrl)
      if (idx >= 0) screenshotPreviews.value.splice(idx, 1)
    }
  }

  // Reset input so same file can be selected again
  if (imageInput.value) imageInput.value.value = ''
}

const removeScreenshot = (idx) => {
  screenshotPreviews.value.splice(idx, 1)
  form.screenshots.splice(idx, 1)
}

const handleFileUpload = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  packageFileName.value = file.name
  uploadingPackage.value = true
  errorMsg.value = ''
  successMsg.value = ''

  try {
    const uploadRes = await uploadSkillPackage(file)
    if (uploadRes.code === 0) {
      form.file_url = uploadRes.data?.url || uploadRes.data?.file_url
      form.file_size = file.size
      form.file_hash = uploadRes.data?.file_hash || null
      packageUploaded.value = true
      newFileUploaded.value = true

      // Store file tree
      packageFileTree.value = uploadRes.data?.file_tree || []

      // Auto-fill from SKILL.md
      const md = uploadRes.data?.skill_md
      if (md) {
        skillMdParsed.value = true
        if (md.title && !form.title) form.title = md.title
        if (md.description && !form.subtitle) form.subtitle = md.description
        if (md.full_description && !descriptionText.value) descriptionText.value = md.full_description
        if (md.version && form.version === '1.0.0') form.version = md.version
        if (md.tags && !tagsInput.value) tagsInput.value = md.tags.join(', ')
        successMsg.value = 'SKILL.md 已解析，表单已自动填充'
      } else {
        successMsg.value = '商品包上传成功（未找到 SKILL.md）'
      }
    } else {
      errorMsg.value = uploadRes.message || '商品包上传失败'
      packageUploaded.value = false
    }
  } catch (err) {
    errorMsg.value = '商品包上传失败'
    packageUploaded.value = false
  } finally {
    uploadingPackage.value = false
  }
}

const insertMd = (field, text) => {
  const targetRef = descRef.value
  if (!targetRef) {
    descriptionText.value += text
    return
  }
  const start = targetRef.selectionStart
  const end = targetRef.selectionEnd
  const val = descriptionText.value
  descriptionText.value = val.substring(0, start) + text + val.substring(end)
  setTimeout(() => {
    targetRef.focus()
    targetRef.setSelectionRange(start + text.length, start + text.length)
  }, 0)
}

const handleSubmit = async () => {
  errorMsg.value = ''
  successMsg.value = ''
  titleErrorMsg.value = ''
  submitHelpMsg.value = ''

  if (!form.title.trim()) { errorMsg.value = '请填写商品名称'; return }
  if (!form.category_id) { errorMsg.value = '请选择分类'; return }
  if (!descriptionText.value.trim()) { errorMsg.value = '请填写详细介绍'; return }

  normalizeProductMode()

  if (form.product_type === 'digital' && !form.file_url) {
    errorMsg.value = '数字商品请先上传 ZIP 商品包'
    return
  }
  if (form.product_type === 'physical' && form.sale_mode !== 'cash') {
    errorMsg.value = '实体商品仅支持现金支付'
    return
  }
  if (isCashMode() && (!form.cash_price_yuan || form.cash_price_yuan <= 0)) {
    errorMsg.value = '启用现金售卖时必须填写大于 0 的现金价格'
    return
  }

  submitting.value = true

  try {
    const tags = tagsInput.value ? tagsInput.value.split(/[,，]/).map(t => t.trim()).filter(Boolean) : []
    const pointsPrice = isPointsMode() ? (Number(form.price) || 0) : 0
    const cashPrice = isCashMode() ? (Number(form.cash_price_yuan) || 0) : 0
    const isFree = form.sale_mode === 'points' ? pointsPrice === 0 : false
    const isDigital = form.product_type === 'digital'

    const payload = {
      title: form.title,
      description: descriptionText.value,
      subtitle: form.subtitle || '',
      category_id: parseInt(form.category_id),
      price: pointsPrice,
      is_free: isFree,
      tags,
      cover_image: form.screenshots[0] || null,
      screenshots: form.screenshots,
      file_url: isDigital ? form.file_url : null,
      file_size: isDigital ? form.file_size : null,
      file_hash: isDigital ? form.file_hash : null,
      original_filename: isDigital ? (packageFileName.value || null) : null,
      version: form.version || '1.0.0',
      file_tree: isDigital && packageFileTree.value.length > 0 ? packageFileTree.value : undefined,
      // ── Generic-product extensions ──
      product_type: form.product_type,
      sale_mode: form.sale_mode,
      cash_price_yuan: cashPrice,
      stock: form.stock === '' || form.stock === null ? null : Number(form.stock),
      shipping_fee_yuan: Number(form.shipping_fee_yuan) || 0,
      shipping_required: form.product_type === 'physical' ? true : !!form.shipping_required,
    }

    let res
    if (isEdit.value) {
      res = await updateSkill(route.params.id, payload)

      // Create version record when updating with new file or changelog
      if (res.code === 0 && (newFileUploaded.value || form.changelog.trim())) {
        try {
          await createVersion(route.params.id, {
            version: form.version || '1.0.0',
            changelog: form.changelog || '更新商品',
            file_url: form.file_url || '',
            file_size: form.file_size,
            file_hash: form.file_hash,
          })
        } catch (e) { /* version creation is best-effort */ }
      }
    } else {
      res = await createSkill(payload)
    }

    if (res.code === 0) {
      const status = res.data?.status
      const rejectReason = res.data?.reject_reason
      if (status === 'approved') {
        toast.success(isEdit.value ? '商品已更新，审核通过已自动上架！' + '\n' + KV_SYNC_HINT : '商品提交成功，审核通过已自动上架！' + '\n' + KV_SYNC_HINT, '审核通过')
        setTimeout(() => router.push('/profile'), 2000)
      } else if (status === 'rejected') {
        const isRateLimit = rejectReason && rejectReason.includes('频率限制')
        if (isRateLimit) {
          errorMsg.value = `${rejectReason}。您可以稍等片刻后重新点击「提交审核」。`
        } else {
          errorMsg.value = rejectReason || '商品审核未通过，请检查内容后重新提交'
        }
        toast.error(rejectReason || '商品审核未通过', '审核未通过')
      } else {
        toast.success((isEdit.value ? '商品已更新，等待审核中...' : '商品已提交审核，审核结果请在「我发布的商品」中查看') + '\n' + KV_SYNC_HINT, '已提交')
        setTimeout(() => router.push('/profile'), 2000)
      }
    } else {
      const submitError = resolveSkillSubmitError(res)
      errorMsg.value = submitError.message
      titleErrorMsg.value = submitError.titleError || ''
      submitHelpMsg.value = submitError.help || ''
      toast.error(submitError.toastMessage, submitError.toastTitle)
    }
  } catch (e) {
    errorMsg.value = '网络错误，请重试'
    submitHelpMsg.value = ''
  } finally {
    submitting.value = false
  }
}

const handleDelete = async () => {
  showDeleteConfirm.value = false
  submitting.value = true
  try {
    const res = await del(`/skills/${route.params.id}`)
    if (res.code === 0) {
      successMsg.value = '商品已删除。' + KV_SYNC_HINT
      setTimeout(() => router.push('/profile'), 1500)
    } else {
      errorMsg.value = res.message || '删除失败'
    }
  } catch (e) {
    errorMsg.value = '网络错误'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  try {
    const res = await getCategories()
    if (res.code === 0) categories.value = res.data?.categories || res.data?.items || []
  } catch (e) { /* ignore */ }

  // Edit mode: load existing skill data
  if (route.params.id) {
    try {
      const res = await getSkillDetail(route.params.id)
      if (res.code === 0 && res.data) {
        const s = res.data
        form.title = s.title || ''
        form.subtitle = s.subtitle || ''
        form.category_id = s.category_id || ''
        form.price = s.price || 0
        form.version = s.version || '1.0.0'
        form.cover_image = s.cover_image || null
        form.file_url = s.file_url || null
        form.file_size = s.file_size || null
        form.file_hash = s.file_hash || null
        form.screenshots = s.screenshots || []
        form.product_type = s.product_type || 'digital'
        form.sale_mode = s.sale_mode || (s.cash_price_yuan ? 'cash' : 'points')
        form.cash_price_yuan = Number(s.cash_price_yuan) || 0
        form.stock = s.stock ?? null
        form.shipping_fee_yuan = Number(s.shipping_fee_yuan) || 0
        form.shipping_required = !!s.shipping_required
        packageFileTree.value = s.file_tree || []
        descriptionText.value = s.description || ''
        tagsInput.value = (s.tags || []).join(', ')
        if (form.screenshots.length > 0) {
          screenshotPreviews.value = [...form.screenshots]
        }
        if (s.file_url) {
          packageUploaded.value = true
          packageFileName.value = s.original_filename || '已上传的商品包'
        }
        normalizeProductMode()
      }
    } catch (e) { /* ignore */ }
  }
})
</script>

<style scoped>
.upload-container { padding: 40px 24px 100px; max-width: 1080px; }

.page-header { margin-bottom: 40px; }
.page-title { font-size: 36px; font-weight: 800; margin-bottom: 12px; }
.page-subtitle { font-size: 16px; color: var(--text-secondary); }

.upload-layout { display: grid; grid-template-columns: 1fr 320px; gap: 32px; align-items: start; }
.form-card { padding: 40px; }
.form-group { margin-bottom: 24px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 8px; color: var(--text-primary); }
.required { color: var(--color-primary); }

.field-hint { font-size: 12px; color: var(--color-primary); margin-top: 6px; opacity: 0.8; }
.field-error { font-size: 12px; color: #ff6b6b; margin-top: 6px; }
.error-hint { font-size: 13px; color: #ffb86b; margin-bottom: 12px; line-height: 1.6; }

.form-control {
  width: 100%; background: var(--bg-glass); border: 1px solid var(--border-glass);
  border-radius: 8px; padding: 12px 16px; color: var(--text-primary); font-family: inherit;
  font-size: 15px; transition: var(--transition-smooth);
}
.form-control:focus { outline: none; border-color: var(--color-primary); box-shadow: 0 0 0 2px var(--color-primary-glow); }
textarea.form-control { resize: vertical; }

.input-with-icon { position: relative; }
.input-with-icon .input-icon {
  position: absolute; right: 16px; top: 50%; transform: translateY(-50%);
  pointer-events: none;
  line-height: 1;
  font-size: 16px;
}
.input-with-icon .form-control { padding-right: 44px; }

.upload-box {
  border: 2px dashed var(--border-glass); border-radius: 12px;
  background: rgba(255,255,255,0.02); text-align: center;
  transition: var(--transition-smooth); cursor: pointer; overflow: hidden;
}
.upload-box:hover { border-color: var(--color-primary); background: rgba(30, 224, 127, 0.03); }
.upload-box.has-file { border-color: #34C759; border-style: solid; }
.upload-box.uploading { border-color: var(--color-accent); animation: pulse-border 1.5s ease-in-out infinite; }

@keyframes pulse-border {
  0%, 100% { border-color: var(--color-accent); }
  50% { border-color: var(--color-primary); }
}

.upload-content { padding: 40px 20px; cursor: pointer; }
.upload-content.compact { padding: 24px 20px; }
.upload-content .icon { font-size: 40px; display: block; margin-bottom: 12px; }
.upload-content p { color: var(--text-primary); font-size: 15px; margin-bottom: 4px; }
.upload-content .sub-text { color: var(--text-tertiary); font-size: 13px; }

.upload-box.has-tree .upload-content { padding: 16px 20px; }
.upload-box.has-tree { cursor: default; }

/* Uploaded header (compact display inside upload box) */
.uploaded-header {
  display: flex; align-items: center; gap: 12px; width: 100%; text-align: left;
}
.uploaded-header .icon-sm { font-size: 24px; flex-shrink: 0; }
.uploaded-info { flex: 1; min-width: 0; }
.uploaded-name { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.uploaded-size { font-size: 13px; color: var(--text-tertiary); margin: 0; }
.btn-reupload {
  background: rgba(255,255,255,0.08); border: 1px solid var(--border-glass);
  color: var(--text-secondary); padding: 6px 14px; border-radius: 6px;
  font-size: 12px; cursor: pointer; transition: var(--transition-smooth); flex-shrink: 0;
}
.btn-reupload:hover { background: rgba(255,255,255,0.15); color: var(--text-primary); }

.file-upload .upload-content { padding: 40px 20px; }
.file-upload.has-tree .upload-content { padding: 16px 20px; }

/* Screenshots */
.screenshots-area { display: flex; flex-direction: column; gap: 12px; }
.screenshot-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }

.screenshot-item {
  position: relative;
  border-radius: 10px;
  overflow: hidden;
  aspect-ratio: 16/9;
  border: 1px solid var(--border-glass);
}

.screenshot-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.screenshot-remove {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.screenshot-item:hover .screenshot-remove { opacity: 1; }
.screenshot-remove:hover { background: rgba(255, 59, 48, 0.8); }

.error-msg {
  color: #FF453A; font-size: 14px; padding: 10px 16px;
  background: rgba(255, 69, 58, 0.1); border-radius: 8px;
  border: 1px solid rgba(255, 69, 58, 0.2); margin-bottom: 16px;
}
.success-msg {
  color: #34C759; font-size: 14px; padding: 10px 16px;
  background: rgba(52, 199, 89, 0.1); border-radius: 8px;
  border: 1px solid rgba(52, 199, 89, 0.2); margin-bottom: 16px;
}

.form-actions {
  display: flex; justify-content: flex-end; gap: 16px; margin-top: 40px;
  padding-top: 24px; border-top: 1px solid var(--border-glass);
}

.btn-danger {
  background: rgba(255, 59, 48, 0.15);
  border: 1px solid rgba(255, 59, 48, 0.3);
  color: #FF453A;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
  margin-right: auto;
}
.btn-danger:hover { background: rgba(255, 59, 48, 0.3); }

/* Sidebar */
.tips-panel { padding: 24px; position: sticky; top: 96px; }
.tips-panel h3 { font-size: 16px; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
.tips-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 20px; }
.tips-list li { font-size: 14px; color: var(--text-secondary); line-height: 1.6; }
.tips-list strong { display: block; color: var(--text-primary); margin-bottom: 4px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }

/* Markdown Editor */
.md-editor { border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; }
.editor-tabs { display: flex; background: rgba(0, 0, 0, 0.4); border-bottom: 1px solid var(--border-glass); }
.editor-tabs > span {
  padding: 10px 20px; font-size: 14px; color: var(--text-secondary);
  cursor: pointer; border-bottom: 2px solid transparent; transition: var(--transition-smooth);
}
.editor-tabs > span:hover { color: var(--text-primary); }
.editor-tabs > span.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }

.toolbar { margin-left: auto; display: flex; align-items: center; padding-right: 8px; gap: 4px; }
.toolbar button {
  background: transparent; border: none; color: var(--text-secondary);
  width: 28px; height: 28px; border-radius: 4px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: var(--transition-smooth); font-family: var(--font-mono); font-size: 13px;
}
.toolbar button:hover { background: rgba(255, 255, 255, 0.1); color: var(--text-primary); }
.toolbar .divider { width: 1px; height: 16px; background: var(--border-glass); margin: 0 4px; }

.editor-content { flex: 1; }
.editor-content .form-control { border: none; border-radius: 0; background: rgba(20, 20, 25, 0.6); }
.editor-content .form-control:focus { box-shadow: none; }

.preview-area {
  padding: 16px; min-height: 200px; background: rgba(10, 10, 14, 0.8);
  font-size: 14px; color: #e6e6e6;
}
.preview-area :deep(h1), .preview-area :deep(h2), .preview-area :deep(h3) { color: var(--text-primary); margin-top: 16px; margin-bottom: 8px; }
.preview-area :deep(pre) {
  background: rgba(0,0,0,0.5); border: 1px solid var(--border-glass);
  padding: 12px; border-radius: 8px; overflow-x: auto; font-family: var(--font-mono); color: #a6e22e;
}

.empty-text { color: var(--text-tertiary); font-style: italic; text-align: center; margin-top: 40px; }

@media (max-width: 768px) {
  .upload-layout { grid-template-columns: 1fr; }
  .form-row { grid-template-columns: 1fr; }
  .screenshot-grid { grid-template-columns: repeat(2, 1fr); }
}

/* File Tree (inside upload box) */
.file-tree-section {
  border-top: 1px solid var(--border-glass);
}
.file-tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid var(--border-glass);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.file-tree-count {
  font-weight: 400;
  color: var(--text-tertiary);
  font-size: 12px;
}
.file-tree-list {
  max-height: 240px;
  overflow-y: auto;
}
.file-tree-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  font-size: 13px;
  color: var(--text-secondary);
  border-bottom: 1px solid rgba(255,255,255,0.02);
}
.file-tree-item.is-dir {
  color: var(--text-primary);
  font-weight: 500;
}
.file-tree-item:hover {
  background: rgba(255, 255, 255, 0.03);
}
.file-icon { font-size: 14px; flex-shrink: 0; }
.file-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { font-size: 11px; color: var(--text-tertiary); flex-shrink: 0; }

/* ─── 亮色主题适配 ─── */
[data-theme="light"] .editor-tabs { background: rgba(0, 0, 0, 0.04); }
[data-theme="light"] .toolbar button:hover { background: rgba(0, 0, 0, 0.08); }
[data-theme="light"] .editor-content .form-control { background: rgba(255, 255, 255, 0.9); }
[data-theme="light"] .preview-area { background: rgba(255, 255, 255, 0.95); color: #1a1a2e; }
[data-theme="light"] .preview-area :deep(pre) { background: rgba(0, 0, 0, 0.04); color: #2e7d32; }
[data-theme="light"] .upload-box { background: rgba(255, 255, 255, 0.6); }
[data-theme="light"] .file-tree-header { background: rgba(0, 0, 0, 0.02); }
[data-theme="light"] .file-tree-item:hover { background: rgba(0, 0, 0, 0.03); }
[data-theme="light"] .file-tree-item { border-bottom-color: rgba(0, 0, 0, 0.04); }
</style>
