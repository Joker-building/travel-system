import request from '@/utils/request'

/**
 * 获取天气访问令牌
 *
 * 说明：和风天气密钥现由后端 /api/proxy/weather 统一保管，
 * 前端不再需要持有或刷新任何天气 token，故此处直接返回成功的占位响应，
 * 以兼容既有调用方（App.vue / aiAssistant / user 等）。
 */
export function weatherToken() {
	return request({
		url: '/api/proxy/weather',
		method: 'GET',
		data: {
			endpoint: 'now',
			location: '114.31,30.59'
		}
	}).then((response) => {
		return response;
	}).catch(() => {
		// 即便失败也不影响主流程
		return {
			data: {
				code: 200,
				message: 'ok',
				data: {}
			}
		};
	});
}
