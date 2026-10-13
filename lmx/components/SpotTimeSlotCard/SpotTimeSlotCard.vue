<template>
	<view class="time-slot-card">
		<!-- 时间段 -->
		<view class="time-label">
			<text class="time-text">{{ timeSlot.time }}</text>
			<text class="more-icon" @click.stop="handleMoreClick">⋯</text>
		</view>

		<!-- 上半部分：图片 + 基础信息（名称/地址/价格/备注） -->
		<view class="spot-card">
			<!-- <image class="spot-img"
				:src="timeSlot.image ||'https://youimg1.c-ctrip.com/target/100e1600000101s6mC4D4.jpg'"
				mode="aspectFill"></image> -->
			<view class="spot-info">
				<view class="spot-title-row">
					<text class="spot-name">{{ timeSlot.name }}</text>
				</view>
				<text class="spot-address">{{ timeSlot.address }}</text>
				<text class="spot-price" :class="{ free: isFreePrice }">{{ displayPrice }}</text>

				<!-- 备注展示 -->
				<view class="spot-remark" v-if="timeSlot.remark && timeSlot.remark.trim()">
					<text class="remark-label">备注：</text>
					<text class="remark-content">{{ timeSlot.remark }}</text>
				</view>
			</view>
		</view>

		<!-- 下半部分：景区详情（独立区块） -->
		<view class="spot-detail-collapse" @click.stop="isCollapsed = !isCollapsed">
			<view class="collapse-header">
				<text class="collapse-title">景区详情</text>
				<text class="collapse-icon" :class="{ rotated: !isCollapsed }">▲</text>
			</view>
			<view class="collapse-content" v-show="!isCollapsed">
				<view class="detail-item">
					<text class="detail-label">开放时间：</text>
					<text class="detail-value">{{ timeSlot.open_time || '暂无信息' }}</text>
				</view>
				<!--最佳游玩季节 -->
				<view class="detail-item">
					<text class="detail-label">最佳季节：</text>
					<text class="detail-value">{{ timeSlot.best_season || '全年适宜' }}</text>
				</view>
				<view class="detail-item">
					<text class="detail-label">建议游玩：</text>
					<text
						class="detail-value">{{ timeSlot.suggest_duration ? timeSlot.suggest_duration + '分钟' : '暂无信息' }}</text>
				</view>
				<view class="detail-item introduction">
					<text class="detail-label">景区简介：</text>
					<text class="detail-value">{{ timeSlot.introduction || '暂无简介' }}</text>
				</view>
			</view>
		</view>
	</view>
</template>

<script>
	export default {
		name: "SpotTimeSlotCard",
		props: {
			timeSlot: {
				type: Object,
				required: true,
				default: () => ({
					time: "00:00 - 00:00",
					name: "",
					image: "",
					score: "",
					address: "",
					price: "",
					user_price: "",
					remark: "",
					open_time: "",
					suggest_duration: "",
					introduction: "",
					best_season: ""
				})
			}
		},
		data() {
			return {
				isCollapsed: true // 默认折叠
			}
		},
		computed: {
			// 计算：是否为免费（0元/免费）
			isFreePrice() {
				const {
					user_price,
					price
				} = this.timeSlot;

				// 优先级：用户修改的价格 > 原始价格
				if (user_price !== undefined && user_price !== null) {
					return Number(user_price) <= 0;
				}
				// 原始价格为"免费"
				if (price === "免费") {
					return true;
				}
				// 原始价格提取数字后<=0
				const purePrice = String(price || '0').replace(/[^\d.]/g, '');
				return Number(purePrice) <= 0;
			},
			// 计算：显示的价格文本
			displayPrice() {
				const {
					user_price,
					price
				} = this.timeSlot;

				// 优先级：用户修改的价格 > 原始价格
				if (user_price !== undefined && user_price !== null) {
					const num = Number(user_price);
					return num <= 0 ? "免费" : `${num.toFixed(2)}`;
				}
				// 原始价格
				return price || "免费";
			}
		},
		methods: {
			handleMoreClick() {
				this.$emit('more-action', this.timeSlot);
			}
		}
	};
