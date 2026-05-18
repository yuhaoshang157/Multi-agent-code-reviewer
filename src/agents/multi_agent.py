"""Multi-agent code review pipeline: Planner → Reviewer → Reporter."""

import ast
import logging
import os
import json
from typing import Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv

log = logging.getLogger(__name__)
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from src.schemas.review import PlannerOutput, ReviewAspect, ReviewResult, ReviewIssue
from src.prompts.templates import (
    PLANNER_SYSTEM,
    REVIEWER_SYSTEM,
    REPORTER_SYSTEM,
    planner_prompt,
    reviewer_prompt,
    reporter_prompt,
)
from src.tools.code_chunker import chunk_python_code, chunk_diff
from src.tools.rag_store import query_similar_bugs, COLLECTION as DEFAULT_COLLECTION  # re-exported for tests

load_dotenv()

# ---------------------------------------------------------------------------
# LLM registry -pre-instantiate all supported models at module load time.
# Nodes select from this registry at runtime via state["model"].
# ---------------------------------------------------------------------------
_LLM_REGISTRY: dict[str, ChatOpenAI] = {
    "claude": ChatOpenAI(
        model="anthropic/claude-sonnet-4.6",
        openai_api_key=os.environ["ANTHROPIC_API_KEY"],
        openai_api_base="https://openrouter.ai/api/v1",
        max_retries=3,
        request_timeout=60,
    ),
    "deepseek-pro": ChatOpenAI(
        model=os.environ.get("DEEPSEEK_V4_Pro_MODEL", "deepseek-v4-pro"),
        openai_api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
        openai_api_base="https://api.deepseek.com",
        max_retries=3,
        request_timeout=60,
        extra_body={"thinking": {"type": "disabled"}},
    ),
    "deepseek-flash": ChatOpenAI(
        model=os.environ.get("DEEPSEEK_V4_Flash_MODEL", "deepseek-v4-flash"),
        openai_api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
        openai_api_base="https://api.deepseek.com",
        max_retries=3,
        request_timeout=60,
        extra_body={"thinking": {"type": "disabled"}},
    ),
}

MAX_RAG_RESULTS = 5  # cap total RAG hits injected into prompt to control token cost


def _get_llm(state: "ReviewState") -> ChatOpenAI:
    """Return the base LLM for the current run, falling back to claude."""
    return _LLM_REGISTRY.get(state.get("model", "deepseek-pro"), _LLM_REGISTRY["deepseek-pro"])


class ReviewState(TypedDict):
    code: str
    plan: Optional[PlannerOutput]
    review: Optional[ReviewResult]
    report: str
    use_rag: bool        # set False to skip RAG retrieval (used in ablation experiments)
    rag_collection: str  # Milvus collection name; supports exp2/exp3 multi-collection runs
    rag_context: str     # pre-fetched by rag_prefetch_node, consumed by reviewer_node
    model: str           # LLM provider: "claude" | "deepseek-pro" | "deepseek-flash"
    skip_reporter: bool  # set True to stop after Reviewer (eval mode: Reporter output unused)


def _lenient_parse_planner(exc: OutputParserException) -> PlannerOutput:
    """Build PlannerOutput from a failed structured-output attempt (missing fields get defaults)."""
    try:
        raw = getattr(exc, "llm_output", None) or "{}"
        data = ast.literal_eval(raw) if isinstance(raw, str) else {}
    except Exception:
        data = {}

    aspects = [
        ReviewAspect(
            category=str(item.get("category") or "general"),
            description=str(item.get("description") or ""),
        )
        for item in data.get("aspects", [])
    ]
    return PlannerOutput(
        aspects=aspects,
        summary=str(data.get("summary") or ""),
    )


def planner_node(state: ReviewState) -> dict:
    log.info("[Planner] Analyzing code structure...")
    llm = _get_llm(state)
    try:
        result = llm.with_structured_output(PlannerOutput, method="json_mode").invoke(
            [
                SystemMessage(content=PLANNER_SYSTEM),
                HumanMessage(content=planner_prompt(state["code"])),
            ]
        )
    except OutputParserException as e:
        log.warning("[Planner] Structured parse failed (%s), applying lenient fallback...", e.__class__.__name__)
        result = _lenient_parse_planner(e)
    log.info("[Planner] Done - %d review aspects identified", len(result.aspects))
    return {"plan": result}


