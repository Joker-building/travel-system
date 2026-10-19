<template>
	<view class="profile-container">
		<!-- 顶部背景 -->
		<view class="profile-background"></view>

		<scroll-view scroll-y class="profile-content" :scroll-with-animation="false">
			<!-- 加载中状态 -->
			<view class="loading-container" v-if="loading">
				<view class="loading-spinner"></view>
				<text class="loading-text">加载个人信息中...</text>
			</view>

			<!-- 错误提示 -->
			<view class="error-container" v-else-if="errorMsg">
				<view class="error-icon">
					<text class="fas fa-exclamation-circle"></text>
				</view>
				<text class="error-text">{{errorMsg}}</text>
				<view class="error-action" @click="loadUserInfo">
					<text class="action-text">重新加载</text>
				</view>
			</view>

			<template v-else>
				<!-- 用户基本信息卡片 -->
				<view class="profile-header">
					<view class="profile-avatar-section">
						<image class="profile-avatar" :src="getAvatarUrl()|| '/static/default-avatar.jpg'"
							mode="aspectFill"></image>
						<view class="profile-edit-avatar" @click="editAvatar">
							<view class="edit-icon"></view>
						</view>
					</view>
					<view class="profile-info">
						<text class="profile-name">{{userInfo.nickname}} </text>
						<!-- <text class="profile-name">{{userInfo.lastName}} {{userInfo.firstName}}</text> -->
						<text class="profile-username"> @{{userInfo.username}}</text>
						<!-- <view class="profile-tags">
							<view class="profile-tag">{{getNationalityText(userInfo.nationality)}}</view>
							<view class="profile-tag">{{getLanguageName(userInfo.preferredLanguage)}}</view>
						</view> -->
					</view>
				</view>

				<!-- 快捷功能区 -->
				<!-- <view class="quick-actions">
          <view class="quick-action-item" @click="navigateTo('myTrips')">
            <text class="action-number">3</text>
            <text class="action-text">我的行程</text>
          </view>
          <view class="quick-action-item" @click="navigateTo('favorites')">
            <text class="action-number">12</text>
            <text class="action-text">收藏景点</text>
          </view>
          <view class="quick-action-item" @click="navigateTo('reviews')">
            <text class="action-number">5</text>
            <text class="action-text">我的点评</text>
          </view>
        </view> -->

				<!-- 用户详细信息列表 -->
				<view class="profile-details">
					<view class="detail-section">
						<view class="section-header">
							<text class="section-title">基本信息</text>
							<view class="section-action" @click="editProfile">编辑</view>
						</view>
						<!-- <view class="detail-item">
							<text class="item-label">邮箱</text>
							<text class="item-value">{{userInfo.email}}</text>
						</view> -->
						<view class="detail-item">
							<text class="item-label">联系电话</text>
							<text class="item-value">{{ desensitizePhone(userInfo.phone) }}</text>
						</view>
						<view class="detail-item">
							<text class="item-label">性别</text>
							<text class="item-value">{{getGenderText(userInfo.gender)}}</text>
						</view>
						<view class="detail-item">
							<text class="item-label">常驻地区</text>
							<text class="item-value">{{userInfo.city}}</text>
						</view>
					</view>

					<view class="detail-section">
						<view class="section-header">
							<text class="section-title">账号信息</text>
						</view>
						<view class="detail-item">
							<text class="item-label">注册时间</text>
							<text class="item-value">{{formatDate(userInfo.create_time)}}</text>
						</view>
						<!-- <view class="detail-item">
							<text class="item-label">最后登录</text>
							<text class="item-value">{{formatDate(userInfo.lastLogin)}}</text>
						</view> -->
					</view>
				</view>

				<!-- 退出登录按钮 -->
				<view class="profile-actions">
					<button class="action-button logout" @click="logout">
						<text class="button-text">退出登录</text>
					</button>
				</view>
			</template>
		</scroll-view>
	</view>
</template>

