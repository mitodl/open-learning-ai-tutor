import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from open_learning_ai_tutor.tools import execute_python, python_calculator


def get_inital_prompt(problem, problem_set):
    prompt = f"""A student and their tutor are working on a math problem:
*Problem Statement*:
{problem}

This problem is in xml format and includes a solution. The problem is part of a problem set.

*Problem Set*:

{problem_set}

Some information required to solve the problem may be in other parts of the problem set.

The tutor's utterances are preceded by "Tutor:" and the student's utterances are preceded by "Student:".

Analyze the last student's utterance.
select all the feedbacks that apply from "a,b,c,d,e,f,g,h,i,j,k,l,m":

a) The student is using or suggesting a wrong method or taking a wrong path to solve the problem
b) The student made an error in the algebraic manipulation
c) The student made a numerical error
d) The student provided an intuitive or incomplete solution
e) The student's answer is not clear or ambiguous
f) The student correctly answered the tutor's previous question
g) The student is explicitly asking about how to solve the problem
h) The student is explicitly asking the tutor to state a specific theorem, definition, formula or programming command that is not the **direct answer** to the question they have to solve.
i) The student is explicitly asking the tutor to perform a numerical calculation
j) The student and tutor arrived at a complete solution for the entirety of the initial *Problem Statement*
k) The student and tutor arrived at a complete solution for the entirety of the initial *Problem Statement* equivalent to the method provided in the *Provided Solution*
l) The student's message is *entirely* irrelevant to the problem at hand or to the material covered by the exercise.
m) The student is asking about concepts or information related to the material covered by the problem, or is continuing such a discussion.

Proceed step by step. First briefly justify your selection, then provide a string containing the selected letters.
Answer in the following JSON format ONLY and do not output anything else:

{{
    "justification": "..",
    "selection": ".."

}}

Analyze the last student's utterance.
"""
    return prompt


class Assessor:
    def __init__(self, client, assessment_history, new_messages, tools=None) -> None:
        self.assessment_history = assessment_history
        self.new_messages = new_messages

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

    def create_prompt(self, problem, problem_set):
        initial_prompt = get_inital_prompt(problem, problem_set)
        prompt = [SystemMessage(initial_prompt)]

        if len(self.assessment_history) > 0:
            prompt = prompt + self.assessment_history

        new_messages_text = ""
        for message in self.new_messages:
            new_messages_text += ' Student: "' + message.content + '"'
        prompt.append(HumanMessage(content=new_messages_text))
        return prompt

    def assess(self, problem, problem_set):
        prompt = self.create_prompt(problem, problem_set)
        final_state = self.app.invoke({"messages": prompt})

        return final_state["messages"]
