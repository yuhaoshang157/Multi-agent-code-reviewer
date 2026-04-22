"""Pydantic schemas for multi-agent code review pipeline."""

from pydantic import BaseModel


class ReviewAspect(BaseModel):
    category: str  # e.g. security / performance / correctness / style
    description: str  # what to look for


class PlannerOutput(BaseModel):
    aspects: list[ReviewAspect]
    summary: str  # one-line description of the code


class ReviewIssue(BaseModel):
    issue_type: str  # security / performance / correctness / style
    severity: str  # critical / high / medium / low
    location: str  # e.g. "line 5" or "function get_user"
    description: str
    suggestion: str


class ReviewResult(BaseModel):
    issues: list[ReviewIssue]
    overall_score: int  # 1-10
    summary: str
