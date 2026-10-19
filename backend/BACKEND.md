# AI 辅助个性化旅游行程定制系统 · 后端技术文档

> 技术栈：Python + FastAPI + MySQL + DeepSeek（大模型）+ Langchain + pgvector
> 版本：v1.0.0 ｜ 文档更新：2026-10-18
> 重点：**AI 能力架构**（DeepSeek 接入、意图路由、RAG 检索增强、行程规划、语音识别）

---

## 1. 系统概述

后端是一个基于 **FastAPI** 的异步 Web 服务，承担三件事：

1. **业务数据层**：用户、行程、景点库的 CRUD 与持久化（MySQL + SQLAlchemy 2.0）。
2. **AI 智能层（核心）**：以 **DeepSeek** 大模型为大脑，提供对话问答、行程规划、景点语义检索、景点详情生成；并基于 **Langchain + pgvector** 构建 RAG 检索增强，抑制大模型"编造景点/编造事实"的幻觉。
3. **外部能力代理层**：天气（和风/Open-Meteo）、地图逆地理编码（高德）、翻译（百度）经后端代理，密钥不落前端；语音识别（Vosk 本地离线 STT）。

设计原则：**RAG 与 AI 增强默认以开关保护，关闭时完全回退到原始工程行为**，保证已完成的业务链路不受任何影响（`config.py:50` `USE_RAG` 默认 `False`）。

---

## 2. 技术栈清单

| 类别 | 技术 | 版本 / 说明 | 主要用途 |
|------|------|------------|----------|
| Web 框架 | FastAPI | 0.115.6 | 异步 REST API、依赖注入、OpenAPI 文档 |
| 服务器 | uvicorn | 0.34.0（standard） | ASGI 运行，`0.0.0.0:8000` |
| ORM | SQLAlchemy | 2.0.41 | 数据模型、会话管理 |
| 数据库驱动 | PyMySQL | 1.1.1 | MySQL 连接 |
| 数据库 | MySQL | 84（本地 3306） | 业务主库 `travel_system` |
| 向量库 | PostgreSQL + pgvector | 17 / 0.8.0 | RAG 向量索引 `vector_db`，集合 `travel_kb` |
| 大模型 | DeepSeek | `deepseek-chat`（OpenAI 兼容 `/v1/chat/completions`） | 对话、规划、详情生成 |
| LLM 编排 | Langchain | 1.4.5 | RAG 问答链（LCEL）、tool-calling 智能体 |
| 向量检索 | langchain-postgres (PGVector) | 0.0.19 | PGVector 检索器（psycopg3 驱动） |
| Embedding | bge-m3（本地） | 维度 1024 | 经 **Ollama** 本地推理，零联网 |
| 认证 | python-jose + passlib(bcrypt) | HS256 JWT | 用户登录态、接口鉴权 |
| HTTP 客户端 | httpx | 0.28.1 | 异步调用 DeepSeek / 天气 / 代理 |
| 配置 | pydantic-settings + python-dotenv | — | 环境变量管理 |
| 语音识别 | Vosk | small-cn-0.22（本地离线） | 语音转文字（STT），无需 API Key |
| 工具 | aiofiles / python-multipart | — | 文件上传、静态资源 |

> RAG 相关依赖（langchain 1.x 栈、pgvector、psycopg3、langchain-ollama）单独维护在 `requirements_rag.txt`，与核心依赖隔离（`requirements.txt:11-13`）。

---

## 3. 目录结构

