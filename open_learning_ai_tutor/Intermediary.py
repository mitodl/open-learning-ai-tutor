import open_learning_ai_tutor.PromptGenerator as PromptGenerator
import open_learning_ai_tutor.IntentSelector as IntentSelector
import open_learning_ai_tutor.Assessor as Assessor

def_options = {"version":"V1","tools":None}

class Intermediary():
    def __init__(self,client,model,assessor = None, intentSelector=None,promptGenerator = None,intent_history = [],assessment_history=[]) -> None:
        self.client = client
        self.model = model

        self.assessor = Assessor.Assessor(self.client,self.model,assessment_history = assessment_history) if assessor is None else assessor
        self.intentSelector = IntentSelector.IntentSelector(intent_history=intent_history) if intentSelector is None else intentSelector
        self.promptGenerator = PromptGenerator.RigidPromptGenerator() if promptGenerator is None else promptGenerator

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
        #print("generating tutor's prompt...")
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
    
class GraphIntermediary2(Intermediary):
    def __init__(self,model,assessor = None, intentSelector=None,promptGenerator = None,chat_history = [],intent_history = [],assessment_history=[], options = dict()) -> None:
        self.model = model
        self.options = options
        self.assessor = Assessor.GraphAssessor2(self.model,assessment_history = assessment_history, new_messages=[], options = options) if assessor is None else assessor
        self.intentSelector = IntentSelector.SimpleIntentSelector2(intent_history=intent_history, options = options) if intentSelector is None else intentSelector
        self.promptGenerator = PromptGenerator.SimplePromptGenerator2(options = options, chat_history = chat_history) if promptGenerator is None else promptGenerator

    def get_prompt2(self,pb,sol):
        #print("generating tutor's prompt...")
        assessment_history,metadata = self.assessor.assess2(pb,sol)
        assessment = assessment_history[-1].content
        
        docs = None
        rag_questions = None
        if "docs" in metadata:
            self.options["docs"] = metadata["docs"]
        if "rag_queries" in metadata:
            self.options["rag_questions"] = metadata["rag_queries"]

        intent = self.intentSelector.get_intent(assessment)
       
        chat_history = self.promptGenerator.get_prompt2(pb,sol,intent,self.options)
        
        return chat_history,intent,assessment_history, metadata