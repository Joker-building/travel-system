import request from '@/utils/request'
import {
	API_CONFIG
} from '@/utils/config'

// 获取API基础URL
const baseUrl = API_CONFIG.BASE_URL;

/**
 * 获取用户个人信息
 * @returns {Promise<Object>} 用户信息
 */
export function getUserInfo() {
	try {
		return request({
			url: '/api/user/info',
			method: 'GET'
		});
	} catch (error) {
		console.error('准备获取用户信息请求出错:', error);
		return Promise.reject(error);
	}
}

/**
 * 更新用户个人信息
 * @param {Object} data 用户更新的信息
 * @param {string} data.email 邮箱
 * @param {string} data.firstName 名
 * @param {string} data.lastName 姓
 * @param {string} data.nationality 国籍
 * @param {string} data.preferredLanguage 偏好语言
 * @param {string} data.phone 手机号
 * @param {string} data.gender 性别(male/female/other)
 * @param {string} data.birthDate 出生日期
 * @param {string} data.avatarUrl 头像URL(base64格式)
 * @returns {Promise<Object>} 更新结果
 */
export function updateUserInfo(data) {
	try {


		return request({
			url: '/api/user/update',
			method: 'PUT',
			data
		});
	} catch (error) {
		console.error('准备更新用户信息请求出错:', error);
		return Promise.reject(error);
	}
}

/**
 * 上传用户头像（multipart/form-data）
 * 后端接口：POST /api/user/avatar/upload，后端会同时更新用户 avatar_url
 * @param {string} filePath 临时图片路径（uni.chooseImage 返回的 tempFilePaths[0]）
 * @returns {Promise<Object>} 响应对象，data.data.avatar_url 为可访问的头像路径
 */
export function uploadAvatar(filePath) {
	return new Promise((resolve, reject) => {
		// 动态引入避免循环依赖
		import('@/utils/auth').then(auth => {
			const token = auth.getToken()
			uni.uploadFile({
				url: baseUrl + '/api/user/avatar/upload',
				filePath,
				name: 'file',
				fileType: 'image',
				header: {
					'Authorization': token ? `Bearer ${token}` : ''
				},
				success: (uploadRes) => {
					try {
						const data = JSON.parse(uploadRes.data)
						resolve({ statusCode: uploadRes.statusCode, data })
					} catch (e) {
						reject({ errMsg: '头像上传响应解析失败', raw: uploadRes })
					}
				},
				fail: (err) => {
					reject(err)
				}
			})
		}).catch(reject)
	})
}

/**
 * 退出登录
 * 后端接口：POST /api/user/logout
 * @returns {Promise<Object>} 登出结果
 */
export function logout() {
	return request({
		url: '/api/user/logout',
		method: 'POST'
	})
}

/**
 * 获取用户提醒列表
 * @returns {Promise<Object>} 提醒列表
 */
export function getUserRemindList() {
	try {


		return request({
			url: '/user/remind/list',
			method: 'GET'
		});
	} catch (error) {
		console.error('准备获取用户提醒列表请求出错:', error);
		return Promise.reject(error);
	}
}

/**
 * 获取论坛文章列表
 * @returns {Promise<Array>} 文章列表
 */
export function getForumArticles() {
	try {
		return request({
			url: '/user/forum/article',
			// url: '/abc',
			method: 'GET'
		});
	} catch (error) {
		console.error('准备获取论坛文章列表请求出错:', error);
		return Promise.reject(error);
	}
}

/**
 * 发布论坛文章
 * @param {Object} articleData 文章数据
 * @param {number} articleData.userId 用户ID
 * @param {string} articleData.title 文章标题
 * @param {string} articleData.richContent 富文本内容
 * @param {number} articleData.category 文章分类ID(0-未分类,1-综合,2-签证,3-旅行,4-住宿,5-美食,6-文化,7-其他)
 * @returns {Promise<Object>} 发布结果
 */
export function publishForumArticle(articleData) {
	try {
		return request({
			url: '/user/forum/article',
			method: 'POST',
			data: articleData
		});
	} catch (error) {
		console.error('准备发布论坛文章请求出错:', error);
		return Promise.reject(error);
	}
}

/**
 * 获取文章评论列表
 * @param {string|number} articleId - 文章ID
 * @returns {Promise<object>} 返回评论数据
 */
