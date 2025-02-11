#### STUFF RELATED TO FUNCTIONAL APPROACH. TO MOVE TO ADEQUATE FILE ####
def pretty_print_list(list):
    for item in list:
        print(repr(item),"\n--")

def parse_final_state(state):
    return state["messages"][-1].content

def find_differences(list1, list2):
    # Find the index where lists start differing
    min_length = min(len(list1), len(list2))
    diff_index = min_length
    
    while diff_index > 0 and list1[diff_index - 1] != list2[diff_index - 1]:
        diff_index -= 1
    
    # Extract the differing parts
    part1 = list1[diff_index:]
    part2 = list2[diff_index:]
    common_prefix = list1[:diff_index]
    
    return common_prefix, part1, part2


def display_messages(messages, allow_feedback=True):
    turn = 0
    for i, msg in enumerate(messages):
        if isinstance(msg, ToolMessage):
            if msg.name == 'text_student':
                with st.chat_message(name="ai",avatar=url_prof_image):
                    # Message content
                    response = st.markdown(messages[i-1].tool_calls[0]['args']['message_to_student'])
                    if allow_feedback and turn != 0:
                        col1, col2, col3 = st.columns([0.9, 0.05, 0.05])  # Adjust column ratios
                        with col2:
                            if st.button("👍", key=f"thumbs_up_{i}", disabled= not st.session_state['tutor_answered']):
                                st.session_state['feedback'][i] = 1
                        with col3:
                            if st.button("👎", key=f"thumbs_down_{i}", disabled= not st.session_state['tutor_answered']):
                                st.session_state['feedback'][i] = -1
                    turn += 1
            elif msg.name == 'display_figure' and "Error" not in msg.content:
                exec(correct_figure_query(messages[i-1].tool_calls[0]['args']['query']))
            else:
                pass # no need to display other tool calls
        elif isinstance(msg, HumanMessage):
            with st.chat_message(name="human",avatar=url_student_image):
                response = st.write(msg.content)
    return turn

def correct_figure_query(query):
    query = query.replace('plt.show()', 'st.pyplot(plt.gcf())')
    query = re.sub(r'(\w+)\.show\(\)', r'st.pyplot(\1)', query)
    query = query.strip("`")
    # query += ''
    return query

#########################################################################



# By Romain Puech

###### for streamlit cloud, uncomment below:
#__import__('pysqlite3')
#import sys
#sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
#import sqlite3
# USER STUDY APP
#import sqlite3
#######

import asyncio
import itertools
import json
import os
import random
import time
import re

import streamlit as st
import tiktoken
from e2b_code_interpreter import Sandbox
#from get_key import get_client_openAI
from github import Auth, Github
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_together import ChatTogether
from matplotlib import pyplot as plt
from open_learning_ai_tutor.problems import get_pb_sol
from open_learning_ai_tutor.taxonomy import Intent
from open_learning_ai_tutor.tools import tutor_tools
from open_learning_ai_tutor.StratL import convert_StratL_input_to_json, process_StratL_json_output, message_tutor, serialize_A_B_test_responses
from open_learning_ai_tutor.utils import json_to_messages, json_to_intent_list, messages_to_json, intent_list_to_json

import numpy as np

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage


os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"] if "ANTHROPIC_API_KEY" in st.secrets else ""
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else ""
os.environ["E2B_API_KEY"]=  st.secrets["E2B_API_KEY"] if "E2B_API_KEY" in st.secrets else ""
os.environ["TOGETHER_API_KEY"] = st.secrets["TOGETHER_API_KEY"] if "TOGETHER_API_KEY" in st.secrets else ""

if "GITHUB_TOKEN" in st.secrets:
    auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
    g = Github(auth=auth)
    repo = g.get_user().get_repo('Universal_AI') # repo name

##### Github #####
def commit(g,repo,content):
    file_path = f"logs2/{st.session_state['session_ID']}.txt"
    branch_name = "main"
    commit_message = f"log {st.session_state['session_ID']} commit"
    # Read the content of the file to be committed

    # Check if the file already exists in the repository
    try:
        # Get the file if it exists
        file = repo.get_contents(file_path, ref=branch_name)
        # Update the file if it exists
        repo.update_file(file.path, commit_message, content, file.sha, branch=branch_name)
        #print(f"File '{file_path}' updated successfully.")
    except:
        # Create a new file if it does not exist
        repo.create_file(file_path, commit_message, content, branch=branch_name)
        print(f"File '{file_path}' created successfully.")

