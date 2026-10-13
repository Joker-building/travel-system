<template>
	<view class="trips-container">
		<!-- 顶部状态栏 -->
		<view class="status-bar">
			<view class="location-brief">
				<text class="location-name">我的行程</text>
			</view>
			<view class="header-icons">
				<!-- <text class="fas fa-filter-circle filter-icon" @click="filterTrips"></text> -->
				<text class="location-name">新建行程</text>
				<!-- plusempty -->

				<uni-icons type="plus" size="30" color="white" @click="addNewTrip"></uni-icons>
				<!-- <text class="fas fa-plus-circle add-icon" @click="addNewTrip"></text> -->
			</view>
		</view>

		<!-- 主要内容区域 -->
		<scroll-view scroll-y class="content-area">
			<!-- 搜索框 -->


			<!-- 加载中提示 -->
			<view class="loading-container" v-if="loading">
				<text class="loading-text">正在加载行程...</text>
			</view>

			<!-- 行程列表 -->
			<view class="trips-list" v-if="!loading">
				<view v-if="filteredTrips.length ===0" class="empty-trips">
					<view class="empty-icon"></view>
					<text class="empty-text">暂无{{emptyText}}</text>
					<button class="button-add" @click="handleReload" v-if="isShowReload">重试</button>
				</view>
				<!-- 行程列表 -->
				<view v-else class="trip-item" v-for="(item, index) in trips" :key="item.id"
					:class="{ 'trip-completed': formatTripStatus(item.start_date,item.end_date) === '已完成' }"
					@click="viewTripDetail(item,formatTripStatus(item.start_date,item.end_date))">
					<view class="trip-item-right">
						<view class="trip-item-header">
							<text class="trip-item-name"
								style="color:#2E86DE;letter-spacing: 2rpx;">{{item.trip_name}}</text>
							<!-- <text class="trip-item-date">{{item.start_date}} →
								{{item.end_date}}</text> -->
							<!-- <text class="trip-item-status">修改时间：{{item.update_time}}</text> -->
							<!-- 状态字样  未修改-->
							<text class="trip-item-status"
								:class="{'completed':statusColor[index]==='已完成'}">{{formatTripStatus(item.start_date,item.end_date)}}</text>
						</view>
						<!-- 起始城市 -->
						<!-- <view class="aCity-content" v-for="(city,cityIndex) in item.travelCity.length" :key="cityIndex">
							<view class="trip-item-dates">
								<text class="fas fa-calendar-alt date-icon"></text>
								<text class="trip-item-date">{{item.travelTime[cityIndex].Start}} →
									{{item.travelTime[cityIndex].End}}</text>
							</view>
							<view class="trip-item-location" v-if="item.travelCity">
								<text class="fas fa-map-marker-alt location-icon"></text>
								<text class="trip-item-place">旅游城市：{{item.travelCity[cityIndex]}}</text>
							</view>
							<hr />
						</view> -->
						<!-- 起始日期 -->
						<view class="aCity-content">
							<view class="trip-item-dates">
								<text class="fas fa-calendar-alt date-icon"></text>
								<text class="trip-item-date">{{item.start_date}} →
									{{item.end_date}} 共{{item.travel_days}}天</text>
							</view>
							<!-- <text class="trip-item-date"> {{item.travel_days}}天</text> -->
						</view>
						<!-- 起始城市 -->
						<view class="City-content">
							<view class="trip-item-dates">
								<!-- <text class="fas fa-route date-icon"></text> -->
								<text class="trip-item-date">目的地：
									{{item.dest_city}}</text>
							</view>
							<text class="trip-item-date">同行人类型：{{item.traveler_type}} </text>
							<br />
							<!-- <text class="trip-item-date">预算：{{item.total_budget}} </text> -->
						</view>

						<!-- <view class="trip-item-transport" v-if="item.transport">
							<text class="fas transport-icon" :class="{
                'fa-plane': item.transport === '飞机',
                'fa-bullet-train': item.transport === '高铁',
				'fa-train': item.transport === '火车',
                'fa-car': item.transport === '自驾'||'汽车'||'小车',
                'fa-bus': item.transport === '大巴',
                'fa-ship': item.transport === '轮船',
				'fa-bicycle': item.transport === '自行车'||'单车'||'骑行',
              }"></text>
							<text class="trip-item-transport-text">交通工具：{{item.transport}}</text>
							</view> -->
						<view class="trip-item-footer">
							<!-- <view class="trip-item-reminder" v-if="trip.hasReminders">
								<text class="fas fa-bell reminder-icon"></text>
								<text class="reminder-text">{{trip.reminders}}个提醒</text>
							</view> -->
							<!-- <view class="trip-item-companions" v-if="item.people > 0"> -->

							<!-- </view> -->
						</view>
						<view class="companions-text">
							<text class="trip-item-status">创建时间：{{ item.create_time.replace('T', ' ')}}</text>
						</view>
						<view class="button-del-box">
							<button class="button-del" @click.stop="del_list(index)">删除行程</button>
						</view>
					</view>
				</view>

			</view>
		</scroll-view>

		<!-- 新建行程弹窗 -->
		<view class="popup-mask" v-show="showAddPopup" @click="closeAddPopup"></view>
		<view class="popup-content" v-show="showAddPopup">
			<view class="popup-title">创建新行程</view>

			<view class="form-item">
				<text class="label">行程标题</text>
				<input v-model="addForm.trip_name" placeholder="请输入行程标题" class="form-input" />
			</view>

			<!-- 日期段选择：开始日期 + 结束日期 -->
			<view class="form-item">
				<text class="label">出行日期</text>
				<view class="date-picker-row">
					<!-- 开始日期 -->
					<picker mode="date" :value="addForm.start_date" @change="onStartDateChange" :start="todayDate">
						<view class="form-input picker-input">
							{{ addForm.start_date || '开始日期' }}
						</view>
					</picker>

					<text class="date-split"> 至 </text>

					<!-- 结束日期 -->
					<picker mode="date" :value="addForm.end_date" @change="onEndDateChange"
						:start="addForm.start_date || todayDate">
						<view class="form-input picker-input">
							{{ addForm.end_date || '结束日期' }}
						</view>
					</picker>
				</view>
			</view>

			<!-- 出发城市 + 目的地城市 同行显示 -->
			<view class="form-item">
				<text class="label">城市选择</text>
				<view class="city-row">
					<view class="city-item">
						<text class="small-label">出发地</text>
						<input v-model="addForm.start_city" placeholder="请输入" class="form-input" />
					</view>

					<text class="to-text">→</text>

					<view class="city-item">
						<text class="small-label">目的地</text>
						<input v-model="addForm.dest_city" placeholder="请输入" class="form-input" />
					</view>
				</view>
			</view>

			<view class="form-item">
				<text class="label">同行人类型</text>
				<input v-model="addForm.traveler_type" placeholder="例如：朋友/家人/独自" class="form-input" />
			</view>

			<view class="form-item">
				<text class="label">行程预算</text>
				<input v-model="addForm.total_budget" placeholder="例如：100" class="form-input" />
			</view>

			<view class="popup-buttons">
				<button class="btn cancel" @click="closeAddPopup">取消</button>
				<button class="btn save" @click="saveTrip">保存</button>
			</view>
		</view>
	</view>
