/**
 * 天气数据处理工具类
 */

// 天气图标映射
const WEATHER_ICONS = {
	'晴': 'icon-qing',
	'多云': 'icon-duoyun',
	'阴': 'icon-yin',
	'阵雨': 'icon-zhenyu',
	'雷阵雨': 'icon-leizhenyu',
	'雨夹雪': 'icon-yujiaxue',
	'小雨': 'icon-xiaoyu',
	'中雨': 'icon-zhongyu',
	'大雨': 'icon-dayu',
	'暴雨': 'icon-baoyu',
	'大暴雨': 'icon-dabaoyu',
	'特大暴雨': 'icon-tedabaoyu',
	'阵雪': 'icon-zhenxue',
	'小雪': 'icon-xiaoxue',
	'中雪': 'icon-zhongxue',
	'大雪': 'icon-daxue',
	'暴雪': 'icon-baoxue',
	'雾': 'icon-wu',
	'冻雨': 'icon-dongyu',
	'沙尘暴': 'icon-shachenbao',
	'小雨-中雨': 'icon-xiaoyu',
	'中雨-大雨': 'icon-zhongyu',
	'大雨-暴雨': 'icon-dayu',
	'暴雨-大暴雨': 'icon-baoyu',
	'大暴雨-特大暴雨': 'icon-dabaoyu',
	'小雪-中雪': 'icon-xiaoxue',
	'中雪-大雪': 'icon-zhongxue',
	'大雪-暴雪': 'icon-daxue',
	'浮尘': 'icon-fuchen',
	'扬沙': 'icon-yangsha',
	'强沙尘暴': 'icon-qiangshachenbao',
	'霾': 'icon-mai',
	'雨': 'icon-xiaoyu', // 兜底
	'雪': 'icon-xiaoxue', // 兜底
	'未知': 'icon-weizhi'
};

// 生活指数图标映射
const LIFE_INDEX_ICONS = {
	'comf': 'icon-shushi', // 舒适度指数
	'cw': 'icon-xiche', // 洗车指数
	'drsg': 'icon-chuanyi', // 穿衣指数
	'flu': 'icon-ganmao', // 感冒指数
	'sport': 'icon-yundong', // 运动指数
	'trav': 'icon-lvyou', // 旅游指数
	'uv': 'icon-ziwaixian', // 紫外线指数
	'air': 'icon-kongqi' // 空气指数
};

// 星期映射
const WEEKDAY = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

/**
 * 格式化日期
 * @param {Date|String} date - 日期对象或字符串
 * @returns {Object} 格式化后的日期对象
 */
export function formatDate(date) {
	if (typeof date === 'string') {
		date = new Date(date);
	}

	const year = date.getFullYear();
	const month = date.getMonth() + 1;
	const day = date.getDate();
	const weekday = WEEKDAY[date.getDay()];
	const hour = date.getHours().toString().padStart(2, '0');
	const minute = date.getMinutes().toString().padStart(2, '0');

	return {
		year,
		month,
		day,
		weekday,
		hour,
		minute,
		fullDate: `${year}-${month}-${day}`,
		monthDay: `${month}月${day}日`,
		time: `${hour}:${minute}`
	};
}

/**
 * 格式化天气数据
 * @param {Object} weatherData - 天气API返回的原始数据
 * @returns {Object} 格式化后的天气数据
 */
export function formatWeatherData(weatherData) {
	try {
		if (!weatherData || !weatherData.lives || weatherData.lives.length === 0) {
			return null;
		}

		const live = weatherData.lives[0];

		return {
			city: live.city,
			weather: live.weather,
			temperature: live.temperature,
			windDirection: live.winddirection,
			windPower: live.windpower,
			humidity: live.humidity,
			reportTime: formatDate(live.reporttime).time,
			date: formatDate(new Date()),
			icon: WEATHER_ICONS[live.weather] || 'icon-weizhi'
		};
	} catch (error) {
		console.error('格式化天气数据出错', error);
		return null;
	}
}

/**
 * 格式化天气预报数据
 * @param {Object} forecastData - 预报API返回的原始数据
 * @returns {Array} 格式化后的预报数据
 */
