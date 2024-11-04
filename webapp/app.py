
# USER STUDY APP

from openai import AzureOpenAI
import streamlit as st
from streamlit_chat import message
from streamlit_modal import Modal
import json
import copy
import itertools
import Student
import StratL.Tutor as Tutor
import StratL.Intermediary
from utils import print_logs,generate_messages
from get_key import get_client, get_client_openAI
from problems import create_msgs,get_pb_sol
from StratL.taxonomy import Intent
import random
import time
import tiktoken

import asyncio
from datetime import datetime

import base64
from github import Github
from github import InputGitTreeElement
from github import Auth

gtb_token = "token"
#auth = Auth.Token(gtb_token)
#g = Github(auth=auth)
#repo = g.get_user().get_repo('Universal_AI') # repo name

##### Github #####
def commit(g,repo,content):
    file_path = f"logs/{st.session_state['session_ID']}.txt"
    branch_name = "main"
    commit_message = f"log {st.session_state['session_ID']} commit"
    # Read the content of the file to be committed

    # Check if the file already exists in the repository
    try:
        # Get the file if it exists
        file = repo.get_contents(file_path, ref=branch_name)
        # Update the file if it exists
        repo.update_file(file.path, commit_message, content, file.sha, branch=branch_name)
        print(f"File '{file_path}' updated successfully.")
    except:
        # Create a new file if it does not exist
        repo.create_file(file_path, commit_message, content, branch=branch_name)
        print(f"File '{file_path}' created successfully.")

def generate_and_commit(g,repo):
    data_to_store = {
                "ID": st.session_state['session_ID'],
                "Version": st.session_state["AI_version"],
                "Topic": st.session_state['topic'],
                "Messages": [{"turn":i,
                               "tutor":msg_t,
                               "student":msg_s,
                               "model":st.session_state['model_name'][i] if len(st.session_state['model_name'])>i else "",
                               "assessment":st.session_state['assessment'][i] if len(st.session_state['assessment'])>i else "",
                               "intent":[intent.name for intent in st.session_state['intent'][i]] if len(st.session_state['intent'])>i else "",
                               "elapsed_time":st.session_state['inter_question_time'][i] if len(st.session_state['inter_question_time'])>i else ""
                               } 
                            for (i,(msg_s,msg_t)) in enumerate(itertools.zip_longest(st.session_state['student'],st.session_state['tutor']))]
            }
    content = json.dumps(data_to_store, indent=4)
    commit(g,repo,content)
##################

url_prof_image = "data:image/jpeg;base64,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"
url_student_image = "https://api.dicebear.com/5.x/fun-emoji/svg?seed=88"

####################################
############# Settings #############

### global vars
randomex = random.randint(0,2)
topic = "country"
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
    st.session_state["AI_version"] = "V1"
    print("AI Version: ",st.session_state["AI_version"])


model = "gpt-4o-2024-05-13"
model_name = "GPT-4o"
client = get_client_openAI()

### Session state vars
if 'tutor' not in st.session_state:
    st.session_state['tutor'] = ["Hello! Can you walk me through your solution?"]
if 'student' not in st.session_state:
    st.session_state['student'] = []
if 'model_name' not in st.session_state:
    st.session_state['model_name'] = []
if 'cost' not in st.session_state:
    st.session_state['cost'] = []
if 'total_tokens' not in st.session_state:
    st.session_state['total_tokens'] = []
if 'total_cost' not in st.session_state:
    st.session_state['total_cost'] = 0.0
if 'tellprompt' not in st.session_state:
    st.session_state['tellprompt'] = False
if 'Student' not in st.session_state:
    st.session_state['Student'] = Student.Student(client, pb = st.session_state['pb'], model = model)
if 'Tutor' not in st.session_state:
    st.session_state['Tutor'] = Tutor.Tutor(client, pb=st.session_state['pb'], sol=st.session_state['sol'], model = model, version=st.session_state["AI_version"])
if 'intent' not in st.session_state:
    st.session_state['intent'] = []
