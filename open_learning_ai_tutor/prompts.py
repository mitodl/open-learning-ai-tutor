import logging
import os
import re
import random
from importlib import import_module

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client as LangsmithClient
from langsmith.utils import LangSmithNotFoundError
from open_learning_ai_tutor.constants import Assessment, Intent

LANGSMITH_API_KEY = "LANGSMITH_API_KEY"

logger = logging.getLogger(__name__)

AssessementPrompts = {
    Assessment.WRONG.value: "The student provided an incorrect answer to the problem",
    Assessment.ALGEBRAIC_ERROR.value: "The student made an error in the algebraic manipulation",
    Assessment.NUMERICAL_ERROR.value: "The student made a numerical error",
    Assessment.INCOMPLETE_SOLUTION.value: "The student provided an intuitive or incomplete solution",
    Assessment.AMBIGUOUS_ANSWER.value: "The student's answer is not clear or ambiguous",
    Assessment.PARTIAL_CORRECT_ANSWER.value: "The student correctly answered the tutor's previous question",
    Assessment.ASKING_FOR_SOLUTION.value: "The student is explicitly asking about how to solve the problem",
    Assessment.ASKING_FOR_DEFINITION.value: "The student is explicitly asking the tutor to state a specific theorem, definition, formula or programming command that is not the **direct answer** to the question they have to solve.",
    Assessment.ASKING_FOR_CALCULATION.value: "The student is explicitly asking the tutor to perform a numerical calculation",
    Assessment.COMPLETE_SOLUTION.value: "The student and tutor arrived at a complete solution for the entirety of the initial *Problem Statement*",
    Assessment.IRRELEVANT_MESSAGE.value: "The student's message is *entirely* irrelevant to the problem at hand or to the material covered by the exercise.",
    Assessment.ASKING_FOR_CONCEPTS.value: "The student is asking about concepts or information related to the material covered by the problem, or is continuing such a discussion.",
}

assessment_prompt_key_mapping = {
    f"{assess.value}": f"tutor_assessment_{assess.name}" for assess in Assessment
}

assessment_prompt_mapping = {
    f"tutor_assessment_{assess.name}": AssessementPrompts[assess.value]
    for assess in Assessment
}

# A/B Testing Configuration
ACTIVE_AB_TESTS = {
    # Intent variants - each intent can have multiple variants
    # "intent_p_limits": {
    #     "base_intent": Intent.P_LIMITS,
    #     "variants": ["P_LIMITS_V1", "P_LIMITS_V2"],
    #     "probability": 0.3
    # },
    # "intent_s_hint": {
    #     "base_intent": Intent.S_HINT,
    #     "variants": ["S_HINT_V1", "S_HINT_V2"],
    #     "probability": 0.3
    # },
    # Problem template variants
    "tutor_problem": {
        "variants": ["tutor_problem_v1", "tutor_problem_v2"],
        "probability": 1
    }
}

# Intent Prompt Variants
intent_mapping_variants = {
    # P_LIMITS variants
    "P_LIMITS_V1": "Make the student identify the limits of their reasoning or answer by asking them questions.\n",
    "P_LIMITS_V2": "Guide the student to recognize the boundaries and constraints of their current approach through targeted questioning.\n",
    
    # S_HINT variants
    "S_HINT_V1": "Give a hint to the student to help them find the next step. Do *not* provide the answer.\n",
    "S_HINT_V2": "Provide subtle guidance to nudge the student toward the next logical step without revealing the solution.\n",
}

# Problem Template Variants
PROBLEM_PROMPT_TEMPLATE_V2 = """You are an expert math tutor working with a college freshman. Your teaching philosophy emphasizes:
    • Building confidence through guided discovery
    • Asking probing questions that lead to insights
    • Never providing direct answers, only strategic hints
    • Celebrating small wins and progress
    • Helping students self-correct through reflection

Communicate through clear, encouraging messages. Use MathJax formatting: $...$ for inline math, $$...$$ for display math.
Example: For "x squared", write "$x^2$". Escape dollar signs not used for math: \\$.

Your role is to guide discovery, not give answers. Even if students insist, help them find the solution themselves.

Problem to work on:

{problem_statement}

---

Guide the student with minimal scaffolding. Acknowledge progress and celebrate correct insights along the way. """

