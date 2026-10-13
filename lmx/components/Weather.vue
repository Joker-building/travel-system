<template>
  <div class="weather-container">
    <!-- 加载中状态 -->
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <div class="loading-text">正在获取天气信息...</div>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="error-container">
      <div class="error-icon">!</div>
      <div class="error-message">{{ error }}</div>
      <button class="retry-button" @click="fetchWeatherData">重试</button>
    </div>
    
    <!-- 天气数据显示 -->
    <div v-else-if="weatherData" class="weather-content">
      <!-- 当前天气信息 -->
      <div class="current-weather">
        <div class="location-info">
          <div class="city-name">{{ weatherData.city }}</div>
          <div class="refresh-button" @click="refreshWeatherData">
            <i class="refresh-icon">⟳</i>
            <span>刷新</span>
          </div>
        </div>
        
        <div class="weather-main">
          <div class="weather-icon">
            <!-- 根据天气状况显示对应图标 -->
            <img :src="getWeatherIcon(weatherData.weather)" alt="天气图标">
          </div>
          <div class="weather-info">
            <div class="temperature">{{ weatherData.temperature }}°C</div>
            <div class="weather-desc">{{ weatherData.weather }}</div>
          </div>
        </div>
        
        <div class="weather-details">
          <div class="detail-item">
            <div class="detail-label">风向</div>
            <div class="detail-value">{{ weatherData.windDirection }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">风力</div>
            <div class="detail-value">{{ weatherData.windPower }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">湿度</div>
            <div class="detail-value">{{ weatherData.humidity }}%</div>
          </div>
        </div>
      </div>
      
      <!-- 未来天气预报 -->
      <div v-if="forecastData && forecastData.length" class="forecast-section">
        <div class="section-title">未来天气预报</div>
        <div class="forecast-list">
          <div v-for="(item, index) in forecastData" :key="index" class="forecast-item">
            <div class="forecast-date">{{ formatDate(item.date) }}</div>
            <div class="forecast-icon">
              <img :src="getWeatherIcon(item.dayWeather)" alt="天气图标">
            </div>
            <div class="forecast-temp">{{ item.dayTemp }}°C / {{ item.nightTemp }}°C</div>
            <div class="forecast-weather">{{ item.dayWeather }}</div>
          </div>
        </div>
      </div>
      
      <!-- 小时预报 -->
      <div v-if="hourlyData && hourlyData.length" class="hourly-section">
        <div class="section-title">小时预报</div>
        <div class="hourly-list">
          <div v-for="(item, index) in hourlyData" :key="index" class="hourly-item">
            <div class="hourly-time">{{ formatTime(item.time) }}</div>
            <div class="hourly-icon">
              <img :src="getWeatherIcon(item.weather)" alt="天气图标">
            </div>
            <div class="hourly-temp">{{ item.temperature }}°C</div>
          </div>
        </div>
      </div>
      
      <!-- 生活指数 -->
      <div v-if="lifeIndexData && lifeIndexData.length" class="life-section">
        <div class="section-title">生活指数</div>
        <div class="life-list">
          <div 
            v-for="(item, index) in lifeIndexData" 
            :key="index" 
            class="life-item"
            @click="showLifeIndexDetail(item)"
          >
            <div class="life-icon">
              <img :src="getLifeIndexIcon(item.type)" alt="指数图标">
            </div>
            <div class="life-name">{{ item.name }}</div>
            <div class="life-level">{{ item.level }}</div>
          </div>
        </div>
      </div>
      
      <!-- 旅游建议 -->
      <div class="travel-tips" v-if="travelTips">
        <div class="section-title">旅游建议</div>
        <div class="tips-content">{{ travelTips }}</div>
      </div>
    </div>
    
    <!-- 生活指数详情弹窗 -->
    <div v-if="showDetailDialog" class="detail-dialog">
      <div class="dialog-content">
        <div class="dialog-header">
          <div class="dialog-title">{{ selectedLifeIndex.name }}</div>
          <div class="dialog-close" @click="showDetailDialog = false">×</div>
        </div>
        <div class="dialog-body">
          <div class="index-level">指数级别：{{ selectedLifeIndex.level }}</div>
          <div class="index-desc">{{ selectedLifeIndex.desc }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { getWeather, getLocationByIP } from '../utils/amap';

export default {
  name: 'WeatherComponent',
  data() {
    return {
      loading: true,
      error: null,
      weatherData: null,
      forecastData: [],
      hourlyData: [],
      lifeIndexData: [],
      travelTips: '',
      city: null,
      showDetailDialog: false,
      selectedLifeIndex: {}
    };
  },
  created() {
    this.fetchWeatherData();
  },
  methods: {
    async fetchWeatherData() {
      this.loading = true;
      this.error = null;
      
      try {
        // 1. 获取当前位置
        if (!this.city) {
          const locationData = await getLocationByIP();
          if (locationData && locationData.city) {
            this.city = locationData.adcode || locationData.city;
          } else {
            throw new Error('无法获取位置信息');
          }
        }
        
        // 2. 获取实时天气
        const baseWeather = await getWeather(this.city, 'base');
        if (!baseWeather || !baseWeather.lives || baseWeather.lives.length === 0) {
          throw new Error('无法获取当前天气信息');
        }
        
        // 3. 获取天气预报
        const forecastWeather = await getWeather(this.city, 'all');
        if (!forecastWeather || !forecastWeather.forecasts || forecastWeather.forecasts.length === 0) {
          throw new Error('无法获取天气预报信息');
        }
        
        // 4. 处理返回数据
        const liveData = baseWeather.lives[0];
        this.weatherData = {
          city: liveData.city,
          adcode: liveData.adcode,
          province: liveData.province,
          weather: liveData.weather,
          temperature: liveData.temperature,
          windDirection: liveData.winddirection,
          windPower: liveData.windpower,
          humidity: liveData.humidity,
          reportTime: liveData.reporttime
        };
        
        // 5. 处理预报数据
        const forecast = forecastWeather.forecasts[0];
        this.forecastData = forecast.casts || [];
        
        // 6. 模拟小时预报数据（高德API没有直接提供小时预报，这里模拟一下）
        this.generateHourlyForecast();
        
        // 7. 模拟生活指数数据（高德API没有直接提供生活指数，这里模拟一下）
        this.generateLifeIndex();
        
        // 8. 根据天气生成旅游建议
        this.generateTravelTips();
        
        this.loading = false;
      } catch (error) {
        this.error = typeof error === 'string' ? error : error.message || '获取天气信息失败';
        this.loading = false;
        console.error('天气数据获取失败:', error);
      }
    },
    
    refreshWeatherData() {
      this.fetchWeatherData();
    },
    
    // 格式化日期：2023-04-01 -> 4月1日
    formatDate(dateStr) {
      try {
        const date = new Date(dateStr);
        return `${date.getMonth() + 1}月${date.getDate()}日`;
      } catch (e) {
        return dateStr;
      }
    },
    
    // 格式化时间：2023-04-01 12:00:00 -> 12:00
    formatTime(timeStr) {
      try {
        const date = new Date(timeStr);
        return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
      } catch (e) {
        return timeStr;
      }
    },
    
    // 获取天气图标（实际项目中应该使用真实图标）
    getWeatherIcon(weather) {
      // 这里应该根据天气状况返回对应的图标URL
      // 简化处理，返回一个占位符
      return 'https://example.com/icons/weather.png';
    },
    
    // 获取生活指数图标
    getLifeIndexIcon(type) {
      // 这里应该根据指数类型返回对应的图标URL
      // 简化处理，返回一个占位符
      return 'https://example.com/icons/life-index.png';
    },
    
    // 显示生活指数详情
    showLifeIndexDetail(item) {
      this.selectedLifeIndex = item;
      this.showDetailDialog = true;
    },
    
    // 模拟生成小时预报
    generateHourlyForecast() {
      const hourlyData = [];
      const now = new Date();
      
      for (let i = 0; i < 24; i++) {
        const time = new Date(now.getTime() + i * 60 * 60 * 1000);
        hourlyData.push({
          time: time.toISOString(),
          temperature: Math.round(this.weatherData.temperature * 1 + Math.sin(i / 4) * 3),
          weather: this.weatherData.weather
        });
      }
      
      this.hourlyData = hourlyData;
    },
    
    // 模拟生成生活指数
    generateLifeIndex() {
      this.lifeIndexData = [
        {
          type: 'comfort',
          name: '舒适度指数',
          level: '舒适',
          desc: '白天温度适宜，风力不大，相对湿度较小，天气舒适。'
        },
        {
          type: 'uv',
          name: '紫外线指数',
          level: this.weatherData.weather.includes('雨') ? '最弱' : '中等',
          desc: this.weatherData.weather.includes('雨') ? '紫外线强度最弱，无需防晒。' : '紫外线强度中等，外出建议涂抹SPF大于15的防晒霜。'
        },
        {
          type: 'dressing',
          name: '穿衣指数',
          level: parseInt(this.weatherData.temperature) > 25 ? '炎热' : (parseInt(this.weatherData.temperature) > 15 ? '舒适' : '凉爽'),
          desc: parseInt(this.weatherData.temperature) > 25 ? '天气炎热，建议穿着轻薄、透气的衣物。' : (parseInt(this.weatherData.temperature) > 15 ? '天气舒适，建议穿着薄长袖或短袖衬衫。' : '天气凉爽，建议穿着长袖衬衫或薄外套。')
        },
        {
          type: 'travel',
          name: '旅游指数',
          level: this.weatherData.weather.includes('雨') ? '较差' : '适宜',
          desc: this.weatherData.weather.includes('雨') ? '天气较差，不建议进行户外旅游活动。' : '天气适宜旅游，适合户外活动和游览。'
        }
      ];
    },
    
    // 生成旅游建议
    generateTravelTips() {
      const weather = this.weatherData.weather;
      const temp = parseInt(this.weatherData.temperature);
      
      if (weather.includes('雨')) {
        this.travelTips = '今日有雨，建议携带雨具，选择室内景点游览。适合参观博物馆、美术馆等文化场所。';
      } else if (weather.includes('雪')) {
        this.travelTips = '今日有雪，注意保暖，道路可能湿滑，请注意安全。可以选择欣赏雪景，但不建议长时间户外活动。';
      } else if (temp > 30) {
        this.travelTips = '今日气温较高，注意防暑防晒，多补充水分。建议选择清凉的景点，如水上乐园、山区或有空调的室内场所。';
      } else if (temp < 5) {
        this.travelTips = '今日气温较低，注意保暖，添加衣物。适合参观室内景点，如果户外活动，建议准备热饮和保暖设备。';
      } else {
        this.travelTips = '今日天气适宜，是旅游的好时机。可以选择户外景点，进行徒步、摄影等活动，记得做好防晒工作。';
      }
    }
  }
};
</script>

<style scoped>
.weather-container {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  background-color: #f5f7fa;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  position: relative;
}

/* 加载状态 */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  color: #666;
  font-size: 16px;
}

/* 错误状态 */
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  padding: 20px;
}

.error-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background-color: #ff6b6b;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 16px;
}

