import {
	getToken
} from '@/utils/auth'
import {
	API_CONFIG,
	getApiBaseUrl
} from '@/utils/config'

// 请求超时时间 - 从配置文件中获取
const TIMEOUT = API_CONFIG.TIMEOUT;

/**
 * 请求拦截函数
 * @param {Object} config 请求配置
 * @returns {Object} 处理后的请求配置
 */
function requestInterceptor(config) {
	// 生成请求ID用于追踪
	const requestId = Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
	config.requestId = requestId;



	// 从auth工具获取token
	const token = getToken();


	// 初始化header对象，避免未定义错误
	config.header = config.header || {};

	if (token) {
		// 添加token到header，只有在header中没有设置Authorization的情况下才添加
		if (!config.header['Authorization']) {
			config.header['Authorization'] = `Bearer ${token}`;

		} else {

		}
	}

	// 设置默认Content-Type，仅当没有设置时
	if (!config.header['Content-Type']) {
		config.header['Content-Type'] = 'application/json';

	} else {

	}

	// 添加X-Requested-With，有助于防止CSRF攻击并标识AJAX请求
	// if (!config.header['X-Requested-With']) {
	//   config.header['X-Requested-With'] = 'XMLHttpRequest';

	// }

	// 打印请求头信息，便于调试


	// 打印请求体信息，如果存在
	if (config.data) {

	}

	return config;
}

/**
 * 响应拦截函数
 * @param {Object} response 响应数据
 * @returns {Object|Promise} 处理后的响应数据或错误
 */
function responseInterceptor(response) {
	// uni-app 请求成功回调的数据结构与axios不同
	// response = { data, statusCode, header, cookies }

	// 获取请求ID
	const requestId = response.config ? response.config.requestId : '未知';

	// 记录响应状态码，便于调试


	// 记录响应头
	if (response.header) {

	}

	// 尝试记录响应体大小
	const dataSize = response.data ?
		(typeof response.data === 'string' ? response.data.length : JSON.stringify(response.data).length) : 0;


	if (response.statusCode === 200) {
		// HTTP状态为200，返回数据


		// 尝试记录小部分响应数据以供调试
		if (response.data) {
			if (typeof response.data === 'string') {

			} else {


				// 检查业务状态码，即使HTTP状态为200，业务状态可能是未授权
				if (response.data && response.data.code === 401) {
					console.error(`[业务错误401] ID:${requestId} | 业务状态码表示未授权: ${response.data.message}`);

					// 防止在登录页面触发401时导致循环
					const pages = getCurrentPages();
					const currentPage = pages[pages.length - 1];
					const isLoginPage = currentPage && currentPage.route && currentPage.route.includes('login');

					if (!isLoginPage) {
						console.log(`[错误处理] ID:${requestId} | 收到业务401响应，清除登录状态并跳转`);
						// 异步导入auth模块
						import('./auth').then(auth => {
							auth.clearLoginState();

							// 重定向到登录页
							uni.reLaunch({
								url: '/pages/login/login'
							});
						});

						// 创建一个包含原始响应的错误对象
						const error = {
							statusCode: 401, // 将业务状态码映射为HTTP状态码
							data: response.data,
							config: response.config,
							errMsg: response.data.message || '用户未登录',
							requestId: requestId
						};

						return Promise.reject(error);
					} else {
						console.log(`[错误处理] ID:${requestId} | 登录页面收到业务401响应，不进行重定向`);
					}
				}
			}
		}

		return response;
	} else {
		// 处理HTTP错误
		console.log(`[响应失败] ID:${requestId} | 状态码:${response.statusCode}`);
		return Promise.reject(handleError(response));
	}
}

/**
 * 统一错误处理
 * @param {Object} err 错误对象
 * @returns {Object} 处理后的错误信息
 */
