"""景点详情链（scenic_detail_chain）：单景点深度介绍。

输入:  {"messages": [{role, content}, ...]}  （system=详情提示 + user=城市+景点名）
输出:  dict，形如 {"introduction", "price", "special_notice", "budget_suggestion"}

要点（修复 M6：只读，删除 db 落库分支）：
- 链只负责「调用 LLM → 解析 JSON」，返回详情 dict。
- 不接收 db、不写 scenic_spot 表；落库（upsert）由调用方显式决定，
  避免 dead code 与隐式写库污染数据。
"""
import logging

from services.langchain_layer.chains.base import build_messages_json_chain

logger = logging.getLogger(__name__)


def build_scenic_detail_chain(model=None, *, temperature: float = 0.3):
    """构建景点详情链（只读，不落库）。

    model: 可注入（单测用 SeqChatModel），默认真实 DeepSeek。
    """
    return build_messages_json_chain(model=model, temperature=temperature)
