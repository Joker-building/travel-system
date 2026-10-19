# AI 辅助个性化旅游行程定制系统 · 后端技术文档

> 技术栈：Python + FastAPI + MySQL + DeepSeek（大模型）+ Langchain（接入层，非 RAG）
> 版本：v1.0.0 ｜ 文档更新：2026-10-18
> 重点：**AI 能力架构**（DeepSeek 接入、意图路由、行程规划、语音识别）

---

## 1. 系统概述

后端是一个基于 **FastAPI** 的异步 Web 服务，承担三件事：

1. **业务数据层**：用户、行程、景点库的 CRUD 与持久化（MySQL + SQLAlchemy 2.0）。
2. **AI 智能层（核心）**：以 **DeepSeek** 大模型为大脑，提供对话问答、行程规划、景点语义检索、景点详情生成。
3. **外部能力代理层**：天气（和风/Open-Meteo）、地图逆地理编码（高德）、翻译（百度）经后端代理，密钥不落前端；语音识别（Vosk 本地离线 STT）。

设计原则：**AI 增强以确定性规则 + DeepSeek function calling 为核心**，保证业务链路稳定、可回退。

---

## 2. 技术栈清单

| 类别 | 技术 | 版本 / 说明 | 主要用途 |
|------|------|------------|----------|
| Web 框架 | FastAPI | 0.115.6 | 异步 REST API、依赖注入、OpenAPI 文档 |
| 服务器 | uvicorn | 0.34.0（standard） | ASGI 运行，`0.0.0.0:8000` |
| ORM | SQLAlchemy | 2.0.41 | 数据模型、会话管理 |
| 数据库驱动 | PyMySQL | 1.1.1 | MySQL 连接 |
| 数据库 | MySQL | 84（本地 3306） | 业务主库 `travel_system` |
| 大模型 | DeepSeek | `deepseek-chat`（OpenAI 兼容 `/v1/chat/completions`） | 对话、规划、详情生成 |
| AI 编排层 | Langchain | langchain 1.4.5 / langchain-openai 1.7.1 | ChatOpenAI 封装 DeepSeek + 行程规划 tool-calling 智能体（非 RAG） |
| 认证 | python-jose + passlib(bcrypt) | HS256 JWT | 用户登录态、接口鉴权 |
| HTTP 客户端 | httpx | 0.28.1 | 异步调用 DeepSeek / 天气 / 代理 |
| 配置 | pydantic-settings + python-dotenv | — | 环境变量管理 |
| 语音识别 | Vosk | small-cn-0.22（本地离线） | 语音转文字（STT），无需 API Key |
| 工具 | aiofiles / python-multipart | — | 文件上传、静态资源 |

---

## 3. 目录结构

```
backend/
├── main.py                      # 应用入口：FastAPI 实例、CORS、路由注册、静态资源
├── config.py                    # 全局配置（DB / JWT / DeepSeek / 天气 / 地图）
├── database.py                  # SQLAlchemy 引擎、Session、Base
├── models/                      # 数据模型（user / trip / trip_detail / scenic_spot / chat）
├── schemas/                     # Pydantic 请求/响应模型
├── routers/                     # 路由层（API 端点）
│   ├── auth.py                  # 注册 / 登录
│   ├── user_info.py             # 用户信息 / 头像
│   ├── trips.py                 # 行程 CRUD（含每天安排）
│   ├── ai_chat.py               # 对话主入口 + 会话管理
│   ├── ai_planning.py           # 景点搜索 / AI 详情 / 行程保存
│   ├── ai_voice.py              # 语音识别 + 语音对话
│   ├── weather.py               # 天气 forecast
│   └── proxy.py                 # 天气 / 逆地理 / 翻译代理（密钥在服务端）
├── services/                    # 业务逻辑层
│   ├── ai_service.py            # ★ AI 核心：经 langchain_layer 调用 DeepSeek、意图路由、行程规划
│   ├── langchain_layer/         # Langchain 接入层（非 RAG）
│   │   ├── llm.py               # ChatOpenAI 封装 DeepSeek（推导 base_url）
│   │   └── orchestrator.py      # to_langchain_messages + run_itinerary_agent 智能体
│   ├── scenic_service.py        # 景点库 CRUD
│   ├── trip_service.py          # 行程服务
│   ├── chat_service.py          # 会话服务
│   ├── auth_service.py          # 认证服务
│   ├── voice_service.py         # Vosk 离线 STT
│   ├── weather_service.py       # 和风优先 + Open-Meteo 兜底
│   └── proxy_service.py
├── scripts/                     # 运维脚本
│   └── backfill_scenic_fields.py# 回填景点稀疏字段
└── libs/                        # 本地 vendored 依赖（vosk / tqdm / srt）
```

---

## 4. 非 AI 业务功能（基础支撑）