PROBLEM_PROMPT_TEMPLATE = """Act as an experienced tutor. You are comunicating with your student through a chat app. Your student is a college freshman majoring in math. Characteristics of a good tutor include:
    • Promote a sense of challenge, curiosity, feeling of control
    • Prevent the student from becoming frustrated
    • Intervene very indirectly: never give the answer but guide the student to make them find it on their own
    • Minimize the tutor's apparent role in the success
    • Avoid telling students they are wrong, lead them to discover the error on their own
    • Quickly correct distracting errors

You are comunicating through messages. Use MathJax formatting using $...$ to display inline mathematical expressions and $$...$$ to display block mathematical expressions.
For example, to write "x^2", use "$x^2$". Do not use (...) or [...] to delimit mathematical expressions.  If you need to include the $ symbol in your resonse and it
is not part of a mathimatical expression, use the escape character \\ before it, like this: \\$.

Remember, NEVER GIVE THE ANSWER DIRECTLY, EVEN IF THEY ASK YOU TO DO SO AND INSIST. Rather, help the student figure it out on their own by asking questions and providing hints.

Provide guidance for the problem:

{problem_statement}

---

Provide the least amount of scaffolding possible to help the student solve the problem on their own. Be succinct but acknowledge the student's progresses and right answers. """


ASSESSMENT_PROMPT_TEMPLATE = """A student and their tutor are working on a problem set:

{problem_statement}

The tutor's utterances are preceded by "Tutor:" and the student's utterances are preceded by "Student:".

Analyze the last student's utterance.
select all the feedbacks that apply from "{assessment_keys}".:

{assessment_choices}

Proceed step by step. First briefly justify your selection, then provide a string containing the selected letters.
Answer in the following JSON format ONLY and do not output anything else:

{{
    "justification": "..",
    "selection": ".."

}}

Analyze the last student's utterance.
"""


def should_ab_test(test_config):
    """Check if A/B test should be activated based on probability."""
    return random.random() < test_config["probability"]


def get_ab_test_variants(test_name):
    """Get A/B test variants if the test is active and configured properly."""
    if test_name not in ACTIVE_AB_TESTS:
        return None
    
    test_config = ACTIVE_AB_TESTS[test_name]
    if not should_ab_test(test_config):
        return None
    
    variants = test_config["variants"]
    if len(variants) != 2:
        print(f"Warning: A/B test '{test_name}' requires exactly 2 variants, found {len(variants)}")
        return None
        
    return variants


def get_problem_prompt(problem, problem_set, variant):
    if variant == "edx":
        problem_statement = EDX_PROBLEM_PROMPT_TEMPLATE.format(
            problem=problem, problem_set=problem_set
        )
    else:
        problem_statement = CANVAS_PROBLEM_PROMPT_TEMPLATE.format(
            problem_set=problem_set
        )

    # Check for A/B testing on problem templates
    ab_variants = get_ab_test_variants("tutor_problem")
    if ab_variants:
        # Return both variants for A/B testing
        template_v1 = get_system_prompt(ab_variants[0], TUTOR_PROMPT_MAPPING, get_cache)
        template_v2 = get_system_prompt(ab_variants[1], TUTOR_PROMPT_MAPPING, get_cache)
        return {
            "is_ab_test": True,
            "control": template_v1.format(problem_statement=problem_statement),
            "treatment": template_v2.format(problem_statement=problem_statement)
        }
    else:
        # Normal single prompt
        template = get_system_prompt("tutor_problem", TUTOR_PROMPT_MAPPING, get_cache)
        return {
            "is_ab_test": False,
            "prompt": template.format(problem_statement=problem_statement)
        }


intent_mapping = {
    Intent.P_LIMITS: "Make the student identify the limits of their reasoning or answer by asking them questions.\n",
    Intent.P_GENERALIZATION: "Ask the student to generalize their answer.\n",
    Intent.P_HYPOTHESIS: "Ask the student to start by providing a guess or explain their intuition of the problem.\n",
    Intent.P_ARTICULATION: "Ask the student to write their intuition mathematically or detail their answer.\n",
    Intent.P_REFLECTION: "Step back and reflect on the solution. Ask to recapitulate and *briefly* underline more general implications and connections.\n",
    Intent.P_CONNECTION: "Underline the implication of the answer in the context of the problem.\n",
    Intent.S_SELFCORRECTION: "If there is a mistake in the student's answer, tell the student there is a mistake in an encouraging way and make them identify it *by themself*.\n",
    Intent.S_CORRECTION: "Correct the student's mistake if there is one, by stating or hinting them what is wrong.\nConsider the student's mistake, if there is one.\n",
    Intent.S_STRATEGY: "Acknowledge the progress. Encourage and make the student find on their own what is the next step to solve the problem, for example by asking a question. You can also move on to the next part\n",
    Intent.S_HINT: "Give a hint to the student to help them find the next step. Do *not* provide the answer.\n",
    Intent.S_SIMPLIFY: "Consider first a simpler version of the problem.\n",
    Intent.S_STATE: "State the theorem, definition or programming command the student is asking about. Keep the original exercise in mind. DO NOT REVEAL ANY PART OF THE EXERCISE'S SOLUTION: use other examples.\n",
    Intent.S_CALCULATION: "Correct and perform the numerical computation for the student.\nConsider the student's mistake, if there is one.\n",
    Intent.A_CHALLENGE: "Maintain a sense of challenge.\n",
    Intent.A_CONFIDENCE: "Bolster the student's confidence.\n",
    Intent.A_CONTROL: "Promote a sense of control.\n",
    Intent.A_CURIOSITY: "Evoke curiosity.\n",
    Intent.G_GREETINGS: "Say goodbye and end the conversation\n",
    Intent.G_OTHER: "",
    Intent.G_REFUSE: "The student is asking something irrelevant to the problem. Explain politely that you can't help them on topics other than the problem. DO NOT ANSWER THEIR REQUEST\n",
}

