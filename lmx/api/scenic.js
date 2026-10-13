import request from '@/utils/request'

/**
 * 景点 / AI辅助规划相关接口封装
 * 后端路由前缀：/api/planning
 * 响应统一为 { code, message, data }
 */

/**
 * 将后端景点对象转换为页面期望的结构（与 trip.js 中 toScenicInfo 保持一致）
 */
function toScenicCard(s) {
  if (!s) return null
  const priceNum = Number(s.price)
  const priceStr = (!s.price && priceNum !== 0) || priceNum === 0 ? '免费' : `${s.price}元`
  return {
    id: s.id,
    name: s.name || '',
    city: s.city || '',
    category: s.category || '',
    introduction: s.introduction || '',
    address: s.address || '',
    open_time: s.open_time || '',
    price: priceStr,
    raw_price: priceNum,
    score: String(s.rating ?? s.score ?? '0.0'),
    rating: s.rating ?? 0,
    suggest_duration: s.suggested_duration || s.suggest_duration || '',
    suggested_duration: s.suggested_duration || '',
    special_notice: s.special_notice || '',
    latitude: s.latitude,
    longitude: s.longitude,
    tel: s.tel || '',
    tags: s.tags || [],
    recommendation: s.recommendation || ''
  }
}

/**
 * 搜索景点（数据库匹配 name 和 address）
 * GET /api/planning/scenic/search?keyword=xxx&city=xxx
 * @param {string} keyword 关键词（可为空字符串，表示仅按城市列出）
 * @param {string} city 所属城市（可选）
 * @returns {Promise<Object>} 响应对象，data.data 为景点数组（已转换为页面结构）
 */
export function searchScenic(keyword, city = '') {
  const params = []
  // keyword 后端为必填 query 参数，即使为空也要带上，避免 422
  params.push(`keyword=${encodeURIComponent(keyword || '')}`)
  if (city) params.push(`city=${encodeURIComponent(city)}`)
  return request({
    url: `/api/planning/scenic/search?${params.join('&')}`,
    method: 'GET'
  }).then(response => {
    if (response && response.statusCode === 200 && response.data && response.data.code === 200) {
      const list = Array.isArray(response.data.data) ? response.data.data : []
      response.data.data = list.map(toScenicCard)
    }
    return response
  })
}

/**
 * AI搜索景点（高德式）：返回多个候选景点卡片
 * POST /api/planning/scenic/ai-search  body: { keyword, city, trip_id?, day_num? }
 * @param {Object} param { keyword, city, trip_id?, day_num? }
 * @returns {Promise<Object>} 响应对象，data.data.results 为候选景点数组（已转换为页面结构）
 */
export function aiSearchScenic({ keyword, city, trip_id, day_num } = {}) {
  const payload = { keyword, city }
  if (trip_id !== undefined && trip_id !== null) payload.trip_id = Number(trip_id)
  if (day_num !== undefined && day_num !== null) payload.day_num = Number(day_num)
  return request({
    url: '/api/planning/scenic/ai-search',
    method: 'POST',
    data: payload,
    // AI 搜索调用 DeepSeek 可能需要 15-40 秒
    timeout: 90000
  }).then(response => {
    if (response && response.statusCode === 200 && response.data && response.data.code === 200) {
      const d = response.data.data || {}
      const list = Array.isArray(d.results) ? d.results : []
      d.results = list.map(toScenicCard)
      response.data.data = d
    }
    return response
  })
}

/**
 * 将已有景点添加到行程
 * POST /api/planning/scenic/add-to-trip  body: { scenic_id, trip_id, day_num }
 * @param {number} scenicId 景点id
 * @param {number} tripId 行程id
 * @param {number} dayNum 第几天（默认1）
 * @returns {Promise<Object>} 响应对象，data.data.detail_id 为新建的行程节点id
 */
export function addScenicToTrip(scenicId, tripId, dayNum = 1) {
  return request({
    url: '/api/planning/scenic/add-to-trip',
    method: 'POST',
    data: {
      scenic_id: Number(scenicId),
      trip_id: Number(tripId),
      day_num: Number(dayNum)
    }
  })
}

/**
 * AI获取景点详细信息（景区介绍、门票、注意事项、预算规划）
 * POST /api/planning/scenic/ai-detail  body: { scenic_name, city }
 * @param {string} scenicName 景点名称
 * @param {string} city 所在城市
 * @returns {Promise<Object>} 响应对象，data.data 已转换为页面期望结构：
 *   { introduction, price, address, open_time, special_notice, budgetPlanning }
 */
export function getScenicAiDetail(scenicName, city) {
  return request({
    url: '/api/planning/scenic/ai-detail',
    method: 'POST',
    data: { scenic_name: scenicName, city },
    // AI 获取详情调用 DeepSeek 可能需要 10-30 秒
    timeout: 90000
  }).then(response => {
    if (response && response.statusCode === 200 && response.data && response.data.code === 200) {
      const d = response.data.data || {}
      const priceNum = Number(d.price)
      const priceStr = (!d.price && priceNum !== 0) || priceNum === 0 ? '免费' : `${d.price}元`
      response.data.data = {
        introduction: d.introduction || '',
        price: priceStr,
        raw_price: priceNum,
        address: d.address || '',
        open_time: d.open_time || '',
        special_notice: d.special_notice || '',
        budgetPlanning: d.budget_suggestion || d.budgetPlanning || ''
      }
    }
    return response
  })
}

/**
 * 根据ID获取景点信息
 * GET /api/planning/scenic/{scenic_id}
 * @param {number} scenicId 景点id
 * @returns {Promise<Object>} 响应对象，data.data 为景点信息（已转换为页面结构）
 */
export function getScenicById(scenicId) {
  return request({
    url: `/api/planning/scenic/${scenicId}`,
    method: 'GET'
  }).then(response => {
    if (response && response.statusCode === 200 && response.data && response.data.code === 200) {
      response.data.data = toScenicCard(response.data.data)
    }
    return response
  })
}

export default {
  searchScenic,
  aiSearchScenic,
  addScenicToTrip,
  getScenicAiDetail,
  getScenicById
}
