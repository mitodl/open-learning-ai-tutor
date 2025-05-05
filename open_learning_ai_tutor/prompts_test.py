import pytest
from open_learning_ai_tutor.constants import Intent
from open_learning_ai_tutor.prompts import (
    get_intent_prompt,
    intent_mapping,
    get_assessment_prompt,
    get_assessment_initial_prompt,
    get_tutor_prompt,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


@pytest.mark.parametrize(
    ("intents", "message"),
    [
        ([Intent.P_LIMITS], intent_mapping[Intent.P_LIMITS]),
        (
            [Intent.P_GENERALIZATION, Intent.P_HYPOTHESIS, Intent.P_ARTICULATION],
            f"{intent_mapping[Intent.P_GENERALIZATION]}{intent_mapping[Intent.P_HYPOTHESIS]}{intent_mapping[Intent.P_ARTICULATION]}",
        ),
        (
            [Intent.S_STATE, Intent.S_CORRECTION],
            f"{intent_mapping[Intent.S_STATE]}{intent_mapping[Intent.S_CORRECTION]}",
        ),
        (
            [Intent.G_REFUSE, Intent.P_ARTICULATION],
            "The student is asking something irrelevant to the problem. Explain politely that you can't help them on topics other than the problem. DO NOT ANSWER THEIR REQUEST\n",
        ),
        (
            [Intent.G_REFUSE],
            "The student is asking something irrelevant to the problem. Explain politely that you can't help them on topics other than the problem. DO NOT ANSWER THEIR REQUEST\n",
        ),
    ],
)
def test_intent_prompt(intents, message):
    """Test get_intent"""
    assert get_intent_prompt(intents) == message


@pytest.mark.parametrize("existing_assessment_history", [True, False])
def test_get_assessment_prompt(mocker, existing_assessment_history):
    """Test that the Assessor create_prompt method returns the correct prompt."""
    if existing_assessment_history:
        assessment_history = [
            HumanMessage(content=' Student: "what do i do next?"'),
            AIMessage(
                content='{\n    "justification": "The student is explicitly asking for guidance on how to proceed with solving the problem, indicating they are unsure of the next steps.",\n    "selection": "g"\n}'
            ),
        ]
    else:
        assessment_history = []

    new_messages = [HumanMessage(content="what if i took the mean?")]

    problem = "problem"
    problem_set = "problem_set"

    prompt = get_assessment_prompt(
        problem, problem_set, assessment_history, new_messages
    )

    initial_prompt = SystemMessage(get_assessment_initial_prompt(problem, problem_set))
    new_messages_prompt_part = HumanMessage(
        content=' Student: "what if i took the mean?"'
    )

    if existing_assessment_history:
        expected_prompt = [
            initial_prompt,
            *assessment_history,
            new_messages_prompt_part,
        ]
    else:
        expected_prompt = [initial_prompt, new_messages_prompt_part]
    assert prompt == expected_prompt


def test_get_tutor_prompt():
    """Test that the Tutor create_prompt method returns the correct prompt."""
    problem = "problem"
    problem_set = "problem_set"
    chat_history = [
        HumanMessage(content=' Student: "what do i do next?"'),
    ]
    intent = [Intent.P_HYPOTHESIS]

    prompt = get_tutor_prompt(problem, problem_set, chat_history, intent)
    expected_prompt = [
        SystemMessage(
            content='Act as an experienced tutor. You are comunicating with your student through a chat app. Your student is a college freshman majoring in math. Characteristics of a good tutor include:\n    • Promote a sense of challenge, curiosity, feeling of control\n    • Prevent the student from becoming frustrated\n    • Intervene very indirectly: never give the answer but guide the student to make them find it on their own\n    • Minimize the tutor\'s apparent role in the success\n    • Avoid telling students they are wrong, lead them to discover the error on their own\n    • Quickly correct distracting errors\n\nYou are comunicating through messages. Use MathJax formatting using $...$ to display inline mathematical expressions and $$...$$ to display block mathematical expressions.\nFor example, to write "x^2", use "$x^2$". Do not use (...) or [...] to delimit mathematical expressions.  If you need to include the $ symbol in your resonse and it\nis not part of a mathimatical expression, use the escape character \\ before it, like this: \\$.\n\nRemember, NEVER GIVE THE ANSWER DIRECTLY, EVEN IF THEY ASK YOU TO DO SO AND INSIST. Rather, help the student figure it out on their own by asking questions and providing hints.\n\nProvide guidance for the problem:\nproblem\n\nThis problem is in xml format and includes a solution. The problem is part of a problem set.\n\nproblem_set\n\nSome information required to solve the problem may be in other parts of the problem set.\n\n---\n\nProvide the least amount of scaffolding possible to help the student solve the problem on their own. Be succinct but acknowledge the student\'s progresses and right answers. ',
            additional_kwargs={},
            response_metadata={},
        ),
        HumanMessage(
            content=' Student: "what do i do next?"',
            additional_kwargs={},
            response_metadata={},
        ),
        SystemMessage(
            content="Ask the student to start by providing a guess or explain their intuition of the problem.\n",
            additional_kwargs={},
            response_metadata={},
        ),
    ]

    assert prompt == expected_prompt