def _lenient_parse_review(exc: OutputParserException) -> ReviewResult:
    """Build ReviewResult from a failed structured-output attempt.

    When json_mode produces valid JSON but with a missing/misplaced field,
    LangChain parses the JSON successfully then fails at Pydantic validation.
    The parsed dict is stored in exc.llm_output as repr(dict); we recover it
    here and fill in any missing fields with safe defaults.
    """
    try:
        raw = getattr(exc, "llm_output", None) or "{}"
        data = ast.literal_eval(raw) if isinstance(raw, str) else {}
    except Exception:
        data = {}

    issues: list[ReviewIssue] = []
    for item in data.get("issues", []):
        suggestion = (
            item.get("suggestion")
            or item.get("建议")
            or item.get("修复建议")
            or item.get("fix")
            or ""
        )
        issues.append(ReviewIssue(
            issue_type=str(item.get("issue_type") or "unknown"),
            severity=str(item.get("severity") or "medium"),
            location=str(item.get("location") or ""),
            description=str(item.get("description") or ""),
            suggestion=str(suggestion),
        ))

    return ReviewResult(
        issues=issues,
        overall_score=int(data.get("overall_score") or 5),
        summary=str(data.get("summary") or "[Recovered from parse error]"),
    )


def rag_prefetch_node(state: ReviewState) -> dict:
    """Runs in parallel with planner_node. Fetches RAG context so reviewer_node
    can start immediately once both planner and this node complete (fan-in)."""
    if not state.get("use_rag", True):
        log.info("[RAG] Disabled, skipping Milvus query")
        return {"rag_context": ""}

    log.info("[RAG] Querying Milvus...")
    rag_lines: list[str] = []
    seen_reviews: set[str] = set()
    collection = state.get("rag_collection", DEFAULT_COLLECTION)
    for chunk in (chunk_diff(state["code"]) or chunk_python_code(state["code"])):
        if len(rag_lines) >= MAX_RAG_RESULTS:
            break
        for hit in query_similar_bugs(chunk["code"], top_k=2, collection=collection):
            if len(rag_lines) >= MAX_RAG_RESULTS:
                break
            dedup_key = f"{hit['source']}:{hit['review'][:200]}"
            if dedup_key not in seen_reviews:
                seen_reviews.add(dedup_key)
                rag_lines.append(
                    f"- [{hit['similarity']}] [{hit['source']}/{hit['language']}] {hit['review']}"
                )
    log.info("[RAG] Done - %d hits fetched", len(rag_lines))
    return {"rag_context": "\n".join(rag_lines)}


def reviewer_node(state: ReviewState) -> dict:
    log.info("[Reviewer] Starting code review...")
    plan: PlannerOutput = state["plan"]
    aspects_text = "\n".join(f"- [{a.category}] {a.description}" for a in plan.aspects)
    rag_context = state.get("rag_context", "")

    log.info("[Reviewer] Calling LLM for review result...")
    llm = _get_llm(state)
    messages = [
        SystemMessage(content=REVIEWER_SYSTEM),
        HumanMessage(content=reviewer_prompt(state["code"], plan.summary, aspects_text, rag_context)),
    ]
    try:
        result = llm.with_structured_output(ReviewResult, method="json_mode").invoke(messages)
    except OutputParserException as e:
        log.warning("[Reviewer] Structured parse failed (%s), applying lenient fallback...", e.__class__.__name__)
        result = _lenient_parse_review(e)
    log.info("[Reviewer] Done - score %d/10, %d issues found", result.overall_score, len(result.issues))
    return {"review": result}


def reporter_node(state: ReviewState) -> dict:
    log.info("[Reporter] Generating Markdown report...")
    review: ReviewResult = state["review"]
    review_json = json.dumps(review.model_dump(), indent=2)
    llm = _get_llm(state)
    response = llm.invoke(
        [
            SystemMessage(content=REPORTER_SYSTEM),
            HumanMessage(content=reporter_prompt(review_json)),
        ]
    )
    log.info("[Reporter] Done")
    return {"report": response.content}


def _route_after_reviewer(state: ReviewState) -> str:
    """Skip Reporter when skip_reporter=True (eval mode: Reporter output unused in BERTScore)."""
    return END if state.get("skip_reporter", False) else "reporter"


# Build graph — fan-out: planner and rag_prefetch run in parallel from START,
# reviewer waits for both to complete (fan-in) before executing.
builder = StateGraph(ReviewState)
builder.add_node("planner", planner_node)
builder.add_node("rag_prefetch", rag_prefetch_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("reporter", reporter_node)
builder.add_edge(START, "planner")
builder.add_edge(START, "rag_prefetch")
builder.add_edge("planner", "reviewer")
builder.add_edge("rag_prefetch", "reviewer")
builder.add_conditional_edges("reviewer", _route_after_reviewer, {"reporter": "reporter", END: END})
builder.add_edge("reporter", END)

graph = builder.compile()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

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
        {"code": test_code, "plan": None, "review": None, "report": "",
         "use_rag": False, "rag_context": "", "rag_collection": DEFAULT_COLLECTION,
         "model": "deepseek-flash", "skip_reporter": False}
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
