"""AI服务：对接 DeepSeek 大模型，实现智能行程生成、智能问答、景点搜索"""

import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from config import settings
from models.trip import Trip
from models.trip_detail import TripDetail
from models.scenic_spot import ScenicSpot
from models.chat import ChatSession, ChatMessage

from services.langchain_layer import (
    get_chat_model,
    to_langchain_messages,
)


# 系统提示词 

# 规划分支使用 SYSTEM_PROMPT_PLAN_TOOL（短指令）+ ITINERARY_TOOL（function calling schema）。

ITINERARY_TOOL = {
    "type": "function",
    "function": {
        "name": "create_itinerary",
        "description": "根据用户的出行需求生成完整旅游行程方案，包含行程概况与每日景点安排",
        "parameters": {
            "type": "object",
            "properties": {
                "chat_title": {"type": "string", "description": "会话标题，如'北京3日游规划'（城市必须与用户指定城市一致，禁止写其他城市）"},
                "narrative": {"type": "string", "description": "给用户的详细自然语言行程说明，必须按天分块（Day N 日期 天气），每天包含：天气与穿衣建议、上下午景点安排（含到达时间/停留时长/看点/门票）、景点间具体交通方式（地铁线/公交路号/打车时长与费用/步行距离）、早午晚餐推荐（具体店名或菜名）、当日预算小计。开篇要有总览，结尾要有实用提示。3 日游至少 800 字，5 日游至少 1200 字。允许使用换行符、Emoji、小标题格式（如 Day 1、【交通】、【美食】）增强可读性。"},
                "trip": {
                    "type": "object",
                    "description": "行程概况",
                    "properties": {
                        "trip_name": {"type": "string", "description": "行程标题（标题中的城市必须与用户指定城市一致）"},
                        "dest_city": {"type": "string", "description": "目的地城市，必须严格等于用户指定的城市，禁止替换为武汉/广州等其他城市"},
                        "start_date": {"type": "string", "description": "YYYY-MM-DD，未指定则留空字符串"},
                        "end_date": {"type": "string", "description": "YYYY-MM-DD，未指定则留空字符串"},
                        "travel_days": {"type": "integer", "description": "游玩天数"},
                        "total_budget": {"type": "number", "description": "预算总额"},
                        "traveler_type": {"type": "string", "description": "游客类型，如情侣/家庭/朋友/独自旅行"}
                    },
                    "required": ["trip_name", "dest_city", "travel_days"]
                },
                "scenic_spots": {
                    "type": "array",
                    "description": "行程包含的所有景点",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "景点名称"},
                            "city": {"type": "string", "description": "所属城市，必须严格等于用户指定的城市，禁止替换为武汉/广州等其他城市"},
                            "introduction": {"type": "string"},
                            "address": {"type": "string"},
                            "open_time": {"type": "string"},
                            "price": {"type": "number", "description": "门票价格，0表示免费"},
                            "latitude": {"type": "number"},
                            "longitude": {"type": "number"},
                            "special_notice": {"type": "string"},
                            "suggested_duration": {"type": "string"},
                            "trip_detail": {
                                "type": "object",
                                "properties": {
                                    "day_num": {"type": "integer", "description": "第几天，从1开始"},
                                    "start_time": {"type": "string", "description": "HH:MM"},
                                    "end_time": {"type": "string", "description": "HH:MM"},
                                    "remark": {"type": "string"},
                                    "spot_budget": {"type": "number"},
                                    "sort_order": {"type": "integer", "description": "当日排序，从1开始"}
                                },
                                "required": ["day_num"]
                            }
                        },
                        "required": ["name", "city", "trip_detail"]
                    }
                }
            },
            "required": ["trip", "scenic_spots"]
        }
    }
}

SYSTEM_PROMPT_PLAN_TOOL = """你是专业的旅游行程规划助手。用户会描述出行需求（目的地城市、游玩天数、预算、人数、偏好等）。
默认必须调用 create_itinerary 工具来返回完整行程方案，不要直接输出文本或 JSON，也不要返回 question_answer 类型。
若用户需求缺少必要信息（如目的地、天数）或明显无法生成行程，则先简短追问缺失信息，不得编造行程。
若预算、人数或偏好未提供，可在行程中做合理假设并明确标注，或在关键信息缺失时先追问。
**JSON/参数格式硬性要求**：所有字符串值（尤其是 narrative）内部严禁出现未转义的英文双引号——引用词语一律用中文引号「」；若必须用英文双引号必须写成 \\" 转义，否则会破坏 JSON 导致回复截断。

【城市必须严格匹配】行程的 dest_city 以及每一个景点的 city 都必须严格等于用户在消息中明确提到的目的地城市，绝不可自行替换为其他城市（例如用户说"三亚"就必须生成"三亚"，不得生成"武汉""广州"等其他城市）。trip_name 与 chat_title 中的城市也必须与用户指定城市一致。

【narrative 必须详细且结构化】narrative 字段是给用户看的唯一长文本，必须包含完整行程说明。严格遵守：
1. **开篇总览**（2-3 句）：行程亮点、整体节奏、适合人群、总预算说明。
2. **按天分块叙述**，每一天必须用 `Day N（日期，天气）` 作为小标题，并包含以下要素：
   - 当日天气与穿衣/装备建议（如"晴 26-33°C，建议防晒、戴墨镜"）
   - 当日行程主题（如"历史人文之旅"/"海岛休闲日"）
   - 上午/下午/晚上的具体安排，每个景点要写出：到达时间、停留时长、推荐看点、门票说明
   - **景点间交通方式**：明确写出从 A 到 B 的交通方式（地铁X号线/打车约XX分钟/步行X分钟/公交XX路），并给出大概耗时与费用
   - 餐饮推荐：早餐/午餐/晚餐分别推荐当地特色餐厅或美食（具体店名或菜名）
   - 当日预算小计（交通+门票+餐饮）
3. **结尾实用提示**：包含整体注意事项、应急联系方式、当地特色小贴士等。

narrative 允许使用换行符、Emoji（适度）和小标题格式（如 `Day 1`、`【交通】`、`【美食】`）来增强可读性。篇幅要充足，3 日游至少 800 字，5 日游至少 1200 字。

【每日天气】若后端注入了天气数据，必须把每天的天气（温度区间、天气状况、风力）嵌入到对应 Day 的小标题与出行建议中；若未注入天气数据，基于该城市当季气候给出合理估计并标注"（季节性参考）"。

【交通方式必须具体】禁止只写"交通便利"这类空话，必须写明：地铁线路+站名、公交路号、打车预估时长与费用、步行距离，让用户能直接按文执行。"""

