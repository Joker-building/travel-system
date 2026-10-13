<template>
	<view class="trip-detail-container">
		<view class="page-header">
			<view class="header-left" @click="goBack">
				<text class="back-icon">←</text>
			</view>
		</view>

		<scroll-view scroll-y class="content-area">
			<view class="loading-container" v-if="loading">
				<view class="loading-spinner"></view>
				<text class="loading-text">加载行程详情中...</text>
			</view>

			<view class="error-container" v-else-if="errorMsg">
				<view class="error-icon">!</view>
				<text class="error-text">{{errorMsg}}</text>
				<view class="error-action" @click="fetchTripDetail">
					<text class="action-text">重新加载</text>
				</view>
			</view>

			<view class="trip-info" v-else-if="Details">
				<!-- 行程标题栏：预算统计 -->
				<view class="trip-title-bar">
					<view class="title-main">
						<input v-if="isEditingTitle" class="title-input" v-model="tripTitle" @blur="saveTitle"
							@confirm="saveTitle" placeholder="请输入行程名称" auto-height maxlength="20" />
						<view v-else class="title-view">
							<text class="title-text">{{ tripTitle }}</text>
							<text class="edit-icon" @click="startEditTitle">✏️</text>

						</view>
						<!-- 预算展示 -->
						<view class="budget-stat">
							<text class="budget-total">总预算：¥{{ wholeBudget }}</text>
							<text class="budget-daily">今日：¥{{ currentDayBudget }}</text>
							<text class="budget-daily">日均：¥{{ dailyBudget }}</text>
						</view>
					</view>
					<view class="title-more" @click="showMoreMenu">
						<text>⋯</text>
					</view>
				</view>

				<!-- 日期标签栏 -->
				<view class="day-tab-container">
					<scroll-view class="day-scroll" scroll-x="true" scroll-with-animation="true"
						:scroll-left="scrollLeft">
						<view class="day-item" v-for="(item, index) in dayList" :key="index"
							:class="{ active: currentIndex === index }" @click="switchDay(index)">
							<view class="day-inner">
								<text class="day-text-scroll">{{ item }}</text>
								<!-- 选中 & 不是总览 → 显示垃圾桶 -->
								<text v-if="index !== 0 && currentIndex === index" class="del-icon"
									@click.stop="deleteDay(index)">
									<uni-icons type="trash" size="18" color="#ffffff"></uni-icons>️
								</text>
							</view>
						</view>

						<view class="day-item add-day-btn" @click="addNewDay">
							<text>+</text>
						</view>
					</scroll-view>
				</view>

				<!-- 行程概况标题 -->
				<view v-if="showOverview" style="font-size: 32rpx;font-weight: bold;margin:-20rpx 30rpx 20rpx 30rpx;">
					行程概况
				</view>

				<!-- 总览卡片列表 -->
				<view class="itinerary-container" v-if="showOverview">
					<view class="itinerary-card" v-for="(item, index) in filteredItineraryList" :key="index"
						@click="handleCardClick(item, index)">
						<view class="card-title">{{ item.dayTitle }}</view>
						<view class="card-date">{{ item.city }} {{ item.date }}</view>
						<view class="card-places">
							<view class="place-item" v-for="(place, pIndex) in item.places" :key="pIndex">
								{{ place }}
							</view>
						</view>
						<view class="card-arrow">></view>
					</view>

					<view class="empty-overview" v-if="filteredItineraryList.length === 0">
						<text class="empty-text">暂无行程安排</text>
					</view>
				</view>

				<!-- 时间段详情：可拖拽排序 -->
				<view class="page-container" v-if="!showOverview">
					<scroll-view scroll-y class="slot-list" :style="{ height: '100%' }">
						<view v-for="(item, index) in timeSlotList" :key="index" class="slot-item"
							:class="{ dragging: item.dragging }" :data-index="index" @longpress="startDrag"
							@touchmove="onDrag" @touchend="endDrag">
							<!-- 点击卡片 → 获取景点详情 -->
							<SpotTimeSlotCard :timeSlot="item" @click="openSpotDetail(item)"
								@more-action="handleMoreAction(item, index)" />
						</view>
					</scroll-view>
				</view>

				<!-- ====================== 添加地点 ====================== -->
				<view class="add-spot-box" v-if="!showOverview">
					<view class="add-spot-btn" @click="showAddPanel = !showAddPanel">
						<text class="add-icon">+</text>
						<text>添加地点</text>
					</view>

					<view class="add-panel" v-show="showAddPanel">
						<input class="search-input" v-model="searchKeyword" placeholder="搜索当前城市景点..."
							@input="onSearchInput" />

						<scroll-view scroll-y class="spot-list">
							<view class="spot-item" v-for="item in filteredSpotList" :key="item.id"
								@click="chooseSpot(item)">
								<view class="spot-name">{{ item.name }}</view>
							</view>
							<view class="no-result" v-if="searchKeyword && filteredSpotList.length === 0">
								<text>未找到「{{ searchKeyword }}」</text>
								<view class="ai-btn" @click="aiGenerateSpot">
									<text>让 AI 搜索该景点</text>
								</view>
							</view>

						</scroll-view>
					</view>
				</view>
			</view>
		</scroll-view>
	</view>

	<!-- 时间选择器（隐藏） -->
	<view style="display:none;">
		<picker mode="time" :value="startTime" @change="onStartTimeChange">
			<view ref="startTimePicker"></view>
		</picker>
		<picker mode="time" :value="endTime" @change="onEndTimeChange">
			<view ref="endTimePicker"></view>
		</picker>
	</view>


	<!-- 底部抽屉 景点详情 -->
	<view class="drawer-mask" v-if="showSpotModal" @click="showSpotModal=false"></view>
	<view class="spot-drawer" :class="showSpotModal ? 'drawer-open' : ''">
		<view class="drawer-header">
			<view class="drawer-bar"></view>
			<text class="drawer-title">{{ spotDetail.name }}</text>
			<text class="drawer-close" @click="showSpotModal=false">关闭</text>
		</view>
		<scroll-view scroll-y class="drawer-body">
			<!-- 加载中状态 -->
			<view class="loading-inner" v-if="detailLoading">
				<view class="loading-spinner"></view>
				<text>正在获取...</text>
			</view>
			<!-- 加载完成显示内容 -->
			<view v-else>
				<view class="detail-item">
					<text class="label">景区介绍</text>
					<text class="value">{{ spotDetail.intro || '暂无介绍' }}</text>
				</view>
				<view class="detail-item">
					<text class="label">门票价格</text>
					<text class="value"
						:style="{ color: spotDetail.ticket === '免费' ? '#07c160' : '#ff3b30' }">{{ spotDetail.ticket || '暂无信息' }}</text>
				</view>
				<view class="detail-item">
					<text class="label">景区地址</text>
					<text class="value">{{ spotDetail.address || '暂无信息' }}</text>
				</view>
				<view class="detail-item">
					<text class="label">开放时间</text>
					<text class="value">{{ spotDetail.open_time || '暂无信息' }}</text>
				</view>
				<view class="detail-item">
					<text class="label">您的预算</text>
					<text class="value" :style="{ 
						      color: !spotDetail.budget 
						        ? '#999' 
						        : (spotDetail.budget === 0 || spotDetail.budget === '免费') 
						          ? '#07c160' 
						          : '#ff3b30' 
						    }">{{ !spotDetail.budget 
        ? '暂无信息' 
        : (spotDetail.budget === 0 || spotDetail.budget === '免费') 
          ? '免费' 
          : spotDetail.budget  }}</text>
				</view>
				<view class="detail-item">
					<text class="label">预算规划</text>
					<text class="value">{{ spotDetail.budgetPlanning || '暂无信息' }}</text>
				</view>
				<view class="detail-item">
					<text class="label">特殊提醒</text>
					<text class="value">{{ spotDetail.tip || '暂无提醒' }}</text>
					<br />
					<text class="value">*以上信息仅供参考，具体以景区当日实际公示信息为准</text>
				</view>

			</view>
		</scroll-view>
	</view>