</template>

<script>
	import {
		People,
		Transport
	} from '@icon-park/vue-next';
	import user, {
		getUserInfo
	} from '@/api/user.js';
	import {
		getTripList,
		createTrip,
		deleteTrip
	} from '@/api/trip.js';
	export default {
		data() {
			return {
				currentTab: 'trips',
				activeTab: 'all',
				loading: false,
				nearestTrip: null,
				trips: [],

				// 弹窗控制
				showAddPopup: false,
				addForm: {
					trip_name: '',
					start_date: '',
					end_date: '',
					dest_city: '',
					traveler_type: '',
					start_city: '',
					travel_days: '',
					total_budget: ''
				},

				isShowReload: false, //重试按钮
				userName: '', //用户名
				user_id: '', //用户id
				statusColor: [], //状态码颜色
				statusBarHeight: 44, // 添加状态栏高度属性
				// 默认的封面图列表
				defaultCovers: [
					'/static/index/wuhan16.jpg',
					'/static/index/chongqing.jpg',
					'/static/index/beijing.jpg',
					'/static/index/chengdu.jpg',
					'/static/index/sanya.jpg',
					'/static/index/xian.jpg'
				]
			}
		},
		async onShow() {

			// 获取今天日期，禁止选择过去时间
			const date = new Date();
			this.todayDate = date.getFullYear() + "-" +
				String(date.getMonth() + 1).padStart(2, '0') + "-" +
				String(date.getDate()).padStart(2, '0');
			// 加载
			this.loading = true;
			// 获取用户信息
			await this.getUserId()
			// 组件创建后立即获取行程数据
			this.fetchUserPlans();

		},
		computed: {
			filteredTrips() {
				return this.trips;
			},
			emptyText() {
				return '行程';
			},
		},
		methods: {
			// 保存行程
			async saveTrip() {
				const {
					trip_name,
					start_date,
					end_date,
					start_city,
					dest_city,
					traveler_type
				} = this.addForm
				// 1. 校验必填项
				if (!trip_name) {
					uni.showToast({
						title: '请输入行程标题',
						icon: 'none'
					})
					return
				}
				if (!start_date || !end_date) {
					uni.showToast({
						title: '请选择开始/结束日期',
						icon: 'none'
					})
					return
				}
				if (!start_city) {
					uni.showToast({
						title: '请输入出发地',
						icon: 'none'
					})
					return
				}
				if (!dest_city) {
					uni.showToast({
						title: '请输入目的地',
						icon: 'none'
					})
					return
				}
				if (!traveler_type) {
					uni.showToast({
						title: '请输入同行人类型',
						icon: 'none'
					})
					return
				}
				// 2. 自动计算出行天数
				const start = new Date(this.addForm.start_date)
				const end = new Date(this.addForm.end_date)
				const days = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1
				this.addForm.travel_days = days

				// 获取用户信息（可选，用于默认值等）
				let userInfo = uni.getStorageSync('userInfo');
				if (userInfo && typeof userInfo === 'string') {
					try {
						userInfo = JSON.parse(userInfo);
					} catch (e) {
						userInfo = {};
					}
				}

				const data = {
					user_id: this.user_id,
					trip_name: this.addForm.trip_name,
					start_city: this.addForm.start_city,
					dest_city: this.addForm.dest_city,
					travel_days: this.addForm.travel_days,
					start_date: this.addForm.start_date,
					end_date: this.addForm.end_date,
					total_budget: this.addForm.total_budget,
					traveler_type: this.addForm.traveler_type,
					trip_status: 0, // 默认状态为未开始

				}

				console.log('提交的数据：', data)



				// 3. 提交后端
				uni.showLoading({
					title: '保存中...'
				})
				try {
					// 后端 TripCreateRequest 仅接受：trip_name/dest_city/start_date/end_date/total_budget
					// travel_days 由后端根据日期自动计算；start_city/traveler_type 暂不存储
					const res = await createTrip({
						trip_name: this.addForm.trip_name,
						dest_city: this.addForm.dest_city,
						start_date: this.addForm.start_date,
						end_date: this.addForm.end_date,
						total_budget: this.addForm.total_budget
					})

					if (res.data.code === 200) {
						uni.showToast({
							title: '保存成功'
						})
						this.closeAddPopup() // 关闭弹窗
						this.fetchUserPlans() // 刷新行程列表
						// 清空表单
						this.addForm = {
							trip_name: '',
							start_date: '',
							end_date: '',
							dest_city: '',
							traveler_type: '',
							start_city: '武汉',
							travel_days: 1,
							total_budget: 0
						}
					} else {
						uni.showToast({
							title: res.data.message || '保存失败',
							icon: 'none'
						})
					}
				} catch (err) {
					uni.showToast({
						title: err?.data?.message || '网络异常',
						icon: 'none'
					})
				} finally {
					uni.hideLoading()
				}

			},

			// 开始日期选择
			onStartDateChange(e) {
				this.addForm.start_date = e.detail.value;
			},
			// 结束日期选择
			onEndDateChange(e) {
				this.addForm.end_date = e.detail.value;
			},
			// ========== 打开弹窗 ==========
			addNewTrip() {
				this.showAddPopup = true;
			},
			closeAddPopup() {
				this.showAddPopup = false;
			},


			// 删除行程
			del_list(index) {
				uni.showModal({
					title: "提示",
					content: "确定要删除该行程吗？",
					success: async (e) => {
						if (!e.confirm) return;

						uni.showLoading({
							title: "删除中"
						});

						try {
							// 1. 获取当前行程ID
							const trip_id = this.trips[index].id;

							// 调用真实接口删除
							const res = await deleteTrip(trip_id);

							// 2. 根据返回判断
							const data = res.data;
							if (data.code === 200) {
								uni.showToast({
									title: "删除成功"
								});
								this.fetchUserPlans(); // 刷新列表
							} else {
								uni.showToast({
									title: data.message || "删除失败",
									icon: "none"
								});
							}
						} catch (err) {
							uni.showToast({
								title: err?.data?.message || "网络异常",
								icon: "none"
							});
						} finally {
							uni.hideLoading();
						}
					}
				});
			},
			// 获取用户id
			async getUserId() {
				try {
					// 先尝试从本地存储获取
					let userInfo = uni.getStorageSync('userInfo');
					if (userInfo) {
						if (typeof userInfo === 'string') {
							userInfo = JSON.parse(userInfo);
						}
						// 兼容不同的数据格式
						this.user_id = userInfo.id || userInfo.data?.id || '';
						console.log('从本地存储获取用户ID：', this.user_id);
						return;
					}
					
					// 如果本地没有，调用API获取
					const res = await getUserInfo();
					console.log('API返回的用户信息：', res);
					if (res && res.data && res.data.code === 200) {
						this.user_id = res.data.data.id;
						console.log('从API获取用户ID：', this.user_id);
					}
				} catch (error) {
					console.error('获取用户ID失败：', error);
				}
			},
			// 获取用户行程数据
			async fetchUserPlans() {
				this.loading = true
				uni.showLoading({
					title: '加载中'
				})
				try {
					// 后端基于 token 自动识别当前用户，无需传 user_id
					const response = await getTripList()

					this.loading = false
					console.log('获取的用户行程列表为：', response)
					if (response.statusCode === 200 && response.data) {
						this.trips = response.data.data || []
						console.log('存储的trips行程列表：', this.trips)
					}
				} catch (error) {
					console.error('获取行程异常:', error);
					uni.showToast({
						title: '加载失败',
						icon: 'none'
					})
					this.isShowReload = true
				} finally {
					this.loading = false;
					uni.hideLoading()
				}
			},

			// 重新加载
			handleReload() {
				this.fetchUserPlans()
			},
			// 判断行程状态码
			formatTripStatus(dateStart, dateEnd) {
				const currentDate = new Date();

				// 转换API数据格式

				// 解析日期字符串为Date对象
				const startDate = dateStart ? new Date(dateStart) : new Date();
				const endDate = dateEnd ? new Date(dateEnd) : new Date(startDate.getTime() +
					86400000); // 默认+1天

				// 计算距离开始日期的天数
				const timeDiff = startDate.getTime() - currentDate.getTime();
				const daysLeft = Math.ceil(timeDiff / (1000 * 3600 * 24));

				// 确定行程状态

				let status = '准备中';
				if (currentDate > endDate) {
					status = '已完成';
				} else if (currentDate >= startDate && currentDate <= endDate) {
					status = '进行中';

				} else if (daysLeft <= 7) {
					status = '即将出发';
				}
				return status
			},

			// 格式化日期为YYYY/MM/DD格式
			formatDate(date) {
				const year = date.getFullYear();
				const month = String(date.getMonth() + 1).padStart(2, '0');
				const day = String(date.getDate()).padStart(2, '0');
				return `${year}/${month}/${day}`;
			},
			viewTripDetail(item, status) {
				// 导航到行程详情页
				// uni.navigateTo({
				// 	url: `/pages/trips/detail?id=${trip.id}`
				// });
				console.log('item是：', item)
				console.log('状态码是:', status)
				uni.navigateTo({
					url: `/pages/trips/detail?trip_id=${item.id}&status=${status}&trip_name=${item.trip_name}&city=${item.dest_city}&traveler_type=${item.traveler_type}&total_budget=${item.total_budget}`
				})
				console.log(item.id)
				console.log(status)
			},
			getTransportName(transport) {
				const names = {
					'plane': '飞机',
					'train': '火车',
					'car': '汽车',
					'bus': '巴士',
					'ship': '轮船'
				};
				return names[transport] || '未指定';
			}
		}
	}