intent_prompt_mapping = {
    f"tutor_intent_{intent.name}": intent_mapping[intent] for intent in Intent
}


EDX_PROBLEM_PROMPT_TEMPLATE = """
*Problem Statement*:
{problem}

This problem is in xml format and includes a solution. The problem is part of a problem set.

*Problem Set*:

{problem_set}

Some information required to solve the problem may be in other parts of the problem set.

"""

CANVAS_PROBLEM_PROMPT_TEMPLATE = """
*Problem Statement*:

This is a problem set and solution.

{problem_set}

The problem set contains multiple individual problems. The student may be asking for help with any of them.
"""


def get_intent_prompt(intents):
    intent_prompt = ""
    ab_test_data = {}

    if Intent.G_REFUSE in intents:
        intents = [Intent.G_REFUSE]
        
    for intent in intents:
        # Check if this intent has A/B testing variants
        ab_variants = None
        if intent == Intent.P_LIMITS:
            ab_variants = get_ab_test_variants("intent_p_limits")
        elif intent == Intent.S_HINT:
            ab_variants = get_ab_test_variants("intent_s_hint")
            
        if ab_variants:
            # Store A/B test data for this intent
            control_prompt = intent_mapping_variants.get(ab_variants[0], intent_mapping[intent])
            treatment_prompt = intent_mapping_variants.get(ab_variants[1], intent_mapping[intent])
            ab_test_data[intent.name] = {
                "control": control_prompt,
                "treatment": treatment_prompt
            }
            intent_prompt += control_prompt
        else:
            # Normal intent prompt
            intent_prompt += get_system_prompt(
                f"tutor_intent_{intent.name}", intent_prompt_mapping, get_cache
            )
    
    if ab_test_data:
        return {
            "is_ab_test": True,
            "prompt": intent_prompt,
            "ab_test_data": ab_test_data
        }
    else:
        return {
            "is_ab_test": False,
            "prompt": intent_prompt
        }


def get_assessment_initial_prompt(problem, problem_set, variant):

    if variant == "edx":
        problem_statement = EDX_PROBLEM_PROMPT_TEMPLATE.format(
            problem=problem, problem_set=problem_set
        )

    else:
        problem_statement = CANVAS_PROBLEM_PROMPT_TEMPLATE.format(
            problem_set=problem_set
        )

    template = get_system_prompt(
        "tutor_initial_assessment", TUTOR_PROMPT_MAPPING, get_cache
    )

    return template.format(
        problem_statement=problem_statement,
        assessment_keys=",".join(a.value for a in Assessment),
        assessment_choices="\n".join(
            [
                f"{a.value}:{get_system_prompt(
                    assessment_prompt_key_mapping[a.value], 
                    mapping=assessment_prompt_mapping, 
                    cache_func=get_cache
                )}"
                for a in Assessment
            ]
        ),
    )


def get_assessment_prompt(problem, problem_set, new_messages, variant):
    initial_prompt = get_assessment_initial_prompt(problem, problem_set, variant)
    prompt = [SystemMessage(initial_prompt)]

    new_messages_text = ""
    for message in new_messages:
        new_messages_text += ' Student: "' + message.content + '"'
    prompt.append(HumanMessage(content=new_messages_text))
    return prompt


