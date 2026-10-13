<template>
	<view class="page" :style="popupStyleCom">
		<view class="header">
			<view class="search-box">
				<view class="input-box">
					<input class="input" v-model="searchValue" placeholder="搜索城市" @blur="search" />
				</view>
			</view>
			<view class="hot-city">
				<view class="title">热门城市</view>
				<view class="hot-city-list">
					<view class="hot-city-item" v-for="(item,index) in hotCity" :key="index" @click="hotCityClick(item.code)">
						{{ item.name }}
					</view>
				</view>
			</view>
		</view>
		<uni-city-list :options="list" :showSelect="false" @click="cityClick"></uni-city-list>
	</view>
</template>

<script>
	const db = uniCloud.database();
	const _ = db.command;
	const $ = _.aggregate;
	
	var cache = {};
	
	const hotCityCacheKey = "uni-city-list.hotCity";

	import uniCityList from "../../components/uni-city-list/uni-city-list"
	export default {
		components: {
			uniCityList
		},
		onLoad() {
			this.getCloudData();
			let hotCity = uni.getStorageSync(hotCityCacheKey);
			if (hotCity) {
				this.hotCity = hotCity;
			}
			const eventChannel = this.getOpenerEventChannel();
			// 监听data事件，获取上一页面通过eventChannel.emit传送到当前页面的数据
			if (eventChannel.on) {
				eventChannel.on('data', (data) => {
					this.hotCity = data.hotCity;
					// 需要缓存
					uni.setStorageSync(hotCityCacheKey, data.hotCity);
				});
			}
		},
		data() {
			return {
				searchValue: "",
				where: {},
				list: [],
				hotCity: []
			}
		},
		methods: {
			_select(cityInfo) {
				const eventChannel = this.getOpenerEventChannel();
				if (eventChannel.emit) eventChannel.emit('select', cityInfo);
				uni.navigateBack();
			},
			search() {
				if (this.searchValue) {
					// 只有搜索的时候才可以搜索到县级市（因为县级市太多了，如果一开始就全部显示组件会卡住）
					this.where = {
						name: new RegExp(this.searchValue),
						type: _.in([1,2])
					};
				} else {
					this.where = {};
				}
				this.getCloudData();
			},
			getWhere(){
				let {
					where = {}
				} = this;
				return {
					type: 1,
					...where
				}
			},
			// 获取云端数据
			async getCloudData() {
				let where = this.getWhere();
				if (cache[JSON.stringify(where)]) {
					this.list = cache[JSON.stringify(where)];
				}
				let dbRes = await db.collection("opendb-city-china").aggregate()
					.match(where)
					.group({
						_id: "$first_letter",
						name: $.push("$name"),
						code: $.push("$code")
					})
					.addFields({
						letter: "$_id",
					})
					.sort({
						_id: 1
					})
					.limit(1000)
					.end();
				let rows = dbRes.result.data;
				if (rows && rows.length === 0 && !this.searchValue.trim()) {
					uni.showModal({
						content: "请右键 uniCloud/database 目录，点击【初始化云函数库】（如果有出现其他表名，不要打勾，直接点覆盖选中的表）",
						showCancel: false
					});
				}
				this.list = rows;
				cache[JSON.stringify(where)] = rows;
			},
			cityClick(e) {
				let name = e.item.name;
				let cityInfo = this.getCityInfo({ name });
				this._select(cityInfo);
			},
			hotCityClick(code) {
				let cityInfo = this.getCityInfo({ code });
				this._select(cityInfo);
			},
			getCityInfo(obj = {}) {
				let { code, name } = obj;
				let list = [];
				this.list.forEach((item) => {
					(item.name || []).forEach((n, idx) => {
						list.push({
							name: n,
							code: (item.code || [])[idx]
						});
					});
				});
				let cityInfo = list.find((item) => {
					return (code && item.code == code) || (name && item.name == name);
				});
				return cityInfo;
			},
		},
		computed: {
			popupStyleCom() {
				let systemInfo = uni.getSystemInfoSync();
				let top = systemInfo.safeAreaInsets.top || 0;
				//console.log('systemInfo: ', systemInfo)
				return `height: ${systemInfo.windowHeight - top}px`;
			}
		}
	}
</script>

<style lang="scss" scoped>
	.page {
		box-sizing: border-box;

		.header {
			height: 165px;
			background-color: #f8f8f8;

			.search-box {
				display: flex;
				padding: 10px;
				height: 30px;
				align-items: center;

				.close-box {}

				.input-box {
					flex: 1;

					.input {
						background-color: #ffffff;
						padding: 5px 10px;
						border-radius: 10px;
					}
				}
			}

			.hot-city {
				padding: 10px;
				box-sizing: border-box;

				.title {
					font-weight: bold;
				}

				.hot-city-list {
					display: flex;
					flex-wrap: wrap;
					box-sizing: border-box;
					margin: 0 -5px;
				}

				.hot-city-item {
					border: 1px solid #f8f8f8;
					background-color: #ffffff;
					width: calc(25% - 10px);
					height: 30px;
					margin: 5px;
					display: flex;
					box-sizing: border-box;
					justify-content: center;
					align-items: center;
				}
			}
		}
	}
</style>