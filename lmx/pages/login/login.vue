<template>
	<view class="login-container">
		<!-- 左侧宣传区域 -->
		<view class="promo-section">
			<text class="promo-title">AI 定制</text>
			<text class="promo-subtitle">专属你的旅行方案</text>
			<text class="promo-text">AI Customization, Your Exclusive Travel Plan</text>
		</view>

		<!-- 右侧表单区域 -->
		<view class="login-section">
			<view class="login-box">
				<!-- 表单切换标签 -->
				<view class="form-tabs">
					<view class="tab-item" :class="{ 'active': activeForm === 'login' }" @click="switchForm('login')">
						<text>登录</text>
					</view>
					<view class="tab-item" :class="{ 'active': activeForm === 'register' }"
						@click="switchForm('register')">
						<text>注册</text>
					</view>
				</view>

				<!-- 登录表单 -->
				<view v-if="activeForm === 'login'">
					<text class="login-title">登录系统</text>
					<text class="login-subtitle">System Login</text>

					<view class="input-group">
						<input type="text" v-model="loginForm.username" maxlength="16"
							:placeholder="$t('login.username')" class="login-input" />
						<input :type="showPassword ? 'text' : 'password'" v-model="loginForm.password" maxlength="16"
							:placeholder="$t('login.password')" class="login-input" />

						<button class="login-button" @click="handleLogin">{{$t('login.submit')}}</button>
					</view>
				</view>

				<!-- 注册表单 -->
				<view v-if="activeForm === 'register'">
					<text class="login-title">用户注册</text>
					<text class="login-subtitle">User Registration</text>

					<view class="input-group">
						<input type="text" v-model="registerForm.username" placeholder="用户名" class="login-input"
							maxlength="16" />
						<input :type="showPassword ? 'text' : 'password'" v-model="registerForm.password"
							placeholder="密码" class="login-input" maxlength="16" />
						<span class="isSame" v-if="isSame"></span>
						<input :type="showPassword ? 'text' : 'password'" v-model="Secondpassword"
							placeholder="再次输入上述密码" class="login-input" maxlength="16" />
						<input type="text" v-model="registerForm.nickName" placeholder="昵称" class="login-input">

						<!-- 常住城市（手动三级联动选择器） -->
						<view class="input-item input-select">
							<picker mode="multiSelector" :value="cityIndex" :range="cityArray" @change="onCityChange"
								@columnchange="onCityColumnChange">
								<view class="login-input picker-text">
									常住城市：{{ registerForm.city || '请选择城市' }}
								</view>
							</picker>
						</view>
						<!-- <input type="email" v-model="registerForm.email" placeholder="邮箱" class="login-input" /> -->

						<!-- <input type="text" v-model="registerForm.firstName" placeholder="名" class="login-input" />
						<input type="text" v-model="registerForm.lastName" placeholder="姓" class="login-input" /> -->

						<!-- 语言选择 -->
						<!-- <view class="select-container">
							<picker @change="onLanguageChange" :value="languageIndex" :range="languageOptions">
								<view class="picker-view">
									<text>偏好语言: {{languageOptions[languageIndex]}}</text>
								</view>
							</picker>
						</view> -->

						<!-- 性别选择 -->
						<view class="select-container">
							<picker @change="onGenderChange" :value="genderIndex" :range="genderOptions">
								<view class="picker-view">
									<text>性别: {{genderOptions[genderIndex]}}</text>
								</view>
							</picker>
						</view>

						<button class="login-button" @click="handleRegister">注册</button>
					</view>
				</view>

			</view>
		</view>
	</view>
</template>

