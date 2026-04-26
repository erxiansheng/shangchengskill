/**
 * EdgeOne Pages Edge Function — API 路由器
 *
 * 目录: edge-functions/api/[[default]].js
 * 路由: 匹配所有 /api/* 请求
 *
 * /_internal/kv  → KV 代理（供 Cloud Function 调用）
 * 公开 GET 请求  → 直接从 MY_KV 读取返回（边缘处理，快速）
 * 其他请求       → fetch() 转发到 Cloud Function (/fn/...)
 */

const DEFAULT_INTERNAL_KEY = 'EdgeOneMall_internal_2026';

// 运行时从 env 注入（参见 onRequest 入口）。
// 不要在这里硬编码 secret——生产环境一定走 env。
let INTERNAL_KEY = DEFAULT_INTERNAL_KEY;
let JWT_SECRET = '';

// ─── 工具函数 ───

function base64UrlDecode(str) {
  str = str.replace(/-/g, '+').replace(/_/g, '/');
  while (str.length % 4) str += '=';
  const binary = atob(str);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function verifyJwt(token) {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(new TextDecoder().decode(base64UrlDecode(parts[1])));
    if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) return null;
    if (payload.type !== 'access') return null;

    const key = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(JWT_SECRET),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['verify']
    );
    const sigValid = await crypto.subtle.verify(
      'HMAC',
      key,
      base64UrlDecode(parts[2]),
      new TextEncoder().encode(parts[0] + '.' + parts[1])
    );
    return sigValid ? payload : null;
  } catch {
    return null;
  }
}

async function getAuthUser(request) {
  const auth = request.headers.get('Authorization');
  if (!auth || !auth.startsWith('Bearer ')) return null;
  const payload = await verifyJwt(auth.slice(7));
  if (!payload || !payload.sub) return null;
  const userId = parseInt(payload.sub);
  const user = await kvGet(`user:${userId}`);
  return user && !user.is_banned && user.status !== 'banned' ? user : null;
}

function sanitizeKey(key) {
  if (!key || typeof key !== 'string') return '_invalid_';
  return key.replace(/[^a-zA-Z0-9_]/g, '_');
}

function ts() {
  return Math.floor(Date.now() / 1000);
}

function ok(data, message = 'success') {
  return jsonResp({ code: 0, message, data, timestamp: ts() });
}

function paginated(items, total, page, pageSize) {
  const totalPages = Math.ceil(total / pageSize) || 0;
  return ok({ items, total, page, page_size: pageSize, total_pages: totalPages });
}

function errResponse(code, message, status = 400) {
  return jsonResp({ code, message, data: null, timestamp: ts() }, status);
}

function jsonResp(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=UTF-8',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Token, X-Internal-Key, X-Admin-Password',
    },
  });
}

// ─── KV 读写辅助 ───

// Edge worker 内存缓存（单个请求生命周期内有效，不跨请求）
// EdgeOne 的 edge function 是长驻进程，可跨请求缓存
const _cache = new Map();
const CACHE_TTL = 120_000; // 120 秒内存缓存（原 30s）

// 技能列表查询缓存（按筛选条件缓存完整排序结果，分页时直接切片）
const _skillsQueryCache = new Map();
const SKILLS_QUERY_TTL = 120_000; // 120 秒（原 20s）
const SKILLS_QUERY_CACHE_MAX = 200;

// 聚合 KV 缓存：分片存储，支持 5 万条数据上限
const SHARD_COUNT = 10;
const SHARD_PREFIX = 'skill_listdata_s';
const LISTDATA_KEY = 'skill_approved_listdata'; // 兼容旧缓存
const LISTDATA_MAX_AGE = 300;

// 注册去重锁：防止同一 openid 在 KV 写入传播前被并发注册
// key: openid/unionid, value: timestamp; 5秒后自动过期
const _registerLock = new Map();
const REGISTER_LOCK_TTL = 5_000;

// 积分余额计算缓存（避免每次请求重新加载全量 PR 记录）
const _balanceCache = new Map();
const BALANCE_CACHE_TTL = 60_000; // 60 秒

// 用户消息列表缓存（避免 type 过滤时重复加载全量消息）
const _msgListCache = new Map();
const MSG_LIST_CACHE_TTL = 30_000; // 30 秒

async function cachedKvGet(key) {
  const now = Date.now();
  const cached = _cache.get(key);
  if (cached && now - cached.ts < CACHE_TTL) return cached.val;
  const val = await kvGet(key);
  _cache.set(key, { val, ts: now });
  return val;
}

async function cachedKvGetList(key) {
  const val = await cachedKvGet(key);
  return Array.isArray(val) ? val : [];
}

async function cachedKvBatchGet(keys) {
  const now = Date.now();
  const results = [];
  const missing = [];
  const missingIdx = [];

  for (let i = 0; i < keys.length; i++) {
    const cached = _cache.get(keys[i]);
    if (cached && now - cached.ts < CACHE_TTL) {
      results[i] = cached.val;
    } else {
      missing.push(keys[i]);
      missingIdx.push(i);
    }
  }

  if (missing.length > 0) {
    const fetched = await kvBatchGet(missing);
    for (let j = 0; j < fetched.length; j++) {
      results[missingIdx[j]] = fetched[j];
      _cache.set(missing[j], { val: fetched[j], ts: now });
    }
  }

  return results;
}

async function kvGet(key) {
  const sk = sanitizeKey(key);
  try {
    return await MY_KV.get(sk, { type: 'json' });
  } catch {
    return null;
  }
}

// 强制回源读取，跳过 EdgeOne 边缘缓存（用于注册等需要强一致性的场景）
async function kvGetFresh(key) {
  const sk = sanitizeKey(key);
  try {
    return await MY_KV.get(sk, { type: 'json', cacheTtl: 60 });
  } catch {
    return null;
  }
}

async function kvPut(key, value) {
  const sk = sanitizeKey(key);
  await MY_KV.put(sk, JSON.stringify(value));
}

async function kvDelete(key) {
  const sk = sanitizeKey(key);
  await MY_KV.delete(sk);
}

async function kvGetList(key) {
  const val = await kvGet(key);
  return Array.isArray(val) ? val : [];
}

async function kvBatchGet(keys) {
  const results = new Array(keys.length);
  const CONCURRENCY = 200;
  for (let i = 0; i < keys.length; i += CONCURRENCY) {
    const batch = keys.slice(i, i + CONCURRENCY);
    const batchResults = await Promise.all(batch.map(k => kvGet(k)));
    for (let j = 0; j < batchResults.length; j++) {
      results[i + j] = batchResults[j];
    }
  }
  return results;
}

