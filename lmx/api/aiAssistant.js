import { getToken } from '@/utils/auth'
import request from '@/utils/request'
import { API_CONFIG } from '@/utils/config'

/**
 * 发送聊天消息并接收响应
 * @param {string} message - 用户发送的消息
 * @param {string} sessionId - 当前会话ID，用于维持对话上下文（可选，首次对话可为空）
 * @param {Function} onProgress - 当使用非流式输出时，此参数仅在最终结果返回时被调用一次
 * @returns {Promise<Object>} - 返回响应结果
 */
export const sendChatMessage = (message, sessionId, onProgress) => {
  return new Promise((resolve, reject) => {
    try {
      // 构建请求数据，sessionId字段用于维持对话上下文
      const requestData = { 
        message,
        sessionId: sessionId || '' // 首次对话可为空，后续对话应传入服务端返回的sessionId
      };
      
      console.log('发送聊天请求');
      console.log('请求参数:', JSON.stringify(requestData));
      
      // 获取认证Token
      const token = getToken();

      // 设置请求头
      const header = {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
        // 移除Accept: text/event-stream，因为不再使用流式响应
      };
      
      if (token) {
        header['Authorization'] = `Bearer ${token}`;
        console.log('已添加认证Token到请求头');
      } else {
        console.log('未找到认证Token');
      }
      
      // 构建API URL - 从流式改为非流式接口
      const apiUrl = 'https://travel.jasenon.xyz/user/chat/send';
      // const apiUrl = 'http://192.168.0.8:8002/user/chat/send';
      // 使用uni.request发送标准请求
      uni.request({
        url: apiUrl,
        method: 'POST',
        header,
        data: requestData,
        timeout: 600000, // 60秒超时
        success: (res) => {
          try {
            if (res.statusCode !== 200) {
              throw new Error(`HTTP错误! 状态码: ${res.statusCode}`);
            }
            
            console.log('收到聊天响应，状态码:', res.statusCode);
            
            // 处理响应数据
            let responseContent = '';
            let responseData = null;
            
            if (res.data) {
              if (typeof res.data === 'object') {
                responseData = res.data;
                
                // 检查API返回的状态码
                if (responseData.code !== undefined && responseData.code !== 200) {
                  const errorMsg = responseData.message || '服务器返回错误';
                  console.error(`API错误: 代码 ${responseData.code}, 消息: ${errorMsg}`);
                  throw new Error(errorMsg);
                }
                
                // 从响应中提取消息内容
                if (responseData.data !== undefined) {
                  responseContent = responseData.data; // 直接使用data字段作为响应内容
                } else if (responseData.message !== undefined) {
                  responseContent = responseData.message; // 后备使用message字段
                }
              } else if (typeof res.data === 'string') {
                // 如果直接返回字符串，则直接使用
                responseContent = res.data;
                try {
                  // 尝试解析为JSON
                  const parsedData = JSON.parse(res.data);
                  if (parsedData && typeof parsedData === 'object') {
                    responseData = parsedData;
                    if (parsedData.data !== undefined) {
                      responseContent = parsedData.data;
                    } else if (parsedData.message !== undefined && parsedData.code === 200) {
                      responseContent = parsedData.message;
                    }
                  }
                } catch (e) {
                  // 解析失败，使用原始字符串
                  console.log('响应不是有效的JSON，使用原始字符串');
                }
              }
            }
            
            if (!responseContent && responseData && responseData.message) {
              responseContent = responseData.message;
            }
            
            // 如果还是没有内容，使用默认消息
            if (!responseContent) {
              responseContent = '抱歉，我没有获取到有效回复。';
              console.warn('从响应中未能提取到有效内容');
            }
            
            // 构建统一的响应格式
            const finalResponse = {
              content: responseContent,
              sessionId: responseData && responseData.sessionId ? responseData.sessionId : '',
              hasRecommendation: false, // 非流式响应通常不包含推荐
              recommendation: null
            };
            
            // 调用进度回调，模拟流式输出的最终结果
            if (onProgress) {
              onProgress({
                content: responseContent,
                hasRecommendation: false,
                recommendation: null,
                isComplete: true
              });
            }
            
            // 完成请求
            resolve(finalResponse);
            
          } catch (error) {
            console.error('处理聊天响应出错:', error);
            
            // 显示错误消息
            const errorMessage = error.message || '处理响应时发生错误，请稍后再试。';
            
            if (onProgress) {
              onProgress({
                content: errorMessage,
                hasRecommendation: false,
                recommendation: null,
                isComplete: true
              });
            }
            
            reject(error);
          }
        },
        fail: (err) => {
          console.error('聊天请求失败:', err);
          
          // 构建错误响应
          const errorMessage = err.errMsg || '网络请求失败，请检查您的网络连接。';
          
          if (onProgress) {
            onProgress({
              content: errorMessage,
              hasRecommendation: false,
              recommendation: null,
              isComplete: true
            });
          }
          
          reject(err);
        }
      });
    } catch (error) {
      console.error('发送聊天请求出错:', error);
      
      if (onProgress) {
        onProgress({
          content: '发送消息时发生错误，请稍后再试。',
          hasRecommendation: false,
          recommendation: null,
          isComplete: true
        });
      }
      
      reject(error);
    }
  });
};

