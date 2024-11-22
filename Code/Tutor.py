from typing import Literal

import Intermediary
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_together import ChatTogether
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


class Tutor():

    def __init__(self,client,pb,sol,model="gpt-4o-2024-05-13",intermediary=None,intent_history = [],assessment_history=[],is_open=True, version="V1") -> None:
        print("---")
        print("Creating tutor...")
        print("---")
        self.client = client
        self.model = model#"myGPT4"#model
        self.pb,self.sol = pb,sol
        self.open = is_open
        if not intermediary is None:
            self.intermediary = intermediary
        elif version == "V2":
            self.intermediary = Intermediary.EmptyIntermediary(client = self.client,model = self.model, intent_history = intent_history, assessment_history = assessment_history)
        elif version == "V3":
            self.intermediary = Intermediary.NextStepIntermediary(client = self.client,model = self.model, intent_history = intent_history, assessment_history = assessment_history)
        else:
            # notably if V1
            self.intermediary = Intermediary.SimpleIntermediary(client = self.client,model = self.model, intent_history = intent_history, assessment_history = assessment_history)

    def update_client(self,client):
        self.client = client
        self.intermediary.update_client(client)

    def update_model(self,model):
        self.model = model
        self.intermediary.update_model(model)
        

    def get_response(self,messages_student,messages_tutor,max_tokens=1500):
        print("\n---")
        #print("tutor called using model ", self.model)
        prompt,intent,assessment,prompt_tokens,completion_tokens = self.intermediary.get_prompt(self.pb,self.sol,messages_student,messages_tutor,open=self.open)
        #prompt.append({"role": "system", "content": "Ask the student to find by themself a problem with their answer without giving any hint"})
        print("prompt generated:")
        #print_logs(prompt)
        

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=prompt,
            max_tokens=max_tokens
        )
        response = completion.choices[0].message.content

        prompt_tokens += completion.usage.prompt_tokens
        completion_tokens += completion.usage.completion_tokens
        total_tokens = prompt_tokens + completion_tokens

        response = response.replace("\(","$").replace("\)","$").replace("\[","$$").replace("\]","$$")
        print("tutor answers:")
        print(response)
        print("---")
        return response, total_tokens, prompt_tokens, completion_tokens, intent, assessment
    
    def get_response_stream(self,messages_student,messages_tutor,max_tokens=1500):
        print("\n---")
        #print("tutor called using model ", self.model)
        prompt,intent,assessment,prompt_tokens,completion_tokens = self.intermediary.get_prompt(self.pb,self.sol,messages_student,messages_tutor,open=self.open)
        #prompt.append({"role": "system", "content": "Ask the student to find by themself a problem with their answer without giving any hint"})
        print("prompt generated:")
        #print_logs(prompt)

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=prompt,
            max_tokens=max_tokens,
            stream=True,
        )
        #response = response.replace("\(","$").replace("\)","$").replace("\[","$$").replace("\]","$$")
        #print("tutor answers:")
        #print(response)
        #print("---")
        total_tokens = prompt_tokens + completion_tokens
        return stream, total_tokens, prompt_tokens, completion_tokens, intent, assessment
    