SYSTEM_PROMPT_QA = """你是一个友好、专业、像真人导游朋友一样的旅游助手，负责和用户聊天、答疑、给建议。

**绝对禁止照搬示例**：本提示词中出现的任何城市名、景点名、美食名、交通方式、价格等，**仅仅是规则示例**，你不得在任何回答中直接复制或默认使用它们。你必须严格根据本会话的真实历史消息和用户的实际输入来确定城市、景点与内容。如果用户当前没有明确城市，但对话历史围绕某个城市展开，则继续围绕该真实城市作答。

用户可能问你：某个城市有什么好玩的/好吃的、景点介绍、交通方式、最佳旅行季节、预算建议、签证/行李等旅行常识，也可能是在闲聊或进一步追问。请遵守：

1. 用自然、详细、有条理的中文回答，可以适当分点、列出景点/美食名称，但不要死板；
2. **可以结合对话历史理解用户意图**：后端会把本会话的历史消息一并传给你。当用户用简短承接词延续上文（如"需要""好的""然后呢""还有吗""那交通呢""怎么去"）时，应理解为对前文的确认或追问，自然地接着聊；但**作答核心必须是用户当前这条消息的字面语义**，不要生硬复制上一轮的长文本。若用户切换到完全无关的话题，立即跟随新话题。
3. 如果用户只是咨询或闲聊，可以在回答末尾自然地追问一句"需要我帮你规划一份具体的行程吗？"来引导，但**不要主动生成完整行程**；
4. 严禁输出完整行程规划结构（不要输出 itinerary / trip / scenic_spots 这类结构），也不要调用任何工具；
5. 用户当前消息是核心；当用户用简短承接词延续上文时，请结合历史给出连贯回复，不要当作孤立问题。
6. 关于具体事实（门票价格、开放时间、地址、营业时间、交通票价、是否需要预约等）：你基于自身知识作答，但不保证实时准确。**若不确定或信息可能过时，必须明确标注「以景区/官方现场公布为准」或坦诚建议「出行前请再核实」，绝不可把猜测的精确数字伪装成确凿事实**。宁可少给一个具体数字，也不要给错一个数字；宁可说明"我不太确定"，也不要编造。
7. **【选择问承接规则，必须严格遵守】** 当你上一轮的末尾是以选择问/追问形式结尾，而用户在最新一条消息里用简短的名词或短语作答时，**必须把这条消息理解成对前文话题的延续，而不是一个全新、孤立的问题**：
   - 例：前文正在讨论「[某城市]旅游」，你问「更喜欢历史古迹还是胡同文艺范儿？」，用户仅回复「历史古迹」→ 必须理解为「用户想在该城市范围内挑选历史古迹」，回答时继续围绕【该城市】，给出该城市内的具体景点与建议，**绝不能**突然泛化为全国范围的历史古迹大盘点。
   - 例：前文讨论「[某城市]美食」，你问「火锅还是小吃？」，用户回「火锅」→ 应理解为「想在该城市吃火锅」，继续围绕该城市推荐，而非列举全国火锅。
   **注意**：示例中的 `[某城市]` 只是占位符，你**不得照搬示例里的任何具体城市或景点/美食名称**，必须替换为对话历史中真实在讨论的城市。
   判断依据：用户消息很短（通常 ≤12 字）、且上一条 assistant 消息明显在抛出一个二选一或多项选择。此时作答核心虽仍以该名词短语为线索，但**地理范围、话题背景必须继承上文**，直到用户明确切换到新城市/新话题。
8. **【确认型短回复规则，必须严格遵守】** 当你上一轮以提议/请求确认的问句结尾（如"需要我帮你规划/查一下/安排XXX吗？"），而用户在最新一条消息里用"需要/好的/可以/行/嗯/对/是的/好/要/想/继续/安排"等简短确认词回复时，**必须直接执行该提议并继续围绕当前话题作答**，**绝不要再反问**"你想规划行程还是了解城市/景点/美食细节？"：
   - 例：我上一句提出了一个具体建议，用户仅用"需要/好的"等简短词确认 → 必须理解为"用户同意并希望我直接执行【我上一句实际提出的那个建议本身】"，立即给出与该建议一致的具体结果，不要二次确认、不要切换话题、不要替换为其他城市。
   - 例：若我上一句是关于某景点门票/交通的追问，用户回"好的" → 应立即给出该景点周边的对应信息，而非另起一个全新话题。
   **注意**：你必须严格基于【我上一句实际说出的内容】来回应，不得照搬或套用本提示词中的任何示例模板（包括任何示例里的具体城市、景点、美食、交通信息），必须根据对话历史中真实在讨论的城市与话题作答。
   判断依据：用户消息很短（通常 ≤8 字）、属于常见确认词，且上一条 assistant 消息明显在提出一个可执行的具体建议。此时应视为"同意并执行"，而不是"请求澄清"。若用户说"不需要/不用/算了"等否定词，则不触发。
9. **【天气数据使用规则】** 若后端在系统提示词中注入了【实时天气信息 - 城市】数据块，你必须直接基于这些具体数据回答天气相关问题，给出具体城市、日期、天气状况、温度范围和风力；**严禁再说"无法实时联网查询"或"给不了准确温度"**。若数据块标注为"（模拟数据）"，可在回答中注明"（基于季节性参考）"。只有当系统提示词里确实没有天气数据块时，才可基于自身知识给出季节性参考，并建议用户查看官方天气 App。
10. 必须只返回如下 JSON，不要包含 markdown 标记或额外文字：
{
    "response_type": "question_answer",
    "data": {
        "chat_title": "简短的会话标题",
        "answer": "你给用户的自然回答（可较长，支持换行与分点）"
    }
}
**JSON 格式硬性要求**：answer / chat_title 字符串值内部**严禁出现未转义的英文双引号 "**——如需引用词语，一律使用中文引号「」或‘’；若必须用英文双引号，必须写成 \\" 转义。违反会导致 JSON 解析失败、用户看到的回复被截断。
"""

SYSTEM_PROMPT_SCENIC_SEARCH_LIST = """你是一个旅游信息搜索助手，模拟地图 App（如高德地图）的 POI 搜索体验。用户会提供一个搜索关键词（可以是景点名、类型或兴趣，如"海滩""亲子乐园""古镇""美食"）和城市，你需要返回该城市内最相关的多个候选地点，形成一张「搜索结果列表」。

请返回如下结构的纯 JSON（以 { 开头、} 结尾，禁止 YAML、禁止 markdown 代码块）：

{
  "results": [
    {
      "name": "地点全称",
      "category": "分类标签，必须从以下选项中选最贴切的一个：自然风光 / 历史古迹 / 主题乐园 / 亲子游乐 / 美食街区 / 城市地标 / 宗教文化 / 博物馆 / 休闲街区 / 夜景观光",
      "city": "所属城市（等于用户指定的城市）",
      "address": "详细地址（区/街道，尽量具体）",
      "latitude": 纬度(浮点数，如30.5728),
      "longitude": 经度(浮点数，如104.0668),
      "rating": 评分(数字，0-5，保留一位小数，如4.6),
      "price": 门票价格(数字，0表示免费),
      "open_time": "开放时间（如'08:00-18:00'，未知写'以景区公告为准'）",
      "tel": "咨询电话（未知写空字符串）",
      "tags": ["标签1", "标签2"],
      "suggested_duration": "建议游玩时长（如'2-3小时'）",
      "special_notice": "注意事项或特殊提醒（无则空字符串）",
      "introduction": "一句话亮点/简介（20-40字，用于卡片副标题）",
      "recommendation": "推荐理由（30-60字，说明为什么值得去）"
    }
  ]
}

重要规则：
1. 必须返回 5-8 个最相关的候选地点，按相关度/热度从高到低排序；
2. 每个地点都要真实存在于该城市，不要编造不存在的景点（可用常识补全知名景点，但确保大体真实）；
3. 经纬度尽量准确（保留小数点后4位）；评分基于大众口碑合理估计，范围 0-5；
4. 分类 category 必须从给定选项中选取最贴切的一个；
5. 必须只返回纯 JSON，不要任何 markdown 标记或额外文字。
"""

SYSTEM_PROMPT_SCENIC_DETAIL = """你是一个旅游信息助手。用户会提供景点名称和城市，你需要返回该景点的详细介绍信息。

请返回结构化的JSON数据：
{
    "introduction": "景区详细介绍（100-200字）",
    "price": 门票价格(数字，0表示免费),
    "special_notice": "注意事项（如穿衣建议、最佳游览时间等）",
    "budget_suggestion": "预算建议（如'建议预留200元用于门票和交通'）"
}

重要规则：
1. 必须只返回纯JSON格式数据，不要包含任何markdown标记或额外文字
2. 信息要准确且实用
"""


