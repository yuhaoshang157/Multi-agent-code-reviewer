"""Run multi-agent review on a real GitHub PR and save results."""

import json
from pathlib import Path

from src.tools.github_fetcher import fetch_pr
from src.agents.multi_agent import graph
from src.tools.token_tracker import TokenUsageCallback

_REVIEWS_DIR = Path(__file__).parent.parent.parent / "outputs" / "reviews"


def review_pr(repo_name: str, pr_number: int) -> dict:
    """Fetch PR, run multi-agent review, save report to outputs/reviews/."""
    print(f"Fetching PR #{pr_number} from {repo_name}...")
    pr = fetch_pr(repo_name, pr_number)
    print(f"Title: {pr.title}")
    print(f"Files: {pr.changed_files}\n")

    print("Running multi-agent review pipeline...")
    tracker = TokenUsageCallback()
    result = graph.invoke(
        {"code": pr.diff, "plan": None, "review": None, "report": "", "use_rag": True},
        config={"callbacks": [tracker]},
    )

    output = {
        "repo": repo_name,
        "pr_number": pr_number,
        "title": pr.title,
        "changed_files": pr.changed_files,
        "review_score": result["review"].overall_score,
        "issues_count": len(result["review"].issues),
        "report": result["report"],
        "token_usage": tracker.summary(),
    }

    _REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _REVIEWS_DIR / f"{repo_name.replace('/', '_')}_pr{pr_number}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Score: {output['review_score']}/10 | Issues: {output['issues_count']}")
    print(f"Report saved to: {out_path}")
    return output


if __name__ == "__main__":
    review_pr("psf/requests", 6710)
