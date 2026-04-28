<template>
  <div class="skill-detail container">
    <button class="btn btn-glass btn-back" @click="$router.back()">
      &larr; 返回市场
    </button>

    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载商品详情...</p>
    </div>

    <div class="detail-grid" v-else-if="skill">
      <!-- Left Column: Main Content -->
      <div class="main-col">
        <div class="header-glass glass-panel">
          <div class="header-info">
            <div class="tags">
              <span class="tag-category">{{ skill.category_name || '未分类' }}</span>
              <span class="tag" v-for="tag in (skill.tags || []).slice(0, 3)" :key="tag">{{ tag }}</span>
            </div>
            <h1 class="title">{{ skill.title }}</h1>
            <p class="subtitle">{{ skill.subtitle || skill.description }}</p>

            <div class="meta-row">
              <div class="author">
                <div class="author-avatar-wrap" @click="openAuthorProfile">
                  <img :src="skill.author_avatar || 'https://api.dicebear.com/7.x/avataaars/svg?seed=default'" alt="Author" />
                </div>
                <div class="author-info">
                  <div class="author-name-row">
                    <span class="author-name-link" @click="openAuthorProfile">{{ skill.author_name || '未知作者' }}</span>
                    <span v-if="skill.author_role === 'admin'" class="review-lv admin-lv">管理员</span>
                    <span v-else-if="skill.author_level_info" class="review-lv" @click="showLevelModal = true">{{ skill.author_level_info.icon }} {{ skill.author_level_info.name }}</span>
                    <span v-else class="review-lv" @click="showLevelModal = true">🦐 新手虾</span>
                  </div>
                  <span class="publish-date">发布于 {{ formatDateShort(skill.published_at || skill.created_at) }}</span>
                </div>
              </div>
              <div class="stats">
                <span>⭐ {{ skill.avg_rating || 0 }} ({{ skill.review_count || 0 }} 评价)</span>
                <span>📥 {{ skill.download_count || 0 }} 次下载</span>
                <span>📦 v{{ skill.version || '1.0.0' }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="content-tabs glass-panel">
          <div class="tab-scroller">
            <div class="tab" :class="{ active: activeTab === 'intro' }" @click="activeTab = 'intro'">商品介绍</div>
            <div class="tab" :class="{ active: activeTab === 'install', locked: !purchased && !isOwner && !isFreeSkill }" @click="handleInstallTabClick">
              <span v-if="!purchased && !isOwner && !isFreeSkill">🔒 </span>安装方式
            </div>
            <div class="tab" :class="{ active: activeTab === 'changelog' }" @click="activeTab = 'changelog'">版本记录</div>
            <div class="tab" :class="{ active: activeTab === 'screenshots' }" @click="activeTab = 'screenshots'" v-if="hasScreenshots">效果展示</div>
            <div class="tab" :class="{ active: activeTab === 'reviews' }" @click="activeTab = 'reviews'; loadReviews()">
              用户评价 ({{ skill.review_count || 0 }})
            </div>
          </div>

          <div class="tab-content">
            <!-- Intro -->
            <div class="markdown-body" v-if="activeTab === 'intro'" v-html="renderedDesc"></div>

            <!-- Changelog -->
            <div class="markdown-body" v-if="activeTab === 'changelog'">
              <div v-if="versions.length === 0"><p>暂无版本记录</p></div>
              <div v-for="ver in versions" :key="ver.id">
                <h2>📝 v{{ ver.version }} <span style="font-size: 14px; color: var(--text-tertiary); font-weight: 400;">{{ formatDateShort(ver.created_at) }}</span></h2>
                <p>{{ ver.changelog || '无更新说明' }}</p>
              </div>
            </div>

            <!-- Screenshots -->
            <div v-if="activeTab === 'screenshots'" class="screenshots-section">
              <div class="screenshots-grid">
                <div
                  v-for="(img, idx) in (skill.screenshots || [])"
                  :key="idx"
                  class="screenshot-card"
                  @click="openLightbox(idx)"
                >
                  <img :src="img" alt="效果图" />
                </div>
              </div>
            </div>

            <!-- Reviews -->
            <div class="markdown-body" v-if="activeTab === 'reviews'">
              <!-- Write review -->
              <div class="review-form" v-if="userStore.isLoggedIn && (purchased || isFreeSkill)">
                <h3>写评价</h3>
                <div class="star-picker">
                  <span
                    v-for="s in 5"
                    :key="s"
                    class="star"
                    :class="{ active: s <= newReview.rating }"
                    @click="newReview.rating = s"
                  >⭐</span>
                </div>
                <div class="textarea-wrap">
                  <textarea v-model="newReview.content" class="review-textarea" placeholder="分享你的使用体验..." rows="3" :maxlength="REVIEW_MAX_LENGTH"></textarea>
                  <span class="char-count" :class="{ warn: newReview.content.length >= REVIEW_MAX_LENGTH }">{{ newReview.content.length }}/{{ REVIEW_MAX_LENGTH }}</span>
                </div>
                <div class="captcha-row">
                  <img v-if="captcha.image" :src="captcha.image" class="captcha-image" alt="验证码" @click="refreshCaptcha" title="点击刷新" />
                  <input v-model="captcha.answer" class="captcha-input" type="number" placeholder="输入答案" />
                  <button class="btn btn-glass btn-sm captcha-refresh" @click="refreshCaptcha" :disabled="captcha.loading" title="换一题">↻</button>
                </div>
                <button class="btn btn-primary btn-sm" @click="submitReview" :disabled="submittingReview">
                  {{ submittingReview ? '提交中...' : '提交评价' }}
                </button>
              </div>

              <div v-if="reviewsLoading" class="loading-state" style="padding: 20px">
                <div class="loading-spinner"></div>
              </div>
              <div v-else-if="reviews.length === 0"><p>暂无评价，快来成为第一个评价者！</p></div>
              <div v-else class="reviews-list">
                <div class="review-item" v-for="review in reviews" :key="review.id">
                  <div class="review-avatar-wrap" @click="openUserProfile(review.user_id)">
                    <img :src="review.user_avatar || 'https://api.dicebear.com/7.x/avataaars/svg?seed=default'" alt="" />
                  </div>
                  <div class="review-body">
                    <div class="review-top-row">
                      <span class="review-name" @click="openUserProfile(review.user_id)">{{ review.user_nickname || '匿名用户' }}</span>
                      <span v-if="review.user_role === 'admin'" class="review-lv admin-lv">管理员</span>
                      <span v-else-if="review.user_level_info" class="review-lv" @click="showLevelModal = true">{{ review.user_level_info.icon }} {{ review.user_level_info.name }}</span>
                      <span v-else class="review-lv" @click="showLevelModal = true">🦐 新手虾</span>
                      <span class="review-stars">{{ '⭐'.repeat(review.rating) }}</span>
                    </div>
                    <div class="review-date">{{ formatDateShort(review.created_at) }}</div>
                    <p class="review-text">{{ review.content || '用户未留下文字评价' }}</p>
                    <button
                      v-if="userStore.isLoggedIn && (review.user_id === userStore.user?.id || userStore.user?.role === 'admin')"
                      class="btn-review-delete"
                      @click="handleDeleteReview(review)"
                    >删除</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Installation Guide (auto-generated) -->
            <div v-if="activeTab === 'install'" class="install-guide-content">
              <!-- Not purchased: show purchase prompt -->
              <div v-if="!purchased && !isOwner && !isFreeSkill" class="install-lock-prompt">
                <div class="lock-icon">🔒</div>
                <h3>购买后查看安装方式</h3>
                <p>购买此商品后即可查看完整的安装教程和下载商品包</p>
                <button class="btn btn-primary" @click="handlePurchase" :disabled="purchasing">
                  {{ purchasing ? '购买中...' : `立即购买（${skill.price} 积分）` }}
                </button>
              </div>

              <!-- Purchased or free or owner: show install guide -->
              <template v-if="purchased || isOwner || isFreeSkill">
                <div class="install-tabs">
                  <button :class="{ active: installMethod === 'dialog' }" @click="installMethod = 'dialog'">通过对话安装</button>
                  <button :class="{ active: installMethod === 'zip' }" @click="installMethod = 'zip'">Zip包安装</button>
                </div>

                <!-- Dialog install -->
                <div v-if="installMethod === 'dialog'">

                  <div class="install-section">
                    <h3>方式一：通过对话安装（推荐）</h3>
                    <div class="install-block">
                      <p>将以下提示词发送给你的小龙虾或AI助手，AI 会引导你登录并自动完成安装：</p>
                      <div class="code-block">
                        <code>请阅读 EdgeOneMall 商品市场的安装说明（{{ siteOrigin }}/skill.md），按照其中的步骤下载并安装商品「{{ skill.title }}」（商品 ID: {{ skill.id }}）。</code>
                      </div>
                    </div>
                  </div>

                  <div class="install-section">
                    <h3>方式二：手动提供商品包</h3>
                    <div class="install-block">
                      <p>先点击上方「<strong>下载商品包</strong>」按钮下载 ZIP 包，然后发送给 AI 助手：</p>
                      <div class="code-block">
                        <code>请将这个商品包解压，阅读其中的 SKILL.md 文件，按照说明安装「{{ skill.title }}」商品到当前项目中。</code>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Zip install -->
                <div v-if="installMethod === 'zip'">
                  <p class="install-hint">手动下载 ZIP 商品包后，按以下步骤安装到你的环境中</p>

                  <div class="install-section">
                    <h3>步骤一：下载商品包</h3>
                    <div class="install-block">
                      <button class="btn btn-primary" @click="handleDownload" :disabled="downloading" style="margin-bottom:12px">{{ downloading ? '⏳ 下载中...' : '📥 手动下载 ZIP 包' }}</button>
                      <p>点击上方按钮下载 <code>.zip</code> 格式的商品压缩包。</p>
                    </div>
                  </div>

                  <div class="install-section">
                    <h3>步骤二：解压商品包</h3>
                    <div class="install-block">
                      <p>将下载的 ZIP 包解压到本地目录：</p>
                      <p><code>unzip {{ skill.title.replace(/\s+/g, '-').toLowerCase() }}-v{{ skill.version || '1.0.0' }}.zip -d ./skills/</code></p>
                      <p>解压后根目录应包含 <code>SKILL.md</code> 描述文件和入口执行文件。</p>
                    </div>
                  </div>

                  <div class="install-section">
                    <h3>步骤三：按照 SKILL.md 安装</h3>
                    <div class="install-block">
                      <p>打开解压目录中的 <code>SKILL.md</code> 文件，按照其中的说明完成安装配置。</p>
                      <p>通常步骤包括：</p>
                      <p>1. 将商品文件复制到 AI 助手的商品目录</p>
                      <p>2. 在 AI 助手中注册/启用商品</p>
                      <p>3. 根据需要配置参数</p>
                    </div>
                  </div>

                  <div class="install-section">
                    <h3>步骤四：验证安装</h3>
                    <div class="install-block">
                      <p>安装完成后，在 AI 助手中测试商品是否正常工作。如遇问题可查看商品介绍或联系作者。</p>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: Sidebar -->
      <div class="sidebar-col sticky-sidebar">
        <div class="purchase-card glass-panel">
          <div class="price-display">
            <span class="amount" v-if="isFreeSkill">免费</span>
            <template v-else>
              <template v-if="effectiveSaleMode === 'points'">
                <span class="amount">{{ skill.price }}</span>
                <span class="coin">💰 积分</span>
              </template>
              <template v-else-if="effectiveSaleMode === 'cash'">
                <span class="amount">¥{{ skill.cash_price_yuan }}</span>
                <span class="coin" v-if="skill.product_type === 'physical' && skill.shipping_fee_yuan">+ 运费 ¥{{ skill.shipping_fee_yuan }}</span>
              </template>
              <template v-else>
                <span class="amount">{{ skill.price }}</span>
                <span class="coin">💰 积分 / ¥{{ skill.cash_price_yuan }}</span>
              </template>
            </template>
          </div>

          <!-- 售卖方式 (both 时让用户切换) -->
          <div class="sale-mode-switch" v-if="skill.sale_mode === 'both' && !purchased && !isFreeSkill">
            <button class="btn btn-glass btn-sm" :class="{ active: chosenMode === 'points' }" @click="chosenMode = 'points'">积分支付</button>
            <button class="btn btn-glass btn-sm" :class="{ active: chosenMode === 'cash' }" @click="chosenMode = 'cash'">现金支付</button>
          </div>

          <!-- 现金支付的渠道选择 -->
          <div class="cash-method-row" v-if="(effectiveSaleMode === 'cash' || (skill.sale_mode === 'both' && chosenMode === 'cash')) && !purchased && !isFreeSkill">
            <button class="pm-pill" :class="{ active: cashMethod === 'wechat' }" @click="cashMethod = 'wechat'">💬 微信支付</button>
            <button class="pm-pill" :class="{ active: cashMethod === 'alipay' }" @click="cashMethod = 'alipay'">💳 支付宝</button>
          </div>

          <div class="action-buttons">
            <template v-if="purchased || isFreeSkill">
              <button v-if="skill.product_type !== 'physical'" class="btn btn-primary btn-block text-lg" @click="handleDownload" :disabled="downloading">{{ downloading ? '⏳ 下载中...' : '⬇️ 下载商品包' }}</button>
              <div v-else class="msg-box success">✅ 已下单，等待商家发货。可在「我的 → 已购」查看物流。</div>
            </template>
            <template v-else>
              <button v-if="skill.sale_mode === 'both' ? chosenMode === 'points' : effectiveSaleMode === 'points'" class="btn btn-primary btn-block text-lg" @click="handlePurchase" :disabled="purchasing">
                {{ purchasing ? '购买中...' : `立即购买（${skill.price} 积分）` }}
              </button>
              <button v-else class="btn btn-primary btn-block text-lg" @click="handleCashPurchase" :disabled="purchasing">
                {{ purchasing ? '下单中...' : `立即支付 ¥${cashPayableTotal}` }}
              </button>
            </template>
            <button class="btn btn-glass btn-block" @click="handleFavorite" :disabled="favoriting">
              {{ isFavorited ? '💛 已收藏' : '⭐ 收藏商品' }}
            </button>
            <button v-if="isOwner" class="btn btn-glass btn-block" @click="$router.push(`/skill/${skill.id}/edit`)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              更新商品
            </button>
          </div>

          <div class="msg-box" v-if="actionMsg" :class="actionMsgType">{{ actionMsg }}</div>

          <div class="guarantee-list">
            <div class="g-item">
              <span>🛡️</span> 平台安全交易
            </div>
            <div class="g-item" v-if="!skill.force_approved">
              <span>✅</span> 已通过 VirusTotal 审核
            </div>
            <div class="g-item warning" v-else>
              <span>⚠️</span> 未通过 VirusTotal 审核，自行判断风险
            </div>
            <div class="g-item">
              <span>🔄</span> 支持免费获取后续更新
            </div>
            <div class="g-item" v-if="skill.images?.length || skill.screenshots?.length">
              <span>🖼️</span> 带示例图
            </div>
          </div>

          <hr class="divider" />

          <!-- Audit Status (visible to owner) -->
          <div v-if="isOwner && skill.status && skill.status !== 'approved'" class="audit-status-card" :class="skill.status">
            <div class="audit-icon">
              <span v-if="skill.status === 'pending'">⏳</span>
              <span v-else-if="skill.status === 'rejected'">❌</span>
              <span v-else>📴</span>
            </div>
            <div class="audit-info">
              <div class="audit-label">
                {{ skill.status === 'pending' ? '审核中' : skill.status === 'rejected' ? '审核未通过' : '已下架' }}
              </div>
              <div class="audit-desc" v-if="skill.status === 'pending'">商品正在审核中，审核通过后将自动上架</div>
              <div class="audit-desc" v-else-if="skill.status === 'rejected'">
                <span v-if="skill.reject_reason">原因：{{ skill.reject_reason }}</span>
                <span v-else>请修改后重新提交审核</span>
              </div>
            </div>
          </div>

          <hr class="divider" v-if="isOwner && skill.status && skill.status !== 'approved'" />

          <div class="system-req">
            <h3>商品信息</h3>
            <div class="req-item"><span>版本</span> <span>v{{ skill.version || '1.0.0' }}</span></div>
            <div class="req-item"><span>分类</span> <span>{{ skill.category_name || '未分类' }}</span></div>
            <div class="req-item"><span>下载</span> <span>{{ skill.download_count || 0 }} 次</span></div>
            <div class="req-item"><span>评分</span> <span>⭐ {{ skill.avg_rating || 0 }}</span></div>
          </div>
        </div>

        <!-- File Tree Panel -->
        <div class="file-tree-card glass-panel" v-if="fileTree.length > 0">
          <div class="file-tree-header">
            <h3>📂 商品包目录</h3>
            <span class="file-tree-count">{{ fileTreeFileCount }} 个文件</span>
          </div>
          <div class="file-tree-body">
            <div
              v-for="(node, idx) in flatFileTree"
              :key="idx"
              class="file-tree-node"
              :style="{ paddingLeft: (node.depth * 16 + 12) + 'px' }"
              :class="{ 'is-folder': node.is_dir }"
              @click="node.is_dir ? toggleTreeNode(node.path) : null"
            >
              <span class="file-tree-icon">
                <template v-if="node.is_dir">
                  <span v-if="expandedDirs.has(node.path)">📂</span>
                  <span v-else>📁</span>
                </template>
                <template v-else>
                  <span v-if="node.name.endsWith('.md')">📝</span>
                  <span v-else-if="node.name.endsWith('.js') || node.name.endsWith('.ts')">📜</span>
                  <span v-else-if="node.name.endsWith('.json')">📋</span>
                  <span v-else-if="node.name.endsWith('.py')">🐍</span>
                  <span v-else-if="node.name.match(/\.(png|jpg|jpeg|gif|svg|webp)$/i)">🖼️</span>
                  <span v-else-if="node.name.endsWith('.zip') || node.name.endsWith('.tar')">📦</span>
                  <span v-else>📄</span>
                </template>
              </span>
              <span class="file-tree-name">{{ node.name }}</span>
              <span class="file-tree-size" v-if="!node.is_dir && node.size">{{ formatFileSize(node.size) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>商品不存在或已下架</p>
    </div>

    <!-- Lightbox (zoomable & scrollable) -->
    <Teleport to="body">
      <Transition name="lightbox">
        <div v-if="lightboxVisible" class="lightbox-overlay" @click="lightboxVisible = false">
          <div class="lightbox-toolbar" @click.stop>
            <button class="lb-btn" @click="lbZoomOut" title="缩小">−</button>
            <span class="lb-zoom-label">{{ Math.round(lbScale * 100) }}%</span>
            <button class="lb-btn" @click="lbZoomIn" title="放大">+</button>
            <button class="lb-btn" @click="lbResetZoom" title="重置">1:1</button>
            <button class="lb-btn lb-close" @click="lightboxVisible = false" title="关闭">✕</button>
          </div>
          <div class="lightbox-scroll-area" ref="lbScrollArea" @click.self="lightboxVisible = false" @wheel="lbWheel">
            <img
              :src="(skill.screenshots || [])[lightboxIndex]"
              alt="效果图"
              class="lightbox-img"
              :style="{ width: lbScale === 1 ? '' : `${lbScale * 100}%`, maxWidth: lbScale > 1 ? 'none' : '' }"
              @click.stop
              draggable="false"
            />
          </div>
          <button class="lightbox-nav lightbox-prev" @click.stop="lightboxPrev" v-if="(skill.screenshots || []).length > 1">‹</button>
          <button class="lightbox-nav lightbox-next" @click.stop="lightboxNext" v-if="(skill.screenshots || []).length > 1">›</button>
          <div class="lightbox-counter" @click.stop>{{ lightboxIndex + 1 }} / {{ (skill.screenshots || []).length }}</div>
        </div>
      </Transition>
    </Teleport>

    <!-- User Profile Popup -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="profilePopupVisible" class="profile-popup-overlay" @click.self="profilePopupVisible = false">
          <div class="profile-popup glass-panel">
            <button class="profile-popup-close" @click="profilePopupVisible = false">✕</button>
            <div v-if="profileLoading" class="profile-popup-loading">
              <div class="loading-spinner"></div>
            </div>
            <template v-else-if="profilePopupData">
              <div class="profile-popup-header">
                <div class="profile-popup-avatar">
                  <img :src="profilePopupData.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${profilePopupData.id}`" alt="avatar" />
                </div>
                <div class="profile-popup-info">
                  <h3 class="profile-popup-name">{{ profilePopupData.nickname || '匿名用户' }}</h3>
                  <span class="profile-popup-badge admin-popup-badge" v-if="profilePopupData.role === 'admin'">🔧 管理员</span>
                  <span class="profile-popup-badge level-popup-badge" v-else-if="profilePopupData.level_info">{{ profilePopupData.level_info.icon }} {{ profilePopupData.level_info.name }}</span>
                  <span class="profile-popup-badge level-popup-badge" v-else>🦐 新手虾</span>
                </div>
              </div>
              <p class="profile-popup-bio">{{ profilePopupData.bio || '这只龙虾还没有签名' }}</p>
              <div class="profile-popup-stats">
                <div class="pp-stat">
                  <span class="pp-stat-val">{{ profilePopupData.skill_count || 0 }}</span>
                  <span class="pp-stat-label">商品</span>
                </div>
                <div class="pp-stat">
                  <span class="pp-stat-val">{{ profilePopupData.follower_count || 0 }}</span>
                  <span class="pp-stat-label">粉丝</span>
                </div>
                <div class="pp-stat">
                  <span class="pp-stat-val">{{ profilePopupData.total_downloads || 0 }}</span>
                  <span class="pp-stat-label">总下载</span>
                </div>
              </div>
              <div class="profile-popup-actions" v-if="userStore.isLoggedIn && profilePopupData.id !== userStore.user?.id">
                <button
                  class="btn btn-block profile-popup-btn"
                  :class="profileFollowed ? 'btn-glass' : 'btn-primary'"
                  @click="toggleFollow(profilePopupData.id)"
                  :disabled="followLoading"
                >
                  {{ followLoading ? '...' : (profileFollowed ? '✓ 已关注' : '+ 关注') }}
                </button>
              </div>
              <div class="profile-popup-meta">
                <span>加入于 {{ formatDateShort(profilePopupData.created_at) }}</span>
              </div>
              <button class="btn btn-primary btn-block profile-popup-btn" @click="goToProfile(profilePopupData.id)">查看完整主页</button>
            </template>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Level Info Modal -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="showLevelModal" class="level-modal-overlay" @click.self="showLevelModal = false">
          <div class="level-modal">
            <div class="level-modal-header">
              <h3>🏆 等级体系</h3>
              <button class="level-modal-close" @click="showLevelModal = false">✕</button>
            </div>
            <div class="level-list">
              <div v-for="lv in allLevels" :key="lv.level"
                class="level-row" :class="{ 'level-current': currentViewLevel.level === lv.level, 'level-locked': (currentViewLevel.exp || 0) < lv.min_exp }">
                <div class="level-icon-col">
                  <span class="level-icon">{{ lv.icon }}</span>
                  <div class="level-connector" v-if="lv.level < allLevels.length"></div>
                </div>
                <div class="level-info-col">
                  <div class="level-name-row">
                    <span class="level-name">{{ lv.name }}</span>
                    <span class="level-tag current-tag" v-if="currentViewLevel.level === lv.level">当前</span>
                    <span class="level-tag locked-tag" v-else-if="(currentViewLevel.exp || 0) < lv.min_exp">🔒</span>
                    <span class="level-tag done-tag" v-else>✓</span>
                  </div>
                  <div class="level-req">{{ lv.min_exp === 0 ? '初始等级' : lv.min_exp + ' 经验值' }}</div>
                </div>
              </div>
            </div>
            <div class="level-progress-section" v-if="currentViewLevel.next_level">
              <div class="level-progress-text">
                距离 {{ currentViewLevel.next_level.icon }} {{ currentViewLevel.next_level.name }} 还需 <strong>{{ currentViewLevel.next_level.min_exp - (currentViewLevel.exp || 0) }}</strong> 经验
              </div>
              <div class="level-progress-track">
                <div class="level-progress-fill" :style="{ width: levelProgressPct + '%' }"></div>
              </div>
              <div class="level-progress-nums">
                <span>{{ currentViewLevel.exp || 0 }}</span>
                <span>{{ currentViewLevel.next_level.min_exp }}</span>
              </div>
            </div>
            <div class="level-progress-section" v-else>
              <div class="level-progress-text max-lv">🎉 已达最高等级！经验 {{ currentViewLevel.exp || 0 }}</div>
            </div>
            <div class="exp-ways">
              <div class="exp-ways-title">经验获取方式</div>
              <div class="exp-way-grid">
                <div class="exp-way-item"><span class="exp-way-icon">📤</span><span>发布商品</span><span class="exp-way-val">+20</span></div>
                <div class="exp-way-item"><span class="exp-way-icon">📥</span><span>被下载</span><span class="exp-way-val">+2</span></div>
                <div class="exp-way-item"><span class="exp-way-icon">⭐</span><span>被收藏</span><span class="exp-way-val">+3</span></div>
                <div class="exp-way-item"><span class="exp-way-icon">💰</span><span>充值</span><span class="exp-way-val">+1/元</span></div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ── Cash payment QR / shipping modal ────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showCashModal" class="cash-overlay" @click.self="closeCashModal">
        <div class="cash-modal glass-panel">
          <button class="cash-close" @click="closeCashModal">✕</button>

          <!-- Step 1: 收货地址（仅实体商品） -->
          <template v-if="cashStep === 'address'">
            <h3>填写收货地址</h3>
            <div class="form-row"><label>收件人</label><input v-model="shippingForm.name" class="form-control" placeholder="真实姓名" /></div>
            <div class="form-row"><label>手机号</label><input v-model="shippingForm.phone" class="form-control" placeholder="11 位手机号" /></div>
            <div class="form-row"><label>详细地址</label><textarea v-model="shippingForm.address" class="form-control" rows="2" placeholder="省 / 市 / 区 / 街道 / 门牌"></textarea></div>
            <div class="form-row"><label>备注</label><input v-model="shippingForm.note" class="form-control" placeholder="选填" /></div>
            <button class="btn btn-primary btn-block" @click="confirmAddressAndPay" :disabled="purchasing">
              {{ purchasing ? '下单中…' : `确认并支付 ¥${cashPayableTotal}` }}
            </button>
          </template>

          <!-- Step 2: 二维码 -->
          <template v-else-if="cashStep === 'qr'">
            <h3>{{ cashMethod === 'wechat' ? '微信扫码支付' : '支付宝扫码支付' }}</h3>
            <p class="cash-amount">¥ {{ cashPayableTotal }}</p>
            <div class="cash-qr-wrap">
              <img v-if="cashQrUrl && cashQrUrl.startsWith('http')" :src="cashQrUrl" alt="支付二维码" />
              <div v-else class="qr-text">{{ cashQrUrl || '二维码生成中…' }}</div>
            </div>
            <p class="cash-hint">{{ cashStatusText }}</p>
            <button class="btn btn-glass btn-block" @click="closeCashModal">取消支付</button>
          </template>

          <!-- Step 3: 完成 -->
          <template v-else-if="cashStep === 'done'">
            <div class="cash-done-icon">✅</div>
            <h3>{{ skill?.product_type === 'physical' ? '下单成功' : '支付成功' }}</h3>
            <p class="cash-hint">{{ skill?.product_type === 'physical' ? '商家将尽快为您发货，物流信息可在「我的 → 已购」查看。' : '您可以在下方下载商品包。' }}</p>
            <button class="btn btn-primary btn-block" @click="closeCashModal">好的</button>
          </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { getSkillDetail, getSkillReviews, createReview, getCaptcha, deleteReview } from '../api/skill.js'
import { purchaseSkill, checkPurchase, downloadSkill } from '../api/points.js'
import { addFavorite, removeFavorite } from '../api/social.js'
import { getUserProfile, followUser, unfollowUser, checkFollow } from '../api/user.js'
import { userStore } from '../stores/user.js'
import { KV_SYNC_HINT } from '../composables/useToast.js'
import { formatDateShort } from '../utils.js'
import { getLevelInfo, getActiveLevels } from '../utils/levels.js'
import { get, post } from '../api/request.js'

const route = useRoute()
const router = useRouter()

const skill = ref(null)
const loading = ref(true)
const activeTab = ref('intro')
const versions = ref([])
const reviews = ref([])
const reviewsLoading = ref(false)
const purchased = ref(false)
const isFavorited = ref(false)
const purchasing = ref(false)
const favoriting = ref(false)
const downloading = ref(false)
const submittingReview = ref(false)
const actionMsg = ref('')
const actionMsgType = ref('success')
const installMethod = ref('dialog')

const siteOrigin = window.location.origin

// Lightbox
const lightboxVisible = ref(false)
const lightboxIndex = ref(0)
const lbScale = ref(1)
const lbScrollArea = ref(null)

const newReview = reactive({ rating: 5, content: '' })
const captcha = reactive({ image: '', token: '', answer: '', loading: false })
const REVIEW_MAX_LENGTH = 300

// Profile Popup
const profilePopupVisible = ref(false)
const profilePopupData = ref(null)
const profileLoading = ref(false)
const profileFollowed = ref(false)
const followLoading = ref(false)

// Level Modal
const showLevelModal = ref(false)
const allLevels = computed(() => getActiveLevels())
const currentViewLevel = computed(() => {
  const info = skill.value?.author_level_info
  if (info && info.name) return info
  return getLevelInfo(skill.value?.author_exp || 0)
})
const levelProgressPct = computed(() => {
  const lv = currentViewLevel.value
  if (!lv.next_level) return 100
  const lvs = allLevels.value
  const prev = lvs.find(l => l.level === lv.level)
  const prevExp = prev ? prev.min_exp : 0
  const range = lv.next_level.min_exp - prevExp
  if (range <= 0) return 100
  return Math.min(100, Math.round(((lv.exp || 0) - prevExp) / range * 100))
})

// File Tree
const fileTree = ref([])
const expandedDirs = ref(new Set())

const fileTreeFileCount = computed(() => {
  let count = 0
  const countFiles = (nodes) => {
    for (const n of nodes) {
      if (n.is_dir) countFiles(n.children || [])
      else count++
    }
  }
  countFiles(fileTree.value)
  return count
})

const flatFileTree = computed(() => {
  const result = []
  const walk = (nodes, depth) => {
    for (const n of nodes) {
      result.push({ ...n, depth })
      if (n.is_dir && expandedDirs.value.has(n.path)) {
        walk(n.children || [], depth + 1)
      }
    }
  }
  walk(fileTree.value, 0)
  return result
})

const toggleTreeNode = (path) => {
  const s = new Set(expandedDirs.value)
  if (s.has(path)) s.delete(path)
  else s.add(path)
  expandedDirs.value = s
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const buildTree = (flatList) => {
  // Convert flat ZIP entries (name like "dir/sub/file.txt") into a nested tree
  const root = []
  const dirMap = {}

  // Sort so directories come before their children
  const sorted = [...flatList].sort((a, b) => a.name.localeCompare(b.name))

  for (const entry of sorted) {
    const parts = entry.name.split('/')
    const baseName = parts[parts.length - 1] || parts[parts.length - 2] || entry.name
    const node = {
      name: baseName,
      path: entry.name,
      is_dir: entry.is_dir,
      size: entry.size || 0,
      children: entry.is_dir ? [] : undefined,
    }

    if (parts.length <= 1 || (parts.length === 2 && entry.is_dir)) {
      // Root level
      root.push(node)
      if (entry.is_dir) dirMap[entry.name.replace(/\/$/, '')] = node
    } else {
      // Find parent dir
      const parentPath = parts.slice(0, -1).join('/')
      const parent = dirMap[parentPath] || dirMap[parentPath.replace(/\/$/, '')]
      if (parent && parent.children) {
        parent.children.push(node)
      } else {
        root.push(node)
      }
      if (entry.is_dir) dirMap[entry.name.replace(/\/$/, '')] = node
    }
  }
  return root
}

const loadFileTree = async () => {
  try {
    const res = await get(`/skills/${route.params.id}/file-tree`)
    const flat = (res.code === 0 && res.data) ? res.data : []
    if (flat.length > 0) {
      const tree = buildTree(flat)
      fileTree.value = tree
      // Auto-expand root level dirs
      const rootDirs = tree.filter(n => n.is_dir).map(n => n.path)
      expandedDirs.value = new Set(rootDirs)
    }
  } catch (e) { /* ignore - API may not support file-tree yet */ }
}

// User Profile Popup
const openAuthorProfile = () => {
  if (skill.value?.author_id) {
    openUserProfile(skill.value.author_id)
  }
}

const openUserProfile = async (userId) => {
  if (!userId) return
  profilePopupVisible.value = true
  profileLoading.value = true
  profilePopupData.value = null
  profileFollowed.value = false
  try {
    const res = await getUserProfile(userId)
    if (res.code === 0) {
      profilePopupData.value = res.data
    }
    // Check follow status
    if (userStore.isLoggedIn && userId !== userStore.user?.id) {
      try {
        const fRes = await checkFollow(userId)
        if (fRes.code === 0) profileFollowed.value = !!fRes.data?.followed
      } catch (e) { /* ignore */ }
    }
  } catch (e) {
    console.error('Failed to load profile:', e)
  } finally {
    profileLoading.value = false
  }
}

const toggleFollow = async (userId) => {
  if (!userStore.isLoggedIn) return
  followLoading.value = true
  try {
    if (profileFollowed.value) {
      const res = await unfollowUser(userId)
      if (res.code === 0) {
        profileFollowed.value = false
        if (profilePopupData.value) {
          profilePopupData.value.follower_count = Math.max(0, (profilePopupData.value.follower_count || 1) - 1)
        }
      }
    } else {
      const res = await followUser(userId)
      if (res.code === 0) {
        profileFollowed.value = true
        if (profilePopupData.value) {
          profilePopupData.value.follower_count = (profilePopupData.value.follower_count || 0) + 1
        }
      }
    }
  } catch (e) {
    console.error('Follow toggle failed:', e)
  } finally {
    followLoading.value = false
  }
}

const goToProfile = (userId) => {
  profilePopupVisible.value = false
  router.push(`/user/${userId}`)
}

const isFreeSkill = computed(() => {
  if (!skill.value) return false
  const mode = skill.value.sale_mode || 'points'
  const pointsPrice = Number(skill.value.price || 0)
  const cashPrice = Number(skill.value.cash_price_yuan || 0)
  if (mode === 'cash') return cashPrice <= 0
  if (mode === 'both') return pointsPrice <= 0 && cashPrice <= 0
  return !!skill.value.is_free || pointsPrice <= 0
})

// ── Cash payment / shipping state ───────────────────────────────────────
const chosenMode = ref('points')          // for sale_mode === 'both' switch
const cashMethod = ref('wechat')          // 'wechat' | 'alipay'
const showCashModal = ref(false)
const cashStep = ref('qr')                // 'address' | 'qr' | 'done'
const cashOrderNo = ref('')
const cashQrUrl = ref('')
const cashStatusText = ref('请扫码支付')
let cashPollTimer = null
const shippingForm = reactive({ name: '', phone: '', address: '', note: '' })

const effectiveSaleMode = computed(() => {
  if (!skill.value) return 'points'
  if (skill.value.sale_mode === 'both') return chosenMode.value
  return skill.value.sale_mode || 'points'
})

const cashPayableTotal = computed(() => {
  if (!skill.value) return 0
  const unit = Number(skill.value.cash_price_yuan) || 0
  const ship = (skill.value.product_type === 'physical') ? (Number(skill.value.shipping_fee_yuan) || 0) : 0
  return (unit + ship).toFixed(2)
})

function closeCashModal() {
  showCashModal.value = false
  if (cashPollTimer) { clearInterval(cashPollTimer); cashPollTimer = null }
}

async function handleCashPurchase() {
  if (!userStore.isLoggedIn) { showMsg('请先登录', 'error'); return }
  if (skill.value?.product_type === 'physical') {
    cashStep.value = 'address'
    showCashModal.value = true
    return
  }
  await placeCashOrder(null)
}

async function confirmAddressAndPay() {
  if (!shippingForm.name || !shippingForm.phone || !shippingForm.address) {
    showMsg('请填写完整收货信息', 'error')
    return
  }
  await placeCashOrder({ ...shippingForm })
}

async function placeCashOrder(shippingInfo) {
  purchasing.value = true
  try {
    const res = await post('/purchases/cash/order', {
      skill_id: route.params.id,
      payment_method: cashMethod.value,
      shipping_info: shippingInfo,
      quantity: 1,
      client_type: '',
    })
    if (res.code !== 0) { showMsg(res.message || '下单失败', 'error'); return }
    cashOrderNo.value = res.data.order_no
    cashQrUrl.value = res.data.qr_url || ''
    cashStep.value = 'qr'
    showCashModal.value = true
    cashStatusText.value = cashMethod.value === 'wechat' ? '请使用微信扫码支付' : '请使用支付宝扫码支付'
    // Poll status every 3s for up to 5 minutes
    let polls = 0
    cashPollTimer = setInterval(async () => {
      polls++
      try {
        const s = await get(`/purchases/cash/${cashOrderNo.value}/status`)
        if (s.code === 0 && (s.data.status === 'paid' || s.data.status === 'paid_unverified')) {
          cashStep.value = 'done'
          clearInterval(cashPollTimer); cashPollTimer = null
          purchased.value = true
        }
      } catch (e) { /* ignore */ }
      if (polls > 100) { clearInterval(cashPollTimer); cashPollTimer = null; cashStatusText.value = '支付超时，请关闭后重试' }
    }, 3000)
  } catch (e) {
    showMsg(e?.message || '下单失败', 'error')
  } finally {
    purchasing.value = false
  }
}

const isOwner = computed(() => userStore.isLoggedIn && skill.value && userStore.user?.id === skill.value.author_id)

const hasScreenshots = computed(() => (skill.value?.screenshots || []).length > 0)

const renderedDesc = computed(() => {
  let text = skill.value?.description || ''
  
  // Auto-detect video links on their own line before markdown parsing
  // Bilibili: https://www.bilibili.com/video/BVxxxxxxx
  text = text.replace(
    /^(https?:\/\/(?:www\.)?bilibili\.com\/video\/(BV[a-zA-Z0-9]+)[^\s]*)$/gm,
    '\n\n<div class="video-embed"><iframe src="https://player.bilibili.com/player.html?bvid=$2&autoplay=0&high_quality=1&danmaku=0" scrolling="no" frameborder="no" allowfullscreen="true"></iframe></div>\n\n'
  )
  // YouTube: https://www.youtube.com/watch?v=xxx or https://youtu.be/xxx
  text = text.replace(
    /^https?:\/\/(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)[^\s]*$/gm,
    '\n\n<div class="video-embed"><iframe src="https://www.youtube.com/embed/$1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>\n\n'
  )
  text = text.replace(
    /^https?:\/\/youtu\.be\/([a-zA-Z0-9_-]+)[^\s]*$/gm,
    '\n\n<div class="video-embed"><iframe src="https://www.youtube.com/embed/$1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>\n\n'
  )
  
  const html = marked.parse(text)
  const clean = DOMPurify.sanitize(html, { ADD_TAGS: ['iframe'], ADD_ATTR: ['allow', 'allowfullscreen', 'frameborder', 'scrolling', 'src'] })
  // Wrap <table> in scrollable container for responsive layout
  return clean.replace(/<table>/g, '<div class="table-wrapper"><table>').replace(/<\/table>/g, '</table></div>')
})

const showMsg = (msg, type = 'success') => {
  actionMsg.value = msg
  actionMsgType.value = type
  setTimeout(() => { actionMsg.value = '' }, 3000)
}

const openLightbox = (idx) => {
  lightboxIndex.value = idx
  lbScale.value = 1
  lightboxVisible.value = true
}

const lightboxPrev = () => {
  const len = (skill.value?.screenshots || []).length
  lightboxIndex.value = (lightboxIndex.value - 1 + len) % len
  lbScale.value = 1
}

const lightboxNext = () => {
  const len = (skill.value?.screenshots || []).length
  lightboxIndex.value = (lightboxIndex.value + 1) % len
  lbScale.value = 1
}

const lbZoomIn = () => { lbScale.value = Math.min(lbScale.value + 0.25, 5) }
const lbZoomOut = () => { lbScale.value = Math.max(lbScale.value - 0.25, 0.25) }
const lbResetZoom = () => { lbScale.value = 1 }
const lbWheel = (e) => {
  if (e.ctrlKey || e.metaKey) {
    // Ctrl+wheel = zoom, prevent page zoom
    e.preventDefault()
    if (e.deltaY < 0) lbZoomIn()
    else lbZoomOut()
  }
  // Normal scroll passes through natively to the scroll area
}

const loadSkill = async () => {
  loading.value = true
  const id = route.params.id
  try {
    const res = await getSkillDetail(id)
    if (res.code === 0) {
      skill.value = res.data
      versions.value = res.data?.versions || []
    }
  } catch (e) {
    console.error('Failed to load skill:', e)
  } finally {
    loading.value = false
  }
}

const checkPurchaseStatus = async () => {
  if (!userStore.isLoggedIn) return
  try {
    const res = await checkPurchase(route.params.id)
    if (res.code === 0) {
      purchased.value = res.data?.purchased || false
    }
  } catch (e) { /* ignore */ }
}

const checkFavoriteStatus = async () => {
  if (!userStore.isLoggedIn) return
  try {
    const res = await get(`/favorites/${route.params.id}/check`)
    if (res.code === 0) isFavorited.value = !!res.data?.favorited
  } catch (e) { /* ignore */ }
}

const loadReviews = async () => {
  reviewsLoading.value = true
  try {
    const res = await getSkillReviews(route.params.id, { page: 1, page_size: 20 })
    if (res.code === 0) {
      reviews.value = res.data?.items || []
    }
  } catch (e) {
    console.error('Failed to load reviews:', e)
  } finally {
    reviewsLoading.value = false
  }
}

const handlePurchase = async () => {
  if (!userStore.isLoggedIn) {
    showMsg('请先登录', 'error')
    return
  }
  purchasing.value = true
  try {
    const res = await purchaseSkill(route.params.id)
    if (res.code === 0) {
      purchased.value = true
      showMsg('购买成功！' + KV_SYNC_HINT)
      if (res.data?.points_balance !== undefined) {
        userStore.updateUser({ points_balance: res.data.points_balance })
      }
    } else {
      showMsg(res.message || '购买失败', 'error')
    }
  } catch (e) {
    showMsg('网络错误', 'error')
  } finally {
    purchasing.value = false
  }
}

const handleInstallTabClick = () => {
  if (!purchased.value && !isOwner.value && !isFreeSkill.value) {
    showMsg('请先购买后再查看安装方式', 'error')
    return
  }
  activeTab.value = 'install'
}

const handleDownload = async () => {
  if (!userStore.isLoggedIn) {
    showMsg('请先登录去购买或下载', 'error')
    return
  }
  if (downloading.value) return
  downloading.value = true

  activeTab.value = 'install'
  installMethod.value = 'zip'
  // 直接通过 API 端点下载文件
  try {
    const token = localStorage.getItem('EdgeOneMall_token')
    const a = document.createElement('a')
    a.href = `/api/v1/purchases/${skill.value.id}/download/file`
    // 通过隐藏 form 提交来携带 auth（避免 token 泄露在 URL 中）
    const form = document.createElement('form')
    form.method = 'GET'
    form.action = `/api/v1/purchases/${skill.value.id}/download/file`
    form.target = '_blank'
    form.style.display = 'none'
    document.body.appendChild(form)

    // 使用 fetch 下载并触发浏览器保存
    const res = await fetch(`/api/v1/purchases/${skill.value.id}/download/file`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      showMsg(err.message || '下载失败', 'error')
      document.body.removeChild(form)
      return
    }
    const blob = await res.blob()
    const disposition = res.headers.get('Content-Disposition') || ''
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/)
    const filename = filenameMatch ? filenameMatch[1] : `${skill.value.title || 'skill'}.zip`

    const url = URL.createObjectURL(blob)
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    document.body.removeChild(form)
    showMsg('开始下载...', 'success')
  } catch (e) {
    showMsg('网络错误', 'error')
  } finally {
    downloading.value = false
  }
}

const handleFavorite = async () => {
  if (!userStore.isLoggedIn) {
    showMsg('请先登录', 'error')
    return
  }
  if (favoriting.value) return
  favoriting.value = true
  // 乐观更新：立即切换状态，请求失败时回滚
  const prev = isFavorited.value
  isFavorited.value = !prev
  try {
    if (prev) {
      const res = await removeFavorite(route.params.id)
      if (res.code === 0) {
        showMsg('已取消收藏。' + KV_SYNC_HINT)
      } else {
        isFavorited.value = prev // 回滚
        showMsg(res.message || '操作失败', 'error')
      }
    } else {
      const res = await addFavorite(route.params.id)
      if (res.code === 0) {
        showMsg('收藏成功。' + KV_SYNC_HINT)
      } else {
        isFavorited.value = prev // 回滚
        showMsg(res.message || '操作失败', 'error')
      }
    }
  } catch (e) {
    isFavorited.value = prev // 回滚
    showMsg('操作失败', 'error')
  } finally {
    favoriting.value = false
  }
}

const refreshCaptcha = async () => {
  captcha.loading = true
  try {
    const res = await getCaptcha()
    if (res.code === 0) {
      captcha.image = res.data.image
      captcha.token = res.data.token
      captcha.answer = ''
    }
  } catch (e) {
    console.error('Failed to load captcha:', e)
  } finally {
    captcha.loading = false
  }
}

const submitReview = async () => {
  if (!newReview.content.trim()) {
    showMsg('请填写评价内容', 'error')
    return
  }
  if (newReview.content.length > REVIEW_MAX_LENGTH) {
    showMsg(`评价内容不能超过 ${REVIEW_MAX_LENGTH} 字`, 'error')
    return
  }
  if (!captcha.answer) {
    showMsg('请输入验证码答案', 'error')
    return
  }
  submittingReview.value = true
  try {
    const res = await createReview(route.params.id, {
      rating: newReview.rating,
      content: newReview.content,
      captcha_token: captcha.token,
      captcha_answer: parseInt(captcha.answer),
    })
    if (res.code === 0) {
      // 乐观更新：立即插入到评论列表头部
      const tempReview = {
        id: res.data?.id || Date.now(),
        rating: newReview.rating,
        content: newReview.content,
        user_id: userStore.user?.id,
        user_nickname: userStore.user?.nickname || '我',
        user_avatar: userStore.user?.avatar_url,
        user_role: userStore.user?.role || 'user',
        user_level_info: null,
        created_at: new Date().toISOString(),
      }
      reviews.value.unshift(tempReview)
      if (skill.value) {
        skill.value.review_count = (skill.value.review_count || 0) + 1
      }
      newReview.content = ''
      newReview.rating = 5
      showMsg('评价成功')
    } else {
      showMsg(res.message || '评价失败', 'error')
    }
    // 无论成功失败都刷新验证码
    refreshCaptcha()
  } catch (e) {
    showMsg('网络错误', 'error')
  } finally {
    submittingReview.value = false
  }
}

const handleDeleteReview = async (review) => {
  if (!confirm('确定要删除这条评价？')) return
  try {
    const res = await deleteReview(review.id)
    if (res.code === 0) {
      reviews.value = reviews.value.filter(r => r.id !== review.id)
      if (skill.value) {
        skill.value.review_count = Math.max(0, (skill.value.review_count || 0) - 1)
      }
      showMsg('评价已删除')
    } else {
      showMsg(res.message || '删除失败', 'error')
    }
  } catch (e) {
    showMsg('网络错误', 'error')
  }
}

onMounted(() => {
  loadSkill()
  checkPurchaseStatus()
  checkFavoriteStatus()
  loadFileTree()
  refreshCaptcha()
})
</script>

<style scoped>
.skill-detail {
  padding: 40px 24px 100px;
  max-width: 1200px;
  margin: 0 auto;
  box-sizing: border-box;
}

.btn-back { margin-bottom: 24px; }

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 28px;
  align-items: start;
  min-width: 0;
}

/* Left Column */
.main-col { min-width: 0; }
.header-glass { padding: 0; overflow: hidden; margin-bottom: 24px; }

.header-info { padding: 32px; }

.tags { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }

.tag-category {
  background: var(--color-primary);
  color: white;
  padding: 4px 12px;
  border-radius: 99px;
  font-size: 13px;
  font-weight: 600;
}

.tag {
  background: rgba(255,255,255,0.1);
  padding: 4px 12px;
  border-radius: 99px;
  font-size: 13px;
}

.title { font-size: 32px; font-weight: 800; margin-bottom: 12px; }

.subtitle { font-size: 16px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 24px; }

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid var(--border-glass);
  padding-top: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.author { display: flex; align-items: flex-start; gap: 16px; font-weight: 500; }

.author-avatar-wrap {
  cursor: pointer;
  flex-shrink: 0;
}

.author-avatar-wrap img {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 2px solid var(--border-glass);
  transition: border-color 0.2s;
  display: block;
}

.author-avatar-wrap:hover img {
  border-color: var(--color-primary);
}

.author-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.author-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.author-name-link {
  cursor: pointer;
  transition: color 0.2s;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.author-name-link:hover {
  color: var(--color-primary);
}

.publish-date { 
  color: var(--text-tertiary); 
  font-size: 13px; 
  font-weight: 400; 
}

.stats { display: flex; gap: 16px; color: var(--text-secondary); font-size: 14px; flex-wrap: wrap; }

/* Tabs */
.content-tabs { padding: 0; }

.tab-scroller { display: flex; border-bottom: 1px solid var(--border-glass); padding: 0 16px; overflow-x: auto; }

.tab {
  padding: 20px 24px;
  cursor: pointer;
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 2px solid transparent;
  transition: var(--transition-smooth);
  white-space: nowrap;
}

.tab:hover { color: var(--text-primary); }
.tab.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }
.tab.locked { opacity: 0.5; cursor: not-allowed; }

.tab-content { padding: 32px; overflow-x: hidden; }

/* Screenshots */
.screenshots-section { padding: 0; }

.screenshots-grid {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.screenshot-card {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-glass);
  cursor: pointer;
  transition: all 0.2s;
  max-width: 720px;
  width: 100%;
}

.screenshot-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.screenshot-card img {
  width: 100%;
  display: block;
}

/* Installation empty state */
.empty-install {
  text-align: center;
  padding: 48px 20px;
}
.empty-install .empty-icon { font-size: 48px; display: block; margin-bottom: 16px; }
.empty-install p { color: var(--text-secondary); font-size: 16px; margin-bottom: 8px; }
.empty-install .empty-sub { color: var(--text-tertiary); font-size: 14px; }

/* Install Lock Prompt */
.install-lock-prompt {
  text-align: center;
  padding: 60px 20px;
}

.install-lock-prompt .lock-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.install-lock-prompt h3 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.install-lock-prompt p {
  color: var(--text-secondary);
  font-size: 15px;
  margin-bottom: 24px;
  line-height: 1.6;
}

/* Install Guide */
.install-guide-content { color: var(--text-secondary); }

.install-tabs {
  display: flex; gap: 8px; margin-bottom: 20px;
}
.install-tabs button {
  padding: 8px 20px; border-radius: 8px;
  background: rgba(255,255,255,0.05); border: 1px solid var(--border-glass);
  color: var(--text-secondary); cursor: pointer; font-size: 14px;
  transition: var(--transition-smooth);
}
.install-tabs button.active {
  background: var(--color-primary); color: white; border-color: var(--color-primary);
}
.install-tabs button:hover:not(.active) { background: rgba(255,255,255,0.1); color: var(--text-primary); }

.install-hint {
  font-size: 14px; color: var(--text-tertiary); line-height: 1.6; margin-bottom: 24px;
}

.install-section {
  margin-bottom: 24px;
}
.install-section h3 {
  font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px;
}
.install-block {
  background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass);
  border-radius: 10px; padding: 16px 20px; line-height: 1.8; font-size: 14px;
}
.install-block p { margin-bottom: 8px; color: var(--text-secondary); }
.install-block p:last-child { margin-bottom: 0; }
.install-block strong { color: var(--text-primary); }
.install-block code {
  background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px;
  font-family: 'Fira Code', monospace; font-size: 12px; color: #a6e22e;
}
.code-block {
  background: rgba(0,0,0,0.4); border: 1px solid var(--border-glass);
  border-radius: 8px; padding: 14px 16px; margin-top: 12px;
  cursor: pointer; transition: var(--transition-smooth);
}
.code-block:hover { background: rgba(0,0,0,0.5); }
.code-block code {
  font-family: 'Fira Code', monospace; font-size: 13px; line-height: 1.7;
  color: #e6db74; word-break: break-all; white-space: pre-wrap;
}

/* Reviews */
.review-form { margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid var(--border-glass); }
.review-form h3 { font-size: 16px; margin-bottom: 12px; }

.star-picker { margin-bottom: 12px; }
.star-picker .star { cursor: pointer; font-size: 20px; opacity: 0.3; transition: opacity 0.2s; }
.star-picker .star.active { opacity: 1; }

.review-textarea {
  width: 100%;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 12px;
  color: var(--text-primary);
  font-family: inherit;
  resize: vertical;
  outline: none;
  margin-bottom: 12px;
}

.review-textarea:focus { border-color: var(--color-primary); }

.reviews-list { display: flex; flex-direction: column; gap: 20px; }

.review-item {
  padding: 16px;
  border: 1px solid var(--border-glass);
  border-radius: 12px;
}

/* Review item layout */
.review-item {
  display: flex;
  gap: 14px;
  padding: 20px 10px;
  border-bottom: 1px solid var(--border-glass);
  align-items: flex-start;
}
.review-item:last-child { border-bottom: none; }

.review-item > .review-avatar-wrap {
  flex-shrink: 0;
  cursor: pointer;
}

.review-item > .review-avatar-wrap img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid var(--border-glass);
  transition: border-color 0.2s;
  display: block;
}