<script>
	import {
		login,
		register
	} from '@/api/login'
	import {
		saveLoginState,
		getToken,
		getUserInfo
	}
	from '@/utils/auth'

	export default {
		data() {
			return {
				activeForm: 'login', // 当前活动表单：login 或 register
				Secondpassword: '',
				isSame: false,
				// 登录表单数据
				loginForm: {
					username: '',
					password: ''
				},

				// 注册表单数据
				registerForm: {
					username: '',
					password: '',
					email: '',
					// firstName: '',
					// lastName: '',
					nickName: '', //姓名
					city: '',
					gender: 'male',
					//占位 城市！！！！！！


					// preferredLanguage: 'zh', // 默认中文
					// gender: 'male' // 默认男性，使用字符串而非数字
				},
				// 三级联动 省市区
				cityIndex: [0, 0],
				provinceList: [], // 所有省份
				cityList: [], // 对应城市
				cityArray: [], // 选择器显示

				// 语言和性别选择器配置
				languageOptions: ['中文', '英文'],
				languageIndex: 0,
				languageValues: ['zh', 'en'],

				genderOptions: ['男', '女'],
				genderIndex: 0,
				genderValues: ['male', 'female', 'other'], // 使用字符串表示性别，而非数字

				currentLanguage: 'zh',
				showPassword: false,
				isLandscape: false
			}
		},
		watch: {
			// 二次验证密码
			Secondpassword: {
				handler(newValue) {
					clearTimeout(this.timer)
					this.timer = setTimeout(() => {
						console.log('值改变了！', newValue)
						if (this.registerForm.password !== this.Secondpassword) {
							console.log('密码不相同！')
							this.isSame = true
						} else {
							console.log('密码相同')
							this.isSame = false
							return
						}
					}, 300)
				}
			}
		},
		methods: {
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

			// 更新选择器内容
			updateCityArray() {
				this.cityArray = [
					this.provinceList.map(item => item.name),
					this.cityList
				];
			},

			// 切换省，联动市
			onCityColumnChange(e) {
				const col = e.detail.column;
				const val = e.detail.value;

				if (col === 0) {
					this.cityIndex[0] = val;
					this.cityIndex[1] = 0;
					this.cityList = this.provinceList[val].cities;
					this.updateCityArray();
				}
			},

			// 选择完成，赋值到表单
			onCityChange(e) {
				const index = e.detail.value;
				const p = this.provinceList[index[0]].name;
				const c = this.cityList[index[1]];
				this.registerForm.city = p + " " + c;
			},
			// 切换登录/注册表单
			switchForm(form) {
				this.activeForm = form;
			},

			// 处理登录
			handleLogin() {
				if (!this.loginForm.username || !this.loginForm.password) {
					uni.showToast({
						title: this.$t('login.inputRequired'),
						icon: 'none'
					});
					return;
				}

				uni.showLoading({
					title: this.$t('login.loggingIn'),
					mask: true
				});

				// 使用API登录
				login({
					username: this.loginForm.username,
					password: this.loginForm.password
				}).then(async res => {
					// 登录成功
					uni.hideLoading();

					console.log('登录成功后端给的数据是：!!!', res)
					// 检查HTTP状态码和业务状态码
					if (res.statusCode === 200) {
						// 获取响应数据
						const responseData = res.data;

						if (responseData.code === 200) {
							// 存储token和用户信息
							const token = responseData.data.token;
							const userInfo = responseData.data.userInfo || {};

							console.log('token:', token)
							console.log('userInfo:', userInfo)
							// 使用auth工具保存登录状态
							saveLoginState(token, userInfo);

							// 提示登录成功
							uni.showToast({
								title: '登录成功',
								icon: 'success',
								duration: 1500
							});


							setTimeout(() => {
								// 使用switchTab而不是reLaunch
								uni.switchTab({

									url: '/pages/ai_generate/ai_generate',
									success: () => {

									},
									fail: (err) => {
										console.error('跳转到首页失败:', err);
									}
								});
							}, 1500);
						} else {
							// 业务逻辑错误
							uni.showToast({
								title: responseData.message || '登录失败',
								icon: 'none'
							});
						}
					} else {
						// HTTP错误
						uni.showToast({
							title: '服务器响应错误: ' + res.statusCode,
							icon: 'none'
						});
					}
				}).catch(err => {
					uni.hideLoading();
					console.error('登录失败', err);
					const errorMsg = err?.data?.detail?.message || 
						err?.data?.message || 
						err?.message || 
						'登录失败，请检查网络或稍后重试';
					uni.showToast({
						title: errorMsg,
						icon: 'none'
					});
				});
			},

			// 处理注册
			handleRegister() {
				// 验证必填字段
				const form = this.registerForm;
				// if (!form.username || !form.password || !form.email || !form.firstName || !form.lastName) {
				if (!form.username || !form.password || !form.city || !form.nickName) {
					uni.showToast({
						title: '请填写所有必填字段',
						icon: 'none'
					});
					return;
				}



				uni.showLoading({
					title: '正在注册...',
					mask: true
				});

				// 构建注册请求参数
				const registerData = {
					username: form.username,
					password: form.password,
					// email: form.email,
					// firstName: form.firstName,
					// lastName: form.lastName,
					nickname: form.nickName,
					city: form.city,
					gender: form.gender // 现在是字符串类型
				};

				// 调用注册接口
				register(registerData).then(res => {
					uni.hideLoading();


					if (res.statusCode === 200) {
						const responseData = res.data;

						if (responseData.code === 200) {
							// 注册成功\
							console.log(res)
							uni.showToast({
								title: '注册成功',
								icon: 'success',
								duration: 1500
							});

							// 延迟后切换到登录表单
							setTimeout(() => {
								// 清空表单
								this.registerForm = {
									username: '',
									password: '',
									email: '',
									// firstName: '',
									// lastName: '',
									nickName: '',
									preferredLanguage: 'zh',
									gender: 'male'
								};
								this.Secondpassword = ''

								// 切换到登录表单并预填写用户名
								this.loginForm.username = registerData.username;
								this.switchForm('login');
							}, 1500);
						} else {
							console.log(res)
							// 业务逻辑错误
							uni.showToast({
								title: responseData.message || '注册失败',
								icon: 'none'
							});
						}
					} else {
						// HTTP错误
						uni.showToast({
							title: '服务器响应错误: ' + res.statusCode,
							icon: 'none'
						});
					}
				}).catch(err => {
					uni.hideLoading();
					console.error('注册失败', err);
					const errorMsg = err?.data?.detail?.message || 
						err?.data?.message || 
						err?.message || 
						'注册失败，请检查网络或稍后重试';
					uni.showToast({
						title: errorMsg,
						icon: 'none'
					});
				});
			},


		},
		onLoad() {
			// 检查token是否存在
			const token = getToken();
			// 如果token存在，直接跳转到首页
			if (token) {

				uni.reLaunch({
					url: '/pages/ai_generate/ai_generate'
				});
				return;
			} else {

			}


			this.initCityData();
		},

	}
