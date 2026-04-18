"""Demo 3: Structured output with Pydantic v2 schema"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

load_dotenv()

class CodeIssue(BaseModel):
    issue_type: str = Field(description="Category: bug / style / performance / security")
    severity: str = Field(description="Level: low / medium / high")
    line_hint: str = Field(description="Brief description of the problematic line")
    suggestion: str = Field(description="How to fix it")

class ReviewResult(BaseModel):
    issues: list[CodeIssue] = Field(description="List of issues found")
    overall_score: int = Field(description="Code quality score 1-10 (1=worst, 10=best)")
    summary: str = Field(description="One-sentence overall assessment")

llm = ChatOpenAI(
    model="anthropic/claude-sonnet-4-5",
    openai_api_key=os.environ["ANTHROPIC_API_KEY"],
    openai_api_base="https://openrouter.ai/api/v1",
)

structured_llm = llm.with_structured_output(ReviewResult)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert Python code reviewer. Analyze the code and return structured feedback."),
    ("user", "Review this code:\n\n{code}"),
])

chain = prompt | structured_llm

test_code = """
import pickle

def load_user_data(filepath):
    with open(filepath, 'rb') as f:
        return pickle.load(f)  # loads untrusted data

def get_user(users, id):
    for i in range(len(users)):
        if users[i]['id'] == id:
            return users[i]
"""

result: ReviewResult = chain.invoke({"code": test_code})

print("=== Structured Review ===")
print(f"Overall Score: {result.overall_score}/10")
print(f"Summary: {result.summary}")
print(f"\nIssues found: {len(result.issues)}")
for i, issue in enumerate(result.issues, 1):
    print(f"\n[{i}] {issue.issue_type.upper()} ({issue.severity})")
    print(f"    Where: {issue.line_hint}")
    print(f"    Fix:   {issue.suggestion}")