.review-item > .review-avatar-wrap:hover img {
  border-color: var(--color-primary);
}

.review-body {
  flex: 1;
  min-width: 0;
}

.review-top-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 2px;
}

.review-name {
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  color: var(--text-primary);
  transition: color 0.2s;
}
.review-name:hover { color: var(--color-primary); }

.review-lv {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(30, 224, 127, 0.12);
  color: var(--color-primary);
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.review-lv.admin-lv {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
}

.review-stars {
  margin-left: auto;
  font-size: 13px;
  flex-shrink: 0;
  white-space: nowrap;
}

.review-date {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}

.review-text {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

.btn-review-delete {
  background: none;
  border: none;
  color: var(--text-tertiary);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 0;
  margin-top: 4px;
  transition: color 0.2s;
}
.btn-review-delete:hover {
  color: #ef4444;
}

/* Textarea char count */
.textarea-wrap {
  position: relative;
  width: 100%;
}
.char-count {
  position: absolute;
  bottom: 8px;
  right: 10px;
  font-size: 11px;
  color: var(--text-tertiary);
  pointer-events: none;
}
.char-count.warn {
  color: #ef4444;
}

/* Captcha */
.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0;
}
.captcha-image {
  height: 40px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid var(--border-glass);
  user-select: none;
  -webkit-user-drag: none;
}
.captcha-input {
  width: 80px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-glass);
  background: var(--bg-glass);
  color: var(--text-primary);
  font-size: 14px;
  text-align: center;
}
.captcha-input:focus {
  outline: none;
  border-color: var(--color-primary);
}
.captcha-refresh {
  font-size: 18px;
  padding: 4px 10px;
  line-height: 1;
}

