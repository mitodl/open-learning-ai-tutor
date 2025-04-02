from open_learning_ai_tutor.prompts import get_problem_prompt, get_intent_prompt
from open_learning_ai_tutor.intent_selector import get_intent
from open_learning_ai_tutor.constants import Intent
from langchain_core.messages import SystemMessage

def_options = {"version": "V1", "tools": None}


class GraphIntermediary:
    def __init__(
        self,
        model,
        assessment_history=[],
        chat_history=[],
        intent_history=[],
        options=dict(),
    ) -> None:
        self.model = model
        self.options = options
        self.intent_history = intent_history
        self.chat_history = chat_history
        self.assessment_history = assessment_history

    def get_prompt(self, problem, problem_set):
        metadata = {}
        assessment = self.assessment_history[-1].content

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

        problem_prompt = get_problem_prompt(problem, problem_set)
        intent_prompt = get_intent_prompt(intent)

        if isinstance(self.chat_history[0], SystemMessage):
            self.chat_history[0] = SystemMessage(content=problem_prompt)
        else:
            self.chat_history.insert(0, SystemMessage(content=problem_prompt))

        self.chat_history.append(SystemMessage(content=intent_prompt))

        return self.chat_history, intent, metadata
