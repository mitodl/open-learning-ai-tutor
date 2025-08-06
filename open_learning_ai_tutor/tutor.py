import json
from typing import Literal

from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from open_learning_ai_tutor.tools import execute_python, python_calculator
from langchain_core.messages import SystemMessage

class Tutor:

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

    def get_streaming_response(self, prompt):
        return self.app.astream(
            {"messages": prompt}, stream_mode=["messages", "values"]
        )


class CanvasTutor(Tutor):
    """
    A specialized tutor for Canvas problems.
    This class can be extended to add more specific tools or functionality.
    """



    def __init__(self, client, tools=None) -> None:
        if tools is None:
            tools = [execute_python, python_calculator]

        client = client.bind_tools(tools)
        tool_node = ToolNode(tools)
        self.client = client

        class CanvasTutorState(MessagesState):
            problem_title: str = None

        def should_continue(state: CanvasTutorState) -> Literal["tools", "ask_problem_title", END]:
            messages = state["messages"]
            last_message = messages[-1]
            # If the LLM makes a tool call, then we route to the "tools" node
            if not getattr(state, "problem_title", None):
                return "ask_problem_title"
           
            if last_message.tool_calls:
                return "tools"
            # Otherwise, we stop (reply to the user)
            return END
        
        def call_model(state: CanvasTutorState):
            messages = state["messages"]
            response = self.client.invoke(messages)
            # We return a list, because this will get added to the existing list
            return {"messages": [response]}
        
        def ask_problem_title(state: CanvasTutorState):
            messages = state["messages"]
            # Add a message asking for the problem title
            system_message = SystemMessage(
                role="system",
                content="What problem are you working on?",
            )
            return {"messages": messages + [system_message]}
       
        workflow = StateGraph(CanvasTutorState)

        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        workflow.add_node("ask_problem_title", ask_problem_title)


        workflow.add_edge(START, "agent")

        workflow.add_conditional_edges(
            "agent",
            should_continue,
        )

        workflow.add_edge("tools", "agent")
        workflow.add_edge("ask_problem_title", "agent")

        app = workflow.compile()
        self.app = app

    def get_response(self, prompt,  problem_title=None):
        state = {"messages": prompt, "problem_title": problem_title}
        return self.app.invoke(state)

    def get_streaming_response(self, prompt, problem_title=None):
        state = {"messages": prompt, "problem_title": problem_title}
        return self.app.astream(state, stream_mode=["messages", "values"])