export function formatForecastData(forecastData) {
	try {
		if (!forecastData || !forecastData.forecasts || forecastData.forecasts.length === 0) {
			return [];
		}

		const forecast = forecastData.forecasts[0];

		return forecast.casts.map((cast) => {
			const date = new Date(cast.date);
			return {
				date: formatDate(date),
				dayWeather: cast.dayweather,
				nightWeather: cast.nightweather,
				dayTemp: cast.daytemp,
				nightTemp: cast.nighttemp,
				dayWind: cast.daywind,
				nightWind: cast.nightwind,
				dayPower: cast.daypower,
				nightPower: cast.nightpower,
				icon: WEATHER_ICONS[cast.dayweather] || 'icon-weizhi'
			};
		});
	} catch (error) {
		console.error('格式化预报数据出错', error);
		return [];
	}
}

/**
 * 获取未来24小时天气数据（模拟）
 * @param {Object} currentWeather - 当前天气数据
 * @param {Array} forecastData - 天气预报数据
 * @returns {Array} 小时预报数据
 */
export function generateHourlyData(currentWeather, forecastData) {
	const hourlyData = [];
	const now = new Date();
	const currentHour = now.getHours();
	const currentTemp = parseInt(currentWeather.temperature);
	const tomorrowTemp = forecastData[1] ? parseInt(forecastData[1].dayTemp) : currentTemp;

	// 生成24小时数据
	for (let i = 0; i < 24; i++) {
		const hour = (currentHour + i) % 24;
		const isNextDay = currentHour + i >= 24;
		const date = new Date();

		if (isNextDay) {
			date.setDate(date.getDate() + 1);
		}

		date.setHours(hour);

		// 简单模拟温度变化
		let temp;
		if (hour >= 6 && hour <= 14) {
			// 上午温度上升
			temp = isNextDay ?
				Math.round(tomorrowTemp - 2 + (hour - 6) * 0.5) :
				Math.round(currentTemp - 2 + (hour - 6) * 0.5);
		} else if (hour >= 15 && hour <= 18) {
			// 傍晚温度保持
			temp = isNextDay ? tomorrowTemp : currentTemp;
		} else {
			// 夜间温度下降
			temp = isNextDay ?
				Math.round(tomorrowTemp - (hour < 6 ? (6 - hour) : (hour - 18)) * 0.3) :
				Math.round(currentTemp - (hour < 6 ? (6 - hour) : (hour - 18)) * 0.3);
		}

		// 简单模拟天气情况
		let weather;
		if (i === 0) {
			weather = currentWeather.weather;
		} else {
			if (isNextDay && forecastData[1]) {
				weather = forecastData[1].dayWeather;
			} else {
				weather = currentWeather.weather;
			}
		}

		hourlyData.push({
			time: `${hour}:00`,
			hour: hour,
			temperature: temp.toString(),
			weather: weather,
			icon: WEATHER_ICONS[weather] || 'icon-weizhi'
		});
	}

	return hourlyData;
}

/**
 * 生成生活指数数据（模拟）
 * @param {String} weather - 天气状况
 * @returns {Array} 生活指数数据
 */
