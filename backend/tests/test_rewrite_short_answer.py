"""回归测试：短确认句重写（_rewrite_short_answer）。

锁定此前 session 169 的漂移 bug：用户回「需要」承接助手「按天气把武功山安排一下」的提议，
助手却生成「南昌美食路线」。根因是 ctx_city 因 萍乡/武功山 不在白名单取空、且提示词示例诱导。
修复后：重写必须直接注入「上一句真实建议原文」+「最近用户话题」，不再依赖白名单城市，
且不照搬提示词示例模板。
"""

import asyncio
from types import SimpleNamespace

import pytest

from services.ai_service import AIService

Msg = lambda role, content: SimpleNamespace(role=role, content=content)  # noqa: E731


def _rewrite(message, history):
    # _rewrite_short_answer 是同步静态方法
    return AIService._rewrite_short_answer(message, history)


def test_confirmation_injects_proposal_excerpt_when_ctx_city_none():
    """萍乡/武功山 不在白名单 → ctx_city=None，但仍须注入上一句真实建议与用户话题。"""
    history = [
        Msg("user", "萍乡"),
        Msg("assistant", "萍乡啊，武功山是招牌。需要我帮你按天气把武功山那两天具体怎么安排理一理吗？"),
    ]
    out = _rewrite("需要", history)
    # 必须包含上一句真实建议的核心内容（武功山），模型才不会被示例模板带偏
    assert "武功山" in out, f"重写未注入真实建议原文：{out}"
    # 必须继承最近用户话题（萍乡）作为兜底锚点
    assert "萍乡" in out, f"重写未继承用户话题：{out}"
    # 不应出现提示词示例里的无关城市诱导
    assert "南昌" not in out, f"重写不应含诱导城市南昌：{out}"
    # 必须带有「不要套用/照搬示例模板」的护栏
    assert ("套用" in out or "照搬" in out), f"重写缺少防模板护栏：{out}"


def test_confirmation_with_known_city_still_anchors_city():
    """白名单城市（北京）时，ctx_city 命中，重写应同时带城市与真实建议。"""
    history = [
        Msg("user", "北京"),
        Msg("assistant", "北京三日游不错。需要我再帮你查一下故宫的门票预约方式吗？"),
    ]
    out = _rewrite("好的", history)
    assert "北京" in out
    assert "故宫" in out  # 上一句真实建议


def test_non_trigger_message_unchanged():
    """非承接/非确认的普通消息应原样返回，不重写。"""
    history = [Msg("user", "你好"), Msg("assistant", "你好，有什么可以帮你？")]
    out = _rewrite("帮我规划一个去杭州的旅行", history)
    assert out == "帮我规划一个去杭州的旅行"


def test_negative_confirmation_not_rewritten():
    """否定词（不需要）不应被当作确认而重写。"""
    history = [
        Msg("user", "萍乡"),
        Msg("assistant", "需要我帮你按天气把武功山安排一下吗？"),
    ]
    out = _rewrite("不需要", history)
    assert out == "不需要"