</template>

<script>
	import SpotTimeSlotCard from "@/components/SpotTimeSlotCard/SpotTimeSlotCard.vue";
	import {
		getTripDetail,
		updateTrip,
		addDay,
		deleteDay,
		updateTripDetail,
		deleteTripDetail
	} from "@/api/trip.js";
	import {
		searchScenic,
		aiSearchScenic,
		addScenicToTrip,
		getScenicAiDetail
	} from "@/api/scenic.js";

	export default {
		components: {
			SpotTimeSlotCard
		},
		data() {
			return {
				success: false,
				isDisable: true,
				trip_id: '',
				loading: true,
				errorMsg: '',
				tripDetail: null,
				defaultCover: '/static/index/wuhan16.jpg',
				Details: {},
				Details_temp: {},
				status: '',
				Duration: '',
				calendar: [],
				days: [],
				targetDays: [],
				isShowModal: false,
				dayChoose: '',
				isShowData: false,
				isShowNormalData: false,
				isShowChangeButton: true,
				isShowSubmitButton: false,
				isShowCancleButton: false,
				dayList: ['总览'],
				currentIndex: 0,
				scrollLeft: 0,
				itineraryList: [],
				timeSlotList: [],
				rawDetails: [],
				showOverview: true,
				tripTitle: "",
				isEditingTitle: false,

				wholeBudget: 0,
				currentDayBudget: 0,
				dailyBudget: 0,

				isDragging: false,
				dragIndex: -1,
				startY: 0,
				scrollTop: 0,
				dragOffset: 0,

				startTime: '09:00',
				endTime: '11:00',
				tempEditIndex: -1,

				showAddPanel: false,
				searchKeyword: '',
				citySpotList: [],
				currentCity: '', //所属城市
				traveler_type: '', //同行人类型
				// 地图相关
				mapMarkers: [],
				currentDayMarkers: [],
				mapCenterLng: 114.316200,
				mapCenterLat: 30.592900,
				currentDayPolyline: [],

				createdDays: [],

				// ========== 新增：景点详情弹窗数据 ==========
				showSpotModal: false,
				spotDetail: {
					name: '',
					intro: '',
					ticket: '',
					address: '',
					open_time: '',
					budget: '',
					budgetPlanning: '',
					tip: ''
				},
				detailLoading: false
			}
		},
		computed: {
			filteredItineraryList() {
				if (this.currentIndex === 0) {
					return this.itineraryList;
				} else {
					return this.itineraryList.filter(item => item.day_num === this.currentIndex);
				}
			},
			filteredSpotList() {
				if (!this.searchKeyword) return this.citySpotList;
				return this.citySpotList.filter(item =>
					item.name.includes(this.searchKeyword.trim())
				);
			}
		},
		onLoad(options) {
			console.log('页面加载参数：', options)
			this.loading = true
			this.errorMsg = ''
			this.trip_id = options.trip_id || ''
			this.status = options.status || ''
			// currentCity 兜底：优先 options.city（由 trips 列表页传入）；否则等待详情接口返回 dest_city 补齐
			this.currentCity = (options.city && options.city !== 'undefined') ? options.city : '武汉市';
			this.traveler_type = options.traveler_type || '';
			this.tripTitle = options.trip_name || `${this.currentCity}几日游`;

			if (this.trip_id) {
				this.fetchTripDetail(this.trip_id);
				this.success = true
			} else {
				this.errorMsg = '无效的行程ID';
				this.loading = false;
				this.success = false
			}
		},
		methods: {
			// ========== 新增：打开景点详情 ==========
			async openSpotDetail(item) {
				console.log('item:', item)
				const traveler_type = this.traveler_type || (item && item.traveler_type)
				console.log('同行人类型：', traveler_type)
				const spotName = item && item.name;
				let budget = 0;
				if (item) {
					budget = item.user_price != null ?
						Number(item.user_price) || 0 :
						String(item.price || '').includes('免费') ?
						0 :
						parseFloat(String(item.price || '').replace(/[^\d.]/g, '')) || 0;
				}

				const city = this.currentCity;
				console.log('budget:', budget)
				if (!spotName || !city) {
					uni.showToast({ title: '信息不全', icon: 'none' });
					return;
				}

				// 1. 先重置数据
				this.spotDetail = {
					name: spotName,
					intro: '加载中...',
					ticket: '查询中',
					address: '-',
					open_time: '-',
					budget: budget,
					budgetPlanning: '-',
					tip: '-'
				};
				// 2. 先弹出抽屉
				this.showSpotModal = true;
				// 3. 开启加载状态
				this.detailLoading = true;

				try {
					// 调用真实接口：AI 获取景点详情
					const res = await getScenicAiDetail(spotName, city);
					const backendData = (res && res.data && res.data.code === 200 && res.data.data) || null;

					if (backendData) {
						// AI 详情接口未返回 address/open_time 时，用卡片已有的数据兜底
						this.spotDetail = {
							name: spotName,
							intro: backendData.introduction || '暂无介绍',
							ticket: backendData.price || '免费',
							address: backendData.address || (item && item.address) || '暂无信息',
							open_time: backendData.open_time || (item && item.open_time) || '暂无信息',
							tip: backendData.special_notice || '暂无提醒',
							budget: budget,
							budgetPlanning: backendData.budgetPlanning || '暂无规划'
						};
						console.log('渲染的数据是:', this.spotDetail)
					} else {
						this.spotDetail.intro = '暂无介绍';
						this.spotDetail.ticket = '免费';
						uni.showToast({ title: '获取失败', icon: 'none' });
					}
				} catch (err) {
					console.error(err);
					uni.showToast({ title: '网络异常', icon: 'none' });
				} finally {
					this.detailLoading = false;
				}
			},

			// 删除某一天
			async deleteDay(dayIndex) {
				const dayNum = dayIndex;
				const dayName = this.dayList[dayIndex];

				const confirm = await new Promise(resolve => {
					uni.showModal({
						title: "确认删除",
						content: `确定要删除「${dayName}」的所有行程吗？`,
						success: (res) => resolve(res.confirm)
					});
				});
				if (!confirm) return;

				uni.showLoading({ title: "删除中..." });
				try {
					// 调用真实接口：删除指定天数（后端会自动重排后续天数）
					await deleteDay(this.trip_id, dayNum);

					const newRawDetails = (this.rawDetails || []).map(item => {
						if (!item) return item;
						if (item.day_num > dayNum) {
							return { ...item, day_num: item.day_num - 1 };
						}
						return item;
					}).filter(item => item && item.day_num !== dayNum);

					this.rawDetails = newRawDetails;

					const dayNums = [...new Set(newRawDetails.map(item => item && item.day_num).filter(Boolean))].sort((a, b) => a - b);
					this.dayList = ['总览', ...dayNums.map(num => `第${num}天`)];

					if (this.currentIndex === dayIndex) {
						const newIndex = Math.max(0, dayIndex - 1);
						this.switchDay(newIndex);
					} else if (this.currentIndex > dayIndex) {
						this.currentIndex -= 1;
					}

					uni.showToast({ title: "删除成功", icon: "success" });
					this.fetchTripDetail(this.trip_id);
				} catch (err) {
					console.error(err);
					uni.showToast({ title: "删除失败", icon: "none" });
				} finally {
					uni.hideLoading();
				}
			},

			// 添加新一天
			async addNewDay() {
				const allDays = (this.rawDetails || []).map(item => item && item.day_num).filter(Boolean);
				const maxDay = allDays.length ? Math.max(...allDays) : 0;
				const newDay = maxDay + 1;

				uni.showLoading({ title: '创建新天数...' });

				try {
					// 调用真实接口：后端自动 travel_days+1，并返回新的 travel_days
					await addDay(this.trip_id);

					await this.fetchTripDetail(this.trip_id);
					this.switchDay(newDay);
					uni.showToast({ title: `第${newDay}天已创建`, icon: 'success' });
				} catch (e) {
					uni.showToast({ title: '创建失败', icon: 'none' });
				} finally {
					uni.hideLoading();
				}
			},

			// 加载城市景点
				async loadCitySpots() {
					if (!this.currentCity) { this.citySpotList = []; return; }
					try {
						// 后端按城市列出景点（keyword 传空串表示不限定关键词）
						const res = await searchScenic('', this.currentCity);
						this.citySpotList = (res && res.data && res.data.code === 200 && res.data.data) || [];
					} catch (e) {
						console.warn('[detail] loadCitySpots 失败，置空', e);
						this.citySpotList = [];
					}
				},

			onSearchInput() {},

			async chooseSpot(item) {
				let targetDay = this.currentIndex;
				if (targetDay === 0) {
					const day1 = this.dayList && this.dayList[1] ? 1 : 1;
					uni.showModal({
						title: "提示",
						content: "当前处于「总览」，将自动加入第1天。继续吗？",
						success: async (res) => {
							if (!res.confirm) return;
							this.currentIndex = day1;
							this.switchDay(day1);
							await this.addSpotToTrip(item && item.id, item);
						}
					});
					return;
				}
				uni.showModal({
					title: "确认添加",
					content: `要把「${item.name}」加入第${targetDay}天行程吗？`,
					success: async (res) => {
						if (res.confirm) {
							await this.addSpotToTrip(item && item.id, item);
						}
					}
				});
			},
			async aiGenerateSpot() {
				const name = this.searchKeyword.trim();
				if (!name) {
					uni.showToast({ title: "请输入景点名称", icon: "none" });
					return;
				}

				// ==============================================
				// 第一步：AI 搜索候选景点（高德式，返回多个候选并入库）
				// ==============================================
				uni.showLoading({ title: "AI 搜索景点中..." });

				let candidates = [];
				try {
					const res = await aiSearchScenic({ keyword: name, city: this.currentCity });
					candidates = (res && res.data && res.data.code === 200 && res.data.data && res.data.data.results) || [];
				} catch (e) {
					console.error('AI 搜索失败：', e);
					candidates = [];
				}

				uni.hideLoading();

				if (!candidates.length) {
					uni.showToast({ title: "未找到相关景点", icon: "none" });
					return;
				}

				// 取第一个候选作为最佳匹配
				const best = candidates[0];
				const realSpotName = best.name || name;

				// ==============================================
				// 第二步：让用户确认是否正确
				// ==============================================
				uni.showModal({
					title: "AI 搜索结果",
					content: `你想找的是不是：\n「${realSpotName}」· ${this.currentCity}`,
					confirmText: "添加该景点",
					cancelText: "取消",
					success: async (res) => {
						if (res.confirm) {
							// ==============================================
							// 第三步：通过 scenic_id 加入行程
							// ==============================================
							uni.showLoading({ title: "添加中..." });
							// 总览（currentIndex === 0）无法添加：自动切换到第 1 天
							let useDay = this.currentIndex || 1;
							if (useDay === 0) useDay = 1;
							try {
								await addScenicToTrip(best.id, this.trip_id, useDay);

								uni.hideLoading();
								uni.showToast({ title: "添加成功" });
								if (this.currentIndex === 0) {
									this.currentIndex = useDay;
									this.switchDay(useDay);
								}
								this.fetchTripDetail(this.trip_id);
								this.showAddPanel = false;
								this.searchKeyword = "";
							} catch (err) {
								console.error('添加景点失败：', err);
								uni.hideLoading();
								uni.showToast({ title: "添加失败", icon: "none" });
							}
						}
					},
				})
			},

			async addSpotToTrip(scenic_id, spotItem) {
				uni.showLoading();
				try {
					// 总览（currentIndex === 0）时默认加到第 1 天
					let useDay = this.currentIndex || 1;
					if (useDay === 0) useDay = 1;

					// 调用真实接口：后端自动计算 sort_order，并以景点价格初始化 spot_budget
					const res = await addScenicToTrip(scenic_id, this.trip_id, useDay);
					const added = (res && res.data && res.data.code === 200 && res.data.data) || null;

					if (added) {
						this.rawDetails = Array.isArray(this.rawDetails) ? this.rawDetails : [];
						this.rawDetails.push(added);
					}

					uni.hideLoading();
					uni.showToast({ title: "添加成功" });
					this.fetchTripDetail(this.trip_id);
					this.showAddPanel = false;
					this.searchKeyword = "";
				} catch (err) {
					console.log(err)
					uni.hideLoading();
					uni.showToast({ title: "添加失败", icon: "none" });
				}
			},

			handleMoreAction(timeSlot, index) {
				uni.showActionSheet({
					itemList: ['修改时间段', '修改备注', '修改预算', '删除该活动'],
					success: (res) => {
						const i = res.tapIndex
						if (i === 0) this.openEditTimeModal(timeSlot,
							index)
						else if (i === 1) this.handleEditRemark(
							timeSlot, index)
						else if (i === 2) this.openEditPriceModal(
							timeSlot, index)
						else if (i === 3) this.deleteSpotCard(index)
					}
				})
			},

			openEditTimeModal(timeSlot, index) {
				this.tempEditIndex = index
				uni.showModal({
					title: '修改时间段',
					content: '请先选择【开始时间】，再选择【结束时间】',
					confirmText: '去选择',
					cancelText: '取消',
					success: (res) => {
						if (res.confirm) {
							this.$refs.startTimePicker.$el.click()
						}
					}
				})
			},

			onStartTimeChange(e) {
				this.startTime = e.detail.value
				uni.showToast({
					title: '开始时间已选择：' + this.startTime,
					icon: 'none',
					duration: 1000
				})
				this.$nextTick(() => {
					this.$refs.endTimePicker.$el.click()
				})
			},

			onEndTimeChange(e) {
				this.endTime = e.detail.value
				const index = this.tempEditIndex

				const startMin = this.timeToMinute(this.startTime)
				const endMin = this.timeToMinute(this.endTime)

				if (startMin >= endMin) {
					uni.showToast({
						title: '开始时间不能晚于结束时间',
						icon: 'none'
					});
					return
				}

				const hasConflict = this.timeSlotList.some((item, idx) => {
					if (idx === index) return false
					const [t1, t2] = item.time.split('-')
					const sMin = this.timeToMinute(t1)
					const eMin = this.timeToMinute(t2)
					return !(endMin <= sMin || startMin >= eMin)
				})

				if (hasConflict) {
					uni.showToast({
						title: '时间段与其他景点冲突！',
						icon: 'none'
					});
					return
				}

				const originalStartTime = this.timeSlotList[index].original
					.start_time;
				const dateStr = originalStartTime.split('T')[0];
				const newStartDatetime = `${dateStr}T${this.startTime}:00`;
				const newEndDatetime = `${dateStr}T${this.endTime}:00`;

				this.$set(this.timeSlotList[index], 'time',
					`${this.startTime}-${this.endTime}`);
				this.$set(this.timeSlotList[index], 'time_slot',
					`${this.startTime}-${this.endTime}`);
				this.$set(this.timeSlotList[index], 'start_time', newStartDatetime);
				this.$set(this.timeSlotList[index], 'end_time', newEndDatetime);
				this.calculateTotalBudget();

				const detail_id = this.timeSlotList[index].original.id;
				this.saveUpdateToBackend(detail_id, {
					start_time: newStartDatetime,
					end_time: newEndDatetime,
					time_slot: `${this.startTime}-${this.endTime}`
				});

				const rawItem = this.rawDetails.find(r => r.id === detail_id);
				if (rawItem) {
					rawItem.time_slot = `${this.startTime}-${this.endTime}`;
					rawItem.start_time = newStartDatetime;
					rawItem.end_time = newEndDatetime;
				}

				uni.showToast({
					title: '时间段修改成功',
					icon: 'none'
				});
				this.tempEditIndex = -1;
			},

			timeToMinute(timeStr) {
				if (!timeStr) return 0
				const [h, m] = timeStr.split(':').map(Number)
				return h * 60 + m
			},

			handleEditRemark(timeSlot, index) {
				uni.showModal({
					title: '编辑备注',
					editable: true,
					placeholderText: '输入备注',
					success: async (res) => {
						if (res.confirm) {
							const val = res.content.trim()
							this.$set(this.timeSlotList[index],
								'remark', val)
							const detail_id = this.timeSlotList[index]
								.original.id;
							await this.saveUpdateToBackend(detail_id, {
								remark: val
							});
							uni.showToast({
								title: val ? '备注已保存' : '已清空',
								icon: 'none'
							})
						}
					}
				})
			},

			openEditPriceModal(timeSlot, index) {
				uni.showModal({
					title: '修改预算',
					editable: true,
					placeholderText: '输入价格（0=免费）',
					success: async (res) => {
						if (!res.confirm) return
						const num = Number(res.content.trim())
						if (isNaN(num)) {
							uni.showToast({
								title: '请输入数字',
								icon: 'none'
							})
							return
						}
						const showPrice = num <= 0 ? '免费' :
							`${num.toFixed(2)}`
						this.$set(this.timeSlotList[index],
							'user_price', num)
						this.$set(this.timeSlotList[index], 'price',
							showPrice)

						const detail_id = this.timeSlotList[index]
							.original.id;
						const rawItem = this.rawDetails.find(r => r
							.id === detail_id);
						if (rawItem) {
							rawItem.user_price = num;
						}
						await this.saveUpdateToBackend(detail_id, {
							user_price: num
						});
						this.calculateTotalBudget()
						uni.showToast({
							title: '预算已更新',
							icon: 'none'
						})
					}
				})
			},

			deleteSpotCard(index) {
				uni.showModal({
					title: '确认删除',
					content: '确定删除该活动？',
					success: async (res) => {
						if (res.confirm) {
							const detail_id = this.timeSlotList[index]
								.original.id;
							try {
								await deleteTripDetail(detail_id);

								this.timeSlotList.splice(index, 1);
								this.rawDetails = this.rawDetails
									.filter(item => item.id !==
										detail_id);

								this.calculateTotalBudget();
								uni.showToast({
									title: '删除成功',
									icon: 'success'
								});
							} catch (err) {
								uni.showToast({
									title: '删除失败',
									icon: 'none'
								});
							}
						}
					}
				})
			},

			// 自动删除默认景点
			async autoDeleteSpotCard(detail_id) {
				try {
					await deleteTripDetail(detail_id);

					this.rawDetails = this.rawDetails.filter(item => item.id !==
						detail_id);
					this.timeSlotList = this.timeSlotList.filter(item => item.original
						.id !== detail_id);
					this.calculateTotalBudget();
				} catch (err) {
					console.log(err)
				}
			},

			async saveUpdateToBackend(detail_id, updateData) {
				try {
					// updateTripDetail 会把页面字段（start_time/end_time/user_price 等）
					// 转换为后端期望的 { start_time, end_time, spot_budget, remark, sort_order, day_num }
					const res = await updateTripDetail(detail_id, updateData);
					if (res.data.code === 200) {
						console.log("✅ 保存成功", res.data);
						return true;
					} else {
						uni.showToast({
							title: res.data.message || "保存失败",
							icon: "none"
						});
						return false;
					}
				} catch (err) {
					console.error("❌ 接口调用失败", err);
					uni.showToast({
						title: "网络异常",
						icon: "none"
					});
					return false;
				}
			},

			calculateTotalBudget() {
				const raw = Array.isArray(this.rawDetails) ? this.rawDetails : [];
				const days = raw.map(item => item && item.day_num).filter(Boolean);
				const totalTripDays = days.length ? Math.max(...days) : 1;

				let wholeTotal = 0;
				raw.forEach(item => {
					if (!item) return;
					let price = 0;
					if (item.user_price != null) {
						price = Number(item.user_price) || 0;
					} else {
						const scenic = item.scenic_info || {};
						const rawPrice = String(scenic.price || '0').replace(/[^\d.]/g, '');
						price = Number(rawPrice) || 0;
					}
					wholeTotal += price;
				});

				const slots = Array.isArray(this.timeSlotList) ? this.timeSlotList : [];
				let dayTotal = 0;
				slots.forEach(item => {
					if (!item) return;
					let price = 0;
					if (item.user_price !== undefined && item.user_price !== null) {
						price = Number(item.user_price) || 0;
					} else if (item.price === '免费') {
						price = 0;
					} else {
						const rawPrice = String(item.price || '0').replace(/[^\d.]/g, '');
						price = Number(rawPrice) || 0;
					}
					dayTotal += price;
				});

				this.wholeBudget = Number(wholeTotal.toFixed(2));
				this.currentDayBudget = Number(dayTotal.toFixed(2));
				this.dailyBudget = totalTripDays ? Number((wholeTotal / totalTripDays).toFixed(2)) : 0;
			},

			startEditTitle() {
				this.isEditingTitle = true;
				this.$nextTick(() => {
					uni.createSelectorQuery().select(
						'.title-input').focus();
				});
			},
			async saveTitle() {
				this.isEditingTitle = false;
				try {
					// 调用真实接口：更新行程标题
					await updateTrip(this.trip_id, { trip_name: this.tripTitle });
					uni.showToast({ title: "标题已保存", icon: "none" });
				} catch (err) {
					console.error('标题保存失败：', err);
					uni.showToast({ title: "保存失败", icon: "none" });
				}
			},
			showMoreMenu() {
				uni.showActionSheet({
					itemList: ['删除行程'],
					success: (res) => {}
				});
			},
			switchDay(index) {
				this.currentIndex = index;
				const raw = Array.isArray(this.rawDetails) ? this.rawDetails : [];
				if (index === 0) {
					this.showOverview = true;
					this.timeSlotList = [];
				} else {
					this.showOverview = false;
					const dayNum = index;
					const dayDetails = raw.filter(item => item && item.day_num === dayNum);
					this.renderTimeSlotList(dayDetails);
					this.loadCitySpots();
				}
				this.calculateTotalBudget();
			},
			handleCardClick(item, index) {
				if (!item) return;
				this.showOverview = false;
				this.currentIndex = item.day_num;
				const raw = Array.isArray(this.rawDetails) ? this.rawDetails : [];
				const dayDetails = raw.filter(d => d && d.day_num === item.day_num);
				this.renderTimeSlotList(dayDetails);
				this.scrollLeft = (item.day_num - 1) * 140;
				this.loadCitySpots();
				this.calculateTotalBudget();
			},
			getOverviewList(details) {
				const groups = {};
				const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
				const safe = Array.isArray(details) ? details : [];
				safe.forEach(item => {
					if (!item) return;
					const day = item.day_num;
					const scenic = item.scenic_info || {};
					if (!day) return;
					if (!groups[day]) {
						const ts = item.start_time || new Date().toISOString();
						const dateStr = (ts || '').split('T')[0] || new Date().toISOString().split('T')[0];
						const parsed = new Date(dateStr);
						const weekDay = isNaN(parsed.getTime()) ? '' : (weekDays[parsed.getDay()] || '');
						groups[day] = {
							dayTitle: `第${day}天`,
							day_num: day,
							city: scenic.city || this.currentCity || '武汉',
							date: `${dateStr}${weekDay ? ' ' + weekDay : ''}`,
							places: []
						};
					}
					const name = scenic.name;
					if (name && !groups[day].places.includes(name)) {
						groups[day].places.push(name);
					}
				});
				return Object.values(groups).sort((a, b) => a.day_num - b.day_num);
			},
			renderOverviewList(details) {
				this.itineraryList = this.getOverviewList(details);
			},
			renderTimeSlotList(details) {
				const safe = Array.isArray(details) ? details : [];
				const timeSlots = safe
					.filter(Boolean)
					.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
					.map(item => {
						const scenic = item.scenic_info || {};
						let price = scenic.price || '';
						const purePrice = String(price).replace(/[^\d.]/g, '');
						const finalPrice = purePrice === '0.00' || purePrice === '' ? '免费' : price;
						return {
							start_time: item.start_time || '',
							end_time: item.end_time || '',
							time_slot: item.time_slot || '',
							type: item.type || "spot",
							sort_order: item.sort_order || 0,
							remark: item.remark || '',
							time: item.time_slot || '',
							name: scenic.name || '未命名景点',
							image: scenic.image || '',
							score: scenic.score || '0.0',
							address: scenic.address || '暂无地址',
							price: finalPrice,
							user_price: item.user_price != null ? item.user_price : null,
							open_time: scenic.open_time || '',
							suggest_duration: scenic.suggest_duration || '',
							introduction: scenic.introduction || '',
							best_season: scenic.best_season || '',
							original: item,
							dragging: false
						};
					});
				this.timeSlotList = timeSlots;
				this.calculateTotalBudget();
			},
			startDrag(e) {
				this.isDragging = true;
				this.dragIndex = parseInt(e.currentTarget.dataset.index);
				this.startY = e.touches ? e.touches[0].clientY : e.clientY;
				this.$set(this.timeSlotList[this.dragIndex], 'dragging',
					true);
			},
			onDrag(e) {
				if (!this.isDragging) return;
				const currentY = e.touches ? e.touches[0].clientY : e
					.clientY;
				const moveY = currentY - this.startY;
				const cardHeight = 80;
				const offset = Math.floor(moveY / cardHeight);
				if (offset === 0) return;
				const newIndex = this.dragIndex + offset;
				if (newIndex < 0 || newIndex >= this.timeSlotList.length)
					return;

				const dragTime = this.timeSlotList[this.dragIndex].time;
				const newTime = this.timeSlotList[newIndex].time;
				const dragItem = {
					...this.timeSlotList[this.dragIndex]
				};
				const newItem = {
					...this.timeSlotList[newIndex]
				};

				this.$set(this.timeSlotList, this.dragIndex, {
					...newItem,
					time: dragTime
				});
				this.$set(this.timeSlotList, newIndex, {
					...dragItem,
					time: newTime
				});
				this.dragIndex = newIndex;
				this.startY = currentY;
			},
			endDrag() {
				if (!this.isDragging) return;
				this.isDragging = false;
				this.timeSlotList.forEach(item => {
					this.$set(item, 'dragging', false);
				});

				this.calculateTotalBudget();
			},
			// 获取行程详情
			async fetchTripDetail(trip_id) {
				this.loading = true;
				this.errorMsg = '';
				let responseData = null;
				try {
					// 调用真实后端接口（api/trip.js 已将 details 转换为页面期望结构）
					const res = await getTripDetail(trip_id);
					responseData = (res && res.data && res.data.code === 200 && res.data.data) || null;

					// 严格空保护：details 必须是数组
					const details = Array.isArray(responseData && responseData.details)
						? responseData.details
						: [];
					this.rawDetails = details;
					console.log('[detail] rawDetails =', details);

					// 固定连续天数 1、2、3...永远不乱序
					const allDays = details.map(item => item && item.day_num).filter(Boolean);
					const maxDay = allDays.length ? Math.max(...allDays) : 0;

					let continuousDays = [];
					for (let i = 1; i <= maxDay; i++) {
						continuousDays.push(i);
					}
					// 后端 travel_days 为权威天数，取两者较大值保证天数标签不丢
					const tripDays = (responseData && responseData.travel_days) || 0;
					const dayCount = Math.max(maxDay, tripDays, 0);
					let dayNums = [];
					for (let i = 1; i <= dayCount; i++) {
						dayNums.push(i);
					}
					if (dayNums.length === 0) dayNums = [1];
					this.dayList = ['总览', ...dayNums.map(num => `第${num}天`)];

					this.renderOverviewList(details);
					this.timeSlotList = [];
					// Details 用于模板 v-else-if="Details" 判断，保证即使接口返回空对象也能显示主内容
					this.Details = responseData || {
						trip_id,
						trip_name: this.tripTitle,
						dest_city: this.currentCity,
						traveler_type: this.traveler_type,
						details: []
					};

					// 若 trips 列表没带 city，用详情里的 dest_city 补齐
					if ((!this.currentCity || this.currentCity === '武汉市') && this.Details && this.Details.dest_city) {
						this.currentCity = this.Details.dest_city;
					}
					// 同步标题
					if (this.Details && this.Details.trip_name) {
						this.tripTitle = this.Details.trip_name;
					}

					this.calculateTotalBudget();

					if (this.currentIndex !== 0) {
						const dayDetails = this.rawDetails.filter(
							item => item && item.day_num === this.currentIndex
						);
						this.renderTimeSlotList(dayDetails);
						this.loadCitySpots();
					} else {
						// 总览页也需要城市景点列表（便于用户添加景点）
						this.loadCitySpots();
					}
				} catch (error) {
					console.error('[detail] fetchTripDetail 异常：', error);
					this.errorMsg = '获取行程详情失败：' + (error && error.errMsg ? error.errMsg : (error && error.message ? error.message : '未知错误'));
				} finally {
					this.loading = false;
				}
			},

			goBack() {
				uni.navigateBack();
			},



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

	/* ===== 添加地点区 ===== */
	.add-spot-box {
		width: 90%;
		margin: 0 auto 30rpx auto;
	}

	.add-spot-btn {
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		color: #fff;
		border-radius: 16rpx;
		padding: 24rpx;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12rpx;
		font-size: 30rpx;
		font-weight: 500;
		box-shadow: 0 8rpx 20rpx rgba(46, 134, 222, 0.25);

		.add-icon {
			font-size: 36rpx;
			font-weight: bold;
		}

		&:active {
			transform: scale(0.98);
		}
	}

	.add-panel {
		background: #fff;
		border-radius: 18rpx;
		padding: 24rpx;
		margin-top: 20rpx;
		box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.06);
	}

	.search-input {
		border: 1rpx solid $border;
		border-radius: 14rpx;
		padding: 20rpx;
		font-size: 28rpx;
		margin-bottom: 20rpx;
		background: #f8fafc;
		transition: all 0.2s ease;

		&:focus {
			border-color: $brand;
			background: #fff;
			box-shadow: 0 0 0 3px rgba(46, 134, 222, 0.12);
		}
	}

	.spot-list {
		max-height: 500rpx;
	}

	.spot-item {
		padding: 24rpx 8rpx;
		border-bottom: 1rpx solid #f1f5f9;
		transition: background 0.2s ease;

		&:active {
			background: $brand-bg;
		}

		.spot-name {
			font-size: 30rpx;
			color: $text-1;
			font-weight: 600;
		}
	}

	/* ===== 行程标题栏 ===== */
	.trip-title-bar {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		width: 90%;
		margin: 20rpx auto;
		padding: 28rpx;
		border: none;
		border-radius: 20rpx;
		background-color: #fff;
		box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.06);
	}

	.title-main {
		display: flex;
		flex-direction: column;
		flex: 1;
		gap: 10rpx;
	}

	.budget-stat {
		display: flex;
		gap: 20rpx;
		align-items: center;
		margin-top: 16rpx;
		padding: 14rpx 18rpx;
		background: $brand-bg;
		border-radius: 14rpx;
		flex-wrap: wrap;
	}

	.budget-total {
		font-size: 30rpx;
		color: $brand;
		font-weight: bold;
	}

	.budget-daily {
		font-size: 26rpx;
		color: $text-2;
	}

	.title-view {
		display: flex;
		align-items: center;
		gap: 15rpx;
	}

	.title-text {
		font-size: 36rpx;
		font-weight: 800;
		letter-spacing: 2rpx;
		color: $brand;
	}

	.edit-icon {
		font-size: 26rpx;
		color: $brand;
		cursor: pointer;
		padding: 6rpx 10rpx;
		border-radius: 10rpx;
		border: 1rpx solid $brand;
		background: $brand-bg;
	}

	.title-input {
		flex: 1;
		font-size: 32rpx;
		color: $text-1;
		padding: 8rpx 0;
		border: none;
		border-bottom: 2rpx solid $brand;
		outline: none;
		font-weight: 700;
	}

	.title-more {
		font-size: 36rpx;
		color: $text-3;
		align-self: center;
		padding: 0 8rpx;

		&:active {
			color: $brand;
		}
	}

	/* ===== 时间段卡片 ===== */
	.slot-item {
		transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
		transform: translate3d(0, 0, 0);
		margin-bottom: 18rpx;
	}

	.slot-item.dragging {
		opacity: 0.9;
		background-color: $brand-bg;
		border: 2rpx dashed $brand;
		border-radius: 18rpx;
		transform: scale(1.02);
		box-shadow: 0 12rpx 32rpx rgba(46, 134, 222, 0.2);
		z-index: 10;
	}

	.slot-list {
		width: 100%;
		height: calc(100vh - 300rpx);
	}

	/* ===== 主容器 ===== */
	.trip-detail-container {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background-color: $bg-page;
		position: relative;
	}

	.page-header {
		display: flex;
		align-items: center;
		height: 56px;
		padding: 0 16px;
		padding-top: env(safe-area-inset-top);
		background-color: transparent;
		position: relative;
		z-index: 10;

		.header-left {
			width: 36px;
			height: 36px;
			display: flex;
			justify-content: center;
			line-height: 36px;
			align-items: center;
			background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
			border-radius: 50%;
			box-shadow: 0 6rpx 16rpx rgba(46, 134, 222, 0.3);

			.back-icon {
				font-size: 22px;
				color: #fff;
				font-weight: bold;
			}

			&:active {
				transform: scale(0.92);
			}
		}
	}

	.content-area {
		flex: 1;
		width: 100%;
		position: relative;
		padding-bottom: 70px;
		overflow-y: auto;
	}

	/* 加载中 */
	.loading-container {
		padding: 60px 0;
		display: flex;
		align-items: center;
		justify-content: center;

		.loading-spinner {
			width: 36px;
			height: 36px;
			border: 3px solid $brand-bg;
			top: 30rpx;
			border-top: 3px solid $brand;
			border-radius: 50%;
			margin-bottom: 15px;
			animation: spin 1s linear infinite;
		}

		.loading-text {
			font-size: 14px;
			color: $text-2;
		}
	}

	/* 错误状态 */
	.error-container {
		padding: 60px 15px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;

		.error-icon {
			width: 56px;
			height: 56px;
			border-radius: 28px;
			background: linear-gradient(135deg, $danger 0%, #ff6b6b 100%);
			color: #fff;
			font-size: 32px;
			font-weight: bold;
			display: flex;
			align-items: center;
			justify-content: center;
			margin-bottom: 18px;
			box-shadow: 0 8rpx 20rpx rgba(255, 59, 48, 0.25);
		}

		.error-text {
			font-size: 14px;
			color: $text-2;
			text-align: center;
			margin-bottom: 22px;
			line-height: 1.6;
		}

		.error-action {
			background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
			border-radius: 22px;
			padding: 10px 26px;
			box-shadow: 0 6rpx 16rpx rgba(46, 134, 222, 0.28);

			.action-text {
				font-size: 14px;
				color: #fff;
				font-weight: 500;
			}
		}
	}

	/* ===== 日期标签栏 ===== */
	.day-tab-container {
		width: 90%;
		height: 80rpx;
		margin: 24rpx auto;
		position: relative;

		.day-scroll {
			width: 100%;
			height: 80rpx;
			white-space: nowrap;
			scrollbar-width: none;

			&::-webkit-scrollbar {
				display: none;
			}
		}

		.day-item {
			display: inline-flex;
			align-items: center;
			justify-content: center;
			height: 60rpx;
			margin-right: 20rpx;
			background-color: #e2e8f0;
			border-radius: 50rpx;
			transition: all 0.25s ease;
			width: 130rpx;
			position: relative;

			&.active {
				background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
				width: auto !important;
				padding: 0 28rpx;
				box-shadow: 0 6rpx 16rpx rgba(46, 134, 222, 0.3);
			}

			.day-text-scroll {
				font-size: 28rpx;
				color: $text-2;
				white-space: nowrap;
				font-weight: 500;
			}

			&.active .day-text-scroll {
				color: #fff;
				font-weight: 600;
			}
		}

		.add-day-btn {
			background: $brand-bg !important;
			color: $brand !important;
			font-weight: bold;
			width: 60rpx !important;
			padding: 0 !important;
			font-size: 36rpx;
		}
	}

	/* ===== 总览卡片 ===== */
	.itinerary-container {
		width: 90%;
		margin: 0 auto;
		padding: 20rpx;
		background-color: transparent;

		.itinerary-card {
			background-color: #fff;
			border-radius: 20rpx;
			padding: 32rpx;
			margin-bottom: 20rpx;
			position: relative;
			box-shadow: 0 6rpx 20rpx rgba(15, 23, 42, 0.06);
			transition: all 0.2s ease;

			&:active {
				transform: scale(0.99);
			}

			.card-title {
				font-size: 38rpx;
				font-weight: 800;
				color: $text-1;
				margin-bottom: 12rpx;
			}

			.card-date {
				font-size: 26rpx;
				color: $brand;
				margin-bottom: 24rpx;
				font-weight: 500;
			}

			.card-places {
				display: flex;
				flex-direction: column;
				gap: 14rpx;

				.place-item {
					font-size: 28rpx;
					color: $text-1;
					line-height: 1.5;
					padding-left: 20rpx;
					position: relative;

					&::before {
						content: "";
						position: absolute;
						left: 0;
						top: 50%;
						transform: translateY(-50%);
						width: 10rpx;
						height: 10rpx;
						border-radius: 50%;
						background: $brand;
					}
				}
			}

			.card-arrow {
				position: absolute;
				right: 30rpx;
				top: 50%;
				transform: translateY(-50%);
				font-size: 36rpx;
				color: $text-3;
				font-weight: 300;
			}
		}
	}

	.page-container {
		width: 90%;
		margin: 20rpx auto 0;
		padding: 0;
	}

	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}

		100% {
			transform: rotate(360deg);
		}
	}

	// 地图样式
	.map-container {
		width: 90%;
		margin: 20rpx auto;
		border-radius: 20rpx;
		overflow: hidden;
		box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.08);
	}

	.trip-map {
		width: 100%;
		height: 420rpx;
	}

	// 空行程总览
	.empty-overview {
		width: 100%;
		padding: 80rpx 0;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.empty-text {
		font-size: 28rpx;
		color: $text-3;
	}

	/* ===== 底部抽屉 ===== */
	.drawer-mask {
		position: fixed;
		top: 0;
		left: 0;
		width: 100vw;
		height: 100vh;
		background: rgba(15, 23, 42, 0.55);
		z-index: 9998;
		transition: opacity 0.3s ease;
		backdrop-filter: blur(4px);
	}

	.spot-drawer {
		position: fixed;
		bottom: 0;
		left: 0;
		width: 100vw;
		max-height: 85vh;
		background: #fff;
		border-radius: 32rpx 32rpx 0 0;
		z-index: 9999;
		transform: translateY(100%);
		transition: transform 0.3s ease;
		box-shadow: 0 -8rpx 32rpx rgba(15, 23, 42, 0.12);
	}

	.drawer-open {
		transform: translateY(0);
	}

	.drawer-header {
		padding: 24rpx 30rpx;
		display: flex;
		align-items: center;
		justify-content: space-between;
		border-bottom: 1rpx solid #f1f5f9;
		position: relative;
	}

	.drawer-bar {
		width: 64rpx;
		height: 8rpx;
		background: #e2e8f0;
		border-radius: 4rpx;
		position: absolute;
		top: 16rpx;
		left: 50%;
		transform: translateX(-50%);
	}

	.drawer-title {
		font-size: 34rpx;
		font-weight: 700;
		color: $text-1;
		margin-top: 20rpx;
	}

	.drawer-close {
		font-size: 28rpx;
		color: $brand;
		margin-top: 20rpx;
		font-weight: 500;
		padding: 6rpx 16rpx;
		background: $brand-bg;
		border-radius: 100rpx;
	}

	.drawer-body {
		padding: 24rpx;
		max-height: 70vh;
	}

	.loading-inner {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 100rpx 0;
		color: $text-2;
		font-size: 28rpx;
	}

	.loading-inner .loading-spinner {
		width: 44rpx;
		height: 44rpx;
		border: 3rpx solid $brand-bg;
		border-top: 3rpx solid $brand;
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin-bottom: 20rpx;
	}

	/* 详情项 */
	.detail-item {
		margin-bottom: 20rpx;
		border-bottom: 1rpx solid #f1f5f9;
		padding: 22rpx 20rpx;

		&:last-child {
			border-bottom: none;
		}
	}

	.label {
		font-size: 28rpx;
		font-weight: 600;
		color: $text-2;
		display: block;
		margin-bottom: 10rpx;
	}

	.value {
		font-size: 28rpx;
		color: $text-1;
		line-height: 1.6;
	}

	.no-result {
		padding: 50rpx 0;
		text-align: center;
		color: $text-2;
		font-size: 26rpx;

		.ai-btn {
			background: $brand-bg;
			color: $brand;
			padding: 22rpx;
			border-radius: 14rpx;
			margin-top: 24rpx;
			font-weight: 600;
			display: inline-block;

			&:active {
				opacity: 0.8;
			}
		}
	}
</style>