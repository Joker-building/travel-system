import request from '@/utils/request';

// 日志前缀
const LOG_PREFIX = '【城市API】';

/**
 * 获取城市信息
 * @param {string} cityName - 城市名称
 * @returns {Promise} 返回城市信息的Promise对象
 */
export function getCityInfo(cityName) {
  console.log(`${LOG_PREFIX} 获取城市信息 API 调用:`, cityName);
  return request({
    url: '/city/info',
    method: 'get',
    params: {
      city_name: cityName
    }
  }).then(response => {
    console.log(`${LOG_PREFIX} 城市信息 API 返回:`, response);
    
    // 处理简化的数据结构，确保返回的数据格式一致
    if (response.code === 200 && response.data) {
      // 检查是否是简化数据结构
      if (response.data.city_name && !response.data.location) {
        console.log(`${LOG_PREFIX} 检测到简化数据结构，保持原样返回，由页面处理默认值`);
      }
    }
    
    return response;
  }).catch(error => {
    console.error(`${LOG_PREFIX} 城市信息 API 错误:`, error);
    throw error;
  });
}

/**
 * 获取所有支持的城市列表
 * @returns {Promise} 返回支持城市列表的Promise对象
 */
export function getSupportedCities() {
  console.log(`${LOG_PREFIX} 获取支持的城市列表 API 调用`);
  return request({
    url: '/city/supported',
    method: 'get'
  }).then(response => {
    console.log(`${LOG_PREFIX} 支持的城市列表 API 返回:`, response);
    return response;
  }).catch(error => {
    console.error(`${LOG_PREFIX} 支持的城市列表 API 错误:`, error);
    throw error;
  });
}

/**
 * 获取当前位置
 * @returns {Promise<{latitude: number, longitude: number, city: string|undefined}>} 位置信息
 */
export function getLocation() {
  console.log(`${LOG_PREFIX} 开始获取当前位置信息`);
  return new Promise((resolve, reject) => {
    // 添加超时处理
    let isResolved = false;
    const timeout = setTimeout(() => {
      if (!isResolved) {
        isResolved = true;
        // 武汉市默认位置
        console.log(`${LOG_PREFIX} 位置获取超时，使用武汉市默认位置`);
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
          console.log(`${LOG_PREFIX} 成功获取位置信息:`, res);
          resolve({
            latitude: res.latitude,
            longitude: res.longitude
          });
        }
      },
      fail: (err) => {
        clearTimeout(timeout);
        console.error(`${LOG_PREFIX} 获取位置失败:`, err);
        
        if (!isResolved) {
          isResolved = true;
          // 武汉市默认位置
          console.log(`${LOG_PREFIX} 位置获取失败，使用武汉市默认位置`);
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
 * 根据经纬度获取城市名称
 * @param {number} longitude - 经度
 * @param {number} latitude - 纬度
 * @returns {Promise<string>} 城市名称
 */
export function getCityNameByCoords(longitude, latitude) {
  console.log(`${LOG_PREFIX} 开始通过经纬度[${longitude},${latitude}]获取城市名称`);
  return new Promise((resolve, reject) => {
    // 经由后端代理（密钥仅在服务端），避免高德 Key 暴露在前端
    request({
      url: '/api/proxy/regeo',
      method: 'GET',
      data: {
        location: `${longitude},${latitude}`
      }
    }).then((res) => {
      const city = res.data && res.data.data && res.data.data.city;
      if (city) {
        console.log(`${LOG_PREFIX} 解析到的城市名称:`, city);
        resolve(city);
      } else {
        const msg = (res.data && res.data.message) || '获取城市名称失败';
        console.error(`${LOG_PREFIX} 代理返回错误:`, msg);
        reject(new Error(msg));
      }
    }).catch((error) => {
      console.error(`${LOG_PREFIX} 请求城市名称代理失败:`, error);
      reject(error);
    });
  });
}

/**
 * 获取当前位置城市信息
 * 自动获取位置并转换为城市名称，再获取城市详情
 * @param {Array} supportedCities - 支持的城市列表（可选）
 * @returns {Promise<Object>} 城市信息对象
 */
export async function getCurrentCityInfo(supportedCities = []) {
  console.log(`${LOG_PREFIX} 开始获取当前位置城市信息`, supportedCities.length > 0 ? `(已提供${supportedCities.length}个支持的城市)` : '');
  try {
    // 获取位置信息
    console.log(`${LOG_PREFIX} 1. 获取位置信息`);
    const locationInfo = await getLocation();
    console.log(`${LOG_PREFIX} 获取到位置:`, locationInfo);
    
    let cityName = '';
    
    // 如果已经有城市名称，直接使用
    if (locationInfo.city) {
      cityName = locationInfo.city;
      console.log(`${LOG_PREFIX} 位置中已包含城市名称:`, cityName);
      
      if (supportedCities.length > 0 && !isSupportedCity(cityName, supportedCities)) {
        console.warn(`${LOG_PREFIX} 城市不在支持列表中:`, cityName);
        // 返回一个只包含城市名称的基础数据，而不是抛出错误
        return {
          code: 200,
          message: '城市暂不支持详细数据',
          data: {
            city_name: cityName
          }
        };
      }
      
      console.log(`${LOG_PREFIX} 2. 直接使用位置中的城市名称获取城市信息`);
      return await getCityInfo(cityName);
    }
    
    // 根据经纬度获取城市名称
    console.log(`${LOG_PREFIX} 2. 通过经纬度获取城市名称`);
    cityName = await getCityNameByCoords(locationInfo.longitude, locationInfo.latitude);
    
    // 检查是否支持该城市
    if (supportedCities.length > 0 && !isSupportedCity(cityName, supportedCities)) {
      console.warn(`${LOG_PREFIX} 城市不在支持列表中:`, cityName);
      // 返回一个只包含城市名称的基础数据，而不是抛出错误
      return {
        code: 200,
        message: '城市暂不支持详细数据',
        data: {
          city_name: cityName
        }
      };
    }
    
    // 获取城市详情信息
    console.log(`${LOG_PREFIX} 3. 获取城市详情信息`);
    return await getCityInfo(cityName);
  } catch (error) {
    console.error(`${LOG_PREFIX} 获取当前城市信息失败:`, error);
    // 返回一个错误响应，但保持与API一致的结构
    return {
      code: 500,
      message: error.message || '获取城市信息失败',
      data: {
        city_name: '未知城市'
      }
    };
  }
}

/**
 * 检查是否是支持的城市
 * @param {string} cityName - 城市名称
 * @param {Array} supportedCities - 支持的城市列表
 * @returns {boolean} 是否支持
 */
function isSupportedCity(cityName, supportedCities) {
  const isSupported = supportedCities.some(city => city.name === cityName);
  console.log(`${LOG_PREFIX} 检查城市${cityName}是否支持:`, isSupported ? '支持' : '不支持');
  return isSupported;
} 