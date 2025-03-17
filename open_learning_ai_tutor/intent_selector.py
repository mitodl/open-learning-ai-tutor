from open_learning_ai_tutor.constants import Intent, Assesment
import json
import logging

logger = logging.getLogger(__name__)


def extract_assessment_codes(assessment):
    try:
        json_data = json.loads(assessment)
        selection = json_data["selection"]
        codes = list(selection)
        return codes
    except json.decoder.JSONDecodeError:
        logger.error(
            f"Error decoding assessment: {assessment}. Defaulting to m) The student is asking about concepts"
            "or information related to the materialcovered by the problem, or is continuing such a discussion. "
        )
        return [Assesment.ASKING_FOR_CONCEPTS.value]


def get_intent(assessment, previous_intent):
    assessment_codes = extract_assessment_codes(assessment)

    intents = []
    if Assesment.IRRELEVANT_MESSAGE.value in assessment_codes:
        return [Intent.G_REFUSE]

    if Assesment.ASKING_FOR_CONCEPTS.value in assessment_codes:
        intents.append(Intent.S_STATE)
        intents.append(Intent.A_CURIOSITY)

    if Assesment.ASKING_FOR_CALCULATION.value in assessment_codes:
        intents.append(Intent.S_CALCULATION)

    if Assesment.ASKING_FOR_DEFINITION.value in assessment_codes:
        intents.append(Intent.S_STATE)

    if (
        Assesment.AMBIGUOUS_ANSWER.value in assessment_codes
        and Assesment.ASKING_FOR_SOLUTION.value not in assessment_codes
    ):
        intents.append(Intent.P_ARTICULATION)

    if Intent.S_SELFCORRECTION in previous_intent:
        if Assesment.PARTIAL_CORRECT_ANSWER.value in assessment_codes:
            intents.append(Intent.S_STRATEGY)
        elif (
            Assesment.WRONG.value in assessment_codes
            or Assesment.ALGEBRAIC_ERROR.value in assessment_codes
        ):
            intents.append(Intent.S_CORRECTION)
        if Assesment.NUMERICAL_ERROR.value in assessment_codes:
            intents.append(Intent.S_CALCULATION)

    if Assesment.ASKING_FOR_SOLUTION.value in assessment_codes:
        if Intent.P_HYPOTHESIS in previous_intent:
            intents.append(Intent.S_HINT)
        elif (
            Assesment.INCOMPLETE_SOLUTION.value not in assessment_codes
            and Assesment.PARTIAL_CORRECT_ANSWER.value not in assessment_codes
        ):
            intents.append(Intent.P_HYPOTHESIS)

        if Intent.S_CORRECTION in previous_intent:
            intents.append(Intent.S_CORRECTION)

    if (
        any(
            code in assessment_codes
            for code in (
                Assesment.WRONG.value,
                Assesment.ALGEBRAIC_ERROR.value,
                Assesment.NUMERICAL_ERROR.value,
            )
        )
        and not Intent.S_CALCULATION in intents
    ):
        intents.append(Intent.S_SELFCORRECTION)
    elif Assesment.INCOMPLETE_SOLUTION.value in assessment_codes:
        intents.append(Intent.S_STRATEGY)
        intents.append(Intent.S_HINT)

    if Assesment.COMPLETE_SOLUTION.value in assessment_codes and not any(
        code in intents
        for code in (Intent.S_CORRECTION, Intent.S_SELFCORRECTION, Intent.S_CALCULATION)
    ):
        intents.append(Intent.G_GREETINGS)

    if intents == []:
        intents.append(Intent.S_STRATEGY)

    # remove duplicates
    intents = list(set(intents))
    return intents
