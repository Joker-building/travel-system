/**
 * 天气API接口
 *
 * 说明：和风天气的密钥仅在后端保存，前端统一通过后端代理
 * /api/proxy/weather 获取天气数据，避免密钥落入客户端/小程序包。
 */

import request from '@/utils/request';

// 调用后端天气代理，endpoint: now | 7d | 24h | indices | air
async function callProxy(endpoint, location, type = '0') {
	const res = await request({
		url: '/api/proxy/weather',
		method: 'GET',
		data: {
			endpoint,
			location,
			type
		}
	});
	// 后端返回 success_response(data=<和风原始JSON>)
	return res.data.data;
}

/**
 * 获取当前位置
 * @returns {Promise<{latitude: number, longitude: number}>} 位置信息
 */
function getLocation() {
	return new Promise((resolve, reject) => {
		// 添加超时处理
		let isResolved = false;
		const timeout = setTimeout(() => {
			if (!isResolved) {
				isResolved = true;
				// 武汉市默认位置
				resolve({
					longitude: 114.3162,
					latitude: 30.5811,
					city: '武汉市'
				});
			}
		}, 5000); // 5秒超时

		uni.getLocation({
			type: 'gcj02',
			success: (res) => {
				clearTimeout(timeout);
				if (!isResolved) {
					isResolved = true;
					resolve({
						latitude: res.latitude,
						longitude: res.longitude
					});
				}
			},
			fail: (err) => {
				clearTimeout(timeout);
				console.error('获取位置失败:', err);

				if (!isResolved) {
					isResolved = true;
					// 武汉市默认位置
					resolve({
						longitude: 114.3162,
						latitude: 30.5811,
						city: '武汉市'
					});
				}
			}
		});
	});
}

/**
 * 获取实时天气
 * @param {string} location 位置坐标，经度,纬度，如"116.41,39.92"
 * @returns {Promise<Object>} 天气数据
 */
function getWeatherNow(location) {
	return callProxy('now', location);
}

/**
 * 获取天气预报
 * @param {string} location 位置坐标，经度,纬度，如"116.41,39.92"
 * @returns {Promise<Object>} 天气预报数据
 */
function getWeatherForecast(location) {
	return callProxy('7d', location);
}

/**
 * 获取24小时天气预报
 * @param {string} location 位置坐标，经度,纬度，如"116.41,39.92"
 * @returns {Promise<Object>} 24小时天气预报数据
 */
function getWeatherHourly(location) {
	return callProxy('24h', location);
}

/**
 * 获取生活指数
 * @param {string} location 位置坐标，经度,纬度，如"116.41,39.92"
 * @returns {Promise<Object>} 生活指数数据
 */
function getLifeIndices(location) {
	return callProxy('indices', location, '0');
}

/**
 * 获取空气质量
 * @param {string} location 位置坐标，经度,纬度，如"116.41,39.92"
 * @returns {Promise<Object>} 空气质量数据
 */
function getAirQuality(location) {
	return callProxy('air', location);
}

/**
 * 获取完整天气数据
 * @returns {Promise<Object>} 完整天气数据
 */