export function getArticleComments(articleId) {
	// 检查articleId是否存在
	if (!articleId) {
		console.error('【API-获取评论】文章ID不存在');
		return Promise.reject({
			statusCode: 400,
			data: {
				code: 400,
				message: '文章ID不能为空'
			}
		});
	}
	// 打印文章ID信息
	// 确保articleId是字符串类型
	const articleIdStr = String(articleId);
	// 记录请求开始时间
	const startTime = Date.now();
	// 使用request统一请求函数，不需要手动构建完整URL
	return request({
		url: '/user/forum/comment?articleId=' + articleIdStr,
		method: 'GET',
	}).then(response => {
		console.log('得到的评论数据：', response)
		// 计算请求耗时
		const endTime = Date.now();
		const duration = endTime - startTime;
		// 详细记录响应状态和数据
		if (response.statusCode === 200) {
			// 分析响应数据
			if (response.data) {
				if (typeof response.data === 'object') {
					if (response.data.data && Array.isArray(response.data.data)) {
						// 记录一些评论数据的结构，便于调试
						if (response.data.data.length > 0) {
							const firstComment = response.data.data[0];
						}
					} else {}
				} else {}
			} else {}
		} else {
			console.error(`【API-获取评论】请求失败, HTTP状态码: ${response.statusCode}`);
			if (response.data) {
				console.error('【API-获取评论】错误响应数据:', JSON.stringify(response.data));
			}
		}

		return response;
	}).catch(error => {
		const endTime = Date.now();
		const duration = endTime - startTime;
		console.error(`【API-获取评论】请求发生错误, 耗时: ${duration}ms`);
		console.error('【API-获取评论】错误详情:', error);

		return Promise.reject({
			statusCode: error.statusCode || 500,
			data: error.data || {
				code: 500,
				message: error.errMsg || '网络请求失败'
			}
		});
	});
}

/**
 * 发布评论
 * @param {Object} params - 评论参数对象
 * @param {string|number} params.articleId - 文章ID
 * @param {string|number} params.userId - 用户ID
 * @param {string} params.content - 评论内容
 * @returns {Promise<object>} 返回评论结果
 */
export function publishComment(params) {


	// 深拷贝参数，避免修改原始对象
	const requestParams = {
		...params
	};

	// 检查articleId是否存在
	if (!requestParams.articleId) {
		console.error('【API-发布评论】文章ID不存在');
		return Promise.reject({
			statusCode: 400,
			data: {
				code: 400,
				message: '文章ID不能为空'
			}
		});
	}

	// 检查并确保articleId是字符串类型
	if (typeof requestParams.articleId !== 'string') {

		requestParams.articleId = String(requestParams.articleId);
	}

	// 检查userId是否存在，如不存在尝试从本地获取
	if (!requestParams.userId) {

		try {
			const userInfo = uni.getStorageSync('userInfo');
			if (userInfo && userInfo.id) {
				requestParams.userId = userInfo.id;

			} else {
				console.error('【API-发布评论】本地存储中无用户信息');
				return Promise.reject({
					statusCode: 401,
					data: {
						code: 401,
						message: '用户未登录'
					}
				});
			}
		} catch (error) {
			console.error('【API-发布评论】读取本地存储失败:', error.message || error);
			return Promise.reject({
				statusCode: 500,
				data: {
					code: 500,
					message: '获取用户信息失败'
				}
			});
		}
	}

	// 检查评论内容是否为空
	if (!requestParams.content || requestParams.content.trim() === '') {
		console.error('【API-发布评论】评论内容为空');
		return Promise.reject({
			statusCode: 400,
			data: {
				code: 400,
				message: '评论内容不能为空'
			}
		});
	}

	// 记录请求参数详情


	// 记录请求开始时间
	const startTime = Date.now();


	// 使用request统一请求函数
	return request({
		url: '/user/forum/comment',
		method: 'POST',
		data: requestParams
	}).then(response => {
		// 计算请求耗时
		const endTime = Date.now();
		const duration = endTime - startTime;


		// 详细记录响应状态和数据


		if (response.statusCode === 200 || response.statusCode === 201) {


			// 分析响应数据
			if (response.data) {
				if (typeof response.data === 'object') {
					// 记录业务状态码


					if (response.data.code === 200 || response.data.code === 0) {


						// 记录返回的评论ID
						if (response.data.data && response.data.data.id) {

						}
					} else {
						console.error('【API-发布评论】业务处理失败:', response.data.message || '未知错误');
					}
				} else {

				}
			} else {

			}
		} else {
			console.error(`【API-发布评论】请求失败, HTTP状态码: ${response.statusCode}`);
			if (response.data) {
				console.error('【API-发布评论】错误响应数据:', JSON.stringify(response.data));
			}
		}

		return response;
	}).catch(error => {
		const endTime = Date.now();
		const duration = endTime - startTime;
		console.error(`【API-发布评论】请求发生错误, 耗时: ${duration}ms`);
		console.error('【API-发布评论】错误详情:', error);

		return Promise.reject({
			statusCode: error.statusCode || 500,
			data: error.data || {
				code: 500,
				message: error.errMsg || '网络请求失败'
			}
		});
	});
}

export default {
	getUserInfo,
	updateUserInfo,
	uploadAvatar,
	logout,
	getUserRemindList,
	getForumArticles,
	publishForumArticle,
	getArticleComments,
	publishComment
};