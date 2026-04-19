"""Demo 4: LangGraph basics — StateGraph with 2 nodes (Planner → Reviewer)"""
import os
from typing import Annotated
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

load_dotenv()

llm = ChatOpenAI(
    model="anthropic/claude-sonnet-4-5",
    openai_api_key=os.environ["ANTHROPIC_API_KEY"],
    openai_api_base="https://openrouter.ai/api/v1",
)

# State: messages list, append-only via add_messages reducer
class State(TypedDict):
    messages: Annotated[list, add_messages]
    code: str

# Node 1: Planner — decides what aspects to review
def planner(state: State) -> dict:
    response = llm.invoke([
        HumanMessage(content=(
            f"You are a code review planner. Given this Python code, list 3 specific aspects to check:\n\n"
            f"```python\n{state['code']}\n```\n\n"
            "Reply in 3 bullet points only."
        ))
    ])
    return {"messages": [response]}

# Node 2: Reviewer — performs the actual review based on planner output
def reviewer(state: State) -> dict:
    plan = state["messages"][-1].content
    response = llm.invoke([
        HumanMessage(content=(
            f"You are a code reviewer. Review this Python code based on the following checklist:\n\n"
            f"Checklist:\n{plan}\n\n"
            f"Code:\n```python\n{state['code']}\n```\n\n"
            "Give a concise review (3-5 sentences)."
        ))
    ])
    return {"messages": [response]}

# Build graph: START → planner → reviewer → END
builder = StateGraph(State)
builder.add_node("planner", planner)
builder.add_node("reviewer", reviewer)
builder.add_edge(START, "planner")
builder.add_edge("planner", "reviewer")
builder.add_edge("reviewer", END)

graph = builder.compile()

# Test code with obvious issues
test_code = """
def get_user(users, id):
    for i in range(len(users)):
        if users[i]['id'] == id:
            return users[i]
    password = "admin123"
    return None
"""

print("=== LangGraph 2-Node Pipeline ===\n")
result = graph.invoke({"messages": [], "code": test_code})

print("[Planner Output]")
print(result["messages"][0].content)
print("\n[Reviewer Output]")
print(result["messages"][1].content)
