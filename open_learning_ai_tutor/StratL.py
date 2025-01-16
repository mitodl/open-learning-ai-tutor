# By Romain Puech, Jan 2025
import json
import open_learning_ai_tutor.Tutor as Tutor
import open_learning_ai_tutor.Assessor as Assessor
import open_learning_ai_tutor.IntentSelector as IntentSelector
import open_learning_ai_tutor.PromptGenerator as PromptGenerator
import open_learning_ai_tutor.Intermediary as Intermediary




def message_tutor(problem: str, solution: str, client, student_messages:list, tutor_messages:list, assessment_history:list, intent_history:list, options:dict):
    """
    Perform the steps to generate a response to the student message.
    Args:
        problem (str): The problem text.
        solution (str): The solution text.
        client (langchain client): The langchain client for the LLM selected for the problem.
        student_messages (list): The chat history of student messages.
        tutor_messages (list): The chat history of tutor messages.
        assessment_history (list): The history of previous assessments of student state/intent.
        intent_history (list): The history of previous intents.
        options (dict): Optional options that will influence tutor intent inference or prompt generation:
            - version (str): The version of the tutor to use.
            - tools (list): The list of tools to use for the tutor.
    Returns:
        str: A JSON string with the following keys:
            - output (str): The text response to be shown to the student.
            - intents (list): The chosen tutor's intens
            - assessments (list): The assessments of the student's state/intent.
            - extra_infromation (dict): Extra information that can be used for debugging or analysis:
                + tutor_prompt_tokens (int): The number of tokens in the tutor's prompt.
                + tutor_completion_tokens (int): The number of tokens in the tutor's completion.
                + version_dependent_information (dict): Information that is specific to the tutor version used (tools used, rag questions used, documents retrieved, etc.)

    """
    model = client.model_name
    assessor = Assessor.GraphAssessor(client, model, assessment_history, version = options['version'] if 'version' in options else 'V1')
    intentSelector = IntentSelector.SimpleIntentSelector(intent_history)
    promptGenerator = PromptGenerator.SimplePromptGenerator(version=options['version'] if 'version' in options else 'V1')
    intermediary = Intermediary.GraphIntermediary(client, model, assessor, intentSelector, promptGenerator)
    tutor = Tutor.GraphTutor(client, pb = problem, sol = solution, model = client, intermediary = intermediary, version = options['version'] if 'version' in options else '', tools = options['tools'] if 'tools' in options else [])
    output, tutor_total_tokens, tutor_prompt_tokens, tutor_completion_tokens, intent_turn, assessment_turn,extra = tutor.get_response(student_messages, tutor_messages)
    intent_history.append(intent_turn)
    assessment_history.append(assessment_turn)

    #generate_and_commit(g,repo,session_id, exercise_id, user_id, username, pb, sol, student_messages, tutor_messages, assessment_history, intent_history)
    res = json.dumps({"response": output, "intents": [intent.name for intent in intent_turn], "assessments": assessment_turn, "extra_information": {"tutor_prompt_tokens": tutor_prompt_tokens, "tutor_completion_tokens": tutor_completion_tokens, 'version_dependent_information':extra}})
    return res