// ─── 聚合缓存：分片存储 + 增量更新，支持 5 万条数据 ───

function skillShardIndex(skillId) {
  let h = 0;
  for (let i = 0; i < skillId.length; i++) h = ((h << 5) - h + skillId.charCodeAt(i)) | 0;
  return Math.abs(h) % SHARD_COUNT;
}

function extractListingFields(s) {
  return {
    id: s.id, title: s.title, subtitle: s.subtitle || '',
    price: s.price, is_free: !!s.is_free,
    cover_image: s.cover_image || null,
    version: s.version || '1.0.0',
    avg_rating: s.avg_rating || 0,
    review_count: s.review_count || 0,
    download_count: s.download_count || 0,
    purchase_count: s.purchase_count || 0,
    favorite_count: s.favorite_count || 0,
    tags: s.tags || [],
    category_id: s.category_id,
    user_id: s.user_id,
    status: s.status,
    created_at: s.created_at || null,
  };
}

async function getApprovedSkillsAggregate() {
  // 并行读取所有分片（10 次 KV 读取）
  const shardKeys = Array.from({ length: SHARD_COUNT }, (_, i) => `${SHARD_PREFIX}${i}`);
  const shards = await cachedKvBatchGet(shardKeys);
  let allSkills = [];
  let hasData = false;
  for (const shard of shards) {
    if (Array.isArray(shard) && shard.length) {
      allSkills = allSkills.concat(shard);
      hasData = true;
    }
  }
  if (hasData) return allSkills;

  // 兼容旧的单条聚合缓存
  const oldData = await cachedKvGet(LISTDATA_KEY);
  if (oldData && oldData.ts && (ts() - oldData.ts) < LISTDATA_MAX_AGE) {
    // 迁移到分片
    _migrateToShards(oldData.skills);
    return oldData.skills;
  }

  // 冷启动：逐条读取并分片存储
  const skillIds = await cachedKvGetList('skill:by_status:approved');
  if (!skillIds.length) return [];
  const rawSkills = (await cachedKvBatchGet(skillIds.map(id => `skill:${id}`))).filter(Boolean);
  const listings = rawSkills.map(extractListingFields);

  // 写入分片
  _migrateToShards(listings);
  return listings;
}

function _migrateToShards(listings) {
  const shardMap = {};
  for (const l of listings) {
    const si = skillShardIndex(l.id);
    if (!shardMap[si]) shardMap[si] = [];
    shardMap[si].push(l);
  }
  for (let i = 0; i < SHARD_COUNT; i++) {
    const key = `${SHARD_PREFIX}${i}`;
    const data = shardMap[i] || [];
    kvPut(key, data).catch(() => {});
    _cache.set(key, { val: data, ts: Date.now() });
  }
  // 清理旧的单条聚合
  kvDelete(LISTDATA_KEY).catch(() => {});
  _cache.delete(LISTDATA_KEY);
}

// 增量更新：向聚合中添加/更新一条技能
async function upsertSkillInAggregate(skill) {
  const listing = extractListingFields(skill);
  const si = skillShardIndex(skill.id);
  const shardKey = `${SHARD_PREFIX}${si}`;
  const shard = (await kvGet(shardKey)) || [];
  const idx = shard.findIndex(s => s.id === skill.id);
  if (idx >= 0) shard[idx] = listing; else shard.push(listing);
  await kvPut(shardKey, shard);
  _cache.set(shardKey, { val: shard, ts: Date.now() });
  _skillsQueryCache.clear();
}

// 增量更新：从聚合中移除一条技能
async function removeSkillFromAggregate(skillId) {
  const si = skillShardIndex(skillId);
  const shardKey = `${SHARD_PREFIX}${si}`;
  const shard = (await kvGet(shardKey)) || [];
  const idx = shard.findIndex(s => s.id === skillId);
  if (idx >= 0) {
    shard.splice(idx, 1);
    await kvPut(shardKey, shard);
    _cache.set(shardKey, { val: shard, ts: Date.now() });
  }
  _skillsQueryCache.clear();
}

// ─── KV 代理（供 Cloud Function 通过 HTTP 调用）───

