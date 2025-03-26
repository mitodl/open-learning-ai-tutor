import json
import open_learning_ai_tutor.Tutor as Tutor
import open_learning_ai_tutor.assessor as Assessor
import open_learning_ai_tutor.PromptGenerator as PromptGenerator
import open_learning_ai_tutor.Intermediary as Intermediary
from open_learning_ai_tutor.utils import (
    json_to_messages,
    json_to_intent_list,
    messages_to_json,
    intent_list_to_json,
)
from langchain_core.messages import SystemMessage
import concurrent.futures


## functions called internally by StratL to interract with exernal app
def StratL_json_input_to_python(
    client,
    new_messages: str,
    chat_history: str,
    assessment_history: str,
    intent_history: str,
    tools: list = [],
):
    chat_history = json_to_messages(chat_history)
    assessment_history = json_to_messages(assessment_history)
    intent_history = json_to_intent_list(intent_history)
    new_messages = json_to_messages(new_messages)
    return (
        client,
        new_messages,
        chat_history,
        assessment_history,
        intent_history,
        tools,
    )


def StratL_python_output_to_json(
    new_chat_history, new_intent_history, new_assessment_history, metadata
):
    json_output = {
        "chat_history": messages_to_json(new_chat_history),
        "intent_history": intent_list_to_json(new_intent_history),
        "assessment_history": messages_to_json(new_assessment_history),
        "metadata": metadata,
    }
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


def convert_StratL_input_to_json(
    problem: str,
    solution: str,
    client,
    new_messages: list,
    chat_history: list,
    assessment_history: list,
    intent_history: list,
):
    json_new_messages = messages_to_json(new_messages)
    json_chat_history = messages_to_json(chat_history)
    json_assessment_history = messages_to_json(assessment_history)
    json_intent_history = intent_list_to_json(intent_history)
    return (
        problem,
        solution,
        client,
        json_new_messages,
        json_chat_history,
        json_assessment_history,
        json_intent_history,
    )


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
    return [
        serialize_A_B_test_response(list_of_dicts[i]) for i in range(len(list_of_dicts))
    ]  # usually 2 if A/B test


## Actual StratL interface
def message_tutor(
    problem: str,
    problem_set: str,
    client,
    new_messages: str,
    chat_history: str,
    assessment_history: str,
    intent_history: str,
    options: dict,
    tools: list = [],
):
    """
    Obtain the next response from the tutor given a message and the current state of the conversation.

    Args:
        problem (str): The problem xml
        problem_set (str): The problem set xml
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
        new_history, new_intent_history, new_assessment_history, metadata = (
            _single_message_tutor(
                problem,
                problem_set,
                client,
                new_messages,
                chat_history,
                assessment_history,
                intent_history,
                options,
                tools,
            )
        )
        metadata["A_B_test"] = False
        metadata["tutor_model"] = client.model_name
        return StratL_python_output_to_json(
            new_history, new_intent_history, new_assessment_history, metadata
        )
    else:  # For A/B testing, run two instances in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(
                _single_message_tutor,
                problem,
                problem_set,
                client,
                new_messages,
                chat_history,
                assessment_history,
                intent_history,
                options,
                tools,
            )
            future2 = executor.submit(
                _single_message_tutor,
                problem,
                problem_set,
                client,
                new_messages,
                chat_history,
                assessment_history,
                intent_history,
                options,
                tools,
            )

            (
                new_history_1,
                new_intent_history_1,
                new_assessment_history_1,
                metadata_1,
            ) = future1.result()
            (
                new_history_2,
                new_intent_history_2,
                new_assessment_history_2,
                metadata_2,
            ) = future2.result()

            metadata_1["A_B_test"] = True
            metadata_1["tutor_model"] = client.model_name
            metadata_2["A_B_test"] = False
            metadata_2["tutor_model"] = client.model_name

            json_output_2 = StratL_python_output_to_json(
                new_history_2,
                new_intent_history_2,
                new_assessment_history_2,
                metadata_2,
            )
            metadata_1["A_B_test_content"] = json_output_2

            json_output_1 = StratL_python_output_to_json(
                new_history_1,
                new_intent_history_1,
                new_assessment_history_1,
                metadata_1,
            )
            # Combine both results into a list
            return json_output_1


def _single_message_tutor(
    problem: str,
    problem_set: str,
    client,
    new_messages: str,
    chat_history: str,
    assessment_history: str,
    intent_history: str,
    options: dict,
    tools: list = [],
):
    """Internal function that contains the original message_tutor logic"""
    (
        client,
        new_messages,
        chat_history,
        assessment_history,
        intent_history,
        tools,
    ) = StratL_json_input_to_python(
        client,
        new_messages,
        chat_history,
        assessment_history,
        intent_history,
        tools,
    )
    model = client.model_name
    assessor_client = options.get("assessor_client", None)
    assessor = Assessor.Assessor(
        client=assessor_client,
        assessment_history=assessment_history,
        new_messages=new_messages,
    )
    promptGenerator = PromptGenerator.SimplePromptGenerator2(
        chat_history=chat_history, options=options
    )
    intermediary = Intermediary.GraphIntermediary2(
        model,
        assessor=assessor,
        promptGenerator=promptGenerator,
        intent_history=intent_history,
    )
    tutor = Tutor.GraphTutor2(
        client,
        problem=problem,
        problem_set=problem_set,
        model=model,
        intermediary=intermediary,
        options=options,
        tools=tools,
    )

    new_history, new_intent, new_assessment_history, metadata = tutor.get_response2()
    new_assessment_history = new_assessment_history[
        1:
    ]  # [1:] because we don't include system prompt
    new_intent_history = intent_history + [new_intent]
    return (
        filter_out_system_messages(new_history["messages"]),
        new_intent_history,
        new_assessment_history,
        metadata,
    )
