"""Run multi-agent review on a real GitHub PR and save results."""

import json
import logging
from pathlib import Path

from src.tools.github_fetcher import fetch_pr
from src.agents.multi_agent import graph
from src.tools.rag_store import COLLECTION as DEFAULT_COLLECTION
from src.tools.token_tracker import TokenUsageCallback

log = logging.getLogger(__name__)

_REVIEWS_DIR = Path(__file__).parent.parent.parent / "outputs" / "reviews"


def review_pr(repo_name: str, pr_number: int, model: str = "claude") -> dict:
    """Fetch PR, run multi-agent review, save report to outputs/reviews/."""
    log.info("Fetching PR #%d from %s...", pr_number, repo_name)
    pr = fetch_pr(repo_name, pr_number)
    log.info("Title: %s | Files: %s", pr.title, len(pr.changed_files))

    log.info("Running multi-agent review pipeline...")
    tracker = TokenUsageCallback()
    result = graph.invoke(
        {"code": pr.diff, "plan": None, "review": None, "report": "",
         "use_rag": True, "rag_collection": DEFAULT_COLLECTION, "model": model},
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

    log.info("Score: %d/10 | Issues: %d | saved to %s",
             output["review_score"], output["issues_count"], out_path)
    return output


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    review_pr("psf/requests", 6710)
