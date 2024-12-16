import PromptGenerator
import IntentSelector
import Assessor
from taxonomy import Intent

class Intermediary():
    def __init__(self,client,model,assessor = None, intentSelector=None,promptGenerator = None,intent_history = [],assessment_history=[]) -> None:
        self.client = client
        self.model = model

        self.assessor = Assessor.Assessor(self.client,self.model,assessment_history = assessment_history) if assessor is None else assessor
        self.intentSelector = IntentSelector.IntentSelector(intent_history=intent_history) if intentSelector is None else intentSelector
        self.promptGenerator = PromptGenerator.PromptGenerator() if promptGenerator is None else promptGenerator

    def update_client(self,client):
        self.client = client
        self.assessor.client = client
        self.intentSelector.client = client
        self.promptGenerator.client = client
            
    def update_model(self,model):
        self.model = model
        self.assessor.model = model
        self.intentSelector.model = model
        self.promptGenerator.model = model

    def get_prompt(self,pb,sol,student_messages,tutor_messages,open=True):
        print("generating tutor's prompt...")
        assessment,metadata = self.assessor.assess(pb,sol,student_messages,tutor_messages)
        assessor_prompt_tokens,assessor_completion_tokens = metadata[0], metadata[1]
        docs = None
        rag_questions = None
        if len(metadata) > 2:
            docs = metadata[2]
        if len(metadata) > 3:
            rag_questions = metadata[3]
        intent = self.intentSelector.get_intent(assessment,open=open)
        prompt = self.promptGenerator.get_prompt(pb,sol,student_messages,tutor_messages,intent,docs)
        return prompt,intent,assessment,assessor_prompt_tokens,assessor_completion_tokens,docs,rag_questions
    

# This is the one we use
class GraphIntermediary(Intermediary):
    def __init__(self,client,model,assessor = None, intentSelector=None,promptGenerator = None,intent_history = [],assessment_history=[], version="V1") -> None:
        self.client = client
        self.model = model

        self.assessor = Assessor.GraphAssessor(self.client,self.model,assessment_history = assessment_history, version=version) if assessor is None else assessor
        self.intentSelector = IntentSelector.SimpleIntentSelector(intent_history=intent_history) if intentSelector is None else intentSelector
        self.promptGenerator = PromptGenerator.SimplePromptGenerator(version=version) if promptGenerator is None else promptGenerator