```
backend/
├── main.py                      # 应用入口：FastAPI 实例、CORS、路由注册、静态资源
├── config.py                    # 全局配置（DB / JWT / DeepSeek / RAG / 天气 / 地图）
├── database.py                  # SQLAlchemy 引擎、Session、Base
├── models/                      # 数据模型（user / trip / trip_detail / scenic_spot / knowledge_doc / chat）
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
│   ├── ai_service.py            # ★ AI 核心：DeepSeek 调用、意图路由、行程规划、RAG 集成
│   ├── scenic_service.py        # 景点库 CRUD
│   ├── trip_service.py          # 行程服务
│   ├── chat_service.py          # 会话服务
│   ├── auth_service.py          # 认证服务
│   ├── voice_service.py         # Vosk 离线 STT
│   ├── weather_service.py       # 和风优先 + Open-Meteo 兜底
│   ├── langchain_layer/         # ★ Langchain 编排层
│   │   ├── llm.py               # DeepSeek 的 ChatOpenAI 封装
│   │   └── orchestrator.py      # RAG 问答链（LCEL）+ tool-calling 智能体
│   ├── rag/                     # ★ RAG 检索层
│   │   └── vector_store.py      # PGVector 索引构建 / 检索 / 过滤
│   └── proxy_service.py
├── scripts/                     # 运维脚本
│   ├── build_scenic_index.py    # 从 DB 全量建/重建向量索引
│   ├── seed_knowledge_corpus.py # 灌入 starter 知识语料
│   └── backfill_scenic_fields.py# 回填景点稀疏字段
└── libs/                        # 本地 vendored 依赖（vosk / tqdm / srt）
```

---

## 4. 非 AI 业务功能（基础支撑）

| 模块 | 端点前缀 | 能力 |
|------|----------|------|
| 认证 | `/api/auth` | 注册、登录（JWT 签发，`config.py:35` `SECRET_KEY` / HS256） |
| 用户 | `/api/user` | 信息查询、更新、头像上传、登出 |
| 行程 | `/api/trips` | 行程增删改查、每日安排（day）增删、明细更新 |
| 景点库 | `/api/planning/scenic` | 关键词搜索（DB name/address 匹配）、按 ID 查询、加入行程 |
| 外部代理 | `/api/proxy` | 天气、高德逆地理编码、百度翻译（密钥仅服务端，防泄露） |

---

## 5. AI 能力总览（核心章节）

后端 AI 由 **「一个大脑（DeepSeek）+ 两层编排（原生 function calling / Langchain）+ 一个知识库（pgvector）」** 构成。

| AI 能力 | 入口 | 技术实现 | 状态 |
|--------|------|----------|------|
| 智能对话问答 | `POST /api/ai/chat` | DeepSeek + 意图路由 | ✅ 已落地 |
| 三意图分类 | `AIService.classify_intent` | DeepSeek 分类器 + 规则兜底 | ✅ 已落地 |
| RAG 知识问答 | `AIService.rag_qa` | Langchain LCEL + pgvector（开关保护） | ✅ 已落地（`USE_RAG`） |
| 行程规划 | `AIService.chat`（plan 分支） | DeepSeek function calling + 确定性约束注入 | ✅ 已落地 |
| 景点语义搜索 | `AIService.search_scenic_rag` | pgvector 向量检索真实景点库 | ✅ 已落地（`USE_RAG`） |
| 景点详情生成 | `AIService.get_scenic_detail` | DeepSeek 生成介绍/门票/预算 | ✅ 已落地 |
| 语音识别对话 | `/api/ai/voice/chat` | Vosk 离线 STT → `AIService.chat` | ✅ 已落地 |
| Langchain 智能体 | `build_agent` | tool-calling（景点检索 + 天气工具） | 🟡 演示/进阶（主链路未强制启用） |
| 业务规则 grounding | — | 预算档位/天数建议/偏好标签 | ⚪ 规划中（待接入 RAG 链） |
| 实时数据 Tool | 天气/票价/余票 | Langchain Tool | 🟡 天气部分落地，票价/余票待接入 |

---

## 6. AI 架构详解

### 6.1 DeepSeek 大模型接入

- **接入方式**：DeepSeek 兼容 OpenAI 协议，后端直接调用 `https://api.deepseek.com/v1/chat/completions`（`config.py:43-46`）。
- **统一封装**：`AIService.call_deepseek_api()`（`ai_service.py:197`）——异步 `httpx` 调用，支持两种模式：
  - **结构化规划**：传入 `tools` 时走 **function calling**（`tool_choice="required"`），强制模型输出可解析 JSON；
  - **自然语言问答**：否则要求 `response_format={"type":"json_object"}`，便于稳健解析。
