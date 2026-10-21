"""景点搜索链（scenic_search_chain）：高德式多候选 POI 搜索。

输入:  {"messages": [{role, content}, ...]}  （system=搜索提示 + user=城市+关键词）
输出:  {"results": [候选卡片 dict, ...]}

要点（修复 M5：默认不落库）：
- 链只负责「调用 LLM → 解析 JSON」，不触碰数据库。
- 兼容模型偶发返回单个对象（含 name）的情况，自动包装为列表。
- 落库由调用方显式触发（或独立 persist 链），避免幻觉景点堆积到 scenic_spot 表。
"""
import logging

from langchain_core.runnables import RunnableLambda

from services.langchain_layer.chains.base import build_messages_json_chain

logger = logging.getLogger(__name__)


def _normalize_search(data) -> dict:
    if not isinstance(data, dict):
        return {"results": []}
    items = data.get("results") or []
    # 兼容：模型返回单个对象（含 name 字段）时，包装为列表
    if not items and isinstance(data.get("name"), str):
        items = [data]
    return {"results": items if isinstance(items, list) else []}


def build_scenic_search_chain(model=None, *, temperature: float = 0.3):
    """构建景点搜索链（默认不落库）。

    model: 可注入（单测用 SeqChatModel），默认真实 DeepSeek。
    """
    return build_messages_json_chain(model=model, temperature=temperature) | RunnableLambda(_normalize_search)
