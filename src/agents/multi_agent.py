"""Multi-agent code review pipeline: Planner → Reviewer → Reporter."""

import os
import json
from typing import Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from src.schemas.review import PlannerOutput, ReviewResult
from src.prompts.templates import (
    PLANNER_SYSTEM,
    REVIEWER_SYSTEM,
    REPORTER_SYSTEM,
    planner_prompt,
    reviewer_prompt,
    reporter_prompt,
)
from src.tools.code_chunker import chunk_python_code
from src.tools.rag_store import query_similar_bugs

load_dotenv()

llm = ChatOpenAI(
    model="anthropic/claude-sonnet-4.6",
    openai_api_key=os.environ["ANTHROPIC_API_KEY"],
    openai_api_base="https://openrouter.ai/api/v1",
    max_retries=3,  # retry on transient API errors (rate limit / 5xx)
    request_timeout=60,
)

planner_llm = llm.with_structured_output(PlannerOutput)
reviewer_llm = llm.with_structured_output(ReviewResult)


class ReviewState(TypedDict):
    code: str
    plan: Optional[PlannerOutput]
    review: Optional[ReviewResult]
    report: str


def planner_node(state: ReviewState) -> dict:
    result = planner_llm.invoke(
        [
            SystemMessage(content=PLANNER_SYSTEM),
            HumanMessage(content=planner_prompt(state["code"])),
        ]
    )
    return {"plan": result}


def reviewer_node(state: ReviewState) -> dict:
    plan: PlannerOutput = state["plan"]
    aspects_text = "\n".join(f"- [{a.category}] {a.description}" for a in plan.aspects)

    # RAG: chunk code, query each chunk, deduplicate hits
    rag_lines = []
    seen_labels = set()
    for chunk in chunk_python_code(state["code"]):
        for hit in query_similar_bugs(chunk["code"], top_k=2):
            key = hit["label"] + hit["comment"]
            if key not in seen_labels:
                seen_labels.add(key)
                rag_lines.append(f"- [{hit['similarity']}] {hit['label']}: {hit['comment']}")
    rag_context = "\n".join(rag_lines)

    result = reviewer_llm.invoke(
        [
            SystemMessage(content=REVIEWER_SYSTEM),
            HumanMessage(
                content=reviewer_prompt(state["code"], plan.summary, aspects_text, rag_context)
            ),
        ]
    )
    return {"review": result}


def reporter_node(state: ReviewState) -> dict:
    review: ReviewResult = state["review"]
    review_json = json.dumps(review.model_dump(), indent=2)
    response = llm.invoke(
        [
            SystemMessage(content=REPORTER_SYSTEM),
            HumanMessage(content=reporter_prompt(review_json)),
        ]
    )
    return {"report": response.content}


# Build graph
builder = StateGraph(ReviewState)
builder.add_node("planner", planner_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("reporter", reporter_node)
builder.add_edge(START, "planner")
builder.add_edge("planner", "reviewer")
builder.add_edge("reviewer", "reporter")
builder.add_edge("reporter", END)

graph = builder.compile()


if __name__ == "__main__":
    test_code = """
def get_user(users, id):
    for i in range(len(users)):
        if users[i]['id'] == id:
            return users[i]
    password = "admin123"
    return None

def process_data(data):
    result = []
    for item in data:
        result = result + [item * 2]  # O(n^2) due to list concatenation
    return result

def read_file(path):
    f = open(path)
    content = f.read()
    return content  # file never closed
"""

    print("=== Multi-Agent Code Review Pipeline ===\n")
    result = graph.invoke(
        {"code": test_code, "plan": None, "review": None, "report": ""}
    )

    print("[Planner Output]")
    for a in result["plan"].aspects:
        print(f"  [{a.category}] {a.description}")

    print(f"\n[Reviewer Output] Score: {result['review'].overall_score}/10")
    for issue in result["review"].issues:
        print(
            f"  [{issue.severity.upper()}] {issue.issue_type} @ {issue.location}: {issue.description}"
        )

    print("\n[Reporter Output]")
    print(result["report"])
