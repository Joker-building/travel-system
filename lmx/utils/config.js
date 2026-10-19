/**
 * 全局配置文件
 *
 * API 基地址（BASE_URL）解耦说明 —— 支持多机联调与真机调试
 * 解析优先级（从高到低）：
 *   1) 运行时手动覆盖：uni.setStorageSync('API_BASE_URL', 'http://192.168.1.100:8000')
 *      —— 换电脑 / 真机调试时无需改代码重新编译，在"我的"页或调试控制台设置一次即可生效。
 *   2) 环境变量：生产包（process.env.NODE_ENV === 'production'）走 PROD_BASE_URL，其余走 DEV_BASE_URL。
 *   3) 开发默认：DEV_BASE_URL。真机调试时把下面这个 IP 改成你电脑的局域网地址
 *      （如 http://192.168.1.100:8000），且手机与电脑须连同一 WiFi。
 */

// 开发环境基地址（本机浏览器 / H5 调试；真机调试请改为电脑局域网 IP）
const DEV_BASE_URL = 'http://127.0.0.1:8000';
// 生产环境基地址（打包发行后自动启用）
const PROD_BASE_URL = 'https://travel.jasenon.xyz';

/**
 * 运行时解析 API 基地址。
 * 推荐在每次发起请求时调用（而非仅在模块加载时取一次），
 * 以便读取运行时手动覆盖值（真机调试 / 多机联调场景）。
 * @returns {string} API 基地址
 */
export function getApiBaseUrl() {
	// 1) 运行时手动覆盖（优先级最高）
	try {
		const override = uni.getStorageSync('API_BASE_URL');
		if (override) return override;
	} catch (e) {
		// 忽略存储读取异常，继续走下面的规则
	}
	// 2) 按环境切换
	if (process.env.NODE_ENV === 'production') {
		return PROD_BASE_URL;
	}
	// 3) 开发默认
	return DEV_BASE_URL;
}

// API 基地址配置
export const API_CONFIG = {
	// 模块加载时的解析值（向后兼容：request.js 等仍可直接读取）
	BASE_URL: getApiBaseUrl(),
	// API超时时间（毫秒）
	TIMEOUT: 10000,
	// API版本
	VERSION: 'v1'
};

// 高德地图API配置（密钥由后端代理保管，前端不再持有真实 Key）
export const AMAP_CONFIG = {
	key: '',
	securityJsCode: '',
	baseUrl: 'https://restapi.amap.com'
};

export default {
	API_CONFIG,
	AMAP_CONFIG,
	getApiBaseUrl
};