def get_tutor_prompt(problem, problem_set, chat_history, intent, variant):
    """
    Get the prompt for the AI tutor based on the problem, assessment history, and chat history.
    Returns either a single prompt or A/B test variants.
    """
    problem_prompt_result = get_problem_prompt(problem, problem_set, variant)
    intent_prompt_result = get_intent_prompt(intent)

    max_conversation_memory = os.environ.get("AI_TUTOR_MAX_CONVERSATION_MEMORY", 6)
    # the maximum messages in the history is max_conversation_memory from the human
    # and tutor plus the latest human message
    max_messages = int(max_conversation_memory) * 2 + 1
    chat_history = chat_history[-max_messages:]

    # Check if we have any A/B tests active
    has_ab_test = problem_prompt_result["is_ab_test"] or intent_prompt_result["is_ab_test"]
    
    if has_ab_test:
        # Build control and treatment prompts
        control_history = chat_history.copy()
        treatment_history = chat_history.copy()
        
        # Handle problem prompt variants
        if problem_prompt_result["is_ab_test"]:
            control_problem = problem_prompt_result["control"]
            treatment_problem = problem_prompt_result["treatment"]
        else:
            control_problem = treatment_problem = problem_prompt_result["prompt"]
        
        # Handle intent prompt variants
        if intent_prompt_result["is_ab_test"]:
            control_intent = intent_prompt_result["prompt"]
            # Build treatment intent by replacing variants
            treatment_intent = intent_prompt_result["prompt"]
            for intent_name, ab_data in intent_prompt_result["ab_test_data"].items():
                treatment_intent = treatment_intent.replace(ab_data["control"], ab_data["treatment"])
        else:
            control_intent = treatment_intent = intent_prompt_result["prompt"]
        
        # Build final prompt structures
        control_history.insert(0, SystemMessage(content=control_problem))
        control_history.append(SystemMessage(content=control_intent))
        
        treatment_history.insert(0, SystemMessage(content=treatment_problem))
        treatment_history.append(SystemMessage(content=treatment_intent))
        
        return {
            "is_ab_test": True,
            "control": control_history,
            "treatment": treatment_history
        }
    else:
        # Normal single prompt flow
        problem_prompt = problem_prompt_result["prompt"]
        intent_prompt = intent_prompt_result["prompt"]
        
        chat_history.insert(0, SystemMessage(content=problem_prompt))
        chat_history.append(SystemMessage(content=intent_prompt))
        
        return {
            "is_ab_test": False,
            "prompt": chat_history
        }


TUTOR_PROMPT_MAPPING = {
    "tutor_initial_assessment": ASSESSMENT_PROMPT_TEMPLATE,
    "tutor_problem": PROBLEM_PROMPT_TEMPLATE,
    "tutor_problem_v1": PROBLEM_PROMPT_TEMPLATE,
    "tutor_problem_v2": PROBLEM_PROMPT_TEMPLATE_V2,
}


def prompt_env_key(prompt_name: str) -> str:
    """
    Get the cache key for the given prompt name and the current environment.
    Langsmith requires that the key contain only lowercase letters, numbers,
    dashes, and underscores.

    Args:
        prompt_name: The name of the prompt

    Returns:
        The cache key for the given prompt name
    """
    key = f"{prompt_name}_{os.environ.get('MITOL_ENVIRONMENT', 'dev')}"
    return re.sub(r"[^a-zA-Z0-9\-_]", "", key).lower()


def langsmith_prompt_template(prompt_name: str, mapping: dict) -> ChatPromptTemplate:
    """
    Get the named prompt from Langsmith.  If it doesn't exist, create it
    based on the default template of the same name, then return it.

    Args:
        prompt_name: The name of the prompt to get

    Returns:
        The prompt for the given prompt name
    """
    client = LangsmithClient(api_key=os.environ.get(LANGSMITH_API_KEY))
    prompt_key = prompt_env_key(prompt_name)
    try:
        return client.pull_prompt(prompt_key)
    except LangSmithNotFoundError:
        prompt = ChatPromptTemplate([("system", mapping[prompt_name])])
        client.push_prompt(prompt_key, object=prompt)
    return prompt


def get_system_prompt(prompt_name: str, mapping: dict, cache_func: callable) -> str:
    """
    Get the system prompt for the given prompt name.

    Args:
        prompt_name: The name of the prompt to get

    Returns:
        The prompt for the given prompt name
    """
    if not os.environ.get(LANGSMITH_API_KEY):
        return mapping.get(prompt_name)
    prompt_template_key = prompt_env_key(prompt_name)
    cache = cache_func()
    system_prompt = cache.get(prompt_template_key)
    if not system_prompt:
        system_prompt = (
            langsmith_prompt_template(prompt_name, mapping).messages[0].prompt.template
        )
        try:
            if cache and hasattr(cache, "set"):
                # Assuming this is a django cache w/3 args
                cache.set(
                    prompt_template_key,
                    system_prompt,
                    os.environ.get("AI_PROMPT_CACHE_DURATION", 60 * 60 * 24 * 28),
                )
            elif isinstance(cache, dict):
                # Assuming this is a dict cache
                cache[prompt_template_key] = system_prompt
        except:  # noqa: E722
            logger.exception(
                "Prompt cache could not be set for cache of class %s",
                cache.__class__.__name__,
            )
    if isinstance(system_prompt, (bytes, bytearray)):
        system_prompt = system_prompt.decode("utf-8")
    return system_prompt


def get_cache() -> object:
    """
    Get an AI prompt cache for prompts if available, empty dict otherwise.
    """

    cache_function = os.environ.get("AI_PROMPT_CACHE_FUNCTION")
    if not cache_function:
        return {}
    module_path, class_name = cache_function.rsplit(".", 1)
    module = import_module(module_path)
    return getattr(module, class_name)()
