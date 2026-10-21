"""意图识别链（LLM 分类，对应方案决策①：用 LLM 分类链替代纯规则）。

输入:  {"message": str, "history": [ChatMessage|{role,content}, ...]}（history 可选，提供上下文）
输出:  {"is_plan": bool, "is_weather": bool, "is_qa": bool}

设计要点：
- 用 LLM + JsonOutputParser 判断用户意图（规划 / 天气 / 问答）。
- 异步 RunnableLambda，便于在顶层 chat_chain 的 RunnableParallel 中与 context 并发。
- 异常降级为 qa（最保守，避免误判导致行程/天气误触发）；router 另有确定性硬守门兜底。
"""
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda

from services.langchain_layer.llm import get_chat_model

logger = logging.getLogger(__name__)

_INTENT_SYSTEM = """你是旅游对话的意图分类器。根据用户当前消息（必要时结合历史），判断其意图类别。
只输出合法 JSON 对象，结构严格如下（注意花括号是字面量，不要当作模板变量）：
{{"is_plan": <bool>, "is_weather": <bool>, "is_qa": <bool>}}
- is_plan=True 表示用户想规划完整行程（如"规划武汉3日游""帮我安排行程""北京怎么玩三天"）。
- is_weather=True 表示用户在问天气（如"北京明天天气""气温多少""会下雨吗"）。
- is_qa=True 表示普通咨询 / 闲聊 / 问答（兜底类别）。
互斥优先级：若同时像规划与天气，优先 is_plan；否则 is_weather 优先于 is_qa。
不要输出额外文字或 markdown 代码块。"""


def _history_to_text(history) -> str:
    """把 history（ChatMessage 对象或 {role, content} dict 列表）转成简短文本。"""
    if not isinstance(history, list):
        return ""
    lines = []
    for m in history[-6:]:
        content = None
        if isinstance(m, dict):
            content = m.get("content")
        else:
            content = getattr(m, "content", None)
        if content:
            lines.append(f"- {str(content)[:200]}")
    return "\n".join(lines)


def build_intent_chain(model=None, *, temperature: float = 0.0):
    """构建意图识别链（LLM 分类）。

    model: 可注入（单测用 fake model），默认真实 DeepSeek。
    """
    if model is None:
        model = get_chat_model(temperature=temperature)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _INTENT_SYSTEM),
        ("user", "历史（最近几条）:\n{history_text}\n\n当前用户消息:\n{message}\n\n请分类。"),
    ])
    model_json = model.bind(response_format={"type": "json_object"})
    chain = prompt | model_json | JsonOutputParser()

    async def _classify(inputs: dict) -> dict:
        try:
            built = {
                "message": inputs.get("message", ""),
                "history_text": _history_to_text(inputs.get("history")),
            }
            result = await chain.ainvoke(built)
            if not isinstance(result, dict):
                result = {}
            is_plan = bool(result.get("is_plan", False))
            is_weather = bool(result.get("is_weather", False))
            is_qa = bool(result.get("is_qa", False))
            # 优先级兜底：plan > weather > qa
            if is_plan:
                is_weather = False
            if not (is_plan or is_weather):
                is_qa = True
            return {"is_plan": is_plan, "is_weather": is_weather, "is_qa": is_qa}
        except Exception as e:
            logger.warning("intent_chain 异常降级为 qa: %s", e)
            return {"is_plan": False, "is_weather": False, "is_qa": True}

    return RunnableLambda(_classify)
