"""history_manager 单测：修剪（成对截断 + token 上限）/ 摘要触发标志 / token 计数。

全部纯函数，零 DB / 零真实 LLM。
"""
from services.history_manager import HistoryManager


def _msgs(n, base="m"):
    out = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        out.append({"role": role, "content": f"{base}{i}"})
    return out


def test_trim_keeps_recent_pairs():
    """最近 N 配对：只保留尾部 N 个 (user,assistant) 配对。"""
    out = HistoryManager.trim_history(_msgs(30), max_pairs=5, max_tokens=10 ** 9)
    assert len(out) == 10
    assert out[0]["content"] == "m20"


def test_trim_pops_by_token_paired():
    """token 上限：从最旧开始成对 pop，且 user/assistant 数量始终相等（结构不被破坏）。"""
    msgs = [{"role": "user", "content": "x" * 500},
            {"role": "assistant", "content": "y" * 500}] * 20
    out = HistoryManager.trim_history(msgs, max_pairs=1000, max_tokens=1500)
    assert HistoryManager._total_tokens(out) <= 1500
    users = sum(1 for m in out if m["role"] == "user")
    assts = sum(1 for m in out if m["role"] == "assistant")
    assert users == assts


def test_count_tokens_approx():
    """tiktoken 可用时返回正数；空串为 0。"""
    assert HistoryManager.count_tokens("") == 0
    assert HistoryManager.count_tokens("hello world") > 0


def test_prepare_short_no_summary():
    """短对话：不触发摘要，for_model == for_intent == 全量。"""
    class S:
        summary = None

    msgs = _msgs(6)
    r = HistoryManager.prepare(msgs, S(), {
        "max_pairs": 12, "max_tokens": 6000,
        "trigger_pairs": 8, "summary_max_tokens": 400,
    })
    assert r["summary"] == ""
    assert len(r["for_model"]) == 6
    assert len(r["for_intent"]) == 6


def test_prepare_long_triggers_refresh():
    """长对话：窗口外累计达阈值 → summary 置 __NEED_REFRESH__；for_model 仅留最近窗口。"""
    class S:
        summary = None

    msgs = _msgs(40)
    r = HistoryManager.prepare(msgs, S(), {
        "max_pairs": 5, "max_tokens": 6000,
        "trigger_pairs": 8, "summary_max_tokens": 400,
    })
    assert r["summary"] == "__NEED_REFRESH__"
    assert len(r["for_model"]) == 10  # 5 pairs * 2


def test_prepare_respects_existing_summary_when_no_new_drop():
    """已有摘要且窗口外未新增 → 沿用旧摘要，不重算。"""
    class S:
        summary = "旧摘要"

    msgs = _msgs(10)
    r = HistoryManager.prepare(msgs, S(), {
        "max_pairs": 12, "max_tokens": 6000,
        "trigger_pairs": 8, "summary_max_tokens": 400,
    })
    assert r["summary"] == "旧摘要"
    assert len(r["for_model"]) == 10


def test_assemble_messages_injects_summary_in_qa():
    """QA 分支携带历史时，摘要作为前置 system 上下文注入（软压缩生效）。"""
    from services.ai_service import AIService
    messages = AIService._assemble_messages(
        message="故宫几点开门", history_messages=[], weather_prompt="",
        cities=[], days=None, budget=None, is_plan=False,
        summary="用户想去北京3日游，预算3000",
    )
    assert any("【早期对话摘要】" in m["content"] for m in messages)


def test_assemble_messages_no_summary_when_none():
    """无摘要时不注入额外上下文。"""
    from services.ai_service import AIService
    messages = AIService._assemble_messages(
        message="你好", history_messages=[], weather_prompt="",
        cities=[], days=None, budget=None, is_plan=False, summary=None,
    )
    assert not any("【早期对话摘要】" in m["content"] for m in messages)