- **健壮性处理**：
  - `_extract_tool_args()`（`ai_service.py:236`）：循环解包 DeepSeek 偶发的"双重 JSON 编码"参数，最多解 3 层，失败统一返回 `{}`；
  - `_extract_human_text_from_ai_raw()`（`ai_service.py:264`）：从 JSON / 双重编码 / tool_calls 中提取用户可读中文（优先级：narrative → answer → chat_title）。
- **Langchain 封装**：`langchain_layer/llm.py:get_deepseek_llm()` 用 `langchain_openai.ChatOpenAI` 接入，作为 RAG 链与智能体的 LLM 来源，避免 base_url 硬编码散落。

### 6.2 三意图路由（核心调度逻辑）

对话主入口 `AIService.chat()`（`ai_service.py:700`）首先做意图判断，再分流到不同处理路径：

```
用户消息 → classify_intent() → {intent, subtopic}
                │
   ┌────────────┼───────────────────────┐
   ▼            ▼                       ▼
daily_qa     knowledge               plan
大模型直答     RAG 知识库问答          函数调用行程规划
(不进知识库)   (按 subtopic 细分检索)   (function calling)
```

- **分类器**：`classify_intent()`（`ai_service.py:1547`）用 DeepSeek 把对话分为三类，并给 `knowledge` 标 `subtopic`：
  - `scenic`（景点）/ `food`（美食）/ `culture`（人文）。
- **规则兜底**：`INTENT_ROUTER_ENABLED`（`config.py:55`，默认开启）关闭、或 LLM 异常时，回退 `_rule_based_intent()`（`ai_service.py:1533`），保留原"plan 由确定性规则守门、非 plan 全进知识库"的兼容行为。
- **plan 安全保护**：若判定为 `plan` 但消息与历史均无目的地城市，降级为 `daily_qa` 反问城市（`ai_service.py:755-763`），规避"无上下文硬生成默认行程"的历史 Bug。

### 6.3 RAG 检索增强（Langchain + pgvector + bge-m3）

**目标**：让问答只基于真实知识库，抑制大模型编造景点与事实。

**检索层** `services/rag/vector_store.py`：
- **统一索引**：`ScenicPGVectorStore.build_from_db()`（`vector_store.py:179`）把 `scenic_spot`（景点本体）+ `knowledge_doc`（知识库）全量建成 **单一集合 `travel_kb`**，靠 `doc_type` 元数据区分类型：
  `scenic_spot / city / guide / topic / itinerary / faq`。
- **Embedding**：`get_embeddings()`（`vector_store.py:83`）默认走 **本机 Ollama 的 bge-m3**（维度 1024，纯本地零联网）；可切 `hf` 后端用 sentence-transformers。
- **知识库分块**：长文（攻略/城市知识）经 `RecursiveCharacterTextSplitter`（块 500 字、重叠 50）分块，召回更精准；景点简介较短不分块。
- **细分 subtype**：`_infer_subtype()`（`vector_store.py:52`）将 `city/guide/topic` 按内容关键词把"美食段/人文段"精准分离（food/culture），实现同一篇里两类内容互不污染。
- **组合过滤检索**：`get_retriever()`（`vector_store.py:230`）/ `similarity_search()`（`vector_store.py:256`）支持 `city` + `doc_type(s)` + `subtype(s)` 任意组合过滤。

**编排层** `services/langchain_layer/orchestrator.py`：
- **RAG 问答链** `build_qa_chain()`（`orchestrator.py:53`）：用 **LCEL** 把"检索 → 拼上下文 → DeepSeek → 解析"串成一条 Runnable。System Prompt 强约束"只使用检索资料、不编造、信息不足直说不知道"。
- **智能体（进阶）** `build_agent()`（`orchestrator.py:83`）：Langchain `create_agent` 的 tool-calling 智能体，内置 `scenic_search`（景点检索）+ `get_weather`（天气查询）两个工具，演示意图编排。

