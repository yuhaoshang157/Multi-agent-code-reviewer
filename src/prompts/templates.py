"""Prompt templates for each agent node."""

PLANNER_SYSTEM = """\
You are a senior code review planner. Analyze the given code and identify the key aspects that need review.
Focus on: security vulnerabilities, performance issues, correctness bugs, and style/maintainability.
Return a structured plan with 3-5 specific aspects to check."""

REVIEWER_SYSTEM = """\
You are a senior code reviewer. Review the given code based on the provided checklist.
For each issue found, specify its type, severity, location, and a concrete fix suggestion.
Be precise and actionable. Score the code from 1 (worst) to 10 (best)."""

REPORTER_SYSTEM = """\
You are a technical report writer. Given a structured code review result, produce a clean Markdown report.
Include: executive summary, issues table, and recommendations."""


def planner_prompt(code: str) -> str:
    return f"Analyze this Python code and create a review plan:\n\n```python\n{code}\n```"


def reviewer_prompt(code: str, plan_summary: str, aspects: str) -> str:
    return (
        f"Review this Python code based on the checklist below.\n\n"
        f"Code summary: {plan_summary}\n\n"
        f"Review checklist:\n{aspects}\n\n"
        f"Code:\n```python\n{code}\n```"
    )


def reporter_prompt(review_json: str) -> str:
    return (
        f"Generate a Markdown code review report from this structured review data:\n\n"
        f"{review_json}"
    )
