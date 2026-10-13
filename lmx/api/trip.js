import request from '@/utils/request'

/**
 * 行程相关接口封装
 * 后端路由前缀：/api/trips
 * 响应统一为 { code, message, data }
 */

/**
 * 将 "YYYY-MM-DD" + dayNum 计算出该天对应的日期（YYYY-MM-DD）
 * dayNum 为 1 基：第 1 天 = start_date，第 N 天 = start_date + (N-1)
 */
function dayDateFromStart(startDateStr, dayNum) {
  let base
  if (startDateStr) {
    base = new Date(startDateStr + 'T00:00:00')
  }
  if (!base || isNaN(base.getTime())) {
    base = new Date()
  }
  base.setDate(base.getDate() + (Math.max(dayNum, 1) - 1))
  const y = base.getFullYear()
  const m = String(base.getMonth() + 1).padStart(2, '0')
  const d = String(base.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/**
 * 将日期 + "HH:MM" 组合成 ISO datetime 字符串（供页面 split('T') 取日期用）
 */
function toISODateTime(dateStr, hhmm) {
  if (!hhmm) return ''
  return `${dateStr}T${hhmm}:00`
}

/**
 * 从 ISO datetime 字符串中提取 "HH:MM"
 */
function hhmmFromISO(isoStr) {
  if (!isoStr || typeof isoStr !== 'string') return null
  if (isoStr.includes('T')) {
    const t = isoStr.split('T')[1]
    return t ? t.slice(0, 5) : null
  }
  // 已经是 HH:MM 格式
  if (/^\d{1,2}:\d{2}$/.test(isoStr)) return isoStr.slice(0, 5)
  return null
}

/**
 * 将后端 scenic_spot 转换为页面期望的 scenic_info 结构（与原 mock 保持一致）
 */
function toScenicInfo(scenic) {
  if (!scenic) return null
  const priceNum = Number(scenic.price)
  const priceStr = (!scenic.price || priceNum === 0) ? '免费' : `${scenic.price}元`
  return {
    id: scenic.id,
    name: scenic.name || '',
    city: scenic.city || '',
    introduction: scenic.introduction || '',
    address: scenic.address || '',
    open_time: scenic.open_time || '',
    price: priceStr,
    score: String(scenic.rating ?? scenic.score ?? '0.0'),
    suggest_duration: scenic.suggested_duration || scenic.suggest_duration || '',
    suggested_duration: scenic.suggested_duration || '',
    best_season: scenic.best_season || '',
    image: scenic.image || '',
    special_notice: scenic.special_notice || '',
    latitude: scenic.latitude,
    longitude: scenic.longitude,
    tel: scenic.tel || '',
    tags: scenic.tags || [],
    category: scenic.category || '',
    recommendation: scenic.recommendation || ''
  }
}

/**
 * 将后端行程详情节点转换为页面期望的结构
 */
function transformDetailItem(detail, tripStartDate) {
  const startDate = dayDateFromStart(tripStartDate, detail.day_num)
  const startTimeHHMM = detail.start_time || ''
  const endTimeHHMM = detail.end_time || ''
  return {
    id: detail.id,
    trip_id: detail.trip_id,
    scenic_id: detail.scenic_id,
    day_num: detail.day_num,
    sort_order: detail.sort_order,
    remark: detail.remark || '',
    type: 'spot',
    start_time: toISODateTime(startDate, startTimeHHMM),
    end_time: toISODateTime(startDate, endTimeHHMM),
    time_slot: startTimeHHMM && endTimeHHMM ? `${startTimeHHMM}-${endTimeHHMM}` : '',
    user_price: detail.spot_budget ?? null,
    spot_budget: detail.spot_budget ?? 0,
    scenic_info: toScenicInfo(detail.scenic_spot)
  }
}

/**
 * 获取当前用户所有行程列表
 * GET /api/trips/list
 */
export function getTripList() {
  return request({
    url: '/api/trips/list',
    method: 'GET'
  })
}

/**
 * 创建新行程
 * POST /api/trips/create
 * @param {Object} data { trip_name, dest_city, start_date?, end_date?, total_budget }
 */
export function createTrip(data) {
  const payload = { ...data }
  // total_budget 后端要求 float，兜底转数字
  if (payload.total_budget !== undefined && payload.total_budget !== null && payload.total_budget !== '') {
    payload.total_budget = Number(payload.total_budget) || 0
  } else {
    payload.total_budget = 0
  }
  return request({
    url: '/api/trips/create',
    method: 'POST',
    data: payload
  })
}

/**
 * 获取行程详情（含景点信息）
 * GET /api/trips/detail/{trip_id}
 * 响应 data.data.details 会被转换为页面期望的结构（scenic_info / time_slot / user_price / ISO start_time）
 */
export function getTripDetail(tripId) {
  return request({
    url: `/api/trips/detail/${tripId}`,
    method: 'GET'
  }).then(response => {
    if (response && response.statusCode === 200 && response.data && response.data.code === 200) {
      const d = response.data.data || {}
      const startDate = d.start_date || ''
      if (Array.isArray(d.details)) {
        d.details = d.details.map(item => transformDetailItem(item, startDate))
      }
      response.data.data = d
    }
    return response
  })
}

/**
 * 更新行程基础信息（标题、目的地、日期、预算等）
 * PUT /api/trips/update/{trip_id}
 * @param {number} tripId
 * @param {Object} data { trip_name?, dest_city?, start_date?, end_date?, total_budget? }
 */
export function updateTrip(tripId, data) {
  return request({
    url: `/api/trips/update/${tripId}`,
    method: 'PUT',
    data
  })
}

/**
 * 删除行程（级联删除行程节点）
 * DELETE /api/trips/delete/{trip_id}
 */
export function deleteTrip(tripId) {
  return request({
    url: `/api/trips/delete/${tripId}`,
    method: 'DELETE'
  })
}

/**
 * 更新行程节点（修改游玩时间、备注、预算等）
 * PUT /api/trips/detail/update/{detail_id}
 * @param {number} detailId
 * @param {Object} updateData 页面侧字段：{ start_time(ISO), end_time(ISO), time_slot, remark, user_price, sort_order, day_num }
 */
export function updateTripDetail(detailId, updateData) {
  const payload = {}
  if (updateData.remark !== undefined) payload.remark = updateData.remark
  if (updateData.user_price !== undefined) payload.spot_budget = Number(updateData.user_price) || 0
  if (updateData.sort_order !== undefined) payload.sort_order = updateData.sort_order
  if (updateData.day_num !== undefined) payload.day_num = updateData.day_num
  if (updateData.start_time) {
    const hhmm = hhmmFromISO(updateData.start_time)
    if (hhmm) payload.start_time = hhmm
  }
  if (updateData.end_time) {
    const hhmm = hhmmFromISO(updateData.end_time)
    if (hhmm) payload.end_time = hhmm
  }
  return request({
    url: `/api/trips/detail/update/${detailId}`,
    method: 'PUT',
    data: payload
  })
}

/**
 * 删除行程节点（移除景点）
 * DELETE /api/trips/detail/delete/{detail_id}
 */
export function deleteTripDetail(detailId) {
  return request({
    url: `/api/trips/detail/delete/${detailId}`,
    method: 'DELETE'
  })
}

/**
 * 新增行程天数
 * POST /api/trips/day/add  body: { trip_id }
 * @param {number} tripId
 */
export function addDay(tripId) {
  return request({
    url: '/api/trips/day/add',
    method: 'POST',
    data: { trip_id: Number(tripId) }
  })
}

/**
 * 删除行程天数
 * POST /api/trips/day/delete  body: { trip_id, day_num }
 */
export function deleteDay(tripId, dayNum) {
  return request({
    url: '/api/trips/day/delete',
    method: 'POST',
    data: { trip_id: Number(tripId), day_num: Number(dayNum) }
  })
}

export default {
  getTripList,
  createTrip,
  getTripDetail,
  updateTrip,
  deleteTrip,
  updateTripDetail,
  deleteTripDetail,
  addDay,
  deleteDay
}