| 模块 | 端点前缀 | 能力 |
|------|----------|------|
| 认证 | `/api/auth` | 注册、登录（JWT 签发，`config.py` `SECRET_KEY` / HS256） |
| 用户 | `/api/user` | 信息查询、更新、头像上传、登出 |
| 行程 | `/api/trips` | 行程增删改查、每日安排（day）增删、明细更新 |
| 景点库 | `/api/planning/scenic` | 关键词搜索（DB name/address 匹配）、按 ID 查询、加入行程 |
| 外部代理 | `/api/proxy` | 天气、高德逆地理编码、百度翻译（密钥仅服务端，防泄露） |

---

## 5. AI 能力总览（核心章节）

后端 AI 由 **「一个大脑（DeepSeek）+ 原生 function calling 编排」** 构成。

| AI 能力 | 入口 | 技术实现 | 状态 |
|--------|------|----------|------|
| 智能对话问答 | `POST /api/ai/chat` | DeepSeek + 意图路由 | ✅ 已落地 |
| 行程规划 | `AIService.chat`（plan 分支） | Langchain tool-calling 智能体（run_itinerary_agent）+ 确定性约束注入 | ✅ 已落地 |
| 景点语义搜索 | `AIService.search_scenic` | DeepSeek 生成高德式候选卡片 | ✅ 已落地 |
| 景点详情生成 | `AIService.get_scenic_detail` | DeepSeek 生成介绍/门票/预算 | ✅ 已落地 |
| 语音识别对话 | `/api/ai/voice/chat` | Vosk 离线 STT → `AIService.chat` | ✅ 已落地 |

---

## 6. AI 架构详解

### 6.1 DeepSeek 大模型接入

- **接入方式**：DeepSeek 兼容 OpenAI 协议，后端直接调用 `https://api.deepseek.com/v1/chat/completions`（`config.py`）。
- **统一封装**：`AIService.call_deepseek_api()`（`ai_service.py`）——经 `services/langchain_layer` 的 **ChatOpenAI 接入层**调用 DeepSeek（底层仍为 OpenAI 兼容协议，base_url 由 `DEEPSEEK_API_URL` 推导），支持两种模式：
  - **结构化规划**：传入 `tools` 时走 **function calling**（`bind_tools` + `tool_choice="required"`），强制模型输出可解析 JSON；
  - **自然语言问答**：否则 `bind(response_format={"type":"json_object"})`，便于稳健解析。
- **行程规划智能体**：`is_plan=True` 时不再直接走 `call_deepseek_api`，而改走 `orchestrator.run_itinerary_agent()`——通过 `bind_tools` 强制调用 `create_itinerary` 工具，并内置「空工具调用 → 强制重试一次」兜底。
- **健壮性处理**：
  - `_extract_tool_args()`：循环解包 DeepSeek 偶发的"双重 JSON 编码"参数，最多解 3 层，失败统一返回 `{}`；
  - `_extract_human_text_from_ai_raw()`：从 JSON / 双重编码 / tool_calls 中提取用户可读中文（优先级：narrative → answer → chat_title）。

### 6.2 意图路由（核心调度逻辑）

对话主入口 `AIService.chat()`（`ai_service.py`）先判断是否为「行程规划」意图，再分流到规划或通用问答：

- **plan 判定**：由确定性规则守住——`_is_plan_intent()` 匹配「规划/行程/日游/攻略」等关键词与「X天怎么玩」等句式；`_is_plan_continuer()` 识别用户用极简肯定词（需要/好的）承接上一轮 AI 的规划提议。
- **plan 安全保护**：若判定为 `plan` 但消息与历史均无目的地城市，降级为通用问答反问城市，规避"无上下文硬生成默认行程"的历史 Bug。
- **其余消息**：走通用 QA 分支（DeepSeek 直答 + 自适应历史上下文 + 天气注入）。

### 6.3 行程规划（function calling + 确定性约束注入）

`AIService.chat()` 在 `is_plan=True` 时进入规划分支，由 `services/langchain_layer/orchestrator.run_itinerary_agent()` 智能体负责工具调用，核心设计：

- **强制结构化**：智能体用 `SYSTEM_PROMPT_PLAN_TOOL` 经 `bind_tools` + `tool_choice="required"` 让 DeepSeek 必须输出结构化行程 JSON（含 `dest_city`、每日景点 `city` 等字段）；空工具调用时智能体内部强制重试一次。
- **确定性约束注入（抑制幻觉的关键）**：
  - **城市约束**：`_extract_cities()` 提取单/多城市；单城市强约束"所有景点 city 必须等于该城市"，多城市软约束"必须覆盖全部城市、每天标注所在城市"。无城市时从历史继承（`_extract_city_from_history`）。
  - **天数约束**：`_extract_days()` 提取"X 日游"，强制 `travel_days` 与标题天数一致。
- **落库**：用户确认后由 `POST /api/planning/itinerary/save` → `AIService._process_itinerary()` 保存为行程，避免自动落库产生孤儿记录。

### 6.4 景点语义搜索与详情

- **语义搜索**：`search_scenic()` 用 DeepSeek 生成高德式候选景点卡片，前端挑选后 `add-to-trip` 加入行程。
- **AI 详情**：`get_scenic_detail()` 用 DeepSeek 生成景区介绍、门票、注意事项、预算规划。

