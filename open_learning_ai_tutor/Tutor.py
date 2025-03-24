from typing import Literal

import open_learning_ai_tutor.Intermediary as Intermediary
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_together import ChatTogether
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


class Tutor:

    def __init__(
        self,
        client,
        pb,
        sol,
        model="gpt-4o-2024-05-13",
        intermediary=None,
        intent_history=[],
        assessment_history=[],
        is_open=True,
        version="V1",
    ) -> None:
        self.client = client
        self.model = model  # "myGPT4"#model
        self.pb, self.sol = pb, sol
        self.open = is_open
        if not intermediary is None:
            self.intermediary = intermediary
        elif version == "V2":
            self.intermediary = Intermediary.EmptyIntermediary(
                client=self.client,
                model=self.model,
                intent_history=intent_history,
                assessment_history=assessment_history,
            )
        elif version == "V3":
            self.intermediary = Intermediary.NextStepIntermediary(
                client=self.client,
                model=self.model,
                intent_history=intent_history,
                assessment_history=assessment_history,
            )
        else:
            # notably if V1
            self.intermediary = Intermediary.SimpleIntermediary(
                client=self.client,
                model=self.model,
                intent_history=intent_history,
                assessment_history=assessment_history,
            )

    def update_client(self, client):
        self.client = client
        self.intermediary.update_client(client)

    def update_model(self, model):
        self.model = model
        self.intermediary.update_model(model)

    def get_response(self, messages_student, messages_tutor, max_tokens=1500):
        prompt, intent, assessment, prompt_tokens, completion_tokens = (
            self.intermediary.get_prompt(
                self.pb, self.sol, messages_student, messages_tutor, open=self.open
            )
        )

        completion = self.client.chat.completions.create(
            model=self.model, messages=prompt, max_tokens=max_tokens
        )
        response = completion.choices[0].message.content

        prompt_tokens += completion.usage.prompt_tokens
        completion_tokens += completion.usage.completion_tokens
        total_tokens = prompt_tokens + completion_tokens

        response = (
            response.replace("\\(", "$")
            .replace("\\)", "$")
            .replace("\\[", "$$")
            .replace("\\]", "$$")
            .replace("\\", "")
        )
        return (
            response,
            total_tokens,
            prompt_tokens,
            completion_tokens,
            intent,
            assessment,
        )


class GraphTutor2(Tutor):

    def __init__(
        self,
        client,
        problem,
        problem_set,
        model="gpt-4o-mini",
        intermediary=None,
        intent_history=[],
        assessment_history=[],
        tools=None,
        options=dict(),
    ) -> None:
        self.problem, self.problem_set = problem, problem_set
        if "open" in options:
            self.open = options["open"]
        else:
            self.open = True
        if "version" in options:
            self.version = options["version"]
        else:
            self.version = "V1"
        self.model = model
        self.final_response = None
        self.tools_used = []

        # tools
        if tools is None or tools == []:
            self.tools = []
        else:
            self.tools = tools

        # model
        if client is None:
            if "gpt" in model:
                client = ChatOpenAI(
                    model=model, temperature=0.0, top_p=0.1, max_tokens=300
                )  # response_format = { "type": "json_object" }
            elif "claude" in model:
                client = ChatAnthropic(
                    model=model, temperature=0.0, top_p=0.1, max_tokens=300
                )
            elif "llama" in model or "Llama" in model:
                client = ChatTogether(
                    model=model, temperature=0.0, top_p=0.1, max_tokens=300
                )
            else:
                raise ValueError("Model not supported")

        tool_node = None
        if self.tools != None and self.tools != []:
            client = client.bind_tools(self.tools, parallel_tool_calls=False)
            tool_node = ToolNode(self.tools)
        self.client = client

        # version and init
        self.intermediary = None
        if not intermediary is None:
            self.intermediary = intermediary
        else:
            raise ValueError("intermediary is None")

        # graph
        def should_continue(state: MessagesState) -> Literal["tools", "agent", END]:
            messages = state["messages"]
            last_message = messages[-1]
            # If the LLM makes a tool call, then we route to the "tools" node
            if last_message.tool_calls:
                self.tools_used.append(
                    [
                        last_message.tool_calls[-1]["name"],
                        last_message.tool_calls[-1]["args"],
                    ]
                )
                return "tools"
            # Otherwise, we stop (reply to the user)
            self.final_response = messages[-1].content
            return END

        # graph
        def should_stop(state: MessagesState) -> Literal["agent", END]:
            messages = state["messages"]
            penultimate_message = messages[-2]
            # If the LLM makes a tool call, then we route to the "tools" node
            if penultimate_message.tool_calls:
                if penultimate_message.tool_calls[-1]["name"] == "text_student":
                    self.final_response = penultimate_message.tool_calls[-1]["args"][
                        "message_to_student"
                    ]
                    return END
            return "agent"

        # Define the function that calls the model
        def call_model(state: MessagesState):
            messages = state["messages"]
            response = self.client.invoke(messages)
            # We return a list, because this will get added to the existing list
            return {"messages": [response]}

        # Define a new graph
        workflow = StateGraph(MessagesState)

        # Define the two nodes we will cycle between
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)

        # Set the entrypoint as `agent`
        # This means that this node is the first one called
        workflow.add_edge(START, "agent")

        # We now add a conditional edge
        workflow.add_conditional_edges(
            # First, we define the start node. We use `agent`.
            # This means these are the edges taken after the `agent` node is called.
            "agent",
            # Next, we pass in the function that will determine which node is called next.
            should_continue,
        )

        # We now add a normal edge from `tools` to `agent`.
        # This means that after `tools` is called, `agent` node is called next.
        workflow.add_conditional_edges(
            # First, we define the start node. We use `agent`.
            # This means these are the edges taken after the `agent` node is called.
            "tools",
            # Next, we pass in the function that will determine which node is called next.
            should_stop,
        )

        # Initialize memory to persist state between graph runs
        checkpointer = MemorySaver()

        app = workflow.compile(checkpointer=checkpointer)
        self.app = app

    def get_response2(self):

        prompt, intent, assessment, metadata = self.intermediary.get_prompt2(
            self.problem, self.problem_set
        )

        final_state = self.app.invoke(
            {"messages": prompt}, config={"configurable": {"thread_id": 42}}
        )

        return final_state, intent, assessment, metadata

    def get_response2_given_prompt(self, prompt):
        final_state = self.app.invoke(
            {"messages": prompt}, config={"configurable": {"thread_id": 42}}
        )

        return final_state