async function handleKvProxy(request) {
  // 验证内部密钥
  const key = request.headers.get('X-Internal-Key');
  if (key !== INTERNAL_KEY) {
    return errResponse(1003, '无权访问 KV 代理', 403);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return errResponse(1001, '请求体格式错误', 400);
  }

  const { action } = body;

  try {
    switch (action) {
      case 'get': {
        const val = await kvGet(body.key);
        return jsonResp({ result: val });
      }
      case 'get_fresh': {
        // 强制最短 cacheTtl 读取，减少因边缘缓存导致的脏读
        const val = await kvGetFresh(body.key);
        return jsonResp({ result: val });
      }
      case 'put': {
        await kvPut(body.key, body.value);
        // 技能数据变更时增量更新聚合缓存
        if (typeof body.key === 'string' && /^skill:[a-f0-9]+$/.test(body.key) && body.value && typeof body.value === 'object') {
          if (body.value.status === 'approved') {
            upsertSkillInAggregate(body.value).catch(() => {});
          } else {
            removeSkillFromAggregate(body.value.id || body.key.slice(6)).catch(() => {});
          }
        }
        return jsonResp({ result: true });
      }
      case 'delete': {
        await kvDelete(body.key);
        return jsonResp({ result: true });
      }
      case 'batch_get': {
        const keys = (body.keys || []).filter(k => k && typeof k === 'string');
        const results = await kvBatchGet(keys);
        return jsonResp({ result: results });
      }
      case 'claim_register': {
        // 边缘侧注册去重锁：防止同一 openid 并发注册
        const lockKey = body.key;
        const now = Date.now();
        const existing = _registerLock.get(lockKey);
        if (existing && now - existing < REGISTER_LOCK_TTL) {
          // 已被锁定，说明有并发注册正在进行
          return jsonResp({ result: false });
        }
        _registerLock.set(lockKey, now);
        // 清理过期锁
        if (_registerLock.size > 1000) {
          for (const [k, ts] of _registerLock) {
            if (now - ts > REGISTER_LOCK_TTL) _registerLock.delete(k);
          }
        }
        return jsonResp({ result: true });
      }
      case 'get_list': {
        const list = await kvGetList(body.key);
        return jsonResp({ result: list });
      }
      case 'add_to_list': {
        const list = await kvGetList(body.key);
        if (!list.some(x => String(x) === String(body.item_id))) {
          list.push(body.item_id);
          await kvPut(body.key, list);
        }
        // 技能变为 approved 时增量加入聚合
        if (typeof body.key === 'string' && body.key === 'skill:by_status:approved' && body.item_id) {
          const skillData = await kvGet(`skill:${body.item_id}`);
          if (skillData) upsertSkillInAggregate(skillData).catch(() => {});
        }
        return jsonResp({ result: true });
      }
      case 'remove_from_list': {
        const list = await kvGetList(body.key);
        const idx = list.findIndex(x => String(x) === String(body.item_id));
        if (idx !== -1) {
          list.splice(idx, 1);
          await kvPut(body.key, list);
        }
        // 技能从 approved 移除时增量删除
        if (typeof body.key === 'string' && body.key === 'skill:by_status:approved' && body.item_id) {
          removeSkillFromAggregate(String(body.item_id)).catch(() => {});
        }
        return jsonResp({ result: true });
      }
      case 'next_id': {
        const counterKey = `${body.entity}:_counter`;
        const current = await kvGet(counterKey);
        const nextVal = (Number(current) || 0) + 1;
        await kvPut(counterKey, nextVal);
        return jsonResp({ result: nextVal });
      }
      case 'list_keys': {
        // 列出所有 KV 键，支持 prefix 过滤和游标分页
        const prefix = body.prefix ? sanitizeKey(body.prefix) : undefined;
        const cursor = body.cursor || undefined;
        const limit = Math.min(body.limit || 256, 256);  // EdgeOne KV max limit is 256
        const opts = { limit };
        if (prefix) opts.prefix = prefix;
        if (cursor) opts.cursor = cursor;
        const listResult = await MY_KV.list(opts);
        // EdgeOne KV may return keys as objects {name: str} or strings
        const keyNames = (listResult.keys || []).map(k => typeof k === 'string' ? k : (k && (k.name || k.key))).filter(Boolean);
        const isComplete = listResult.list_complete ?? listResult.listComplete ?? true;
        return jsonResp({
          result: {
            keys: keyNames,
            list_complete: isComplete,
            cursor: listResult.cursor || null,
          }
        });
      }
      case 'bulk_put': {
        // 批量写入 KV 键值对
        const pairs = body.pairs || [];
        for (const p of pairs) {
          await kvPut(p.key, p.value);
        }
        return jsonResp({ result: { count: pairs.length } });
      }
      case 'dump_all':
      case 'dump_by_structure': {
        // 通过应用数据结构（counter + list）推导出所有键，然后直接读取
        // 全部在 edge function 内完成，直读 MY_KV，无 HTTP 往返
        const errors = [];
        const allKeys = new Set();

        // Step 1: 读取所有 counter
        const counterEntities = [
          'user', 'review', 'purchase', 'msg', 'audit', 'fav',
          'pr', 'wd', 'token', 'follow', 'recharge_order', 'si', 'sv',
        ];
        const counterResults = await Promise.all(
          counterEntities.map(e => kvGet(`${e}:_counter`))
        );
        const counters = {};
        for (let idx = 0; idx < counterEntities.length; idx++) {
          const e = counterEntities[idx];
          const n = Number(counterResults[idx]) || 0;
          counters[e] = n;
          if (n > 0) {
            allKeys.add(sanitizeKey(`${e}:_counter`));
            for (let i = 1; i <= n; i++) {
              allKeys.add(sanitizeKey(`${e}:${i}`));
            }
          }
        }

        // Step 2: Skill status lists
        for (const status of ['approved', 'pending', 'rejected', 'offline', 'deleted']) {
          const listKey = `skill:by_status:${status}`;
          const sids = await kvGetList(listKey);
          allKeys.add(sanitizeKey(listKey));
          for (const sid of sids) {
            allKeys.add(sanitizeKey(`skill:${sid}`));
            allKeys.add(sanitizeKey(`si:by_skill:${sid}`));
            allKeys.add(sanitizeKey(`sv:by_skill:${sid}`));
            allKeys.add(sanitizeKey(`review:by_skill:${sid}`));
            allKeys.add(sanitizeKey(`audit:by_skill:${sid}`));
          }
        }

        // Step 3: Categories
        const catIds = await kvGetList('cat:all');
        allKeys.add(sanitizeKey('cat:all'));
        for (const cid of catIds) {
          allKeys.add(sanitizeKey(`cat:${cid}`));
          allKeys.add(sanitizeKey(`skill:by_cat:${cid}`));
        }

        // Step 4: User-associated list keys
        const userCount = counters['user'] || 0;
        for (let uid = 1; uid <= userCount; uid++) {
          for (const prefix of [
            'skill:by_user', 'purchase:by_user', 'fav:by_user',
            'msg:by_user', 'msg:unread', 'pr:by_user',
            'token:by_user', 'follow:by_er', 'follow:by_ing',
          ]) {
            allKeys.add(sanitizeKey(`${prefix}:${uid}`));
          }
        }

        // Step 5: Fixed keys
        allKeys.add(sanitizeKey('wd:pending'));
        allKeys.add(sanitizeKey('site:settings'));

        console.log(`[dump_by_structure] enumerated ${allKeys.size} keys`);

        // Step 6: 直接从 MY_KV 读取所有值（并发 20）
        const keyArr = [...allKeys];
        const allData = {};
        const BATCH = 20;
        for (let i = 0; i < keyArr.length; i += BATCH) {
          const batch = keyArr.slice(i, i + BATCH);
          try {
            const entries = await Promise.all(
              batch.map(async k => {
                try {
                  const val = await MY_KV.get(k, { type: 'json' });
                  return [k, val];
                } catch (e) {
                  try {
                    const text = await MY_KV.get(k, { type: 'text' });
                    if (text) {
                      try { return [k, JSON.parse(text)]; }
                      catch { return [k, text]; }
                    }
                  } catch { /* ignore */ }
                  return [k, null];
                }
              })
            );
            for (const [k, v] of entries) {
              if (v != null) allData[k] = v;
            }
          } catch (batchErr) {
            console.error(`[dump_by_structure] batch ${i} error:`, batchErr);
            errors.push(`batch ${i}: ${batchErr.message}`);
          }
        }

        // Step 7: 从已读取的值中发现索引键并补充读取
        const idxKeys = new Set();
        for (const [key, val] of Object.entries(allData)) {
          if (!val || typeof val !== 'object' || Array.isArray(val)) continue;
          if (key.startsWith('user_') && !key.startsWith('user_idx_') && !key.startsWith('user__')) {
            for (const [field, pre] of [
              ['username', 'user_idx_username_'], ['openid', 'user_idx_openid_'],
              ['unionid', 'user_idx_unionid_'], ['qq_openid', 'user_idx_qq_'],
              ['wx_openid', 'user_idx_wx_'], ['wx_mini_openid', 'user_idx_wxmini_'],
            ]) {
              if (val[field]) idxKeys.add(sanitizeKey(`user:idx:${field.replace('_openid','').replace('openid','openid')}:${val[field]}`));
            }
          } else if (key.startsWith('purchase_') && !key.startsWith('purchase_idx_') && !key.startsWith('purchase__') && !key.startsWith('purchase_by_')) {
            if (val.user_id && val.skill_id) idxKeys.add(sanitizeKey(`purchase:idx:${val.user_id}:${val.skill_id}`));
          } else if (key.startsWith('fav_') && !key.startsWith('fav_idx_') && !key.startsWith('fav__') && !key.startsWith('fav_by_')) {
            if (val.user_id && val.skill_id) idxKeys.add(sanitizeKey(`fav:idx:${val.user_id}:${val.skill_id}`));
          } else if (key.startsWith('token_') && !key.startsWith('token_idx_') && !key.startsWith('token__') && !key.startsWith('token_by_')) {
            if (val.token_key) idxKeys.add(sanitizeKey(`token:idx:${val.token_key}`));
          } else if (key.startsWith('follow_') && !key.startsWith('follow_idx_') && !key.startsWith('follow__') && !key.startsWith('follow_by_')) {
            if (val.follower_id && val.following_id) idxKeys.add(sanitizeKey(`follow:idx:${val.follower_id}:${val.following_id}`));
          }
        }
        // 只读取尚未在 allData 中的索引键
        const newIdxKeys = [...idxKeys].filter(k => !(k in allData));
        if (newIdxKeys.length > 0) {
          console.log(`[dump_by_structure] fetching ${newIdxKeys.length} index keys`);
          for (let i = 0; i < newIdxKeys.length; i += BATCH) {
            const batch = newIdxKeys.slice(i, i + BATCH);
            try {
              const entries = await Promise.all(
                batch.map(async k => {
                  try { return [k, await MY_KV.get(k, { type: 'json' })]; }
                  catch { return [k, null]; }
                })
              );
              for (const [k, v] of entries) {
                if (v != null) allData[k] = v;
              }
            } catch { /* ignore */ }
          }
        }

        console.log(`[dump_by_structure] total data entries: ${Object.keys(allData).length}`);
        return jsonResp({ result: allData, errors: errors.length > 0 ? errors : undefined });
      }
      default:
        return errResponse(1001, `未知的 KV 操作: ${action}`, 400);
    }
  } catch (e) {
    console.error('[KV Proxy] Error:', e);
    return errResponse(1001, `KV 操作失败: ${e.message}`, 500);
  }
}

