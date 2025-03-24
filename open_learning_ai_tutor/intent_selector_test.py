import pytest
import json
from open_learning_ai_tutor.constants import Intent, Assesment
from open_learning_ai_tutor.intent_selector import get_intent


@pytest.mark.parametrize(
    ("assesment_selections", "previous_intent", "intents"),
    [
        ([Assesment.IRRELEVANT_MESSAGE.value], [], [Intent.G_REFUSE]),
        (
            [Assesment.ASKING_FOR_CONCEPTS.value],
            [],
            [Intent.S_STATE, Intent.A_CURIOSITY],
        ),
        ([Assesment.ASKING_FOR_CALCULATION.value], [], [Intent.S_CALCULATION]),
        ([Assesment.ASKING_FOR_DEFINITION.value], [], [Intent.S_STATE]),
        ([Assesment.AMBIGUOUS_ANSWER.value], [], [Intent.P_ARTICULATION]),
        (
            [Assesment.AMBIGUOUS_ANSWER.value, Assesment.ASKING_FOR_SOLUTION.value],
            [],
            [Intent.P_HYPOTHESIS],
        ),
        (
            [
                Assesment.PARTIAL_CORRECT_ANSWER.value,
                Assesment.ASKING_FOR_CALCULATION.value,
            ],
            [],
            [Intent.S_CALCULATION],
        ),
        (
            [
                Assesment.PARTIAL_CORRECT_ANSWER.value,
                Assesment.ASKING_FOR_CALCULATION.value,
            ],
            [Intent.S_SELFCORRECTION],
            [Intent.S_CALCULATION, Intent.S_STRATEGY],
        ),
        ([Assesment.WRONG.value], [], [Intent.S_SELFCORRECTION]),
        (
            [Assesment.WRONG.value],
            [Intent.S_SELFCORRECTION],
            [Intent.S_CORRECTION, Intent.S_SELFCORRECTION],
        ),
        ([Assesment.ALGEBRAIC_ERROR.value], [], [Intent.S_SELFCORRECTION]),
        (
            [Assesment.ALGEBRAIC_ERROR.value],
            [Intent.S_SELFCORRECTION],
            [Intent.S_CORRECTION, Intent.S_SELFCORRECTION],
        ),
        ([Assesment.NUMERICAL_ERROR.value], [], [Intent.S_SELFCORRECTION]),
        (
            [Assesment.NUMERICAL_ERROR.value],
            [Intent.S_SELFCORRECTION],
            [Intent.S_CALCULATION],
        ),
        ([Assesment.ASKING_FOR_SOLUTION.value], [Intent.P_HYPOTHESIS], [Intent.S_HINT]),
        ([Assesment.ASKING_FOR_SOLUTION.value], [], [Intent.P_HYPOTHESIS]),
        (
            [Assesment.ASKING_FOR_SOLUTION.value, Assesment.INCOMPLETE_SOLUTION.value],
            [],
            [Intent.S_STRATEGY, Intent.S_HINT],
        ),
        ([Assesment.WRONG.value], [], [Intent.S_SELFCORRECTION]),
        (
            [Assesment.WRONG.value, Assesment.ASKING_FOR_CALCULATION.value],
            [],
            [Intent.S_CALCULATION],
        ),
        ([Assesment.INCOMPLETE_SOLUTION.value], [], [Intent.S_STRATEGY, Intent.S_HINT]),
        ([Assesment.PARTIAL_CORRECT_ANSWER.value], [], [Intent.S_STRATEGY]),
        ([Assesment.COMPLETE_SOLUTION.value], [], [Intent.G_GREETINGS]),
    ],
)
def test_intent_selector(assesment_selections, previous_intent, intents):
    """Test get_intent"""
    assesments = json.dumps({"selection": "".join(assesment_selections)})
    assert set(get_intent(assesments, previous_intent)) == set(intents)
