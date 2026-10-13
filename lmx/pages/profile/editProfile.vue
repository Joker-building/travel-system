<template>
	<view class="edit-profile-container">
		<view class="page-header">
			<view class="header-left" @click="goBack">
				<text class="back-icon">←</text>
			</view>
			<text class="header-title">编辑个人资料</text>
			<view class="header-right"></view>
		</view>

		<scroll-view scroll-y class="edit-profile-content">
			<!-- 头像编辑 -->
			<view class="avatar-section">
				<image class="profile-avatar" :src="getAvatarUrl()" mode="aspectFill">
				</image>
				<view class="edit-avatar-btn" @click="editAvatar">
					<text class="btn-text">更换头像</text>
				</view>
			</view>

			<!-- 表单内容 -->
			<view class="form-wrapper">
				<view class="form-section">
					<!-- <view class="form-group">
						<text class="form-label">姓氏</text>
						<input class="form-input" type="text" v-model="formData.lastName" placeholder="请输入姓氏" />
					</view>

					<view class="form-group">
						<text class="form-label">名字</text>
						<input class="form-input" type="text" v-model="formData.firstName" placeholder="请输入名字" />
					</view> -->
					<view class="form-group">
						<text class="form-label">昵称</text>
						<input class="form-input" type="text" v-model="formData.nickname" placeholder="请输入昵称" />
					</view>
					<!-- <view class="form-group">
						<text class="form-label">邮箱</text>
						<input class="form-input" type="text" v-model="formData.email" placeholder="请输入邮箱" />
					</view> -->

					<view class="form-group">
						<text class="form-label">手机号</text>
						<input class="form-input" type="number" v-model="formData.phone" placeholder="请输入手机号" />
					</view>

					<view class="form-group">
						<text class="form-label">性别</text>
						<picker class="form-picker" :range="genderOptions" range-key="label" @change="onGenderChange">
							<view class="picker-value">
								<text>{{ getGenderText(formData.gender) }}</text>
								<text class="picker-arrow">▼</text>
							</view>
						</picker>
					</view>

					<!-- <view class="form-group">
						<text class="form-label">出生日期</text>
						<picker class="form-picker" mode="date" :value="formData.birthDate" @change="onBirthDateChange">
							<view class="picker-value">
								<text>{{ formData.birthDate || '请选择出生日期' }}</text>
								<text class="picker-arrow">▼</text>
							</view>
						</picker>
					</view> -->
					<view class="form-group">
						<!-- 常住城市（手动三级联动选择器） -->
						<view class="form-group">
							<picker mode="multiSelector" :value="cityIndex" :range="cityArray" @change="onCityChange"
								@columnchange="onCityColumnChange" class="form-picker">
								<view class="picker-value">
									<text> 常住城市：{{ formData.city || '请选择城市' }}</text>
									<text class="picker-arrow">▼</text>
								</view>
							</picker>
						</view>
					</view>
					<!-- <view class="form-group">
						<text class="form-label">国籍</text>
						<picker class="form-picker" :range="nationalityOptions" range-key="label"
							@change="onNationalityChange">
							<view class="picker-value">
								<text>{{ getNationalityText(formData.nationality) }}</text>
								<text class="picker-arrow">▼</text>
							</view>
						</picker>
					</view> -->

					<!-- <view class="form-group">
						<text class="form-label">首选语言</text>
						<picker class="form-picker" :range="languageOptions" range-key="label"
							@change="onLanguageChange">
							<view class="picker-value">
								<text>{{ getLanguageName(formData.preferredLanguage) }}</text>
								<text class="picker-arrow">▼</text>
							</view>
						</picker>
					</view> -->
				</view>
			</view>

			<!-- 提交按钮 -->
			<button class="submit-button" @click="saveProfile" :disabled="isSubmitting">
				<text v-if="isSubmitting">保存中...</text>
				<text v-else>保存修改</text>
			</button>
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
		getToken
	} from '@/utils/auth'
	export default {
		data() {
			return {
				baseUrl: 'http://127.0.0.1:8000',

				isSubmitting: false,
				originalUserInfo: null,
				tempAvatarUrl: '', // 用于本地显示的临时头像URL
				originalAvatarUrl: '', // 保存原始头像URL
				formData: {
					// firstName: '',
					// lastName: '',
					nickname: '',
					// email: '',
					phone: '',
					gender: '',
					city: '',
					avatar_url: '',
					// birthDate: '',
					// nationality: '',
					// preferredLanguage: '',

				},

				// 三级联动 省市区
				cityIndex: [0, 0],
				provinceList: [], // 所有省份
				cityList: [], // 对应城市
				cityArray: [], // 选择器显示

				avatarChanged: false,
				genderOptions: [{
						value: 'male',
						label: '男'
					},
					{
						value: 'female',
						label: '女'
					},
					{
						value: 'other',
						label: '其他'
					}
				],
				nationalityOptions: [{
						value: 'china',
						label: '中国'
					},
					{
						value: 'usa',
						label: '美国'
					},
					{
						value: 'japan',
						label: '日本'
					},
					{
						value: 'korea',
						label: '韩国'
					},
					{
						value: 'uk',
						label: '英国'
					},
					{
						value: 'germany',
						label: '德国'
					},
					{
						value: 'france',
						label: '法国'
					}
				],
				languageOptions: [{
						value: 'zh',
						label: '中文'
					},
					{
						value: 'en',
						label: 'English'
					},
					{
						value: 'ja',
						label: '日本語'
					},
					{
						value: 'ko',
						label: '한국어'
					}
				]
			};
		},
		onLoad() {
			// 加载用户信息
			this.loadUserInfo();
			this.initCityData()
		},
		methods: {
			async loadUserInfo() {
				try {
					uni.showLoading({
						title: '加载中...'
					});
					const response = await getUserInfo();
					console.log(response)
					if (response.statusCode === 200 && response.data && response.data.code === 200) {
						const userData = response.data.data;
						// 保存原始数据，用于比较变更
						this.originalUserInfo = JSON.parse(JSON.stringify(userData));

						// 填充表单数据
						this.formData = {
							// firstName: userData.firstName || '',
							// lastName: userData.lastName || '',
							nickname: userData.nickname,
							// email: userData.email || '',
							phone: userData.phone || '',
							gender: userData.gender || '',
							city: userData.city || '',
							// birthDate: userData.birthDate ? this.formatDate(userData.birthDate) : '',
							// nationality: userData.nationality || '',
							// preferredLanguage: userData.preferredLanguage || '',
							avatar_url: userData.avatar_url || ''
						};

						// 设置临时头像URL用于显示
						this.tempAvatarUrl = userData.avatar_url || '';

						// 保存原始头像URL
						this.originalAvatarUrl = userData.avatar_url || '';


					} else {
						this.showError('加载用户数据失败');
						console.error('加载用户数据失败:', response.data);
						setTimeout(() => this.goBack(), 1500);
					}
				} catch (error) {
					this.showError('加载用户数据出错');
					console.error('加载用户数据出错:', error);
					setTimeout(() => this.goBack(), 1500);
				} finally {
					uni.hideLoading();
				}
			},

			// chooseAvatar() {
			// 	uni.chooseImage({
			// 		count: 1,
			// 		sizeType: ['compressed'],
			// 		sourceType: ['album', 'camera'],
			// 		success: (res) => {
			// 			const tempFilePath = res.tempFilePaths[0];
			// 			console.log('tempFilePath:', tempFilePath)
			// 			// 读取图片并转为base64
			// 			this.imageToBase64(tempFilePath);
			// 		}
			// 	});
			// },

			// imageToBase64(tempFilePath) {

			// 	// #ifdef H5
			// 	// H5 环境：用 XMLHttpRequest + FileReader 读取图片
			// 	// 显示加载中
			// 	uni.showLoading({
			// 		title: '上传中...'
			// 	});
			// 	const xhr = new XMLHttpRequest();
			// 	xhr.open('GET', tempFilePath, true);
			// 	xhr.responseType = 'blob';
			// 	xhr.onload = () => {
			// 		const reader = new FileReader();
			// 		reader.onload = async (e) => {
			// 			try {
			// 				// 获取 Base64 数据（带前缀）
			// 				const base64Data = e.target.result;

			// 				// 构建要更新的数据
			// 				const updateData = {
			// 					avatarUrl: base64Data
			// 				};

			// 				// 调用更新接口
			// 				const response = await updateUserInfo(updateData);

			// 				if (response.statusCode === 200 && response.data?.code ===
			// 					200) {
			// 					// 更新本地头像（注意：H5 不能直接显示 Base64 临时路径，需用 Base64 或重新加载）
			// 					this.formData.avatarUrl =
			// 						base64Data; // 或 tempFilePath（但可能失效）

			// 					uni.showToast({
			// 						title: '头像更新成功',
			// 						icon: 'success'
			// 					});

			// 					// 重新加载用户信息
			// 					this.loadUserInfo();
			// 				} else {
			// 					throw new Error(response.data?.message || '上传失败');
			// 				}
			// 			} catch (error) {
			// 				console.error('上传头像失败:', error);
			// 				uni.showToast({
			// 					title: '头像更新失败: ' + (error.message || '未知错误'),
			// 					icon: 'none'
			// 				});
			// 			} finally {
			// 				// uni.hideLoading();
			// 			}
			// 		};
			// 		reader.onerror = () => {

			// 			uni.showToast({
			// 				title: '图片读取失败',
			// 				icon: 'none'
			// 			});
			// 		};
			// 		reader.readAsDataURL(xhr.response);
			// 	};
			// 	xhr.onerror = () => {

			// 		uni.showToast({
			// 			title: '图片请求失败',
			// 			icon: 'none'
			// 		});
			// 	};
			// 	xhr.send();
			// 	// #endif

			// 	// #ifdef APP-PLUS
			// 	// 读取图片并转为base64
			// 	// 显示加载中
			// 	uni.showLoading({
			// 		title: '上传中...'
			// 	});
			// 	uni.getFileSystemManager().readFile({
			// 		filePath: tempFilePath,
			// 		encoding: 'base64',
			// 		success: async (readRes) => {
			// 			console.log('readRes为：', readRes)
			// 			try {
			// 				// 构建base64字符串
			// 				const base64Data = `data:image/jpeg;base64,${readRes.data}`;

			// 				// 构建要更新的数据 - 仅更新头像
			// 				const updateData = {
			// 					avatarUrl: base64Data
			// 				};

			// 				// 调用更新接口
			// 				const response = await updateUserInfo(updateData);

			// 				if (response.statusCode === 200 && response.data && response
			// 					.data.code === 200) {
			// 					// 更新本地头像
			// 					this.formData.avatarUrl = tempFilePath;

			// 					// 显示成功提示
			// 					uni.showToast({
			// 						title: '头像更新成功',
			// 						icon: 'success'
			// 					});

			// 					// 重新加载用户信息，确保显示最新数据
			// 					this.loadUserInfo();
			// 				} else {
			// 					throw new Error(response.data ? response.data.message :
			// 						'上传失败');
			// 				}
			// 			} catch (error) {
			// 				console.error('上传头像失败:', error);
			// 				uni.showToast({
			// 					title: '头像更新失败: ' + (error.message || '未知错误'),
			// 					icon: 'none'
			// 				});
			// 			} finally {
			// 				uni.hideLoading();
			// 			}
			// 		},
			// 		fail: (err) => {
			// 			console.error('读取图片失败:', err);
			// 			uni.hideLoading();
			// 			uni.showToast({
			// 				title: '图片处理失败',
			// 				icon: 'none'
			// 			});
			// 		}
			// 	});
			// 	// #endif
			// 	// 	uni.showLoading({
			// 	// 		title: '处理图片中...'
			// 	// 	});
			// 	// 	// #ifdef H5
			// 	// 	// H5 环境：用 XMLHttpRequest + FileReader 读取图片
			// 	// 	// 显示加载中
			// 	// 	uni.showLoading({
			// 	// 		title: '上传中...'
			// 	// 	});
			// 	// 	const xhr = new XMLHttpRequest();
			// 	// 	xhr.open('GET', tempFilePath, true);
			// 	// 	xhr.responseType = 'blob';
			// 	// 	xhr.onload = () => {
			// 	// 		const reader = new FileReader();
			// 	// 		reader.onload = async (e) => {
			// 	// 			try {
			// 	// 				// 获取 Base64 数据（带前缀）
			// 	// 				const base64Data = e.target.result;

			// 	// 				// 构建要更新的数据
			// 	// 				const updateData = {
			// 	// 					avatarUrl: base64Data
			// 	// 				};

			// 	// 				// 调用更新接口
			// 	// 				const response = await updateUserInfo(updateData);

			// 	// 				if (response.statusCode === 200 && response.data?.code ===
			// 	// 					200) {
			// 	// 					// 更新本地头像（注意：H5 不能直接显示 Base64 临时路径，需用 Base64 或重新加载）
			// 	// 					this.userInfo.avatarUrl =
			// 	// 						base64Data; // 或 tempFilePath（但可能失效）

			// 	// 					uni.showToast({
			// 	// 						title: '头像更新成功',
			// 	// 						icon: 'success'
			// 	// 					});

			// 	// 					// 重新加载用户信息
			// 	// 					this.loadUserInfo();
			// 	// 				} else {
			// 	// 					throw new Error(response.data?.message || '上传失败');
			// 	// 				}
			// 	// 			} catch (error) {
			// 	// 				console.error('上传头像失败:', error);
			// 	// 				uni.showToast({
			// 	// 					title: '头像更新失败: ' + (error.message || '未知错误'),
			// 	// 					icon: 'none'
			// 	// 				});
			// 	// 			} finally {
			// 	// 				// uni.hideLoading();
			// 	// 			}
			// 	// 		};
			// 	// 		reader.onerror = () => {

			// 	// 			uni.showToast({
			// 	// 				title: '图片读取失败',
			// 	// 				icon: 'none'
			// 	// 			});
			// 	// 		};
			// 	// 		reader.readAsDataURL(xhr.response);
			// 	// 	};
			// 	// 	xhr.onerror = () => {

			// 	// 		uni.showToast({
			// 	// 			title: '图片请求失败',
			// 	// 			icon: 'none'
			// 	// 		});
			// 	// 	};
			// 	// 	xhr.send();
			// 	// 	// #endif

			// 	// 	// 如果是 H5 环境，使用 FileReader
			// 	// 	// if (typeof window !== 'undefined' && window.FileReader) {
			// 	// 	// 	const reader = new FileReader();
			// 	// 	// 	reader.onload = (e) => {
			// 	// 	// 		const base64Data = e.target.result; // 已经是带前缀的 base64 字符串
			// 	// 	// 		this.tempAvatarUrl = base64Data; // 或者根据需求处理
			// 	// 	// 		this.formData.avatarUrl = base64Data;
			// 	// 	// 		this.avatarChanged = true;
			// 	// 	// 		console.log('base64Data:', base64Data, 'tempAvatarUrl:', tempAvatarUrl)
			// 	// 	// 		uni.hideLoading();
			// 	// 	// 	};
			// 	// 	// 	reader.onerror = (err) => {
			// 	// 	// 		console.error('图片转 base64 失败:', err);
			// 	// 	// 		this.showError('图片处理失败');
			// 	// 	// 		uni.hideLoading();
			// 	// 	// 	};
			// 	// 	// 	// 如果是文件对象，直接读取
			// 	// 	// 	if (file instanceof File) {
			// 	// 	// 		reader.readAsDataURL(file);
			// 	// 	// 	} else {
			// 	// 	// 		console.error('传入的参数不是文件对象');
			// 	// 	// 		this.showError('参数错误');
			// 	// 	// 		uni.hideLoading();
			// 	// 	// 	}
			// 	// 	// }
			// 	// 	// 如果是小程序环境，使用 getFileSystemManager
			// 	// 	if (uni.getFileSystemManager) {
			// 	// 		uni.getFileSystemManager().readFile({
			// 	// 			filePath: file, // 这里 file 是文件路径
			// 	// 			encoding: 'base64',
			// 	// 			success: (res) => {
			// 	// 				const base64Data = `data:image/jpeg;base64,${res.data}`;
			// 	// 				this.tempAvatarUrl = file; // 或者根据需求处理
			// 	// 				this.formData.avatarUrl = base64Data;
			// 	// 				this.avatarChanged = true;
			// 	// 				uni.hideLoading();
			// 	// 			},
			// 	// 			fail: (err) => {
			// 	// 				console.error('图片转 base64 失败:', err);
			// 	// 				this.showError('图片处理失败');
			// 	// 				uni.hideLoading();
			// 	// 			}
			// 	// 		});
			// 	// 	}
			// 	// 	// 其他环境
			// 	// 	else {
			// 	// 		console.error('当前环境不支持图片转 base64');
			// 	// 		this.showError('环境不支持');
			// 	// 		uni.hideLoading();
			// 	// 	}
			// 	// 	// 读取文件内容
			// 	// 	// uni.getFileSystemManager().readFile({
			// 	// 	//   filePath: filePath,
			// 	// 	//   encoding: 'base64',
			// 	// 	//   success: (res) => {
			// 	// 	//     // 构建带前缀的base64字符串 
			// 	// 	//     const base64Data = `data:image/jpeg;base64,${res.data}`;

			// 	// 	//     // 更新本地显示头像为完整URL
			// 	// 	//     this.tempAvatarUrl = filePath;

			// 	// 	//     // 更新表单数据为带前缀的base64字符串
			// 	// 	//     this.formData.avatarUrl = base64Data;
			// 	// 	//     this.avatarChanged = true;

			// 	// 	//     uni.hideLoading();
			// 	// 	//   },
			// 	// 	//   fail: (err) => {
			// 	// 	//     console.error('图片转base64失败:', err);
			// 	// 	//     this.showError('图片处理失败');
			// 	// 	//     uni.hideLoading();
			// 	// 	//   }
			// 	// 	// });
			// 	// 
			// },

			onGenderChange(e) {
				const index = e.detail.value;
				this.formData.gender = this.genderOptions[index].value;
			},

			onBirthDateChange(e) {
				this.formData.birthDate = e.detail.value;
			},

			onNationalityChange(e) {
				const index = e.detail.value;
				this.formData.nationality = this.nationalityOptions[index].value;
			},

			onLanguageChange(e) {
				const index = e.detail.value;
				this.formData.preferredLanguage = this.languageOptions[index].value;
			},
			getAvatarUrl() {
				// 如果有头像，拼接完整URL；否则使用默认头像
				if (this.formData.avatar_url) {
					return this.baseUrl + this.formData.avatar_url;
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
								throw new Error('图片过大，请上传不超过1MB的图片');
							}
							if (data.code !== 200) throw new Error(data.message);

							// 后端返回的头像 URL（data.data.avatar_url）
							const avatar_url = data.data.avatar_url;
							console.log('头像URL：', avatar_url);

							// 更新表单与本地显示
							this.formData.avatar_url = avatar_url;
							this.tempAvatarUrl = avatar_url;
							this.avatarChanged = true;

							uni.showToast({
								title: '头像更新成功',
								icon: 'success'
							});
							// 重新加载用户信息，确保显示最新数据
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
			async saveProfile() {
				try {
					// 表单验证
					// if (!this.formData.firstName || !this.formData.lastName) {
					if (!this.formData.nickname) {
						return this.showError('姓名不能为空');
					}

					// if (!this.formData.email) {
					// 	return this.showError('邮箱不能为空');
					// }

					// // 检查邮箱格式
					// const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
					// if (!emailRegex.test(this.formData.email)) {
					// 	return this.showError('邮箱格式不正确');
					// }

					// 手机号验证
					if (this.formData.phone) {
						const phoneRegex = /^1[3-9]\d{9}$/;
						if (!phoneRegex.test(this.formData.phone)) {
							return this.showError('手机号格式不正确');
						}
					}

					this.isSubmitting = true;
					uni.showLoading({
						title: '保存中...'
					});

					// 准备提交的数据（后端字段为 snake_case：nickname/phone/gender/city/avatar_url）
					const updateData = {
						...this.formData
					};

					// 头像已在 editAvatar 中通过 /api/user/avatar/upload 单独保存，
					// 这里无需再传 avatar_url，避免覆盖；后端只更新非 None 字段
					delete updateData.avatar_url;

					// 确保性别字段使用正确的枚举值
					if (updateData.gender && !['male', 'female', 'other'].includes(updateData.gender)) {
						const genderMap = {
							'男': 'male',
							'女': 'female',
							'其他': 'other'
						};

						if (genderMap[updateData.gender]) {
							updateData.gender = genderMap[updateData.gender];

						}
					}

					console.log(updateData)
					const response = await updateUserInfo(updateData);

					if (response.statusCode === 200 && response.data) {
						if (response.data.code === 200) {
							uni.showToast({
								title: '更新成功',
								icon: 'success'
							});

							// 更新成功后返回个人资料页
							setTimeout(() => {
								uni.navigateBack();
							}, 1500);
						} else {
							console.error('API返回错误:', response.data);
							this.showError(response.data.message || '更新失败');
						}
					} else {
						console.error('HTTP请求失败:', response);
						this.showError('网络请求失败');
					}
				} catch (error) {
					console.error('保存个人资料出错:', error);
					this.showError('保存失败，请稍后重试');
				} finally {
					this.isSubmitting = false;
					uni.hideLoading();
				}
			},

			showError(message) {
				uni.showToast({
					title: message,
					icon: 'none',
					duration: 2000
				});
			},

			goBack() {
				uni.navigateBack();
			},

			getGenderText(gender) {
				const map = {
					'male': '男',
					'female': '女',
					'other': '其他'
				};
				return map[gender] || '请选择性别';
			},

			getNationalityText(nationality) {
				const map = {
					'china': '中国',
					'usa': '美国',
					'japan': '日本',
					'korea': '韩国',
					'uk': '英国',
					'germany': '德国',
					'france': '法国'
				};
				return map[nationality] || '请选择国籍';
			},

			getLanguageName(code) {
				const languages = {
					'en': 'English',
					'zh': '中文',
					'ja': '日本語',
					'ko': '한국어'
				};
				return languages[code] || '请选择语言';
			},

			formatDate(dateString) {
				try {
					const date = new Date(dateString);
					const year = date.getFullYear();
					const month = String(date.getMonth() + 1).padStart(2, '0');
					const day = String(date.getDate()).padStart(2, '0');
					return `${year}-${month}-${day}`;
				} catch (e) {
					return '';
				}
			},
			initCityData() {
				this.provinceList = [{
						name: "北京市",
						cities: ["东城区", "西城区", "朝阳区", "丰台区", "石景山区", "海淀区", "门头沟区", "房山区", "通州区", "顺义区", "昌平区", "大兴区",
							"怀柔区", "平谷区", "密云区", "延庆区"
						]
					},
					{
						name: "天津市",
						cities: ["和平区", "河东区", "河西区", "南开区", "河北区", "红桥区", "东丽区", "西青区", "津南区", "北辰区", "武清区", "宝坻区",
							"滨海新区", "宁河区", "静海区", "蓟州区"
						]
					},
					{
						name: "河北省",
						cities: ["石家庄市", "唐山市", "秦皇岛市", "邯郸市", "邢台市", "保定市", "张家口市", "承德市", "沧州市", "廊坊市", "衡水市"]
					},
					{
						name: "山西省",
						cities: ["太原市", "大同市", "阳泉市", "长治市", "晋城市", "朔州市", "晋中市", "运城市", "忻州市", "临汾市", "吕梁市"]
					},
					{
						name: "内蒙古自治区",
						cities: ["呼和浩特市", "包头市", "乌海市", "赤峰市", "通辽市", "鄂尔多斯市", "呼伦贝尔市", "巴彦淖尔市", "乌兰察布市"]
					},
					{
						name: "辽宁省",
						cities: ["沈阳市", "大连市", "鞍山市", "抚顺市", "本溪市", "丹东市", "锦州市", "营口市", "阜新市", "辽阳市", "盘锦市", "铁岭市",
							"朝阳市", "葫芦岛市"
						]
					},
					{
						name: "吉林省",
						cities: ["长春市", "吉林市", "四平市", "辽源市", "通化市", "白山市", "松原市", "白城市", "延边州"]
					},
					{
						name: "黑龙江",
						cities: ["哈尔滨市", "齐齐哈尔市", "鸡西市", "鹤岗市", "双鸭山市", "大庆市", "伊春市", "佳木斯市", "七台河市", "牡丹江市", "黑河市",
							"绥化市"
						]
					},
					{
						name: "上海市",
						cities: ["黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "虹口区", "杨浦区", "闵行区", "宝山区", "嘉定区", "浦东新区", "金山区",
							"松江区", "青浦区", "奉贤区", "崇明区"
						]
					},
					{
						name: "江苏省",
						cities: ["南京市", "无锡市", "徐州市", "常州市", "苏州市", "南通市", "连云港市", "淮安市", "盐城市", "扬州市", "镇江市", "泰州市",
							"宿迁市"
						]
					},
					{
						name: "浙江省",
						cities: ["杭州市", "宁波市", "温州市", "嘉兴市", "湖州市", "绍兴市", "金华市", "衢州市", "舟山市", "台州市", "丽水市"]
					},
					{
						name: "安徽省",
						cities: ["合肥市", "芜湖市", "蚌埠市", "淮南市", "马鞍山市", "淮北市", "铜陵市", "安庆市", "黄山市", "滁州市", "阜阳市", "宿州市",
							"六安市", "亳州市", "池州市", "宣城市"
						]
					},
					{
						name: "福建省",
						cities: ["福州市", "厦门市", "莆田市", "三明市", "泉州市", "漳州市", "南平市", "龙岩市", "宁德市"]
					},
					{
						name: "江西省",
						cities: ["南昌市", "景德镇市", "萍乡市", "九江市", "新余市", "鹰潭市", "赣州市", "吉安市", "宜春市", "抚州市", "上饶市"]
					},
					{
						name: "山东省",
						cities: ["济南市", "青岛市", "淄博市", "枣庄市", "东营市", "烟台市", "潍坊市", "济宁市", "泰安市", "威海市", "日照市", "临沂市",
							"德州市", "聊城市", "滨州市", "菏泽市"
						]
					},
					{
						name: "河南省",
						cities: ["郑州市", "开封市", "洛阳市", "平顶山市", "安阳市", "鹤壁市", "新乡市", "焦作市", "濮阳市", "许昌市", "漯河市", "三门峡市",
							"南阳市", "商丘市", "信阳市", "周口市", "驻马店市"
						]
					},
					{
						name: "湖北省",
						cities: ["武汉市", "黄石市", "十堰市", "宜昌市", "襄阳市", "鄂州市", "荆门市", "孝感市", "荆州市", "黄冈市", "咸宁市", "随州市",
							"恩施州"
						]
					},
					{
						name: "湖南省",
						cities: ["长沙市", "株洲市", "湘潭市", "衡阳市", "邵阳市", "岳阳市", "常德市", "张家界市", "益阳市", "郴州市", "永州市", "怀化市",
							"娄底市", "湘西州"
						]
					},
					{
						name: "广东省",
						cities: ["广州市", "韶关市", "深圳市", "珠海市", "汕头市", "佛山市", "江门市", "湛江市", "茂名市", "肇庆市", "惠州市", "梅州市",
							"汕尾市", "河源市", "阳江市", "清远市", "东莞市", "中山市", "潮州市", "揭阳市", "云浮市"
						]
					},
					{
						name: "广西壮族自治区",
						cities: ["南宁市", "柳州市", "桂林市", "梧州市", "北海市", "防城港市", "钦州市", "贵港市", "玉林市", "百色市", "贺州市", "河池市",
							"来宾市", "崇左市"
						]
					},
					{
						name: "海南省",
						cities: ["海口市", "三亚市", "三沙市", "儋州市"]
					},
					{
						name: "重庆市",
						cities: ["万州区", "涪陵区", "渝中区", "大渡口区", "江北区", "沙坪坝区", "九龙坡区", "南岸区", "北碚区", "渝北区", "巴南区", "黔江区",
							"长寿区"
						]
					},
					{
						name: "四川省",
						cities: ["成都市", "自贡市", "攀枝花市", "泸州市", "德阳市", "绵阳市", "广元市", "遂宁市", "内江市", "乐山市", "南充市", "眉山市",
							"宜宾市", "广安市", "达州市", "雅安市", "巴中市", "资阳市", "阿坝州", "甘孜州", "凉山州"
						]
					},
					{
						name: "贵州省",
						cities: ["贵阳市", "六盘水市", "遵义市", "安顺市", "毕节市", "铜仁市", "黔西南州", "黔东南州", "黔南州"]
					},
					{
						name: "云南省",
						cities: ["昆明市", "曲靖市", "玉溪市", "保山市", "昭通市", "丽江市", "普洱市", "临沧市", "楚雄州", "红河州", "文山州", "西双版纳州",
							"大理州", "德宏州", "怒江州", "迪庆州"
						]
					},
					{
						name: "西藏自治区",
						cities: ["拉萨市", "日喀则市", "昌都市", "林芝市", "山南市", "那曲市", "阿里地区"]
					},
					{
						name: "陕西省",
						cities: ["西安市", "铜川市", "宝鸡市", "咸阳市", "渭南市", "延安市", "汉中市", "榆林市", "安康市", "商洛市"]
					},
					{
						name: "甘肃省",
						cities: ["兰州市", "嘉峪关市", "金昌市", "白银市", "天水市", "武威市", "张掖市", "平凉市", "酒泉市", "庆阳市", "定西市", "陇南市",
							"临夏州", "甘南州"
						]
					},
					{
						name: "青海省",
						cities: ["西宁市", "海东市", "海北州", "黄南州", "海南州", "果洛州", "玉树州", "海西州"]
					},
					{
						name: "宁夏回族自治区",
						cities: ["银川市", "石嘴山市", "吴忠市", "固原市", "中卫市"]
					},
					{
						name: "新疆维吾尔自治区",
						cities: ["乌鲁木齐市", "克拉玛依市", "吐鲁番市", "哈密市", "昌吉州", "博尔塔拉州", "巴音郭楞州", "阿克苏地区", "克孜勒苏州", "喀什地区",
							"和田地区", "伊犁州", "塔城地区", "阿勒泰地区"
						]
					}
				];

				// 默认加载第一个省的城市
				this.cityList = this.provinceList[0].cities;
				this.updateCityArray();
			},

			// 更新选择器显示的数组
			updateCityArray() {
				this.cityArray = [
					this.provinceList.map(item => item.name),
					this.cityList
				];
			},

			// 滑动切换省份时，刷新城市列表
			onCityColumnChange(e) {
				const col = e.detail.column;
				const val = e.detail.value;

				if (col === 0) {
					// 切换省份
					this.cityIndex[0] = val;
					this.cityIndex[1] = 0;
					this.cityList = this.provinceList[val].cities;
					this.updateCityArray();
				}
			},

			// 选择完成，赋值到表单（修复版）
			onCityChange(e) {
				const index = e.detail.value;
				const p = this.provinceList[index[0]].name;
				const c = this.cityList[index[1]];

				// ✅ 关键：赋值给 formData，页面才会显示
				this.formData.city = p + " " + c;
			},

		},

	};
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

	* {
		box-sizing: border-box;
		margin: 0;
		padding: 0;
	}

	/* 滚动选择器样式 */
	.input-select {
		position: relative;
		margin-bottom: 15px;
	}

	.edit-profile-container {
		min-height: 100vh;
		background-color: $bg-page;
		display: flex;
		flex-direction: column;
		box-sizing: border-box;
		width: 100%;
	}

	/* 顶部导航栏：品牌渐变 */
	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		height: 56px;
		padding: 0 15px;
		padding-top: env(safe-area-inset-top);
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		position: relative;
		width: 100%;
		box-sizing: border-box;
		box-shadow: 0 8rpx 24rpx rgba(46, 134, 222, 0.18);
	}

	.header-left {
		width: 44px;
		height: 44px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		transition: background 0.2s ease;

		&:active {
			background: rgba(255, 255, 255, 0.18);
		}
	}

	.back-icon {
		font-size: 24px;
		color: #fff;
		font-weight: bold;
	}

	.header-title {
		font-size: 18px;
		color: #fff;
		font-weight: 600;
		flex: 1;
		text-align: center;
		letter-spacing: 1px;
	}

	.header-right {
		width: 44px;
	}

	.edit-profile-content {
		flex: 1;
		padding: 18px 14px;
		box-sizing: border-box;
		width: 100%;
		height: calc(100vh - 56px);
	}

	/* 头像编辑区 */
	.avatar-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		margin-bottom: 22px;
		width: 100%;
		box-sizing: border-box;
		padding: 24px 0 8px;
	}

	.profile-avatar {
		width: 110px;
		height: 110px;
		border-radius: 55px;
		margin-bottom: 16px;
		border: 4px solid #fff;
		box-shadow: 0 8rpx 24rpx rgba(46, 134, 222, 0.2);
		background-color: $brand-bg;
	}

	.edit-avatar-btn {
		padding: 9px 22px;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		border-radius: 22px;
		box-shadow: 0 6rpx 16rpx rgba(46, 134, 222, 0.28);
		transition: all 0.2s ease;

		&:active {
			transform: scale(0.96);
		}
	}

	.btn-text {
		color: #fff;
		font-size: 14px;
		font-weight: 500;
	}

	/* 表单容器 */
	.form-wrapper {
		padding: 0;
		width: 100%;
		box-sizing: border-box;
	}

	.form-section {
		background-color: #fff;
		border-radius: 18px;
		padding: 18px 16px 6px;
		margin-bottom: 20px;
		box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
		box-sizing: border-box;
		width: 100%;
	}

	.form-group {
		margin-bottom: 16px;
		box-sizing: border-box;
		width: 100%;
		position: relative;
	}

	.form-label {
		font-size: 13px;
		color: $text-2;
		margin-bottom: 8px;
		display: block;
		width: 100%;
		font-weight: 500;
		letter-spacing: 0.5px;
	}

	.form-input {
		width: 100%;
		height: 46px;
		border: 1px solid $border;
		border-radius: 12px;
		padding: 0 14px;
		font-size: 15px;
		color: $text-1;
		background-color: #f8fafc;
		box-sizing: border-box;
		transition: all 0.2s ease;

		&:focus {
			border-color: $brand;
			background: #fff;
			box-shadow: 0 0 0 3px rgba(46, 134, 222, 0.12);
		}
	}

	.form-picker {
		width: 100%;
		height: 46px;
		box-sizing: border-box;
	}

	.picker-value {
		width: 100%;
		height: 46px;
		border: 1px solid $border;
		border-radius: 12px;
		padding: 0 14px;
		font-size: 15px;
		color: $text-1;
		background-color: #f8fafc;
		display: flex;
		align-items: center;
		justify-content: space-between;
		box-sizing: border-box;
		transition: all 0.2s ease;

		&:active {
			border-color: $brand;
			background: $brand-bg;
		}
	}

	.picker-arrow {
		font-size: 11px;
		color: $text-3;
		margin-left: 4px;
	}

	/* 提交按钮 */
	.submit-button {
		height: 50px;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		color: #fff;
		font-size: 16px;
		font-weight: 600;
		border-radius: 25px;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-top: 22px;
		margin-bottom: 24px;
		box-sizing: border-box;
		width: 100%;
		letter-spacing: 2px;
		box-shadow: 0 12rpx 28rpx rgba(46, 134, 222, 0.3);
		transition: all 0.2s ease;

		&:active {
			transform: scale(0.98);
			opacity: 0.92;
		}
	}

	.submit-button[disabled] {
		background: #cbd5e1;
		color: #fff;
		box-shadow: none;
	}
</style>