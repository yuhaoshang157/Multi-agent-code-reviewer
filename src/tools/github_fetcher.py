"""Fetch PR diff from GitHub using PyGithub."""
import os
from dataclasses import dataclass
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()


@dataclass
class PRData:
    repo: str
    pr_number: int
    title: str
    diff: str           # raw unified diff text
    changed_files: list[str]


def fetch_pr(repo_name: str, pr_number: int) -> PRData:
    """Fetch PR metadata and diff from GitHub.

    Args:
        repo_name: e.g. "psf/requests"
        pr_number: PR number integer
    """
    token = os.environ.get("GITHUB_TOKEN")
    g = Github(auth=Auth.Token(token) if token else None)

    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # collect diff per file (skip binary files)
    diff_parts = []
    changed_files = []
    for f in pr.get_files():
        changed_files.append(f.filename)
        if f.patch:  # binary files have no patch
            diff_parts.append(f"### {f.filename}\n```diff\n{f.patch}\n```")

    return PRData(
        repo=repo_name,
        pr_number=pr_number,
        title=pr.title,
        diff="\n\n".join(diff_parts),
        changed_files=changed_files,
    )


if __name__ == "__main__":
    # test with a small real PR from requests library
    pr = fetch_pr("psf/requests", 6710)
    print(f"Title: {pr.title}")
    print(f"Files changed: {pr.changed_files}")
    print(f"\nDiff preview (first 500 chars):\n{pr.diff[:500]}")
