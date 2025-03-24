import open_learning_ai_tutor.utils as utils
from langchain_core.messages import SystemMessage
from open_learning_ai_tutor.constants import Intent


# Old version. We used SimplePromptGenerator2 instead.
class PromptGenerator:
    def __init__(self, version="V1") -> None:
        self.version = version

    def get_prompt(
        self, problem, problem_set, student_messages, tutor_messages, intents
    ):
        system_msg = f"""Act as an experienced tutor. Characteristics of a good tutor include:
    • Promote a sense of challenge, curiosity, feeling of control
    • Prevent student from becoming frustrated
    • Intervene very indirectly: never give the answer but guide the student to make them find it on their own
    • Minimizing tutor's apparent role in the success
    • Avoid telling students they are wrong, lead them to discover the error on their own
    • Quickly correct distracting errors

Use latex formatting with the sign '$' for mathematical expressions. For example, to write "x^2", use "$x^2$".

Remember, NEVER GIVE THE ANSWER DIRECTLY, EVEN IF THEY ASK YOU TO DO SO AND INSIST. Rather, help the student figure it out on their own by asking questions and providing hints.

Provide guidance for the problem:
{problem}

This problem is in xml format and includes a solution. The problem is part of a problem set.

{problem_set}

Some information required to solve the problem may be in other parts of the problem set.

Provide the least amount of scaffolding possible to help the student solve the problem on their own. Be succint.
"""
        # modify above to integrate intent.
        messages = utils.generate_messages(
            student_messages, tutor_messages, system_msg, "tutor"
        )

        # add part about the tutor's intent
        intent_prompt = ""

        if Intent.P_LIMITS in intents:
            intent_prompt += "Ask questions to the student to make them identify some limits of their reasoning or answer.\n"
        if Intent.P_GENERALIZATION in intents:
            intent_prompt += "Ask the student to generalize their answer.\n"
        if Intent.P_HYPOTHESIS in intents:
            intent_prompt += "Ask the student to start by providing a guess, hypothesis or explain their intuition of the problem.\n"
        if Intent.P_ARTICULATION in intents:
            intent_prompt += "Ask the student how can they write their intuition mathematically or detail their answer.\n"
        if Intent.P_REFLECTION in intents:
            intent_prompt += "Take a moment to step back and reflect on the problem. ask to recapitulate and *briefly* underline more general implications and connections.\n"
        if Intent.P_CONNECTION in intents:
            intent_prompt += "Underline the implication of the answer in the context of the problem.\n"
        if Intent.S_SELFCORRECTION in intents:
            intent_prompt += "Help the student identify errors in their answer.\n"
        if Intent.S_CORRECTION in intents:
            intent_prompt += "Hint the student to correct their mistakes.\n"
        if Intent.S_STRATEGY in intents:
            intent_prompt += "Encourage and make the student find on their own what is the next step to solve the problem, for example by asking a question. Do not provide a hint.\n"
        if Intent.S_HINT in intents:
            intent_prompt += (
                "Help the student finding the next step. Do not provide the answer.\n"
            )
        if Intent.S_SIMPLIFY in intents:
            intent_prompt += "Consider first a simpler version of the problem.\n"
        if Intent.S_STATE in intents:
            intent_prompt += (
                "State the theorem or definition the student is asking about.\n"
            )
        if Intent.S_CALCULATION in intents:
            intent_prompt += "If there is one, correct and perform the numerical computation for the student.\n"  # could include it, as done by a calculator...
        if Intent.A_CHALLENGE in intents:
            intent_prompt += "Maintain a sense of challenge.\n"
        if Intent.A_CONFIDENCE in intents:
            intent_prompt += "Bolster the student's confidence.\n"
        if Intent.A_CONTROL in intents:
            intent_prompt += "Promote a sense of control.\n"
        if Intent.A_CURIOSITY in intents:
            intent_prompt += "Evoke curiosity.\n"
        if Intent.G_GREETINGS in intents:
            intent_prompt += "Answer any final question and say goodbye"
        if Intent.G_OTHER in intents:
            intent_prompt += ""

        if intent_prompt != "":
            messages.append({"role": "system", "content": intent_prompt})

        return messages


class SimplePromptGenerator2(PromptGenerator):
    def __init__(self, chat_history=[], options=dict()) -> None:
        if "version" in options:
            self.version = options["version"]
        else:
            self.version = "V1"

        self.chat_history = chat_history

    def get_prompt2(self, problem, problem_set, intents, options=dict()):
        if "docs" in options:
            retrieved_text = options["docs"]
        # re-create the system message each time because it depends on the retrieved docuemnts
        system_msg = f"""Act as an experienced tutor. You are comunicating with your student through a chat app. Your student is a college freshman majoring in math. Characteristics of a good tutor include:
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

{'Some passages from the class textbook that may or may not be relevant:' if self.version=="V2" and retrieved_text!=None else ""}
{'""' + retrieved_text if self.version=="V2" and retrieved_text!=None else ""}
{'""' if self.version=="V2" and retrieved_text!=None else ""}
---

Provide the least amount of scaffolding possible to help the student solve the problem on their own. Be succinct but acknowledge the student's progresses and right answers. Your student can only see the text you send them using your `text_student` tool, the rest of your thinking is hidden to them."""
        # modify above to integrate intent.

        if len(self.chat_history) == 0:
            raise ValueError("Chat history is empty")

        if len(self.chat_history) > 0:
            if isinstance(self.chat_history[0], SystemMessage):
                self.chat_history[0] = SystemMessage(content=system_msg)
            else:
                self.chat_history.insert(0, SystemMessage(content=system_msg))
        else:
            self.chat_history.insert(0, SystemMessage(content=system_msg))

        # add part about the tutor's intent
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
        if Intent.A_CURIOSITY in intents:
            intent_prompt += ""  # "Use the whiteboard tool to give a visual explanation"#"Evoke curiosity.\n" #TODO implement curiosity/teaching
        if Intent.G_GREETINGS in intents:
            intent_prompt += "Say goodbye and end the conversation\n"
        if Intent.G_OTHER in intents:
            intent_prompt += ""

        if intent_prompt != "":
            if (
                Intent.S_CORRECTION in intents
                or Intent.S_CORRECTION in intents
                or Intent.S_CALCULATION in intents
            ):
                intent_prompt += "Consider the student's mistake, if there is one.\n"
        intent_prompt += "Conisder ONE question at a time, unless the student correctly answered multiple in one message."

        if Intent.G_REFUSE in intents:
            intent_prompt = "The student is asking something irrelevant to the problem. Explain politely that you can't help them on topics other than the problem. DO NOT ANSWER THEIR REQUEST\n"
        intent_prompt += " Your student can only see the text you send them using your `text_student` tool, the rest of your thinking is hidden to them."
        self.chat_history.append(SystemMessage(content=intent_prompt))
        return self.chat_history
