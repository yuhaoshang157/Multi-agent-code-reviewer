"""Run multi-agent review on a real GitHub PR and save results."""

import json
import os
from src.tools.github_fetcher import fetch_pr
from src.agents.multi_agent import graph


def review_pr(repo_name: str, pr_number: int) -> str:
    """Fetch PR, run multi-agent review, save report to outputs/reviews/."""
    print(f"Fetching PR #{pr_number} from {repo_name}...")
    pr = fetch_pr(repo_name, pr_number)
    print(f"Title: {pr.title}")
    print(f"Files: {pr.changed_files}\n")

    print("Running multi-agent review pipeline...")
    result = graph.invoke(
        {
            "code": pr.diff,
            "plan": None,
            "review": None,
            "report": "",
        }
    )

    # build output
    output = {
        "repo": repo_name,
        "pr_number": pr_number,
        "title": pr.title,
        "changed_files": pr.changed_files,
        "review_score": result["review"].overall_score,
        "issues_count": len(result["review"].issues),
        "report": result["report"],
    }

    # save to outputs/reviews/
    os.makedirs("outputs/reviews", exist_ok=True)
    filename = f"outputs/reviews/{repo_name.replace('/', '_')}_pr{pr_number}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Score: {output['review_score']}/10 | Issues: {output['issues_count']}")
    print(f"Report saved to: {filename}")
    return filename


if __name__ == "__main__":
    review_pr("psf/requests", 6710)
