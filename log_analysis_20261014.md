# 后端运行日志分析报告

> 分析对象：`2026-10-14 20:10:19 ~ 20:14:51` 后端运行日志
> 用户：`users.id=11`；会话：`chat_session.id=148`
> 涉及模块：FastAPI + SQLAlchemy + DeepSeek + Vosk（语音）+ Open-Meteo（天气）

---

## 一、请求时间线

| 时间 | 方法/路径 | 状态 | 说明 |
|------|-----------|------|------|
| 20:10:19 | OPTIONS /api/ai/sessions、/api/user/info | 200 | CORS 预检 |
| 20:10:19 | （启动）Vosk 模型加载 | — | `Vosk 模型加载成功`，路径 `vosk_models/vosk-model-small-cn-0.22` |
| 20:10:19 | GET /api/ai/voice/status | 200 | 语音模块就绪（前端轮询） |
| 20:10:28 | POST /api/ai/chat（武汉今日天气） | 200 | intent=qa，DeepSeek 1.96s，response_type=question_answer |
| 20:10:32 | GET /api/ai/sessions | 200 | 会话列表刷新 |
| 20:10:56 | POST /api/ai/chat（武汉旅行计划） | 200 | intent=plan，DeepSeek 21.53s，response_type=itinerary |
| 20:11:23 | GET /api/ai/sessions | 200 | 会话列表刷新 |
| 20:14:51 | GET /api/ai/voice/status | 200 | 语音状态轮询 |

> 两次 chat 落在**同一个会话（id=148）**，第二次 `history_msgs=2`（user+assistant 历史被正确携带）。

---

## 二、关键发现

### 🔴 问题 1：Open-Meteo 实时天气接口偶发失败（最核心）

日志明确记录（`weather_service.py:219`）：

```
[天气] Open-Meteo 调用失败: ，降级为模拟数据
```

- 出现于 **20:10:56 的 plan 请求**（用户问"武汉旅行计划"）。plan 分支**无条件**调用天气查询，失败即降级为季节性模拟数据。
- 但 **28 秒前的 QA 请求（20:10:28，武汉今日天气）完全没有天气失败日志**——而 `ai_service.py:832` 的 `_is_weather_query` 命中关键词"天气"，必然触发天气查询。无失败日志即表明**当时调用成功**，DeepSeek 拿到的是真实天气（回答里"阴天 17~26°C、东风 2 级"为真实数据）。
- **结论**：Open-Meteo（`api.open-meteo.com`，境外域名）在当前网络下**可用性是间歇的**，并非稳定可用或稳定不可用，符合"境外站点 TCP 重置"偶发特征。
- **影响**：
  - plan 行程里的"当日天气/穿衣建议"在失败时来自模拟数据，**可能不准确**；
  - 用户无法提前知道当前拿到的天气是真的还是模拟的。

**建议**：
1. 接入国内可直连的天气源（如和风天气，需 API Key；或经代理/镜像）；
2. 降级时在前端/回答中**明确标注「天气为模拟参考值」**，避免误导；
3. 对天气调用做短时缓存 + 重试，降低偶发失败对 plan 的影响。

### 🟠 问题 2：失败异常被吞没，日志无法排障

```
[天气] Open-Meteo 调用失败: ，降级为模拟数据
```

异常占位符 `{}` 为**空字符串**（`{e}` 打印为空）。无论底层是 TCP 重置、超时还是 DNS 失败，都应能看出原因。说明当前捕获的异常对象 `str(e)` 为空（如被包装的 `ConnectionResetError`/`ConnectError`），代码未记录类型与堆栈。

**建议**：改为 `print(f"[天气] Open-Meteo 调用失败: {type(e).__name__}: {e}")`，必要时 `logging.exception(...)` 输出 traceback。

### 🟡 问题 3：SQLAlchemy SQL echo 日志严重冗余

- 每个请求都打印 `SELECT users ... WHERE users.id = 11`（auth 中间件逐请求查用户）；
- 大量只读查询后紧跟 `ROLLBACK`（autocommit 关闭下的正常行为，但噪音大）；
- 语句本身已标注 `[cached since ...]`，说明是语句解析缓存命中，并非重复硬解析。

**建议**：生产环境关闭 SQL echo，将 SQLAlchemy 日志级别设为 `WARNING`；仅在本地调试开启 `echo=True`。

### 🟡 问题 4：QA 天气回答"真实性"不可辨

QA 分支（`ai_service.py:831-855`）逻辑：命中天气关键词 → 查 Open-Meteo → 成功则注入真实数据，失败则 `except` 静默跳过（仅打印 `QA 天气获取失败`），DeepSeek 退化为**凭训练知识编造天气**。
- 优点：意图识别正确，关键词命中稳定；
- 风险：用户无法区分"真实天气"还是"LLM 编造"，且失败时无提示。

**建议**：天气查询失败时，在 system prompt 明确要求 DeepSeek **标注「天气为参考值，未能实时获取」**，与成功路径区分。

---

## 三、运行健康项（正常）

- ✅ **语音模块已落地并工作**：Vosk 中文小模型加载成功，`/api/ai/voice/status` 返回 200，前端轮询正常（说明微信完整版的语音能力已迁移至 travel-system 后端）。
- ✅ **意图识别准确**："武汉今日天气"→ qa，"武汉旅行计划"→ plan，分类正确。
- ✅ **DeepSeek 主链路稳定**：两次调用均成功（1.96s / 21.53s），无超时/报错。
- ✅ **数据库读写正常**：会话创建（INSERT chat_session，id=148）、消息落库（user+assistant 双写）、会话更新（UPDATE update_time）均 `COMMIT` 成功。
- ✅ **无 5xx 错误**：所有 HTTP 接口返回 200。
- ✅ **历史上下文管理正确**：plan 分支不携带历史（独立任务），QA 分支自适应携带（无城市冲突时），`history_msgs=2` 符合预期。

---

## 四、优化建议汇总

| 优先级 | 项 | 动作 |
|--------|----|------|
| 高 | Open-Meteo 偶发失败 | 换国内天气源 / 加缓存重试 / 降级显式标注 |
| 高 | 异常信息为空 | 记录 `type(e)` 与 traceback |
| 中 | SQL 日志冗余 | 生产关 echo，级别 WARNING |
| 中 | QA 天气真实性 | 失败时在回答标注"参考值" |

---

*注：本分析基于单段运行日志，天气接口的可用性需多次/跨时段复测确认。*
