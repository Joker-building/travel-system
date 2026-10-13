<template>
	<view>
		<view class="add-Place">
			<view class="add-Place-content">


				<!-- 多城市 -->
				<swiper class="swiper" :indicator-dots="true" :autoplay="false" :duration="800"
					indicator-active-color="green" v-if="TravelData.city.length>=2">
					<swiper-item v-for="(city,cityIndex) in TravelData.city.length" :key="cityIndex">
						<view class="swiper-item">
							<view class="title-content">
								<text class="title">{{TravelData.city[cityIndex]}}</text>
								<text class="title">第{{cityIndex+1}}个城市</text>
							</view>
							<uni-collapse>
								<uni-collapse-item :title="this.TravelDays[cityIndex][dayIndex]"
									v-for="(day,dayIndex) in TravelData.days[cityIndex].length" :key="dayIndex">
									<view style="padding: 20rpx;">
										<input type="text" class="add-Place-input" placeholder="可填写多个游玩地点，不填则为空"
											v-model="TravelPlace[cityIndex][dayIndex]">
									</view>
								</uni-collapse-item>
							</uni-collapse>
						</view>
					</swiper-item>
				</swiper>

				<!-- 单城市 -->
				<view class="add-Place-one" v-else>
					<view class="title-content">
						<text class="title">{{TravelData.city[0]}}</text>
					</view>
					<view class="add-place-content">
						<!-- 基本折叠面板 -->
						<uni-collapse>
							<uni-collapse-item :title="this.TravelDays[dayIndex]"
								v-for="(day,dayIndex) in TravelData.days.length" :key="dayIndex">
								<!-- :open="true" 默认展开 -->
								<view style="padding: 20rpx;">
									<input type="text" class="add-Place-input" placeholder="可填写多个游玩地点，不填则为空"
										v-model="TravelPlace[dayIndex]">
								</view>
							</uni-collapse-item>
							<!-- <uni-collapse-item title="标题2">
								<view style="padding: 20rpx;">这里是折叠内容2</view>
							</uni-collapse-item> -->
						</uni-collapse>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>


<script>
	export default {
		name: "TravelItinerary",
		props: {
			TravelData: {
				type: Object
			},
			ChildSent: {
				type: Boolean,
				default: false
			}
		},
		data() {
			return {
				days: [], //天数
				TravelDays: [], //渲染天数日期用
				TravelPlace: [] //游玩地点
			};
		},
		mounted() {
			this.getTrueDays()
			this.getInput()
		},
		watch: {
			ChildSent(newValue) {
				if (newValue) {
					this.sentMsg()
				}
			}
		},
		methods: {
			// 子传父
			sentMsg() {
				const data = {
					input: this.TravelPlace
				}
				this.$nextTick(() => {
					console.log("子传父,数据是：", data)
					this.$emit('getTravelPlace', data)
				})
			},
			// 获得表单的数组
			getInput() {
				this.TravelPlace = []
				if (this.TravelData.city.length === 1) {
					for (let a = 0; a < this.TravelData.days.length; a++) {
						this.TravelPlace.push('')
					}
				} else {
					for (let i = 0; i < this.TravelData.city.length; i++) {
						this.TravelPlace.push([])
						for (let j = 0; j < this.TravelData.days[i].length; j++) {
							this.TravelPlace[i].push('')
						}
					}
				}
			},

			// 渲染天数日期用

			// 获得天数和日期
			getTrueDays() {
				let arr = []
				if (this.TravelData.city.length === 1) {
					for (let i = 0; i < this.TravelData.days.length; i++) {
						arr.push(this.TravelData.days[i] + ' ' + this.TravelData.calendar[i])
					}
				} else {
					for (let a = 0; a < this.TravelData.days.length; a++) {
						arr.push([])

						for (let b = 0; b < this.TravelData.days[a].length; b++) {
							arr[a].push(this.TravelData.days[a][b] + ' ' + this.TravelData.calendar[a][b])
						}
					}
				}
				console.log('拼起来的数组是', arr)
				this.TravelDays = arr
				return arr
			},
		},
	}
</script>

<style>
	/* 地点输入框 */
	.add-Place-input {}

	/* 旅游的城市标题 */
	.title-content {
		text-align: center;
		font-size: 20px;
		font-weight: bold;
		color: #00cb9c;
		display: flex;
		justify-content: space-around;
	}

	/* 滑块内容 */
	.swiper {
		height: 100%;
	}

	/* 添加具体地点内容 */
	.add-Place-content {
		height: 80vh;
		padding: 15px;
	}
</style>