# By Romain Puech, Jan 2025
import os
import json
import open_learning_ai_tutor.Tutor  as Tutor
import open_learning_ai_tutor.Assessor as Assessor
import open_learning_ai_tutor.IntentSelector as IntentSelector
import open_learning_ai_tutor.PromptGenerator as PromptGenerator
import open_learning_ai_tutor.Intermediary as Intermediary
from open_learning_ai_tutor.utils import json_to_messages, json_to_intent_list, messages_to_json, intent_list_to_json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
import concurrent.futures

## functions called internally by StratL to interract with exernal app
def StratL_json_input_to_python(problem: str, solution: str, client, new_messages: str, chat_history: str, assessment_history: str, intent_history: str, tools: list = []):
    chat_history = json_to_messages(chat_history)
    assessment_history = json_to_messages(assessment_history)
    intent_history = json_to_intent_list(intent_history)
    new_messages = json_to_messages(new_messages)
    return problem, solution, client, new_messages, chat_history, assessment_history, intent_history,  tools

def StratL_python_output_to_json(new_chat_history,new_intent_history,new_assessment_history,metadata):
    json_output = {"chat_history": messages_to_json(new_chat_history), "intent_history": intent_list_to_json(new_intent_history), "assessment_history": messages_to_json(new_assessment_history), "metadata": metadata}
    json_output = json.dumps(json_output)
    return json_output

def filter_out_system_messages(messages):
    return [msg for msg in messages if not isinstance(msg, SystemMessage)]

## functions called externally by app to interract with StratL
def process_StratL_json_output(json_output):
    json_output = json.loads(json_output)
    chat_history = json_to_messages(json_output["chat_history"])
    intent_history = json_to_intent_list(json_output["intent_history"])
    assessment_history = json_to_messages(json_output["assessment_history"])
    metadata = json_output["metadata"]
    return chat_history, intent_history, assessment_history, metadata

def convert_StratL_input_to_json(problem: str, solution: str, client, new_messages: list, chat_history: list, assessment_history: list, intent_history: list):
    json_new_messages = messages_to_json(new_messages)
    json_chat_history = messages_to_json(chat_history)
    json_assessment_history = messages_to_json(assessment_history)
    json_intent_history = intent_list_to_json(intent_history)
    return problem, solution, client, json_new_messages, json_chat_history, json_assessment_history, json_intent_history

def serialize_A_B_test_response(dico):
    if dico is None:
        return None
    json_output = {}
    for key, value in dico.items():
        if key == "new_messages":
            json_output["new_messages"] = messages_to_json(value)
        elif key == "intents":
            json_output["intents"] = intent_list_to_json([value])
        elif key == "new_assessments":
            json_output["new_assessments"] = messages_to_json(value)
        else:
            json_output[key] = value
    return json_output

def serialize_A_B_test_responses(list_of_dicts):
    if list_of_dicts is None:
        return None
    return [serialize_A_B_test_response(list_of_dicts[i]) for i in range(len(list_of_dicts))] # usually 2 if A/B test