/* Sidebar */
.sticky-sidebar {
  position: sticky;
  top: 96px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
  /* hide scrollbar */
  scrollbar-width: none;
}
.sticky-sidebar::-webkit-scrollbar { display: none; }
.purchase-card { padding: 32px; }

.price-display { display: flex; align-items: baseline; gap: 8px; margin-bottom: 24px; }
.price-display .amount { font-size: 48px; font-weight: 800; color: var(--color-accent); line-height: 1; }
.price-display .coin { font-size: 18px; color: var(--text-secondary); }

.action-buttons { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }
.btn-block { width: 100%; padding: 14px; }
.text-lg { font-size: 16px; }

.msg-box {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 16px;
  text-align: center;
}
.msg-box.success { background: rgba(52, 199, 89, 0.1); color: #34C759; border: 1px solid rgba(52, 199, 89, 0.2); }
.msg-box.error { background: rgba(255, 69, 58, 0.1); color: #FF453A; border: 1px solid rgba(255, 69, 58, 0.2); }

.guarantee-list { display: flex; flex-direction: column; gap: 12px; }
.g-item { display: flex; gap: 12px; font-size: 14px; color: var(--text-secondary); }
.g-item.warning { color: #FF9F0A; }

.divider { border: none; border-top: 1px solid var(--border-glass); margin: 24px 0; }

/* Audit Status Card */
.audit-status-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid var(--border-glass);
}

.audit-status-card.pending {
  background: rgba(255, 149, 0, 0.08);
  border-color: rgba(255, 149, 0, 0.2);
}

.audit-status-card.rejected {
  background: rgba(255, 69, 58, 0.08);
  border-color: rgba(255, 69, 58, 0.2);
}

.audit-status-card.offline {
  background: rgba(255, 255, 255, 0.03);
}

.audit-icon { font-size: 24px; flex-shrink: 0; }
.audit-info { flex: 1; }
.audit-label { font-weight: 600; font-size: 14px; color: var(--text-primary); margin-bottom: 2px; }
.audit-desc { font-size: 12px; color: var(--text-tertiary); }

.system-req h3 { font-size: 14px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }
.req-item { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 14px; }
.req-item span:first-child { color: var(--text-secondary); }
.req-item span:last-child { color: var(--text-primary); font-weight: 500; text-align: right; }

/* Lightbox */
.lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.92);
  backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  z-index: 10000;
}

