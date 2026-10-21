"""结构化理解链（LLM 优先 + 规则兜底，对应方案 B）。

输入:  {"message": str, "history": [ChatMessage|{role,content}, ...]}（history 提供上下文）
输出:  DialogUnderstanding（intent / cities / days / budget / weather_city / is_continuation / confidence）

设计要点：
- 用一次 LLM 结构化抽取，替代原有的散落规则（`_extract_cities` / `_extract_days` / `_extract_budget`
  / `_extract_weather_city` / `_is_plan_intent` 等）。
- 异常或低置信时返回 intent="qa"、confidence=0.0，由调用方（chat()）回退既有规则（双保险）。
- 承接上文能力（"细化下""明天呢"）依赖 history：模型自行从上下文继承城市/天数。
- 复用 intent_chain 的 _history_to_text，避免重复。
"""
import logging
from typing import List, Literal, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

from services.langchain_layer.chains.intent_chain import _history_to_text
from services.langchain_layer.llm import get_chat_model

logger = logging.getLogger(__name__)


class DialogUnderstanding(BaseModel):
    intent: Literal["plan", "weather", "qa"] = Field(default="qa")
    cities: List[str] = Field(default_factory=list)
    days: Optional[int] = None
    budget: Optional[int] = None
    weather_city: Optional[str] = None
    is_continuation: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


_SYSTEM = """你是旅游对话的语义理解模块。阅读【当前消息】与【近期上下文】，输出结构化理解（JSON）。
规则：
- intent: "plan"=规划完整行程；"weather"=询问天气；"qa"=其他咨询/闲聊/问答。
- cities: 用户提及或意图前往的城市（中文全称），可多个；无则 []。
- days: 游玩天数（整数），未提及则 null。
- budget: 预算总额（整数，单位元），未提及则 null。
- weather_city: 若用户在问天气，点名的城市；否则 null。
- is_continuation: 当前消息是否承接/细化上文（如"细化下""那住宿呢""第二天呢"），是则 true。
- confidence: 你对本理解的确信度，0~1 浮点数。
仅输出 JSON，不要额外文字或 markdown 代码块。"""


def _coerce_int(v):
    try:
        return int(v) if v not in (None, "") else None
    except Exception:
        return None


def _coerce_float(v):
    try:
        return max(0.0, min(1.0, float(v)))
    except Exception:
        return 1.0


def build_understand_chain(model=None, *, temperature: float = 0.0):
    """构建结构化理解链。

    model: 可注入（单测用 fake model），默认真实 DeepSeek。
    """
    if model is None:
        model = get_chat_model(temperature=temperature)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM),
        ("user", "【近期上下文】\n{history_text}\n\n【当前消息】\n{message}"),
    ])
    model_json = model.bind(response_format={"type": "json_object"})
    parser = JsonOutputParser()
    chain = prompt | model_json | parser

    async def _understand(inputs: dict) -> DialogUnderstanding:
        try:
            built = {
                "message": inputs.get("message", ""),
                "history_text": _history_to_text(inputs.get("history")),
            }
            raw = await chain.ainvoke(built)
            if not isinstance(raw, dict):
                raw = {}
            intent = raw.get("intent") or "qa"
            if intent not in ("plan", "weather", "qa"):
                intent = "qa"
            cities = raw.get("cities") or []
            if not isinstance(cities, list):
                cities = [cities]
            cities = [str(c) for c in cities if c]
            return DialogUnderstanding(
                intent=intent,
                cities=cities,
                days=_coerce_int(raw.get("days")),
                budget=_coerce_int(raw.get("budget")),
                weather_city=raw.get("weather_city") or None,
                is_continuation=bool(raw.get("is_continuation", False)),
                confidence=_coerce_float(raw.get("confidence", 1.0)),
            )
        except Exception as e:
            logger.warning("understand_chain 异常降级为 qa: %s", e)
            return DialogUnderstanding(
                intent="qa", cities=[], days=None, budget=None,
                weather_city=None, is_continuation=False, confidence=0.0,
            )

    return RunnableLambda(_understand)
