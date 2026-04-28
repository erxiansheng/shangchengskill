<template>
  <div class="admin-container container">
    <div v-if="adminVerified">
    <div class="admin-header glass-panel">
      <h1>管理后台</h1>
      <p class="admin-subtitle">SkillHub 平台管理控制台</p>
    </div>

    <div class="admin-layout">
      <!-- Sidebar -->
      <aside class="admin-sidebar glass-panel">
        <ul class="admin-menu">
          <li :class="{ active: tab === 'dashboard' }" @click="tab = 'dashboard'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            仪表盘
          </li>
          <li :class="{ active: tab === 'users' }" @click="tab = 'users'; usersPage = 1; loadUsers()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            用户管理
          </li>
          <li :class="{ active: tab === 'skills' }" @click="tab = 'skills'; skillsPage = 1; loadSkills()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            商品管理
          </li>
          <li :class="{ active: tab === 'audit' }" @click="tab = 'audit'; loadPending(); loadRejected()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
            审核管理
            <span class="badge" v-if="stats.skills_pending > 0">{{ stats.skills_pending }}</span>
          </li>
          <li :class="{ active: tab === 'reviews' }" @click="tab = 'reviews'; reviewsPage = 1; loadReviews()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            评论管理
          </li>
          <li :class="{ active: tab === 'withdrawals' }" @click="tab = 'withdrawals'; wdPage = 1; loadWithdrawals()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            提现管理
            <span class="badge" v-if="pendingWdCount > 0">{{ pendingWdCount }}</span>
          </li>
          <li :class="{ active: tab === 'recharges' }" @click="tab = 'recharges'; rechargePage = 1; loadRecharges()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/><polyline points="7 2 12 7 17 2"/></svg>
            充值订单
            <span class="badge" v-if="pendingRechargeCount > 0">{{ pendingRechargeCount }}</span>
          </li>
          <li :class="{ active: tab === 'orders' }" @click="tab = 'orders'; ordersAdminPage = 1; loadAllOrders()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
            订单管理
          </li>
          <li :class="{ active: tab === 'settings' }" @click="tab = 'settings'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            系统设置
          </li>
          <li :class="{ active: tab === 'backup' }" @click="tab = 'backup'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            数据管理
          </li>
        </ul>
      </aside>

      <!-- Main Content -->
      <main class="admin-content glass-panel">

        <!-- Dashboard -->
        <div v-if="tab === 'dashboard'" class="panel-section">
          <h2>概览</h2>
          <div class="stats-grid">
            <div class="stat-box">
              <div class="stat-num">{{ stats.skills_total || 0 }}</div>
              <div class="stat-lbl">商品总数</div>
            </div>
            <div class="stat-box accent">
              <div class="stat-num">{{ stats.skills_pending || 0 }}</div>
              <div class="stat-lbl">待审核</div>
            </div>
            <div class="stat-box success">
              <div class="stat-num">{{ stats.skills_approved || 0 }}</div>
              <div class="stat-lbl">已上架</div>
            </div>
            <div class="stat-box">
              <div class="stat-num">{{ stats.skills_deleted || 0 }}</div>
              <div class="stat-lbl">已删除</div>
            </div>
            <div class="stat-box">
              <div class="stat-num">{{ stats.user_count || 0 }}</div>
              <div class="stat-lbl">注册用户</div>
            </div>
          </div>
        </div>

        <!-- Users -->
        <div v-if="tab === 'users'" class="panel-section">
          <div class="panel-toolbar">
            <h2>用户管理</h2>
            <input type="text" class="search-input" placeholder="搜索用户..." v-model="userSearch" @keyup.enter="loadUsers()" />
          </div>
          <div class="data-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>用户名</th>
                  <th>昵称</th>
                  <th>角色</th>
                  <th>积分</th>
                  <th>状态</th>
                  <th>注册时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="u in users" :key="u.id">
                  <td>{{ u.id }}</td>
                  <td>{{ u.username }}</td>
                  <td>{{ u.nickname }}</td>
                  <td><span class="role-tag" :class="u.role">{{ u.role === 'admin' ? '管理员' : '用户' }}</span></td>
                  <td>{{ u.points_balance }}</td>
                  <td>
                    <span class="status-dot" :class="u.is_banned ? 'banned' : 'active'"></span>
                    {{ u.is_banned ? '已封禁' : '正常' }}
                  </td>
                  <td>{{ formatDate(u.created_at) }}</td>
                  <td>
                    <button class="btn-sm-action" @click="toggleBan(u)" :title="u.is_banned ? '解封' : '封禁'">
                      {{ u.is_banned ? '解封' : '封禁' }}
                    </button>
                    <button class="btn-sm-action" @click="setAdmin(u)" v-if="u.role !== 'admin'">设为管理员</button>
                    <button class="btn-sm-action" @click="viewUserOrders(u)">订单</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="users.length === 0" class="empty-msg">暂无用户</div>
          <div class="admin-pagination" v-if="usersTotalPages > 1">
            <button class="page-btn" :disabled="usersPage <= 1" @click="usersPage--; loadUsers()">上一页</button>
            <span class="page-info">{{ usersPage }} / {{ usersTotalPages }}</span>
            <button class="page-btn" :disabled="usersPage >= usersTotalPages" @click="usersPage++; loadUsers()">下一页</button>
          </div>
        </div>

        <!-- Skills -->
        <div v-if="tab === 'skills'" class="panel-section">
          <div class="panel-toolbar">
            <div class="toolbar-left">
              <h2>商品管理</h2>
              <span v-if="selectedSkillCount > 0" class="selection-hint">已选 {{ selectedSkillCount }} 项</span>
            </div>
            <div class="toolbar-right">
              <button class="btn-sm-action danger" :disabled="selectedSkillCount === 0 || skillBatchDeleting" @click="batchDeleteSkills()">
                {{ skillBatchDeleting ? '删除中...' : `一键删除 (${selectedSkillCount})` }}
              </button>
              <select class="filter-select" v-model="skillStatusFilter" @change="loadSkills()">
                <option value="">全部状态</option>
                <option value="approved">已上架</option>
                <option value="pending">审核中</option>
                <option value="rejected">已拒绝</option>
                <option value="offline">已下架</option>
                <option value="deleted">已删除</option>
              </select>
              <input type="text" class="search-input" placeholder="搜索商品..." v-model="skillSearch" @keyup.enter="loadSkills()" />
            </div>
          </div>
          <div class="data-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th class="checkbox-cell">
                    <input
                      type="checkbox"
                      :checked="allSkillsSelected"
                      :disabled="allSkills.length === 0 || skillBatchDeleting"
                      @change="toggleSelectAllSkills"
                    />
                  </th>
                  <th>ID</th>
                  <th>名称</th>
                  <th>作者</th>
                  <th>价格</th>
                  <th>状态</th>
                  <th>下载</th>
                  <th>评分</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in allSkills" :key="s.id">
                  <td class="checkbox-cell">
                    <input
                      type="checkbox"
                      :checked="selectedSkillIds.includes(s.id)"
                      :disabled="skillBatchDeleting"
                      @change="toggleSkillSelection(s.id)"
                    />
                  </td>
                  <td>{{ s.id }}</td>
                  <td class="title-cell">{{ s.title }}</td>
                  <td>{{ s.author_name }}</td>
                  <td>{{ s.price === 0 ? '免费' : s.price + ' 积分' }}</td>
                  <td><span class="status-tag" :class="s.status">{{ statusMap[s.status] }}</span></td>
                  <td>{{ s.download_count }}</td>
                  <td>⭐ {{ s.avg_rating }}</td>
                  <td>{{ formatDate(s.created_at) }}</td>
                  <td>
                    <button v-if="s.status === 'approved'" class="btn-sm-action warning" :disabled="skillBatchDeleting" @click="promptOfflineSkill(s)">下架</button>
                    <router-link v-if="s.status === 'deleted'" :to="'/skill/' + s.id" class="btn-sm-action" target="_blank">查看详情</router-link>
                    <button class="btn-sm-action danger" :disabled="skillBatchDeleting" @click="adminDeleteSkill(s)">{{ s.status === 'deleted' ? '物理删除' : '删除' }}</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="allSkills.length === 0" class="empty-msg">暂无商品</div>
          <div class="admin-pagination" v-if="skillsTotalPages > 1">
            <button class="page-btn" :disabled="skillsPage <= 1" @click="skillsPage--; loadSkills()">上一页</button>
            <span class="page-info">{{ skillsPage }} / {{ skillsTotalPages }}</span>
            <button class="page-btn" :disabled="skillsPage >= skillsTotalPages" @click="skillsPage++; loadSkills()">下一页</button>
          </div>
        </div>

        <!-- Audit -->
        <div v-if="tab === 'audit'" class="panel-section">
          <h2>待审核商品 ({{ pendingSkills.length }})</h2>
          <div v-if="pendingSkills.length === 0" class="empty-msg">暂无待审核商品</div>
          <div class="audit-list">
            <div class="audit-card glass-panel" v-for="s in pendingSkills" :key="s.id">
              <div class="audit-info">
                <h3>{{ s.title }}</h3>
                <p>作者: {{ s.author }} · 提交于 {{ formatDate(s.created_at) }}</p>
              </div>
              <div class="audit-actions">
                <button class="btn btn-primary btn-sm" @click="auditSkill(s.id, 'approved')">通过</button>
                <button class="btn btn-glass btn-sm" @click="auditSkill(s.id, 'rejected', '内容不符合规范')">拒绝</button>
              </div>
            </div>
          </div>

          <h2 style="margin-top: 32px;">审核未通过商品 ({{ rejectedSkills.length }})</h2>
          <div v-if="rejectedSkills.length === 0" class="empty-msg">暂无未通过商品</div>
          <div class="audit-list">
            <div class="audit-card glass-panel rejected-card" v-for="s in rejectedSkills" :key="s.id">
              <div class="audit-info">
                <h3>{{ s.title }}</h3>
                <p>作者: {{ s.author_name }} · 价格: {{ s.price === 0 ? '免费' : s.price + ' 积分' }}</p>
              </div>
              <div class="audit-actions">
                <button class="btn btn-warning btn-sm" @click="auditSkill(s.id, 'approved', '', true)">⚠️ 强制上架</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Reviews -->
        <div v-if="tab === 'reviews'" class="panel-section">
          <div class="panel-toolbar">
            <h2>评论管理</h2>
            <input type="text" class="search-input" placeholder="搜索评论内容或用户..." v-model="reviewSearch" @keyup.enter="reviewsPage = 1; loadReviews()" />
          </div>
          <div class="data-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>商品ID</th>
                  <th>用户</th>
                  <th>评分</th>
                  <th>内容</th>
                  <th>时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in allReviews" :key="r.id">
                  <td>{{ r.id }}</td>
                  <td>{{ r.skill_id }}</td>
                  <td>{{ r.user_nickname }}</td>
                  <td>{{ '⭐'.repeat(r.rating) }}</td>
                  <td class="content-cell">{{ r.content }}</td>
                  <td>{{ formatDate(r.created_at) }}</td>
                  <td>
                    <button class="btn-sm-action danger" @click="deleteReview(r)">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="allReviews.length === 0" class="empty-msg">暂无评论</div>
          <div class="admin-pagination" v-if="reviewsTotalPages > 1">
            <button class="page-btn" :disabled="reviewsPage <= 1" @click="reviewsPage--; loadReviews()">上一页</button>
            <span class="page-info">{{ reviewsPage }} / {{ reviewsTotalPages }}</span>
            <button class="page-btn" :disabled="reviewsPage >= reviewsTotalPages" @click="reviewsPage++; loadReviews()">下一页</button>
          </div>
        </div>

        <!-- Withdrawals -->
        <div v-if="tab === 'withdrawals'" class="panel-section">
          <div class="panel-toolbar">
            <h2>提现管理</h2>
            <div class="toolbar-right">
              <select class="filter-select" v-model="wdStatusFilter" @change="wdPage = 1; loadWithdrawals()">
                <option value="">全部</option>
                <option value="pending">待处理</option>
                <option value="completed">已完成</option>
                <option value="rejected">已拒绝</option>
              </select>
              <input type="text" class="search-input" placeholder="搜索用户或支付宝..." v-model="wdSearch" @keyup.enter="wdPage = 1; loadWithdrawals()" />
            </div>
          </div>

          <div v-if="adminWithdrawals.length === 0" class="empty-msg">暂无提现申请</div>

          <div class="data-table-wrap" v-else>
            <table class="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>用户</th>
                  <th>金额</th>
                  <th>支付宝账号</th>
                  <th>真实姓名</th>
                  <th>状态</th>
                  <th>申请时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="wd in adminWithdrawals" :key="wd.id">
                  <td>{{ wd.id }}</td>
                  <td>{{ wd.user_name }}</td>
                  <td class="wd-amount-cell">{{ wd.amount }} 积分<br><small v-if="wd.actual_yuan" style="color: var(--text-secondary)">到账 ¥{{ wd.actual_yuan }}（手续费 ¥{{ wd.fee_yuan }}）</small></td>
                  <td>{{ wd.alipay_account }}</td>
                  <td>{{ wd.alipay_name }}</td>
                  <td><span class="status-tag" :class="wd.status">{{ wdStatusMap[wd.status] || wd.status }}</span></td>
                  <td>{{ formatDate(wd.created_at) }}</td>
                  <td>
                    <template v-if="wd.status === 'pending'">
                      <button class="btn-sm-action" style="color: #34C759;" @click="completeWithdrawal(wd)">已转账</button>
                      <button class="btn-sm-action danger" @click="rejectWithdrawal(wd)">拒绝</button>
                    </template>
                    <span v-else class="text-muted">--</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="admin-pagination" v-if="wdTotalPages > 1">
            <button class="page-btn" :disabled="wdPage <= 1" @click="wdPage--; loadWithdrawals()">上一页</button>
            <span class="page-info">{{ wdPage }} / {{ wdTotalPages }}</span>
            <button class="page-btn" :disabled="wdPage >= wdTotalPages" @click="wdPage++; loadWithdrawals()">下一页</button>
          </div>
        </div>

        <!-- Orders -->
        <div v-if="tab === 'recharges'" class="panel-section">
          <div class="panel-toolbar">
            <h2>充值订单</h2>
            <div class="toolbar-right">
              <select class="filter-select" v-model="rechargeStatusFilter" @change="rechargePage = 1; loadRecharges()">
                <option value="">全部</option>
                <option value="pending">待支付</option>
                <option value="paid">已完成</option>
                <option value="cancelled">已作废</option>
              </select>
              <input type="text" class="search-input" placeholder="搜索订单号或用户名..." v-model="rechargeSearch" @keyup.enter="rechargePage = 1; loadRecharges()" />
            </div>
          </div>

          <div v-if="adminRecharges.length === 0" class="empty-msg">暂无充值订单</div>

          <div class="data-table-wrap" v-else>
            <table class="data-table">
              <thead>
                <tr>
                  <th>订单号</th>
                  <th>用户</th>
                  <th>金额</th>
                  <th>积分</th>
                  <th>支付方式</th>
                  <th>状态</th>
                  <th>创建时间</th>
                  <th>支付时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="order in adminRecharges" :key="order.id">
                  <td style="font-family: monospace; font-size: 12px;">{{ order.order_no }}</td>
                  <td>{{ order.user_name }}</td>
                  <td>¥{{ order.amount_yuan }}</td>
                  <td>{{ order.points_amount }}</td>
                  <td>
                    <span v-if="order.payment_method === 'wechat'" style="color: #09B83E">💬 微信</span>
                    <span v-else-if="order.payment_method === 'alipay'" style="color: #1677FF">💳 支付宝</span>
                    <span v-else>{{ order.payment_method }}</span>
                  </td>
                  <td><span class="status-tag" :class="order.status">{{ rechargeStatusMap[order.status] || order.status }}</span></td>
                  <td>{{ formatDate(order.created_at) }}</td>
                  <td>{{ order.paid_at ? formatDate(order.paid_at) : '--' }}</td>
                  <td>
                    <template v-if="order.status === 'pending'">
                      <button class="btn-sm-action" style="color: #34C759;" @click="confirmRecharge(order)">确认到账</button>
                      <button class="btn-sm-action danger" @click="cancelRecharge(order)">作废</button>
                    </template>
                    <span v-else class="text-muted">--</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="admin-pagination" v-if="rechargeTotalPages > 1">
            <button class="page-btn" :disabled="rechargePage <= 1" @click="rechargePage--; loadRecharges()">上一页</button>
            <span class="page-info">{{ rechargePage }} / {{ rechargeTotalPages }}</span>
            <button class="page-btn" :disabled="rechargePage >= rechargeTotalPages" @click="rechargePage++; loadRecharges()">下一页</button>
          </div>
        </div>

        <!-- Orders -->
        <div v-if="tab === 'orders'" class="panel-section">
          <div class="panel-toolbar">
            <h2>订单管理</h2>
            <input type="text" class="search-input" placeholder="搜索订单号、买家或商品..." v-model="orderSearch" @keyup.enter="ordersAdminPage = 1; loadAllOrders()" />
          </div>
          <div v-if="ordersAdminLoading" style="text-align:center;padding:32px;color:var(--text-secondary)">加载中...</div>
          <div v-else-if="!allOrders.length" class="empty-msg">暂无订单记录</div>
          <div v-else class="data-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>订单号</th>
                  <th>买家</th>
                  <th>商品</th>
                  <th>金额</th>
                  <th>收货信息</th>
                  <th>状态</th>
                  <th>下单时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="o in allOrders" :key="o.id">
                  <td><span class="order-no-text">{{ o.order_no || '--' }}</span></td>
                  <td>{{ o.user_name || o.user_id }}</td>
                  <td>{{ o.skill_title }}</td>
                  <td>{{ formatOrderAmount(o) }}</td>
                  <td>
                    <div v-if="o.is_physical && o.shipping_info" class="shipping-cell">
                      <span>{{ o.shipping_info.name }} · {{ o.shipping_info.phone }}</span>
                      <span>{{ o.shipping_info.address }}</span>
                    </div>
                    <span v-else>--</span>
                  </td>
                  <td><span class="status-tag" :class="o.status">{{ formatOrderStatus(o) }}</span></td>
                  <td>{{ formatDate(o.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="admin-pagination" v-if="ordersAdminTotalPages > 1">
            <button class="page-btn" :disabled="ordersAdminPage <= 1" @click="ordersAdminPage--; loadAllOrders()">上一页</button>
            <span class="page-info">{{ ordersAdminPage }} / {{ ordersAdminTotalPages }}</span>
            <button class="page-btn" :disabled="ordersAdminPage >= ordersAdminTotalPages" @click="ordersAdminPage++; loadAllOrders()">下一页</button>
          </div>
        </div>

        <!-- Settings -->
        <div v-if="tab === 'settings'" class="panel-section">
          <h2>系统设置</h2>
          <!-- 设置子导航 -->
          <div class="setting-tabs">
            <span :class="{ active: settingSub === 'basic' }" @click="settingSub = 'basic'">📋 基本设置</span>
            <span :class="{ active: settingSub === 'points' }" @click="settingSub = 'points'">💎 积分设置</span>
            <span :class="{ active: settingSub === 'levels' }" @click="settingSub = 'levels'">🏆 等级设置</span>
            <span :class="{ active: settingSub === 'withdraw' }" @click="settingSub = 'withdraw'">💸 提现设置</span>
            <span :class="{ active: settingSub === 'payment' }" @click="settingSub = 'payment'">💰 支付管理</span>
            <span :class="{ active: settingSub === 'login' }" @click="settingSub = 'login'">🔐 登录管理</span>
            <span :class="{ active: settingSub === 'storage' }" @click="settingSub = 'storage'">☁️ 存储管理</span>
            <span :class="{ active: settingSub === 'security' }" @click="settingSub = 'security'">🛡️ 安全配置</span>
            <span :class="{ active: settingSub === 'email' }" @click="settingSub = 'email'">📧 邮件配置</span>
          </div>
          <div class="settings-grid">
            <!-- ========== 基本设置 ========== -->
            <template v-if="settingSub === 'basic'">
            <div class="setting-card glass-panel">
              <h3>SEO 设置</h3>
              <div class="setting-group">
                <label>网站标题</label>
                <input type="text" class="form-control" v-model="siteSettings.title" placeholder="SkillHub - AI 商品市场" />
              </div>
              <div class="setting-group">
                <label>网站描述</label>
                <textarea class="form-control" rows="2" v-model="siteSettings.description" placeholder="发现和交易顶尖 AI 商品..."></textarea>
              </div>
              <div class="setting-group">
                <label>关键词</label>
                <input type="text" class="form-control" v-model="siteSettings.keywords" placeholder="AI, 商品, 市场, SkillHub" />
              </div>
            </div>

            <div class="setting-card glass-panel">
              <h3>备案信息</h3>
              <div class="setting-group">
                <label>ICP 备案号</label>
                <input type="text" class="form-control" v-model="siteSettings.icp" placeholder="京ICP备XXXXXXXX号" />
              </div>
              <div class="setting-group">
                <label>公安备案号</label>
                <input type="text" class="form-control" v-model="siteSettings.police" placeholder="京公网安备 XXXXXXXXXXX 号" />
              </div>
            </div>

            <div class="setting-card glass-panel">
              <h3>关于页面</h3>
              <div class="setting-group">
                <label>关于内容 (Markdown)</label>
                <textarea
                  class="form-control"
                  rows="20"
                  v-model="siteSettings.about"
                  placeholder="# 关于 SkillHub..."
                  style="font-family: 'Fira Code', 'JetBrains Mono', Consolas, monospace; font-size: 13px; line-height: 1.7;"
                ></textarea>
                <p class="setting-hint" style="line-height:1.7">
                  使用 Markdown 编辑。支持以下扩展：<br />
                  • <strong>图片</strong>：<code>![描述](https://example.com/img.png)</code><br />
                  • <strong>Bilibili 视频</strong>：将链接 <code>https://www.bilibili.com/video/BVxxxxx</code> 单独占一行<br />
                  • <strong>YouTube 视频</strong>：<code>https://youtu.be/xxx</code> 或 <code>https://www.youtube.com/watch?v=xxx</code> 单独占一行<br />
                  • <strong>自定义视频</strong>：<code>.mp4 / .webm / .mov</code> 链接单独占一行将自动渲染为播放器<br />
                  • 标题 / 列表 / 表格 / 代码块 / 引用块均按标准 Markdown 语法<br />
                  保留为空时将使用前端内置的默认关于内容。完整模板请参考 <code>public/about.md</code>。
                </p>
              </div>
            </div>

            <div class="setting-card glass-panel">
              <h3>平台设置</h3>
              <div class="setting-group">
                <label>平台手续费率 (%)</label>
                <input type="number" class="form-control" v-model.number="siteSettings.feeRate" min="0" max="100" />
              </div>
              <div class="setting-group">
                <label>注册赠送积分</label>
                <input type="number" class="form-control" v-model.number="siteSettings.registerBonus" min="0" />
              </div>
              <div class="setting-group">
                <label class="toggle-label">
                  <input type="checkbox" v-model="siteSettings.rechargeEnabled" />
                  启用充值功能
                </label>
                <p class="setting-hint">关闭后，小程序和网页端将隐藏"充值与流水"模块</p>
              </div>
              <div class="setting-group">
                <label class="toggle-label">
                  <input type="checkbox" v-model="siteSettings.publishEnabled" />
                  启用发布功能
                </label>
                <p class="setting-hint">关闭后，小程序底部导航栏将隐藏"发布"按钮</p>
              </div>
              <div class="setting-group">
                <label class="toggle-label">
                  <input type="checkbox" v-model="siteSettings.betaAnnouncement" />
                  开启公告弹窗
                </label>
                <p class="setting-hint">开启后，用户打开站点时会弹出公告（每次会话仅显示一次）</p>
              </div>
              <div class="setting-group" v-if="siteSettings.betaAnnouncement">
                <label>公告标题</label>
                <input type="text" class="form-control" v-model="siteSettings.announcementTitle" placeholder="例：站点公告" />
              </div>
              <div class="setting-group" v-if="siteSettings.betaAnnouncement">
                <label>公告内容</label>
                <textarea class="form-control" rows="4" v-model="siteSettings.announcementContent" placeholder="输入公告正文，支持换行"></textarea>
              </div>
            </div>
            </template>

            <!-- ========== 积分设置 ========== -->
            <template v-if="settingSub === 'points'">
            <div class="setting-card glass-panel">
              <h3>💎 充值积分比例</h3>
              <div class="setting-group">
                <label>每元兑换积分数</label>
                <input type="number" class="form-control" v-model.number="siteSettings.pointsPerYuan" min="1" placeholder="10" />
                <p class="setting-hint">默认 10，即 1 元 = 10 积分</p>
              </div>
              <div class="setting-group">
                <label>最低充值金额（元）</label>
                <input type="number" class="form-control" v-model.number="siteSettings.minRechargeYuan" min="1" placeholder="1" />
              </div>
            </div>
            <div class="setting-card glass-panel">
              <h3>📦 充值套餐配置</h3>
              <p class="setting-hint" style="margin-bottom:12px">配置预设充值套餐（JSON 数组），留空使用默认套餐。每项需包含 amountYuan（金额）和 points（积分）。</p>
              <div class="setting-group">
                <label>套餐列表（JSON）</label>
                <textarea class="form-control" rows="6" v-model="rechargePackagesJson" placeholder='[{"amount_yuan":6,"points":60},{"amount_yuan":30,"points":300}]'></textarea>
                <p class="setting-hint" v-if="rechargePackagesError" style="color:var(--danger)">{{ rechargePackagesError }}</p>
              </div>
            </div>
            </template>

            <!-- ========== 等级设置 ========== -->
            <template v-if="settingSub === 'levels'">
            <div class="setting-card glass-panel">
              <h3>🏆 经验值获取</h3>
              <div class="setting-group">
                <label>发布商品获得经验</label>
                <input type="number" class="form-control" v-model.number="siteSettings.expPublish" min="0" placeholder="20" />
              </div>
              <div class="setting-group">
                <label>被下载获得经验</label>
                <input type="number" class="form-control" v-model.number="siteSettings.expDownload" min="0" placeholder="2" />
              </div>
              <div class="setting-group">
                <label>被收藏获得经验</label>
                <input type="number" class="form-control" v-model.number="siteSettings.expFavorite" min="0" placeholder="3" />
              </div>
              <div class="setting-group">
                <label>每充值 1 元获得经验</label>
                <input type="number" class="form-control" v-model.number="siteSettings.expRechargeYuan" min="0" placeholder="1" />
              </div>
            </div>
            <div class="setting-card glass-panel">
              <h3>📊 等级配置</h3>
              <p class="setting-hint" style="margin-bottom:12px">配置等级列表（JSON 数组），留空使用默认等级。每项需包含 level、name、icon、minExp。</p>
              <div class="setting-group">
                <label>等级列表（JSON）</label>
                <textarea class="form-control" rows="8" v-model="levelsConfigJson" placeholder='[{"level":1,"name":"新手虾","icon":"🦐","minExp":0}]'></textarea>
                <p class="setting-hint" v-if="levelsConfigError" style="color:var(--danger)">{{ levelsConfigError }}</p>
              </div>
            </div>
            </template>

            <!-- ========== 提现设置 ========== -->
            <template v-if="settingSub === 'withdraw'">
            <div class="setting-card glass-panel">
              <h3>💸 提现参数</h3>
              <div class="setting-group">
                <label>提现手续费率</label>
                <input type="number" class="form-control" v-model.number="siteSettings.withdrawFeeRate" min="0" max="1" step="0.01" placeholder="0.04" />
                <p class="setting-hint">填写小数，如 0.04 表示 4%</p>
              </div>
              <div class="setting-group">
                <label>最低提现积分</label>
                <input type="number" class="form-control" v-model.number="siteSettings.minWithdrawPoints" min="100" placeholder="1040" />
                <p class="setting-hint">用户余额≥此值才可申请提现</p>
              </div>
            </div>
            </template>

            <!-- ========== 支付管理 ========== -->
            <template v-if="settingSub === 'payment'">
            <div class="setting-card glass-panel">
              <h3> 支付宝配置</h3>
              <div class="setting-group">
                <label class="toggle-label">
                  <input type="checkbox" v-model="siteSettings.alipayEnabled" />
                  启用支付宝支付
                </label>
              </div>
              <template v-if="siteSettings.alipayEnabled">
                <div class="setting-group">
                  <label>应用 AppID</label>
                  <input type="text" class="form-control" v-model="siteSettings.alipayAppId" placeholder="应用的 AppID" />
                </div>
                <div class="setting-group">
                  <label>应用私钥</label>
                  <textarea class="form-control" rows="3" v-model="siteSettings.alipayPrivateKey" placeholder="RSA2 应用私钥（PKCS1 格式）"></textarea>
                </div>
                <div class="setting-group">
                  <label>支付宝公钥</label>
                  <textarea class="form-control" rows="3" v-model="siteSettings.alipayPublicKey" placeholder="支付宝公钥（用于验签）"></textarea>
                </div>
                <div class="setting-group">
                  <label class="toggle-label">
                    <input type="checkbox" v-model="siteSettings.alipaySandbox" />
                    沙箱环境（测试模式）
                  </label>
                </div>
              </template>
            </div>

            <div class="setting-card glass-panel">
              <h3>💬 微信支付配置</h3>
              <div class="setting-group">
                <label class="toggle-label">
                  <input type="checkbox" v-model="siteSettings.wechatEnabled" />
                  启用微信支付
                </label>
              </div>
              <template v-if="siteSettings.wechatEnabled">
                <div class="setting-group">
                  <label>公众号 AppID</label>
                  <input type="text" class="form-control" v-model="siteSettings.wechatAppId" placeholder="微信公众号 AppID" />
                </div>
                <div class="setting-group">
                  <label>商户号 MchID</label>
                  <input type="text" class="form-control" v-model="siteSettings.wechatMchId" placeholder="微信支付商户号" />
                </div>
                <div class="setting-group">
                  <label>API 密钥 (V2)</label>
                  <input type="password" class="form-control" v-model="siteSettings.wechatApiKey" placeholder="微信支付 API 密钥" />
                </div>
                <div class="setting-group">
                  <label>API V3 密钥</label>
                  <input type="password" class="form-control" v-model="siteSettings.wechatApiV3Key" placeholder="微信支付 API V3 密钥" />
                </div>
                <div class="setting-group">
                  <label>证书序列号</label>
                  <input type="text" class="form-control" v-model="siteSettings.wechatSerialNo" placeholder="商户 API 证书序列号" />
                </div>
              </template>
            </div>
            </template>

            <!-- ========== 登录管理 ========== -->
            <template v-if="settingSub === 'login'">
            <div class="setting-card glass-panel">
              <h3>🐧 QQ 登录配置</h3>
              <div class="setting-group">
                <label>QQ 互联 App ID</label>
                <input type="text" class="form-control" v-model="siteSettings.qqAppId" placeholder="在 connect.qq.com 申请的 APP ID" />
              </div>
              <div class="setting-group">
                <label>App Key</label>
                <input type="password" class="form-control" v-model="siteSettings.qqAppKey" placeholder="QQ 互联 App Key" />
              </div>
              <div class="setting-group">
                <label>回调地址</label>
                <input type="text" class="form-control" v-model="siteSettings.qqRedirectUri" placeholder="https://yourdomain.com/api/v1/auth/qq/callback" />
                <p class="setting-hint">QQ 登录回调 API: <code>/api/v1/auth/qq/callback</code></p>
              </div>
            </div>

            <div class="setting-card glass-panel">
              <h3>💬 微信扫码登录配置</h3>
              <div class="setting-group">
                <label>微信开放平台 AppID</label>
                <input type="text" class="form-control" v-model="siteSettings.wxLoginAppId" placeholder="在 open.weixin.qq.com 申请的网站应用 AppID" />
              </div>
              <div class="setting-group">
                <label>AppSecret</label>
                <input type="password" class="form-control" v-model="siteSettings.wxLoginAppSecret" placeholder="微信开放平台 AppSecret" />
              </div>
              <div class="setting-group">
                <label>回调地址</label>
                <input type="text" class="form-control" v-model="siteSettings.wxLoginRedirectUri" placeholder="https://yourdomain.com/api/v1/auth/wechat/callback" />
                <p class="setting-hint">微信登录回调 API: <code>/api/v1/auth/wechat/callback</code></p>
              </div>
            </div>

            <div class="setting-card glass-panel">
              <h3>📱 微信 H5 网页授权配置（公众号）</h3>
              <div class="setting-group">
                <label>公众号 AppID</label>
                <input type="text" class="form-control" v-model="siteSettings.wxMpAppId" placeholder="已认证微信服务号的 AppID" />
                <p class="setting-hint">H5 微信登录需要已认证的微信服务号（不是开放平台网站应用）</p>
              </div>
              <div class="setting-group">
                <label>公众号 AppSecret</label>
                <input type="password" class="form-control" v-model="siteSettings.wxMpAppSecret" placeholder="公众号 AppSecret" />
              </div>
              <div class="setting-group">
                <p class="setting-hint">⚠️ 需要在微信公众平台 → 设置与开发 → 公众号设置 → 功能设置中，将你的域名添加到「网页授权域名」</p>
                <p class="setting-hint">回调地址由系统自动生成: <code>/api/v1/auth/wechat/h5-callback</code></p>
              </div>
            </div>

            <div class="setting-card glass-panel">
              <h3>🤖 微信小程序配置</h3>
              <div class="setting-group">
                <label>小程序 AppID</label>
                <input type="text" class="form-control" v-model="siteSettings.wxMiniAppId" placeholder="微信小程序 AppID" />
                <p class="setting-hint">在 mp.weixin.qq.com 创建的小程序 AppID</p>
              </div>
              <div class="setting-group">
                <label>小程序 AppSecret</label>
                <input type="password" class="form-control" v-model="siteSettings.wxMiniAppSecret" placeholder="小程序 AppSecret" />
              </div>
              <div class="setting-group">
                <p class="setting-hint">⚠️ 需要在小程序管理后台 → 开发管理 → 开发设置 → 服务器域名中配置 request 合法域名和业务域名</p>
              </div>
            </div>
            </template>

            <!-- ========== 安全配置 ========== -->
            <template v-if="settingSub === 'security'">
            <div class="setting-card glass-panel">
              <h3>🛡️ VirusTotal 配置</h3>
              <div class="setting-group">
                <label>VirusTotal API Key</label>
                <input type="password" class="form-control" v-model="siteSettings.vtApiKey" placeholder="在 virustotal.com 获取的 API Key" />
                <p class="setting-hint">商品文件上传后将通过 VirusTotal 进行安全扫描。未配置时自动跳过安全检查。</p>
              </div>
            </div>
            </template>

            <!-- ========== 邮件配置 ========== -->
            <template v-if="settingSub === 'email'">
            <div class="setting-card glass-panel">
              <h3>📧 邮件通知配置</h3>
              <div class="setting-group">
                <label>通知邮箱</label>
                <input type="email" class="form-control" v-model="siteSettings.notifyEmail" placeholder="admin@example.com" />
                <p class="setting-hint">接收系统通知的邮箱地址（提现申请、充值到账、VT key 失效等）</p>
              </div>
              <div class="setting-group">
                <label>SMTP 服务器</label>
                <input type="text" class="form-control" v-model="siteSettings.smtpHost" placeholder="smtp.qq.com" />
              </div>
              <div class="setting-group">
                <label>SMTP 端口</label>
                <input type="number" class="form-control" v-model.number="siteSettings.smtpPort" placeholder="465" />
                <p class="setting-hint">SSL 端口通常为 465，STARTTLS 端口通常为 587</p>
              </div>
              <div class="setting-group">
                <label>SMTP 用户名</label>
                <input type="text" class="form-control" v-model="siteSettings.smtpUser" placeholder="发件邮箱账号" />
              </div>
              <div class="setting-group">
                <label>SMTP 密码</label>
                <input type="password" class="form-control" v-model="siteSettings.smtpPass" placeholder="SMTP 授权码或密码" />
              </div>
              <div class="setting-group">
                <label>发件人地址</label>
                <input type="email" class="form-control" v-model="siteSettings.smtpFrom" placeholder="留空则使用 SMTP 用户名" />
              </div>
            </div>
            </template>

            <!-- ========== 存储管理 ========== -->
            <template v-if="settingSub === 'storage'">
            <div class="setting-card glass-panel">
              <h3>☁️ S3 对象存储配置</h3>
              <p class="setting-hint" style="margin-bottom:12px">配置 S3 兼容存储服务。更换存储不影响已有文件链接。</p>
              <div class="setting-group">
                <label>S3 Endpoint</label>
                <input type="text" class="form-control" v-model="siteSettings.s3Endpoint" placeholder="https://s3.amazonaws.com" />
              </div>
              <div class="setting-group">
                <label>Bucket 名称</label>
                <input type="text" class="form-control" v-model="siteSettings.s3Bucket" placeholder="my-bucket" />
              </div>
              <div class="setting-group">
                <label>Access Key</label>
                <input type="text" class="form-control" v-model="siteSettings.s3AccessKey" placeholder="AKIAXXXXXXXX" />
              </div>
              <div class="setting-group">
                <label>Secret Key</label>
                <input type="password" class="form-control" v-model="siteSettings.s3SecretKey" placeholder="S3 Secret Key" />
              </div>
              <div class="setting-group">
                <label>Region</label>
                <input type="text" class="form-control" v-model="siteSettings.s3Region" placeholder="us-east-1" />
              </div>
              <div class="setting-group">
                <label>公开访问 URL</label>
                <input type="text" class="form-control" v-model="siteSettings.s3PublicUrl" placeholder="https://cdn.example.com" />
                <p class="setting-hint">CDN 或公开访问域名，用于生成文件下载链接</p>
              </div>
            </div>

            <div class="setting-card glass-panel">
              <h3>📦 上传限制</h3>
              <div class="setting-group">
                <label>图片最大大小 (字节)</label>
                <input type="number" class="form-control" v-model.number="siteSettings.maxImageSize" placeholder="5242880" />
                <p class="setting-hint">默认 5MB (5242880)，单位为字节</p>
              </div>
              <div class="setting-group">
                <label>商品包最大大小 (字节)</label>
                <input type="number" class="form-control" v-model.number="siteSettings.maxSkillPackageSize" placeholder="52428800" />
                <p class="setting-hint">默认 5MB (5242880)，单位为字节</p>
              </div>
            </div>
            </template>
          </div>

          <div class="settings-actions">
            <button class="btn btn-primary" @click="saveSettings">保存设置</button>
          </div>
        </div>

        <!-- Backup & Restore -->
        <div v-if="tab === 'backup'" class="panel-section">
          <h2 class="panel-title">📦 数据管理</h2>

          <div class="backup-section glass-panel" style="padding:24px; margin-bottom:24px">
            <h3 style="margin-bottom:16px">维护工具</h3>
            <p style="color:var(--text-secondary);font-size:14px;margin-bottom:16px">
              重建商品标题索引，补齐历史 pending 和 approved 数据的重名校验索引。该操作不会修改商品正文或上下架状态。
            </p>
            <div class="backup-error" v-if="rebuildIndexError" style="color:#FF453A;font-size:14px;margin:12px 0">{{ rebuildIndexError }}</div>
            <div class="backup-success" v-if="rebuildIndexSummary" style="color:#30D158;font-size:14px;margin:12px 0 16px">
              已删除旧索引 {{ rebuildIndexSummary.deleted_index_keys || 0 }} 个，重建 {{ rebuildIndexSummary.rebuilt_indexes || 0 }} 个；
              approved 收录 {{ rebuildIndexSummary.indexed_statuses?.approved || 0 }} 条，pending 收录 {{ rebuildIndexSummary.indexed_statuses?.pending || 0 }} 条。
            </div>
            <button class="btn btn-primary" @click="handleRebuildTitleIndexes" :disabled="rebuildIndexLoading">
              {{ rebuildIndexLoading ? '重建中...' : '重建商品标题索引' }}
            </button>
            <button class="btn btn-glass" @click="handleRebuildAggregate" :disabled="rebuildAggregateLoading" style="margin-left:10px">
              {{ rebuildAggregateLoading ? '重建中...' : '重建边缘列表分片缓存' }}
            </button>
            <div v-if="rebuildAggregateResult" style="color:#30D158;font-size:13px;margin-top:10px">✓ {{ rebuildAggregateResult }}</div>
            <div v-if="rebuildIndexSummary?.conflict_count > 0" style="margin-top:16px;padding:14px 16px;border-radius:12px;background:rgba(255,69,58,0.08);border:1px solid rgba(255,69,58,0.18)">
              <div style="font-size:14px;font-weight:600;color:#ffb4aa;margin-bottom:8px">
                检测到 {{ rebuildIndexSummary.conflict_count }} 组同状态重名商品，以下仅展示前 {{ rebuildIndexSummary.conflicts?.length || 0 }} 组：
              </div>
              <div v-for="conflict in rebuildIndexSummary.conflicts || []" :key="`${conflict.status}-${conflict.title}`" style="font-size:13px;color:var(--text-secondary);line-height:1.6">
                <strong style="color:var(--text-primary)">[{{ conflict.status }}]</strong> {{ conflict.title }}
                <span style="color:var(--text-tertiary)"> · 商品 ID：{{ (conflict.skill_ids || []).join(', ') }}</span>
              </div>
            </div>
          </div>

          <div class="backup-section glass-panel" style="padding:24px; margin-bottom:24px">
            <h3 style="margin-bottom:16px">备份数据</h3>
            <p style="color:var(--text-secondary);font-size:14px;margin-bottom:16px">导出所有数据，自动按分类打包为 ZIP（含用户、商品、设置、订单等独立 JSON 文件）。</p>
            <div class="backup-error" v-if="backupError" style="color:#FF453A;font-size:14px;margin:12px 0">{{ backupError }}</div>
            <button class="btn btn-primary" @click="handleBackup" :disabled="backupLoading">
              {{ backupLoading ? '备份中...' : '开始备份（导出 ZIP）' }}
            </button>
          </div>

          <div class="backup-section glass-panel" style="padding:24px">
            <h3 style="margin-bottom:16px">恢复数据</h3>
            <p style="color:var(--text-secondary);font-size:14px;margin-bottom:16px">
              支持导入完整 ZIP 备份或单个分类 JSON 文件。<strong style="color:#FF453A">⚠️ 导入会覆盖同 key 的现有数据！</strong>
            </p>
            <div class="form-group">
              <label>选择备份文件（ZIP 或 JSON）</label>
              <input type="file" accept=".json,.zip" @change="handleRestoreFile" style="color:var(--text-secondary)" ref="restoreFileInput" />
            </div>
            <!-- Category selector for ZIP -->
            <div v-if="restoreCategories.length > 1" class="form-group" style="margin-top:12px">
              <label>选择要恢复的分类（可多选）</label>
              <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px">
                <label v-for="cat in restoreCategories" :key="cat.name"
                  style="display:flex;align-items:center;gap:6px;font-size:14px;cursor:pointer;padding:6px 12px;border-radius:8px;border:1px solid var(--border-glass);background:rgba(255,255,255,0.03)">
                  <input type="checkbox" v-model="cat.selected" />
                  <span>{{ cat.label }}</span>
                  <span style="font-size:12px;color:var(--text-tertiary)">({{ cat.count }} 条)</span>
                </label>
              </div>
            </div>
            <div class="backup-error" v-if="restoreError" style="color:#FF453A;font-size:14px;margin:12px 0">{{ restoreError }}</div>
            <div class="backup-success" v-if="restoreSuccess" style="color:#30D158;font-size:14px;margin:12px 0">{{ restoreSuccess }}</div>
            <button class="btn btn-danger-solid" @click="handleRestore" :disabled="restoreLoading || !hasRestoreData">
              {{ restoreLoading ? '恢复中...' : '开始恢复' }}
            </button>
          </div>
        </div>

      </main>
    </div>

    <!-- Offline Reason Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showOfflineModal" class="modal-overlay" @click.self="showOfflineModal = false">
          <div class="modal-dialog glass-panel">
            <h3 class="modal-title">下架商品</h3>
            <p class="modal-message">确定要下架商品 "{{ offlineSkillTitle }}"？请填写下架原因：</p>
            <textarea v-model="offlineReason" class="offline-reason-input" placeholder="请输入下架原因..." rows="3"></textarea>
            <div class="modal-actions">
              <button class="btn btn-glass" @click="showOfflineModal = false">取消</button>
              <button class="btn btn-danger-solid" @click="confirmOfflineSkill">确认下架</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Reject Withdrawal Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showRejectWdModal" class="modal-overlay" @click.self="showRejectWdModal = false">
          <div class="modal-dialog glass-panel">
            <h3 class="modal-title">拒绝提现</h3>
            <p class="modal-message">确定要拒绝用户 "{{ rejectWdUser }}" 的提现申请？请填写拒绝原因：</p>
            <textarea v-model="rejectWdReason" class="offline-reason-input" placeholder="请输入拒绝原因..." rows="3"></textarea>
            <div class="modal-actions">
              <button class="btn btn-glass" @click="showRejectWdModal = false">取消</button>
              <button class="btn btn-danger-solid" @click="confirmRejectWithdrawal">确认拒绝</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- User Orders Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showOrdersModal" class="modal-overlay" @click.self="showOrdersModal = false">
          <div class="modal-dialog modal-wide glass-panel">
            <h3 class="modal-title">用户订单 — {{ ordersUser }}</h3>
            <div v-if="ordersLoading" style="text-align:center;padding:32px;color:var(--text-secondary)">加载中...</div>
            <div v-else class="orders-tabs-wrap">
              <!-- 子标签 -->
              <div class="orders-tabs">
                <span :class="{ active: ordersTab === 'purchases' }" @click="ordersTab = 'purchases'">
                  购买记录 ({{ orderData.purchases?.length || 0 }})
                </span>
                <span :class="{ active: ordersTab === 'sales' }" @click="ordersTab = 'sales'">
                  售出记录 ({{ orderData.sales?.length || 0 }})
                </span>
                <span :class="{ active: ordersTab === 'points' }" @click="ordersTab = 'points'">
                  积分记录 ({{ orderData.points_records?.length || 0 }})
                </span>
              </div>

              <!-- 购买记录 -->
              <div v-if="ordersTab === 'purchases'" class="orders-list">
                <div v-if="!orderData.purchases?.length" class="empty-msg">暂无购买记录</div>
                <div v-for="p in orderData.purchases" :key="p.id" class="order-item glass-panel">
                  <div class="order-main">
                    <span class="order-title">{{ p.skill_title }}</span>
                    <span class="order-price">{{ formatOrderAmount(p, '-') }}</span>
                  </div>
                  <div class="order-sub">
                    <span>{{ p.order_no }}</span>
                    <span>{{ formatDate(p.created_at) }}</span>
                  </div>
                  <div v-if="p.is_physical && p.shipping_info" class="order-detail">
                    {{ p.shipping_info.name }} · {{ p.shipping_info.phone }} · {{ p.shipping_info.address }}
                  </div>
                </div>
              </div>

              <!-- 售出记录 -->
              <div v-if="ordersTab === 'sales'" class="orders-list">
                <div v-if="!orderData.sales?.length" class="empty-msg">暂无售出记录</div>
                <div v-for="s in orderData.sales" :key="s.skill_id" class="order-item glass-panel">
                  <div class="order-main">
                    <span class="order-title">{{ s.title }}</span>
                    <span class="order-price" style="color:#34C759">+{{ s.total_earned }} 积分</span>
                  </div>
                  <div class="order-sub">
                    <span>单价 {{ s.price }} · 售出 {{ s.purchase_count }} 次</span>
                  </div>
                </div>
              </div>

              <!-- 积分记录 -->
              <div v-if="ordersTab === 'points'" class="orders-list">
                <div v-if="!orderData.points_records?.length" class="empty-msg">暂无积分记录</div>
                <div v-for="r in orderData.points_records" :key="r.id" class="order-item glass-panel">
                  <div class="order-main">
                    <span class="order-title">{{ r.description || r.type }}</span>
                    <span class="order-price" :style="{ color: r.amount >= 0 ? '#34C759' : '#FF453A' }">
                      {{ r.amount >= 0 ? '+' : '' }}{{ r.amount }} 积分
                    </span>
                  </div>
                  <div class="order-sub">
                    <span>余额: {{ r.balance_after }}</span>
                    <span>{{ formatDate(r.created_at) }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="modal-actions" style="margin-top:16px">
              <button class="btn btn-glass" @click="showOrdersModal = false">关闭</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <ConfirmModal
      :visible="showConfirm"
      :title="confirmTitle"
      :message="confirmMsg"
      :type="confirmType"
      @confirm="confirmAction"
      @cancel="showConfirm = false"
    />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { get, post, put, del, adminGet, adminPost, adminPut, adminDel } from '../api/request.js'
import { userStore } from '../stores/user.js'
import { useToast, KV_SYNC_HINT } from '../composables/useToast.js'
import ConfirmModal from '../components/ConfirmModal.vue'

const router = useRouter()
const toast = useToast()

const tab = ref('dashboard')
const settingSub = ref('basic')
const adminVerified = ref(false)
const stats = reactive({ skills_total: 0, skills_pending: 0, skills_approved: 0, user_count: 0 })
const users = ref([])
const allSkills = ref([])
const selectedSkillIds = ref([])
const skillBatchDeleting = ref(false)
const pendingSkills = ref([])
const rejectedSkills = ref([])
const allReviews = ref([])
const adminWithdrawals = ref([])
const wdStatusFilter = ref('')
const pendingWdCount = ref(0)
const wdStatusMap = { pending: '待处理', completed: '已完成', rejected: '已拒绝' }
const userSearch = ref('')
const skillSearch = ref('')
const skillStatusFilter = ref('')
const reviewSearch = ref('')
const wdSearch = ref('')
const orderSearch = ref('')
const showConfirm = ref(false)

// Pagination state
const ADMIN_PAGE_SIZE = 10
const usersPage = ref(1)
const usersTotalPages = ref(1)
const skillsPage = ref(1)
const skillsTotalPages = ref(1)
const reviewsPage = ref(1)
const reviewsTotalPages = ref(1)
const wdPage = ref(1)
const wdTotalPages = ref(1)
const ordersAdminPage = ref(1)
const ordersAdminTotalPages = ref(1)

// Recharge management
const adminRecharges = ref([])
const rechargeStatusFilter = ref('')
const rechargeSearch = ref('')
const rechargePage = ref(1)
const rechargeTotalPages = ref(1)
const pendingRechargeCount = ref(0)
const rechargeStatusMap = { pending: '待支付', paid: '已完成', cancelled: '已作废' }
const ordersAdminLoading = ref(false)
const allOrders = ref([])
const showOfflineModal = ref(false)
const offlineReason = ref('')
const offlineSkillId = ref(null)
const offlineSkillTitle = ref('')
const showRejectWdModal = ref(false)
const rejectWdReason = ref('')
const rejectWdId = ref(null)
const rejectWdUser = ref('')

// User orders modal
const showOrdersModal = ref(false)
const ordersUser = ref('')
const ordersTab = ref('purchases')
const ordersLoading = ref(false)
const orderData = reactive({ purchases: [], sales: [], points_records: [] })

const confirmTitle = ref('')
const confirmMsg = ref('')
const confirmType = ref('danger')
let confirmCallback = null

// Backup & Restore state
const backupLoading = ref(false)
const backupError = ref('')
const backupProgress = ref('')
const rebuildIndexLoading = ref(false)
const rebuildAggregateLoading = ref(false)
const rebuildAggregateResult = ref('')
const rebuildIndexError = ref('')
const rebuildIndexSummary = ref(null)
const restoreLoading = ref(false)
const restoreError = ref('')
const restoreSuccess = ref('')
const restoreFileInput = ref(null)
const restoreCategories = ref([]) // [{name, label, count, data, selected}]
const restoreData = ref(null) // flat KV data for single JSON file

const CATEGORY_LABELS = {
  users: '👤 用户数据',
  skills: '📦 商品数据',
  categories: '📂 分类数据',
  settings: '⚙️ 站点设置',
  orders: '💳 订单/充值',
  messages: '💬 消息',
  reviews: '⭐ 评论',
  favorites: '❤️ 收藏',
  tokens: '🔑 API Token',
  purchases: '🛒 购买记录',
  points: '💰 积分记录',
  withdrawals: '🏦 提现记录',
  social: '👥 关注关系',
  audits: '📝 审核日志',
  other: '📋 其他数据',
}

const hasRestoreData = computed(() => {
  if (restoreData.value) return true
  return restoreCategories.value.some(c => c.selected)
})

const selectedSkillCount = computed(() => selectedSkillIds.value.length)
const allSkillsSelected = computed(() => (
  allSkills.value.length > 0 && allSkills.value.every(skill => selectedSkillIds.value.includes(skill.id))
))

const siteSettings = reactive({
  title: 'SkillHub - AI 商品市场',
  description: '发现和交易顶尖 AI 商品',
  keywords: 'AI, 商品, 市场, SkillHub',
  icp: '',
  police: '',
  about: '',
  feeRate: 30,
  registerBonus: 100,
  rechargeEnabled: true,
  publishEnabled: true,
  betaAnnouncement: false,
  announcementTitle: '',
  announcementContent: '',
  // Alipay
  alipayEnabled: false,
  alipayAppId: '',
  alipayPrivateKey: '',
  alipayPublicKey: '',
  alipaySandbox: false,
  // WeChat Pay
  wechatEnabled: false,
  wechatAppId: '',
  wechatMchId: '',
  wechatApiKey: '',
  wechatApiV3Key: '',
  wechatSerialNo: '',
  // QQ OAuth
  qqAppId: '',
  qqAppKey: '',
  qqRedirectUri: '',
  // WeChat OAuth login
  wxLoginAppId: '',
  wxLoginAppSecret: '',
  wxLoginRedirectUri: '',
  // WeChat MP H5 OAuth
  wxMpAppId: '',
  wxMpAppSecret: '',
  // WeChat Mini Program
  wxMiniAppId: '',
  wxMiniAppSecret: '',
  // VirusTotal
  vtApiKey: '',
  // Email notification
  notifyEmail: '',
  smtpHost: '',
  smtpPort: 465,
  smtpUser: '',
  smtpPass: '',
  smtpFrom: '',
  // S3 storage
  s3Endpoint: '',
  s3Bucket: '',
  s3AccessKey: '',
  s3SecretKey: '',
  s3Region: 'us-east-1',
  s3PublicUrl: '',
  // Upload limits
  maxImageSize: 5242880,
  maxSkillPackageSize: 52428800,
  // 积分设置
  rechargePackages: null,
  minRechargeYuan: 1,
  pointsPerYuan: 10,
  // 等级设置
  levelsConfig: null,
  expPublish: 20,
  expDownload: 2,
  expFavorite: 3,
  expRechargeYuan: 1,
  // 提现设置
  withdrawFeeRate: 0.04,
  minWithdrawPoints: 1040,
})

const rechargePackagesError = ref('')
const rechargePackagesJson = computed({
  get() {
    return siteSettings.rechargePackages ? JSON.stringify(siteSettings.rechargePackages, null, 2) : ''
  },
  set(v) {
    if (!v.trim()) { siteSettings.rechargePackages = null; rechargePackagesError.value = ''; return }
    try { siteSettings.rechargePackages = JSON.parse(v); rechargePackagesError.value = '' }
    catch { rechargePackagesError.value = 'JSON 格式错误' }
  }
})

const levelsConfigError = ref('')
const levelsConfigJson = computed({
  get() {
    return siteSettings.levelsConfig ? JSON.stringify(siteSettings.levelsConfig, null, 2) : ''
  },
  set(v) {
    if (!v.trim()) { siteSettings.levelsConfig = null; levelsConfigError.value = ''; return }
    try { siteSettings.levelsConfig = JSON.parse(v); levelsConfigError.value = '' }
    catch { levelsConfigError.value = 'JSON 格式错误' }
  }
})

const statusMap = {
  approved: '已上架',
  pending: '审核中',
  rejected: '已拒绝',
  offline: '已下架',
  deleted: '已删除',
}

const formatDate = (d) => {
  if (!d) return '--'
  const dt = new Date(d)
  return dt.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const formatOrderAmount = (order, prefix = '') => {
  if (order?.payment_type === 'cash') {
    const amount = Number(order.cash_paid_yuan || 0).toFixed(2)
    return `${prefix}¥${amount}`
  }
  return `${prefix}${order?.price || 0} 积分`
}

const formatOrderStatus = (order) => {
  if (order?.is_physical && order.fulfillment_status === 'pending_shipment') return '待发货'
  const map = {
    completed: '已完成',
    paid: '已支付',
    paid_unverified: '待确认',
  }
  return map[order?.status] || order?.status || '--'
}

const confirmAction = () => {
  showConfirm.value = false
  if (confirmCallback) confirmCallback()
}

const showConfirmDialog = (title, msg, type, cb) => {
  confirmTitle.value = title
  confirmMsg.value = msg
  confirmType.value = type
  confirmCallback = cb
  showConfirm.value = true
}

const loadStats = async () => {
  const res = await adminGet('/admin/stats')
  if (res.code === 0) Object.assign(stats, res.data)
}

const loadUsers = async () => {
  const res = await adminGet('/admin/users', { keyword: userSearch.value, page: usersPage.value, page_size: ADMIN_PAGE_SIZE })
  if (res.code === 0) {
    users.value = res.data?.items || []
    usersTotalPages.value = res.data?.total_pages || 1
  }
}

const loadSkills = async () => {
  const res = await adminGet('/admin/skills', { status: skillStatusFilter.value, keyword: skillSearch.value, page: skillsPage.value, page_size: ADMIN_PAGE_SIZE })
  if (res.code === 0) {
    const totalPages = res.data?.total_pages || 1
    if (skillsPage.value > totalPages && totalPages > 0) {
      skillsPage.value = totalPages
      return loadSkills()
    }
    allSkills.value = res.data?.items || []
    skillsTotalPages.value = totalPages
    selectedSkillIds.value = []
  }
}

const toggleSkillSelection = (skillId) => {
  if (selectedSkillIds.value.includes(skillId)) {
    selectedSkillIds.value = selectedSkillIds.value.filter(id => id !== skillId)
  } else {
    selectedSkillIds.value = [...selectedSkillIds.value, skillId]
  }
}

const toggleSelectAllSkills = () => {
  if (allSkillsSelected.value) {
    selectedSkillIds.value = []
    return
  }
  selectedSkillIds.value = allSkills.value.map(skill => skill.id)
}

const executeSkillDeletion = async (skills) => {
  if (!skills.length) return { successCount: 0, failedSkills: [] }

  skillBatchDeleting.value = true
  const failedSkills = []
  let successCount = 0

  try {
    for (const skill of skills) {
      const res = await adminDel(`/admin/skills/${skill.id}`)
      if (res.code === 0) {
        successCount += 1
      } else {
        failedSkills.push({ id: skill.id, title: skill.title, message: res.message || '删除失败' })
      }
    }

    if (successCount > 0) {
      await Promise.all([loadSkills(), loadStats()])
    }
  } finally {
    skillBatchDeleting.value = false
  }

  return { successCount, failedSkills }
}

const loadPending = async () => {
  const res = await adminGet('/admin/skills/pending', { page_size: 50 })
  if (res.code === 0) pendingSkills.value = res.data?.items || []
}

const loadRejected = async () => {
  const res = await adminGet('/admin/skills', { status: 'rejected', page_size: 50 })
  if (res.code === 0) rejectedSkills.value = res.data?.items || []
}

const loadReviews = async () => {
  const res = await adminGet('/admin/reviews', { keyword: reviewSearch.value || undefined, page: reviewsPage.value, page_size: ADMIN_PAGE_SIZE })
  if (res.code === 0) {
    allReviews.value = res.data?.items || []
    reviewsTotalPages.value = res.data?.total_pages || 1
  }
}

const toggleBan = (user) => {
  const action = user.is_banned ? '解封' : '封禁'
  showConfirmDialog(`${action}用户`, `确定要${action}用户 "${user.nickname}"？`, 'warning', async () => {
    const res = await adminPut(`/admin/users/${user.id}`, { is_banned: !user.is_banned })
    if (res.code === 0) {
      user.is_banned = !user.is_banned
      toast.success(`用户已${action}。${KV_SYNC_HINT}`)
    }
  })
}

const setAdmin = (user) => {
  showConfirmDialog('设为管理员', `确定要将用户 "${user.nickname}" 设为管理员？`, 'warning', async () => {
    const res = await adminPut(`/admin/users/${user.id}`, { role: 'admin' })
    if (res.code === 0) {
      user.role = 'admin'
      toast.success('已设为管理员。' + KV_SYNC_HINT)
    }
  })
}

const viewUserOrders = async (user) => {
  ordersUser.value = user.nickname || user.username || `#${user.id}`
  ordersTab.value = 'purchases'
  orderData.purchases = []
  orderData.sales = []
  orderData.points_records = []
  showOrdersModal.value = true
  ordersLoading.value = true
  try {
    const res = await adminGet(`/admin/users/${user.id}/orders`)
    if (res.code === 0) {
      orderData.purchases = res.data.purchases || []
      orderData.sales = res.data.sales || []
      orderData.points_records = res.data.points_records || []
    }
  } catch (e) {
    toast.error('加载订单失败')
  }
  ordersLoading.value = false
}

const adminDeleteSkill = (skill) => {
  const isPhysical = skill.status === 'deleted'
  const title = isPhysical ? '物理删除商品' : '删除商品'
  const msg = isPhysical
    ? `确定要永久删除商品 "${skill.title}"？此操作不可撤销，数据将被彻底清除。`
    : `确定要删除商品 "${skill.title}"？此操作不可撤销。`
  showConfirmDialog(title, msg, 'danger', async () => {
    const { successCount, failedSkills } = await executeSkillDeletion([skill])
    if (successCount > 0) {
      toast.success((isPhysical ? '商品已永久删除。' : '商品已删除。') + KV_SYNC_HINT)
    }
    if (failedSkills.length > 0) {
      toast.error(failedSkills[0].message || '删除失败')
    }
  })
}

const batchDeleteSkills = () => {
  const skillsToDelete = allSkills.value.filter(skill => selectedSkillIds.value.includes(skill.id))
  if (!skillsToDelete.length) {
    toast.warning('请先选择要删除的商品')
    return
  }

  const previewTitles = skillsToDelete.slice(0, 3).map(skill => `「${skill.title}」`).join('、')
  const extraCount = skillsToDelete.length > 3 ? ` 等 ${skillsToDelete.length} 个商品` : ''
  showConfirmDialog(
    '一键删除商品',
    `确定要删除已选择的 ${skillsToDelete.length} 个商品吗？${previewTitles}${extraCount} 将逐个调用删除接口处理。`,
    'danger',
    async () => {
      const { successCount, failedSkills } = await executeSkillDeletion(skillsToDelete)
      if (successCount > 0) {
        toast.success(`已删除 ${successCount} 个商品。${KV_SYNC_HINT}`)
      }
      if (failedSkills.length > 0) {
        const failedPreview = failedSkills.slice(0, 3).map(skill => `「${skill.title}」`).join('、')
        toast.warning(`有 ${failedSkills.length} 个商品删除失败：${failedPreview}`)
      }
    }
  )
}

const auditSkill = async (skillId, result, reason = '', force = false) => {
  const res = await adminPost(`/admin/skills/${skillId}/audit`, { result, reason, force })
  if (res.code === 0) {
    toast.success((result === 'approved' ? (force ? '已强制上架' : '已通过审核') : '已拒绝') + '。' + KV_SYNC_HINT)
    loadPending()
    loadRejected()
    loadStats()
  }
}

const promptOfflineSkill = (skill) => {
  offlineSkillId.value = skill.id
  offlineSkillTitle.value = skill.title
  offlineReason.value = ''
  showOfflineModal.value = true
}

const confirmOfflineSkill = async () => {
  if (!offlineReason.value.trim()) {
    toast.error('请填写下架原因')
    return
  }
  const res = await adminPost(`/admin/skills/${offlineSkillId.value}/offline`, { reason: offlineReason.value.trim() })
  if (res.code === 0) {
    toast.success('商品已下架。' + KV_SYNC_HINT)
    showOfflineModal.value = false
    loadSkills()
    loadStats()
  }
}

const deleteReview = (review) => {
  showConfirmDialog('删除评论', '确定要删除这条评论？', 'danger', async () => {
    const res = await adminDel(`/admin/reviews/${review.id}`)
    if (res.code === 0) {
      allReviews.value = allReviews.value.filter(r => r.id !== review.id)
      toast.success('评论已删除。' + KV_SYNC_HINT)
    }
  })
}

const loadWithdrawals = async () => {
  const res = await adminGet('/admin/withdrawals', { status: wdStatusFilter.value, keyword: wdSearch.value || undefined, page: wdPage.value, page_size: ADMIN_PAGE_SIZE })
  if (res.code === 0) {
    adminWithdrawals.value = res.data?.items || []
    wdTotalPages.value = res.data?.total_pages || 1
    pendingWdCount.value = adminWithdrawals.value.filter(w => w.status === 'pending').length
  }
}

const loadAllOrders = async () => {
  ordersAdminLoading.value = true
  try {
    const res = await adminGet('/admin/orders', { keyword: orderSearch.value || undefined, page: ordersAdminPage.value, page_size: ADMIN_PAGE_SIZE })
    if (res.code === 0) {
      allOrders.value = res.data?.items || []
      ordersAdminTotalPages.value = res.data?.total_pages || 1
    }
  } finally {
    ordersAdminLoading.value = false
  }
}

const completeWithdrawal = (wd) => {
  showConfirmDialog('确认完成转账', `确认已向 ${wd.alipay_name}（${wd.alipay_account}）转账 ${wd.amount} 积分对应金额？将自动扣减用户积分。`, 'warning', async () => {
    const res = await adminPost(`/admin/withdrawals/${wd.id}/complete`)
    if (res.code === 0) {
      toast.success('提现已完成，积分已扣减。' + KV_SYNC_HINT)
      loadWithdrawals()
    } else {
      toast.error(res.message || '操作失败')
    }
  })
}

const rejectWithdrawal = (wd) => {
  rejectWdId.value = wd.id
  rejectWdUser.value = wd.user_name
  rejectWdReason.value = ''
  showRejectWdModal.value = true
}

const confirmRejectWithdrawal = async () => {
  if (!rejectWdReason.value.trim()) {
    toast.error('请填写拒绝原因')
    return
  }
  const res = await adminPost(`/admin/withdrawals/${rejectWdId.value}/reject`, { reason: rejectWdReason.value.trim() })
  if (res.code === 0) {
    toast.success('已拒绝提现。' + KV_SYNC_HINT)
    showRejectWdModal.value = false
    loadWithdrawals()
  }
}

const loadRecharges = async () => {
  const res = await adminGet('/admin/recharges', { status: rechargeStatusFilter.value, keyword: rechargeSearch.value || undefined, page: rechargePage.value, page_size: ADMIN_PAGE_SIZE })
  if (res.code === 0) {
    adminRecharges.value = res.data?.items || []
    rechargeTotalPages.value = res.data?.total_pages || 1
    pendingRechargeCount.value = adminRecharges.value.filter(r => r.status === 'pending').length
  }
}

const confirmRecharge = (order) => {
  showConfirmDialog('确认充值到账', `确认订单 ${order.id} 已支付？将为用户充值 ${order.points_amount} 积分。`, 'warning', async () => {
    const res = await adminPost(`/admin/recharges/${order.id}/confirm`)
    if (res.code === 0) {
      toast.success('充值已确认，积分已到账。' + KV_SYNC_HINT)
      loadRecharges()
    } else {
      toast.error(res.message || '操作失败')
    }
  })
}

const cancelRecharge = (order) => {
  showConfirmDialog('取消充值订单', `确认取消订单 ${order.id}？`, 'warning', async () => {
    const res = await adminPost(`/admin/recharges/${order.id}/cancel`)
    if (res.code === 0) {
      toast.success('订单已取消。' + KV_SYNC_HINT)
      loadRecharges()
    } else {
      toast.error(res.message || '操作失败')
    }
  })
}

const saveSettings = async () => {
  const res = await adminPut('/admin/settings', { ...siteSettings })
  if (res.code === 0) {
    toast.success('设置已保存。' + KV_SYNC_HINT)
  } else {
    toast.error('保存失败')
  }
}

const handleRebuildAggregate = async () => {
  rebuildAggregateLoading.value = true
  rebuildAggregateResult.value = ''
  try {
    const res = await adminPost('/admin/skills/rebuild-aggregate')
    if (res.code === 0 && res.data) {
      rebuildAggregateResult.value = res.message || `已重建 ${res.data.count} 条商品分片缓存`
      toast.success(rebuildAggregateResult.value, '重建完成')
    } else {
      toast.error(res.message || '失败', '重建失败')
    }
  } catch (e) {
    toast.error('网络错误', '重建失败')
  } finally {
    rebuildAggregateLoading.value = false
  }
}

const loadSettings = async () => {
  const res = await adminGet('/admin/settings')
  if (res.code === 0 && res.data) {
    Object.assign(siteSettings, res.data)
  }
}

const handleRebuildTitleIndexes = async () => {
  rebuildIndexError.value = ''
  rebuildIndexSummary.value = null
  rebuildIndexLoading.value = true
  try {
    const res = await adminPost('/admin/skills/rebuild-title-indexes')
    if (res.code === 0 && res.data) {
      rebuildIndexSummary.value = res.data
      const conflictCount = Number(res.data.conflict_count || 0)
      const rebuiltCount = Number(res.data.rebuilt_indexes || 0)
      if (conflictCount > 0) {
        toast.warning(`标题索引已重建 ${rebuiltCount} 条，发现 ${conflictCount} 组同状态重名商品，请在下方处理。`, '重建完成')
      } else {
        toast.success(`标题索引已重建 ${rebuiltCount} 条。`, '重建完成')
      }
    } else {
      rebuildIndexError.value = res.message || '标题索引重建失败'
      toast.error(rebuildIndexError.value, '重建失败')
    }
  } catch (e) {
    rebuildIndexError.value = '网络错误，请稍后重试'
    toast.error(rebuildIndexError.value, '重建失败')
  } finally {
    rebuildIndexLoading.value = false
  }
}

// Backup & Restore handlers
const handleBackup = async () => {
  backupError.value = ''
  backupProgress.value = ''
  backupLoading.value = true
  try {
    // Step 1: 获取键列表（秒级完成）
    backupProgress.value = '正在枚举数据键...'
    const keysRes = await adminPost('/admin/backup', {})
    if (keysRes.code !== 0 || !keysRes.data) {
      backupError.value = keysRes.message || '获取键列表失败'
      return
    }
    const allKeys = keysRes.data.keys || []
    const total = allKeys.length
    if (total === 0) {
      toast.warning('备份完成，但无数据可导出（KV 中可能没有任何数据）')
      return
    }

    // Step 2: 分批获取值
    const CHUNK_SIZE = 50
    const allData = {}
    let fetched = 0
    let errors = 0
    for (let i = 0; i < total; i += CHUNK_SIZE) {
      const chunkKeys = allKeys.slice(i, i + CHUNK_SIZE)
      backupProgress.value = `正在读取数据... ${fetched}/${total} (${Math.round(fetched / total * 100)}%)`
      try {
        const chunkRes = await adminPost('/admin/backup/chunk', { keys: chunkKeys })
        if (chunkRes.code === 0 && chunkRes.data && chunkRes.data.data) {
          for (const [k, v] of Object.entries(chunkRes.data.data)) {
            allData[k] = v
          }
        } else {
          errors++
        }
      } catch (e) {
        errors++
      }
      fetched += chunkKeys.length
    }

    backupProgress.value = `正在打包 ZIP...`
    const dataCount = Object.keys(allData).length
    if (dataCount === 0) {
      backupError.value = '所有 KV 键值读取为空，请重试'
      toast.error('备份失败，无数据')
      return
    }

    // Step 3: 按分类组织数据
    const CATEGORY_RULES = [
      ['users',       /^user[_:]/],
      ['skills',      /^skill[_:]/],
      ['skills',      /^si[_:]/],
      ['skills',      /^sv[_:]/],
      ['categories',  /^cat[_:]/],
      ['settings',    /^site[_:]/],
      ['orders',      /^(order[_:]|recharge[_:])/],
      ['messages',    /^msg[_:]/],
      ['reviews',     /^review[_:]/],
      ['favorites',   /^fav[_:]/],
      ['tokens',      /^token[_:]/],
      ['purchases',   /^purchase[_:]/],
      ['points',      /^pr[_:]/],
      ['withdrawals', /^wd[_:]/],
      ['social',      /^follow[_:]/],
      ['audits',      /^audit[_:]/],
    ]
    function categorize(key) {
      const k = key.replace(/:/g, '_')
      for (const [cat, re] of CATEGORY_RULES) {
        if (re.test(k)) return cat
      }
      return 'other'
    }

    const categorized = {}
    for (const [key, value] of Object.entries(allData)) {
      const cat = categorize(key)
      if (!categorized[cat]) categorized[cat] = {}
      categorized[cat][key] = value
    }

    // Step 4: 创建 ZIP（使用已有的简易 ZIP 创建方式）
    // 使用 Blob 直接拼装简易非压缩 ZIP
    const files = []
    for (const [catName, catData] of Object.entries(categorized)) {
      const json = JSON.stringify(catData, null, 2)
      files.push({ name: `${catName}.json`, content: json })
    }
    // Add metadata
    const meta = {
      created_at: new Date().toISOString(),
      total_keys: dataCount,
      categories: Object.fromEntries(Object.entries(categorized).map(([k, v]) => [k, Object.keys(v).length])),
    }
    files.push({ name: '_meta.json', content: JSON.stringify(meta, null, 2) })

    // Build ZIP file (STORE method, no compression needed for JSON)
    const zipBlob = buildSimpleZip(files)
    const url = URL.createObjectURL(zipBlob)
    const a = document.createElement('a')
    a.href = url
    a.download = `EdgeOneMall-backup-${new Date().toISOString().slice(0, 10)}.zip`
    a.click()
    URL.revokeObjectURL(url)

    const summary = Object.entries(categorized).map(([k, v]) => `${k}: ${Object.keys(v).length}`).join(', ')
    if (errors > 0) {
      toast.success(`备份部分成功，共 ${dataCount} 条数据（${summary}），${errors} 个批次出错`)
    } else {
      toast.success(`备份成功，共 ${dataCount} 条数据（${summary}）`)
    }
  } catch (e) {
    backupError.value = '网络错误: ' + (e.message || e)
  } finally {
    backupLoading.value = false
    backupProgress.value = ''
  }
}

// 简易 ZIP 文件创建（STORE 模式，无压缩）
function buildSimpleZip(files) {
  const encoder = new TextEncoder()
  const entries = files.map(f => ({ name: encoder.encode(f.name), data: encoder.encode(f.content) }))
  // Calculate sizes
  let offset = 0
  const localHeaders = []
  const centralHeaders = []
  for (const entry of entries) {
    const localHeader = new ArrayBuffer(30 + entry.name.length)
    const lv = new DataView(localHeader)
    lv.setUint32(0, 0x04034b50, true) // local file header signature
    lv.setUint16(4, 20, true) // version needed
    lv.setUint16(6, 0, true) // flags
    lv.setUint16(8, 0, true) // compression (STORE)
    lv.setUint16(10, 0, true) // mod time
    lv.setUint16(12, 0, true) // mod date
    // CRC-32
    const crc = crc32(entry.data)
    lv.setUint32(14, crc, true)
    lv.setUint32(18, entry.data.length, true) // compressed size
    lv.setUint32(22, entry.data.length, true) // uncompressed size
    lv.setUint16(26, entry.name.length, true) // name length
    lv.setUint16(28, 0, true) // extra length
    new Uint8Array(localHeader, 30).set(entry.name)
    localHeaders.push(new Uint8Array(localHeader))

    // Central directory header
    const centralHeader = new ArrayBuffer(46 + entry.name.length)
    const cv = new DataView(centralHeader)
    cv.setUint32(0, 0x02014b50, true) // central dir signature
    cv.setUint16(4, 20, true) // version made by
    cv.setUint16(6, 20, true) // version needed
    cv.setUint16(8, 0, true) // flags
    cv.setUint16(10, 0, true) // compression
    cv.setUint16(12, 0, true) // mod time
    cv.setUint16(14, 0, true) // mod date
    cv.setUint32(16, crc, true)
    cv.setUint32(20, entry.data.length, true)
    cv.setUint32(24, entry.data.length, true)
    cv.setUint16(28, entry.name.length, true)
    cv.setUint16(30, 0, true) // extra length
    cv.setUint16(32, 0, true) // comment length
    cv.setUint16(34, 0, true) // disk number
    cv.setUint16(36, 0, true) // internal attr
    cv.setUint32(38, 0, true) // external attr
    cv.setUint32(42, offset, true) // local header offset
    new Uint8Array(centralHeader, 46).set(entry.name)
    centralHeaders.push(new Uint8Array(centralHeader))

    offset += 30 + entry.name.length + entry.data.length
  }

  // End of central directory
  const centralDirOffset = offset
  let centralDirSize = 0
  for (const ch of centralHeaders) centralDirSize += ch.length
  const endRecord = new ArrayBuffer(22)
  const ev = new DataView(endRecord)
  ev.setUint32(0, 0x06054b50, true)
  ev.setUint16(4, 0, true)
  ev.setUint16(6, 0, true)
  ev.setUint16(8, entries.length, true)
  ev.setUint16(10, entries.length, true)
  ev.setUint32(12, centralDirSize, true)
  ev.setUint32(16, centralDirOffset, true)
  ev.setUint16(20, 0, true)

  // Assemble
  const parts = []
  for (let i = 0; i < entries.length; i++) {
    parts.push(localHeaders[i])
    parts.push(entries[i].data)
  }
  for (const ch of centralHeaders) parts.push(ch)
  parts.push(new Uint8Array(endRecord))
  return new Blob(parts, { type: 'application/zip' })
}

// CRC-32 lookup table
const crc32Table = (() => {
  const t = new Uint32Array(256)
  for (let i = 0; i < 256; i++) {
    let c = i
    for (let j = 0; j < 8; j++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1)
    t[i] = c
  }
  return t
})()
function crc32(data) {
  let crc = 0xFFFFFFFF
  for (let i = 0; i < data.length; i++) crc = crc32Table[(crc ^ data[i]) & 0xFF] ^ (crc >>> 8)
  return (crc ^ 0xFFFFFFFF) >>> 0
}

// Minimal ZIP reader (handles flat ZIP files with DEFLATE or STORED entries)
async function parseZipEntries(arrayBuffer) {
  const view = new DataView(arrayBuffer)
  const entries = {}
  let offset = 0
  const bytes = new Uint8Array(arrayBuffer)

  while (offset < bytes.length - 4) {
    const sig = view.getUint32(offset, true)
    if (sig !== 0x04034b50) break // Not a local file header

    const compressionMethod = view.getUint16(offset + 8, true)
    const compressedSize = view.getUint32(offset + 18, true)
    const uncompressedSize = view.getUint32(offset + 22, true)
    const nameLen = view.getUint16(offset + 26, true)
    const extraLen = view.getUint16(offset + 28, true)
    const nameBytes = bytes.slice(offset + 30, offset + 30 + nameLen)
    const fileName = new TextDecoder().decode(nameBytes)
    const dataStart = offset + 30 + nameLen + extraLen

    let fileData
    if (compressionMethod === 0) {
      // STORED
      fileData = bytes.slice(dataStart, dataStart + compressedSize)
    } else if (compressionMethod === 8) {
      // DEFLATE — use DecompressionStream
      const compressed = bytes.slice(dataStart, dataStart + compressedSize)
      const ds = new DecompressionStream('deflate-raw')
      const writer = ds.writable.getWriter()
      writer.write(compressed)
      writer.close()
      const reader = ds.readable.getReader()
      const chunks = []
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        chunks.push(value)
      }
      const totalLen = chunks.reduce((a, c) => a + c.length, 0)
      fileData = new Uint8Array(totalLen)
      let pos = 0
      for (const chunk of chunks) {
        fileData.set(chunk, pos)
        pos += chunk.length
      }
    } else {
      offset = dataStart + compressedSize
      continue
    }

    if (fileName.endsWith('.json')) {
      const text = new TextDecoder().decode(fileData)
      try {
        entries[fileName.replace('.json', '')] = JSON.parse(text)
      } catch { /* skip invalid json */ }
    }
    offset = dataStart + compressedSize
  }
  return entries
}

const handleRestoreFile = async (e) => {
  restoreError.value = ''
  restoreCategories.value = []
  restoreData.value = null

  const file = e.target.files?.[0]
  if (!file) return

  if (file.name.endsWith('.zip')) {
    // Parse ZIP and extract categories
    try {
      const buf = await file.arrayBuffer()
      const entries = await parseZipEntries(buf)
      const cats = []
      for (const [name, data] of Object.entries(entries)) {
        if (name === '_meta') continue
        const count = typeof data === 'object' ? Object.keys(data).length : 0
        cats.push({
          name,
          label: CATEGORY_LABELS[name] || name,
          count,
          data,
          selected: true,
        })
      }
      if (cats.length === 0) {
        restoreError.value = 'ZIP 内无有效的 JSON 分类文件'
        return
      }
      restoreCategories.value = cats
    } catch (err) {
      restoreError.value = 'ZIP 文件解析失败: ' + err.message
    }
  } else {
    // Single JSON file
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result)
        restoreData.value = parsed
        restoreError.value = ''
      } catch {
        restoreError.value = '文件格式错误，请选择有效的 JSON 备份文件'
        restoreData.value = null
      }
    }
    reader.readAsText(file)
  }
}

const handleRestore = async () => {
  restoreError.value = ''
  restoreSuccess.value = ''
  restoreLoading.value = true
  try {
    // Build flat KV data from selection
    let data = {}
    if (restoreCategories.value.length > 0) {
      // ZIP mode: merge selected categories
      for (const cat of restoreCategories.value) {
        if (cat.selected && cat.data) {
          Object.assign(data, cat.data)
        }
      }
    } else if (restoreData.value) {
      data = restoreData.value
    }

    if (Object.keys(data).length === 0) {
      restoreError.value = '没有选择要恢复的数据'
      restoreLoading.value = false
      return
    }

    const res = await adminPost('/admin/restore', { data })
    if (res.code === 0) {
      restoreSuccess.value = `恢复成功，共恢复 ${res.data.restored_keys} 条数据。${KV_SYNC_HINT}`
      restoreData.value = null
      restoreCategories.value = []
      toast.success('数据恢复成功。' + KV_SYNC_HINT)
    } else {
      restoreError.value = res.message || '恢复失败'
    }
  } catch (e) {
    restoreError.value = '网络错误'
  } finally {
    restoreLoading.value = false
  }
}

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    toast.error('请先登录')
    router.push('/login')
    return
  }
  const res = await adminGet('/admin/stats')
  if (res.code === 0) {
    adminVerified.value = true
    stats.skills_total = res.data?.skills_total || 0
    stats.skills_pending = res.data?.skills_pending || 0
    stats.skills_approved = res.data?.skills_approved || 0
    stats.user_count = res.data?.user_count || 0
    loadSettings()
  } else {
    toast.error(res.message || '需要管理员权限')
    router.push('/')
  }
})

