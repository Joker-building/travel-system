"""路由链（RunnableBranch）：按意图把 assembled 结果路由到对应子链。

输入:  assemble 阶段的输出 dict，必须含：
         - "messages": [{role, content}, ...]   （拼装好的完整消息，子链直接取）
         - "is_plan": bool
         - "is_weather": bool
输出:  对应子链的产出（plan_chain → tool_calls 列表 [{name,args,id,type}, ...]；
        qa_chain → 归一化 QA dict）

设计要点（chain 内嵌 chain）：
- 用 RunnableBranch 实现「链包链」：顶层 chat_chain 在 assemble 之后，
  根据意图选择执行 plan_chain 或 qa_chain（两者都是 LCEL 链）。
- plan / qa 子链都通过 inputs["messages"] 取消息，因此可直接作为分支链，
  无需额外包装（assemble 输出已含 messages 键）。
- 优先级：is_plan > is_weather（weather_qa 走 qa_chain，只是 system prompt 已注入天气）；
  两者皆否 → 默认 qa_chain。
"""
from langchain_core.runnables import RunnableBranch

from services.langchain_layer.chains.qa_chain import build_qa_chain
from services.langchain_layer.chains.plan_chain import build_plan_chain


def build_router_chain(*, plan_chain=None, qa_chain=None, tools, model=None):
    """构建意图路由链。

    plan_chain / qa_chain: 可注入已构建的子链；缺省则现场构建。
    tools: plan_chain 必需，ITINERARY_TOOL 等工具定义。
    model: 可注入（单测用 fake model）。
    """
    if qa_chain is None:
        qa_chain = build_qa_chain(model=model)
    if plan_chain is None:
        plan_chain = build_plan_chain(model=model, tools=tools)

    return RunnableBranch(
        (lambda x: bool(x.get("is_plan")), plan_chain),
        (lambda x: bool(x.get("is_weather")), qa_chain),
        qa_chain,  # 默认分支
    )
