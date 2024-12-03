from utils import print_logs
import Intermediary
import copy
from utils import generate_messages
from problems import consistency_pb


class Student():

    def __init__(self,client,pb=consistency_pb,level='10th grade student',confusion="lost and unsure how to proceed. You have never done this kind of problem before",emotion=None,model="myGPT4") -> None:
        print("---")
        print("Creating student...")
        print("---")
        self.client = client
        self.model = model
        self.update_system_message(pb,level,confusion,emotion)

    def update_system_message(self,pb,level = '10th grade student',confusion = "lost and unsure how to proceed",emotion=None):
        self.system_message = self.generate_system_message(pb,level,confusion,emotion)

    def generate_system_message(self,pb,level = '10th grade student',confusion = "lost and unsure how to proceed",emotion=None):
        return f"""You are a {level}, working on a math problem. You are texting with your tutor, the user, through a chat interface.
{"You are feeling" + emotion if emotion else ""}.
Math problem:
"{pb}"

Use latex formatting with the sign '$' for mathematical expressions. For example, to write \"x^2\", use \"$x^2$\".
Say 'Goodbye' when you want to end the conversation.
You are texting using a chat interface: typing is cumbersome so you keep your answers succint.
Remember, it's a simulation so you can do mistakes that a typical 10th grade student would do and text like a 10th grade student would. You can be stuck sometimes. However, keep all your numerical computations right.
You are {confusion}. Your tutor, the user, is here to help you with the problem."""
        

    def get_response(self,messages_student,messages_tutor,max_tokens=1500):
        messages_student = generate_messages(messages_student,messages_tutor,self.system_message,"student")

        print("student called")
        #print_logs(messages_student)
        completion = self.client.chat.completions.create(
            model = self.model,
            messages = messages_student,
            max_tokens = max_tokens,
            temperature = 1.1,
        )
        response = completion.choices[0].message.content
    
        total_tokens = completion.usage.total_tokens
        prompt_tokens = completion.usage.prompt_tokens
        completion_tokens = completion.usage.completion_tokens
        return response.replace("\(","$").replace("\)","$").replace("\[","$$").replace("\]","$$"), total_tokens, prompt_tokens, completion_tokens