if 'assessment' not in st.session_state:
    st.session_state['assessment'] = []
if "elapsed_time" not in st.session_state:
    st.session_state["elapsed_time"] = 0
if "post" not in st.session_state:
    st.session_state["post"] = False
if "post_test_elapsed_time" not in st.session_state:
    st.session_state["post_test_elapsed_time"] = 0
if "finished_clicks" not in st.session_state:
    st.session_state["finished_clicks"] = 0
if "tutor_answered" not in st.session_state:
    st.session_state["tutor_answered"] = True
if "inter_question_time" not in st.session_state:
    st.session_state["inter_question_time"] = []
if "stopmodal" not in st.session_state:
    st.session_state["stopmodal"] = 0


##############################################
########### Chat History Functions ###########
def clear_chat_history():
    st.session_state['tutor'] = ["Hello! Can you walk me through your solution?"]
    st.session_state['student'] = []
    st.session_state['intent'] = []
    st.session_state['assessment'] = []
    st.session_state['number_tokens'] = []
    st.session_state['model_name'] = []
    st.session_state['cost'] = []
    st.session_state['total_cost'] = 0.0
    st.session_state['total_tokens'] = []
    st.session_state['Student'] = Student.Student(client, pb = st.session_state['pb'], model = model)
    st.session_state['Tutor'] = Tutor.Tutor(client, pb=st.session_state['pb'], sol=st.session_state['sol'], model = model, version=st.session_state["AI_version"])
    counter_placeholder.write(f"Total cost of this conversation: ${st.session_state['total_cost']:.5f}")
    exercise_name_placeholder.write(f"Exercice: {st.session_state['topic']}")


############# UI #############