</script>

<style scoped>
.admin-container { padding: 40px 24px 100px; max-width: 1280px; }

.admin-header {
  padding: 32px 40px;
  margin-bottom: 24px;
}
.admin-header h1 { font-size: 28px; font-weight: 800; margin-bottom: 4px; }
.admin-subtitle { color: var(--text-secondary); font-size: 14px; }

.admin-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 24px;
  align-items: start;
}

.admin-sidebar { padding: 12px 0; align-self: start; position: sticky; top: 96px; }

.admin-menu {
  list-style: none;
  padding: 0;
  margin: 0;
}

.admin-menu li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-smooth);
  position: relative;
}

.admin-menu li:hover { background: var(--bg-surface-hover); color: var(--text-primary); }
.admin-menu li.active {
  color: var(--color-primary);
  background: rgba(30, 224, 127, 0.06);
  border-right: 3px solid var(--color-primary);
}

.admin-menu .badge {
  position: absolute;
  right: 16px;
  background: var(--color-danger);
  color: white;
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 99px;
  font-weight: 700;
}

.admin-content { padding: 32px; min-height: 500px; }

.panel-section h2 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 24px;
  color: var(--text-primary);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-box {
  padding: 24px;
  border: 1px solid var(--border-glass);
  border-radius: 12px;
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
}

