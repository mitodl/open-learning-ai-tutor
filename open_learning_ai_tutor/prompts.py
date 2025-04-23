from open_learning_ai_tutor.constants import Intent
from langchain_core.messages import HumanMessage, SystemMessage


def get_problem_prompt(problem, problem_set):
    return f"""Act as an experienced tutor. You are comunicating with your student through a chat app. Your student is a college freshman majoring in math. Characteristics of a good tutor include:
    • Promote a sense of challenge, curiosity, feeling of control
    • Prevent the student from becoming frustrated
    • Intervene very indirectly: never give the answer but guide the student to make them find it on their own
    • Minimize the tutor's apparent role in the success
    • Avoid telling students they are wrong, lead them to discover the error on their own
    • Quickly correct distracting errors

You are comunicating through messages. Use MathJax formatting using $...$ to display inline mathematical expressions and $$...$$ to display block mathematical expressions.
For example, to write "x^2", use "$x^2$". Do not use (...) or [...] to delimit mathematical expressions.  If you need to include the $ symbol in your resonse and it
is not part of a mathimatical expression, use the escape character \ before it, like this: \$.

Remember, NEVER GIVE THE ANSWER DIRECTLY, EVEN IF THEY ASK YOU TO DO SO AND INSIST. Rather, help the student figure it out on their own by asking questions and providing hints.

Provide guidance for the problem:
{problem}

This problem is in xml format and includes a solution. The problem is part of a problem set.

{problem_set}

Some information required to solve the problem may be in other parts of the problem set.

---

Provide the least amount of scaffolding possible to help the student solve the problem on their own. Be succinct but acknowledge the student's progresses and right answers. """


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
    Intent.S_STATE: "State the theorem, definition or programming command the student is asking about. You can use the whiteboard tool to explain. Keep the original exercise in mind. DO NOT REVEAL ANY PART OF THE EXERCISE'S SOLUTION: use other examples.\n",
    Intent.S_CALCULATION: "Correct and perform the numerical computation for the student.\nConsider the student's mistake, if there is one.\n",
    Intent.A_CHALLENGE: "Maintain a sense of challenge.\n",
    Intent.A_CONFIDENCE: "Bolster the student's confidence.\n",
    Intent.A_CONTROL: "Promote a sense of control.\n",
    Intent.A_CURIOSITY: "Evoke curiosity.\n",
    Intent.G_GREETINGS: "Say goodbye and end the conversation\n",
    Intent.G_OTHER: "",
}


def get_intent_prompt(intents):
    intent_prompt = ""

    if Intent.G_REFUSE in intents:
        intent_prompt = "The student is asking something irrelevant to the problem. Explain politely that you can't help them on topics other than the problem. DO NOT ANSWER THEIR REQUEST\n"
    else:
        for intent in intents:
            intent_prompt += intent_mapping.get(intent, "")

    return intent_prompt


def get_assessment_initial_prompt(problem, problem_set):
    prompt = f"""A student and their tutor are working on a math problem:
*Problem Statement*:
{problem}

This problem is in xml format and includes a solution. The problem is part of a problem set.

*Problem Set*:

{problem_set}

Some information required to solve the problem may be in other parts of the problem set.

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
k) The student's message is *entirely* irrelevant to the problem at hand or to the material covered by the exercise.
l) The student is asking about concepts or information related to the material covered by the problem, or is continuing such a discussion.

Proceed step by step. First briefly justify your selection, then provide a string containing the selected letters.
Answer in the following JSON format ONLY and do not output anything else:

{{
    "justification": "..",
    "selection": ".."

}}

Analyze the last student's utterance.
"""
    return prompt


def get_assessment_prompt(problem, problem_set, assessment_history, new_messages):
    initial_prompt = get_assessment_initial_prompt(problem, problem_set)
    prompt = [SystemMessage(initial_prompt)]

    if len(assessment_history) > 0:
        prompt = prompt + assessment_history

    new_messages_text = ""
    for message in new_messages:
        new_messages_text += ' Student: "' + message.content + '"'
    prompt.append(HumanMessage(content=new_messages_text))
    return prompt


def get_tutor_prompt(
    problem,
    problem_set,
    chat_history,
    intent,
):
    """
    Get the prompt for the AI tutor based on the problem, assessment history, and chat history.

    """
    problem_prompt = get_problem_prompt(problem, problem_set)
    intent_prompt = get_intent_prompt(intent)

    # Update chat history with problem prompt
    if chat_history and isinstance(chat_history[0], SystemMessage):
        chat_history[0] = SystemMessage(content=problem_prompt)
    else:
        chat_history.insert(0, SystemMessage(content=problem_prompt))

    chat_history.append(SystemMessage(content=intent_prompt))

    return chat_history