export function generateLifeIndexData(weather) {
	// 基于天气状况生成模拟的生活指数数据
	const hasRain = weather.includes('雨');
	const hasSnow = weather.includes('雪');
	const isCloudy = weather.includes('云') || weather.includes('阴');
	const isSunny = weather.includes('晴');

	return [{
			type: 'comf',
			name: '舒适度指数',
			level: hasRain || hasSnow ? '较差' : (isCloudy ? '一般' : '舒适'),
			description: hasRain || hasSnow ? '天气较凉，注意保暖。' : (isCloudy ? '较舒适，建议穿薄外套。' : '天气舒适，适宜出行。'),
			icon: LIFE_INDEX_ICONS['comf']
		},
		{
			type: 'cw',
			name: '洗车指数',
			level: hasRain || hasSnow ? '不宜' : '较适宜',
			description: hasRain || hasSnow ? '不宜洗车，路面潮湿，车辆易脏。' : '较适宜洗车，天气条件不错。',
			icon: LIFE_INDEX_ICONS['cw']
		},
		{
			type: 'drsg',
			name: '穿衣指数',
			level: '舒适',
			description: '建议穿薄外套或牛仔裤等服装。',
			icon: LIFE_INDEX_ICONS['drsg']
		},
		{
			type: 'flu',
			name: '感冒指数',
			level: hasRain ? '较易发' : '低发',
			description: hasRain ? '天气转凉，较易发生感冒，注意防护。' : '感冒发生几率较低，可放心出门。',
			icon: LIFE_INDEX_ICONS['flu']
		},
		{
			type: 'sport',
			name: '运动指数',
			level: hasRain || hasSnow ? '不宜' : (isSunny ? '适宜' : '较适宜'),
			description: hasRain || hasSnow ? '不宜进行户外运动。' : (isSunny ? '天气较好，适宜户外运动。' : '气象条件对运动影响不大。'),
			icon: LIFE_INDEX_ICONS['sport']
		},
		{
			type: 'trav',
			name: '旅游指数',
			level: hasRain || hasSnow ? '不适宜' : (isSunny ? '适宜' : '较适宜'),
			description: hasRain || hasSnow ? '天气较差，不建议旅游。' : (isSunny ? '天气较好，适宜旅游。' : '天气一般，可考虑出行。'),
			icon: LIFE_INDEX_ICONS['trav']
		},
		{
			type: 'uv',
			name: '紫外线指数',
			level: isSunny ? '中等' : '弱',
			description: isSunny ? '紫外线中等，外出建议涂抹SPF大于15的防晒霜。' : '紫外线较弱，可以适当户外活动。',
			icon: LIFE_INDEX_ICONS['uv']
		},
		{
			type: 'air',
			name: '空气质量指数',
			level: '良',
			description: '空气质量可接受，敏感人群应减少户外活动。',
			icon: LIFE_INDEX_ICONS['air']
		}
	];
}

/**
 * 生成旅游建议（基于天气情况）
 * @param {String} weather - 天气状况
 * @returns {Array} 旅游建议列表
 */
