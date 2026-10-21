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


# ---------------------------------------------------------------------------
# 天气城市提取修复：白名单之外城市（如鸡西）也能从"XX天气"模式取出，
# 避免静默回退到历史城市造成城市串味（问鸡西却回深圳天气）。
# ---------------------------------------------------------------------------
def test_extract_weather_city_outside_whitelist():
    import services.ai_service as ai
    # 鸡西不在 _KNOWN_CITIES 白名单，但应被天气模式提取
    assert ai.AIService._extract_weather_city("鸡西这几天的天气情况") == "鸡西"
    assert ai.AIService._extract_city("鸡西这几天的天气情况") is None  # 对照组：旧逻辑取不到


def test_extract_weather_city_common_patterns():
    import services.ai_service as ai
    assert ai.AIService._extract_weather_city("北京天气") == "北京"
    assert ai.AIService._extract_weather_city("上海的气温") == "上海"
    assert ai.AIService._extract_weather_city("成都未来三天天气") == "成都"
    assert ai.AIService._extract_weather_city("我想知道哈尔滨的天气") == "哈尔滨"


def test_extract_weather_city_recent_time_words():
    """回归：覆盖「最近 / 近期 / 最近几天 / 近N天 / 近N周」等时间词（原 bug 把『鸡西最近天气』误抓成『西最近』）。"""
    import services.ai_service as ai
    # 直接复现日志暴露的两个失败用例
    assert ai.AIService._extract_weather_city("鸡西最近天气") == "鸡西"
    assert ai.AIService._extract_weather_city("鞍山最近几天的天气") == "鞍山"
    # 其它时间词变体
    assert ai.AIService._extract_weather_city("哈尔滨近期天气") == "哈尔滨"
    assert ai.AIService._extract_weather_city("北京近三天天气") == "北京"
    assert ai.AIService._extract_weather_city("广州近一周天气") == "广州"


def test_extract_weather_city_no_city_falls_back_to_none():
    import services.ai_service as ai
    # 未点名城市 —— 应返回 None，交由调用方继承历史城市
    assert ai.AIService._extract_weather_city("明天天气怎么样") is None
    assert ai.AIService._extract_weather_city("这几天的天气") is None
    assert ai.AIService._extract_weather_city("这里的天气") is None
    assert ai.AIService._extract_weather_city("天气怎么样") is None


def test_extract_weather_city_rejects_verb_phrase():
    import services.ai_service as ai
    # "到哈尔滨天气" 中动词前缀（到）不应污染城市：白名单兜底仍能正确取出哈尔滨
    assert ai.AIService._extract_weather_city("到哈尔滨天气") == "哈尔滨"


def test_extract_weather_city_whitelisted_with_tian():
    import services.ai_service as ai
    # 含"天"的白名单城市（天津）即便走通用提取也应被正确取出
    assert ai.AIService._extract_weather_city("天津天气") == "天津"


def test_extract_weather_city_rejects_time_words():
    import services.ai_service as ai
    # 时间/天数词不应被误判为城市（旧逻辑会把"三天"当城市）
    assert ai.AIService._extract_weather_city("未来三天天气") is None
    assert ai.AIService._extract_weather_city("三天天气") is None


def test_weather_city_prefers_current_message_over_history():
    """天气查询：当前消息点名城市应优先于历史城市（修复前的 bug 正是回退到历史）。"""
    import services.ai_service as ai

    class _Msg:
        def __init__(self, role, content):
            self.role = role
            self.content = content

    # 历史最近城市是深圳，但当前消息问鸡西
    history = [_Msg("user", "深圳"), _Msg("user", "深圳湾公园")]
    resolved = (
        ai.AIService._extract_weather_city("鸡西这几天的天气情况")
        or ai.AIService._extract_city("鸡西这几天的天气情况")
        or ai.AIService._extract_city_from_history(history)
    )
    assert resolved == "鸡西"  # 修复前这里会解析成 "深圳"

