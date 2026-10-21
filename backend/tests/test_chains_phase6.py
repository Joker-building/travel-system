"""Phase 6 回归：删除旧 run_itinerary_agent 智能体后，顶层编排入口收敛到 build_chat_chain。

零真实 LLM / 零网络。
"""
import pytest

from services.langchain_layer import orchestrator
import services.langchain_layer as pkg  # 包 __init__


# ---------------------------------------------------------------------------
# 删除旧智能体后，符号应从模块与包导出中彻底消失（防止回潮）
# ---------------------------------------------------------------------------
def test_run_itinerary_agent_removed_from_module():
    assert not hasattr(orchestrator, "run_itinerary_agent"), \
        "run_itinerary_agent 应在 Phase 6 删除，不应残留在 orchestrator 模块"


def test_run_itinerary_agent_not_exported_from_package():
    assert "run_itinerary_agent" not in getattr(pkg, "__all__", []), \
        "run_itinerary_agent 不应再出现在 langchain_layer 包的导出列表"


def test_build_chat_chain_is_the_top_level_entry():
    assert hasattr(orchestrator, "build_chat_chain"), \
        "build_chat_chain 应作为顶层对话编排入口存在"
    assert callable(orchestrator.build_chat_chain)


def test_ai_service_no_longer_imports_run_itinerary_agent():
    # ai_service 不应再持有 run_itinerary_agent 名字（残留 import 会让模块加载即报错）
    import services.ai_service as ai
    assert not hasattr(ai, "run_itinerary_agent")