export function generateTravelTips(weather) {
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

/**
 * 获取天气图标类名
 * @param {String} weather - 天气状况
 * @returns {String} 图标类名
 */
export function getWeatherIcon(weatherText) {
	// if (!weather) return 'fa-cloud';

	// const weatherText = weather
	console.log('来到检索天气图标处，weatherText是：', weatherText)
	// 处理晴天
	if (weatherText.includes('晴') ||
		weatherText.includes('clear') ||
		weatherText.includes('sunny')) {
		return 'fa-sun';
	}

	// 处理多云
	if (weatherText.includes('多云') ||
		weatherText.includes('partly cloudy') ||
		weatherText.includes('cloudy')) {
		console.log('多云天气图标')
		return 'fa-cloud-sun';
	}

	// 处理阴天
	if (weatherText.includes('阴') ||
		weatherText.includes('overcast')) {
		return 'fa-cloud';
	}

	// 处理雨
	if (weatherText.includes('雨') ||
		weatherText.includes('rain') ||
		weatherText.includes('drizzle')) {
		// 处理不同类型的雨
		if (weatherText.includes('雷') || weatherText.includes('thunder')) {
			return 'fa-bolt';
		}
		if (weatherText.includes('小雨') || weatherText.includes('light')) {
			return 'fa-cloud-rain';
		}
		if (weatherText.includes('大雨') || weatherText.includes('heavy')) {
			return 'fa-cloud-showers-heavy';
		}
		// 默认雨图标
		return 'fa-cloud-rain';
	}

	// 处理雪
	if (weatherText.includes('雪') ||
		weatherText.includes('snow')) {
		return 'fa-snowflake';
	}

	// 处理雾
	if (weatherText.includes('雾') ||
		weatherText.includes('霾') ||
		weatherText.includes('fog') ||
		weatherText.includes('haze')) {
		return 'fa-smog';
	}

	// 默认图标
	console.log('返回默认图标')
	return 'fa-cloud';
}

/**
 * 获取生活指数图标类名
 * @param {String} type - 生活指数类型
 * @returns {String} 图标类名
 */
export function getLifeIndexIcon(type) {
	// 基于类型代码匹配图标
	const iconMap = {
		'comf': 'fa-temperature-low', // 舒适度指数
		'cw': 'fa-car', // 洗车指数
		'drsg': 'fa-tshirt', // 穿衣指数
		'flu': 'fa-virus', // 感冒指数
		'sport': 'fa-running', // 运动指数
		'trav': 'fa-plane', // 旅游指数
		'uv': 'fa-sun', // 紫外线指数
		'air': 'fa-wind', // 空气质量指数
		// 扩展更多类型
		'umbrella': 'fa-umbrella', // 雨伞指数
		'drying': 'fa-tshirt', // 晾晒指数
		'makeup': 'fa-smile', // 化妆指数
		'ac': 'fa-snowflake', // 空调指数
		'allergy': 'fa-seedling', // 过敏指数
		'fishing': 'fa-fish', // 钓鱼指数
		'mosquito': 'fa-bug', // 蚊虫指数
		'traffic': 'fa-car-side', // 交通指数
		'sunglasses': 'fa-glasses', // 太阳镜指数
		'beer': 'fa-beer', // 啤酒指数
		'sunscreen': 'fa-shield-alt', // 防晒指数
		'dating': 'fa-heart' // 约会指数
	};

	// 如果能直接通过type匹配到图标，则返回
	if (iconMap[type]) {
		return iconMap[type];
	}

	// 如果type是数字代码，则进行映射
	const typeCodeMap = {
		'1': 'fa-temperature-low', // 体感温度
		'2': 'fa-tshirt', // 穿衣指数
		'3': 'fa-car', // 洗车指数
		'4': 'fa-running', // 运动指数
		'5': 'fa-virus', // 感冒指数
		'6': 'fa-sun', // 紫外线指数
		'7': 'fa-umbrella', // 旅游指数 
		'8': 'fa-seedling', // 过敏指数
		'9': 'fa-bug', // 蚊虫指数
		'10': 'fa-tshirt', // 晾晒指数
		'11': 'fa-plane', // 旅游指数
		'12': 'fa-wind', // 空气污染扩散指数
		'13': 'fa-briefcase-medical', // 空气污染扩散指数
		'14': 'fa-fish', // 钓鱼指数
		'15': 'fa-car-side', // 交通指数
		'16': 'fa-beer' // 啤酒指数
	};

	if (typeCodeMap[type]) {
		return typeCodeMap[type];
	}

	// 基于指数名称的文本匹配
	const textMatches = {
		// 常见指数名称的关键词匹配
		'温度': 'fa-temperature-high',
		'舒适': 'fa-temperature-low',
		'穿衣': 'fa-tshirt',
		'衣物': 'fa-tshirt',
		'洗车': 'fa-car',
		'汽车': 'fa-car',
		'运动': 'fa-running',
		'锻炼': 'fa-running',
		'感冒': 'fa-virus',
		'病毒': 'fa-virus',
		'流感': 'fa-virus',
		'紫外线': 'fa-sun',
		'防晒': 'fa-shield-alt',
		'阳光': 'fa-sun',
		'旅游': 'fa-plane',
		'旅行': 'fa-plane',
		'出行': 'fa-suitcase',
		'过敏': 'fa-seedling',
		'花粉': 'fa-seedling',
		'蚊虫': 'fa-bug',
		'昆虫': 'fa-bug',
		'晾晒': 'fa-tshirt',
		'钓鱼': 'fa-fish',
		'交通': 'fa-car-side',
		'开车': 'fa-car-side',
		'啤酒': 'fa-beer',
		'饮酒': 'fa-beer',
		'医疗': 'fa-briefcase-medical',
		'健康': 'fa-heartbeat',
		'雷电': 'fa-bolt',
		'雨': 'fa-umbrella',
		'风': 'fa-wind',
		'雾': 'fa-smog',
		'霾': 'fa-smog',
		'污染': 'fa-smog',
		'空气': 'fa-wind'
	};

	// 使用字符串匹配查找最合适的图标
	// 注意：这里假设type可能是名称而不是代码
	for (const keyword in textMatches) {
		if (type.includes(keyword)) {
			return textMatches[keyword];
		}
	}

	// 默认返回信息图标
	return 'fa-info-circle';
}

export default {
	formatDate,
	formatWeatherData,
	formatForecastData,
	generateHourlyData,
	generateLifeIndexData,
	generateTravelTips,
	getWeatherIcon,
	getLifeIndexIcon
};