## Actual StratL interface
def message_tutor(problem: str, solution: str, client, new_messages: str, chat_history: str, assessment_history: str, intent_history: str, options: dict, tools: list = []):
    """
    Obtain the next response from the tutor given a message and the current state of the conversation.

    Args:
        problem (str): The problem text
        solution (str): The solution text
        client: A langchain client
        new_messages (json): json of new messages
        chat_history (json): json of chat history
        assessment_history (json): json of assessment history
        intent_history (json): json of intent history
        options (dict): options for the tutor. The following options are supported:
            "assessor_client": the client for the assessor. 
            "A_B_test":  to run the tutor in A/B test mode
        tools (list of tools): list of tools for the tutor

    """
    A_B_test = options.get("A_B_test", False)
    if not A_B_test:
        new_history, new_intent_history, new_assessment_history, metadata =  _single_message_tutor(problem, solution, client, new_messages, chat_history, assessment_history, intent_history, options, tools)
        metadata["A_B_test"] = False
        metadata["tutor_model"] = client.model_name
        return StratL_python_output_to_json(new_history, new_intent_history, new_assessment_history, metadata)
    # else:
    #     # only A/B test for STATE intent
    #     new_messages,chat_history,new_intent_history,new_assessment_history,options,metadata = _single_intent_selection(problem, solution, client, new_messages, chat_history, assessment_history, intent_history, options, tools)
    #     print("\n\n----------------IN MSGT----------------\n\n")
    #     print(new_intent_history)
    #     print(type(new_intent_history))
    #     print("\n\n--------------------------------\n\n")
    #     if Intent.S_STATE in new_intent_history[-1]:
    #         # we A/B test
    #         with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    #             future1 = executor.submit(_single_message_tutor_given_intent, problem, solution, client, new_messages, 
    #                                 chat_history, new_assessment_history, new_intent_history, options, metadata,tools)
    #             future2 = executor.submit(_single_message_tutor_given_intent, problem, solution, client, new_messages, 
    #                                 chat_history, new_assessment_history, new_intent_history, options, metadata,tools)
    #             new_history_1, new_intent_history_1, new_assessment_history_1, metadata_1 = future1.result()
    #             new_history_2, new_intent_history_2, new_assessment_history_2, metadata_2 = future2.result()

    #             metadata_1["A_B_test"] = True
    #             metadata_1["tutor_model"] = client.model_name
    #             metadata_2["A_B_test"] = False
    #             metadata_2["tutor_model"] = client.model_name

    #             json_output_2 = StratL_python_output_to_json(new_history_2, new_intent_history_2, new_assessment_history_2, metadata_2)
    #             metadata_1['A_B_test_content'] = json_output_2
    #             json_output_1 = StratL_python_output_to_json(new_history_1, new_intent_history_1, new_assessment_history_1, metadata_1)
    #             print("\n\n----------------JSON OUTPUT 1----------------\n\n")
    #             print(json_output_1)
    #             print("\n\n----------------JSON OUTPUT 1----------------\n\n")
    #             return json_output_1
    #     else:
    #         print("\n\n--------------------------------\n\n")
    #         print(new_intent_history)
    #         print(type(new_intent_history))
    #         print("\n\n--------------------------------\n\n")
    #         new_history, new_intent_history, new_assessment_history, metadata =  _single_message_tutor_given_intent(problem, solution, client, new_messages, chat_history, new_assessment_history, new_intent_history, options, metadata, tools)
    #         metadata["A_B_test"] = False
    #         metadata["tutor_model"] = client.model_name
    #         return StratL_python_output_to_json(new_history, new_intent_history, new_assessment_history, metadata)
    else: # For A/B testing, run two instances in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(_single_message_tutor, problem, solution, client, new_messages, 
                                    chat_history, assessment_history, intent_history, options, tools)
            future2 = executor.submit(_single_message_tutor, problem, solution, client, new_messages, 
                                    chat_history, assessment_history, intent_history, options, tools)
            
            new_history_1, new_intent_history_1, new_assessment_history_1, metadata_1 = future1.result()
            new_history_2, new_intent_history_2, new_assessment_history_2, metadata_2 = future2.result()
            
            metadata_1["A_B_test"] = True
            metadata_1["tutor_model"] = client.model_name
            metadata_2["A_B_test"] = False
            metadata_2["tutor_model"] = client.model_name
            
            json_output_2 = StratL_python_output_to_json(new_history_2, new_intent_history_2, new_assessment_history_2, metadata_2)
            metadata_1['A_B_test_content'] = json_output_2

            json_output_1 = StratL_python_output_to_json(new_history_1, new_intent_history_1, new_assessment_history_1, metadata_1)
            # Combine both results into a list
            return json_output_1

def _single_message_tutor(problem: str, solution: str, client, new_messages: str, chat_history: str, assessment_history: str, intent_history: str, options: dict, tools: list = []):
    """Internal function that contains the original message_tutor logic"""
    problem, solution, client, new_messages, chat_history, assessment_history, intent_history, tools = StratL_json_input_to_python(problem, solution, client, new_messages, chat_history, assessment_history, intent_history, tools)
    model = client.model_name
    assessor_client = options.get("assessor_client", None)
    assessor = Assessor.GraphAssessor2(model, client=assessor_client, assessment_history=assessment_history, new_messages=new_messages, options = options)
    intentSelector = IntentSelector.SimpleIntentSelector2(intent_history)
    promptGenerator = PromptGenerator.SimplePromptGenerator2(chat_history = chat_history, options = options)
    intermediary = Intermediary.GraphIntermediary2(model, assessor = assessor, intentSelector = intentSelector, promptGenerator = promptGenerator)
    tutor = Tutor.GraphTutor2(client, pb = problem, sol = solution, model = model, intermediary = intermediary, options = options, tools = tools)
    
    new_history, new_intent, new_assessment_history, metadata = tutor.get_response2()
    new_assessment_history = new_assessment_history[1:] # [1:] because we don't include system prompt
    new_intent_history = intent_history + [new_intent]
    return filter_out_system_messages(new_history['messages']), new_intent_history, new_assessment_history, metadata

