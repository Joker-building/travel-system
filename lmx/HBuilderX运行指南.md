# 悦游中国（lmx / uni-app）HBuilderX 运行指南

> 适用目录：`D:\travel-system\lmx`
> 前端工程类型：uni-app（Vue3），**必须用 HBuilderX 打开运行**，不能 `npm run dev`
> （本工程无 `scripts`、无 `vite.config.js`，`node_modules` 里也不含 `@dcloudio` 编译器，编译工具链由 HBuilderX 提供）

---

## 一、前置准备

1. **安装 HBuilderX**
   - 官网下载：https://www.dcloud.io/hbuilderx.html （选 Windows 版，建议标准版）
   - 解压/安装后直接打开即可，无需额外配置 Node（HBuilderX 自带运行环境）
2. **确保后端已启动**（前端默认连 `http://127.0.0.1:8000`）
   - 后端 CORS 已开启（`allow_origins=["*"]`），H5 浏览器可跨域直连
   - 启动命令（在 `D:\travel-system\backend` 目录下，用项目自带 venv）：
     ```
     D:\travel-system\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
     ```
   - 验证：`curl http://127.0.0.1:8000/health` 返回 `{"status":"healthy"}`
   - 依赖说明：后端依赖已装在 `D:\travel-system\venv`（详见 `D:\travel-system\venv使用说明.md`）

---

## 二、在 HBuilderX 中打开项目

1. 打开 HBuilderX → 顶部菜单 **文件 → 打开目录**
2. 选择 **`D:\travel-system\lmx`** 这一层（注意是 `lmx`，不是 `travel-system`）
   - HBuilderX 会根据 `manifest.json` + `pages.json` 自动识别为 uni-app 工程
3. 首次打开可能提示安装 **uni-app 编译** 插件：
   - 顶部菜单 **工具 → 插件安装 → 安装【uni-app 编译】/【App 真机运行】/【uni-app 运行】**（按需勾选，H5 只要有「uni-app 编译」即可）

---

## 三、确认后端地址（已解耦，多机/真机调试无需改代码）

后端地址由 `lmx/utils/config.js` 的 `getApiBaseUrl()` 运行时解析，优先级：
1. **运行时手动覆盖**（最高）：`uni.setStorageSync('API_BASE_URL', 'http://192.168.1.100:8000')`
   —— 换电脑 / 真机调试时在「我的」页或调试控制台设置一次即可，无需重新编译。
2. **环境变量**：生产包（`NODE_ENV=production`）自动走 `PROD_BASE_URL`，开发走 `DEV_BASE_URL`。
3. **开发默认** `DEV_BASE_URL = 'http://127.0.0.1:8000'`（见 `config.js` 顶部常量）。

```js
// lmx/utils/config.js
const DEV_BASE_URL = 'http://127.0.0.1:8000';        // 本机/H5 调试；真机调试改此 IP 为电脑局域网地址
const PROD_BASE_URL = 'https://travel.jasenon.xyz';   // 打包发行后自动启用
export function getApiBaseUrl() { /* 运行时按上述优先级解析 */ }
```

- **本机 H5 调试**：默认 `127.0.0.1:8000`，后端和浏览器同一台机器即可，一般不用改。
- **真机 / 多机联调**：把 `DEV_BASE_URL` 改成你电脑的局域网 IP（如 `http://192.168.1.100:8000`，手机与电脑须同一 WiFi）；
  或更推荐用运行时覆盖键 `API_BASE_URL`，连哪台后端都不用重新打包。
- 注意：H5 在浏览器运行时，页面由 HBuilderX 本地服务托管，但接口请求发往后端地址，故本机场景后端与浏览器须同机。

---

## 四、运行方式（三选一）

### 方式 A：运行到浏览器（H5，最常用，最快验证）
1. 菜单 **运行 → 运行到浏览器 → Chrome**（或你装的浏览器）
2. HBuilderX 编译后会自动打开浏览器，地址类似 `http://localhost:5173/`（端口由 HBuilderX 分配）
3. 页面加载即调用 `127.0.0.1:8000` 的接口，登录/搜索/AI 对话等功能可用

### 方式 B：运行到微信小程序
1. 先安装 **微信开发者工具**（https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html）
2. HBuilderX 菜单 **运行 → 运行到小程序模拟器 → 微信开发者工具**
3. 若提示 appid 无效，打开 `lmx/manifest.json` → `mp-weixin` 节点，把 `appid` 改成你自己的小程序 AppID（当前 `__UNI__B305ADD` 是内置测试号，仅能本地预览，不能正式发布）

### 方式 C：运行到 App（手机/模拟器）
1. 菜单 **运行 → 运行到手机或模拟器**
2. 真机需数据线连接并开启 USB 调试；模拟器需先安装（如 Android Studio 模拟器）

---

## 五、常见问题排查

| 现象 | 原因 / 解决 |
|------|------|
| 浏览器白屏、接口 404/连不上 | 后端没起，或没在 `127.0.0.1:8000`；先按「一、2」把后端跑起来 |
| 接口跨域报错 | 理论上 CORS 已开；若仍报，确认后端 `main.py` 的 `CORSMiddleware` 未被注释 |
| 地图页不显示 / 定位失败 | `utils/config.js` 里 `AMAP_CONFIG.key` 是占位符「你的高德地图API密钥」，需替换成真实高德 Key + 安全密钥 |
| 天气/翻译功能异常 | `QWEATHER_CONFIG.jwtToken` 是示例令牌可能已过期；百度翻译需按 `BAIDU_TRANSLATE_CONFIG` 配置真实 appid/key |
| 提示「缺少编译器 / 找不到 @dcloudio」 | 不要用 npm 跑；务必用 HBuilderX 打开，并确认「uni-app 编译」插件已安装 |
| 改了代码不生效 | HBuilderX 默认热更新；若异常，菜单 **运行 → 重新运行** 或重启浏览器 |

---

## 六、一句话流程（H5 快速验证）

```
1) 启动后端（127.0.0.1:8000）
2) HBuilderX 打开 D:\travel-system\lmx
3) 运行 → 运行到浏览器 → Chrome
4) 浏览器里登录 testuser / 123456 即可体验
```