// ─── 路由匹配（公开 GET 端点）───

function matchEdgeRoute(path) {
  if (path === '/v1/categories') return handleCategories;
  if (path === '/v1/points/packages') return handlePackages;
  if (path === '/v1/skills') return handleSkillsList;
  if (path === '/v1/skills/my') return (url, req) => handleMySkills(url, req);
  if (path === '/v1/users/me') return (url, req) => handleGetMe(url, req);
  if (path === '/v1/messages/unread-count') return (url, req) => handleUnreadCount(url, req);
  if (path === '/v1/messages') return (url, req) => handleMessages(url, req);
  if (path === '/v1/favorites') return (url, req) => handleFavorites(url, req);
  if (path === '/v1/purchases') return (url, req) => handlePurchases(url, req);
  if (path === '/v1/points/balance') return (url, req) => handlePointsBalance(url, req);
  if (path === '/v1/points/records') return (url, req) => handlePointsRecords(url, req);
  if (path === '/v1/tokens') return (url, req) => handleTokens(url, req);
  if (path === '/v1/site/public-settings') return handlePublicSettings;

  let m = path.match(/^\/v1\/skills\/([a-f0-9\w]+)$/);
  if (m) return (url, req) => handleSkillDetail(m[1], req);

  m = path.match(/^\/v1\/skills\/([a-f0-9\w]+)\/reviews$/);
  if (m) return (url, req) => handleSkillReviews(m[1], url);

  m = path.match(/^\/v1\/skills\/([a-f0-9\w]+)\/versions$/);
  if (m) return (url, req) => handleSkillVersions(m[1]);

  m = path.match(/^\/v1\/users\/(\d+)\/profile$/);
  if (m) return (url, req) => handleUserProfile(parseInt(m[1]));

  m = path.match(/^\/v1\/purchases\/([a-f0-9\w]+)\/check$/);
  if (m) return (url, req) => handleCheckPurchase(m[1], url, req);

  m = path.match(/^\/v1\/favorites\/([a-f0-9\w]+)\/check$/);
  if (m) return (url, req) => handleCheckFavorite(m[1], url, req);

  return null;
}

// ─── 等级计算 ───

const DEFAULT_LEVELS = [
  { level: 1, name: '新手虾',  icon: '🦐', min_exp: 0 },
  { level: 2, name: '中级龙虾', icon: '🦞', min_exp: 100 },
  { level: 3, name: '高级龙虾', icon: '🦞', min_exp: 500 },
  { level: 4, name: '澳龙',   icon: '🦞', min_exp: 2000 },
  { level: 5, name: '波龙',   icon: '🦞', min_exp: 8000 },
];

function getLevelInfo(exp, levels) {
  const lvs = levels || DEFAULT_LEVELS;
  let current = lvs[0];
  let nextLevel = lvs.length > 1 ? lvs[1] : null;
  for (let i = 0; i < lvs.length; i++) {
    if (exp >= lvs[i].min_exp) {
      current = lvs[i];
      nextLevel = i + 1 < lvs.length ? lvs[i + 1] : null;
    }
  }
  return { level: current.level, name: current.name, icon: current.icon, exp, next_level: nextLevel };
}

// ─── 端点处理器 ───

async function handleCategories() {
  const ids = await kvGetList('cat:all');
  if (!ids.length) return null; // Fall through to Cloud Function

  const cats = (await kvBatchGet(ids.map(id => `cat:${id}`))).filter(Boolean);
  if (!cats.length) return null;

  const catMap = {};
  for (const c of cats) catMap[c.id] = { ...c, children: [] };

  const roots = [];
  const sorted = cats.slice().sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  for (const c of sorted) {
    const node = catMap[c.id];
    if (c.parent_id && catMap[c.parent_id]) {
      catMap[c.parent_id].children.push(node);
    } else {
      roots.push(node);
    }
  }
  return ok({ categories: roots });
}

