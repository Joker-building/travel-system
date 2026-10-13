/**
 * 认证工具 - 管理用户登录状态和Token
 */

// Token 存储键名
const TOKEN_KEY = 'user_token';
const USER_INFO_KEY = 'user_info';

/**
 * 获取保存的token
 * @returns {string|null} token或null
 */
export function getToken() {
	const token = uni.getStorageSync(TOKEN_KEY);

	return token || null;
}

/**
 * 保存token
 * @param {string} token 用户token
 */
export function setToken(token) {

	uni.setStorageSync(TOKEN_KEY, token);
}

/**
 * 移除token
 */
export function removeToken() {

	uni.removeStorageSync(TOKEN_KEY);
}

/**
 * 获取用户信息
 * @returns {Object|null} 用户信息或null
 */
export function getUserInfo() {
	const userInfo = uni.getStorageSync(USER_INFO_KEY);

	return userInfo || null;
}

/**
 * 保存用户信息
 * @param {Object} userInfo 用户信息对象
 */
export function setUserInfo(userInfo) {

	uni.setStorageSync(USER_INFO_KEY, userInfo);
}

/**
 * 移除用户信息
 */
export function removeUserInfo() {

	uni.removeStorageSync(USER_INFO_KEY);
}

/**
 * 检查用户是否已登录
 * @returns {boolean} 是否已登录
 */
export function isLoggedIn() {
	const hasToken = !!getToken();

	return hasToken;
}

/**
 * 保存完整的登录状态
 * @param {string} token 用户token
 * @param {Object} userInfo 用户信息
 */
export function saveLoginState(token, userInfo) {
	// 确保两个操作都成功完成
	try {
		setToken(token);
		setUserInfo(userInfo);
	} catch (error) {
		console.error('保存登录状态失败:', error);
		// 如果保存失败，清理状态避免不一致
		clearLoginState();
		throw error;
	}
	// 确认一下是否保存成功
	setTimeout(() => {
		const savedToken = getToken();
		const savedUserInfo = getUserInfo();

	}, 100);
}

/**
 * 清除登录状态
 */
export function clearLoginState() {

	removeToken();
	removeUserInfo();
}

export default {
	getToken,
	setToken,
	removeToken,
	getUserInfo,
	setUserInfo,
	removeUserInfo,
	isLoggedIn,
	saveLoginState,
	clearLoginState
};