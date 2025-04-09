import pytest
from open_learning_ai_tutor.constants import Intent
from open_learning_ai_tutor.prompts import (
    get_intent_prompt,
    intent_mapping,
    get_assessment_prompt,
    get_assessment_initial_prompt,
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
async def test_get_assessment_prompt(mocker, existing_assessment_history):
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