</script>

<style lang="scss">
	/* ===== 设计令牌（本页局部，便于编译兼容） ===== */
	$brand: #2E86DE;
	$brand-dark: #1B6EC2;
	$brand-bg: #eef4fb;
	$text-1: #1e293b;
	$text-2: #64748b;
	$text-3: #94a3b8;
	$border: #e2e8f0;
	$bg-page: #f4f7fb;
	$danger: #ff3b30;

	/* 滚动选择器样式 */
	.input-select {
		position: relative;
		margin-bottom: 16px;
	}

	.picker-text {
		width: 100%;
		height: 48px;
		line-height: 48px;
		padding: 0 16px 0 18px;
		border: 1px solid $border;
		border-radius: 12px;
		font-size: 14px;
		color: $text-1;
		background: #f8fafc;
		box-sizing: border-box;
		transition: all 0.2s ease;
	}

	.picker-text:active {
		background: $brand-bg;
		border-color: $brand;
	}

	.isSame {
		color: $danger;
		font-size: 12px;
		display: block;
		margin: -8px 0 10px 4px;
	}

	.isSame::before {
		content: '*两次输入的密码不一致';
	}

	.login-container {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background: $bg-page;
	}

	/* 左侧宣传区：品牌渐变 + 装饰圆 */
	.promo-section {
		flex: 1;
		padding: 56px 24px 40px;
		background: linear-gradient(135deg, #2E86DE 0%, #54A0FF 55%, #74B9FF 100%);
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		text-align: center;
		position: relative;
		overflow: hidden;

		/* 装饰光晕 */
		&::before {
			content: "";
			position: absolute;
			top: -60px;
			right: -60px;
			width: 200px;
			height: 200px;
			border-radius: 50%;
			background: rgba(255, 255, 255, 0.12);
		}

		&::after {
			content: "";
			position: absolute;
			bottom: -80px;
			left: -50px;
			width: 180px;
			height: 180px;
			border-radius: 50%;
			background: rgba(255, 255, 255, 0.08);
		}
	}

	.promo-title {
		font-size: 34px;
		font-weight: 800;
		color: #fff;
		margin-bottom: 14px;
		letter-spacing: 2px;
		position: relative;
		z-index: 1;
		text-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
	}

	.promo-subtitle {
		font-size: 22px;
		color: rgba(255, 255, 255, 0.95);
		margin-bottom: 12px;
		font-weight: 500;
		position: relative;
		z-index: 1;
	}

	.promo-text {
		font-size: 13px;
		color: rgba(255, 255, 255, 0.75);
		letter-spacing: 0.5px;
		position: relative;
		z-index: 1;
	}

	/* 右侧表单区 */
	.login-section {
		padding: 28px 20px 40px;
		background: #fff;
		display: flex;
		align-items: center;
		justify-content: center;
		box-shadow: 0 -8px 30px rgba(15, 23, 42, 0.08);
		border-radius: 28px 28px 0 0;
		position: relative;
		z-index: 2;
		margin-top: -24px;
	}

	.login-box {
		width: 100%;
		max-width: 340px;
	}

	/* 表单切换标签 */
	.form-tabs {
		display: flex;
		margin-bottom: 24px;
		background: #f1f5f9;
		border-radius: 14px;
		padding: 4px;
	}

	.tab-item {
		flex: 1;
		text-align: center;
		padding: 10px 0;
		font-size: 15px;
		color: $text-2;
		position: relative;
		border-radius: 10px;
		transition: all 0.25s ease;
		font-weight: 500;

		&.active {
			color: #fff;
			background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
			box-shadow: 0 4px 12px rgba(46, 134, 222, 0.3);
		}
	}

	.login-title {
		font-size: 24px;
		font-weight: 700;
		color: $text-1;
		margin-bottom: 4px;
	}

	.login-subtitle {
		font-size: 13px;
		color: $text-3;
		margin-bottom: 22px;
		letter-spacing: 0.5px;
	}

	.input-group {
		margin-top: 12px;
	}

	.login-input {
		width: 100%;
		height: 48px;
		border: 1px solid $border;
		border-radius: 12px;
		margin-bottom: 14px;
		padding: 0 16px;
		font-size: 14px;
		box-sizing: border-box;
		background: #f8fafc;
		transition: all 0.2s ease;

		&:focus {
			border-color: $brand;
			background: #fff;
			box-shadow: 0 0 0 3px rgba(46, 134, 222, 0.12);
			outline: none;
		}
	}

	.select-container {
		width: 100%;
		margin-bottom: 14px;
	}

	.picker-view {
		width: 100%;
		height: 48px;
		border: 1px solid $border;
		border-radius: 12px;
		padding: 0 16px;
		font-size: 14px;
		box-sizing: border-box;
		display: flex;
		align-items: center;
		color: $text-1;
		background: #f8fafc;
		transition: all 0.2s ease;
	}

	.login-button {
		width: 100%;
		height: 48px;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		color: #fff;
		border: none;
		border-radius: 999px;
		font-size: 16px;
		font-weight: 600;
		margin-top: 8px;
		box-sizing: border-box;
		letter-spacing: 1px;
		box-shadow: 0 8px 20px rgba(46, 134, 222, 0.3);
		transition: all 0.2s ease;

		&:active {
			transform: scale(0.97);
			opacity: 0.92;
			box-shadow: 0 4px 12px rgba(46, 134, 222, 0.3);
		}
	}

	/* 响应式适配 */
	@media screen and (min-width: 768px) {
		.login-container {
			flex-direction: row;
		}

		.login-section {
			width: 420px;
			height: 100vh;
			border-radius: 28px 0 0 28px;
			margin-top: 0;
			box-shadow: -8px 0 30px rgba(15, 23, 42, 0.08);
		}

		.promo-section {
			text-align: left;
			align-items: flex-start;
			padding: 56px;
		}
	}

	@media screen and (max-width: 380px) {
		.login-section {
			padding: 22px 16px 32px;
		}

		.login-box {
			width: 100%;
		}

		.login-title {
			font-size: 21px;
		}

		.login-subtitle {
			margin-bottom: 16px;
			font-size: 12px;
		}

		.login-input {
			height: 44px;
			margin-bottom: 11px;
			padding: 0 12px;
		}

		.login-button {
			height: 44px;
			font-size: 15px;
		}
	}

	@media screen and (max-width: 320px) {

		.login-input,
		.login-button {
			font-size: 13px;
		}
	}

	@media screen and (max-height: 500px) {
		.promo-section {
			padding: 18px;
			min-height: auto;
		}

		.promo-text {
			display: none;
		}

		.login-subtitle {
			display: none;
		}

		.login-input,
		.login-button {
			margin-bottom: 8px;
		}

		.input-group {
			margin-top: 8px;
		}

		.login-title {
			font-size: 18px;
		}
	}
</style>