async function handlePublicSettings() {
  const settings = await cachedKvGet('site:settings');
  if (!settings) return ok({ icp: '', police: '', title: '', about: '', wechatEnabled: false, alipayEnabled: false, betaAnnouncement: false, announcementTitle: '', announcementContent: '' });
  return ok({
    icp: settings.icp || '',
    police: settings.police || '',
    title: settings.title || '',
    about: settings.about || '',
    wechatEnabled: !!settings.wechatEnabled,
    alipayEnabled: !!settings.alipayEnabled,
    betaAnnouncement: !!settings.betaAnnouncement,
    announcementTitle: settings.announcementTitle || '',
    announcementContent: settings.announcementContent || '',
  });
}

async function handlePackages() {
  return ok({
    packages: [
      { amount_yuan: 6, points: 60, bonus: 0 },
      { amount_yuan: 30, points: 300, bonus: 30 },
      { amount_yuan: 98, points: 980, bonus: 150 },
      { amount_yuan: 198, points: 1980, bonus: 400 },
    ],
  });
}

async function handleSkillsList(url) {
  const params = url.searchParams;
  const page = Math.max(1, parseInt(params.get('page')) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(params.get('page_size')) || 20));
  const categoryId = params.get('category_id') ? parseInt(params.get('category_id')) : null;
  const sort = params.get('sort') || 'newest';
  const keyword = (params.get('keyword') || '').toLowerCase();
  const isFree = params.get('is_free');
  const priceMin = params.get('price_min') ? parseInt(params.get('price_min')) : null;
  const priceMax = params.get('price_max') ? parseInt(params.get('price_max')) : null;
  const minRating = params.get('min_rating') ? parseFloat(params.get('min_rating')) : null;

  const queryKey = JSON.stringify({
    categoryId,
    sort,
    keyword,
    isFree,
    priceMin,
    priceMax,
    minRating,
  });

  const now = Date.now();
  const cacheHit = _skillsQueryCache.get(queryKey);
  let skills;

  if (cacheHit && now - cacheHit.ts < SKILLS_QUERY_TTL) {
    skills = cacheHit.skills;
  } else {
    // 聚合缓存：1 次 KV 读取获取全部技能（代替 300+ 次逐条读取）
    skills = await getApprovedSkillsAggregate();
    if (!skills.length) return paginated([], 0, page, pageSize);

    if (categoryId) skills = skills.filter(s => s.category_id === categoryId);
    if (keyword) {
      // 搜索 title / subtitle / tags（不含 description，保持聚合体积可控）
      skills = skills.filter(s =>
        (s.title || '').toLowerCase().includes(keyword) ||
        (s.subtitle || '').toLowerCase().includes(keyword) ||
        (Array.isArray(s.tags) && s.tags.some(t => t.toLowerCase().includes(keyword)))
      );
    }
    if (isFree !== null && isFree !== undefined && isFree !== '') {
      const free = isFree === 'true' || isFree === '1';
      skills = skills.filter(s => !!s.is_free === free);
    }
    if (priceMin !== null) skills = skills.filter(s => (s.price || 0) >= priceMin);
    if (priceMax !== null) skills = skills.filter(s => (s.price || 0) <= priceMax);
    if (minRating !== null) skills = skills.filter(s => (s.avg_rating || 0) >= minRating);

    if (sort === 'hot') {
      skills.sort((a, b) => (b.download_count || 0) - (a.download_count || 0));
    } else if (sort === 'rating') {
      skills.sort((a, b) => (b.avg_rating || 0) - (a.avg_rating || 0));
    } else {
      skills.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
    }

    _skillsQueryCache.set(queryKey, { skills, ts: now });
    if (_skillsQueryCache.size > SKILLS_QUERY_CACHE_MAX) {
      let oldestKey = null;
      let oldestTs = Infinity;
      for (const [k, v] of _skillsQueryCache.entries()) {
        if (v.ts < oldestTs) {
          oldestTs = v.ts;
          oldestKey = k;
        }
      }
      if (oldestKey) _skillsQueryCache.delete(oldestKey);
    }
  }

  const total = skills.length;
  const start = (page - 1) * pageSize;
  const pageSkills = skills.slice(start, start + pageSize);

  const authorIds = [...new Set(pageSkills.map(s => s.user_id))];
  const catIds = [...new Set(pageSkills.map(s => s.category_id).filter(Boolean))];
  const [authors, cats] = await Promise.all([
    cachedKvBatchGet(authorIds.map(id => `user:${id}`)),
    cachedKvBatchGet(catIds.map(id => `cat:${id}`)),
  ]);
  const authorMap = {};
  for (const a of authors) if (a) authorMap[a.id] = a;
  const catMap = {};
  for (const c of cats) if (c) catMap[c.id] = c;

  const items = pageSkills.map(s => {
    const author = authorMap[s.user_id] || {};
    const cat = catMap[s.category_id] || {};
    return {
      id: s.id, title: s.title,
      subtitle: s.subtitle || '',
      price: s.price, is_free: !!s.is_free,
      cover_image: s.cover_image || null,
      version: s.version || '1.0.0',
      avg_rating: s.avg_rating || 0,
      review_count: s.review_count || 0,
      download_count: s.download_count || 0,
      purchase_count: s.purchase_count || 0,
      tags: s.tags || [],
      category_name: cat.name || null,
      author_id: s.user_id,
      author_name: author.nickname || null,
      author_avatar: author.avatar_url || null,
      status: s.status,
      created_at: s.created_at || null,
    };
  });

  return paginated(items, total, page, pageSize);
}

