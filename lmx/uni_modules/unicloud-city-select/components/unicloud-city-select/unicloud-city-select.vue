<template>
	<view></view>
</template>

<script>
	const uniMapCo = uniCloud.importObject('uni-map-co', {
		customUI: true
	});
	const db = uniCloud.database();
	const _ = db.command;
	const $ = _.aggregate;
	/**
	 * unicloud-city-select
	 * @description 云端一体城市选择组件
	 * @property {Boolean} location = [true|false] 是否自动获取定位所在的城市
	 * @property {Array} hotCity 热门城市列表
	 * @event {Function} mounted 组件加载完成触发（此时不一定有数据）
	 * @event {Function} select 选择城市后触发（若设置location="true"则会在定位成功后触发一次select事件）
	 */
	export default {
		name: "unicloud-city-select",
		emits: ["mounted", "select"],
		props: {
			// 热门城市列表
			hotCity: {
				type: Array,
				default: function() {
					return []
				}
			},
			// 是否自动获取定位所在的城市
			location: {
				type: Boolean,
				default: true
			}
		},
		data() {
			return {

			};
		},
		mounted() {
			let { location } = this;
			if (location) this.getLocation();
			this.$emit("mounted");
		},
		methods: {
			// 打开选择页面
			open() {
				uni.navigateTo({
					url: `/uni_modules/unicloud-city-select/pages/uni-city-list/uni-city-list`,
					events: {
						select: (data) => {
							this.$emit("select", data)
						}
					},
					success: (res) => {
						// 通过eventChannel向被打开页面传送数据
						res.eventChannel.emit('data', {
							hotCity: this.hotCity
						})
					}
				})
			},
			// 获取定位所在城市
			getLocation() {
				uni.getLocation({
					type: 'gcj02',
					success: async (res) => {
						let location2addressRes = await uniMapCo.location2address({
							location: `${res.latitude},${res.longitude}`
						});
						this.city = {
							code: parseInt(Number(location2addressRes.result.result.adcode)/100)*100+"",
							name: location2addressRes.result.result.city,
						}
						this.$emit("select", this.city)
					}
				});
			},
		},
		watch: {

		},
		computed: {

		}
	}
</script>

<style lang="scss" scoped>

</style>