/**
 * 创建AI旅行计划
 * @param {Object} planInfo - 旅行计划信息
 * @returns {Promise<Object>} - 返回响应结果
 */
export const createTravelPlan = (planInfo) => {
  try {
    console.log('创建旅行计划，请求参数:', JSON.stringify(planInfo));
    
    return request({
      url: '/user/travel-plans',
      method: 'POST',
      data: planInfo
    });
  } catch (error) {
    console.error('准备创建旅行计划请求出错:', error);
    return Promise.reject(error);
  }
};

/**
 * 获取旅行计划列表
 * @returns {Promise<Array>} - 返回旅行计划列表
 */
export const getTravelPlans = () => {
  try {
    console.log('获取旅行计划列表');
    
    return request({
      url: '/user/travel-plans',
      method: 'GET'
    });
  } catch (error) {
    console.error('准备获取旅行计划列表请求出错:', error);
    return Promise.reject(error);
  }
};

/**
 * 获取用户行程计划列表
 * @returns {Promise<Array>} - 返回用户行程计划列表
 */
export const getUserPlanList = () => {
  try {
    console.log('开始调用获取用户行程计划列表API');
    
    return request({
      url: '/user/plan/list',
      method: 'GET'
    }).then(response => {
      console.log('用户行程计划列表API调用成功');
      // 打印响应的关键信息但不包含完整内容，避免日志过大
      if (response && response.data) {
        if (Array.isArray(response.data)) {
          console.log(`获取到${response.data.length}条行程数据`);
        } else if (response.data.data && Array.isArray(response.data.data)) {
          console.log(`获取到${response.data.data.length}条行程数据`);
        }
      }
      return response;
    }).catch(error => {
      console.error('获取用户行程计划列表API调用失败:', error);
      throw error;
    });
  } catch (error) {
    console.error('准备获取用户行程计划列表请求出错:', error);
    return Promise.reject(error);
  }
};

/**
 * 获取旅行计划详情
 * @param {string} planId - 旅行计划ID
 * @returns {Promise<Object>} - 返回旅行计划详情
 */
export const getTravelPlanDetail = (planId) => {
  try {
    if (!planId) {
      const error = new Error('计划ID不能为空');
      console.error(error);
      return Promise.reject(error);
    }
    
    console.log('获取旅行计划详情，ID:', planId);
    
    return request({
      url: `/user/travel-plans/${planId}`,
      method: 'GET'
    });
  } catch (error) {
    console.error('准备获取旅行计划详情请求出错:', error);
    return Promise.reject(error);
  }
};

/**
 * 获取特定行程计划详情
 * @param {string|number} planId - 行程计划ID
 * @returns {Promise<Object>} - 返回行程计划详情
 */
export const getTripPlanDetail = (planId) => {
  try {
    if (!planId) {
      const error = new Error('行程计划ID不能为空');
      console.error(error);
      return Promise.reject(error);
    }
    
    console.log(`开始调用获取行程计划详情API, ID: ${planId}`);
    
    return request({
      url: `/user/plan/${planId}`,
      method: 'GET'
    }).then(response => {
      console.log('行程计划详情API调用成功');
      
      // 记录响应数据结构但不打印完整内容
      if (response && response.data) {
        if (typeof response.data === 'object') {
          console.log('响应数据包含的字段:', Object.keys(response.data).join(', '));
          
          if (response.data.data && typeof response.data.data === 'object') {
            console.log('data字段包含的字段:', Object.keys(response.data.data).join(', '));
            
            // 特别检查plan字段
            if (response.data.data.plan) {
              console.log('包含plan字段，长度:', response.data.data.plan.length);
            }
          }
        }
      }
      
      return response;
    }).catch(error => {
      console.error(`获取行程计划详情API调用失败, ID: ${planId}, 错误:`, error);
      throw error;
    });
  } catch (error) {
    console.error('准备获取行程计划详情请求出错:', error);
    return Promise.reject(error);
  }
};

export default {
  sendChatMessage,
  createTravelPlan,
  getTravelPlans,
  getTravelPlanDetail,
  getUserPlanList,
  getTripPlanDetail
}; 