def generate_and_commit(g,repo):
    data_to_store = {
                "ID": st.session_state['session_ID'],
                "Username": st.session_state['username'],
                "Version": st.session_state["AI_version"],
                "Topic": st.session_state['topic'],
                "Messages": [{"turn":i,
                               "tutor":msg_t,
                               "student":msg_s,
                               "model":st.session_state['model_name'][i] if len(st.session_state['model_name'])>i else "",
                               "assessment":st.session_state['assessment'][i] if len(st.session_state['assessment'])>i else "",
                               "intent":[intent.name for intent in st.session_state['intent'][i]] if len(st.session_state['intent'])>i else "",
                               "time_between_questions":st.session_state['time_between_questions'][i] if len(st.session_state['inter_question_time'])>i else "",
                               "execution_time":st.session_state['execution_time'][i] if len(st.session_state['execution_time'])>i else "",
                               } 
                            for (i,(msg_s,msg_t)) in enumerate(itertools.zip_longest(st.session_state['student'],st.session_state['tutor']))]
            }
    content = json.dumps(data_to_store, indent=4)
    commit(g,repo,content)
##################

url_prof_image = "https://blog.ipleaders.in/wp-content/uploads/2020/08/MIT-logo.png" # "data:image/jpeg;base64,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"
url_student_image = "https://api.dicebear.com/5.x/fun-emoji/svg?seed=88"

####################################
############# Settings #############

