# Agent that retrieves parts of the textbook to help the tutor LLM.


from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader, TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_together import ChatTogether
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from concurrent.futures import ThreadPoolExecutor
from open_learning_ai_tutor.Books import analytics_book


def generate_database(filepath,title,chunk_size,overlap,retriever_type="recursive"):
    # VECTOR DATABASE
    #BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    #db_path = os.path.join(BASE_DIR, f"{title[:-4]}")
    #####
    title = title.split(".")[0]
    col_exists = True
    try:
        coll =  Chroma.get_collection(f".db/{chunk_size}_{overlap}_{retriever_type}_{title}")
        return coll
    except:
        col_exists = False
    with open("./"+filepath, "w", encoding="utf-8") as f:
        f.write(analytics_book)
    loader = TextLoader("./"+filepath, encoding="utf-8")
    docs = loader.load()
    eq = {"recursive":RecursiveCharacterTextSplitter,"character":CharacterTextSplitter}
    text_splitter = eq[retriever_type](chunk_size=chunk_size, chunk_overlap=overlap)
    splits = text_splitter.split_documents(docs)
    ## Uncomment below if you want start and end metadata (useful for automatic evaluation)
    for split in splits:
        index1 = analytics_book.find(split.page_content)
        index2 = index1 + len(split.page_content)
        split.metadata["start_index"] = index1
        split.metadata["end_index"] = index2
    vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings(model="text-embedding-3-large"),collection_name = f"{chunk_size}_{overlap}_{retriever_type}_{title}",persist_directory="./db")
    return vectorstore


HyDE_prompt3 = """
You are given a tutoring session transcript. It consists of Student messages, starting with "Student:", and Tutor messages, starting with "Tutor:". You are also given the *problem* and *solution* they are working on.
Look at the **last** student's message. What would be the the title of the paragraph in an analytics textbook that would be most relevant to help the student? Give a paragraph title.
Use the following rules:
1. Use appropriate vocabulary. A title should be expected to be found in an analytics textbook. A title should be a short and descriptive sentence.
2. By default, use a single title. Only if the student is asking multiple things, write one title for each.
3. Use the minimum number of titles possible. Stay as close as possible to the original questions.

Look at the **last** student's message.

Output a JSON file and nothing else. Your output should follow the format:
{{
    "chapters": ["tile1",...]
}}

{{
"""

transcript_prompt = """
Problem statement:
<problem>
{pb}
</problem>

Solution:
<sol>
{sol}
</sol>

Tutoring conversation transcript:
<transcript>
{transcript}
</transcript>
"""

full_prompt_template = ChatPromptTemplate(
    input_variables=["pb", "sol", "transcript"],
    messages =[
    ("system", HyDE_prompt3),
    ("user", transcript_prompt)
])



def create_retriever(vectorstore,k=None,search_type='similarity',llm='gpt',prompt_type='base'):
    eq_llm = {"gpt":ChatOpenAI(temperature=0, model="gpt-4o-mini",  model_kwargs={ "response_format": { "type": "json_object" } }),
              "claude":ChatAnthropic(temperature=0, model="claude-3-5-haiku-20241022"),
              "llama": ChatTogether(model="nvidia/Llama-3.1-Nemotron-70B-Instruct-HF", temperature=0.0),
              "llama-mini": ChatTogether(model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", temperature=0.0),
              "mistral": ChatTogether(model="mistralai/Mistral-7B-Instruct-v0.3", temperature=0.0)}
    eq_type = {"base":None,"chapter":HyDE_prompt3}
    eq_json_field_name = {"base":None,"chapter":"chapters"}

    asker_llm = eq_llm[llm]
    selected_prompt_type = eq_type[prompt_type]
    HyDE_prompt_template = field_name = None
    if selected_prompt_type:
        HyDE_prompt_template = PromptTemplate(
            input_variables=["pb", "sol"],
            template=selected_prompt_type
        )
        field_name = eq_json_field_name[prompt_type]
    
    if k:
        retriever = vectorstore.as_retriever(search_kwargs={"k": k},search_type=search_type)
    else:
        retriever = vectorstore.as_retriever(search_type=search_type)

    if prompt_type=='base':
        return retriever
    
    def my_retriever(questions_dict):
        questions = [question for question in questions_dict[field_name]]
        print(questions)
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(retriever.invoke, questions))
        final_res = []
        final_contents = []
        for l in results:
            for doc in l:
                if doc.page_content not in final_contents:
                    final_res.append(doc)
                    final_contents.append(doc.page_content)
        return final_res,questions
    

    parser = JsonOutputParser()
    HyDE_retriever_chain = (
        full_prompt_template | asker_llm | parser | my_retriever
    )
    return HyDE_retriever_chain


class Retriever():
    def __init__(self,filepath,chunk_size=300,overlap=200,retriever_type="recursive",k=None,search_type='similarity',llm='llama-mini',prompt_type='chapter'):
        database = generate_database(filepath,filepath,chunk_size,overlap,retriever_type)
        self.database = database
        retriever = create_retriever(self.database,k=k,search_type=search_type,llm=llm,prompt_type=prompt_type)
        self.retriever = retriever
        self.rag_queries = None
    
    def invoke(self,prompt):
        ret, questions =  self.retriever.invoke(prompt)
        self.rag_queries = questions
        return ret, questions