/* Toolbar */
.lightbox-toolbar {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(30, 30, 30, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  padding: 4px 8px;
  z-index: 10;
  backdrop-filter: blur(12px);
}
.lb-btn {
  background: transparent;
  border: none;
  color: rgba(255,255,255,0.8);
  width: 32px;
  height: 32px;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}
.lb-btn:hover { background: rgba(255,255,255,0.15); color: white; }
.lb-close { margin-left: 8px; }
.lb-zoom-label {
  font-size: 12px;
  color: rgba(255,255,255,0.6);
  min-width: 40px;
  text-align: center;
  user-select: none;
}

/* Scrollable image area */
.lightbox-scroll-area {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 64px 60px 48px;
}

.lightbox-img {
  max-width: min(90vw, 900px);
  width: auto;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  transition: width 0.15s ease;
  flex-shrink: 0;
  display: block;
}

/* Nav buttons */
.lightbox-nav {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 10;
}
.lightbox-nav:hover { background: rgba(255, 255, 255, 0.2); }
.lightbox-prev { left: 16px; }
.lightbox-next { right: 16px; }

.lightbox-counter {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  color: var(--text-tertiary);
  font-size: 14px;
  z-index: 10;
  user-select: none;
}

.lightbox-enter-active,
.lightbox-leave-active {
  transition: opacity 0.2s;
}
.lightbox-enter-from,
.lightbox-leave-to {
  opacity: 0;
}

/* Loading & Empty */
.loading-state, .empty-state { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
.loading-spinner {
  width: 40px; height: 40px;
  border: 3px solid var(--border-glass); border-top-color: var(--color-primary);
  border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 992px) {
  .detail-grid { grid-template-columns: 1fr; }
  .screenshots-grid { max-width: 100%; }
}

@media (max-width: 600px) {
  .skill-detail { padding-top: 16px; }
  .header-glass { padding: 16px; }
  .title { font-size: 22px; }
  .subtitle { font-size: 14px; }
  .meta-row { flex-direction: column; gap: 8px; }
  .stats { font-size: 12px; gap: 10px; }
  .content-tabs { padding: 12px; }
  .tab-scroller { gap: 8px; padding-bottom: 8px; }
  .tab { font-size: 13px; padding: 8px 12px; white-space: nowrap; }
  .price-display .amount { font-size: 32px; }
  .sidebar-card { padding: 16px; }
  .btn-block { font-size: 14px; padding: 12px; }
  .lightbox-scroll-area { padding: 48px 12px 32px; }
}

/* ============ File Tree ============ */
.file-tree-card {
  padding: 0;
  margin-top: 20px;
  overflow: hidden;
}

.file-tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-glass);
}

