# 模拟服务器配置

这个目录包含模拟服务器的配置文件，用于本地开发时模拟后端API响应。

## 文件说明

- `mock.js`: 主要配置文件，定义了模拟API的路由和响应
  
## 接口说明

### 天气Token刷新
- **URL**: `/weather/refresh`
- **Method**: GET
- **响应**: 
  ```json
  {
    "code": 200,
    "message": null,
    "data": {
      "token": "eyJraWQiOiJUNDVGNUE3NVg5IiwiYWxnIjoiRWREU0EifQ.eyJzdWIiOiIyODhBR1FYNjROIiwiZXhwIjoxNzQ2Mjc5NjU2LCJpYXQiOjE3NDYyNzg3MjZ9.0wmVYXYiayPK_wfM7SNZnl8Bs9ODx94Kk9wqxrqHpp__HsI627YQhalWNJkG_hOuaEiFo_PEGG0DuJWfH60sAQ"
    }
  }
  ```

## 使用说明

这个模拟服务器配置可以与各种前端开发服务器集成，如webpack-dev-server、vue-cli等。在实际项目中，可以通过配置代理将请求转发到这个模拟服务器。 