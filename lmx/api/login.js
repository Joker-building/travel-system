import request from '@/utils/request'

/**
 * 用户登录
 * 后端接口：POST /api/auth/login
 * @param {Object} data 登录参数 { username, password }
 * @returns {Promise<Object>} 响应对象，data.data 已转换为 { token, userInfo }
 */
export function login(data) {
  return request({
    url: '/api/auth/login',
    method: 'POST',
    data
  }).then(response => {
    // 后端返回 data.data = { access_token, token_type, user }
    // 转换为页面期望的 { token, userInfo } 结构，保持与原 mock 一致
    if (response && response.statusCode === 200 && response.data && response.data.code === 200) {
      const d = response.data.data || {}
      response.data.data = {
        token: d.access_token || d.token || '',
        userInfo: d.user || d.userInfo || {}
      }
    }
    return response
  })
}

/**
 * 用户注册
 * 后端接口：POST /api/auth/register
 * @param {Object} data 注册参数 { username, password, confirm_password, nickname, city, gender? }
 * @returns {Promise<Object>} 注册结果
 */
export function register(data) {
  // 后端要求 confirm_password，若调用方未传则用 password 兜底
  const payload = { ...data }
  if (payload.confirm_password === undefined && payload.password !== undefined) {
    payload.confirm_password = payload.password
  }
  return request({
    url: '/api/auth/register',
    method: 'POST',
    data: payload
  })
}

/**
 * 验证用户token是否有效
 * 后端无独立校验接口，复用 GET /api/user/info：能拿到用户信息即 token 有效
 * @returns {Promise<Object>} 验证结果
 */
export function verifyToken() {
  return request({
    url: '/api/user/info',
    method: 'GET'
  })
}

/**
 * 用户登出
 * 后端接口：POST /api/user/logout
 * @returns {Promise<Object>} 登出结果
 */
export function logout() {
  return request({
    url: '/api/user/logout',
    method: 'POST'
  })
}

export default {
  login,
  register,
  verifyToken,
  logout
}