.file-tree-header h3 {
  font-size: 14px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
}

.file-tree-count {
  font-size: 12px;
  color: var(--text-tertiary);
  background: rgba(255,255,255,0.06);
  padding: 2px 10px;
  border-radius: 99px;
}

.file-tree-body {
  max-height: 400px;
  overflow-y: auto;
  padding: 8px 0;
}

.file-tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  font-size: 13px;
  color: var(--text-secondary);
  transition: background 0.15s;
  user-select: none;
}

.file-tree-node:hover {
  background: rgba(255,255,255,0.04);
}

.file-tree-node.is-folder {
  cursor: pointer;
  color: var(--text-primary);
  font-weight: 500;
}

.file-tree-icon {
  font-size: 14px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.file-tree-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-tree-size {
  font-size: 11px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

/* ============ Profile Popup ============ */
.profile-popup-overlay {
  position: fixed;
  inset: 0;
  z-index: 10001;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.profile-popup {
  width: 380px;
  max-width: 92vw;
  padding: 28px;
  border-radius: 20px;
  position: relative;
  background: rgba(22, 22, 28, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5);
}

.profile-popup-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-tertiary);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.profile-popup-close:hover {
  background: rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
}

.profile-popup-loading {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.profile-popup-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.profile-popup-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  border: 3px solid var(--border-glass);
}

.profile-popup-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-popup-info {
  flex: 1;
  min-width: 0;
}

.profile-popup-name {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 6px 0;
  color: var(--text-primary);
}

.profile-popup-badge {
  display: inline-block;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 8px;
  font-weight: 600;
}

.level-popup-badge {
  background: linear-gradient(135deg, rgba(30, 224, 127, 0.15), rgba(0, 240, 255, 0.1));
  color: var(--color-primary);
}

.admin-popup-badge {
  background: linear-gradient(135deg, rgba(88, 86, 214, 0.2), rgba(175, 82, 222, 0.15));
  color: #c084fc;
}

.profile-popup-bio {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0 0 16px 0;
}

.profile-popup-stats {
  display: flex;
  gap: 0;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 14px 0;
  margin-bottom: 16px;
}

.pp-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.pp-stat + .pp-stat {
  border-left: 1px solid var(--border-glass);
}

.pp-stat-val {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.pp-stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.profile-popup-meta {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 16px;
  text-align: center;
}

.profile-popup-actions {
  margin-bottom: 12px;
}

.profile-popup-actions .btn-glass {
  border: 1px solid var(--border-glass);
  color: var(--text-secondary);
}

.profile-popup-actions .btn-glass:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
}

.profile-popup-btn {
  margin-top: 4px;
}

/* ============ Level Modal ============ */
.level-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 10002;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.level-modal {
  width: 440px;
  max-width: 92vw;
  max-height: 85vh;
  overflow-y: auto;
  padding: 28px;
  border-radius: 20px;
  background: rgba(22, 22, 28, 0.97);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5);
}

.level-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.level-modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
}