def remove_streamlit_hamburger():
    # remove the hamburger menu in the upper right hand corner and the Made with Streamlit footer
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
            print("PRINTED")
            return 1
    ## Sidebar elements ##	

    st.sidebar.title("Infos")
    model_name = st.sidebar.radio("Choose model:", ("GPT-4o","GPT-4o mini"), on_change=update_current_model_name, index=0)
    counter_placeholder = st.sidebar.empty()
    counter_placeholder.write(f"Total cost: ${st.session_state['total_cost']:.5f}")
    exercise_name_placeholder = st.sidebar.empty()
    exercise_name_placeholder.write(f"Exercice: {st.session_state['topic']}")
    used_probl = st.sidebar.selectbox("Available problems:",["custom","consistency","country","A1P1","A1P2","A1P3"], key='selection_prev_ex') 
    #exercise = st.sidebar.text_area("Custom latex exercise (pick custom above)")
    #exercise_solution = st.sidebar.text_area("Custom latex solution")
    #exercise_name = st.sidebar.text_input("Exercise name")
    autoplay_button = False
    print_msg_button = False
    change_exercise_button = st.sidebar.button("Change exercise", key="change")


        
    ### Main containers
    st.subheader("Problem")
    st.markdown(st.session_state['pb']) 
    st.subheader("Conversation")


    response_container = st.container()
    container = st.container()

    # Map model names to OpenAI model IDs
    if model_name == "GPT-4o mini":
        model = "gpt-4o-mini"
    else:
        model = "gpt-4o-2024-05-13"


    ############# UX #############

    ### Change exercise


    if change_exercise_button:
        if exercise!= None and used_probl == "custom":

            st.session_state['pb'] = exercise
            st.session_state['sol'] = exercise_solution
            st.session_state['topic'] = exercise_name
            clear_chat_history()
            
        elif used_probl:
            pb,sol = get_pb_sol(used_probl)
            st.session_state['pb'] = pb
            st.session_state['sol'] = sol
            st.session_state['topic'] = used_probl 
            clear_chat_history()
        else:
            st.sidebar.error("Please enter an exercise or choose a pre-loaded one.")
        st.rerun()

    ############# Main Loop #############
    cum_total_tokens = 0
    cum_cost = 0


    #### display messages
    turn = 0
    with response_container:
        for i,(msg_s,msg_t) in enumerate(itertools.zip_longest(st.session_state['student'],st.session_state['tutor'])):
            if msg_t:
                with st.chat_message(name="ai",avatar=url_prof_image):
                    st.write("")
                    response = st.markdown(msg_t)
                #message(msg_t, key=str(i),logo=url_prof_image)
            if msg_s:
                with st.chat_message(name="human",avatar=url_student_image):
                    response = st.write(msg_s)
                #message(msg_s, is_user=True, key=str(i) + '_user')
            turn = i
            #st.write(
            #    f"Model used: {st.session_state['model_name'][i]}; Number of tokens: {st.session_state['total_tokens'][i]}; Cost: ${st.session_state['cost'][i]:.5f}")
            
            #counter_placeholder.write(f"Total Cost: ${st.session_state['total_cost']:.5f}")
            #exercise_name_placeholder.write(f"Exercice: {st.session_state['topic']}")


    with container:
        with st.form(key='my_form', clear_on_submit=True):
            user_input = st.text_area("You:", key='input', height=100, placeholder="Wait for the tutor to answer before typing your message!")
            submit_button = st.form_submit_button(label='Send')

        if submit_button and user_input:
            if not st.session_state['tutor_answered']:
                st.error("Please wait for the tutor to answer before sending your next message!")

            st.session_state['tutor_answered'] = False
            # log student prompt
            student_utterance, student_total_tokens, student_prompt_tokens, student_completion_tokens = user_input,0,0,0
            time_of_question = st.session_state['elapsed_time']
            student_utterance.replace("*","\*")
            turn +=1
            with response_container:
                with st.chat_message(name="human",avatar=url_student_image):
                    response = st.write(student_utterance)
                #message(student_utterance, is_user=True, key=str(turn) + '_user')
            
            # get tutor response
            with response_container:
                with st.chat_message(name="ai",avatar=url_prof_image):
                    st.write("")
                    output, tutor_total_tokens, tutor_prompt_tokens, tutor_completion_tokens, intent, assessment = st.session_state['Tutor'].get_response_stream(st.session_state['student'] + [student_utterance], st.session_state['tutor'])
                    response = st.write_stream(output)
                    print("-----------------------------------------------")
                    encoding = tiktoken.get_encoding("cl100k_base")
                    completion_tokens = len(encoding.encode(response))
                    tutor_completion_tokens += completion_tokens
                    tutor_total_tokens += completion_tokens
                    print(tutor_total_tokens)
                    
                #message(output, is_user=False, key=str(turn),logo=url_prof_image)
                
            # log tutor response
            
            response_content = str(response)
            tutor_total_tokens = tutor_prompt_tokens + tutor_completion_tokens
            print("tutor answers:\n",response_content)
            print("tutor_total_tokens", tutor_total_tokens)
            total_tokens = student_total_tokens + tutor_total_tokens
            prompt_tokens = tutor_prompt_tokens + student_prompt_tokens
            completion_tokens = tutor_completion_tokens + student_completion_tokens

            # Replace latex delimiters in the response content
            response_content = response_content.replace("\(","$").replace("\)","$").replace("\[","$$").replace("\]","$$")


            #### Compute price
            # from https://openai.com/pricing#language-models - updated OCT 2024
            if model_name == "GPT-4o mini":
                print("inexpensive model")
                cost = (prompt_tokens * 0.15 + completion_tokens * 0.6) / 1000000
            else:
                print("expensive model")
                cost = (prompt_tokens * 2.5 + completion_tokens * 10) / 1000000

            st.session_state['cost'].append(cost)
            st.session_state['total_cost'] += cost
            st.session_state['student'].append(student_utterance)
            st.session_state['tutor'].append(response_content)
            st.session_state['intent'].append(intent)
            st.session_state['assessment'].append(assessment)
            st.session_state['model_name'].append(model_name)
            st.session_state['total_tokens'].append(total_tokens)
            st.session_state['inter_question_time'].append(time_of_question)
            st.session_state['tutor_answered'] = True
            #### commit to GitHub
            #generate_and_commit(g,repo)
            