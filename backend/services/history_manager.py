"""对话历史管控：修剪（硬限）+ 摘要（软压缩）。

设计（对应 Langchain 记忆课件 图2/3/4）：
- trim_history：最近 N 配对截取（last 策略）+ token 上限成对 pop（max_tokens 策略）。
  成对删除保证 user/assistant 数量平衡，避免破坏对话结构。
- prepare：编排入口。返回
    for_model  —— 裁剪后历史（喂模型，受 token 硬限）
    for_intent —— 全量历史（供意图/城市判定，保确定性逻辑正确）
    summary    —— 当前会话摘要（"" / 旧摘要 / "__NEED_REFRESH__" 触发重算）
- build_summary：把窗口外的旧消息用 LLM 压成一段摘要（一次调用，结果缓存到 session）。

纯函数 + 少量静态工具，便于单测（零 DB / 零真实 LLM）。
"""
import logging
from typing import List, Optional, Sequence

logger = logging.getLogger(__name__)

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")  # DeepSeek 无官方编码，cl100k_base 近似
except Exception:
    _ENC = None


def count_tokens(text: str) -> int:
    """近似 token 计数：tiktoken 优先，缺失时按 len//2（中文偏宽）回退。"""
    if not text:
        return 0
    if _ENC is not None:
        return len(_ENC.encode(text))
    return max(len(text) // 2, 1)


def _to_pair_list(messages: Sequence) -> List[dict]:
    """DB ChatMessage 或 {role,content} dict 归一为 [{role, content}]。"""
    out = []
    for m in messages:
        if isinstance(m, dict):
            role = m.get("role")
            content = m.get("content") or ""
        else:
            role = getattr(m, "role", None)
            content = getattr(m, "content", None) or ""
        if role:
            out.append({"role": role, "content": content})
    return out


def _total_tokens(pairs: List[dict]) -> int:
    return sum(count_tokens(p["content"]) for p in pairs)


def trim_history(messages: Sequence, max_pairs: int, max_tokens: int) -> List[dict]:
    """修剪：① 最近 N 配对截取 ② token 上限成对 pop（从最旧开始）。"""
    pairs = _to_pair_list(messages)
    # ① 最近 N 配对（保留尾部）
    if max_pairs and len(pairs) > max_pairs * 2:
        pairs = pairs[-(max_pairs * 2):]
    # ② token 上限成对 pop（保持 user/assistant 平衡）
    while pairs and _total_tokens(pairs) > max_tokens:
        if len(pairs) >= 2:
            pairs = pairs[2:]
        else:
            pairs = pairs[1:]
        if not pairs:
            break
    return pairs


async def build_summary(old_messages: Sequence, llm, max_tokens: int) -> str:
    """用 LLM 把窗口外的旧消息压成一段摘要。失败返回 ""（不阻断主流程）。"""
    if not old_messages:
        return ""
    convo = "\n".join(
        f"{m['role']}: {m['content']}" for m in _to_pair_list(old_messages)
    )
    prompt = (
        f"请用不超过 {max_tokens} 字总结以下旅游对话的核心要点，"
        "包括：目的地城市、游玩天数、预算、用户偏好、已确认的行程安排。"
        "只输出摘要本身，不要解释：\n" + convo
    )
    try:
        resp = await llm.ainvoke(prompt)
        return (getattr(resp, "content", None) or str(resp)).strip()
    except Exception as e:
        logger.warning("摘要生成失败，降级为空: %s", e)
        return ""


def prepare(history_full, session, cfg: dict) -> dict:
    """编排：返回 {for_model, for_intent, summary}。

    - for_intent = 全量历史（意图/城市判定用）
    - for_model  = 裁剪后历史（喂模型用）
    - summary    = 现有摘要；仅当窗口外累计达阈值才置 "__NEED_REFRESH__"
    """
    for_intent = _to_pair_list(history_full)
    windowed = trim_history(history_full, cfg["max_pairs"], cfg["max_tokens"])
    dropped = for_intent[: len(for_intent) - len(windowed)]
    summary = getattr(session, "summary", None) or ""
    if dropped and len(dropped) >= cfg["trigger_pairs"] * 2:
        summary = "__NEED_REFRESH__"
    return {"for_model": windowed, "for_intent": for_intent, "summary": summary}


class HistoryManager:
    """门面类：组合上面的纯函数，便于调用与测试。"""

    count_tokens = staticmethod(count_tokens)
    _total_tokens = staticmethod(_total_tokens)
    trim_history = staticmethod(trim_history)
    build_summary = staticmethod(build_summary)
    prepare = staticmethod(prepare)
