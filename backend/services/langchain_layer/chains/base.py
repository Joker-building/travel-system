"""Langchain LCEL 链工厂与公共原语（Phase 1 基础设施）。

提供两条最基础的链工厂：
- build_json_chain  : prompt | model(json_object) | JsonOutputParser
- build_tool_chain : prompt | model.bind_tools   | 工具参数解析

以及公共解析原语 _parse_tool_calls。所有工厂允许注入 model，便于单测用 fake model 替代真实 DeepSeek。
后续 Phase 2 的 qa/plan/scenic*/weather 链均在此基础上组合（含 RunnableParallel / RunnableBranch / with_fallbacks）。
"""
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda

from services.langchain_layer.llm import get_chat_model
from services.langchain_layer.messages import to_langchain_messages

logger = logging.getLogger(__name__)


def messages_to_lc_runnable():
    """把链输入 dict 中的 messages 字段（[{role, content}]）转为 Langchain 消息列表。

    约定所有「接收已拼装消息」的链都以 {"messages": [...]} 为输入，
    从而与 chat() 中 messages_for_api 的拼装逻辑解耦（链只管 LLM + 解析）。
    """
    return RunnableLambda(lambda inputs: to_langchain_messages(inputs["messages"]))


def build_messages_json_chain(model=None, *, temperature: float = 0.3):
    """构建「接收已拼装消息 → 产出 JSON dict」的链。

    输入:  {"messages": [{role, content}, ...]}
    链路:  to_langchain_messages | model(json_object) | JsonOutputParser
    输出:  解析后的 dict（解析失败会抛异常，可接 with_fallbacks 重试）。
    model 可注入（单测用 SeqChatModel），默认走 get_chat_model() 真实 DeepSeek。
    """
    if model is None:
        model = get_chat_model(temperature=temperature)
    model = model.bind(response_format={"type": "json_object"})
    return messages_to_lc_runnable() | model | JsonOutputParser()


def build_json_chain(system_prompt: str, *, temperature: float = 0.3, model=None):
    """构建 JSON 输出链：prompt | model(json_object) | JsonOutputParser。

    适用于问答、景点搜索/详情等「模型直接产出结构化 JSON」的场景。
    model 可注入（单测用 FakeListChatModel），默认走 get_chat_model() 真实 DeepSeek。
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{input}"),
    ])
    if model is None:
        model = get_chat_model(temperature=temperature)
    model = model.bind(response_format={"type": "json_object"})
    return prompt | model | JsonOutputParser()


def build_tool_chain(system_prompt: str, tools: list, *, tool_choice="required",
                    temperature: float = 0.3, model=None):
    """构建 tool-calling 链：prompt | model.bind_tools | 工具参数解析。

    适用于行程规划等「强制调用某个 function」的场景。
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{input}"),
    ])
    if model is None:
        model = get_chat_model(temperature=temperature)
    model = model.bind_tools(tools, tool_choice=tool_choice)
    return prompt | model | RunnableLambda(_parse_tool_calls)


def _parse_tool_calls(ai_msg):
    """从 AIMessage 提取 tool_calls 为可序列化列表（name/args/id/type）。"""
    tool_calls = getattr(ai_msg, "tool_calls", None) or []
    return [
        {
            "name": tc.get("name"),
            "args": tc.get("args"),
            "id": tc.get("id"),
            "type": tc.get("type", "function"),
        }
        for tc in tool_calls
    ]
