import open_learning_ai_tutor.PromptGenerator as PromptGenerator
from open_learning_ai_tutor.intent_selector import get_intent
from open_learning_ai_tutor.constants import Intent

def_options = {"version": "V1", "tools": None}


class GraphIntermediary2:
    def __init__(
        self,
        model,
        assessor,
        promptGenerator=None,
        chat_history=[],
        intent_history=[],
        assessment_history=[],
        options=dict(),
    ) -> None:
        self.model = model
        self.options = options
        self.assessor = assessor
        self.intent_history = intent_history
        self.promptGenerator = (
            PromptGenerator.SimplePromptGenerator2(
                options=options, chat_history=chat_history
            )
            if promptGenerator is None
            else promptGenerator
        )

    def get_prompt2(self, problem, problem_set):
        assessment_history = self.assessor.assess(problem, problem_set)
        metadata = {}
        assessment = assessment_history[-1].content

        if "docs" in metadata:
            self.options["docs"] = metadata["docs"]
        if "rag_queries" in metadata:
            self.options["rag_questions"] = metadata["rag_queries"]

        previous_intent = (
            self.intent_history[-1]
            if self.intent_history != []
            else [Intent.S_STRATEGY]
        )
        intent = get_intent(assessment, previous_intent)

        chat_history = self.promptGenerator.get_prompt2(
            problem, problem_set, intent, self.options
        )

        return chat_history, intent, assessment_history, metadata
