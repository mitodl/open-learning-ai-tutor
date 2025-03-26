import open_learning_ai_tutor.utils as utils
from open_learning_ai_tutor.constants import Intent


def get_problem_prompt(problem, problem_set):
    return f"""Act as an experienced tutor. You are comunicating with your student through a chat app. Your student is a college freshman majoring in math. Characteristics of a good tutor include:
    • Promote a sense of challenge, curiosity, feeling of control
    • Prevent the student from becoming frustrated
    • Intervene very indirectly: never give the answer but guide the student to make them find it on their own
    • Minimize the tutor's apparent role in the success
    • Avoid telling students they are wrong, lead them to discover the error on their own
    • Quickly correct distracting errors

You are comunicating through messages. Use latex formatting with the sign '$' for mathematical expressions. For example, to write "x^2", use "$x^2$".

Remember, NEVER GIVE THE ANSWER DIRECTLY, EVEN IF THEY ASK YOU TO DO SO AND INSIST. Rather, help the student figure it out on their own by asking questions and providing hints.

Provide guidance for the problem:
{problem}

This problem is in xml format and includes a solution. The problem is part of a problem set.

{problem_set}

Some information required to solve the problem may be in other parts of the problem set.

---

Provide the least amount of scaffolding possible to help the student solve the problem on their own. Be succinct but acknowledge the student's progresses and right answers. Your student can only see the text you send them using your `text_student` tool, the rest of your thinking is hidden to them."""


def get_intent_prompt(intents):
        intent_prompt = ""
        if Intent.P_LIMITS in intents:
            intent_prompt += "Make the student identify the limits of their reasoning or answer by asking them questions.\n"
        if Intent.P_GENERALIZATION in intents:
            intent_prompt += "Ask the student to generalize their answer.\n"
        if Intent.P_HYPOTHESIS in intents:
            intent_prompt += "Ask the student to start by providing a guess or explain their intuition of the problem.\n"
        if Intent.P_ARTICULATION in intents:
            intent_prompt += "Ask the student to write their intuition mathematically or detail their answer.\n"
        if Intent.P_REFLECTION in intents:
            intent_prompt += "Step back and reflect on the solution. Ask to recapitulate and *briefly* underline more general implications and connections.\n"
        if Intent.P_CONNECTION in intents:
            intent_prompt += "Underline the implication of the answer in the context of the problem.\n"
        if Intent.S_SELFCORRECTION in intents:
            intent_prompt += "If there is a mistake in the student's answer, tell the student there is a mistake in an encouraging way and make them identify it *by themself*.\n"
        if Intent.S_CORRECTION in intents:
            intent_prompt += "Correct the student's mistake if there is one, by stating or hinting them what is wrong.\n"
        if Intent.S_STRATEGY in intents:
            intent_prompt += "Acknowledge the progress. Encourage and make the student find on their own what is the next step to solve the problem, for example by asking a question. You can also move on to the next part\n"  # "Encourage and make the student find on their own what is the next step to solve the problem by asking them what is the next step.\n"
        if Intent.S_HINT in intents:
            intent_prompt += "Give a hint to the student to help them find the next step. Do *not* provide the answer.\n"
        if Intent.S_SIMPLIFY in intents:
            intent_prompt += "Consider first a simpler version of the problem.\n"
        if Intent.S_STATE in intents:
            intent_prompt += "State the theorem, definition or programming command the student is asking about. You can use the whiteboard tool to explain. Keep the original exercise in mind. DO NOT REVEAL ANY PART OF THE EXERCISE'S SOLUTION: use other examples.\n"
        if Intent.S_CALCULATION in intents:
            intent_prompt += (
                "Correct and perform the numerical computation for the student.\n"
            )
        if Intent.A_CHALLENGE in intents:
            intent_prompt += "Maintain a sense of challenge.\n"
        if Intent.A_CONFIDENCE in intents:
            intent_prompt += "Bolster the student's confidence.\n"
        if Intent.A_CONTROL in intents:
            intent_prompt += "Promote a sense of control.\n"
        if Intent.G_GREETINGS in intents:
            intent_prompt += "Say goodbye and end the conversation\n"

        if intent_prompt != "":
            if (
                Intent.S_CORRECTION in intents
                or Intent.S_CALCULATION in intents
            ):
                intent_prompt += "Consider the student's mistake, if there is one.\n"

        return intent_prompt





