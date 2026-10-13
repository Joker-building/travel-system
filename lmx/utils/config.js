/**
 * 全局配置文件
 */

// API基地址配置
export const API_CONFIG = {
	// 主API基地址
	BASE_URL: 'http://127.0.0.1:8000',
	// BASE_URL: 'https://travel.jasenon.xyz',

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
	AMAP_CONFIG
};