# randomization
models_available = ["gpt-4o-mini"]#, "gpt-4o-mini"]#, "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"]
model_code_to_name = {"gpt-4o-mini": "GPT-4o-mini","gpt-4o":"GPT_4o", "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": "Llama-3.1_405B", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": "Llama-3.1_70B"}
model = None
if "model" not in st.session_state:
    model = random.choice(models_available)
    st.session_state["model"] = model
    print("Model: ",model)

else:
    model = st.session_state["model"]

model_name = model_code_to_name[model]

client = None
if "client" not in st.session_state:
    if "gpt" in model:
        client = ChatOpenAI(model=model, temperature=0.0, top_p=0.1, max_tokens=2000) #response_format = { "type": "json_object" }
    elif "claude" in model:
        client = ChatAnthropic(model=model, temperature=0.0, top_p=0.1, max_tokens=2000)
    elif "llama" in model or "Llama" in model:
        client = ChatTogether(model=model, temperature=0.0, top_p=0.1, max_tokens=2000)
    else:
        raise ValueError("Model not supported")
    st.session_state["client"] = client
else:
    client = st.session_state["client"]


# print("\nModel: ", model)


version = random.choice(["V1"])#,"V2"]) #V1 no RAG, V2 RAG

### global vars
topic = "A1P1"
pb,sol = get_pb_sol(topic)
if 'topic' not in st.session_state:
    st.session_state['topic'] = topic
if 'pb' not in st.session_state:
    st.session_state['pb'] = pb
if 'sol' not in st.session_state:
    st.session_state['sol'] = sol
if "session_ID" not in st.session_state:
    st.session_state["session_ID"] = random.randint(0,1000000)
if "AI_version" not in st.session_state:
    st.session_state["AI_version"] = version
    print("AI Version: ",st.session_state["AI_version"])
if "model" not in st.session_state:
    st.session_state["model"] = model



### Session state vars
if 'question_time' not in st.session_state:
    st.session_state['question_time'] = [time.time()]
if 'execution_time' not in st.session_state:
    st.session_state['execution_time'] = [0]
if 'time_between_questions' not in st.session_state:
    st.session_state['time_between_questions'] = [0]
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if "tutor_answered" not in st.session_state:
    st.session_state["tutor_answered"] = True
if "options" not in st.session_state:
    st.session_state["options"] = {'A_B_test': True}

# new functional approach
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = [
        AIMessage(content='', additional_kwargs={'tool_calls': [{'id': '0', 'function': {'arguments': '{"message_to_student":"Hi! Do you need any help?"}', 'name': 'text_student'}, 'type': 'function'}], 'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 0, 'prompt_tokens': 0, 'total_tokens': 0, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini-2024-07-18', 'system_fingerprint': 'fp_72ed7ab54c', 'finish_reason': 'tool_calls', 'logprobs': None}, id='0', tool_calls=[{'name': 'text_student', 'args': {'message_to_student': "Hi! Do you need any help?"}, 'id': '0', 'type': 'tool_call'}]), 
        ToolMessage(content="Message sent", name='text_student', id='0', tool_call_id='0')
    ]
if 'intent_history' not in st.session_state:
    st.session_state['intent_history'] = []
if 'assessment_history' not in st.session_state:
    st.session_state['assessment_history'] = []
if 'metadata' not in st.session_state:
    st.session_state['metadata'] = []


if 'feedback' not in st.session_state:
    st.session_state['feedback'] = dict()
if 'A_B_test_responses' not in st.session_state:
    st.session_state['A_B_test_responses'] = dict()

if 'A_B_test_running' not in st.session_state:
    st.session_state['A_B_test_running'] = False




##############################################
########### Chat History Functions ###########

############# UI #############

def remove_streamlit_hamburger():
    # remove the hamburger in the upper right hand corner and the Made with Streamlit footer
    hide_menu_style = """
            <style>
            #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
            </style>
            """
    st.markdown(hide_menu_style, unsafe_allow_html=True)



############ Chrono UI #######
limit_time = 60*15
if st.session_state['topic'] == "pythagoras":
    limit_time = 60*10

def timer_display(seconds,limit):
    time_left = max(0,limit-seconds)
    minutes = time_left // 60
    seconds = time_left % 60
    return f"{minutes:02d}:{seconds:02d}"

def friendly_timer_display(seconds,limit):
    time_left = max(0,limit-seconds)
    minutes = time_left // 60
    seconds = time_left % 60
    if time_left < 60:
        return f"**You have {seconds} seconds left with the tutor**"
    if time_left < 180:
        return f"**You have less than 3 minutes left.**"
    return f"You have **{limit//60} minutes** to interract with the tutor. You will be warned when little time remains."	
    

async def watch(test,container):
        while st.session_state['elapsed_time'] < limit_time:
            #test.markdown(f"**Time left: {timer_display(st.session_state['elapsed_time'],limit_time)}**")
            test.markdown(friendly_timer_display(st.session_state['elapsed_time'],limit_time))
            r = await asyncio.sleep(5)
            st.session_state['elapsed_time'] += 5
        st.session_state['done'] = True
        test.markdown("**Time's up!**")
        st.components.v1.html(js)
        time.sleep(0.1)
        st.rerun()

async def end_countdown(end_btn):
        while st.session_state['post_test_elapsed_time'] < 50:
            #end_btn.markdown(f"Time left: {timer_display(st.session_state['post_test_elapsed_time'],50)}")
            st.session_state['post_test_elapsed_time'] += 1
            r = await asyncio.sleep(1)
        #end_btn.markdown("Time's up!")
        # if st.button("Finish"):
        #     st.session_state['post'] = True
        #     st.session_state['done'] = True
        #     st.rerun()

    
############ Tutoring UI #####
if True:
    #### Title
    st.set_page_config(page_title="AI Tutor", page_icon=":book:")
    ### go to top of the page
    js = '''
    <script>
        var body = window.parent.document.querySelector(".main");
        body.scrollTop = 200;
    </script>
    '''
    remove_streamlit_hamburger()
    st.components.v1.html(js)
    st.markdown("<h1 style='text-align: center;'>Universal AI Tutor</h1>", unsafe_allow_html=True)
    #st.markdown("Participant ID: " + str(st.session_state['session_ID']))
    st.markdown("""
    <style>
        .stButton > button {
            background-color: transparent;
            border: none;
            padding: 0px;
            font-size: 20px;
        }
        .stButton > button:hover {
            background-color: transparent;
            border: none;
        }
        /* Style for clicked buttons */
        .stButton > button:disabled,
        .stButton > button[disabled] {
            opacity: 0.5;
        }
        /* Container for the message content */
        .message-container {
            position: relative;
            padding-bottom: 10px;  /* Reduced padding */
        }
        /* Container for the feedback buttons */
        .feedback-buttons {
            position: absolute;
            bottom: 0;
            right: 0;
            text-align: right;  /* Ensure buttons align to the right */
        }
        /* Fix column alignment */
        .feedback-buttons .row-widget.stButton {
            text-align: right;
        }
    </style>
    """, unsafe_allow_html=True)

#################### chrono
    test = st.empty()
    

######################################

    #### Sidebar

    ## Helper functions for model selection radio button ##
    def update_current_model_name():
        reverse = {"GPT-4o": "GPT-4o mini", "GPT-4o mini": "GPT-4o"}
        model_name_to_id = {"GPT-4o": "gpt-4o-2024-05-13", "GPT-4o mini": "gpt-4o-mini"}
        st.session_state['current_model_name'] = reverse[model_name]
        print(st.session_state['current_model_name'])
        print("updated")
        st.session_state['Tutor'].update_model(model_name_to_id[st.session_state['current_model_name']])

    def get_index():
        if "current_model_name" in st.session_state and st.session_state['current_model_name'] == "GPT-4o mini":
            return 0
        else:
            print(st.session_state['current_model_name'])
            return 1
    ## Sidebar elements ##	

    st.sidebar.title("Infos")
    #model_name = st.sidebar.radio("Choose model:", ("GPT-4o","GPT-4o mini"), on_change=update_current_model_name, index=0)
    counter_placeholder = st.sidebar.empty()
    #counter_placeholder.write(f"Total cost: ${st.session_state['total_cost']:.5f}")
    exercise_name_placeholder = st.sidebar.empty()
    exercise_name_placeholder.write(f"Exercice: {st.session_state['topic']}")
    
    used_probl = st.sidebar.selectbox("Available problems:",["A1P1","A1P2","A1P3"], key='selection_prev_ex') #test
    
    change_exercise_button = st.sidebar.button("Change exercise", key="change")


        
    ### Main containers
    # url_form = f"https://docs.google.com/forms/d/e/1FAIpQLSf63VILVIsAAcrTeP9RXfWeeETsVL7Q1JgbjoQ3k5zgE7MY7g/viewform?usp=pp_url&entry.122853667={st.session_state['session_ID']}"
    url_form_2 = f"https://docs.google.com/forms/d/e/1FAIpQLSe1paxzoGygg77eHmLOoSGsOs0EEZtoQ6B-d3bchTTwyegjqw/viewform?usp=pp_url&entry.122853667={st.session_state['session_ID']}&entry.1338762542={st.session_state['username']}"
    st.write("Use this [link](%s) to provide feedback on every test session you have. You are randomly assigned to different versions of the tutor with various level of ability. Feel free to change the exercise you are testing the AI on by using the dropdown menu on the left and clicking 'change exercise'" % url_form_2)
    st.subheader("Problem")
    st.markdown(st.session_state['pb']) 
    st.subheader("Solution (for testing purposes)")
    st.text(st.session_state['sol'])
    st.subheader("Conversation")


    response_container = st.container()
    container = st.container()

    # Map model names to OpenAI model IDs
    # if model_name == "GPT-4o mini":
    #     model = "gpt-4o-mini"
    # else:
    #     model = "gpt-4o"#"myGPT4"


    ############# UX #############

    ### Change exercise


    if change_exercise_button:
        
        # if exercise!= None and used_probl == "custom":

        #     st.session_state['pb'] = exercise
        #     st.session_state['sol'] = exercise_solution
        #     st.session_state['topic'] = exercise_name
        #     clear_chat_history()
        # change to elif below if above is uncommented
        if used_probl:
            pb,sol = get_pb_sol(used_probl)
            st.session_state['pb'] = pb
            st.session_state['sol'] = sol
            st.session_state['topic'] = used_probl 
        else:
            st.sidebar.error("Please enter an exercise or choose a pre-loaded one.")
        st.rerun()

    ############# Main Loop #############
    cum_total_tokens = 0
    cum_cost = 0

    #### display messages

    # Then show the input form
    def toggle_tutor_state():
        st.session_state['tutor_answered'] = False
        with response_container:
            with st.chat_message(name="human",avatar=url_student_image):
                    st.write(st.session_state.input)
            with st.chat_message(name="ai",avatar=url_prof_image):
                    st.write("Thinking...")
    # First display the chat history
    with response_container:
        total_turns = display_messages(st.session_state['chat_history'])
        if st.session_state['A_B_test_running']:# A/B test
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Option A:**")
                display_messages(st.session_state['A_B_test_responses'][total_turns][0]['new_messages'], allow_feedback=False)
                if st.button("Select A", key=f"select_a_{total_turns}", disabled= not st.session_state["A_B_test_running"]):
                    st.session_state['tutor_answered'] = True
                    st.session_state['A_B_test_running'] = False
                    st.session_state['A_B_test_responses'][total_turns][0]['selected'] = True
                    st.session_state['chat_history'].extend(st.session_state['A_B_test_responses'][total_turns][0]['new_messages'])
                    st.session_state['intent_history'].append(st.session_state['A_B_test_responses'][total_turns][0]['intents'])
                    st.session_state['assessment_history'].extend(st.session_state['A_B_test_responses'][total_turns][0]['new_assessments'])
                    st.session_state['metadata'].append(st.session_state['A_B_test_responses'][total_turns][0]['metadata'])
                    #st.rerun()
                    
            with col2:
                st.markdown("**Option B:**")
                display_messages(st.session_state['A_B_test_responses'][total_turns][1]['new_messages'], allow_feedback=False)
                if st.button("Select B", key=f"select_b_{total_turns}", disabled= not st.session_state["A_B_test_running"]):
                    st.session_state['tutor_answered'] = True
                    st.session_state['A_B_test_running'] = False
                    st.session_state['A_B_test_responses'][total_turns][1]['selected'] = True
                    st.session_state['chat_history'].extend(st.session_state['A_B_test_responses'][total_turns][1]['new_messages'])
                    st.session_state['intent_history'].append(st.session_state['A_B_test_responses'][total_turns][1]['intents'])
                    st.session_state['assessment_history'].extend(st.session_state['A_B_test_responses'][total_turns][1]['new_assessments'])
                    st.session_state['metadata'].append(st.session_state['A_B_test_responses'][total_turns][1]['metadata'])
                    #st.rerun()
            
            # Add selection buttons in a separate row
                    


    with container:
        with st.form(key='my_form', clear_on_submit=True):
            user_input = st.text_area("You:", key='input', height=100, placeholder="Wait for the tutor to answer before typing your message!")
            submit_button = st.form_submit_button(label='Send', disabled = not st.session_state['tutor_answered'] or st.session_state['A_B_test_running'], on_click=toggle_tutor_state)

        if submit_button and user_input:

            # Process the new message
            student_utterance = user_input
            time_of_question = time.time()
            st.session_state['time_between_questions'].append(time_of_question - st.session_state['question_time'][-1])
            st.session_state['question_time'].append(time_of_question)
            
            student_utterance.replace("*","\\*").replace("_","\\_").replace('$','\\$')
            
            # Add new message to chat history
            st.session_state['new_messages'] = [HumanMessage(content=student_utterance)] if total_turns != 1 else st.session_state['chat_history'] + [HumanMessage(content=student_utterance)]
            st.session_state['chat_history'].extend([HumanMessage(content=student_utterance)])
            
            # Get tutor response
            json_output = message_tutor(*convert_StratL_input_to_json(st.session_state['pb'], st.session_state['sol'], client, st.session_state['new_messages'], st.session_state['chat_history'], st.session_state['assessment_history'], st.session_state['intent_history']), st.session_state['options'], tools = tutor_tools)
            time_taken = time.time() - time_of_question
            st.session_state['execution_time'].append(time_taken)
            new_chat_history,new_intent_history,new_assessment_history,metadata = process_StratL_json_output(json_output)
            print("new assessment history is:")
            print(new_assessment_history)

            # Add A/B test handling
            if metadata.get("A_B_test", False):
                # Get the second response
                json_output_B = metadata["A_B_test_content"]
                del metadata["A_B_test_content"]
                new_chat_history_B,new_intent_history_B,new_assessment_history_B,metadata_B = process_StratL_json_output(json_output_B)
                old_messages,_,new_messages_A = find_differences(st.session_state['chat_history'],new_chat_history) # [1:] because we don't include system prompt
                old_messages,_,new_messages_B = find_differences(st.session_state['chat_history'],new_chat_history_B)
                intents_A,intents_B = new_intent_history[-1],new_intent_history_B[-1]
                old_assessments,_,assessments_A = find_differences(st.session_state['assessment_history'],new_assessment_history)
                old_assessments,_,assessments_B = find_differences(st.session_state['assessment_history'],new_assessment_history_B)
                print("assessments A is:")
                print(assessments_A)
                print("assessments B is:")
                print(assessments_B)
                # Store both responses temporarily
                st.session_state['A_B_test_responses'][total_turns] = ({"new_messages":new_messages_A, "intents":intents_A, "new_assessments":assessments_A, "metadata":metadata, "selected":False},
                                                               {"new_messages":new_messages_B, "intents":intents_B, "new_assessments":assessments_B, "metadata":metadata_B, "selected":False})
                st.session_state['A_B_test_running'] = True
                st.session_state['tutor_answered'] = True

            else:
                # Normal flow without A/B testing
                st.session_state['chat_history'] = new_chat_history
                st.session_state['intent_history'] = new_intent_history
                st.session_state['assessment_history'] = new_assessment_history
                st.session_state['metadata'].append(metadata)
                st.session_state['tutor_answered'] = True  
            st.rerun()
      

    st.session_state['username'] = 'local'

    @st.dialog("Provide your name")
    def get_user_name():
        st.write(f"What's you name?")
        inputname = st.text_input("Enter your name (or NA) for the log")
        if st.button("Submit"):
            st.session_state['username'] = inputname
            st.rerun()
    if st.session_state['username'] == "":
        # st.session_state['username'] = 'LOCAL-Romain'
        get_user_name()


    def generate_log():
        log = {"ID":st.session_state['session_ID'],
               "username":st.session_state['username'],
               "topic":st.session_state['topic'],
               "A_B_tests":{turn:serialize_A_B_test_responses(responses) for turn,responses in st.session_state['A_B_test_responses'].items()},
               "log":[
            {
                "turn":0,
                "chat_history":messages_to_json(st.session_state['chat_history'][:2]),
                "intents":[],
                "assessment_chat_history":[],
                "metadata":dict()
            }
        ]}
        turn = 1
        human_msg_index = 2
        start_assessment_index = end_assessment_index = 0

        msg_index = 3
        while msg_index < len(st.session_state['chat_history']):
            while msg_index < len(st.session_state['chat_history']) and not isinstance(st.session_state['chat_history'][msg_index],HumanMessage):
                msg_index += 1
            while end_assessment_index < len(st.session_state['assessment_history']) and not st.session_state['assessment_history'][end_assessment_index].content.startswith("{"):
                end_assessment_index += 1
            log["log"].append({
                "turn":turn,
                "chat_history":messages_to_json(st.session_state['chat_history'][human_msg_index:msg_index]),
                "intents":intent_list_to_json([st.session_state['intent_history'][turn-1]]),
                "assessment_chat_history":messages_to_json(st.session_state['assessment_history'][start_assessment_index:end_assessment_index+1]),
                "metadata":st.session_state['metadata'][turn-1],
                "feedback":[st.session_state['feedback'].get(i,None) for i in range(human_msg_index,msg_index)],
                "A_B_test_responses":serialize_A_B_test_responses(st.session_state['A_B_test_responses'].get(turn,None)),
                "time_between_questions":st.session_state['time_between_questions'][turn] if len(st.session_state['time_between_questions'])>turn else None,
                "execution_time":st.session_state['execution_time'][turn] if len(st.session_state['execution_time'])>turn else None
            })
            turn += 1
            human_msg_index = msg_index
            msg_index += 1
            start_assessment_index = end_assessment_index
        return log
    
    
    log = generate_log()
    with open("log.json","w") as f:
        json.dump(log,f,indent=4)

