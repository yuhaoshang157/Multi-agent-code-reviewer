"""
Benchmark: run multi-agent review on merged PRs from diverse Python repos.
Fetches recent merged PRs automatically via GitHub API, reviews each, saves summary.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

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
MAX_DIFF_CHARS = 8000   # skip PRs with very large diffs (too slow / expensive)
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
        # only PRs that touch .py files
        files = [f.filename for f in pr.get_files()]
        if not any(f.endswith(".py") for f in files):
            continue
        results.append({"repo": repo_name, "pr_number": pr.number, "title": pr.title})

    return results


def run_review(repo: str, pr_number: int) -> dict | None:
    """Call the FastAPI /review endpoint and return the result."""
    import urllib.request
    import urllib.error

    payload = json.dumps({"repo": repo, "pr_number": pr_number}).encode()
    req = urllib.request.Request(
        "http://localhost:8000/review",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  [ERROR] HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"  [ERROR] {e}")
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

    # resume: load existing results and skip already-processed PRs
    results, existing_file = load_existing_results()
    done = {(r["repo"], r["pr_number"]) for r in results}
    if done:
        print(f"Resuming from {existing_file.name}, {len(done)} PRs already done.\n")

    print(f"=== Benchmark started: {timestamp} ===\n")

    for repo in REPOS:
        print(f"[{repo}] Fetching merged PRs...")
        try:
            prs = fetch_merged_prs(repo, PRS_PER_REPO)
        except Exception as e:
            print(f"  [ERROR] Failed to fetch PRs: {e}")
            continue

        print(f"  Found {len(prs)} PRs to review")

        for pr in prs:
            pr_num = pr["pr_number"]
            if (repo, pr_num) in done:
                print(f"  Skipping PR #{pr_num} (already done)")
                continue
            print(f"  Reviewing PR #{pr_num}: {pr['title'][:60]}...")
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
                # write immediately so progress is not lost on crash
                out_file = OUTPUT_DIR / f"benchmark_{timestamp}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                cost = result.get("token_usage", {}).get("estimated_cost_usd", 0)
                print(f"    Score: {result['review_score']}/10 | Issues: {result['issues_count']} | {elapsed}s | ${cost:.4f}")
            else:
                print(f"    Skipped (error)")

            time.sleep(2)   # avoid rate limiting

    # print summary
    print(f"\n=== Summary ({len(results)} PRs reviewed) ===")
    if results:
        scores = [r["score"] for r in results]
        print(f"Score range  : {min(scores)} - {max(scores)}")
        print(f"Average score: {sum(scores)/len(scores):.1f}/10")

        total_tokens = sum(r.get("token_usage", {}).get("total_tokens", 0) for r in results)
        total_cost = sum(r.get("token_usage", {}).get("estimated_cost_usd", 0) for r in results)
        print(f"Total tokens : {total_tokens:,}")
        print(f"Total cost   : ${total_cost:.4f} USD")
        print(f"Cost per PR  : ${total_cost/len(results):.4f} USD")

        by_repo = {}
        for r in results:
            by_repo.setdefault(r["repo"], []).append(r["score"])
        for repo, sc in by_repo.items():
            print(f"  {repo}: avg {sum(sc)/len(sc):.1f} ({len(sc)} PRs)")

    print(f"\nFull results saved to: {out_file}")


if __name__ == "__main__":
    main()