class GraphTutor(Tutor):

    def __init__(self,client,pb,sol,model="gpt-4o-mini",intermediary=None,intent_history = [],assessment_history=[],is_open=True, version="V1", tools = None) -> None:
        self.pb,self.sol = pb,sol
        self.open = is_open
        self.model = model
        self.final_response = None
        
        # tools 
        if tools is None or tools == []:
            print("No tools provided!")
            self.tools = []
        else:
            self.tools = tools
        
        # model
        if client is None:
            if "gpt" in model:
                client = ChatOpenAI(model=model, temperature=0.0, top_p=0.1, max_tokens=300) #response_format = { "type": "json_object" }
            elif "claude" in model:
                client = ChatAnthropic(model=model, temperature=0.0, top_p=0.1, max_tokens=300)
            elif "llama" in model or "Llama" in model:
                client = ChatTogether(model=model, temperature=0.0, top_p=0.1, max_tokens=300)
            else:
                raise ValueError("Model not supported")

        tool_node = None  
        if self.tools != None and self.tools != []:
            client = client.bind_tools(self.tools)
            tool_node = ToolNode(self.tools)
        self.client = client

        # version and init
        self.intermediary = Intermediary.GraphIntermediary(client = self.client, model = model, intent_history = intent_history, assessment_history = assessment_history, version=version)

        # graph
        def should_continue(state: MessagesState) -> Literal["tools", END]:
            messages = state['messages']
            last_message = messages[-1]
            print("\n---last message:\n")
            print(last_message)
            # If the LLM makes a tool call, then we route to the "tools" node
            if last_message.tool_calls:
                if last_message.tool_calls[-1]['name'] == "send_message_to_student":
                    self.final_response = last_message.tool_calls[-1]['args']['query']
                    return END
                print("tool call detected")
                print(last_message.tool_calls)
                return "tools"
            # Otherwise, we stop (reply to the user)
            return END


        # Define the function that calls the model
        def call_model(state: MessagesState):
            messages = state['messages']
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
        workflow.add_edge("tools", 'agent')

        # Initialize memory to persist state between graph runs
        checkpointer = MemorySaver()

        # Finally, we compile it!
        # This compiles it into a LangChain Runnable,
        # meaning you can use it as you would any other runnable.
        # Note that we're (optionally) passing the memory when compiling the graph
        app = workflow.compile(checkpointer=checkpointer)
        self.app = app

        

    def get_response(self,messages_student,messages_tutor,max_tokens=1500):
        
        print("\n---")
        #print("tutor called using model ", self.model)
        prompt,intent,assessment,prompt_tokens,completion_tokens,docs = self.intermediary.get_prompt(self.pb,self.sol,messages_student,messages_tutor,open=self.open)
        #prompt.append({"role": "system", "content": "Ask the student to find by themself a problem with their answer without giving any hint"})
        print("\n\nTUTOR prompt generated:")
        print(prompt)
        
        
        # completion = self.client.chat.completions.create(
        #     model=self.model,
        #     messages=prompt,
        #     max_tokens=max_tokens
        # )
        final_state = self.app.invoke(
            {"messages": prompt},
            config={"configurable": {"thread_id": 42}}
        )
        response = self.final_response
        self.final_response = None
        #print("final_state:\n\n",final_state['messages'])
        if response == None:
            response = ''
            for message in final_state['messages']:
                if type(message) != type(AIMessage('')):
                    response = ''
                elif message.content != '':
                    response += message.content.replace("\\(","$").replace("\\)","$").replace("\\[","$$").replace("\\]","$$").replace("\\","") + "\n"
           #response = final_state['messages'][-1].content
        else:
            response = response.replace("\\(","$").replace("\\)","$").replace("\\[","$$").replace("\\]","$$").replace("\\","") + "\n"
        #TODO update token info
        token_info = final_state['messages'][-1].response_metadata['token_usage']
        print("token_info:")
        print(token_info)
        print("---")
        prompt_tokens += token_info['prompt_tokens']
        completion_tokens += token_info['completion_tokens']
        total_tokens = prompt_tokens + completion_tokens

        response = response.replace("\(","$").replace("\)","$").replace("\[","$$").replace("\]","$$")
        print("tutor answers:")
        print(response)
        print("---")
        return response, total_tokens, prompt_tokens, completion_tokens, intent, assessment
    
    def get_response_stream(self,messages_student,messages_tutor,max_tokens=1500):
        #TODO get_responses (plural)
        raise NotImplementedError("Stream not implemented for graph tutor")
        print("\n---")
        #print("tutor called using model ", self.model)
        prompt,intent,assessment,prompt_tokens,completion_tokens = self.intermediary.get_prompt(self.pb,self.sol,messages_student,messages_tutor,open=self.open)
        #prompt.append({"role": "system", "content": "Ask the student to find by themself a problem with their answer without giving any hint"})
        print("prompt generated:")
        #print_logs(prompt)
        
        
        # completion = self.client.chat.completions.create(
        #     model=self.model,
        #     messages=prompt,
        #     max_tokens=max_tokens
        # )
        final_state = self.app.invoke(
            {"messages": prompt},
            config={"configurable": {"thread_id": 42}}
        )
        response = ''
        #print("final_state:\n\n",final_state['messages'])
        for message in final_state['messages']:
            if type(message) != type(AIMessage('')):
                response = ''
            elif message.content != '':
                response += message.content.replace("\\(","$").replace("\\)","$").replace("\\[","$$").replace("\\]","$$").replace("\\","") + "\n"
        #response = final_state['messages'][-1].content
        
        token_info = final_state['messages'][-1].response_metadata['token_usage']
        print("token_info:")
        print(token_info)
        print("---")
        prompt_tokens += token_info['prompt_tokens']
        completion_tokens += token_info['completion_tokens']
        total_tokens = prompt_tokens + completion_tokens

        response = response.replace("\(","$").replace("\)","$").replace("\[","$$").replace("\]","$$")
        print("tutor answers:")
        print(response)
        print("---")
        return response, total_tokens, prompt_tokens, completion_tokens, intent, assessment
    