<script>
	import {
		getUserInfo,
		updateUserInfo,
		uploadAvatar
	} from '@/api/user';
	import {
		clearLoginState,
		getToken
	} from '@/utils/auth';
	import {
		getApiBaseUrl
	} from '@/utils/config';

	export default {
		data() {
			return {
			baseUrl: getApiBaseUrl(),
			currentTab: 'profile',
				loading: false,
				errorMsg: '',
				userInfo: {
					id: null,
					username: '', //✔
					// email: '',
					// firstName: '',
					// lastName: '',
					// nationality: '',
					// preferredLanguage: '',
					phone: '', //✔
					gender: '', //✔
					avatar_url: '',
					create_time: '',
					city: '',
					// lastLogin: '',
					userStatus: 1
				}
			}
		},
		onShow() {
			this.loadUserInfo();
		},
		methods: {
			// 手机号脱敏显示 138****1234
			desensitizePhone(phone) {
				if (!phone) return '未设置';
				// 只保留前3位 + 后4位，中间****
				if (phone.length >= 8) {
					return phone.substr(0, 3) + '****' + phone.substr(-4);
				}
				return phone;
			},
			async loadUserInfo() {
				this.loading = true;
				this.errorMsg = '';

				try {

					const response = await getUserInfo();

					if (response.statusCode === 200 && response.data) {

						// 判断API返回的状态码，接口返回code=200为成功
						if (response.data.code === 200 && response.data.data) {

							// 更新用户信息
							this.userInfo = {
								...this.userInfo,
								...response.data.data
							};
							// 打印信息
							console.log('后端获取的用户信息数据：', response.data.data)
							console.log('前端保存的信息数据：', this.userInfo)
							// 更新本地存储
							uni.setStorageSync('userInfo', this.userInfo);

						} else {
							this.errorMsg = '获取用户信息失败: ' + (response.data.message || '服务器返回数据格式不正确');
							console.error(this.errorMsg, response.data);
						}
					} else if (response.statusCode === 401 || (response.data && response.data.code === 401)) {
						this.errorMsg = '登录状态已过期，请重新登录';
						console.error('用户未登录或登录已过期:', response.data);

						// 清除登录状态并重定向到登录页
						setTimeout(() => {
							clearLoginState();
							uni.reLaunch({
								url: '/pages/login/login'
							});
						}, 1500);
					} else {
						this.errorMsg = '获取用户信息失败: ' + (response.data ? response.data.message || '未知错误' : '网络错误');
						console.error('获取用户信息失败:', response.data || response);
					}
				} catch (error) {
					console.error('获取用户信息异常:', error);
					this.errorMsg = '获取用户信息失败: ' + (error.message || '网络异常');

					// 如果接口调用失败，检查是否有本地存储的用户信息
					this.loadLocalUserInfo();
				} finally {
					this.loading = false;
				}

			},

			// 从本地存储加载用户信息（仅作离线缓存展示，非 mock 数据）
			loadLocalUserInfo() {
				try {
					const localUserInfo = uni.getStorageSync('userInfo');
					if (localUserInfo) {
						this.userInfo = localUserInfo;
						// 清除错误消息，因为我们已经加载了缓存数据
						this.errorMsg = '';
					} else {
						// 本地无缓存，保持错误状态，不填充任何假数据
						console.warn('本地无用户信息缓存，保持错误状态');
					}
				} catch (e) {
					console.error('读取本地用户信息失败:', e);
				}
			},

			navigateTo(target) {
				if (target === 'editProfile') {
					uni.navigateTo({
						url: '/pages/profile/editProfile'
					});
				} else {
					// uni.showToast({
					//   title: `${target}功能开发中`,
					//   icon: 'none'
					// });
				}
			},
			getAvatarUrl() {
				// 如果有头像，拼接完整URL；否则使用默认头像
				if (this.userInfo.avatar_url) {
					return this.baseUrl + this.userInfo.avatar_url;
				}
				return '/static/default-avatar.jpg'; // 默认头像路径
			},
			editAvatar() {
				uni.chooseImage({
					count: 1,
					sizeType: ['compressed'],
					sourceType: ['album', 'camera'],
					success: async (res) => {
						const tempFilePath = res.tempFilePaths[0];
						console.log('图片信息：', tempFilePath);
						// 显示加载中
						uni.showLoading({
							title: '上传中...'
						});

						try {
							// 调用统一封装的上传接口：POST /api/user/avatar/upload
							// 后端会同时更新用户 avatar_url，无需再调 updateUserInfo
							const uploadRes = await uploadAvatar(tempFilePath);
							const data = uploadRes.data;

							if (data.detail?.code === 400) {
								throw new Error("图片过大，请上传不超过1MB的图片");
							}
							if (data.code !== 200) throw new Error(data.message);

							// 后端返回的头像 URL（data.data.avatar_url）
							const avatar_url = data.data.avatar_url;
							console.log('头像URL：', avatar_url);

							this.userInfo.avatar_url = avatar_url;
							uni.setStorageSync('userInfo', this.userInfo);
							uni.showToast({
								title: '头像更新成功',
								icon: 'success'
							});
							this.loadUserInfo();
						} catch (error) {
							console.error('上传失败：', error);
							uni.showToast({
								title: '失败：' + (error.message || '未知错误'),
								icon: 'none'
							});
						} finally {
							uni.hideLoading();
						}
					}
				});
			},

			editProfile() {
				this.navigateTo('editProfile');
			},
			logout() {
				uni.showModal({
					title: '退出登录',
					content: '确定要退出登录吗？',
					success: (res) => {
						if (res.confirm) {
							clearLoginState();
							uni.removeStorageSync('userInfo')
							uni.reLaunch({
								url: '/pages/login/login'
							});
						}
					}
				});
			},
			getLanguageName(code) {
				const languages = {
					'en': 'English',
					'zh': '中文',
					'ja': '日本語',
					'ko': '한국어'
				};
				return languages[code] || code;
			},
			getGenderText(gender) {
				const genderMap = {
					'male': '男',
					'female': '女',
					'other': '其他'
				};
				return genderMap[gender] || '未设置';
			},
			getNationalityText(nationality) {
				const nationalityMap = {
					'china': '中国',
					'usa': '美国',
					'japan': '日本',
					'korea': '韩国',
					'uk': '英国',
					'germany': '德国',
					'france': '法国'
				};
				return nationalityMap[nationality] || nationality;
			},
			formatDate(date) {
				if (!date) return '未设置';
				try {
					const d = new Date(date);
					return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
				} catch (e) {
					return '未设置';
				}
			},
			switchTab(tab) {
				if (tab === this.currentTab) return;

				switch (tab) {
					case 'home':
						uni.switchTab({
							url: '/pages/index/index'
						});
						break;
					case 'explore':
						// uni.showToast({
						//   title: '探索功能开发中',
						//   icon: 'none'
						// });
						break;
					case 'trips':
						// uni.showToast({
						//   title: '行程功能开发中',
						//   icon: 'none'
						// });
						break;
				}
			}
		}
	}