.level-modal-close {
  background: rgba(255, 255, 255, 0.08);
  border: none;
  color: var(--text-secondary);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.level-modal-close:hover { background: rgba(255, 255, 255, 0.15); }

.level-list {
  display: flex;
  flex-direction: column;
  margin-bottom: 20px;
}

.level-row {
  display: flex;
  gap: 14px;
  padding: 10px 0;
  position: relative;
  transition: opacity 0.2s;
}
.level-row.level-locked { opacity: 0.4; }
.level-row.level-current { opacity: 1; }

.level-icon-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 40px;
  flex-shrink: 0;
}

.level-icon { font-size: 24px; line-height: 1; z-index: 1; }

.level-connector {
  width: 2px;
  flex: 1;
  min-height: 12px;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.03));
  margin-top: 4px;
}
.level-row.level-current .level-connector {
  background: linear-gradient(to bottom, var(--color-primary), rgba(30, 224, 127, 0.1));
}

.level-info-col { flex: 1; }

.level-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.level-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.level-tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 6px;
  font-weight: 600;
}

.current-tag {
  background: rgba(30, 224, 127, 0.18);
  color: var(--color-primary);
}

.done-tag {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-tertiary);
}

.locked-tag {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-tertiary);
  font-size: 10px;
}

.level-req {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.level-progress-section {
  margin-bottom: 20px;
}

.level-progress-text {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.level-progress-text strong {
  color: var(--color-primary);
}
.level-progress-text.max-lv {
  text-align: center;
  color: #FFD700;
  font-size: 14px;
}

.level-progress-track {
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.level-progress-fill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
  transition: width 0.3s ease;
}

.level-progress-nums {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.exp-ways {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 14px;
}

.exp-ways-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.exp-way-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.exp-way-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  padding: 6px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
}

.exp-way-icon { font-size: 16px; }

.exp-way-val {
  margin-left: auto;
  font-weight: 600;
  color: var(--color-primary);
  font-size: 12px;
}

/* Modal Transition */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-active .profile-popup,
.modal-fade-enter-active .level-modal,
.modal-fade-leave-active .profile-popup,
.modal-fade-leave-active .level-modal {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-from .profile-popup,
.modal-fade-enter-from .level-modal {
  transform: translateY(16px) scale(0.96);
}
.modal-fade-leave-to .profile-popup,
.modal-fade-leave-to .level-modal {
  transform: translateY(8px) scale(0.98);
}
</style>

<!-- Non-scoped styles for v-html markdown content -->
<style>
/* Markdown Body - Blog-style Typography */
.markdown-body {
  font-size: 16px;
  line-height: 1.85;
  color: var(--text-secondary);
  word-wrap: break-word;
  overflow-wrap: break-word;
  word-break: break-word;
  letter-spacing: 0.01em;
  min-width: 0;
}

.markdown-body h1 {
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 40px 0 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-glass);
  letter-spacing: -0.01em;
}

.markdown-body h1:first-child { margin-top: 0; }

.markdown-body h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 36px 0 18px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-glass);
}

