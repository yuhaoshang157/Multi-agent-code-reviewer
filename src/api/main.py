"""FastAPI gateway: expose multi-agent code review as an HTTP service."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.tools.review_runner import review_pr

app = FastAPI(
    title="Multi-Agent Code Reviewer",
    description="LangGraph + RAG powered code review service",
    version="0.1.0",
)


class ReviewRequest(BaseModel):
    repo: str
    pr_number: int


class ReviewResponse(BaseModel):
    repo: str
    pr_number: int
    title: str
    changed_files: list[str]
    review_score: int
    issues_count: int
    report: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/review", response_model=ReviewResponse)
def review(request: ReviewRequest):
    try:
        result = review_pr(request.repo, request.pr_number)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
