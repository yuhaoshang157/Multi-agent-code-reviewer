"""Tests for multi-agent review pipeline."""

import pytest
from src.schemas.review import ReviewAspect, PlannerOutput, ReviewIssue, ReviewResult
from src.prompts.templates import planner_prompt, reviewer_prompt, reporter_prompt


# ── Schema tests (no API calls) ──────────────────────────────────────────────


def test_planner_output_schema():
    plan = PlannerOutput(
        aspects=[
            ReviewAspect(category="security", description="check for hardcoded secrets")
        ],
        summary="A simple user lookup function",
    )
    assert len(plan.aspects) == 1
    assert plan.aspects[0].category == "security"


def test_review_result_schema():
    result = ReviewResult(
        issues=[
            ReviewIssue(
                issue_type="security",
                severity="critical",
                location="line 6",
                description="Hardcoded password",
                suggestion="Use env var",
            )
        ],
        overall_score=3,
        summary="Critical security issue found.",
    )
    assert result.overall_score == 3
    assert result.issues[0].severity == "critical"


def test_review_result_empty_issues():
    result = ReviewResult(issues=[], overall_score=9, summary="Clean code.")
    assert result.issues == []


# ── Prompt tests (no API calls) ───────────────────────────────────────────────


def test_planner_prompt_contains_code():
    code = "def foo(): pass"
    prompt = planner_prompt(code)
    assert code in prompt
    assert "```python" in prompt


def test_reviewer_prompt_contains_all_parts():
    prompt = reviewer_prompt("def foo(): pass", "simple function", "- check security")
    assert "def foo(): pass" in prompt
    assert "simple function" in prompt
    assert "check security" in prompt


def test_reporter_prompt_contains_json():
    json_str = '{"issues": [], "overall_score": 9}'
    prompt = reporter_prompt(json_str)
    assert json_str in prompt


# ── Pipeline integration test (live API) ─────────────────────────────────────


@pytest.mark.integration
def test_pipeline_runs_end_to_end():
    """Requires ANTHROPIC_API_KEY. Run with: pytest -m integration"""
    from src.agents.multi_agent import graph

    code = "def add(a, b):\n    return a + b\n"
    result = graph.invoke({"code": code, "plan": None, "review": None, "report": ""})

    assert result["plan"] is not None
    assert result["review"] is not None
    assert isinstance(result["review"].overall_score, int)
    assert result["report"] != ""