.markdown-body h2:first-child { margin-top: 0; }

.markdown-body h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 28px 0 14px;
}

.markdown-body h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 24px 0 12px;
}

.markdown-body h5, .markdown-body h6 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 20px 0 10px;
}

.markdown-body p {
  color: var(--text-secondary);
  line-height: 1.85;
  margin-bottom: 20px;
}

.markdown-body ul, .markdown-body ol {
  padding-left: 28px;
  margin-bottom: 20px;
}

.markdown-body li {
  color: var(--text-secondary);
  line-height: 1.85;
  margin-bottom: 8px;
}

.markdown-body li > ul, .markdown-body li > ol {
  margin-top: 8px;
  margin-bottom: 0;
}

.markdown-body a {
  color: var(--color-primary);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.2s;
}

.markdown-body a:hover {
  border-bottom-color: var(--color-primary);
}

.markdown-body strong {
  color: var(--text-primary);
  font-weight: 600;
}

.markdown-body em {
  font-style: italic;
}

.markdown-body blockquote {
  margin: 20px 0;
  padding: 16px 24px;
  border-left: 3px solid var(--color-primary);
  background: rgba(30, 224, 127, 0.06);
  border-radius: 0 10px 10px 0;
  color: var(--text-secondary);
  backdrop-filter: blur(4px);
}

