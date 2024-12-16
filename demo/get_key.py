from openai import AzureOpenAI
from openai import OpenAI
# Not used but would be a clean way to load keys    

#### New API key using OpenAi ####

def get_key_openAI():
    with open('./key_openAI.txt', 'r') as f:
        return tuple(map(str.strip,f.readlines()))
    
def get_client_openAI():
    #organization_key, project_key, secret_key = get_key_openAI()
    client = OpenAI(
    api_key="YOUR KEY"
    )
    return client
    