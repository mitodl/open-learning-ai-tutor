# IMPORTS AND VECTOR DATABASE CREATION

## Imports
from operator import itemgetter
import time
from langchain import hub
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader, TextLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pandas as pd
import json
from langchain.chains import create_citation_fuzzy_match_chain
from langchain_openai import ChatOpenAI
import os
from langchain.chains import RetrievalQA
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain.chains import create_qa_with_sources_chain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser


def generate_database(title,chunk_size,overlap,retriever_type="recursive"):
    # VECTOR DATABASE
    loader = TextLoader("book_no_index.txt", encoding="utf-8")
    docs = loader.load()
    eq = {"recursive":RecursiveCharacterTextSplitter,"character":CharacterTextSplitter}
    text_splitter = eq[retriever_type](chunk_size=chunk_size, chunk_overlap=overlap)
    splits = text_splitter.split_documents(docs)
    with open("book_no_index.txt", "r", encoding="utf-8") as f:
        book = str(f.read())
    for split in splits:
        index1 = book.find(split.page_content)
        index2 = index1 + len(split.page_content)
        split.metadata["start_index"] = index1
        split.metadata["end_index"] = index2
    vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings(model="text-embedding-3-large"),collection_name = f"analytics_edge_textbook_{title}")
    return vectorstore


HyDE_prompt3 = """
You are given a student's question.
Your task is to rephrase the question into a set of paragraph titles form an analytics textbook that would contain the answer to the question. Use the following rules:
1. Use appropriate vocabulary. A title should be a short and descriptive sentence.
2. Use a single title. Only if the student is asking multiple things, write one title for each.
3. Use the minimum number of titles possible to cover the student's question. Stay as close as possible to the original question.

You will output a JSON file and nothing else. Your output should follow the format:
``
{{
    "chapters": ["concept1",...]
}}

student's question: {question}
"""
HyDE_prompt_template = PromptTemplate(
    input_variables=["question"],
    template=HyDE_prompt3
)



def create_retriever(vectorstore,k=None,search_type='similarity',llm='gpt',prompt_type='base'):
    eq_llm = {"gpt":ChatOpenAI(temperature=0, model="gpt-4o-mini",  model_kwargs={ "response_format": { "type": "json_object" } }),
              "claude":ChatAnthropic(temperature=0, model="claude-3-5-haiku-20241022")}
    eq_type = {"base":None,"chapter":HyDE_prompt3,"concept":HyDE_prompt,"question":HyDE_prompt2}
    eq_json_field_name = {"base":None,"chapter":"chapters","concept":"concepts","question":"q"}

    asker_llm = eq_llm[llm]
    selected_prompt_type = eq_type[prompt_type]
    HyDE_prompt_template = field_name = None
    if selected_prompt_type:
        HyDE_prompt_template = PromptTemplate(
            input_variables=["question"],
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
        docs = []
        contents = []
        for question in questions_dict[field_name]: # HERE to change if we don't use chapters
            #print(question)
            retrieved = retriever.invoke(question)
            #print(retrieved)
            for doc in retrieved:
                content = doc.page_content
                if content not in contents:
                    docs.append(doc)
                    contents.append(content)
        return docs
    

    input_data = RunnablePassthrough()
    parser = JsonOutputParser()
    HyDE_retriever_chain = (
        {'question': input_data} | HyDE_prompt_template | asker_llm | parser | my_retriever
    )
    return HyDE_retriever_chain





class RAG_AGENT():
    def __init__(self, filepath):
        self.rag