function handleError(err) {
	// 获取请求ID
	const requestId = err.config ? err.config.requestId : '未知';

	let message = '请求失败';

	if (err.statusCode) {
		// 服务器返回错误状态码
		const status = err.statusCode;
		switch (status) {
			case 401:
				message = '未授权，请重新登录';
				console.error(`[错误401] ID:${requestId} | 未授权，需要重新登录`);

				// 防止在登录页面触发401时导致循环
				const pages = getCurrentPages();
				const currentPage = pages[pages.length - 1];
				const isLoginPage = currentPage && currentPage.route && currentPage.route.includes('login');

				if (!isLoginPage) {
					console.log(`[错误处理] ID:${requestId} | 收到401响应，清除登录状态`);
					// 导入清除登录状态的函数
					import('./auth').then(auth => {
						auth.clearLoginState();

						// 重定向到登录页
						uni.reLaunch({
							url: '/pages/login/login'
						});
					});
				} else {
					console.log(`[错误处理] ID:${requestId} | 登录页面收到401响应，不进行重定向`);
				}
				break;
			case 403:
				message = '拒绝访问，服务器理解请求但拒绝执行';
				console.error(`[错误403] ID:${requestId} | 拒绝访问，可能是权限问题`);
				// 打印详细信息以帮助调试
				console.error(`[错误403详情] ID:${requestId} | 请求URL:`, err.config ? err.config.url : '未知');
				console.error(`[错误403详情] ID:${requestId} | 请求方法:`, err.config ? err.config.method : '未知');
				console.error(`[错误403详情] ID:${requestId} | 请求头:`, err.config ? JSON.stringify(err.config.header) :
				'未知');
				if (err.data) {
					console.error(`[错误403详情] ID:${requestId} | 响应数据:`, JSON.stringify(err.data));
				}
				break;
			case 404:
				message = '请求的资源不存在';
				console.error(`[错误404] ID:${requestId} | 资源不存在:`, err.config ? err.config.url : '未知');
				break;
			case 500:
				message = '服务器内部错误';
				console.error(`[错误500] ID:${requestId} | 服务器内部错误`);
				break;
			default:
				message = `请求错误(${status})`;
				console.error(`[错误${status}] ID:${requestId} | 未预期的错误状态码`);
		}
	} else {
		// 请求发出但没有收到响应
		message = '网络错误，服务器没有响应';
		console.error(`[网络错误] ID:${requestId} | 服务器无响应`);
	}

	console.error(`[错误摘要] ID:${requestId} | 错误信息:${message}`);

	// 记录更多错误信息
	if (err.data) {
		console.error(`[错误响应体] ID:${requestId} |`, JSON.stringify(err.data));
	}

	return {
		errMsg: message,
		requestId: requestId,
		...err
	};
}

/**
 * 统一请求函数
 * @param {Object} options 请求配置
 * @returns {Promise} 请求Promise对象
 */
function request(options) {
	// 构造完整URL
	let url = options.url;

	// 如果不是以http开头的完整URL，添加BASE_URL（运行时解析，支持多机/真机调试）
	if (!url.startsWith('http')) {
		const baseUrl = getApiBaseUrl();
		// 处理有无前导斜杠的情况
		if (url.startsWith('/')) {
			url = baseUrl + url;
		} else {
			url = baseUrl + '/' + url;
		}
	}

	// 合并请求配置
	const config = {
		url: url.trim(),
		timeout: options.timeout || TIMEOUT,
		method: options.method || 'GET',
		data: options.data,
		params: options.params,
		header: options.header || {}
	};

	// 请求拦截
	const interceptedConfig = requestInterceptor(config);

	// 记录请求信息

	// 返回Promise
	return new Promise((resolve, reject) => {
		uni.request({
			...interceptedConfig,
			success: (res) => {
				// 将请求配置添加到响应对象，以便追踪
				res.config = interceptedConfig;

				try {

					const result = responseInterceptor(res);
					resolve(result);
				} catch (error) {
					console.error(`[响应处理错误] ID:${interceptedConfig.requestId} |`, error);
					reject(error);
				}
			},
			fail: (err) => {
				// 将请求配置添加到错误对象，以便追踪
				err.config = interceptedConfig;

				console.error(`[请求失败] ID:${interceptedConfig.requestId} | 错误:`, err.errMsg ||
					'未知错误');
				reject(handleError(err));
			}
		});
	});
}

export default request;