async function handleSkillDetail(skillId, request) {
  const skill = await kvGet(`skill:${skillId}`);
  if (!skill) return errResponse(3001, '技能不存在', 404);
  if (skill.status === 'deleted') {
    const user = await getAuthUser(request);
    if (!user || user.role !== 'admin') return errResponse(3001, '技能不存在', 404);
  }

  const [author, cat, imageIds, versionIds, siteSettings] = await Promise.all([
    kvGet(`user:${skill.user_id}`),
    skill.category_id ? kvGet(`cat:${skill.category_id}`) : null,
    kvGetList(`si:by_skill:${skillId}`),
    kvGetList(`sv:by_skill:${skillId}`),
    kvGet('site:settings'),
  ]);

  const cfgLevels = (siteSettings && siteSettings.levelsConfig) || null;

  const [imagesData, versionsData] = await Promise.all([
    kvBatchGet(imageIds.map(id => `si:${id}`)),
    kvBatchGet(versionIds.map(id => `sv:${id}`)),
  ]);

  const images = imagesData
    .filter(Boolean)
    .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
    .map(i => i.image_url);

  const versions = versionsData
    .filter(Boolean)
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
    .map(v => ({ id: v.id, version: v.version, changelog: v.changelog || null, created_at: v.created_at || null }));

  return ok({
    id: skill.id, title: skill.title,
    subtitle: skill.subtitle || null,
    description: skill.description || null,
    price: skill.price, is_free: !!skill.is_free,
    cover_image: skill.cover_image || null,
    file_url: skill.file_url || null,
    file_size: skill.file_size || null,
    version: skill.version || '1.0.0',
    avg_rating: skill.avg_rating || 0,
    review_count: skill.review_count || 0,
    download_count: skill.download_count || 0,
    purchase_count: skill.purchase_count || 0,
    tags: skill.tags || [],
    status: skill.status,
    reject_reason: skill.reject_reason || null,
    force_approved: skill.force_approved || false,
    vt_result: skill.vt_result || null,
    offline_reason: skill.offline_reason || null,
    category_name: cat ? cat.name : null,
    category_id: skill.category_id || null,
    author_id: skill.user_id,
    author_name: author ? author.nickname : null,
    author_avatar: author ? author.avatar_url : null,
    author_role: author ? (author.role || 'user') : 'user',
    author_level_info: getLevelInfo(author ? (author.exp || 0) : 0, cfgLevels),
    images, versions,
    screenshots: skill.screenshots || [],
    installation_guide: skill.installation_guide || null,
    created_at: skill.created_at || null,
    published_at: skill.published_at || null,
  });
}

async function handleSkillReviews(skillId, url) {
  const params = url.searchParams;
  const page = Math.max(1, parseInt(params.get('page')) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(params.get('page_size')) || 20));

  const reviewIds = await kvGetList(`review:by_skill:${skillId}`);
  let reviews = (await kvBatchGet(reviewIds.map(id => `review:${id}`))).filter(Boolean);
  reviews = reviews.filter(r => r.status === 'visible');
  reviews.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

  const total = reviews.length;
  const start = (page - 1) * pageSize;
  const pageItems = reviews.slice(start, start + pageSize);

  const userIds = [...new Set(pageItems.map(r => r.user_id))];
  const [users, siteSettings] = await Promise.all([
    kvBatchGet(userIds.map(id => `user:${id}`)),
    kvGet('site:settings'),
  ]);
  const cfgLevels = (siteSettings && siteSettings.levelsConfig) || null;
  const userMap = {};
  for (const u of users) if (u) userMap[u.id] = u;

  const items = pageItems.map(r => {
    const u = userMap[r.user_id] || {};
    return {
      id: r.id, rating: r.rating,
      content: r.content || null,
      user_id: r.user_id,
      user_nickname: u.nickname || null,
      user_avatar: u.avatar_url || null,
      user_role: u.role || 'user',
      user_level_info: getLevelInfo(u.exp || 0, cfgLevels),
      created_at: r.created_at || null,
    };
  });

  return paginated(items, total, page, pageSize);
}

async function handleSkillVersions(skillId) {
  const versionIds = await kvGetList(`sv:by_skill:${skillId}`);
  const versions = (await kvBatchGet(versionIds.map(id => `sv:${id}`))).filter(Boolean);
  versions.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

  const items = versions.map(v => ({
    id: v.id, version: v.version,
    changelog: v.changelog || null,
    status: v.status || null,
    created_at: v.created_at || null,
  }));

  return ok({ items });
}

// ─── 已认证的 GET 端点（Edge 优化）───

async function handleGetMe(url, request) {
  const user = await getAuthUser(request);
  if (!user) return null; // Fall through to Cloud Function (handles refresh etc.)
  const siteSettings = await kvGet('site:settings');
  const cfgLevels = (siteSettings && siteSettings.levelsConfig) || null;
  return ok({
    id: user.id,
    username: user.username,
    nickname: user.nickname,
    avatar_url: user.avatar_url || null,
    bio: user.bio || null,
    role: user.role || 'user',
    level: user.level || 1,
    exp: user.exp || 0,
    level_info: getLevelInfo(user.exp || 0, cfgLevels),
    points_balance: user.points_balance || 0,
    earnings_total: user.earnings_total || 0,
    skill_count: user.skill_count || 0,
    is_banned: user.is_banned || false,
    created_at: user.created_at || null,
  });
}

async function handleUnreadCount(url, request) {
  const user = await getAuthUser(request);
  if (!user) return null;
  const unread = await kvGetList(`msg:unread:${user.id}`);
  return ok({ count: unread.length });
}

async function handleUserProfile(userId) {
  const user = await kvGet(`user:${userId}`);
  if (!user) return errResponse(2001, '用户不存在', 404);

  const [stats, followerIds, siteSettings, skillIds] = await Promise.all([
    kvGet(`user:stats:${userId}`),
    kvGetList(`follow:by_ing:${userId}`),
    kvGet('site:settings'),
    kvGetList(`skill:by_user:${userId}`),
  ]);
  const cfgLevels = (siteSettings && siteSettings.levelsConfig) || null;

  // 使用预计算统计缓存，避免全量读取技能
  const skillCount = stats ? (stats.skill_count || 0) : 0;
  const totalDownloads = stats ? (stats.total_downloads || 0) : 0;

  // 只取最近 20 条展示
  const recentIds = skillIds.slice(-20).reverse();
  const recentSkills = recentIds.length
    ? (await kvBatchGet(recentIds.map(id => `skill:${id}`))).filter(s => s && s.status === 'approved')
    : [];

  return ok({
    id: user.id,
    nickname: user.nickname,
    avatar_url: user.avatar_url || null,
    bio: user.bio || null,
    level: user.level || 1,
    level_info: getLevelInfo(user.exp || 0, cfgLevels),
    role: user.role || 'user',
    skill_count: skillCount,
    follower_count: followerIds.length,
    total_downloads: totalDownloads,
    created_at: user.created_at || null,
    skills: recentSkills.map(s => ({
      id: s.id, title: s.title, price: s.price,
      is_free: !!s.is_free, avg_rating: s.avg_rating || 0,
      download_count: s.download_count || 0,
      version: s.version || '1.0.0',
    })),
  });
}

