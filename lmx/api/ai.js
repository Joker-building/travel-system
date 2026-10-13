import request from '@/utils/request'

/**
 * AI 对话相关接口封装
 * 后端路由前缀：/api/ai
 * 响应统一为 { code, message, data }
 *
 * 后端 chat 返回的 data 形如：
 *   { success, response_type, session_id, chat_title, narrative?, answer?, needs_save?, data? }
 *   - response_type=itinerary 时带 needs_save=true 和 data（AI 生成的计划数据），不再自动落库，
 *     需前端确认后调用 saveItinerary(data.data) 才写入行程。
 * 前端 ai_generate.vue 期望：data.data.ai_display_content + data.data.session_id
 * 本层负责把 narrative/answer 归一化为 ai_display_content，并对会话/消息做字段映射。
 */

/**
 * AI对话主接口：智能行程生成 / 智能问答
 * POST /api/ai/chat  body: { session_id?, message }
 * @param {Object} param { session_id?, message }
 * @returns {Promise<Object>} 响应对象，data.data 已附加 ai_display_content 字段
 */
export function aiChat({ session_id, message } = {}) {
  const payload = { message }
  if (session_id !== undefined && session_id !== null && session_id !== '') {
    payload.session_id = Number(session_id)
  }
  return request({
    url: '/api/ai/chat',
    method: 'POST',
    data: payload,
    // AI 调用 DeepSeek 生成回复可能需要 20-60 秒（带历史上下文时偶尔 60-150 秒），
    // 120 秒实测偶发超时（前端 catch 兜底报"请求超时或网络异常"），先调到 180 秒给足余量；
    // 如仍超时，把后端 uvicorn 终端的"DeepSeek 调用耗时 XX 秒"贴给我看具体耗时
    timeout: 180000
  }).then(response => {
    if (response && response.statusCode === 200 && response.data && response.data.code === 200) {
      const d = response.data.data || {}
      // 归一化展示内容：行程用 narrative，问答用 answer
      let display = ''
      if (d.response_type === 'itinerary') {
        display = d.narrative || (d.data && d.data.narrative) || ''
      } else if (d.response_type === 'question_answer') {
        display = d.answer || ''
      }
      // 兜底：若模型返回了 data.answer / data.narrative 但顶层没有
      if (!display && d.data) {
        display = d.data.narrative || d.data.answer || ''
      }
      d.ai_display_content = display || '暂未获取到回复'
      response.data.data = d
    }
    return response
  })
}

/**
 * 获取用户所有历史会话列表
 * GET /api/ai/sessions
 * @returns {Promise<Object>} 响应对象，data.data.sessions 已转换为页面期望结构：
 *   [{ session_id, title, update_time, trip_id }]
 */
export function getSessions() {
  return request({
    url: '/api/ai/sessions',
    method: 'GET'
  }).then(response => {
    if (response && response.statusCode === 200 && response.data && response.data.code === 200) {
      const list = Array.isArray(response.data.data) ? response.data.data : []
      response.data.data = {
        sessions: list.map(s => ({
          session_id: s.id,
          title: s.session_title || s.title || '未命名会话',
          create_time: s.create_time || '',
          update_time: s.update_time || '',
          trip_id: s.trip_id || null
        }))
      }
    }
    return response
  })
}

/**
 * 获取指定会话的所有消息记录
 * GET /api/ai/sessions/{session_id}/messages
 * @param {number} sessionId 会话id
 * @returns {Promise<Object>} 响应对象，data.data.messages 已转换为页面期望结构：
 *   [{ role: 'system'|'user', content }]
 */
export function getSessionMessages(sessionId) {
  return request({
    url: `/api/ai/sessions/${sessionId}/messages`,
    method: 'GET'
  }).then(response => {
    if (response && response.statusCode === 200 && response.data && response.data.code === 200) {
      const list = Array.isArray(response.data.data) ? response.data.data : []
      response.data.data = {
        messages: list.map(m => ({
          id: m.id,
          session_id: m.session_id,
          // 后端 assistant 角色对应前端展示的 system（AI 消息）
          role: m.role === 'assistant' ? 'system' : m.role,
          content: m.content || '',
          create_time: m.create_time || ''
        }))
      }
    }
    return response
  })
}

/**
 * 创建新会话
 * POST /api/ai/sessions/create?title=xxx
 * @param {string} title 会话标题（可选，默认"新对话"）
 * @returns {Promise<Object>} 响应对象，data.data = { session_id, session_title }
 */
export function createSession(title = '新对话') {
  return request({
    url: `/api/ai/sessions/create?title=${encodeURIComponent(title)}`,
    method: 'POST'
  })
}

/**
 * 删除会话
 * DELETE /api/ai/sessions/{session_id}
 * @param {number} sessionId 会话id
 * @returns {Promise<Object>} 响应对象
 */
export function deleteSession(sessionId) {
  return request({
    url: `/api/ai/sessions/${sessionId}`,
    method: 'DELETE'
  })
}

/**
 * 查询语音服务是否可用（Vosk 模型是否已加载）
 * GET /api/ai/voice/status
 * @returns {Promise<Object>} 响应对象，data.data.available 为 bool
 */
export function voiceStatus() {
  return request({
    url: '/api/ai/voice/status',
    method: 'GET'
  }).then(response => {
    if (response && response.statusCode === 200 && response.data && response.data.code === 200) {
      const available = !!(response.data.data && response.data.data.available)
      response.data.data = {
        available
      }
    }
    return response
  })
}

/**
 * 确认将 AI 生成的计划保存为行程（用户在前端点「添加到行程」后调用）
 * POST /api/planning/itinerary/save  body: { data }
 * @param {Object} itineraryData AI 返回的 itinerary 计划数据（chat 响应 data.data.data）
 * @returns {Promise<Object>} 响应对象，成功时 data.data = { trip_id }
 */
export function saveItinerary(itineraryData) {
  return request({
    url: '/api/planning/itinerary/save',
    method: 'POST',
    data: { data: itineraryData }
  })
}

export default {
  aiChat,
  getSessions,
  getSessionMessages,
  createSession,
  deleteSession,
  voiceStatus,
  saveItinerary
}
