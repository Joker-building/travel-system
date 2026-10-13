<template>
	<view>
		<view class="add-TravelCity">
			<text class="form-label">旅行城市</text>
			<view class="form-item" v-if="isShowBtn">
				<button class="add-TravelCity-button" @click="handleAddCity">点击添加旅行城市</button>
			</view>
			<view class="add-TravelCity-Content" v-else>
				<view class="card-Value" v-for="(City,CityIndex) in TravelCity">
					<view class="card-time">
						<view class="card-title-content">
							<text class="card-title-left">旅行日期:</text>
							<text class="card-title-right">第{{CityIndex+1}}个城市</text>
						</view>

						<view class="card-time-content">
							<picker class="form-picker" mode="date" @change="getDateStart($event,CityIndex)">
								<view>{{TravelTime[CityIndex].Start||"起始日期"}}</view>
							</picker>
							→
							<picker class="form-picker" :start="TravelTime[CityIndex].Start" mode="date"
								@change="getDateEnd($event,CityIndex)">
								<view>{{TravelTime[CityIndex].End||"结束日期"}}</view>
							</picker>
						</view>
						<text class="card-title-left">旅行城市:</text>
						<view class="card-city">
							<input v-model="TravelCity[CityIndex]" class="card-input" type="text" placeholder="请输入旅行城市">
						</view>
						<view class="card-button">
							<button class="card-del-button" @click="delCity(CityIndex)">删除城市</button>
							<button class="card-add-button" @click="addCity">添加城市</button>
						</view>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
	export default {
		name: "TravelCity-value",
		props: {
			sent: {
				type: Boolean,
				default: false
			},
		},
		watch: {
			sent(newValue) {
				if (newValue) {
					this.sentMsg()
				}
			}
		},
		data() {
			return {
				isShowBtn: true,
				TravelTime: [], //行程日期
				TravelCity: [], //行程城市
				TravelPlaces: [], //游玩地点
				TravelDays: [], //行程天数
			};
		},
		methods: {
			// 子传父
			sentMsg() {
				const data = {
					time: this.TravelTime,
					days: this.TravelDays,
					city: this.TravelCity,
					isShowBtn: this.isShowBtn
				}
				this.$nextTick(() => {
					console.log("子传父")
					this.$emit('getTravelData', data)
				})
			},

			handleAddCity() {
				console.log('你好')
				this.isShowBtn = false
				this.TravelCity.push('')
				this.TravelTime.push({
					Start: '',
					End: ''
				})
				this.TravelDays.push('')
			},
			// 添加城市
			addCity() {
				this.handleAddCity()
			},

			// 删除城市
			delCity(Index) {

				this.TravelCity.splice(Index, 1)
				this.TravelTime.splice(Index, 1)
				this.TravelDays.splice(Index, 1)
				if (this.TravelCity.length === 0) {
					this.isShowBtn = true
				}
			},

			// 处理日期选择
			getDateStart(e, Index) {
				console.log(e)
				console.log(Index)
				this.TravelTime[Index].Start = e.detail.value
			},
			getDateEnd(e, Index) {
				if (!this.TravelTime[Index].Start) {
					uni.showToast({
						title: '未输入起始日期',
						icon: 'error'
					})
					return
				}
				console.log(e)
				console.log(Index)
				this.TravelTime[Index].End = e.detail.value
				const d1 = new Date(this.TravelTime[Index].Start);
				const d2 = new Date(this.TravelTime[Index].End);
				const timeDiff = Math.abs(d2 - d1) + 1;
				const time = Math.ceil(timeDiff / (1000 * 60 * 60 * 24))
				console.log('时间间隔是', time)
				// 有多少天
				this.TravelDays[Index] = time
			},
		}
	}
</script>

<style scoped>
	/* 添加按钮 和删除按钮*/
	.card-add-button,
	.card-del-button {
		color: white;
		background-color: #00cb9c;
		font-size: 14px;
		width: 34%;
		letter-spacing: 3px;
		font-weight: bold;
	}

	.card-del-button {
		background-color: #ccc;
	}

	/* 按钮盒子 */
	.card-button {
		display: flex;
		justify-content: space-around;
	}

	/* 输入框 */
	.card-input {
		width: 80%;
		height: 20px;
		font-size: 20px;
		border: 1px solid #ccc;
		border-radius: 5px;
		color: #00cb9c;
		text-align: center;
	}

	/* 日期选择框 */
	.form-picker {
		width: 30%;
		border: 1px solid #ccc;
		display: inline-block;
		padding: 0 5px;
		border-radius: 5px;
		font-size: 14px;
		color: #00cb9c;
		text-align: center;
	}

	/* 时间两个输入框盒子 */
	.card-city,
	.card-time-content {
		margin: 10px auto;
		display: flex;
		justify-content: space-around;
	}

	/* 卡片标题 */
	.card-title-left,
	.card-title-right {
		color: #6a67cb;
		font-weight: bold;
		/* margin-left: 10px; */
	}

	/* 添加城市的内容 */
	.add-TravelCity-Content {
		/* border: 1px solid #ccc; */
		/* height: 100px; */
		border-radius: 8px;
		padding: 10px;
	}

	/* 左日期 */
	.card-title-left {
		margin-left: 15px;
	}

	.card-title-right {
		margin-right: 20px;
	}

	/* 日期时间盒子 */
	.card-title-content {
		display: flex;
		justify-content: space-between;
	}

	/* 卡片 */
	.card-Value {
		border: 1px solid #00cb9c;
		margin-top: 10px;
		border-radius: 8px;
	}

	.card-Value:first-child {
		margin-top: -2px;
	}

	.add-TravelCity-button {
		width: 100%;
		color: #00cb9c;
		background-color: rgba(214, 214, 214, 0.1);
		border: 1px solid #ccc;
	}

	/* .form-item {
		border-radius: 8px;
		border: 1px solid #ccc;
	} */


	.form-label {
		display: block;
		margin-top: 10px;
		margin-bottom: 5px;
		font-size: 20px;
		color: #00cb9c;
		font-weight: bold;
	}

	.form-label::after {
		content: ':';
	}
</style>