class AIService:
    """AI 服务"""

    @staticmethod
    async def call_deepseek_api(messages: list, tools: list = None,
                                temperature: float = None) -> dict:
        """调用 DeepSeek（经 Langchain ChatOpenAI 接入层）。

        tools 非空时走 function calling；否则走 json_object 响应格式。
        返回与 OpenAI 兼容的 dict，使现有 _extract_content / _extract_tool_args
        解析逻辑保持不变（详见 _ai_message_to_openai_dict）。
        """
        model = get_chat_model(temperature=temperature if temperature is not None else 0.3)
        if tools:
            model = model.bind_tools(tools, tool_choice="required")
        else:
            model = model.bind(response_format={"type": "json_object"})

        lc_messages = to_langchain_messages(messages)
        ai_msg = await model.ainvoke(lc_messages)
        return AIService._ai_message_to_openai_dict(ai_msg)

    @staticmethod
    def _ai_message_to_openai_dict(ai_msg) -> dict:
        """将 Langchain AIMessage 规整为 OpenAI 兼容 dict，保持旧解析逻辑不变。"""
        msg = {"role": "assistant", "content": ai_msg.content or ""}
        tool_calls = getattr(ai_msg, "tool_calls", None) or []
        if tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.get("id"),
                    "type": "function",
                    "function": {
                        "name": tc.get("name"),
                        "arguments": json.dumps(tc.get("args") or {}, ensure_ascii=False),
                    },
                }
                for tc in tool_calls
            ]
        return {"choices": [{"message": msg}]}

    @staticmethod
    def _extract_content(raw: dict) -> str:
        """从 DeepSeek 完整响应 dict 中提取回复正文（非 function calling 调用用）"""
        try:
            msg = raw["choices"][0]["message"]
            if not isinstance(msg, dict):
                return ""
            return msg.get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError):
            return ""

    @staticmethod
    def _extract_tool_args(raw_args) -> dict:
        """稳健解析 tool_calls[i].function.arguments。
        DeepSeek 偶发把 arguments 双重 JSON 编码为字符串（外层再包一层 JSON），
        这里循环解析直到不再是纯文本 JSON 串为止，始终返回 dict；失败统一返回 {}。
        """
        if not raw_args:
            return {}
        parsed = raw_args
        # 最多解 3 层，防止意外死循环
        for _ in range(3):
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, str):
                stripped = parsed.strip()
                if not stripped:
                    return {}
                # 只有看起来像 JSON（{ 或 [ 开头）才尝试 json.loads
                if not (stripped.startswith("{") or stripped.startswith("[")):
                    return {}
                try:
                    parsed = json.loads(stripped)
                except (ValueError, TypeError):
                    return {}
            else:
                return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _extract_human_text_from_ai_raw(raw_text: str) -> str:
        """从 AI 输出的原始文本（可能是 JSON / 双重编码 JSON / tool_calls）中提取用户能看懂的中文。
        优先级：narrative → answer → chat_title → 非 JSON 的中文片段。
        解析失败统一返回空串。
        """
        if not raw_text:
            return ""
        stripped = raw_text.strip()
        if not stripped:
            return ""
        # 如果根本不是 JSON 结构（不以 { 开头），直接返回原文
        if not stripped.startswith("{"):
            return stripped

        # 最多解 3 层 JSON 编码，尝试每一层提取可读字段
        layer = stripped
        for _ in range(3):
            if isinstance(layer, str):
                if not (layer.startswith("{") or layer.startswith("[")):
                    return layer
                try:
                    layer = json.loads(layer)
                except (ValueError, TypeError):
                    # 解不开，尝试从字符串里手动切 narrative/answer 片段
                    for key in ("narrative", "answer", "chat_title"):
                        m = re.search(rf'"{key}"\s*:\s*"((?:\\.|[^"\\]){{1,20000}})"', raw_text)
                        if m:
                            try:
                                val = json.loads('"' + m.group(1) + '"')
                                if isinstance(val, str) and val.strip():
                                    return val.strip()
                            except Exception:
                                pass
                    return ""
            if isinstance(layer, dict):
                # 优先直接读顶层字段
                for key in ("narrative", "answer"):
                    val = layer.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
                inner = layer.get("data")
                if isinstance(inner, dict):
                    for key in ("narrative", "answer"):
                        val = inner.get(key)
                        if isinstance(val, str) and val.strip():
                            return val.strip()
                chat_title = layer.get("chat_title")
                if isinstance(chat_title, str) and chat_title.strip():
                    return chat_title.strip()
                # 如果是 function calling 结构，解析 arguments
                tool_calls = layer.get("tool_calls")
                if isinstance(tool_calls, list) and tool_calls:
                    fn = tool_calls[0].get("function") if isinstance(tool_calls[0], dict) else None
                    if isinstance(fn, dict):
                        args = fn.get("arguments")
                        if args:
                            parsed_args = AIService._extract_tool_args(args)
                            narrative = parsed_args.get("narrative")
                            if isinstance(narrative, str) and narrative.strip():
                                return narrative.strip()
                            chat_title = parsed_args.get("chat_title")
                            if isinstance(chat_title, str) and chat_title.strip():
                                return chat_title.strip()
                return ""
        return ""

    @staticmethod
    def _repair_json_quotes(text: str) -> str:
        """修复模型在 JSON 字符串值内部输出未转义英文双引号导致的非法 JSON。

        启发式：JSON 的结构引号相邻字符必然是结构字符（{}[]:,）或空白；
        而"内容引号"两侧通常是中文/全角字符（如 导航有时会"失灵"）。
        将内容引号替换为中文引号后，JSON 即可正常解析。
        """
        if '"' not in text:
            return text
        # 第一层（保守）：两侧均为中文/全角字符的英文引号 → 中文引号（按开/闭交替）
        cjk = "\u4e00-\u9fff\u3000-\u303f\uff00-\uffef"
        pattern = f'(?<=[{cjk}])"(?=[{cjk}])'
        counter = {"n": 0}

        def _alt(_m):
            counter["n"] += 1
            # 奇数次视为开引号，偶数次视为闭引号；错乱也不影响 JSON 合法性
            return "\u201c" if counter["n"] % 2 == 1 else "\u201d"

        repaired = re.sub(pattern, _alt, text)
        if repaired != text:
            return repaired

        # 第二层（稍激进）：两侧都不是 JSON 结构字符/空白/引号的英文引号 → 中文引号
        pattern2 = r'(?<![{}\[\]:,\\\s"])"(?![{}\[\]:,\\\s"])'
        return re.sub(pattern2, "\u201d", text)

    @staticmethod
    def parse_json_response(text: str) -> dict:
        """解析 AI 返回的 JSON（兼容 markdown 包裹）；空/非法输入统一返回 {}，绝不返回 None"""
        text = text.strip()
        if not text:
            return {}
        # 去除可能的 markdown 代码块标记
        if text.startswith("```"):
            lines = text.split("\n")
            # 去掉首尾的 ``` 行
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        text = text.strip()

        # 修复模型在字符串值内输出未转义英文双引号导致的非法 JSON
        # （典型症状：answer 正文里写了 "xxx"，json.loads 在该处报
        #   Expecting ',' delimiter，兜底提取后回复被截断一半）
        repaired = AIService._repair_json_quotes(text)
        if repaired != text:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试 YAML 兜底（模型偶尔返回 YAML 而非 JSON）
            try:
                import yaml
                result = yaml.safe_load(text)
                if isinstance(result, dict):
                    return result
            except Exception:
                pass
            # 尝试提取 JSON 部分
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
            raise ValueError(f"无法解析AI返回的JSON: {text[:200]}")

    @staticmethod
    def _is_plan_intent(text: str) -> bool:
        """判断用户消息是否表达规划完整行程意图（而非普通咨询/闲聊）"""
        # 显式规划关键词
        keywords = ["规划", "行程", "日游", "天游", "游玩", "定制", "安排", "攻略", "路线", "旅行计划", "旅游计划"]
        if any(k in text for k in keywords):
            return True
        # "X天怎么玩/怎么安排"、"玩X天"、"玩几天" 也视为规划意图
        if re.search(r"\d+\s*天|玩\s*\d+\s*天|怎么玩|怎么安排|玩几天|几天玩", text):
            return True
        return False

    @staticmethod
    def _is_plan_continuer(message: str, history: list) -> bool:
        """检测『承接上文规划』意图：用户用极简肯定词（需要/好的/要/可以/行）回应了上一轮
        AI 末尾的规划提议（如『需要我帮你规划一份具体的行程吗？』），应触发出行规划分支。
        例：AI 上一轮末尾问『需要我帮你规划一份具体的行程吗？』，用户回『需要』→ True。"""
        m = (message or "").strip()
        if not m or len(m) > 10:
            return False
        # 排除带有新问题内容的消息（避免把『需要推荐的酒店』误判为规划承接）
        _new_q_markers = ["酒店", "美食", "交通", "景点", "推荐", "哪里", "怎么", "什么",
                          "多少钱", "预算", "几天", "住哪", "玩几天", "攻略", "路线", "门票"]
        if any(k in m for k in _new_q_markers):
            return False
        _affirmatives = ["需要", "好的", "好", "要", "可以", "行", "安排", "规划", "出",
                        "帮我", "继续", "对", "是的", "是", "安排一下", "出一份"]
        if not any(k in m for k in _affirmatives):
            return False
        # 历史中最近一条 assistant 必须含有『规划提议』信号
        last_ai = ""
        for msg in reversed(history):
            if getattr(msg, "role", None) == "assistant":
                last_ai = msg.content or ""
                break
        if not last_ai:
            return False
        # 仅当 AI 上一条是"明确的规划提议问句"才承接，避免两类误触发：
        #  1) AI 在普通推荐/叙事里顺带提到"帮你规划"（如"我可以帮你规划当天路线"），
        #     导致后续用户任何"好的/需要"都被误判为行程确认，硬生成 3 日游；
        #  2) 与用户真实意图无关的上下文被强行带入行程规划分支。
        # 要求规划信号词之后短距离内出现问号（？/?）或"吗"，即确属提议式提问。
        _plan_signals = [
            "需要我帮你规划", "需要我为您规划", "需要我为你规划", "帮你规划一份",
            "要我帮你规划", "帮你规划", "规划一份", "需要我帮你做一份", "需要我帮你制定",
        ]
        for s in _plan_signals:
            idx = last_ai.find(s)
            if idx != -1:
                tail = last_ai[idx: idx + len(s) + 18]
                if "？" in tail or "?" in tail or "吗" in tail:
                    return True
        return False

    @staticmethod
    def _extract_city_from_history(history: list) -> Optional[str]:
        """从历史消息里找最近一次提到的目的地城市，用于『承接上文规划』时继承目的地。
        仅看最近 10 条，避免把很久以前、已切换话题的旧城市误继承为当前目的地
        （如先聊北京、再聊齐齐哈尔后说『需要』，不应继承成北京）。
        优先取最近一条含城市的 user 消息；兜底取最近一条 assistant 消息里最后一个提到的白名单城市。"""
        recent = list(history)[-10:]
        for msg in reversed(recent):
            if getattr(msg, "role", None) == "user":
                c = AIService._extract_city(msg.content or "")
                if c:
                    return c
        for msg in reversed(recent):
            if getattr(msg, "role", None) == "assistant":
                cs = AIService._extract_cities(msg.content or "")
                if cs:
                    return cs[-1]
        return None

    # 常见城市白名单（用于从用户消息中确定性提取目的地城市）
    _KNOWN_CITIES = [
        # 直辖市 / 省会
        "北京", "上海", "广州", "深圳", "天津", "重庆", "武汉", "成都", "杭州", "南京",
        "西安", "苏州", "厦门", "青岛", "大连", "昆明", "丽江", "桂林", "三亚", "海口",
        "贵阳", "哈尔滨", "沈阳", "长春", "济南", "合肥", "郑州", "南昌", "福州", "南宁",
        "兰州", "西宁", "银川", "呼和浩特", "石家庄", "太原", "长沙", "拉萨", "乌鲁木齐",
        # 旅游热门城市
        "香港", "澳门", "台北", "大理", "无锡", "宁波", "温州", "佛山", "珠海", "常州",
        "徐州", "泉州", "烟台", "洛阳", "开封", "黄山", "张家界", "西双版纳", "延安",
        "武夷山", "稻城", "腾冲", "承德", "秦皇岛", "北戴河", "喀什", "伊犁", "吐鲁番",
        # 湖北地市（含宜昌 / 恩施等被遗漏的旅游城市）
        "宜昌", "恩施", "襄阳", "荆州", "黄冈", "十堰", "荆门", "随州", "鄂州", "孝感",
        "咸宁", "神农架",
        # 其他高频旅游地
        "婺源", "宏村", "西塘", "乌镇", "周庄", "同里", "凤凰", "平遥", "敦煌",
        "嘉峪关", "额济纳", "海螺沟", "日喀则", "林芝", "香格里拉", "泸沽湖", "喀纳斯",
        "禾木", "布尔津", "阳朔", "北海", "涠洲岛", "鼓浪屿", "莫干山", "千岛湖",
        "嵊泗", "东极岛", "南浔",
        # 东北及其他增补（旅游高频但易被遗漏的地级市 / 区）
        "齐齐哈尔", "牡丹江", "佳木斯", "大庆", "漠河", "延吉", "图们", "抚远",
        "大同", "包头", "鄂尔多斯", "南通", "扬州", "镇江", "泰州", "嘉兴",
        "绍兴", "金华", "台州", "芜湖", "潍坊", "临沂", "唐山", "保定",
        "张家口", "邯郸", "赣州", "柳州", "遵义",
    ]

    @staticmethod
    def _extract_city(text: str) -> Optional[str]:
        """从用户消息中提取目的地城市（确定性，优先白名单命中）"""
        for c in AIService._KNOWN_CITIES:
            if c in text:
                return c
        # 兜底：匹配 "XX(数字)日游/天游" 中的城市词
        m = re.search(r"([一-龥]{2,4})\s*(?:\d+|[一二三四五六七八九十两]+)\s*(?:日|天)游", text)
        if m:
            token = m.group(1)
            if token not in ("城市", "地方", "哪里", "这儿", "那儿"):
                return token
        return None

    @staticmethod
    def _extract_cities(text: str) -> list:
        """提取文本中出现的所有白名单城市，按文本中首次出现顺序返回（去重）。
        用于支持多城市行程场景（如"武汉到宜昌及恩施旅行规划"）。"""
        if not text:
            return []
        seen = set()
        result = []
        # 按白名单顺序扫会破坏"文本出现顺序"，因此改为按文本顺序扫：
        # 找到每个城市在文本中的最早出现位置，按位置排序。
        positions = []
        for c in AIService._KNOWN_CITIES:
            idx = text.find(c)
            if idx != -1:
                positions.append((idx, c))
        positions.sort(key=lambda x: x[0])
        for _, c in positions:
            if c not in seen:
                seen.add(c)
                result.append(c)
        return result

    _CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
               "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

    # 天气查询专用城市提取：白名单之外的城市（如鸡西、大同之外的大量地级市）也能从
    # "XX天气 / XX的天气 / XX未来N天天气" 模式中直接捕获，避免 _extract_city 白名单缺失
    # 导致天气城市静默回退到历史城市（城市串味 bug：问鸡西却回了深圳天气）。
    # 城市 token 限 2~3 字（4 字城市不在本应用范围），避免吞入动词/时间前缀。
    _WEATHER_CITY_RE = re.compile(
        r"([一-龥]{2,3}?)\s*"
        r"(?:的|这几天的?|最近|近期|最近几天的?|近几天的?|"
        r"近\s*[\d一二两三四五六七八九十]*\s*(?:天|周)(?:的)?|"
        r"过去\s*[\d一二两三四五六七八九十]*\s*(?:天|周)(?:的)?|"
        r"未来\s*[\d一二两三四五六七八九十]*\s*(?:天|周)(?:的)?)?\s*"
        r"(?:天气|气温|温度|降雨|下雨|下雪|降水|风力|雾霾)"
    )
    _WEATHER_CITY_STOPWORDS = {
        "这几天", "今天", "明天", "后天", "这里", "那里", "当地", "这个", "那个",
        "哪里", "哪儿",
    }
    # 捕获词若含这些字，基本不是城市（时间/数字/疑问/动词/指代），直接拒绝：
    # 用于剔除"三天""明天""未来""最近""近期"等被误判为城市的情形。
    _WEATHER_CITY_REJECT_CHARS = set(
        "0123456789一二两三四五六七八九十天日号月年几明昨今后周最近"
        "去玩到在游吃住买看帮你我他她它给让请知道想这那"
    )

    @staticmethod
    def _extract_days(text: str) -> Optional[int]:
        """从用户消息中提取游玩天数（确定性）"""
        # 阿拉伯数字：3日游 / 3天游 / 玩3天
        m = re.search(r"(\d+)\s*(?:日游|天游|天)", text)
        if m:
            return int(m.group(1))
        # 中文数字：三日游 / 三天
        m = re.search(r"([一二两三四五六七八九十])\s*(?:日游|天游|天)", text)
        if m:
            return AIService._CN_NUM.get(m.group(1))
        return None

    @staticmethod
    def _extract_budget(text: str) -> Optional[int]:
        """从用户消息中提取预算金额（确定性）"""
        # 必须带「预算/¥/￥」前缀或「元」后缀，避免误抓"3日游"里的数字
        m = re.search(r"(?:预算|¥|￥)\s*(\d+)|(\d+)\s*元", text)
        if m:
            return int(m.group(1) or m.group(2))
        return None

    @staticmethod
    def _is_weather_query(text: str) -> bool:
        """判断用户消息是否为天气相关查询"""
        if not text:
            return False
        keywords = ["天气", "气温", "温度", "降雨", "下雨", "下雪", "降水", "风力", "雾霾"]
        return any(k in text for k in keywords)

    @staticmethod
    def _extract_weather_days(text: str) -> int:
        """从天气类查询中提取想查的天数，默认 3 天"""
        if "今明" in text or "今天和明天" in text:
            return 2
        if "今天" in text and "明天" not in text and "后天" not in text:
            return 1
        if "明天" in text and "后天" not in text:
            return 2
        if "后天" in text:
            return 3
        if "这周" in text or "本周" in text or "一周" in text:
            return 7
        m = re.search(r"(?:未来|近)\s*(\d+)\s*天", text)
        if m:
            return int(m.group(1))
        m = re.search(r"(?:未来|近)\s*([一二两三四五六七八九十])\s*天", text)
        if m:
            return AIService._CN_NUM.get(m.group(1), 3)
        m = re.search(r"([一二两三四五六七八九十])天", text)
        if m:
            return AIService._CN_NUM.get(m.group(1), 3)
        m = re.search(r"(\d+)天", text)
        if m:
            return int(m.group(1))
        return 3

    @staticmethod
    def _extract_weather_city(text: str) -> Optional[str]:
        """从天气类查询中提取用户实际想查的城市（覆盖白名单之外的城市）。

        用「城市词 + 天气关键词」模式直接捕获，能正确取出 鸡西 / 大同 / 拉萨之外的大量
        地级市；与 _extract_city（仅白名单子串匹配）互补。
        仅当当前消息确实点名了城市才返回；否则返回 None，由调用方决定是否继承历史城市
        （避免"问鸡西却用深圳天气上下文回答"的城市串味 bug）。
        """
        if not text:
            return None
        m = AIService._WEATHER_CITY_RE.search(text)
        if not m:
            return None
        token = m.group(1).strip("的了")  # 剥掉被贪婪匹配吞入的"的/了"（如"上海的气温"→"上海"）
        if not token or token in AIService._WEATHER_CITY_STOPWORDS:
            return None
        # 白名单优先：可剔除动词前缀（"道哈尔滨"→哈尔滨），并兼容含"天"的白名单城市（天津）
        wl = AIService._extract_city(token)
        if wl:
            return wl
        # 剔除含时间/数字/动词/指代字的误抓（"三天""明天""未来""这几天"等）
        if any(ch in AIService._WEATHER_CITY_REJECT_CHARS for ch in token):
            return None
        return token

    @staticmethod
    def _history_has_city_conflict(history: list, current_city: Optional[str]) -> bool:
        """判断对话历史是否与当前话题存在"城市冲突"（会导致 AI 答非所问）。

        - 用户已指定城市 current_city：若历史 assistant 消息里曾出现其他城市（行程规划
          痕迹），视为冲突 —— 此时若带历史，AI 可能把旧城市内容混入当前回复。
        - 用户未指定城市：若历史里出现过多于一个不同城市（明显切换过话题），视为冲突。
        返回 True 表示应丢弃历史，避免污染；False 表示可安全携带历史。
        """
        cities_in_history: set = set()
        for m in history:
            if getattr(m, "role", None) != "assistant":
                continue
            content = getattr(m, "content", "") or ""
            for c in AIService._KNOWN_CITIES:
                if c in content:
                    cities_in_history.add(c)
        if current_city:
            return any(c != current_city for c in cities_in_history)
        return len(cities_in_history) > 1

    @staticmethod
    def _rewrite_short_answer(message: str, history: list) -> str:
        """方案 B：短句上下文补全。

        当「最新一条用户消息」极短（≤10 字）且不含明确的城市/规划意图，
        而历史中最近一条 assistant 消息抛出了「选择问」（如「更喜欢历史古迹还是胡同文艺范儿？」，
        句末未必是问号，可能结尾又补了一句陈述），
        则把用户消息改写为带上下文的版本，显式告诉模型：
        「这是对上文话题（已锁定城市）的选择回答，请继承上文作答，不要泛化」。
        不满足触发条件时原样返回 message。
        """
        m = (message or "").strip()
        if not m or len(m) > 10:
            return message
        # 已自带城市/规划意图的短消息不改写
        if AIService._extract_city(m) or AIService._is_plan_intent(m):
            return message

        # 找最近一条 assistant 消息
        last_ai = ""
        for msg in reversed(history):
            if getattr(msg, "role", None) == "assistant":
                last_ai = msg.content or ""
                break
        if not last_ai:
            return message

        stripped_ai = last_ai.strip()
        # 触发条件 A：最近 assistant 消息里存在「选择问」结构
        # （如「更喜欢 A 还是 B？」「喜欢 X 还是 Y？」）。
        # 用正则匹配「选择词 + 0~15字 + 还是 + 0~15字 + 问号」，
        # 同时兜底「句末 50 字内同时出现'还是'与问号」。
        choice_q = re.search(
            r"(更喜欢|偏好|喜欢|选|想要|倾向|要).{0,15}还是.{0,15}[？?]", stripped_ai
        )
        tail = stripped_ai[-50:]
        alt_choice = ("还是" in tail) and ("？" in tail or "?" in tail)

        # 触发条件 B：Yes/No 提议确认型问句
        # 例："需要我帮你按'早餐—正餐—夜宵'排一份南昌美食打卡路线吗？"
        confirm_words = ["需要", "好的", "可以", "行", "嗯", "对", "是的", "好", "要", "想", "继续", "安排"]
        negative_markers = ["不", "别", "没", "无", "算了"]
        is_short_confirm = len(m) <= 8 and any(m == w or m.startswith(w) for w in confirm_words)
        is_negative = any(marker in m for marker in negative_markers)
        tail60 = stripped_ai[-60:]
        has_question = "？" in tail60 or "?" in tail60
        proposal_signals = ["需要我", "帮你", "给你", "安排", "规划", "排", "设计", "推荐", "做", "弄", "好吗", "行吗", "好不"]
        is_proposal_question = has_question and any(k in tail60 for k in proposal_signals)
        is_confirmation = is_short_confirm and is_proposal_question and not is_negative

        if not (choice_q or alt_choice or is_confirmation):
            return message

        # 提取上文最近一次出现的城市，作为继承背景（仅用于提示，不强行限定）
        ctx_city = AIService._extract_city_from_history(history)
        # 取最近一条 user 消息作为话题兜底锚点（白名单取不到城市时仍可用）
        last_user = ""
        for msg in reversed(history):
            if getattr(msg, "role", None) == "user":
                last_user = (msg.content or "").strip()
                break
        # 关键锚点：直接引用上一句 assistant 的真实建议原文片段。
        # 防止模型套用 SYSTEM_PROMPT_QA 里的示例模板（如"美食打卡路线"）而跑偏到无关城市/话题。
        proposal_excerpt = stripped_ai[-160:] if len(stripped_ai) > 160 else stripped_ai

        if is_confirmation:
            if ctx_city:
                return (
                    f"（上下文补全：以上一轮对话正在讨论「{ctx_city}」旅游，我上一句提出的具体建议是：「{proposal_excerpt}」，"
                    f"您用「{m}」表示同意。请直接执行【该建议本身】并继续围绕「{ctx_city}」给出具体结果，"
                    f"千万不要反问确认、不要泛化成全国范围、也不要照搬或套用提示词里的任何示例模板/城市/美食。）\n用户确认：{m}"
                )
            # 白名单取不到城市（如萍乡/武功山）时，用上一句真实建议 + 最近用户话题兜底，仍不依赖示例
            topic_hint = f"，并继承上一轮用户提到的「{last_user}」话题" if last_user else ""
            return (
                f"（上下文补全：我上一句提出的具体建议是：「{proposal_excerpt}」，您用「{m}」表示同意。"
                f"请直接执行【该建议本身】（严格基于以上对话真实内容{topic_hint}），不要反问确认，"
                f"也不要照搬或套用提示词里的任何示例模板、不要替换为其他城市或切换话题。）\n用户确认：{m}"
            )

        # 选择问分支
        if ctx_city:
            return (
                f"（上下文补全：以上一轮对话正在讨论「{ctx_city}」旅游，我上一句问的是"
                f"「更喜欢哪一类」，您这条消息是对该选择问题的回答——"
                f"请围绕「{ctx_city}」作答，给出该城市内的具体建议，"
                f"千万不要泛化成全国范围，也不要照搬提示词示例里的任何城市或景点。）\n用户回答：{m}"
            )
        # 没有可继承城市时，至少提示这是承接上文的选择，并附带上一句真实建议原文
        topic_hint2 = f"，并继承上一轮用户提到的「{last_user}」话题" if last_user else ""
        return (
            f"（上下文补全：以上一轮对话为背景（我上一句的原话是：「{proposal_excerpt}」），"
            f"您这条消息是对我上一句提问的回答，请结合完整历史连贯作答{topic_hint2}，"
            f"不要当作孤立的新问题，也不要照搬提示词示例里的任何城市或景点。）\n用户回答：{m}"
        )

    @staticmethod
    async def _understand(message: str, history) -> Optional[object]:
        """语义理解（LLM 优先）：一次性抽取意图与实体。

        返回 understand_chain 的 DialogUnderstanding；LLM 异常时返回 None，由调用方回退规则。
        """
        try:
            from services.langchain_layer.chains.understand_chain import build_understand_chain
            chain = build_understand_chain()
            return await chain.ainvoke({"message": message, "history": history})
        except Exception as e:
            logger.warning("[AI] understand_chain 失败，转规则兜底: %s", e)
            return None

    @staticmethod
    async def chat(db: Session, user_id: int, session_id: Optional[int], message: str) -> dict:
        """AI 对话主入口（Phase 4：委托 chat_chain 顶层编排，修复 M1/M4/M8）。

        门面签名不变；内部不再手写 400 行拼装/调用/解析，改为委托
        services.langchain_layer.orchestrator.build_chat_chain（LCEL 多链 + 嵌套 + 并发）。
        DB 会话管理、历史查询、行程兜底覆盖、AI 回复落库仍在链外（M7）。
        """
        import time
        _t_total = time.perf_counter()
        _t_prev = _t_total
        # 创建或获取会话
        if not session_id:
            session = ChatSession(
                user_id=user_id,
                session_title=message[:20] + "..." if len(message) > 20 else message,
                create_time=datetime.now(),
                update_time=datetime.now(),
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            session_id = session.id
        else:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                return {"success": False, "message": "会话不存在"}

        # 保存用户消息
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=message,
            create_time=datetime.now(),
        )
        db.add(user_msg)

        # 获取历史消息构建上下文（链外查 DB，M7）
        history_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.create_time)
            .all()
        )

        _t_now = time.perf_counter()
        logger.debug("[AI] 阶段耗时 | 会话与历史加载: %.1fms | 累计: %.1fms",
                     (_t_now - _t_prev) * 1000, (_t_now - _t_total) * 1000)
        _t_prev = _t_now

        # ===== 历史管控（修剪硬限 + 摘要软压缩，两段式闸门）=====
        # for_intent = 全量历史（供意图/城市判定，保确定性逻辑正确）
        # for_model = 裁剪后历史（喂模型，受 token 硬限，防超上下文窗口）
        history_cfg = {
            "max_pairs": settings.HISTORY_MAX_PAIRS,
            "max_tokens": settings.HISTORY_MAX_TOKENS,
            "trigger_pairs": settings.SUMMARY_TRIGGER_PAIRS,
            "summary_max_tokens": settings.SUMMARY_MAX_TOKENS,
        }
        from services.history_manager import HistoryManager
        prepared = HistoryManager.prepare(history_messages, session, history_cfg)
        history_full = prepared["for_intent"]
        history_for_model = prepared["for_model"]
        session_summary = prepared["summary"]
        # 仅当窗口外累计达阈值才用 LLM 重算摘要（避免每轮额外调用）
        if session_summary == "__NEED_REFRESH__":
            try:
                _dropped = history_full[: len(history_full) - len(history_for_model)]
                _new_summary = await HistoryManager.build_summary(
                    _dropped, get_chat_model(), settings.SUMMARY_MAX_TOKENS
                )
                if _new_summary:
                    session.summary = _new_summary
                    session_summary = _new_summary
            except Exception as _sum_err:
                logger.warning("[AI] 摘要重算失败，沿用旧摘要: %s", _sum_err)

        # ===== 语义理解（LLM 优先 + 规则兜底，对应方案 B）=====
        understand = await AIService._understand(message, history_full)

        # 意图：LLM 优先；置信度过低/异常时全回退规则（OR 加固）
        rule_plan = (
            AIService._is_plan_intent(message)
            or (bool(history_full) and AIService._is_plan_continuer(message, history_full))
        )
        rule_weather = AIService._is_weather_query(message)
        if understand is None or understand.confidence < 0.5:
            is_plan_det = bool(rule_plan)
            is_weather_det = bool(rule_weather)
        else:
            # LLM 优先：置信时以 understand.intent 为准，规则不反向覆盖
            # （避免 _is_plan_continuer 等脆弱规则把"承接上文的天气问句"误拉成 plan）
            if understand.intent == "plan":
                is_plan_det, is_weather_det = True, False
            elif understand.intent == "weather":
                is_plan_det, is_weather_det = False, True
            else:  # qa：规则仅在强烈判定时升级（罕见兜底）
                is_plan_det = bool(rule_plan)
                is_weather_det = bool(rule_weather)

        # 实体抽取：LLM 优先，规则兜底（各自独立回退）
        cities = (understand.cities if (understand and understand.cities) else None) \
            or AIService._extract_cities(message)
        days = (understand.days if (understand and understand.days) else None) \
            or AIService._extract_days(message)
        budget = (understand.budget if (understand and understand.budget) else None) \
            or AIService._extract_budget(message)

        # 保护：规划意图但消息与历史均无目的地城市时，降级为日常问答（反问城市），
        # 避免 LLM 在无上下文时硬生成默认行程（历史 bug）。
        if is_plan_det:
            if not cities and history_full:
                hist_city = AIService._extract_city_from_history(history_full)
                if hist_city:
                    cities = [hist_city]
            cities = [c for c in cities if c]
            if not cities:
                is_plan_det = False

        # weather_inputs：确定性算好后传给 context_chain 并发查询（链外算，M7）
        if is_plan_det:
            weather_city = cities[0] if cities else None
            weather_days = days if days else 3
        elif is_weather_det:
            # 优先取 LLM 点名的城市（覆盖白名单外城市，如鸡西）；
            # 当前消息未点名时，回退规则（含继承历史最近城市）。
            weather_city = (
                (understand.weather_city if (understand and understand.weather_city) else None)
                or AIService._extract_weather_city(message)
                or AIService._extract_city(message)
                or (AIService._extract_city_from_history(history_full) if history_full else None)
            )
            weather_days = AIService._extract_weather_days(message)
        else:
            weather_city = None
            weather_days = 3
        weather_inputs = {"city": weather_city or "", "days": weather_days}
        logger.info(
            "[AI][意图判定] session_id=%s user_id=%s is_plan_det=%s is_weather_det=%s "
            "cities=%s days=%s budget=%s history_count=%d summary=%s",
            session_id, user_id, is_plan_det, is_weather_det, cities, days, budget,
            len(history_full), bool(session_summary),
        )

        # ===== 委托 chat_chain 顶层编排（LCEL 多链 + 嵌套 + 并发）=====
        from services.langchain_layer.orchestrator import build_chat_chain
        chat_chain = build_chat_chain(weather_service=None)  # 默认真实 WeatherService 懒加载
        _t_now = time.perf_counter()
        logger.debug("[AI] 阶段耗时 | 意图与天气准备: %.1fms | 累计: %.1fms",
                     (_t_now - _t_prev) * 1000, (_t_now - _t_total) * 1000)
        _t_prev = _t_now

        try:
            chain_result = await chat_chain.ainvoke({
                "message": message,
                "history": history_for_model,
                "weather": weather_inputs,
                "prefs": {},
                "cities": cities,
                "days": days,
                "budget": budget,
                "is_plan_det": is_plan_det,
                "is_weather_det": is_weather_det,
                # 摘要刷新失败时为占位符，不注入 prompt（降级为无摘要）
                "summary": session_summary if session_summary != "__NEED_REFRESH__" else "",
            })
        except Exception as _chain_err:
            logger.error("[AI] chat_chain 编排异常: %s: %s", type(_chain_err).__name__, _chain_err, exc_info=True)
            return {
                "success": True,
                "response_type": "question_answer",
                "session_id": session_id,
                "chat_title": session.session_title,
                "answer": "抱歉，AI 暂时没能生成回复（可能是接口限流或网络异常）。请稍后重试，或把需求描述得更明确一些。",
            }

        response_type = chain_result.get("response_type")
        data = chain_result.get("data") or {}
        error_code = chain_result.get("error_code")

        # 规划分支：确定性兜底覆盖（M1 修复：用 cities[0] 文本序，替代原 _extract_city bug）
        if response_type == "itinerary":
            city = cities[0] if cities else None
            trip = data.setdefault("trip", {})
            if city:
                trip["dest_city"] = city
            if days:
                trip["travel_days"] = days
            if budget is not None:
                trip["total_budget"] = budget
            if city and days:
                data["chat_title"] = f"{city}{days}日游规划"

        # 保存 AI 回复（自然语言摘要，避免历史 assistant 为 JSON 污染上下文）
        if response_type == "itinerary":
            save_content = data.get("narrative") or f"已为您生成{data.get('chat_title', '行程规划')}"
        else:
            save_content = data.get("answer") or ""
        ai_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=save_content,
            create_time=datetime.now(),
        )
        db.add(ai_msg)
        session.update_time = datetime.now()
        db.commit()

        _t_now = time.perf_counter()
        logger.debug("[AI] 阶段耗时 | 回复落库: %.1fms | 累计: %.1fms",
                     (_t_now - _t_prev) * 1000, (_t_now - _t_total) * 1000)
        logger.debug("[AI] chat 总耗时: %.1fms", (_t_now - _t_total) * 1000)

        if response_type == "itinerary":
            return {
                "success": True,
                "response_type": "itinerary",
                "session_id": session_id,
                "chat_title": data.get("chat_title", session.session_title),
                "narrative": data.get("narrative", ""),
                "needs_save": True,
                "data": data,
                "error_code": error_code,
            }
        else:
            return {
                "success": True,
                "response_type": "question_answer",
                "session_id": session_id,
                "chat_title": data.get("chat_title", session.session_title),
                "answer": data.get("answer", ""),
                "error_code": error_code,
            }

    @staticmethod
    def _assemble_messages(message, history_messages, weather_prompt, cities, days, budget, is_plan, summary=None):
        """拼装发送给 LLM 的 messages（system + 历史自适应 + user）。

        修复 M1：城市约束统一用传入的 cities（文本序），primary_city = cities[0]，
        不再用 _extract_city（固定列表序，会导致多城市 dest_city/标题取错）。
        天气注入用传入的 weather_prompt（已在链外查好，可空）。
        本方法为纯函数（无 LLM 调用），被 orchestrator.chat_chain 的 _assemble 调用。
        """
        if is_plan:
            system_prompt = SYSTEM_PROMPT_PLAN_TOOL
            # 确定性城市注入（M1 修复：用传入 cities 文本序，primary_city=cities[0]）
            if len(cities) == 1:
                city = cities[0]
                system_prompt += (
                    f"\n\n用户明确指定的目的地城市是：{city}。"
                    f"dest_city 与每一个景点的 city 都必须严格等于「{city}」，"
                    f"不得替换为其他任何城市。"
                )
            elif len(cities) >= 2:
                city_list = "、".join(cities)
                primary_city = cities[0]
                city = primary_city
                system_prompt += (
                    f"\n\n用户提到了多个目的地城市：{city_list}。"
                    f"行程必须覆盖用户提到的全部城市——"
                    f"narrative 中每天的安排必须明确标注当天所在的城市（如『第1天（武汉）：…』），"
                    f"景点要分散在这些城市的著名景区中，每个城市至少安排 1 个景点。"
                    f"dest_city 字段使用主要城市「{primary_city}」（行程首发城市）；"
                    f"其它城市景点在其各自的 city 字段写明所属城市即可。"
                    f"严禁只覆盖其中一个城市而忽略其他城市。"
                )
            # 确定性天数注入
            if days:
                if cities:
                    title_city = "、".join(cities[:3]) if len(cities) >= 2 else (cities[0] if cities else '')
                else:
                    title_city = ''
                system_prompt += (
                    f"\n用户明确指定的游玩天数是：{days} 天。"
                    f"travel_days 必须严格等于 {days}，不得自行改为其他天数；"
                    f"chat_title 必须写成「{title_city}{days}日游规划」。"
                )
            # 确定性预算注入
            if budget is not None:
                system_prompt += (
                    f"\n用户明确指定的预算是：{budget} 元。"
                    f"total_budget 必须严格等于 {budget}，不得自行改为其他金额。"
                )
            # 天气注入（已在链外查好，可空）
            if weather_prompt:
                system_prompt += weather_prompt
                system_prompt += (
                    "\n【重要】你必须将上述天气信息嵌入到 narrative 字段的每日安排中，"
                    "在每一天的开头标注当天天气"
                    "（如'第1天（8月14日，晴转多云 26~35°C）：'），"
                    "并根据天气给出相应的出行建议（如防晒、带伞等）。"
                )
            include_history = False
            include_summary = False
        else:
            system_prompt = SYSTEM_PROMPT_QA
            # 天气注入（已在链外查好，可空）
            if weather_prompt:
                system_prompt += weather_prompt
                system_prompt += (
                    "\n【重要】以上是你可用的天气数据。"
                    "请直接根据这些数据回答用户的天气问题，给出具体城市、日期、天气状况、温度范围和风力，"
                    "不要再说'无法实时联网查询'。"
                )
            # 历史自适应（plan 不携带历史；qa 携带若无城市冲突）
            include_summary = bool(summary)
            include_history = False
            if history_messages:
                current_city = cities[0] if cities else None
                if not AIService._history_has_city_conflict(history_messages, current_city):
                    include_history = True

        messages_for_api = [{"role": "system", "content": system_prompt}]
        if include_summary:
            # 早期对话摘要（软压缩）：窗口外旧消息的 LLM 摘要，保语义同时不超 token 窗口
            messages_for_api.append({
                "role": "system",
                "content": f"【早期对话摘要】{summary}",
            })
        if include_history:
            for m in history_messages:
                role = getattr(m, "role", None) or "user"
                content = getattr(m, "content", None) or ""
                messages_for_api.append({"role": role, "content": content})
        # 始终携带当前用户消息
        effective_message = message
        if include_history:
            effective_message = AIService._rewrite_short_answer(message, history_messages)
        messages_for_api.append({"role": "user", "content": effective_message})
        return messages_for_api

    @staticmethod
    def _process_itinerary(db: Session, user_id: int, data: dict) -> Optional[int]:
        """处理 AI 生成的行程数据，写入数据库"""
        trip_data = data.get("trip", {})
        scenic_spots = data.get("scenic_spots", [])

        # 计算天数
        travel_days = trip_data.get("travel_days", 1)
        start_date_str = trip_data.get("start_date", "")
        end_date_str = trip_data.get("end_date", "")

        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        if not start_date:
            start_date = date.today() + timedelta(days=7)
        if not end_date:
            end_date = start_date + timedelta(days=travel_days - 1)

        # 创建行程记录
        trip = Trip(
            user_id=user_id,
            trip_name=trip_data.get("trip_name", "AI生成行程"),
            dest_city=trip_data.get("dest_city", ""),
            start_date=start_date,
            end_date=end_date,
            total_budget=trip_data.get("total_budget", 0),
            travel_days=travel_days,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        db.add(trip)
        db.commit()
        db.refresh(trip)

        # 处理景点和行程节点
        for spot_info in scenic_spots:
            scenic = AIService._find_or_create_scenic(db, spot_info)
            if not scenic:
                continue

            detail_info = spot_info.get("trip_detail", {})
            day_num = detail_info.get("day_num", 1)
            sort_order = detail_info.get("sort_order", 1)

            start_time = None
            end_time = None
            if detail_info.get("start_time"):
                try:
                    start_time = datetime.strptime(
                        detail_info["start_time"], "%H:%M"
                    ).time()
                except ValueError:
                    pass
            if detail_info.get("end_time"):
                try:
                    end_time = datetime.strptime(
                        detail_info["end_time"], "%H:%M"
                    ).time()
                except ValueError:
                    pass

            detail = TripDetail(
                trip_id=trip.id,
                scenic_id=scenic.id,
                start_time=start_time,
                end_time=end_time,
                remark=detail_info.get("remark", ""),
                day_num=day_num,
                sort_order=sort_order,
                spot_budget=detail_info.get("spot_budget", scenic.price or 0),
                create_time=datetime.now(),
            )
            db.add(detail)

        db.commit()
        return trip.id

    @staticmethod
    def _find_or_create_scenic(db: Session, spot_info: dict) -> Optional[ScenicSpot]:
        """查找或创建景点记录"""
        name = spot_info.get("name", "")
        city = spot_info.get("city", "")

        if not name:
            return None

        # 先按名称和城市查询是否已存在
        existing = (
            db.query(ScenicSpot)
            .filter(ScenicSpot.name == name, ScenicSpot.city == city)
            .first()
        )
        if existing:
            return existing

        # 创建新景点
        raw_tags = spot_info.get("tags")
        if isinstance(raw_tags, list):
            tags_str = json.dumps(raw_tags, ensure_ascii=False)
        elif isinstance(raw_tags, str) and raw_tags:
            tags_str = raw_tags
        else:
            tags_str = ""

        scenic = ScenicSpot(
            name=name,
            city=city,
            introduction=spot_info.get("introduction", ""),
            address=spot_info.get("address", ""),
            open_time=spot_info.get("open_time", ""),
            price=spot_info.get("price", 0),
            latitude=spot_info.get("latitude"),
            longitude=spot_info.get("longitude"),
            special_notice=spot_info.get("special_notice", ""),
            suggested_duration=spot_info.get("suggested_duration", ""),
            category=spot_info.get("category", "") or "",
            rating=spot_info.get("rating", 0) or 0,
            tel=spot_info.get("tel", "") or "",
            tags=tags_str,
            recommendation=spot_info.get("recommendation", "") or "",
            create_time=datetime.now(),
        )
        db.add(scenic)
        db.commit()
        db.refresh(scenic)
        return scenic

    @staticmethod
    def _parse_tags(tags) -> list:
        """tags 字段统一解析为列表（DB 中存 JSON 字符串或逗号分隔）"""
        if isinstance(tags, list):
            return tags
        if not tags:
            return []
        try:
            parsed = json.loads(tags)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [t.strip() for t in str(tags).split(",") if t.strip()]

    @staticmethod
    def _build_scenic_card(scenic, src: dict) -> dict:
        """把 AI 返回的结果项 + DB 记录组装成高德式卡片（以 AI 返回为主，DB id 用于后续加入行程）"""
        return {
            "id": scenic.id if scenic else None,
            "name": src.get("name") or (scenic.name if scenic else ""),
            "city": src.get("city") or (scenic.city if scenic else ""),
            "category": src.get("category", ""),
            "introduction": src.get("introduction", ""),
            "address": src.get("address", ""),
            "open_time": src.get("open_time", ""),
            "price": src.get("price", 0),
            "rating": src.get("rating", 0) or 0,
            "latitude": src.get("latitude"),
            "longitude": src.get("longitude"),
            "tel": src.get("tel", ""),
            "tags": AIService._parse_tags(src.get("tags")),
            "suggested_duration": src.get("suggested_duration", ""),
            "special_notice": src.get("special_notice", ""),
            "recommendation": src.get("recommendation", ""),
        }

    @staticmethod
    async def search_scenic(keyword: str, city: str) -> dict:
        """AI 搜索景点（高德式）：返回多个候选景点卡片列表。

        修复 M5：默认不落库。AI 幻觉出的虚假景点不应持续写入 scenic_spot 表，
        避免每次搜索 N 次 commit 造成数据堆积。卡片以 AI 返回为主组装，
        id 留空（None），待前端「加入行程」时显式经 ScenicService 持久化。
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_SCENIC_SEARCH_LIST},
            {
                "role": "user",
                "content": f"请在城市「{city}」内搜索与「{keyword}」相关的景点/地点，返回多个候选结果（列表）。",
            },
        ]

        try:
            raw = await AIService.call_deepseek_api(messages)
            ai_response_text = AIService._extract_content(raw)
            parsed = AIService.parse_json_response(ai_response_text)
            items = parsed.get("results") or []
            # 兼容：若模型仍返回单个对象（含 name 字段），包装为列表
            if not items and isinstance(parsed, dict) and parsed.get("name"):
                items = [parsed]
            if not items:
                return {"success": False, "message": "AI未返回有效搜索结果"}

            # 修复 M5：默认不落库，直接以 AI 返回组装高德式卡片（id=None）
            results = [AIService._build_scenic_card(None, it) for it in items]

            return {
                "success": True,
                "keyword": keyword,
                "city": city,
                "total": len(results),
                "results": results,
            }
        except Exception as e:
            logger.error("[AI] 景点搜索失败: %s", e, exc_info=True)
            return {"success": False, "message": f"AI搜索失败: {str(e)}"}

    @staticmethod
    async def get_scenic_detail(scenic_name: str, city: str) -> dict:
        """AI 获取景点详细信息（景区介绍、门票、注意事项、预算规划）。

        修复 M6：只读。删除原 db 落库（upsert）分支（dead code）——路由调用从未传 db，
        且该隐式写库会污染 scenic_spot 表。现仅调用 LLM 并返回详情。
        """
        # 入参校验
        if not scenic_name or not scenic_name.strip() or not city or not city.strip():
            return {"success": False, "message": "缺少景点名称或城市参数"}

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_SCENIC_DETAIL},
            {
                "role": "user",
                "content": f"请详细介绍城市「{city}」的景点「{scenic_name}」，包括景区介绍、门票价格、注意事项和预算建议。",
            },
        ]

        try:
            raw = await AIService.call_deepseek_api(messages)
            ai_response_text = AIService._extract_content(raw)
            result = AIService.parse_json_response(ai_response_text)

            detail = {
                "introduction": result.get("introduction", ""),
                "price": result.get("price", 0),
                "special_notice": result.get("special_notice", ""),
                "budget_suggestion": result.get("budget_suggestion", ""),
            }

            return {
                "success": True,
                "detail": detail,
            }
        except Exception as e:
            logger.error("[AI] 景点详情获取失败: %s", e, exc_info=True)
            return {"success": False, "message": f"AI获取详情失败: {str(e)}"}