.stat-box.accent { border-color: rgba(255, 149, 0, 0.3); background: rgba(255, 149, 0, 0.05); }
.stat-box.success { border-color: rgba(52, 199, 89, 0.3); background: rgba(52, 199, 89, 0.05); }

.stat-num {
  font-size: 36px;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.stat-lbl {
  font-size: 13px;
  color: var(--text-tertiary);
}

/* Toolbar */
.panel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}

.panel-toolbar h2 { margin-bottom: 0; }

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-right {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.selection-hint {
  font-size: 13px;
  color: var(--text-tertiary);
}

.search-input {
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 8px 14px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: var(--transition-smooth);
  width: 200px;
}

.search-input:focus { border-color: var(--color-primary); }

.filter-select {
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 8px 14px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  cursor: pointer;
}

/* Data Table */
.data-table-wrap { overflow-x: auto; }

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  text-align: left;
  padding: 10px 12px;
  color: var(--text-tertiary);
  font-weight: 500;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-glass);
}

.data-table td {
  padding: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
}

.checkbox-cell {
  width: 42px;
  text-align: center !important;
}

.checkbox-cell input {
  width: 14px;
  height: 14px;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.data-table tr:hover td { background: rgba(255, 255, 255, 0.02); }

.title-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary); font-weight: 500; }
.content-cell { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.role-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}
.role-tag.admin { background: rgba(255, 149, 0, 0.15); color: #FF9500; }
.role-tag.user { background: rgba(255, 255, 255, 0.06); color: var(--text-tertiary); }

.status-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}
.status-tag.approved { background: rgba(52, 199, 89, 0.15); color: #34C759; }
.status-tag.pending { background: rgba(255, 149, 0, 0.15); color: #FF9500; }
.status-tag.rejected { background: rgba(255, 69, 58, 0.15); color: #FF453A; }
.status-tag.offline { background: rgba(255, 255, 255, 0.06); color: var(--text-tertiary); }
.status-tag.deleted { background: rgba(142, 142, 147, 0.15); color: #8E8E93; text-decoration: line-through; }
.status-tag.completed, .status-tag.paid { background: rgba(52, 199, 89, 0.15); color: #34C759; }
.status-tag.paid_unverified { background: rgba(255, 149, 0, 0.15); color: #FF9500; }

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}
.status-dot.active { background: #34C759; }
.status-dot.banned { background: #FF453A; }

.btn-sm-action {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-glass);
  color: var(--text-secondary);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: var(--transition-smooth);
  margin-right: 4px;
}
.btn-sm-action:hover { background: rgba(255, 255, 255, 0.1); color: var(--text-primary); }
.btn-sm-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn-sm-action.danger { color: #FF453A; }
.btn-sm-action.danger:hover { background: rgba(255, 69, 58, 0.1); }
.btn-sm-action.warning { color: #FF9F0A; }
.btn-sm-action.warning:hover { background: rgba(255, 159, 10, 0.1); }

.wd-amount-cell { font-weight: 600; color: var(--color-primary); }
.text-muted { color: var(--text-tertiary); font-size: 13px; }

.empty-msg {
  text-align: center;
  padding: 40px;
  color: var(--text-tertiary);
  font-size: 14px;
}

.admin-pagination {
  display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 20px; padding-top: 16px;
  border-top: 1px solid var(--border-glass);
}
.admin-pagination .page-btn {
  background: var(--bg-glass); border: 1px solid var(--border-glass); color: var(--text-primary);
  padding: 6px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; transition: var(--transition-smooth);
}
.admin-pagination .page-btn:hover:not(:disabled) { background: var(--bg-surface-hover); border-color: var(--color-primary); }
.admin-pagination .page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.admin-pagination .page-info { font-size: 13px; color: var(--text-secondary); }

.order-no-text { font-family: monospace; font-size: 12px; color: var(--text-secondary); word-break: break-all; }
.shipping-cell { display: flex; flex-direction: column; gap: 4px; max-width: 220px; color: var(--text-secondary); font-size: 12px; line-height: 1.4; }

/* Audit Cards */
.audit-list { display: flex; flex-direction: column; gap: 12px; }

.audit-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
}

.audit-info h3 { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.audit-info p { font-size: 13px; color: var(--text-tertiary); }

.audit-actions { display: flex; gap: 8px; }

.rejected-card { border-color: rgba(255, 69, 58, 0.3); }

.btn-warning { background: rgba(255, 159, 10, 0.15); color: #FF9F0A; border: 1px solid rgba(255, 159, 10, 0.3); }
.btn-warning:hover { background: rgba(255, 159, 10, 0.25); }

.offline-reason-input {
  width: 100%; padding: 12px; border-radius: 10px;
  background: var(--bg-glass); border: 1px solid var(--border-glass);
  color: var(--text-primary); font-size: 14px; resize: vertical;
  margin: 12px 0;
}

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px); display: flex; align-items: center;
  justify-content: center; z-index: 10000;
}
.modal-dialog { width: 100%; max-width: 420px; padding: 36px; border-radius: 20px; text-align: center; }
.modal-dialog.modal-wide { max-width: 640px; text-align: left; max-height: 80vh; overflow-y: auto; }
.modal-title { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
.modal-message { font-size: 14px; color: var(--text-secondary); margin-bottom: 8px; }
.modal-actions { display: flex; gap: 12px; justify-content: center; margin-top: 16px; }
.btn-danger-solid { background: #FF453A; color: #fff; border: none; }

/* Orders modal */
.orders-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.orders-tabs span {
  padding: 6px 14px; border-radius: 10px; font-size: 13px; cursor: pointer;
  background: rgba(255,255,255,0.03); border: 1px solid var(--border-glass);
  color: var(--text-secondary); transition: all 0.2s;
}
.orders-tabs span.active { background: rgba(30,224,127,0.1); border-color: var(--color-primary); color: var(--color-primary); }
.orders-list { display: flex; flex-direction: column; gap: 8px; }
.order-item { padding: 12px 16px; border-radius: 12px; }
.order-main { display: flex; justify-content: space-between; align-items: center; }
.order-title { font-size: 14px; color: var(--text-primary); font-weight: 500; }
.order-price { font-size: 14px; font-weight: 600; color: #FF453A; flex-shrink: 0; }
.order-sub { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }
.order-detail { margin-top: 6px; color: var(--text-secondary); font-size: 12px; line-height: 1.5; }

/* Settings */
.setting-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}
.setting-tabs span {
  padding: 8px 16px;
  border-radius: 12px;
  font-size: 14px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-glass);
  color: var(--text-secondary);
  transition: all 0.2s;
}
.setting-tabs span:hover {
  background: rgba(255, 255, 255, 0.06);
}
.setting-tabs span.active {
  background: rgba(30, 224, 127, 0.1);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.setting-card { padding: 24px; }
.setting-card h3 { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: var(--text-primary); }

.setting-group {
  margin-bottom: 16px;
}

.setting-group label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.setting-group .form-control {
  width: 100%;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 10px 14px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: var(--transition-smooth);
  font-family: inherit;
}

.setting-group .form-control:focus { border-color: var(--color-primary); }
.setting-group textarea.form-control { resize: vertical; }

.toggle-label {
  display: flex !important;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 500;
  color: var(--text-primary) !important;
}
.toggle-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
}
.setting-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
  line-height: 1.5;
}
.setting-hint code {
  background: rgba(255,255,255,0.06);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 11px;
}

.settings-actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .admin-layout { grid-template-columns: 1fr; }
  .admin-sidebar { position: static; }
  .admin-menu { display: flex; overflow-x: auto; gap: 0; }
  .admin-menu li {
    padding: 10px 14px;
    white-space: nowrap;
    font-size: 13px;
    border-right: none;
    border-bottom: 2px solid transparent;
  }
  .admin-menu li.active {
    border-right: none;
    border-bottom: 2px solid var(--color-primary);
  }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .settings-grid { grid-template-columns: 1fr; }
  .panel-toolbar { flex-direction: column; align-items: stretch; }
  .toolbar-right { flex-wrap: wrap; }
  .search-input { width: 100%; }
  .audit-card { flex-direction: column; gap: 12px; align-items: flex-start; }
}

/* 管理员验证门 */
.admin-gate {
  max-width: 400px;
  margin: 120px auto;
  padding: 40px;
  text-align: center;
}
.admin-gate h2 { font-size: 24px; margin-bottom: 8px; }
.admin-gate p { color: var(--text-secondary); margin-bottom: 24px; font-size: 14px; }
.gate-form { display: flex; flex-direction: column; gap: 16px; }
.gate-form .form-control { text-align: center; font-size: 16px; }
.gate-error { color: #ef4444; font-size: 13px; margin: -8px 0 0; }
</style>