**主链路集成**（`ai_service.py`）：
- `rag_qa()`（`ai_service.py:1423`）：当 `USE_RAG=True` 且 `intent==knowledge` 时接管 QA，按 `subtopic` 映射检索条件（`_subtopic_to_filter`，`ai_service.py:1527` → `_SUBTOPIC_FILTER`）细分召回，再走 LCEL 链生成回答。
- `search_scenic_rag()`（`ai_service.py:1477`）：RAG 版景点搜索，只召回 `doc_type=scenic_spot` 的真实景点，替代原"模型凭记忆编造 POI"，返回高德式卡片。

> 数据流：`scenic_spot / knowledge_doc` 表 → `build_scenic_index.py` 建索引 → pgvector → Langchain retriever → LCEL 链（检索上下文 + DeepSeek）→ 自然语言回答。

### 6.4 行程规划（function calling + 确定性约束注入）

`AIService.chat()` 在 `is_plan=True` 时进入规划分支（`ai_service.py:778` 起），核心设计：

- **强制结构化**：使用 `SYSTEM_PROMPT_PLAN_TOOL` + `tool_choice="required"`，让 DeepSeek 必须输出结构化行程 JSON（含 `dest_city`、每日景点 `city` 等字段）。
- **确定性约束注入（抑制幻觉的关键）**：
  - **城市约束**：`_extract_cities()` 提取单/多城市；单城市强约束"所有景点 city 必须等于该城市"，多城市软约束"必须覆盖全部城市、每天标注所在城市"（`ai_service.py:790-809`）。无城市时从历史继承（`_extract_city_from_history`）。
  - **天数约束**：`_extract_days()` 提取"X 日游"，强制 `travel_days` 与标题天数一致（`ai_service.py:813`）。
- **落库**：用户确认后由 `POST /api/planning/itinerary/save` → `AIService._process_itinerary()`（`ai_service.py:1129`）保存为行程，避免自动落库产生孤儿记录。

### 6.5 景点语义搜索与详情

- **语义搜索**：`search_scenic()`（`ai_service.py:1304`），RAG 开启时转 `search_scenic_rag()` 走向量检索真实景点；返回高德式候选卡片，前端挑选后 `add-to-trip` 加入行程。
- **AI 详情**：`get_scenic_detail()`（`ai_service.py:1345`）用 DeepSeek 生成景区介绍、门票、注意事项、预算规划。

### 6.6 语音识别（Vosk 离线 STT）

- **实现**：`VoiceService`（`voice_service.py`）封装 **Vosk** 开源离线中文模型（`vosk-model-small-cn-0.22`），**无需 API Key、完全离线**，模型以 vendored 形式放 `libs/vosk` 与 `vosk_models/`。
- **链路**：`POST /api/ai/voice/chat`（`ai_voice.py:38`）→ Vosk 语音转文字 → `AIService.chat()` 生成回复；TTS 由前端浏览器 `speechSynthesis` 完成。

### 6.7 天气服务

`WeatherService`（`weather_service.py`）三级策略：和风天气（国内、需配置）→ Open-Meteo（境外免费兜底）→ 季节性模拟数据；任何降级都在 `warning` 字段与日志明示。主链路经 `/api/weather` 与 `/api/proxy/weather` 代理，密钥仅在服务端。

---

## 7. AI 请求数据流