async function getFullWeatherData() {
	try {
		// 获取当前位置
		const position = await getLocation();
		const location = `${position.longitude},${position.latitude}`;

		// 并行请求所有天气数据
		// 空气质量(air)单独兜底：即便失败也不拖垮整体天气请求
		const [nowWeather, forecast, hourly, lifeIndices, airQuality] = await Promise.all([
			getWeatherNow(location),
			getWeatherForecast(location),
			getWeatherHourly(location),
			getLifeIndices(location),
			getAirQuality(location).catch(() => null)
		]);

		// 使用position中的城市名称，如果没有则使用默认值
		const cityName = position.city || '未知城市';

		// 处理实时天气数据，确保数据结构符合组件期望的格式
		const currentWeather = {
			temperature: nowWeather && nowWeather.now ? nowWeather.now.temp : '0',
			weather: nowWeather && nowWeather.now ? nowWeather.now.text : '未知',
			humidity: nowWeather && nowWeather.now ? nowWeather.now.humidity : '0',
			windDirection: nowWeather && nowWeather.now ? nowWeather.now.windDir : '无风向',
			windPower: nowWeather && nowWeather.now ? nowWeather.now.windScale : '0',
			reportTime: nowWeather && nowWeather.updateTime ? nowWeather.updateTime : new Date().toISOString()
		};

		// 处理预报数据
		const forecastData = forecast && forecast.daily ? forecast.daily.map(day => ({
			date: {
				year: new Date(day.fxDate).getFullYear(),
				month: new Date(day.fxDate).getMonth() + 1,
				day: new Date(day.fxDate).getDate(),
				weekday: ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][new Date(day.fxDate).getDay()]
			},
			dayWeather: day.textDay,
			nightWeather: day.textNight,
			dayTemp: day.tempMax,
			nightTemp: day.tempMin
		})) : [];

		// 处理小时预报数据
		const hourlyData = hourly && hourly.hourly ? hourly.hourly.map(hour => ({
			time: hour.fxTime.substring(11, 16),
			weather: hour.text,
			temperature: hour.temp
		})) : [];

		// 处理生活指数
		const lifeIndexData = lifeIndices && lifeIndices.daily ? lifeIndices.daily.map(index => ({
			type: index.type,
			name: index.name,
			level: index.category,
			description: index.text
		})) : [];

		// 生成旅游建议（基于天气情况）
		const weatherCondition = nowWeather && nowWeather.now ? nowWeather.now.text : '';
		const travelTips = generateTravelTips(weatherCondition);

		// 组合所有数据
		const weatherData = {
			cityName: cityName,
			location: location,
			current: nowWeather,
			forecast: forecast,
			hourly: hourly,
			lifeIndices: lifeIndices,
			airQuality: airQuality,
			// 添加已格式化的数据，便于页面直接使用
			currentWeather: currentWeather,
			forecastData: forecastData,
			hourlyData: hourlyData,
			lifeIndexData: lifeIndexData,
			travelTips: travelTips
		};

		return weatherData;
	} catch (error) {
		console.error('获取完整天气数据失败:', error);
		// 返回默认数据结构，避免页面报错
		return {
			cityName: '未知城市',
			location: '',
			currentWeather: {
				temperature: '0',
				weather: '未知',
				humidity: '0',
				windDirection: '无风向',
				windPower: '0',
				reportTime: new Date().toISOString()
			},
			forecastData: [],
			hourlyData: [],
			lifeIndexData: [],
			travelTips: ['当前无法获取天气数据，请稍后再试']
		};
	}
}

/**
 * 生成旅游建议（基于天气情况）
 * @param {String} weather - 天气状况
 * @returns {Array} 旅游建议列表
 */
function generateTravelTips(weather) {
	const tips = [];

	// 基础提示，总是添加
	tips.push('景点人流量较大，建议提前规划行程。');
	tips.push('记得携带身份证和其他必要证件。');

	// 根据天气添加特定提示
	if (weather.includes('雨')) {
		tips.push('当前天气有雨，出行请携带雨具。');
		tips.push('雨天路滑，注意安全，减速慢行。');
		tips.push('部分户外景点可能关闭，请提前确认。');
	} else if (weather.includes('雪')) {
		tips.push('雪天路滑，注意保暖和防滑。');
		tips.push('部分交通可能受影响，请留意路况信息。');
		tips.push('雪景拍照注意相机防潮防水。');
	} else if (weather.includes('晴')) {
		tips.push('晴天紫外线较强，请做好防晒措施。');
		tips.push('户外活动适宜，可多准备些饮用水。');
		tips.push('适合拍照，景色清晰。');
	} else if (weather.includes('云') || weather.includes('阴')) {
		tips.push('阴天光线柔和，适合拍照。');
		tips.push('温度可能有变化，建议携带薄外套。');
	}

	return tips;
}

// 统一导出所有需要的函数
export {
	getLocation,
	getWeatherNow,
	getWeatherForecast,
	getWeatherHourly,
	getLifeIndices,
	getAirQuality,
	getFullWeatherData
};
