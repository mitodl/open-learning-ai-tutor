import json
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_together import ChatTogether
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from utils import print_logs
from Retriever import Retriever
# not used anymore:
#Moreover select if relevant some emotional states from "l,m":
#l) The student shows a strong lack of motivation
#m) The student shows a strong lack of self-confidence

class Assessor():
    def __init__(self,client,model,assessment_history=[]) -> None:
        self.client = client
        self.model = model
        self.history = list(assessment_history)

    def get_purpose(self,pb,sol, docs=None):
        purpose = \
        f"""A student and their tutor are working on a math problem:
*Problem Statement*:
<problem>
{pb}
</problem>

The *Provided Solution* of this problem is:
<solution>
{sol}
</solution>

{"*Textbook passages* that may be relevant to your task:" if docs is not None else ""}
{"<textbook>" +  docs if docs is not None else ""}
{"</textbook>" if docs is not None else ""}

The tutor's utterances are preceded by "Tutor:" and the student's utterances are preceded by "Student:".

Analyze the last student's utterance.
select all the feedbacks that apply from "a,b,c,d,e,f,g,h,i,j,k,l":

a) The student is using or suggesting a wrong method or taking a wrong path to solve the problem
b) The student made an error in the algebraic manipulation
c) The student made a numerical error
d) The student provided an intuitive or incomplete solution
e) The student's answer is not clear or ambiguous
f) The student correctly answered the tutor's previous question
g) The student is explicitly asking about how to solve the problem
h) The student is explicitly asking the tutor to state a specific theorem, definition, formula or programming command that is not the direct answer to the question they have to solve.
i) The student is explicitly asking the tutor to perform a numerical calculation
j) The student and tutor arrived at a complete solution for the entirety of the initial *Problem Statement*
k) The student and tutor arrived at a complete solution for the entirety of the initial *Problem Statement* equivalent to the method provided in the *Provided Solution*
l) The student's message is irrelevant to the problem at hand

Proceed step by step. First briefly justify your selection, then provide a string containing the selected letters.
Answer in the following JSON format ONLY and do not output anything else:
##
{{
    "justification": "..",
    "selection": ".."

}}
##
Analyze the last student's utterance.
{{"""
        return purpose

    def create_prompt(self,pb,sol,tutor_messages,student_messages):
        
        purpose = self.get_purpose(pb,sol)
        #print("DEBUG")
        #print(tutor_messages)
        #print(student_messages)
        #print(self.history)
        prompt = [{"role": "system", "content": purpose}] + \
            [
            msg for i in range(len(self.history))
                for msg in (
                    {"role": "user", "content": f"Tutor: \"{tutor_messages[i]}\"\nStudent: \"{student_messages[i]}\"\n"},
                    {"role": "assistant", "content": self.history[i]}
                )
            ]
        prompt.append({"role": "user", "content":f"Tutor: \"{tutor_messages[-1]}\"\nStudent: \"{student_messages[-1]}\"\n" })
        return prompt

    def assess(self,pb,sol,student_messages,tutor_messages):
        prompt = self.create_prompt(pb,sol,tutor_messages,student_messages)
        print("Assessor called with prompt:")
        print(print_logs(prompt))
        client = self.client
        completion = client.chat.completions.create(
            model=self.model,
            messages=prompt,
            response_format = { "type": "json_object" },
            max_tokens=300, # should never be reached
            temperature=0.0,
            top_p=0.1
        )

        response = (completion.choices[0].message.content).replace("\\(","$").replace("\\)","$").replace("\\[","$$").replace("\\]","$$").replace("\\","")
        print("ASSESSMENT IS \n",response)
        # postprocess make sure the format is right
        s = response.find('{')
        e = response.rfind('}')
        response = response[s:e+1]
        json_data = json.loads(response)
        selection = json_data['selection']
        selection = selection.replace(' ','').replace(',','')
        json_data['selection'] = selection
        assessment = json.dumps(json_data)

        self.history.append(assessment)

        total_tokens = completion.usage.total_tokens
        prompt_tokens = completion.usage.prompt_tokens
        completion_tokens = completion.usage.completion_tokens
        
        return assessment, prompt_tokens, completion_tokens
    

