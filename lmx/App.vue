<script>
	import {
		getToken
	} from '@/utils/auth' // 导入getToken函数

	export default {
		globalData: {
			statusBarHeight: 20,
			userInfo: null
		},
		onLaunch: function() {
			console.log('App Launch')

			// 检查用户是否已登录
			this.checkLoginStatus()

			// 设置状态栏高度CSS变量
			this.setStatusBarHeight()
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		},
		methods: {
			checkLoginStatus() {
				try {
					// 获取本地存储的token
					const token = getToken()
					// 如果没有token，则认为未登录，跳转到登录页面
					if (!token) {
						console.log('未找到用户token，跳转到登录页面')
						uni.redirectTo({
							url: '/pages/login/login'
						})
					} else {
						console.log('检测到用户token，无需跳转')
					}
				} catch (e) {
					console.error('检查登录状态失败:', e)
					// 异常情况下也跳转到登录页
					uni.redirectTo({
						url: '/pages/login/login'
					})
				}
			},

			setStatusBarHeight() {
				// 动态获取状态栏高度
				try {
					const res = uni.getSystemInfoSync();
					const statusBarHeight = res.statusBarHeight || 20;

					// 区分不同平台处理
					// #ifdef H5
					if (document && document.documentElement) {
						document.documentElement.style.setProperty('--status-bar-height', `${statusBarHeight}px`);
					}
					// #endif

					// 设置到全局变量，供其他地方使用
					// getApp().globalData = getApp().globalData || {};
					// getApp().globalData.statusBarHeight = statusBarHeight;

				} catch (e) {
					console.error('获取状态栏高度失败:', e);

					// #ifdef H5
					if (document && document.documentElement) {
						document.documentElement.style.setProperty('--status-bar-height', '20px');
					}
					// #endif

					// 设置默认状态栏高度到全局变量
					getApp().globalData = getApp().globalData || {};
					getApp().globalData.statusBarHeight = 20;
				}
			},
		},
	}
</script>