async function handleCheckPurchase(skillId, url, request) {
  const user = await getAuthUser(request);
  if (!user) return null;

  const purchaseIds = await kvGetList(`purchase:by_user:${user.id}`);
  const purchases = (await kvBatchGet(purchaseIds.map(id => `purchase:${id}`))).filter(Boolean);
  const purchased = purchases.some(p => String(p.skill_id) === String(skillId));

  return ok({ purchased });
}

async function handleCheckFavorite(skillId, url, request) {
  const user = await getAuthUser(request);
  // 未登录直接返回未收藏，不 fall-through 到 Cloud Function
  if (!user) return ok({ favorited: false });

  // O(1) 索引键查询（Cloud Function 在收藏/取消时同步维护此键）
  const favId = await cachedKvGet(`fav:idx:user_skill:${user.id}:${skillId}`);
  return ok({ favorited: favId != null });
}

async function handleFavorites(url, request) {
  const user = await getAuthUser(request);
  if (!user) return null;

  const favIds = await kvGetList(`fav:by_user:${user.id}`);
  if (!favIds.length) return ok({ items: [] });

  const favs = (await kvBatchGet(favIds.map(id => `fav:${id}`))).filter(Boolean);
  const skillIds = favs.map(f => f.skill_id);
  const skills = (await kvBatchGet(skillIds.map(id => `skill:${id}`))).filter(Boolean);

  const authorIds = [...new Set(skills.map(s => s.user_id))];
  const authors = await kvBatchGet(authorIds.map(id => `user:${id}`));
  const authorMap = {};
  for (const a of authors) if (a) authorMap[a.id] = a;

  const items = skills.map(s => {
    const author = authorMap[s.user_id] || {};
    return {
      id: s.id, title: s.title, price: s.price,
      is_free: !!s.is_free, avg_rating: s.avg_rating || 0,
      download_count: s.download_count || 0,
      author_name: author.nickname || null,
      author_avatar: author.avatar_url || null,
      category_name: null,
    };
  });

  return ok({ items });
}

// ─── 新迁移的 Edge 端点 ───

async function handlePurchases(url, request) {
  const user = await getAuthUser(request);
  if (!user) return null;

  const params = url.searchParams;
  const page = Math.max(1, parseInt(params.get('page')) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(params.get('page_size')) || 20));

  const purchaseIds = await kvGetList(`purchase:by_user:${user.id}`);
  if (!purchaseIds.length) return paginated([], 0, page, pageSize);

  const reversed = purchaseIds.slice().reverse();
  const total = reversed.length;
  const start = (page - 1) * pageSize;
  const pageIds = reversed.slice(start, start + pageSize);

  const purchases = (await kvBatchGet(pageIds.map(id => `purchase:${id}`))).filter(Boolean);
  const skillIds = [...new Set(purchases.map(p => p.skill_id).filter(Boolean))];
  const skills = await kvBatchGet(skillIds.map(id => `skill:${id}`));
  const skillMap = {};
  for (const s of skills) if (s) skillMap[s.id] = s;

  const items = purchases.map(p => {
    const s = skillMap[p.skill_id] || {};
    return {
      id: p.id, skill_id: p.skill_id,
      title: s.title || p.skill_title || '已删除的技能',
      cover_image: s.cover_image || null,
      version: s.version || '1.0.0',
      price_paid: p.price_paid || p.amount || 0,
      order_no: p.order_no || null,
      tags: s.tags || [],
      purchase_time: p.created_at || null,
    };
  });

  return paginated(items, total, page, pageSize);
}

async function handlePointsBalance(url, request) {
  const user = await getAuthUser(request);
  if (!user) return null;

  const now = Date.now();
  const bcached = _balanceCache.get(user.id);
  let totalSpent;
  if (bcached && now - bcached.ts < BALANCE_CACHE_TTL) {
    totalSpent = bcached.totalSpent;
  } else {
    const recordIds = await kvGetList(`pr:by_user:${user.id}`);
    totalSpent = 0;
    if (recordIds.length) {
      const records = (await kvBatchGet(recordIds.map(id => `pr:${id}`))).filter(Boolean);
      for (const r of records) {
        if (r.amount < 0) totalSpent += Math.abs(r.amount);
      }
    }
    _balanceCache.set(user.id, { totalSpent, ts: now });
  }

  return ok({
    balance: user.points_balance || 0,
    total_earned: user.total_earned || 0,
    total_spent: totalSpent,
  });
}

async function handlePointsRecords(url, request) {
  const user = await getAuthUser(request);
  if (!user) return null;

  const params = url.searchParams;
  const page = Math.max(1, parseInt(params.get('page')) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(params.get('page_size')) || 20));
  const type = params.get('type') || 'all';

  const recordIds = await kvGetList(`pr:by_user:${user.id}`);
  if (!recordIds.length) return paginated([], 0, page, pageSize);

  let records = (await kvBatchGet(recordIds.map(id => `pr:${id}`))).filter(Boolean);
  records.reverse();

  if (type !== 'all') {
    records = records.filter(r => r.type === type);
  }

  const total = records.length;
  const start = (page - 1) * pageSize;
  const items = records.slice(start, start + pageSize).map(r => ({
    id: r.id, type: r.type,
    amount: r.amount,
    balance_after: r.balance_after || 0,
    description: r.description || '',
    created_at: r.created_at || null,
  }));

  return paginated(items, total, page, pageSize);
}

async function handleMessages(url, request) {
  const user = await getAuthUser(request);
  if (!user) return null;

  const params = url.searchParams;
  const page = Math.max(1, parseInt(params.get('page')) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(params.get('page_size')) || 20));
  const type = params.get('type') || 'all';

  const msgIds = await kvGetList(`msg:by_user:${user.id}`);
  if (!msgIds.length) return paginated([], 0, page, pageSize);

  if (type !== 'all') {
    const now = Date.now();
    const mcached = _msgListCache.get(user.id);
    let allMsgs;
    if (mcached && now - mcached.ts < MSG_LIST_CACHE_TTL) {
      allMsgs = mcached.msgs;
    } else {
      allMsgs = (await kvBatchGet(msgIds.map(id => `msg:${id}`))).filter(Boolean);
      _msgListCache.set(user.id, { msgs: allMsgs, ts: now });
    }
    const filtered = allMsgs.filter(m => m.type === type);
    filtered.reverse();
    const total = filtered.length;
    const start = (page - 1) * pageSize;
    const items = filtered.slice(start, start + pageSize).map(m => ({
      id: m.id, type: m.type,
      title: m.title || '', content: m.content || '',
      is_read: m.is_read || false,
      related_type: m.related_type || null,
      related_id: m.related_id || null,
      created_at: m.created_at || null,
    }));
    return paginated(items, total, page, pageSize);
  }

  const reversed = msgIds.slice().reverse();
  const total = reversed.length;
  const start = (page - 1) * pageSize;
  const pageIds = reversed.slice(start, start + pageSize);
  const msgs = (await kvBatchGet(pageIds.map(id => `msg:${id}`))).filter(Boolean);

  const items = msgs.map(m => ({
    id: m.id, type: m.type,
    title: m.title || '', content: m.content || '',
    is_read: m.is_read || false,
    related_type: m.related_type || null,
    related_id: m.related_id || null,
    created_at: m.created_at || null,
  }));

  return paginated(items, total, page, pageSize);
}