def _single_intent_selection(problem: str, solution: str, client, new_messages: str, chat_history: str, assessment_history: str, intent_history: str, options: str, tools: list = []):
    """Internal function to perform intent selection"""
    problem, solution, client, new_messages, chat_history, assessment_history, intent_history, options, tools = StratL_json_input_to_python(problem, solution, client, new_messages, chat_history, assessment_history, intent_history, options, tools)
    model = client.model_name

    assessor = Assessor.GraphAssessor2(model, assessment_history=assessment_history, new_messages=new_messages, options = options)
    intentSelector = IntentSelector.SimpleIntentSelector2(intent_history)

    assessment_history,metadata = assessor.assess2(problem ,solution)
    assessment = assessment_history[-1].content
    docs = None
    rag_questions = None
    if "docs" in metadata:
        options["docs"] = metadata["docs"]
    if "rag_queries" in metadata:
        options["rag_questions"] = metadata["rag_queries"]

    intent = intentSelector.get_intent(assessment)
    new_intent_history = intent_history + [intent]
    print("\n\n---------------1-----------------\n\n")
    print(new_intent_history)
    print(type(new_intent_history))
    print("\n\n---------------2-----------------\n\n")
    
    return new_messages,chat_history,new_intent_history,assessment_history[1:],options,metadata

def _single_message_tutor_given_intent(problem: str, solution: str, client, new_messages: list, chat_history: list, assessment_history: list, intent_history: list, options: dict, metadata: dict, tools: list = []):
    """Internal function that contains the original message_tutor logic"""
    model = client.model_name
    promptGenerator = PromptGenerator.SimplePromptGenerator2(options = options, chat_history = chat_history)
    print("\n\n--------------------------------\n\n")
    print(intent_history)
    print(type(intent_history))
    print("\n\n--------------------------------\n\n")
    chat_history = promptGenerator.get_prompt2(problem,solution,intent_history[-1],options)
    print("\n\n----------------CHAT HISTORY----------------\n\n")
    for msg in chat_history:
        print(msg)
        print(type(msg))
        print("\n\n")
    print("\n\n----------------CHAT HISTORY----------------\n\n")

    tutor = Tutor.GraphTutor2(client, pb = "", sol = "", model = model, intermediary = "", options = options, tools = tools)
    final_state = tutor.get_response2_given_prompt(chat_history)

    return filter_out_system_messages(final_state['messages']),intent_history,assessment_history,metadata


######################### test: #########################################
# # tool creation
# @tool
# def text_student(message_to_student: str):
#     """A tool to send a message to your student. This tool is the only way for you to communicate with your student. The input should be your message. After the message is sent, you will wait for the student's next message."""
#     return message_to_student

# chat_history = [AIMessage(content="Hello, how are you?"),HumanMessage(content="I am fine, thank you. What s your name?")]
# new_messages = [AIMessage(content="Hello, how are you?"),HumanMessage(content="I am fine, thank you. What s your name?")]
# assessment_history = []
# intent_history = []
# pb = "What is the sum of the first 100 natural numbers?"
# sol = "The sum of the first 100 natural numbers is 5050."
# client = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, top_p=0.1, max_tokens=300)

# json_chat_history = messages_to_json(chat_history)
# json_assessment_history = messages_to_json(assessment_history)
# json_intent_history = intent_list_to_json(intent_history)
# print(json_chat_history)
# print(json_assessment_history)
# print(json_intent_history)


# res = message_tutor(pb, sol, client, new_messages, json_chat_history, json_assessment_history, json_intent_history, json.dumps({"version": "V1"}), tools = [text_student])

# print("--------------------------------\n\n\n round 2 \n\n\n------------------------------")

# chat_history = json_to_messages(res[0])
# intent_history = json_to_intent_list(res[1])
# assessment_history = json_to_messages(res[2])

# new_student_msgs = [HumanMessage(content="Sowry")]
# new_chat_history = chat_history + new_student_msgs
# new_messages = [chat_history[-2],chat_history[-1]] + new_student_msgs

# json_chat_history = messages_to_json(new_chat_history)
# json_assessment_history = messages_to_json(assessment_history)
# json_intent_history = intent_list_to_json(intent_history)

# res2 = message_tutor(pb, sol, client, new_messages, json_chat_history, json_assessment_history, json_intent_history, json.dumps({"version": "V1"}), tools = [text_student])


