"""问答链（qa_chain）：纯 JSON 问答 + 空回复兜底重试。

输入:  {"messages": [{role, content}, ...]}  （已由路由层拼好 system + history + user）
输出:  归一化后的 QA dict，形如 {"response_type": "question_answer", "chat_title": ..., "answer": ...}

要点（延续旧工程稳健策略，修复 M3 可观测）：
- 主链：messages → model(json_object) → JsonOutputParser → 归一化校验。
- 归一化：模型常把正文包在 data 子字段，上提以便统一读取（与旧 chat() 一致）。
- 空回复重试：answer 为空或解析非 dict 时抛 _EmptyAnswerError，
  经 with_fallbacks 触发重试链（追加系统补注，**严禁**假设用户在确认行程，
  不复用旧 bug 的"3 日游" coerce 逻辑）。
- 全程 logging 替代 print。
"""
import logging

from langchain_core.runnables import RunnableLambda

from services.langchain_layer.llm import get_chat_model
from services.langchain_layer.chains.base import build_messages_json_chain

logger = logging.getLogger(__name__)


class _EmptyAnswerError(Exception):
    """QA 结果为空（answer 缺失/空串/非 dict）时抛出，用于触发 with_fallbacks 重试。"""


# 空回复重试补注：仅要求基于历史正常回答最新一条消息，绝不 coerce 行程。
_QA_RETRY_NOTE = {
    "role": "user",
    "content": (
        "（系统补注：你上一轮回复出现了空白内容，已被丢弃，请勿向用户提及此事。）\n"
        "你是友好的旅游助手。请基于【完整对话历史】，针对用户【最新一条消息】给出自然、准确的中文回复；"
        "不要生成完整行程规划，也不要调用任何工具。\n"
        "请只输出合法 JSON 对象，结构严格如下：\n"
        '{"response_type":"question_answer","data":{"chat_title":"<简短会话标题>","answer":"<针对用户最新消息的真实中文回复>"}}\n'
        "answer 字段必须填入真正的回复内容，绝对不要照抄占位符、不要只输出空格、不要反问无关问题。"
    ),
}


def _normalize_qa(data: dict) -> dict:
    """归一化 QA 结果：上提 data 子字段、校验 answer 非空。"""
    if not isinstance(data, dict):
        raise _EmptyAnswerError("qa 解析结果非 dict")
    inner = data.get("data")
    if isinstance(inner, dict):
        for k, v in inner.items():
            data.setdefault(k, v)
        data.pop("data", None)
    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise _EmptyAnswerError("qa answer 为空")
    return data


def build_qa_chain(model=None, *, temperature: float = 0.3):
    """构建问答链（含空回复重试兜底）。

    model: 可注入（单测用 SeqChatModel），默认真实 DeepSeek。
    """
    if model is None:
        model = get_chat_model(temperature=temperature)

    primary = build_messages_json_chain(model=model) | RunnableLambda(_normalize_qa)

    async def _retry(inputs: dict) -> dict:
        retry_messages = inputs["messages"] + [_QA_RETRY_NOTE]
        return await (build_messages_json_chain(model=model) | RunnableLambda(_normalize_qa)).ainvoke(
            {"messages": retry_messages}
        )

    # with_fallbacks：主链抛 _EmptyAnswerError / 解析异常 → 触发重试链（追加补注）
    return primary.with_fallbacks([RunnableLambda(_retry)])
