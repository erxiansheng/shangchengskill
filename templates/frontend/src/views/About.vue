<template>
  <div class="about-container container">
    <div class="page-header">
      <h1 class="page-title">关于 <span class="primary-gradient">EdgeOneMall</span></h1>
      <p class="page-subtitle">探索 2026 最强的商品共享经济网络。</p>
    </div>

    <!-- 优先展示后台配置的关于内容（Markdown 渲染） -->
    <div v-if="renderedAbout" class="about-content glass-panel markdown-body" v-html="renderedAbout"></div>

    <!-- 默认关于内容（仅在后台未配置时使用） -->
    <template v-else>
      <div class="about-content glass-panel">
        <h2>🦞 我们的愿景</h2>
        <p>EdgeOneMall Skill致力于打造一个公平、透明、高效的商品交易市场。我们相信每个人都拥有独特的知识和商品，值得被发现、被分享、被合理变现。</p>
        <p>无论你是 AI 模型架构师、前端开发者、设计达人，还是数据分析专家——你的商品都可以在 EdgeOneMall 上打包成即插即用的 Skill，让全球用户一键获取和体验。</p>

        <h2>🎯 核心特色</h2>
        <ul>
          <li><strong>商品即商品</strong>：将你的专业知识打包成标准化的 Skill，上传即可销售</li>
          <li><strong>积分体系</strong>：灵活的积分充值与消费系统，支持作者收益提现</li>
          <li><strong>即时交付</strong>：购买后立即获取，无需等待，体验极致效率</li>
          <li><strong>评价体系</strong>：真实用户评价帮助发现优质内容，促进社区良性发展</li>
        </ul>

        <h2>💡 如何开始</h2>
        <div class="steps">
          <div class="step">
            <div class="step-num">1</div>
            <div class="step-text">
              <strong>扫码登录</strong>
              <p>使用微信或 QQ 扫码登录，无需注册，一键进入</p>
            </div>
          </div>
          <div class="step">
            <div class="step-num">2</div>
            <div class="step-text">
              <strong>探索市场</strong>
              <p>浏览商品市场，按分类、评分、热度发现优质 Skill</p>
            </div>
          </div>
          <div class="step">
            <div class="step-num">3</div>
            <div class="step-text">
              <strong>购买使用</strong>
              <p>充值积分，一键购买，立即下载使用各类 Skill</p>
            </div>
          </div>
          <div class="step">
            <div class="step-num">4</div>
            <div class="step-text">
              <strong>发布变现</strong>
              <p>打包你的专业商品上传，获得持续的积分收益</p>
            </div>
          </div>
        </div>

        <h2>📬 联系我们</h2>
        <p>有任何问题、建议或合作意向，欢迎通过以下方式联系：</p>
        <ul>
          <li>平台内反馈：登录后在设置页面提交反馈</li>
        </ul>

        <div class="about-footer">
          <p>© {{ new Date().getFullYear() }} EdgeOneMall. Built with 🦞 by the EdgeOneMall community.</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { get } from '../api/request.js'

const remoteAbout = ref('')

onMounted(async () => {
  try {
    const res = await get('/site/public-settings')
    if (res.code === 0 && res.data?.about) {
      remoteAbout.value = res.data.about
    }
  } catch (e) {
    // 使用默认内容
  }
})

// Markdown 渲染（与 SkillDetail.vue 保持一致），自动识别 Bilibili / YouTube 视频链接为内嵌播放器
const renderedAbout = computed(() => {
  let text = remoteAbout.value || ''
  if (!text) return ''

  // Bilibili: https://www.bilibili.com/video/BVxxxxxxx
  text = text.replace(
    /^(https?:\/\/(?:www\.)?bilibili\.com\/video\/(BV[a-zA-Z0-9]+)[^\s]*)$/gm,
    '\n\n<div class="video-embed"><iframe src="https://player.bilibili.com/player.html?bvid=$2&autoplay=0&high_quality=1&danmaku=0" scrolling="no" frameborder="no" allowfullscreen="true"></iframe></div>\n\n'
  )
  // YouTube: https://www.youtube.com/watch?v=xxx
  text = text.replace(
    /^https?:\/\/(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)[^\s]*$/gm,
    '\n\n<div class="video-embed"><iframe src="https://www.youtube.com/embed/$1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>\n\n'
  )
  // YouTube short link: https://youtu.be/xxx
  text = text.replace(
    /^https?:\/\/youtu\.be\/([a-zA-Z0-9_-]+)[^\s]*$/gm,
    '\n\n<div class="video-embed"><iframe src="https://www.youtube.com/embed/$1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>\n\n'
  )
  // 自定义直链视频：单独成行的 .mp4/.webm/.ogg/.mov 链接
  text = text.replace(
    /^(https?:\/\/[^\s]+\.(?:mp4|webm|ogg|mov))$/gim,
    '\n\n<div class="video-embed"><video src="$1" controls preload="metadata" style="width:100%;border-radius:8px"></video></div>\n\n'
  )

  const html = marked.parse(text)
  const clean = DOMPurify.sanitize(html, {
    ADD_TAGS: ['iframe', 'video', 'source'],
    ADD_ATTR: ['allow', 'allowfullscreen', 'frameborder', 'scrolling', 'src', 'controls', 'preload', 'autoplay', 'muted', 'loop', 'poster'],
  })
  return clean.replace(/<table>/g, '<div class="table-wrapper"><table>').replace(/<\/table>/g, '</table></div>')
})
</script>

<style scoped>
.about-container { padding: 40px 24px 100px; max-width: 800px; }
.page-header { margin-bottom: 32px; }
.page-title { font-size: 32px; font-weight: 800; margin-bottom: 8px; }
.page-subtitle { color: var(--text-secondary); }
.about-content { padding: 40px; }
h2 { color: var(--text-primary); margin-bottom: 16px; margin-top: 32px; font-size: 22px; }
h2:first-child { margin-top: 0; }
p, li { color: var(--text-secondary); line-height: 1.8; margin-bottom: 12px; }
ul { padding-left: 20px; }
li { margin-bottom: 8px; }

.steps {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 16px;
}

.step {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.step-num {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), #FF9500);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}

.step-text {
  flex: 1;
}

.step-text strong {
  color: var(--text-primary);
  font-size: 16px;
}

.step-text p {
  margin-top: 4px;
  margin-bottom: 0;
  font-size: 14px;
}

.about-footer {
  margin-top: 48px;
  padding-top: 24px;
  border-top: 1px solid var(--border-glass);
  text-align: center;
}

.about-footer p {
  color: var(--text-tertiary);
  font-size: 13px;
}

@media (max-width: 768px) {
  .about-container { padding: 24px 16px 80px; }
  .about-content { padding: 24px; }
  .page-title { font-size: 26px; }
  h2 { font-size: 18px; }
}
</style>
