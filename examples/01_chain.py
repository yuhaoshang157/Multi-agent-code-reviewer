"""Demo 1: Simple LLM chain — Prompt → LLM → OutputParser"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

llm = ChatOpenAI(
    model="anthropic/claude-sonnet-4-5",
    openai_api_key=os.environ["ANTHROPIC_API_KEY"],
    openai_api_base="https://openrouter.ai/api/v1",
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a concise code reviewer. Identify the main issue in the code.",
        ),
        ("user", "{code}"),
    ]
)

chain = prompt | llm | StrOutputParser()

code_sample = """
def divide(a, b):
    return a / b

result = divide(10, 0)
print(result)
"""

result = chain.invoke({"code": code_sample})
print("=== Chain Output ===")
print(result)
