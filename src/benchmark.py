"""
Benchmark: run multi-agent review on merged PRs from diverse Python repos.
Fetches recent merged PRs automatically via GitHub API, reviews each, saves summary.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Target repos covering different Python domains
REPOS = [
    "psf/requests",            # HTTP client
    "pallets/flask",           # web framework
    "encode/httpx",            # async HTTP client
    "pytest-dev/pytest",       # test framework
    "scikit-learn/scikit-learn",  # machine learning
    "huggingface/transformers",   # LLM / NLP
]

PRS_PER_REPO = 4   # fetch 4 merged PRs per repo → ~24 total
OUTPUT_DIR = Path("outputs/benchmark")


def fetch_merged_prs(repo_name: str, n: int) -> list[dict]:
    """Return the n most recent merged PRs that touch Python files."""
    token = os.environ.get("GITHUB_TOKEN")
    g = Github(auth=Auth.Token(token) if token else None)
    repo = g.get_repo(repo_name)

    results = []
    for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
        if len(results) >= n:
            break
        if not pr.merged:
            continue
        files = [f.filename for f in pr.get_files()]
        if not any(f.endswith(".py") for f in files):
            continue
        results.append({"repo": repo_name, "pr_number": pr.number, "title": pr.title})

    return results


def run_review(repo: str, pr_number: int) -> dict | None:
    """Call the FastAPI /review endpoint and return the result."""
    try:
        resp = requests.post(
            "http://localhost:8000/review",
            json={"repo": repo, "pr_number": pr_number},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        log.error("HTTP %d: %s", e.response.status_code, e.response.text[:200])
        return None
    except Exception as e:
        log.error("Request failed: %s", e)
        return None


def load_existing_results() -> tuple[list[dict], Path | None]:
    """Load the most recent benchmark file if it exists, for resume support."""
    if not OUTPUT_DIR.exists():
        return [], None
    files = sorted(OUTPUT_DIR.glob("benchmark_*.json"))
    if not files:
        return [], None
    latest = files[-1]
    with open(latest, encoding="utf-8") as f:
        return json.load(f), latest


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"benchmark_{timestamp}.json"

    results, existing_file = load_existing_results()
    done = {(r["repo"], r["pr_number"]) for r in results}
    if done:
        log.info("Resuming from %s, %d PRs already done.", existing_file.name, len(done))

    log.info("=== Benchmark started: %s ===", timestamp)

    for repo in REPOS:
        log.info("[%s] Fetching merged PRs...", repo)
        try:
            prs = fetch_merged_prs(repo, PRS_PER_REPO)
        except Exception as e:
            log.error("Failed to fetch PRs for %s: %s", repo, e)
            continue

        log.info("  Found %d PRs to review", len(prs))

        for pr in prs:
            pr_num = pr["pr_number"]
            if (repo, pr_num) in done:
                log.info("  Skipping PR #%d (already done)", pr_num)
                continue
            log.info("  Reviewing PR #%d: %s...", pr_num, pr["title"][:60])
            start = time.time()
            result = run_review(repo, pr_num)
            elapsed = round(time.time() - start, 1)

            if result:
                entry = {
                    "repo": repo,
                    "pr_number": pr_num,
                    "title": pr["title"],
                    "score": result["review_score"],
                    "issues_count": result["issues_count"],
                    "changed_files": result["changed_files"],
                    "elapsed_seconds": elapsed,
                    "token_usage": result.get("token_usage", {}),
                }
                results.append(entry)
                done.add((repo, pr_num))
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                cost = result.get("token_usage", {}).get("estimated_cost_usd", 0)
                log.info("    Score: %d/10 | Issues: %d | %.1fs | $%.4f",
                         result["review_score"], result["issues_count"], elapsed, cost)
            else:
                log.warning("    PR #%d skipped (error)", pr_num)

            time.sleep(2)   # avoid rate limiting

    log.info("\n=== Summary (%d PRs reviewed) ===", len(results))
    if results:
        scores = [r["score"] for r in results]
        log.info("Score range  : %d - %d", min(scores), max(scores))
        log.info("Average score: %.1f/10", sum(scores) / len(scores))

        total_tokens = sum(r.get("token_usage", {}).get("total_tokens", 0) for r in results)
        total_cost = sum(r.get("token_usage", {}).get("estimated_cost_usd", 0) for r in results)
        log.info("Total tokens : %d", total_tokens)
        log.info("Total cost   : $%.4f USD", total_cost)
        log.info("Cost per PR  : $%.4f USD", total_cost / len(results))

        by_repo: dict[str, list] = {}
        for r in results:
            by_repo.setdefault(r["repo"], []).append(r["score"])
        for r_name, sc in by_repo.items():
            log.info("  %s: avg %.1f (%d PRs)", r_name, sum(sc) / len(sc), len(sc))

    log.info("Full results saved to: %s", out_file)


if __name__ == "__main__":
    main()