</script>

<style lang="scss" scoped>
	/* ===== 设计令牌 ===== */
	$brand: #2E86DE;
	$brand-bg: #eef4fb;
	$text-1: #1e293b;
	$text-2: #64748b;
	$text-3: #94a3b8;
	$border: #e2e8f0;
	$success: #07c160;
	$danger: #ff3b30;

	.time-slot-card {
		background-color: #fff;
		border-radius: 24rpx;
		padding: 26rpx;
		margin-bottom: 20rpx;
		box-shadow: 0 8rpx 28rpx rgba(46, 134, 222, 0.08);
	}

	.time-label {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 20rpx;
	}

	.time-text {
		font-size: 26rpx;
		color: #fff;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		padding: 6rpx 18rpx;
		border-radius: 100rpx;
		font-weight: 500;
	}

	.more-icon {
		font-size: 32rpx;
		color: $text-3;
		padding: 10rpx 16rpx;
		border-radius: 50%;

		&:active {
			background-color: #f1f5f9;
			color: $brand;
		}
	}

	/* 上半部分：横向布局 */
	.spot-card {
		display: flex;
		align-items: flex-start;
		gap: 20rpx;
		margin-bottom: 20rpx;
	}

	.spot-img {
		width: 160rpx;
		height: 160rpx;
		border-radius: 14rpx;
		object-fit: cover;
	}

	.spot-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 12rpx;
	}

	.spot-title-row {
		display: flex;
		align-items: center;
	}

	.spot-name {
		font-size: 36rpx;
		font-weight: 700;
		color: $text-1;
	}

	.spot-address {
		font-size: 24rpx;
		color: $text-2;
		line-height: 1.4;
	}

	.spot-price {
		font-size: 28rpx;
		color: $danger;
		font-weight: bold;
		align-self: flex-end;

		&.free {
			color: $success;
		}
	}

	/* 备注样式 */
	.spot-remark {
		margin-top: 8rpx;
		padding: 12rpx 18rpx;
		background-color: $brand-bg;
		border-radius: 12rpx;
		border-left: 6rpx solid $brand;
	}

	.remark-label {
		font-size: 24rpx;
		color: $brand;
		font-weight: 600;
	}

	.remark-content {
		font-size: 24rpx;
		color: $text-1;
		margin-left: 8rpx;
		line-height: 1.5;
	}

	/* 下半部分：景区详情 */
	.spot-detail-collapse {
		padding-top: 22rpx;
		border-top: 1rpx solid #f1f5f9;
	}

	.collapse-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 8rpx 0;
	}

	.collapse-title {
		font-size: 28rpx;
		color: $text-1;
		font-weight: 600;
		position: relative;
		padding-left: 16rpx;

		&::before {
			content: "";
			position: absolute;
			left: 0;
			top: 50%;
			transform: translateY(-50%);
			width: 6rpx;
			height: 22rpx;
			background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
			border-radius: 3rpx;
		}
	}

	.collapse-icon {
		font-size: 22rpx;
		color: $text-3;
		transition: transform 0.3s ease;
	}

	.collapse-icon.rotated {
		transform: rotate(180deg);
	}

	.collapse-content {
		margin-top: 16rpx;
		padding: 18rpx;
		background-color: #f8fafc;
		border-radius: 12rpx;
		border-left: 6rpx solid $brand;
	}

	.detail-item {
		margin-bottom: 12rpx;
		font-size: 26rpx;
		line-height: 1.5;
	}

	.detail-item:last-child {
		margin-bottom: 0;
	}

	.detail-label {
		color: $text-2;
		font-weight: 500;
	}

	.detail-value {
		color: $text-1;
	}

	.detail-item.introduction .detail-value {
		color: $text-2;
		line-height: 1.6;
	}
</style>