<style>
	/* 引入本地Font Awesome字体文件 */
	@font-face {
		font-family: 'Font Awesome 5 Free';
		font-style: normal;
		font-weight: 900;
		font-display: auto;
		src: url('/static/fonts/font-awesome/fa-solid-900.woff2') format('woff2'),
			url('/static/fonts/font-awesome/fa-solid-900.woff') format('woff'),
			url('/static/fonts/font-awesome/fa-solid-900.ttf') format('truetype');
	}

	/* 引入Font Awesome品牌图标字体文件 */
	@font-face {
		font-family: 'Font Awesome 5 Brands';
		font-style: normal;
		font-weight: 400;
		font-display: auto;
		src: url('/static/fonts/font-awesome/fa-brands-400.woff2') format('woff2'),
			url('/static/fonts/font-awesome/fa-brands-400.woff') format('woff'),
			url('/static/fonts/font-awesome/fa-brands-400.ttf') format('truetype');
	}

	/* 全局变量 */
	:root {
		--status-bar-height: 0px;

		/* ===== 品牌主色 ===== */
		--brand-primary: #2E86DE;
		--brand-primary-dark: #1B6EC2;
		--brand-primary-light: #74B9FF;
		--brand-primary-bg: #eef4fb;
		--brand-gradient: linear-gradient(135deg, #2E86DE 0%, #54A0FF 100%);
		--brand-gradient-deep: linear-gradient(135deg, #1B6EC2 0%, #2E86DE 100%);

		/* ===== 辅助色 ===== */
		--accent-coral: #ff6b6b;
		--accent-orange: #ff9f43;
		--accent-yellow: #feca57;
		--accent-blue: #5BC0DE;
		--color-success: #07c160;
		--color-danger: #ff3b30;

		/* ===== 中性色 ===== */
		--bg-page: #f4f7fb;
		--bg-card: #ffffff;
		--bg-muted: #f8fafc;
		--text-primary: #1e293b;
		--text-secondary: #64748b;
		--text-tertiary: #94a3b8;
		--border-color: #e2e8f0;
		--border-light: #f1f5f9;

		/* ===== 阴影 ===== */
		--shadow-sm: 0 2rpx 8rpx rgba(15, 23, 42, 0.04);
		--shadow-md: 0 8rpx 24rpx rgba(15, 23, 42, 0.06);
		--shadow-lg: 0 16rpx 40rpx rgba(15, 23, 42, 0.10);
		--shadow-brand: 0 12rpx 28rpx rgba(46, 134, 222, 0.28);

		/* ===== 圆角 ===== */
		--radius-sm: 8rpx;
		--radius-md: 16rpx;
		--radius-lg: 24rpx;
		--radius-xl: 32rpx;
		--radius-pill: 999rpx;
	}

	/* 安全区域适配 */
	page {
		padding-bottom: constant(safe-area-inset-bottom);
		padding-bottom: env(safe-area-inset-bottom);
		background-color: var(--bg-page);
		color: var(--text-primary);
		font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', 'Segoe UI', sans-serif;
	}

	/* 定义常用Font Awesome图标 */
	.fas {
		font-family: 'Font Awesome 5 Free';
		font-weight: 900;
		-moz-osx-font-smoothing: grayscale;
		-webkit-font-smoothing: antialiased;
		display: inline-block;
		font-style: normal;
		font-variant: normal;
		text-rendering: auto;
		line-height: 1;
	}

	/* 定义Font Awesome品牌图标 */
	.fab {
		font-family: 'Font Awesome 5 Brands';
		font-weight: 400;
		-moz-osx-font-smoothing: grayscale;
		-webkit-font-smoothing: antialiased;
		display: inline-block;
		font-style: normal;
		font-variant: normal;
		text-rendering: auto;
		line-height: 1;
	}

	/* 定义常用图标的Unicode值 */
	.fa-search:before {
		content: "\f002";
	}

	.fa-camera:before {
		content: "\f030";
	}

	.fa-microphone:before {
		content: "\f130";
	}

	.fa-robot:before {
		content: "\f544";
	}

	.fa-language:before {
		content: "\f1ab";
	}

	.fa-credit-card:before {
		content: "\f09d";
	}

	.fa-bell:before {
		content: "\f0f3";
	}

	.fa-exchange-alt:before {
		content: "\f362";
	}

	.fa-phone-alt:before {
		content: "\f879";
	}

	/* 天气相关图标 */
	.fa-cloud-sun:before {
		content: "\f6c4";
	}

	.fa-sun:before {
		content: "\f185";
	}

	.fa-cloud:before {
		content: "\f0c2";
	}

	.fa-cloud-rain:before {
		content: "\f73d";
	}

	.fa-cloud-showers-heavy:before {
		content: "\f740";
	}

	.fa-bolt:before {
		content: "\f0e7";
	}

	.fa-snowflake:before {
		content: "\f2dc";
	}

	.fa-smog:before {
		content: "\f75f";
	}

	.fa-temperature-low:before {
		content: "\f76b";
	}

	.fa-temperature-high:before {
		content: "\f769";
	}

	.fa-wind:before {
		content: "\f72e";
	}

	.fa-tshirt:before {
		content: "\f553";
	}

	.fa-car:before {
		content: "\f1b9";
	}

	.fa-plane:before {
		content: "\f072";
	}

	.fa-virus:before {
		content: "\e074";
	}

	.fa-running:before {
		content: "\f70c";
	}

	/* 生活指数相关图标 */
	.fa-umbrella:before {
		content: "\f0e9";
	}

	.fa-smile:before {
		content: "\f118";
	}

	.fa-seedling:before {
		content: "\f4d8";
	}

	.fa-fish:before {
		content: "\f578";
	}

	.fa-bug:before {
		content: "\f188";
	}

	.fa-car-side:before {
		content: "\f5e4";
	}

	.fa-glasses:before {
		content: "\f530";
	}

	.fa-beer:before {
		content: "\f0fc";
	}

	.fa-shield-alt:before {
		content: "\f3ed";
	}

	.fa-heartbeat:before {
		content: "\f21e";
	}

	.fa-briefcase-medical:before {
		content: "\f469";
	}

	.fa-suitcase:before {
		content: "\f0f2";
	}

	.fa-thermometer-half:before {
		content: "\f2c9";
	}

	.fa-tint:before {
		content: "\f043";
	}

	.fa-compress-arrows-alt:before {
		content: "\f78c";
	}

	.fa-calendar-alt:before {
		content: "\f073";
	}

	.fa-clock:before {
		content: "\f017";
	}

	.fa-chart-line:before {
		content: "\f201";
	}

	.fa-map-marked-alt:before {
		content: "\f5a0";
	}

	.fa-comments:before {
		content: "\f086";
	}

	.fa-volume-up:before {
		content: "\f028";
	}

	.fa-paper-plane:before {
		content: "\f1d8";
	}

	.fa-chevron-left:before {
		content: "\f053";
	}

	.fa-times:before {
		content: "\f00d";
	}

	.fa-copy:before {
		content: "\f0c5";
	}

	.fa-share-alt:before {
		content: "\f1e0";
	}

	.fa-heart:before {
		content: "\f004";
	}

	.fa-caret-down:before {
		content: "\f0d7";
	}

	.fa-check:before {
		content: "\f00c";
	}

	.fa-lightbulb:before {
		content: "\f0eb";
	}

	.fa-sync-alt:before {
		content: "\f2f1";
	}

	.fa-chevron-down:before {
		content: "\f078";
	}

	.fa-trash-alt:before {
		content: "\f2ed";
	}

	.fa-arrow-right:before {
		content: "\f061";
	}

	.fa-plus-circle:before {
		content: "\f055";
	}

	.fa-bold:before {
		content: "\f032";
	}

	.fa-italic:before {
		content: "\f033";
	}

	.fa-underline:before {
		content: "\f0cd";
	}

	.fa-image:before {
		content: "\f03e";
	}

	/* 品牌图标Unicode值 */
	.fa-weixin:before {
		content: "\f1d7";
	}

	.fa-alipay:before {
		content: "\f642";
	}

	/* 货币图标 */
	.fa-cny:before,
	.fa-rmb:before,
	.fa-yen:before,
	.fa-jpy:before {
		content: "\f157";
	}

	.fa-dollar:before,
	.fa-usd:before {
		content: "\f155";
	}

	.fa-eur:before,
	.fa-euro:before {
		content: "\f153";
	}

	.fa-gbp:before {
		content: "\f154";
	}

	.fa-krw:before,
	.fa-won:before {
		content: "\f159";
	}

	.fa-btc:before,
	.fa-bitcoin:before {
		content: "\f15a";
	}

	.fa-rub:before,
	.fa-rouble:before,
	.fa-ruble:before {
		content: "\f158";
	}

	.fa-inr:before,
	.fa-rupee:before {
		content: "\f156";
	}

	.fa-try:before,
	.fa-turkish-lira:before {
		content: "\f195";
	}

	.fa-money:before {
		content: "\f0d6";
	}

	/* 添加更多货币图标 */
	.fa-thb:before,
	.fa-baht:before {
		content: "\f549";
	}

	/* 泰铢 */
	.fa-sgd:before {
		content: "\f155";
	}

	/* 新加坡元，临时使用美元符号 */
	.fa-aud:before {
		content: "\f155";
	}

	/* 澳元，临时使用美元符号 */
	.fa-cad:before {
		content: "\f155";
	}

	/* 加元，临时使用美元符号 */
	.fa-hkd:before {
		content: "\f155";
	}

	/* 港币，临时使用美元符号 */
	.fa-myr:before {
		content: "\f4b9";
	}

	/* 马来西亚林吉特，使用替代符号 */
	.fa-currency-dollar:before {
		content: "\f155";
	}

	/* 通用美元类符号 */
	.fa-shekel:before,
	.fa-shekel-sign:before,
	.fa-ils:before {
		content: "\f20b";
	}

	/* 以色列谢克尔 */
	.fa-tenge:before {
		content: "\f7d7";
	}

	/* 哈萨克斯坦坚戈 */
	.fa-hryvnia:before {
		content: "\f6f2";
	}

	/* 乌克兰格里夫纳 */
	.fa-peso:before {
		content: "\f154";
	}

	/* 墨西哥比索，临时使用英镑符号 */
	.fa-brazil:before,
	.fa-brl:before {
		content: "\f155";
	}

	/* 巴西雷亚尔，临时使用美元符号 */

	/* 地图和位置图标 */
	.fa-map-marker-alt:before {
		content: "\f3c5";
	}

	/* 紧急联系图标 */
	.fa-ambulance:before {
		content: "\f0f9";
	}

	.fa-fire-extinguisher:before {
		content: "\f134";
	}

	.fa-car-crash:before {
		content: "\f5e1";
	}

	.fa-umbrella-beach:before {
		content: "\f5ca";
	}

	/* 提示和信息图标 */
	.fa-exclamation-triangle:before {
		content: "\f071";
	}

	.fa-info-circle:before {
		content: "\f05a";
	}

	/* 其他实用图标 */
	.fa-hand-sparkles:before {
		content: "\e05d";
	}

	/* 国旗图标 */
	.fa-flag-usa:before {
		content: "\f74d";
	}

	.fa-flag:before {
		content: "\f024";
	}

	.fa-flag-checkered:before {
		content: "\f11e";
	}

	.fa-flag-uk:before,
	.fa-flag-gb:before {
		content: "\f7a2";
	}

	.fa-flag-jp:before,
	.fa-flag-japan:before {
		content: "\f7a4";
	}

	.container {
		padding: 16px;
	}

	button {
		margin-bottom: 15px;
	}

	/* 全局滚动条隐藏（移动端体验） */
	::-webkit-scrollbar {
		width: 0;
		height: 0;
		display: none;
	}
</style>