### 6.5 语音识别（Vosk 离线 STT）

- **实现**：`VoiceService`（`voice_service.py`）封装 **Vosk** 开源离线中文模型（`vosk-model-small-cn-0.22`），**无需 API Key、完全离线**，模型以 vendored 形式放 `libs/vosk` 与 `vosk_models/`。
- **链路**：`POST /api/ai/voice/chat`（`ai_voice.py`）→ Vosk 语音转文字 → `AIService.chat()` 生成回复；TTS 由前端浏览器 `speechSynthesis` 完成。

### 6.6 天气服务

`WeatherService`（`weather_service.py`）三级策略：和风天气（国内、需配置）→ Open-Meteo（境外免费兜底）→ 季节性模拟数据；任何降级都在 `warning` 字段与日志明示。主链路经 `/api/weather` 与 `/api/proxy/weather` 代理，密钥仅在服务端。

---

## 7. AI 请求数据流

```
                        ┌─────────────────────────────┐
   前端 / 语音           │        AIService.chat()      │
   ───────────────────▶ │                             │
                        └──────────────┬──────────────┘
                                       │
                       _is_plan_intent() / _is_plan_continuer()  ← 确定性规则
                                       │
            ┌──────────────────────────┴────────────────────┐
            ▼                                           ▼
      通用 QA（DeepSeek 直答）                        plan
    + 自适应历史 + 天气注入                    Langchain tool-calling 智能体 + 约束注入
                                              ↓
                                              结构化行程 JSON → _process_itinerary 落库
```

---

## 8. API 端点清单（标注 AI）

| 方法 | 路径 | AI? | 说明 |
|------|------|-----|------|
| POST | `/api/ai/chat` | ★ | 对话主入口（意图路由 → 问答/规划） |
| GET | `/api/ai/sessions` | | 会话列表 |
| GET | `/api/ai/sessions/{id}/messages` | | 会话消息历史 |
| POST | `/api/ai/sessions/create` | | 新建会话 |
| DELETE | `/api/ai/sessions/{id}` | | 删除会话 |
| POST | `/api/planning/scenic/ai-search` | ★ | AI 语义景点搜索（高德式候选） |
| POST | `/api/planning/scenic/ai-detail` | ★ | AI 生成景点详情 |
| GET | `/api/planning/scenic/search` | | 景点关键词搜索（DB 匹配） |
| POST | `/api/planning/scenic/add-to-trip` | | 景点加入行程 |
| GET | `/api/planning/scenic/{id}` | | 按 ID 查景点 |
| POST | `/api/planning/itinerary/save` | ★ | 保存 AI 规划行程 |
| POST | `/api/ai/voice/stt` | ★ | Vosk 语音转文字 |
| POST | `/api/ai/voice/chat` | ★ | 语音对话（STT → AI 回复） |
| GET | `/api/ai/voice/status` | | 语音服务状态 |
| GET | `/api/weather/forecast` | 🟡 | 天气（和风/Open-Meteo） |
| GET | `/api/proxy/weather` ` /regeo` ` /translate` | | 外部能力代理（密钥服务端） |
| POST/GET | `/api/auth/*` `/api/user/*` `/api/trips/*` | | 认证 / 用户 / 行程 CRUD |

---

## 9. 关键配置开关（`config.py`）

| 配置项 | 默认值 | 作用 |
|--------|--------|------|
| `DEEPSEEK_*` | api.deepseek.com/v1 | 模型名、API Key、API URL |
| `QWEATHER_*` / `AMAP_KEY` / `BAIDU_TRANSLATE_*` | — | 天气/地图/翻译密钥（仅服务端） |

---

## 10. 依赖与运维脚本

- **核心依赖**：`requirements.txt`（已与 `.venv` 逐条核对一致）。
- **启动**：`uvicorn main:app --host 0.0.0.0 --port 8000 --reload`（开发），生产关 `APP_DEBUG`。
- **文档**：`/docs`（Swagger）、`/redoc`。

---

## 11. 关键设计决策与备注

1. **抑制幻觉两条线**：① 行程规划 function calling + 城市/天数确定性约束注入；② 景点搜索由 DeepSeek 生成候选卡片并落库，避免凭记忆编造 POI。
2. **语音离线化**：Vosk 本地 STT 避免云端语音 API 的 Key 与网络依赖。
3. **密钥隔离**：所有第三方密钥（天气/地图/翻译）仅在服务端 `config.py` 与 `.env` 保存，前端经 `/api/proxy` 代理访问。
4. **Langchain 仅作接入 / 编排层（非 RAG）**：以 `ChatOpenAI` 封装 DeepSeek、以 `run_itinerary_agent` 智能体编排行程规划 tool-calling；**不含任何向量检索 / 知识库逻辑**，RAG 专属依赖（langchain-postgres / langchain-ollama / pgvector / psycopg）已卸载。
