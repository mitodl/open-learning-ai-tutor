import json
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_together import ChatTogether
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from open_learning_ai_tutor.utils import print_logs
from open_learning_ai_tutor.Retriever import Retriever
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
h) The student is explicitly asking the tutor to state a specific theorem, definition, formula or programming command that is not the **direct answer** to the question they have to solve.
i) The student is explicitly asking the tutor to perform a numerical calculation
j) The student and tutor arrived at a complete solution for the entirety of the initial *Problem Statement*
k) The student and tutor arrived at a complete solution for the entirety of the initial *Problem Statement* equivalent to the method provided in the *Provided Solution*
l) The student's message is *entirely* irrelevant to the problem at hand or to the material covered by the exercise.
m) The student is asking about concepts or information related to the material covered by the problem, or is continuing such a discussion.

Proceed step by step. First briefly justify your selection, then provide a string containing the selected letters.
Answer in the following JSON format ONLY and do not output anything else:
##
{{
    "justification": "..",
    "selection": ".."

}}
##
Analyze the last student's utterance.
{{
"""
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
        # Order in chat history is tutor messages first, then student messages

        # if no history, create prompt from scratch
        if len(self.history) == 0:
            prompt = self.create_prompt(pb,sol,tutor_messages,student_messages, from_history=False)
        else:
            # append the last tutor and student messages to the history
            prompt_extension = self.create_prompt(pb,sol,tutor_messages,student_messages, from_history=True)
            prompt = self.history + prompt_extension

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

        # return the history
        
        return assessment, self.history
    
class GraphAssessor2(Assessor):
    def __init__(self,model, client=None, assessment_history=[],new_messages=[], options = {}) -> None:
        # init
        
        self.model = model
        self.history = list(assessment_history)
        self.new_messages = new_messages
        

        if "version" in options:
            self.version = options["version"]
        else:
            self.version = "V1"
        if "tools" in options:
            self.tools = options["tools"]
        else:
            self.tools = None
        if self.tools is None:
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
        
        # model
        if not client:
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
        if self.version == "V2":
            self.rag_agent = Retriever("analytics_edge.txt")
        else:
            self.rag_agent = None
        self.rag_queries = None

        
        # Define the asessor's graph
        def should_continue(state: MessagesState) -> Literal["tools", END]:
            messages = state['messages']
            last_message = messages[-1]
            #print(last_message.content)
            # If the LLM makes a tool call, then we route to the "tools" node
            if last_message.tool_calls:
                return "tools"
            # Otherwise, we stop (reply to the user)
            return END


        # Define the function that calls the model
        def call_model(state: MessagesState):
            messages = state['messages']
            response = self.client.invoke(
                messages,
                config={"configurable": {"thread_id": 42}}
            )
            # We return a list, because this will get added to the existing list
            return {"messages": [response]}
        
        # def call_rag(state: MessagesState):
        #     if self.rag_agent is None:
        #         return{"retrieved_docs": []}
        #     messages = state['messages']
        #     transcript = ""
        #     for i in range(1,len(messages),2):
        #         transcript += f"Tutor: \"{messages[i]}\"\nStudent: \"{messages[i+1]}\"\n"

        #     response = self.rag_agent.invoke(transcript)
            
        #     return {"retrieved_docs": [response]}


        # Define a new graph
        workflow = StateGraph(MessagesState)

        # Define the two nodes we will cycle between
        # workflow.add_node("retriever", call_rag)
        workflow.add_node("agent", call_model)
        if tool_node is not None:
            workflow.add_node("tools", tool_node)

        # Set the entrypoint as `retriever`
        # This means that this node is the first one called
        #workflow.add_edge(START, "retriever")
        workflow.add_edge(START, 'agent')

        # We now add a conditional edge
        if tool_node is not None:
            workflow.add_conditional_edges(
                # First, we define the start node. We use `agent`.
                # This means these are the edges taken after the `agent` node is called.
                "agent",
                # Next, we pass in the function that will determine which node is called next.
                should_continue,
            )
        else:
            workflow.add_edge("agent", END)

        # We now add a normal edge from `tools` to `agent`.
        # This means that after `tools` is called, `agent` node is called next.
        workflow.add_edge("tools", 'agent')

        # Initialize memory to persist state between graph runs
        checkpointer = MemorySaver()

        app = workflow.compile(checkpointer=checkpointer)
        self.app = app

    def transcript_line(self,message):
        if isinstance(message,HumanMessage):
            return "Student: \""+message.content+"\""
        elif isinstance(message,AIMessage):
            if message.tool_calls and message.tool_calls[0]['name'] != "text_student":
                return "Tutor (uses a tool)"
            elif message.tool_calls and message.tool_calls[0]['name'] == "text_student":
                return "Tutor (to student): \""+message.tool_calls[0]['args']['message_to_student']+"\""
            elif message.content != "":
                return "Tutor"
            else:
                return ""
        elif isinstance(message,ToolMessage):
            if message.name != "text_student":
                return f"Tool ({message.name}) used. Result:" + message.content
        elif isinstance(message,SystemMessage):
            return "System"
        return ""
    
    def get_transcript2(self, new_messages, from_history = True):
        transcript = ""
        if from_history:
            for message in self.history:
                if isinstance(message,HumanMessage):
                    transcript += message.content+"\n"
        # add the new tutor and student messages
        for message in new_messages:
            if not (isinstance(message,ToolMessage) and message.name == "text_student"):
                a = self.transcript_line(message)
                print("THIS IS A:",a)
                transcript += a
        return transcript
        
    

    def create_prompt2(self,pb,sol):
        docs = None
        rag_queries = None
        # if RAG enabled
        if self.version == "V2":
            transcript = self.get_transcript2(self.new_messages,from_history=True)
            docs,rag_queries = self.rag_agent.invoke({"transcript":transcript, "pb":pb, "sol":sol})
            print("\n\nDOCS ARE:",docs)
            print("\n\nRAG QUESTIONS ARE:",rag_queries)
        self.docs = docs
        self.rag_queries = rag_queries

        purpose = self.get_purpose(pb,sol,docs)

        if len(self.history) > 0:
            prompt = self.history
        else:
            prompt = [SystemMessage(purpose)] 
        
        if not isinstance(prompt[0],SystemMessage):
            prompt.insert(0,SystemMessage(purpose))
        
        prompt.append(HumanMessage(content=self.get_transcript2(self.new_messages,from_history=False)))
        #print("\n\nAssessor prompt is:\n",prompt)
        return prompt
    #######
    
    def assess2(self,pb,sol):
            prompt = self.create_prompt2(pb,sol)
            print("\n\n\n^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n")
            print("prompt is:\n")
            print(prompt)

            final_state = self.app.invoke(
            {"messages": prompt},
            config={"configurable": {"thread_id": 42}}
            )
            print("final state is:")
            print(final_state)

            response = final_state['messages'][-1].content.replace("\\(","$").replace("\\)","$").replace("\\[","$$").replace("\\]","$$").replace("\\","")
            # postprocess make sure the format is right
            s = response.find('{')
            e = response.rfind('}')
            response = response[s:e+1]
            print("response is:")
            print(response)
            json_data = json.loads(response)
            selection = json_data['selection']
            selection = selection.replace(' ','').replace(',','')
            json_data['selection'] = selection
            assessment = json.dumps(json_data)

            self.history = final_state['messages']
            final_state['messages'][-1].content = assessment

        
            return self.history, {"docs":self.docs, "rag_queries":self.rag_queries}
    