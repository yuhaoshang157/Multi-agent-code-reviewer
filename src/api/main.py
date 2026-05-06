"""FastAPI gateway: expose multi-agent code review as an HTTP service."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from src.tools.review_runner import review_pr

app = FastAPI(
    title="Multi-Agent Code Reviewer",
    description="LangGraph + RAG powered code review service",
    version="0.1.0",
)


class ReviewRequest(BaseModel):
    repo: str
    pr_number: int

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        parts = v.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("repo 格式应为 'owner/name'，例如 'psf/requests'")
        return v

    @field_validator("pr_number")
    @classmethod
    def validate_pr_number(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("pr_number 必须为正整数")
        return v


class ReviewResponse(BaseModel):
    repo: str
    pr_number: int
    title: str
    changed_files: list[str]
    review_score: int
    issues_count: int
    report: str
    token_usage: dict


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