.markdown-body blockquote p:last-child {
  margin-bottom: 0;
}

.markdown-body code {
  background: rgba(110, 118, 129, 0.25);
  padding: 2px 8px;
  border-radius: 5px;
  font-family: 'Fira Code', monospace;
  font-size: 0.875em;
  color: #7ee787;
}

.markdown-body pre {
  background: rgba(13, 17, 23, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 20px 24px;
  border-radius: 10px;
  overflow-x: auto;
  font-family: 'Fira Code', monospace;
  margin: 20px 0;
  backdrop-filter: blur(4px);
}

.markdown-body pre code {
  background: none;
  padding: 0;
  border-radius: 0;
  font-size: 13px;
  color: #a6e22e;
  line-height: 1.7;
}

.markdown-body img {
  max-width: 100%;
  height: auto;
  border-radius: 10px;
  margin: 5px 0;
  border: 1px solid var(--border-glass);
}

.markdown-body .table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin: 24px 0;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
}

.markdown-body table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 14px;
  margin: 0;
  min-width: 100%;
  table-layout: fixed;
}

.markdown-body thead {
  background: rgba(255, 255, 255, 0.08);
}

.markdown-body th {
  color: var(--text-primary);
  font-weight: 600;
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  white-space: nowrap;
}

.markdown-body th:last-child {
  border-right: none;
}

.markdown-body td {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
}

.markdown-body td:last-child {
  border-right: none;
}

.markdown-body tbody tr:last-child td {
  border-bottom: none;
}

.markdown-body tr:hover td {
  background: rgba(255, 255, 255, 0.04);
}

.markdown-body hr {
  border: none;
  border-top: 1px solid var(--border-glass);
  margin: 32px 0;
}

.markdown-body details {
  margin: 20px 0;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.04);
}

.markdown-body details summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--text-primary);
}

.markdown-body details > *:last-child {
  margin-bottom: 0;
}

/* Video Embed */
.markdown-body .video-embed {
  position: relative;
  width: 100%;
  padding-bottom: 56.25%;
  margin: 28px 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-glass);
  background: rgba(0, 0, 0, 0.4);
  min-height: 300px;
}

.markdown-body .video-embed iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: none;
}

/* ── Cash payment modal ───────────────────────────────────────────── */
.sale-mode-switch { display: flex; gap: 8px; margin-bottom: 12px; }
.sale-mode-switch .btn-sm { flex: 1; font-size: 13px; padding: 8px 0; }
.sale-mode-switch .btn-sm.active { background: var(--color-primary); color: #000; border-color: var(--color-primary); }
.cash-method-row { display: flex; gap: 8px; margin-bottom: 12px; }
.pm-pill { flex: 1; padding: 10px; border-radius: 10px; background: var(--bg-glass); border: 1px solid var(--border-color); color: var(--text-primary); cursor: pointer; font-size: 13px; }
.pm-pill.active { background: var(--color-primary); color: #000; border-color: var(--color-primary); }
.cash-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(8px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px; }
.cash-modal { width: 100%; max-width: 420px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 28px; position: relative; }
.cash-modal h3 { margin: 0 0 16px; font-size: 18px; color: var(--text-primary); }
.cash-close { position: absolute; top: 12px; right: 12px; background: transparent; border: none; color: var(--text-secondary); font-size: 18px; cursor: pointer; }
.cash-modal .form-row { margin-bottom: 12px; }
.cash-modal .form-row label { display: block; margin-bottom: 4px; font-size: 13px; color: var(--text-secondary); }
.cash-modal .form-control { width: 100%; padding: 10px; border-radius: 8px; background: var(--bg-glass); border: 1px solid var(--border-color); color: var(--text-primary); }
.cash-amount { font-size: 32px; font-weight: 800; color: var(--color-accent); text-align: center; margin: 8px 0 16px; }
.cash-qr-wrap { display: flex; align-items: center; justify-content: center; min-height: 220px; margin: 0 auto 16px; padding: 16px; background: #fff; border-radius: 12px; }
.cash-qr-wrap img { width: 200px; height: 200px; }
.cash-qr-wrap .qr-text { font-family: monospace; font-size: 12px; color: #333; word-break: break-all; }
.cash-hint { text-align: center; color: var(--text-secondary); font-size: 13px; margin-bottom: 12px; }
.cash-done-icon { font-size: 56px; text-align: center; margin-bottom: 8px; }
</style>