</script>
<style lang="scss" scoped>
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

	/* ===== 弹窗样式 ===== */
	.popup-mask {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(15, 23, 42, 0.55);
		z-index: 100;
		backdrop-filter: blur(4px);
	}

	.popup-content {
		position: fixed;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 86%;
		max-width: 700rpx;
		background: #fff;
		border-radius: 24rpx;
		padding: 34rpx 30rpx;
		box-sizing: border-box;
		z-index: 200;
		overflow: visible !important;
		box-shadow: 0 24rpx 60rpx rgba(15, 23, 42, 0.2);
	}

	.popup-title {
		font-size: 34rpx;
		font-weight: 700;
		text-align: center;
		margin-bottom: 32rpx;
		color: $text-1;
		letter-spacing: 1rpx;
	}

	.form-item {
		margin-bottom: 26rpx;
	}

	.form-item .label {
		font-size: 28rpx;
		color: $brand;
		font-weight: 600;
		margin-bottom: 12rpx;
		display: block;
		letter-spacing: 0.5rpx;
	}

	.form-input {
		border: 1rpx solid $border;
		border-radius: 14rpx;
		padding: 0 18rpx;
		font-size: 28rpx;
		font-weight: 500;
		width: 100%;
		box-sizing: border-box;
		height: 76rpx;
		background: #f8fafc;
		color: $text-1;
		transition: all 0.2s ease;

		&:focus {
			border-color: $brand;
			background: #fff;
			box-shadow: 0 0 0 3px rgba(46, 134, 222, 0.12);
		}
	}

	.picker-input {
		color: $text-1;
		line-height: 76rpx;
	}

	.popup-buttons {
		display: flex;
		justify-content: space-around;
		margin-top: 40rpx;
		height: 90rpx;
		gap: 16rpx;
	}

	.popup-buttons .btn {
		flex: 1;
		padding: 20rpx;
		border-radius: 16rpx;
		font-size: 28rpx;
		font-weight: 500;
		margin-bottom: 0rpx;
		border: none;
		transition: all 0.2s ease;
	}

	.btn.cancel {
		background: #f1f5f9;
		color: $text-2;

		&:active {
			background: #e2e8f0;
		}
	}

	.btn.save {
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		color: #fff;
		box-shadow: 0 8rpx 20rpx rgba(46, 134, 222, 0.28);

		&:active {
			transform: scale(0.97);
		}
	}

	/* 双日期选择器 */
	.date-picker-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10rpx;
	}

	.date-split {
		padding: 0 10rpx;
		color: $text-3;
		font-size: 26rpx;
	}

	.form-input.picker-input {
		text-align: center;
		min-width: 200rpx;
	}

	// ////////////////

	/* 删除按钮 */
	.button-del {
		width: 28%;
		font-size: 13px;
		border-radius: 10px;
		background-color: rgba(100, 116, 139, 0.85);
		color: #fff;
		margin-bottom: auto;
		margin-left: 70%;
		z-index: 10;
		padding: 0;
		line-height: 36px;
		height: 36px;
		transition: all 0.2s ease;

		&:active {
			background-color: $danger;
		}
	}

	.button-add {
		margin: auto 0;
		width: 35%;
		height: 36px;
		font-size: 14px;
		font-weight: bold;
		color: #fff;
		vertical-align: middle;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		border-radius: 18px;
	}

	/* ===== 主容器 ===== */
	.trips-container {
		min-height: 100vh;
		height: 100vh;
		display: flex;
		flex-direction: column;
		background-color: $bg-page;
		position: relative;
		overflow: hidden;
	}

	/* 顶部安全区域 */
	.safe-area-top {
		width: 100%;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		position: sticky;
		top: 0;
		z-index: 100;
	}

	/* 顶部状态栏：品牌渐变 */
	.status-bar {
		flex-shrink: 0;
		z-index: 10;
		padding: 14px 16px;
		padding-top: calc(14px + env(safe-area-inset-top));
		display: flex;
		justify-content: space-between;
		align-items: center;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		box-shadow: 0 8rpx 24rpx rgba(46, 134, 222, 0.18);
		border-bottom-left-radius: 24rpx;
		border-bottom-right-radius: 24rpx;
	}

	.location-brief {
		display: flex;
		align-items: center;
	}

	.location-name {
		font-size: 18px;
		font-weight: 600;
		color: #fff;
		letter-spacing: 0.5px;
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
	}

	.header-icons {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.add-icon {
		font-size: 20px;
		color: white;
		background-color: rgba(255, 255, 255, 0.2);
		width: 40px;
		height: 40px;
		border-radius: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.25s ease;

		&:active {
			transform: scale(0.92);
			background-color: rgba(255, 255, 255, 0.32);
		}
	}

	/* 主要内容区域 */
	.content-area {
		flex: 1;
		width: 100%;
		height: calc(100vh - 60px);
		padding: 14px 15px;
		box-sizing: border-box;
		overflow-y: auto;
		padding-bottom: 16px;
		-webkit-overflow-scrolling: touch;
	}

	/* 加载中提示 */
	.loading-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 60px 0;
		background-color: #fff;
		margin: 16px 0;
		border-radius: 18px;
		box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
	}

	.loading-text {
		font-size: 14px;
		color: $text-3;
	}

	/* 搜索框 */
	.search-bar {
		background-color: #fff;
		border-radius: 14px;
		padding: 12px;
		margin-bottom: 12px;
		display: flex;
		align-items: center;
		box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
	}

	.search-icon,
	.voice-icon {
		font-size: 16px;
		color: $brand;
		margin-right: 8px;
	}

	.voice-icon {
		margin-right: 0;
		margin-left: 8px;
	}

	.search-placeholder {
		font-size: 14px;
		color: $text-1;
		flex: 1;
	}

	/* 行程标签页 */
	.trip-tabs {
		display: none;
	}

	/* 行程列表 */
	.trips-list {
		margin-bottom: 15px;
	}

	/* 空状态 */
	.empty-trips {
		padding: 56px 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		background-color: #fff;
		border-radius: 18px;
		box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
	}

	.empty-icon {
		width: 72px;
		height: 72px;
		background: linear-gradient(135deg, $brand-bg 0%, #d1f0e8 100%);
		border-radius: 36px;
		margin-bottom: 18px;
		position: relative;

		&::before {
			content: "";
			position: absolute;
			inset: 22px;
			border: 3rpx solid $brand;
			border-radius: 8rpx;
			opacity: 0.5;
		}
	}

	.empty-text {
		font-size: 14px;
		color: $text-3;
		margin-bottom: 20px;
	}

	.add-trip-btn {
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		border-radius: 22px;
		padding: 10px 22px;
		box-shadow: 0 8rpx 20rpx rgba(46, 134, 222, 0.28);
	}

	.add-trip-text {
		font-size: 14px;
		color: #fff;
		font-weight: 500;
	}

	/* ===== 行程卡片 ===== */
	.trip-item {
		display: flex;
		background-color: #fff;
		border-radius: 18px;
		overflow: hidden;
		margin-bottom: 14px;
		box-shadow: 0 6rpx 20rpx rgba(15, 23, 42, 0.06);
		transition: all 0.2s ease;

		&:active {
			transform: scale(0.99);
			box-shadow: 0 4rpx 12rpx rgba(15, 23, 42, 0.08);
		}
	}

	/* 已完成行程 —— 变暗效果 */
	.trip-completed {
		opacity: 0.6;
		filter: grayscale(0.7);
		background: #f8fafc;
	}

	/* 状态徽章颜色 */
	.completed {
		color: #fff;
		background: $brand;
	}

	.preparing {
		color: #fff;
		background: #5BC0DE;
	}

	.ongoing {
		color: #fff;
		background: #ff9f43;
	}

	.ready {
		color: #fff;
		background: #feca57;
	}

	.trip-item-left {
		width: 100px;
		flex-shrink: 0;
	}

	.trip-thumbnail {
		width: 100%;
		height: 120px;
		background-size: cover;
		background-position: center;
		position: relative;
		background-repeat: no-repeat;
	}

	.trip-type-tag {
		position: absolute;
		top: 8px;
		left: 0;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		color: #fff;
		padding: 3px 10px;
		border-radius: 0 100px 100px 0;
		font-size: 10px;
		font-weight: 500;
		box-shadow: 0 2rpx 8rpx rgba(46, 134, 222, 0.3);
	}

	.trip-item-right {
		flex: 1;
		padding: 14px;
		display: flex;
		flex-direction: column;
	}

	.trip-item-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 10px;
	}

	.trip-item-name {
		font-size: 17px;
		font-weight: 700;
		color: $brand !important;
		letter-spacing: 1rpx;
	}

	/* 状态徽章：圆角小标签 */
	.trip-item-status {
		font-size: 11px;
		color: $text-2;
		padding: 4rpx 16rpx;
		border-radius: 100rpx;
		background: #f1f5f9;
		font-weight: 500;

		&.completed {
			color: #fff;
			background: $brand;
		}
	}

	.trip-item-dates,
	.trip-item-location,
	.trip-item-transport {
		display: flex;
		align-items: center;
		margin-bottom: 6px;
	}

	.date-icon,
	.location-icon,
	.transport-icon,
	.reminder-icon,
	.companions-icon {
		font-size: 14px;
		margin-right: 8px;
		flex-shrink: 0;
	}

	.date-icon {
		color: $brand;
	}

	.location-icon {
		color: #ff9f43;
	}

	.transport-icon {
		color: #5BC0DE;
	}

	.transport-icon.fa-plane {
		color: #5BC0DE;
	}

	.transport-icon.fa-train {
		color: $brand;
	}

	.transport-icon.fa-car {
		color: #ff9f43;
	}

	.transport-icon.fa-bus {
		color: #5BC0DE;
	}

	.transport-icon.fa-ship {
		color: #5BC0DE;
	}

	.trip-item-date,
	.trip-item-place,
	.trip-item-transport-text {
		font-size: 13px;
		font-weight: 500;
		color: $text-2;
	}

	.trip-item-footer {
		display: flex;
		margin-top: auto;
		padding-top: 8px;
	}

	.trip-item-reminder,
	.trip-item-companions {
		display: flex;
		align-items: center;
		margin-right: 15px;
	}

	.reminder-icon {
		color: $danger;
	}

	.companions-icon {
		color: $brand;
	}

	.reminder-text,
	.companions-text {
		font-size: 12px;
		color: $text-2;
	}

	/* 城市一行布局 */
	.city-row {
		display: flex;
		align-items: center;
		gap: 12rpx;
	}

	.city-item {
		flex: 1;
	}

	.small-label {
		font-size: 24rpx;
		color: $text-2;
		margin-bottom: 8rpx;
		display: block;
	}

	.to-text {
		font-size: 30rpx;
		color: $brand;
		font-weight: bold;
		padding: 0 6rpx;
	}
</style>