</script>

<style lang="scss">
	/* ===== 设计令牌 ===== */
	$brand: #2E86DE;
	$brand-dark: #1B6EC2;
	$brand-bg: #eef4fb;
	$text-1: #1e293b;
	$text-2: #64748b;
	$text-3: #94a3b8;
	$border: #e2e8f0;
	$bg-page: #f4f7fb;
	$danger: #ff3b30;

	.profile-container {
		min-height: 100vh;
		background-color: $bg-page;
		position: relative;
	}

	/* 顶部渐变背景 */
	.profile-background {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 220px;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 60%, #74B9FF 100%);
		border-radius: 0 0 32px 32px;

		&::after {
			content: "";
			position: absolute;
			top: 30px;
			right: -40px;
			width: 160px;
			height: 160px;
			border-radius: 50%;
			background: rgba(255, 255, 255, 0.1);
		}
	}

	.profile-content {
		position: relative;
		height: 100vh;
		z-index: 1;
		padding-bottom: calc(56px + env(safe-area-inset-bottom));
	}

	/* 加载中容器 */
	.loading-container {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		padding: 60px 0;
		margin: 20px 15px;
		background-color: #fff;
		border-radius: 20px;
		box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.06);
	}

	.loading-spinner {
		width: 42px;
		height: 42px;
		border-radius: 50%;
		border: 3px solid $brand-bg;
		border-top: 3px solid $brand;
		animation: spin 1s linear infinite;
		margin-bottom: 16px;
	}

	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}

		100% {
			transform: rotate(360deg);
		}
	}

	.loading-text {
		font-size: 14px;
		color: $text-2;
	}

	/* 错误容器 */
	.error-container {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		padding: 60px 0;
		margin: 20px 15px;
		background-color: #fff;
		border-radius: 20px;
		box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.06);
	}

	.error-icon {
		font-size: 44px;
		color: $danger;
		margin-bottom: 16px;
	}

	.error-text {
		font-size: 14px;
		color: $text-2;
		text-align: center;
		margin-bottom: 22px;
		padding: 0 30px;
		line-height: 1.6;
	}

	.error-action {
		padding: 10px 24px;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		border-radius: 22px;
		box-shadow: 0 6rpx 16rpx rgba(46, 134, 222, 0.28);
	}

	.action-text {
		font-size: 14px;
		color: #fff;
		font-weight: 500;
	}

	/* 用户信息头部卡片 */
	.profile-header {
		padding: 22px 18px;
		margin: 24px 15px 16px;
		background-color: #fff;
		border-radius: 22px;
		box-shadow: 0 12rpx 32rpx rgba(15, 23, 42, 0.08);
		display: flex;
		align-items: center;
		justify-content: flex-start;
	}

	.profile-avatar-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		position: relative;
		margin-bottom: 0;
		margin-right: 18px;
		flex-shrink: 0;
	}

	.profile-avatar {
		width: 88px;
		height: 88px;
		border-radius: 44px;
		border: 4px solid #fff;
		box-shadow: 0 6rpx 18rpx rgba(46, 134, 222, 0.18);
		background-color: $brand-bg;
	}

	.profile-edit-avatar {
		position: absolute;
		bottom: 0;
		right: calc(50% - 48px);
		width: 30px;
		height: 30px;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 4rpx 10rpx rgba(46, 134, 222, 0.35);
		border: 2px solid #fff;
	}

	.edit-icon {
		width: 12px;
		height: 12px;
		background-color: #fff;
		border-radius: 2px;
		position: relative;
	}

	.profile-info {
		text-align: left;
		flex: 1;
		overflow: hidden;
	}

	.profile-name {
		font-size: 21px;
		font-weight: 700;
		color: $text-1;
		margin-bottom: 5px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.profile-username {
		font-size: 13px;
		color: $text-3;
		margin-bottom: 8px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.profile-tags {
		display: flex;
		justify-content: flex-start;
		gap: 8px;
		flex-wrap: wrap;
	}

	.profile-tag {
		padding: 3px 10px;
		background-color: $brand-bg;
		color: $brand;
		border-radius: 100px;
		font-size: 12px;
		font-weight: 500;
	}

	.quick-actions {
		display: flex;
		justify-content: space-around;
		margin: 0 15px 16px;
		background-color: #fff;
		border-radius: 16px;
		padding: 16px;
		box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
	}

	.quick-action-item {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.action-number {
		font-size: 22px;
		font-weight: 700;
		color: $brand;
		margin-bottom: 4px;
	}

	.action-text {
		font-size: 12px;
		color: $text-2;
	}

	/* 详细信息列表 */
	.profile-details {
		padding: 0 15px;
	}

	.detail-section {
		background-color: #fff;
		border-radius: 18px;
		padding: 16px 18px;
		margin-bottom: 14px;
		box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
	}

	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 14px;
		padding-bottom: 12px;
		border-bottom: 1px solid #f1f5f9;
	}

	.section-title {
		font-size: 16px;
		font-weight: 700;
		color: $text-1;
		position: relative;
		padding-left: 12px;

		&::before {
			content: "";
			position: absolute;
			left: 0;
			top: 50%;
			transform: translateY(-50%);
			width: 4px;
			height: 16px;
			background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
			border-radius: 2px;
		}
	}

	.section-action {
		font-size: 13px;
		color: $brand;
		font-weight: 500;
		padding: 4px 12px;
		background: $brand-bg;
		border-radius: 12px;
	}

	.detail-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 13px 0;
		border-bottom: 1px solid #f8fafc;
	}

	.detail-item:last-child {
		border-bottom: none;
	}

	.item-label {
		font-size: 14px;
		color: $text-2;
	}

	.item-value {
		font-size: 14px;
		color: $text-1;
		font-weight: 500;
	}

	/* 退出登录按钮 */
	.profile-actions {
		padding: 24px 15px 50px;
	}

	.action-button {
		width: 100%;
		height: 48px;
		border-radius: 24px;
		font-size: 16px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
	}

	.action-button.logout {
		background-color: #fff;
		border: 1px solid $danger;
		color: $danger;
		box-shadow: 0 4rpx 12rpx rgba(255, 59, 48, 0.08);
	}

	.action-button:active {
		transform: scale(0.98);
		opacity: 0.9;
	}

	.button-text {
		font-weight: 600;
		letter-spacing: 1px;
	}
</style>