# THIS IS THE ONE WE ARE USING
class GraphAssessor(Assessor):
    def __init__(self,client,model,assessment_history=[],tools=None, version="V1") -> None:
        # init
        self.version = version
        self.model = model
        self.history = list(assessment_history)

        # tools
        if tools is None:
            python_repl = PythonREPL()
            @tool
            def execute_python(query: str):
                """A Python shell. Use SymPy to solve complex equations. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`."""
                try:
                    return python_repl.run(query)
                except Exception as e:
                    return str(e)
                
            @tool
            def calculator(query: str):
                """A Python Shell. Use it to perform complex computations. Input should be a valid python command. To see the output of a value, print it out with `print(...)`."""
                try:
                    return python_repl.run(query)
                except Exception as e:
                    return str(e)

            self.tools = [execute_python,calculator]
        else:
            self.tools = tools
        
        # model

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

        
        # define the RAG agent
        if version == "V2":
            self.rag_agent = Retriever("analytics_edge.txt")
        else:
            self.rag_agent = None
        self.rag_queries = None

        
        # Define the asessor's graph
        def should_continue(state: MessagesState) -> Literal["tools", END]: # END imported from langgraph.graph
            messages = state['messages']
            last_message = messages[-1]
            print(last_message.content)
            # If the LLM makes a tool call, then we route to the "tools" node
            if last_message.tool_calls:
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

        workflow.add_node("agent", call_model)
        if tool_node is not None:
            workflow.add_node("tools", tool_node)

        # Set the entrypoint as `agent`
        # This means that this node is the first one called
        workflow.add_edge(START, 'agent')

        # We now add a conditional edge
        if tool_node is not None:
            workflow.add_conditional_edges(
                "agent",
                # the function that will determine which node is called next.
                should_continue,
            )
        else:
            workflow.add_edge("agent", END)

        # normal edge from `tools` to `agent`.
        # This means that after `tools` is called, `agent` node is called next.
        workflow.add_edge("tools", 'agent')

        # Initialize memory to persist state between graph runs
        checkpointer = MemorySaver()

        # compile agent
        app = workflow.compile(checkpointer=checkpointer)
        self.app = app


    def get_transcript(self,tutor_messages,student_messages):
        transcript = ""
        for i in range(len(tutor_messages)):
            transcript += f"Tutor: \"{tutor_messages[i]}\"\nStudent: \"{student_messages[i]}\"\n"
        return transcript
    
    def create_prompt(self,pb,sol,tutor_messages,student_messages):
        docs = None
        rag_queries = None
        if self.version == "V2":
            transcript = self.get_transcript(tutor_messages,student_messages)
            docs,rag_queries = self.rag_agent.invoke({"transcript":transcript, "pb":pb, "sol":sol})
            print("\n\nDOCS ARE:",docs)
            print("\n\nRAG QUESTIONS ARE:",rag_queries)
        self.docs = docs
        self.rag_queries = rag_queries
        purpose = self.get_purpose(pb,sol,docs)
        
        prompt = [SystemMessage(purpose)] + \
            [
            msg for i in range(len(self.history))
                for msg in (
                    HumanMessage(f"Tutor: \"{tutor_messages[i]}\"\nStudent: \"{student_messages[i]}\"\n"),
                    AIMessage(self.history[i])
                )
            ]
        prompt.append(HumanMessage(f"Tutor: \"{tutor_messages[-1]}\"\nStudent: \"{student_messages[-1]}\"\n" ))
        print("\n\nAssessor prompt is:\n",prompt)
        return prompt
    

    def assess(self,pb,sol,student_messages,tutor_messages):
        prompt = self.create_prompt(pb,sol,tutor_messages,student_messages)
        print("Assessor called with prompt:")
        print(print_logs(prompt))

        final_state = self.app.invoke(
        {"messages": prompt},
        config={"configurable": {"thread_id": 42}}
        )

        response = final_state['messages'][-1].content.replace("\\(","$").replace("\\)","$").replace("\\[","$$").replace("\\]","$$").replace("\\","")
        print("ASSESSMENT IS \n",response)
        # postprocess make sure the format is right
        s = response.find('{')
        e = response.rfind('}')
        response = response[s:e+1]
        json_data = json.loads(response)
        selection = json_data['selection']
        selection = selection.replace(' ','').replace(',','')
        json_data['selection'] = selection
        assessment = json.dumps(json_data)

        self.history.append(assessment)

        token_info = final_state['messages'][-1].response_metadata['token_usage']

        total_tokens = token_info['total_tokens']
        prompt_tokens = token_info['prompt_tokens']
        completion_tokens = token_info['completion_tokens']

        #TODO log tokens from previous messages, log tool use etc etc
        #TODO return computed equations.
        
        return assessment, [prompt_tokens, completion_tokens,self.docs, self.rag_queries]
    