.error-message {
  color: #666;
  font-size: 16px;
  text-align: center;
  margin-bottom: 20px;
}

.retry-button {
  background-color: #3498db;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.retry-button:hover {
  background-color: #2980b9;
}

/* 天气内容区域 */
.weather-content {
  padding: 20px;
}

/* 当前天气 */
.current-weather {
  background: linear-gradient(to right, #74ebd5, #acb6e5);
  border-radius: 10px;
  padding: 20px;
  color: white;
  margin-bottom: 20px;
}

.location-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.city-name {
  font-size: 24px;
  font-weight: bold;
}

.refresh-button {
  display: flex;
  align-items: center;
  cursor: pointer;
  opacity: 0.8;
  transition: opacity 0.3s;
}

.refresh-button:hover {
  opacity: 1;
}

.refresh-icon {
  margin-right: 5px;
  font-size: 18px;
}

.weather-main {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.weather-icon {
  width: 80px;
  height: 80px;
  margin-right: 20px;
}

.weather-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.temperature {
  font-size: 48px;
  font-weight: bold;
  line-height: 1;
  margin-bottom: 5px;
}

.weather-desc {
  font-size: 18px;
}

.weather-details {
  display: flex;
  justify-content: space-around;
}

.detail-item {
  text-align: center;
}

.detail-label {
  font-size: 14px;
  opacity: 0.8;
  margin-bottom: 5px;
}

.detail-value {
  font-size: 16px;
  font-weight: bold;
}

/* 区域标题 */
.section-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 15px;
  color: #333;
  padding-left: 10px;
  border-left: 4px solid #3498db;
}

/* 未来天气预报 */
.forecast-section {
  background-color: white;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.forecast-list {
  display: flex;
  overflow-x: auto;
  padding-bottom: 10px;
}

.forecast-item {
  min-width: 100px;
  text-align: center;
  padding: 10px;
}

.forecast-date {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.forecast-icon {
  width: 50px;
  height: 50px;
  margin: 0 auto 10px;
}

.forecast-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.forecast-temp {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 5px;
}

.forecast-weather {
  font-size: 12px;
  color: #666;
}

/* 小时预报 */
.hourly-section {
  background-color: white;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.hourly-list {
  display: flex;
  overflow-x: auto;
  padding-bottom: 10px;
}

.hourly-item {
  min-width: 70px;
  text-align: center;
  padding: 10px;
}

.hourly-time {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.hourly-icon {
  width: 40px;
  height: 40px;
  margin: 0 auto 10px;
}

.hourly-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.hourly-temp {
  font-size: 14px;
  font-weight: bold;
}

/* 生活指数 */
.life-section {
  background-color: white;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.life-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.life-item {
  display: flex;
  align-items: center;
  padding: 10px;
  border-radius: 8px;
  background-color: #f9f9f9;
  cursor: pointer;
  transition: background-color 0.3s;
}

.life-item:hover {
  background-color: #f0f0f0;
}

.life-icon {
  width: 30px;
  height: 30px;
  margin-right: 10px;
}

.life-icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.life-name {
  font-size: 14px;
  color: #333;
  flex-grow: 1;
}

.life-level {
  font-size: 14px;
  font-weight: bold;
  color: #3498db;
}

/* 旅游建议 */
.travel-tips {
  background-color: white;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.tips-content {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

/* 生活指数详情弹窗 */
.detail-dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog-content {
  width: 90%;
  max-width: 400px;
  background-color: white;
  border-radius: 10px;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background-color: #3498db;
  color: white;
}

.dialog-title {
  font-size: 18px;
  font-weight: bold;
}

.dialog-close {
  font-size: 24px;
  cursor: pointer;
}

.dialog-body {
  padding: 20px;
}

.index-level {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 15px;
  color: #3498db;
}

.index-desc {
  font-size: 14px;
  color: #666;
  line-height: 1.6;
}

/* 响应式调整 */
@media (max-width: 600px) {
  .life-list {
    grid-template-columns: 1fr;
  }
  
  .weather-main {
    flex-direction: column;
    text-align: center;
  }
  
  .weather-icon {
    margin-right: 0;
    margin-bottom: 15px;
  }
}
</style> 