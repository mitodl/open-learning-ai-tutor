import json
from typing import Literal

from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from open_learning_ai_tutor.tools import execute_python, python_calculator
from open_learning_ai_tutor.summarization import CustomSummarizationNode
from langchain_core.messages.utils import count_tokens_approximately
from open_learning_ai_tutor.prompts import INITIAL_SUMMARY_PROMPT, EXISTING_SUMMARY_PROMPT, FINAL_SUMMARY_PROMPT    
    
class Assesor:
    def __init__(self, client, tools=None) -> None:
        if tools is None:
            tools = [execute_python, python_calculator]

        client = client.bind_tools(tools)
        tool_node = ToolNode(tools)

        self.client = client

        def should_continue(state: MessagesState) -> Literal["tools", END]:
            messages = state["messages"]
            last_message = messages[-1]
            # If the LLM makes a tool call, then we route to the "tools" node
            if last_message.tool_calls:
                return "tools"
            # Otherwise, we stop (reply to the user)
            return END

        def call_model(state: MessagesState):
            messages = state["messages"]
            response = self.client.invoke(messages)
            # We return a list, because this will get added to the existing list
            return {"messages": [response]}

        workflow = StateGraph(MessagesState)

        workflow.add_node("agent", call_model)

        workflow.add_node("tools", tool_node)

        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            should_continue,
        )

        workflow.add_edge("tools", "agent")

        app = workflow.compile()
        self.app = app

    def get_response(self, prompt):
        return self.app.invoke({"messages": prompt})


class Tutor:
    def __init__(self, client, tools=None) -> None:
        if tools is None:
            tools = [execute_python, python_calculator]

        client = client.bind_tools(tools)
        tool_node = ToolNode(tools)
        
        max_summary_tokens = 4000
        max_tokens = 8000

        summarization_node = CustomSummarizationNode(
            token_counter=count_tokens_approximately,
            model=client.bind(max_tokens=max_summary_tokens),
            max_tokens=int(max_tokens),
            max_tokens_before_summary=max_tokens,
            max_summary_tokens=max_summary_tokens,
            output_messages_key="llm_input_messages",
            initial_summary_prompt=INITIAL_SUMMARY_PROMPT,
            existing_summary_prompt=EXISTING_SUMMARY_PROMPT,
            final_prompt=FINAL_SUMMARY_PROMPT,
        )

        self.client = client

        def should_continue(state: MessagesState) -> Literal["tools", END]:
            messages = state["messages"]
            last_message = messages[-1]
            # If the LLM makes a tool call, then we route to the "tools" node
            if last_message.tool_calls:
                return "tools"
            # Otherwise, we stop (reply to the user)
            return END

        def call_model(state: MessagesState):
            messages = state["messages"]
            response = self.client.invoke(messages)
            # We return a list, because this will get added to the existing list
            return {"messages": [response]}

        workflow = StateGraph(MessagesState)

        workflow.add_node("agent", call_model)
        workflow.add_node("summarize", summarization_node)

        workflow.add_node("tools", tool_node)

        workflow.add_edge(START, "summarize")
        workflow.add_edge("summarize", "agent")
        workflow.add_conditional_edges(
            "agent",
            should_continue,
        )

        workflow.add_edge("tools", "agent")

        app = workflow.compile()
        self.app = app

    def get_streaming_response(self, prompt):
        return self.app.astream(
            {"messages": prompt}, stream_mode=["messages", "values"]
        )
