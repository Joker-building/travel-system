/**
 * 高德地图API工具
 * 提供获取位置、天气等功能
 */

import axios from 'axios';
import { AMAP_CONFIG } from '@/utils/config';

/**
 * 通过IP获取定位信息
 * @returns {Promise<Object>} 定位信息
 */
export async function getLocationByIP() {
  try {
    const response = await axios({
      method: 'get',
      url: `${AMAP_CONFIG.baseUrl}/v3/ip`,
      params: {
        key: AMAP_CONFIG.key,
        sig: generateSig(`key=${AMAP_CONFIG.key}`),
      }
    });
    
    if (response.data && response.data.status === '1') {
      return response.data;
    } else {
      console.error('获取位置信息失败:', response.data);
      return null;
    }
  } catch (error) {
    console.error('获取位置信息出错:', error);
    throw error;
  }
}

/**
 * 获取指定城市的天气信息
 * @param {string} city 城市编码，如：110101
 * @param {string} extensions 天气类型：base-返回实况天气，all-返回预报天气
 * @returns {Promise<Object>} 天气信息
 */
export async function getWeather(city, extensions = 'base') {
  try {
    const params = {
      key: AMAP_CONFIG.key,
      city,
      extensions,
      output: 'JSON'
    };
    
    const sigStr = Object.keys(params)
      .sort()
      .map(key => `${key}=${params[key]}`)
      .join('&');
    
    params.sig = generateSig(sigStr);
    
    const response = await axios({
      method: 'get',
      url: `${AMAP_CONFIG.baseUrl}/v3/weather/weatherInfo`,
      params
    });
    
    if (response.data && response.data.status === '1') {
      return response.data;
    } else {
      console.error('获取天气信息失败:', response.data);
      return null;
    }
  } catch (error) {
    console.error('获取天气信息出错:', error);
    throw error;
  }
}

/**
 * 生成签名
 * @param {string} str 待签名字符串
 * @returns {string} 签名
 */
function generateSig(str) {
  // 在实际项目中，应该使用crypto-js等库进行加密
  // 这里为了简化，返回一个占位符
  // 实际项目中应该使用：
  // return CryptoJS.MD5(str + AMAP_CONFIG.securityJsCode).toString();
  return '签名占位符';
}

export default {
  getLocationByIP,
  getWeather
}; 