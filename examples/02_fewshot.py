"""Demo 2: Few-shot prompt template"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import FewShotChatMessagePromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

llm = ChatOpenAI(
    model="anthropic/claude-sonnet-4-5",
    openai_api_key=os.environ["ANTHROPIC_API_KEY"],
    openai_api_base="https://openrouter.ai/api/v1",
)

examples = [
    {
        "code": "x = 1\nif x == True:\n    print('yes')",
        "review": "Bug: comparing with `== True` is fragile; use `if x:` instead.",
    },
    {
        "code": "import os, sys, json, re, math",
        "review": "Style: import each module on a separate line (PEP 8).",
    },
]

example_prompt = ChatPromptTemplate.from_messages(
    [
        ("human", "Review this code:\n{code}"),
        ("ai", "{review}"),
    ]
)

few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=examples,
)

final_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a Python code reviewer. Give a one-sentence review."),
        few_shot_prompt,
        ("human", "Review this code:\n{code}"),
    ]
)

chain = final_prompt | llm | StrOutputParser()

test_code = """
passwords = []
for i in range(0, len(passwords)):
    print(passwords[i])
"""

result = chain.invoke({"code": test_code})
print("=== Few-shot Review ===")
print(result)