async function handleTokens(url, request) {
  const user = await getAuthUser(request);
  if (!user) return null;

  const tokenIds = await kvGetList(`token:by_user:${user.id}`);
  if (!tokenIds.length) return ok([]);

  const tokens = (await kvBatchGet(tokenIds.map(id => `token:${id}`))).filter(Boolean);
  const items = tokens.map(t => ({
    id: t.id, name: t.name,
    scopes: t.scopes || [],
    is_active: t.is_active !== false,
    created_at: t.created_at || null,
    expires_at: t.expires_at || null,
    last_used: t.last_used || null,
  }));

  return ok(items);
}

async function handleMySkills(url, request) {
  const user = await getAuthUser(request);
  if (!user) return null;

  const params = url.searchParams;
  const page = Math.max(1, parseInt(params.get('page')) || 1);
  const pageSize = Math.min(50, Math.max(1, parseInt(params.get('page_size')) || 20));
  const status = params.get('status') || null;

  const skillIds = await kvGetList(`skill:by_user:${user.id}`);
  if (!skillIds.length) return paginated([], 0, page, pageSize);

  let skills = (await kvBatchGet(skillIds.map(id => `skill:${id}`))).filter(Boolean);
  skills.reverse();

  if (status && status !== 'all') {
    skills = skills.filter(s => s.status === status);
  }

  const total = skills.length;
  const start = (page - 1) * pageSize;
  const items = skills.slice(start, start + pageSize).map(s => ({
    id: s.id, title: s.title,
    subtitle: (s.subtitle || '').slice(0, 100),
    description: (s.description || '').slice(0, 200),
    price: s.price, is_free: !!s.is_free,
    cover_image: s.cover_image || null,
    version: s.version || '1.0.0',
    avg_rating: s.avg_rating || 0,
    download_count: s.download_count || 0,
    status: s.status,
    reject_reason: s.reject_reason || null,
    offline_reason: s.offline_reason || null,
    tags: s.tags || [],
    created_at: s.created_at || null,
    updated_at: s.updated_at || null,
  }));

  return paginated(items, total, page, pageSize);
}

// ─── 主入口 ───

export async function onRequest(context) {
  const { request, env } = context;

  // 从 Pages 环境变量加载 secret。同一个 Edge Function 实例可能复用
  // module 作用域，但 env.INTERNAL_KEY / env.JWT_SECRET 在同一次部署
  // 内常量不变，不会造成跨请求污染。
  if (env && typeof env === 'object') {
    if (env.INTERNAL_KEY) INTERNAL_KEY = env.INTERNAL_KEY;
    if (env.JWT_SECRET) JWT_SECRET = env.JWT_SECRET;
  }

  const url = new URL(request.url);
  const method = request.method;

  // CORS 预检
  if (method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Token, X-Internal-Key, X-Admin-Password',
        'Access-Control-Max-Age': '86400',
      },
    });
  }

  const rawPath = url.pathname;
  const path = rawPath.startsWith('/api') ? rawPath.slice(4) : rawPath;

  // ── KV 代理端点（Cloud Function 通过 HTTP 调用此端点操作 KV）──
  if (path === '/_internal/kv' && method === 'POST') {
    return handleKvProxy(request);
  }

  // ── 公开 GET 端点 → Edge 直接处理 ──
  if (method === 'GET') {
    const handler = matchEdgeRoute(path);
    if (handler) {
      try {
        const result = await handler(url, request);
        if (result) return result;
      } catch (e) {
        console.error('Edge handler error, falling back:', e);
      }
    }
  }

  // ── 其他请求 → 转发到 Cloud Function ──
  if (method !== 'GET' && path.startsWith('/v1/skills')) {
    _skillsQueryCache.clear();
  }

  const fnUrl = new URL(request.url);
  fnUrl.pathname = '/fn' + path;

  let body = null;
  if (method !== 'GET' && method !== 'HEAD') {
    try {
      body = await request.arrayBuffer();
    } catch (e) {
      body = null;
    }
  }

  const forwardHeaders = new Headers();
  const contentType = request.headers.get('Content-Type');
  const authorization = request.headers.get('Authorization');
  const apiToken = request.headers.get('X-API-Token');
  if (contentType) forwardHeaders.set('Content-Type', contentType);
  if (authorization) forwardHeaders.set('Authorization', authorization);
  if (apiToken) forwardHeaders.set('X-API-Token', apiToken);
  const adminPwd = request.headers.get('X-Admin-Password');
  if (adminPwd) forwardHeaders.set('X-Admin-Password', adminPwd);
  // 传递源地址给 Cloud Function，用于回调 KV 代理
  forwardHeaders.set('X-Internal-Origin', url.origin);
  // 传递客户端真实 IP
  const clientIp = request.headers.get('X-Forwarded-For')?.split(',')[0]?.trim()
    || request.headers.get('CF-Connecting-IP')
    || request.headers.get('X-Real-IP')
    || '';
  if (clientIp) forwardHeaders.set('X-Real-IP', clientIp);

  try {
    return await fetch(fnUrl.toString(), {
      method,
      headers: forwardHeaders,
      body,
      redirect: 'manual',  // 不跟随重定向，直接将 3xx 响应返回给客户端（OAuth 回调等场景需要）
    });
  } catch (e) {
    console.error('[Proxy] Cloud Function fetch failed:', e?.message || e, 'url=', fnUrl.toString());
    return errResponse(
      5001,
      `Cloud Function 不可达 (${e?.message || 'fetch failed'})。请检查：1) Cloud Function 是否已部署成功；2) edgeone.json 的 env 是否包含 ADMIN_PASSWORD/JWT_SECRET/INTERNAL_KEY；3) KV 命名空间是否在控制台绑定为 MY_KV。`,
      502,
    );
  }
}
