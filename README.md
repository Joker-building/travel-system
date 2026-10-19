# 悦游中国 · AI 辅助个性化旅游行程定制系统

> 一个以 **DeepSeek 大模型** 为大脑的旅游行程定制应用：用户用一句话描述目的地、天数、预算和偏好，系统自动生成可落库、可编辑、可分享的逐日行程，并支持 AI 对话问答、景点搜索与详情生成、语音交互、天气与地图代理。

前端为 **uni-app（Vue 3）** 移动端应用，后端为 **FastAPI + MySQL** 异步服务。

---

## 目录

- [核心功能](#核心功能)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [目录结构](#目录结构)
- [快速开始](#快速开始)
- [环境变量](#环境变量)
- [API 一览](#api-一览)
- [AI 能力设计](#ai-能力设计)
- [常见问题](#常见问题)

---

## 核心功能

| 模块 | 说明 |
|------|------|
| 账号体系 | 注册 / 登录（JWT + bcrypt），头像上传、个人资料编辑 |
| AI 对话 | 多轮对话、会话管理，支持日常问答与「帮我规划行程」意图切换 |
| AI 行程规划 | 从自然语言中抽取 **城市 / 天数 / 预算 / 偏好**，生成逐日行程并结构化落库 |
| 行程管理 | 行程列表、详情、逐日安排增删改，支持手动微调 AI 结果 |
| 景点能力 | 关键词 + 城市检索景点候选（高德式卡片），AI 生成景点详情与玩法建议 |
| 语音交互 | 本地离线语音识别（Vosk small-cn），语音输入转文字后走对话链路 |
| 天气服务 | 和风天气实时 / 预报，按行程城市与日期展示 |
| 第三方代理 | 天气、逆地理编码、翻译统一由后端代理，**密钥不落前端** |

---

## 技术栈

### 后端

| 类别 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | 0.115.6 |
| ASGI 服务器 | uvicorn[standard] | 0.34.0 |
| ORM | SQLAlchemy | 2.0.41 |
| 数据库 | MySQL + PyMySQL | 8.x / 1.1.1 |
| 大模型 | DeepSeek `deepseek-chat`（OpenAI 兼容接口） | — |
| AI 编排层 | Langchain / langchain-openai（ChatOpenAI 封装 + tool-calling） | 1.4.5 / 1.7.1 |
| 认证 | python-jose + passlib[bcrypt] | 3.3.0 / 1.7.4 |
| HTTP 客户端 | httpx | 0.28.1 |
| 语音识别 | Vosk（本地 vendored，随仓库提供） | small-cn-0.22 |

### 前端

| 类别 | 技术 |
|------|------|
| 框架 | uni-app（Vue 3） |
| 运行方式 | **HBuilderX**（工程无 vite 配置，不能 `npm run dev`） |
| 页面 | 登录 / 个人信息 / 行程列表 / 行程详情 / AI 生成 |
| 能力 | 请求封装、token 鉴权、语音录制、天气工具、地图逆地理 |

---

## 系统架构

```
uni-app 客户端 (lmx/)
        │  HTTP / JSON（Bearer Token）
        ▼
FastAPI 后端 (backend/, 0.0.0.0:8000)
 ├── routers/   路由层：auth / trips / ai_chat / ai_planning / ai_voice / weather / proxy / user_info
 ├── services/  业务层：ai_service（AI 核心）/ trip_service / scenic_service / voice_service / weather_service / proxy_service
 │     └── langchain_layer/  ChatOpenAI 封装 DeepSeek + 行程规划 tool-calling 智能体
 ├── models/    SQLAlchemy 模型：user / trip / trip_detail / scenic_spot / chat
 └── schemas/   Pydantic 请求响应模型
        │
        ├── MySQL（业务主库 travel_system）
        └── 外部服务：DeepSeek API / 和风天气 / 高德地图 / 百度翻译
```

**设计原则**：AI 增强以「确定性规则 + function calling」为核心 —— 城市、天数、预算等硬约束由服务端规则抽取并注入提示词，模型只负责内容生成，保证链路稳定、可回退、可落库。

---

## 目录结构

```
travel-system/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 应用入口：CORS、静态资源、路由注册
│   ├── config.py               # 全局配置（从 .env 读取）
│   ├── database.py             # SQLAlchemy 引擎 / Session / Base
│   ├── .env.example            # 环境变量模板
│   ├── requirements.txt        # 核心依赖
│   ├── BACKEND.md              # 后端技术文档（详细）
│   ├── routers/                # API 路由
│   ├── services/               # 业务逻辑（ai_service.py 为 AI 核心）
│   ├── models/                 # 数据模型
│   ├── schemas/                # Pydantic 模型
│   ├── scripts/                # 运维脚本（回填字段 / 清洗城市名等）
│   ├── libs/                   # vendored 依赖（vosk 语音识别）
│   ├── vosk_models/            # 离线中文语音模型
│   └── postman/                # Postman 接口集合与测试音频
├── lmx/                        # uni-app 前端
│   ├── pages/                  # 登录 / 我的 / 行程 / AI 生成
│   ├── api/                    # 接口封装
│   ├── utils/                  # config（BASE_URL 解析）/ request / auth / voice
│   ├── manifest.json           # uni-app 应用配置
│   └── HBuilderX运行指南.md     # 前端运行详细步骤
└── README.md
```

---

## 快速开始

### 0. 前置条件

- Python 3.10+
- MySQL 8.x（本地 3306）
- HBuilderX（前端编译运行，需安装「uni-app 编译」插件）
- DeepSeek API Key（[platform.deepseek.com](https://platform.deepseek.com)）

### 1. 初始化数据库

```sql
CREATE DATABASE travel_system DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

数据表由后端启动时 `Base.metadata.create_all()` 自动创建，无需手工建表。

### 2. 启动后端

```bash
cd backend

# 安装依赖（国内镜像）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 配置环境变量
cp .env.example .env      # 然后填写 DB_PASSWORD / DEEPSEEK_API_KEY 等

# 启动服务
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

验证：

```bash
curl http://127.0.0.1:8000/health     # {"status":"healthy"}
```

交互式 API 文档：<http://127.0.0.1:8000/docs>

### 3. 启动前端

1. HBuilderX → **文件 → 打开目录** → 选择 `lmx/`（不是仓库根目录）
2. 首次打开按提示安装「uni-app 编译」插件
3. 顶部 **运行 → 运行到浏览器 → Chrome**（或运行到手机模拟器 / 真机）

> 前端默认请求 `http://127.0.0.1:8000`。真机或多机联调无需改代码，在调试控制台执行一次即可覆盖：
> ```js
> uni.setStorageSync('API_BASE_URL', 'http://192.168.x.x:8000')
> ```
> 详细步骤见 [`lmx/HBuilderX运行指南.md`](lmx/HBuilderX运行指南.md)。

---

## 环境变量

复制 `backend/.env.example` 为 `backend/.env`，按下表填写：

| 变量 | 必填 | 说明 |
|------|:---:|------|
| `DB_TYPE` | ✅ | `mysql`（默认）或 `sqlite` |
| `DB_HOST` / `DB_PORT` | ✅ | 默认 `localhost:3306` |
| `DB_USER` / `DB_PASSWORD` | ✅ | MySQL 账号密码 |
| `DB_NAME` | ✅ | 默认 `travel_system` |
| `SECRET_KEY` | ✅ | JWT 签名密钥，生产环境务必改为随机长串 |
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek 密钥，未配置则 AI 相关接口不可用 |
| `DEEPSEEK_API_URL` | — | 默认 `https://api.deepseek.com/v1/chat/completions` |
| `DEEPSEEK_MODEL` | — | 默认 `deepseek-chat` |
| `QWEATHER_HOST` / `QWEATHER_KEY` | — | 和风天气，缺失时天气模块降级 |
| `AMAP_KEY` | — | 高德地图，用于逆地理编码 |
| `BAIDU_TRANSLATE_APPID` / `BAIDU_TRANSLATE_KEY` | — | 百度翻译 |
| `APP_HOST` / `APP_PORT` | — | 默认 `0.0.0.0:8000` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | 默认 1440（24 小时） |

> `.env` 已在 `.gitignore` 中，**不要提交密钥**。

---

## API 一览

| 前缀 | 模块 | 主要端点 |
|------|------|----------|
| `/api/auth` | 认证 | `POST /register`、`POST /login` |
| `/api/user` | 用户信息 | `GET /info`、`PUT /update`、`POST /avatar/upload`、`POST /logout` |
| `/api/trips` | 行程管理 | `GET /list`、`POST /create`、`GET /detail/{trip_id}`、`PUT /update/{trip_id}`、`DELETE /delete/{trip_id}`、`PUT /detail/update/{detail_id}`、`POST /day/add`、`POST /day/delete` |
| `/api/ai` | AI 对话 | `POST /chat`、`GET /sessions`、`GET /sessions/{id}/messages`、`POST /sessions/create` |
| `/api/ai/voice` | 语音 | `POST /stt`（语音转文字）、`POST /chat`（语音对话）、`GET /status` |
| `/api/planning` | AI 规划 | `GET /scenic/search`、`POST /scenic/ai-search`、`POST /scenic/ai-detail`、`POST /scenic/add-to-trip`、`POST /itinerary/save` |
| `/api/weather` | 天气 | `GET /forecast` |
| `/api/proxy` | 第三方代理 | `GET /weather`、`GET /regeo`、`GET /translate`（服务端持钥） |

完整参数与响应示例见 `backend/postman/travel-system.postman_collection.json`，或运行时访问 `/docs`。

---

## AI 能力设计

1. **意图判定**：`_is_plan_intent()` / `_is_plan_continuer()` 区分「闲聊问答」与「行程规划」，并支持在已规划上下文中的补充追问。
2. **约束抽取**：城市、天数、预算由 `_extract_*` 系列规则方法从用户输入 + 历史上下文中抽取，作为硬约束注入提示词，避免模型自由发挥导致行程不可用。
3. **智能体编排**：行程规划走 Langchain tool-calling 智能体（`langchain_layer/orchestrator.run_itinerary_agent`），`tool_choice="required"` 强制结构化输出，并对空工具调用做重试兜底。
4. **结构化落库**：模型输出经 `parse_json_response()` 容错解析后，由 `_process_itinerary()` 写入 `trip` / `trip_detail`，同步维护 `scenic_spot` 景点库。
5. **景点检索**：`search_scenic()` 生成高德式候选卡片，`get_scenic_detail()` 补充游玩亮点、开放信息与建议时长。

> 设计取舍：当前 AI 链路为「规则约束 + DeepSeek function calling」，未引入 RAG / 向量检索。景点知识来自 `scenic_spot` 表结构化数据与模型自身能力，优点是无额外数据库依赖、链路稳定可回退；若后续需要私有语料问答，再单独评估检索增强方案。

---

## 常见问题

**Q：`uvicorn` 启动后立刻崩溃 / 循环导入？**
SQLAlchemy 需 ≥ 2.0.37（`requirements.txt` 已锁定 2.0.41），旧版本在 uvicorn 热重载下存在 C 扩展导入崩溃问题。

**Q：前端报跨域错误？**
后端已设置 `allow_origins=["*"]`；仍失败时检查请求地址是否为后端实际监听的 IP 与端口，而非 `localhost` 与 `127.0.0.1` 混用。

**Q：AI 相关接口返回 500？**
优先检查 `.env` 中 `DEEPSEEK_API_KEY` 是否有效、账户余额是否充足，以及服务器能否访问 `api.deepseek.com`。

**Q：语音功能不可用？**
确认 `backend/libs/vosk` 与 `backend/vosk_models/vosk-model-small-cn-0.22` 均在位；Vosk 为本地离线模型，不需要任何 API Key。

**Q：天气 / 地图数据为空？**
对应第三方 Key 缺失时接口会降级返回空数据。和风天气的自定义 API Host 必须与其订阅绑定，否则返回 401/403。

---

## 相关文档

- [`backend/BACKEND.md`](backend/BACKEND.md) — 后端架构、模块职责、接口与 AI 链路细节
- [`lmx/HBuilderX运行指南.md`](lmx/HBuilderX运行指南.md) — 前端运行与联调步骤
- `backend/postman/` — Postman 接口集合、测试音频与样例图片