```
                        ┌─────────────────────────────┐
   前端 / 语音           │        AIService.chat()      │
   ───────────────────▶ │   (ai_service.py:700)        │
                        └──────────────┬──────────────┘
                                       │
                          classify_intent()  ← DeepSeek 三意图分类
                                       │
            ┌──────────────┬───────────┴───────────┬──────────────┐
            ▼              ▼                       ▼              ▼
       daily_qa       knowledge (USE_RAG)       plan        语音 / 详情
    DeepSeek 直答      ├─ USE_RAG=False:          function      (独立端点)
                       │   DeepSeek 直答          calling
                       └─ USE_RAG=True:          + 约束注入
                           rag_qa()              ↓
                           ├ PGVector 检索       结构化行程 JSON
                           │  (按 subtopic 过滤)  ↓
                           └ LCEL 链 + DeepSeek   _process_itinerary 落库
```

---

## 8. API 端点清单（标注 AI）

| 方法 | 路径 | AI? | 说明 |
|------|------|-----|------|
| POST | `/api/ai/chat` | ★ | 对话主入口（意图路由 → 问答/规划/RAG） |
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
| `USE_RAG` | `False` | RAG 总开关；开启后 `knowledge` 意图走 pgvector 检索，关闭则全回退原逻辑 |
| `INTENT_ROUTER_ENABLED` | `True` | 三意图路由开关；关闭回退旧二元逻辑（非 plan 全进 RAG） |
| `RAG_EMBED_BACKEND` | `ollama` | Embedding 后端：`ollama`（bge-m3 本地）/ `hf`（sentence-transformers） |
| `RAG_TOP_K` | `5` | 每次语义检索召回候选条数 |
| `RAG_PG_*` | localhost:5432 / vector_db | PostgreSQL + pgvector 连接（psycopg3 `postgresql+psycopg://`） |
| `RAG_PG_COLLECTION` | `travel_kb` | 统一向量集合名 |
| `DEEPSEEK_*` | api.deepseek.com/v1 | 模型名、API Key、API URL |
| `QWEATHER_*` / `AMAP_KEY` / `BAIDU_TRANSLATE_*` | — | 天气/地图/翻译密钥（仅服务端） |

---

## 10. 依赖与运维脚本

- **核心依赖**：`requirements.txt`（13 项，已与 `.venv` 逐条核对一致）。
- **RAG 依赖**：`requirements_rag.txt`（langchain 1.4.5 / langchain-openai / langchain-postgres / langchain-ollama / psycopg / pgvector 等）。
- **建索引**：`python scripts/build_scenic_index.py` —— 从 `scenic_spot` + `knowledge_doc` 全量建/重建 `travel_kb`（重建前清空旧集合）。
- **灌语料**：`python scripts/seed_knowledge_corpus.py` —— 写入 13 城 starter 种子（城市知识/深度攻略/行程模板 + 全局 FAQ/主题专题），上线前需替换为真实攻略。
- **启动**：`uvicorn main:app --host 0.0.0.0 --port 8000 --reload`（开发），生产关 `APP_DEBUG`。
- **文档**：`/docs`（Swagger）、`/redoc`。

---

## 11. 关键设计决策与备注

1. **RAG 技术选型 = 纯 Langchain（弃用 LlamaIndex）**：检索（`langchain_postgres.PGVector`）+ 编排（`orchestrator.py` 的 LCEL 链 / 智能体）统一用 Langchain，减少桥接层。
2. **双开关灰度策略**：`USE_RAG` + `INTENT_ROUTER_ENABLED` 保证 AI 增强"可灰度、可回滚"，不影响已完成工程。
3. **抑制幻觉三条线**：① RAG 只答检索内容；② 行程规划 function calling + 城市/天数确定性约束注入；③ 景点搜索改走真实向量库，杜绝模型编造 POI。
4. **知识库三层规划**：① 静态知识（已落地，入库 pgvector）；② 业务规则 grounding（预算档位/天数建议/偏好标签，规划中）；③ 实时动态数据（天气已落地为代理/工具，票价/余票 Tool 待接入 RAG 链）。
5. **语音离线化**：Vosk 本地 STT 避免云端语音 API 的 Key 与网络依赖。
6. **密钥隔离**：所有第三方密钥（天气/地图/翻译）仅在服务端 `config.py` 与 `.env` 保存，前端经 `/api/proxy` 代理访问。
```

