from open_learning_ai_tutor.taxonomy import Intent
import json


class IntentSelector():
    def __init__(self,intent_history=[]) -> None:
        self.previous_intent = intent_history[-1] if intent_history != [] else [Intent.S_STRATEGY]

    def get_intent(self,assessment,open=True):
        print("selecting intent... ")
        previous_intent = self.previous_intent
        assessment_codes = self.extract_assessment_codes(assessment)
        intents = self.get_intent_aux(previous_intent,assessment_codes,open=open)
        print(f"selected intent: {intents}")
        return intents
    
    def extract_assessment_codes(self,assessment):
        json_data = json.loads(assessment)
        selection = json_data['selection']
        codes = list(selection)
        return codes
        
    def get_intent_aux(self,previous_intent,assessment_codes,open=True):
        raise NotImplementedError("This method should be implemented in the subclass")


# This is the one we use
class SimpleIntentSelector(IntentSelector):

    def get_intent_aux(self, previous_intent,assessment_codes, open=True):
        intents = []
        if 'l' in assessment_codes: # here l is irrelevant, not motiv
            return [Intent.G_REFUSE]
        if 'm' in assessment_codes:
            intents.append(Intent.S_STATE)
            intents.append(Intent.A_CURIOSITY)
        if 'i' in assessment_codes:
            intents.append(Intent.S_OFFLOAD)
        if 'h' in assessment_codes:
            intents.append(Intent.S_STATE)
        if 'e' in assessment_codes and 'g' not in assessment_codes:
            intents.append(Intent.P_ARTICULATION)
        if any(code in assessment_codes for code in ('a','b','c')):
            intents.append(Intent.S_SELFCORRECTION)
        elif 'd' in assessment_codes:
            intents.append(Intent.S_STRATEGY)
            intents.append(Intent.S_HINT)

        # previous intent-dependent selections:
        
        if Intent.S_SELFCORRECTION in previous_intent:
            if 'f' in assessment_codes:
                intents.append(Intent.S_STRATEGY)
            elif 'a' in assessment_codes or 'b' in assessment_codes:
                intents.append(Intent.S_CORRECTION)
            if 'c' in assessment_codes:
                intents.append(Intent.S_OFFLOAD)

        if 'g' in assessment_codes:
            if Intent.P_HYPOTHESIS in previous_intent:
                intents.append(Intent.S_HINT)
            elif 'd' not in assessment_codes and 'f' not in assessment_codes:
                    intents.append(Intent.P_HYPOTHESIS)

            if Intent.S_CORRECTION in previous_intent:
                intents.append(Intent.S_CORRECTION)
            
        

        if len(intents)==0 and ('f' in assessment_codes or 'g' in assessment_codes):
            intents.append(Intent.S_STRATEGY)
        
        #dirty fixes
        if Intent.S_CORRECTION in intents and Intent.S_SELFCORRECTION in intents:
            intents.remove(Intent.S_SELFCORRECTION)

        if Intent.S_SELFCORRECTION in intents and Intent.S_OFFLOAD in intents:
            intents.remove(Intent.S_SELFCORRECTION)

        if not (Intent.S_CORRECTION in intents) and not (Intent.S_SELFCORRECTION in intents) and not (Intent.S_OFFLOAD in intents) and 'j' in assessment_codes:
            intents.append(Intent.G_GREETINGS)

        if intents == []:
            intents.append(Intent.S_STRATEGY)
        self.previous_intent = intents
        return intents

