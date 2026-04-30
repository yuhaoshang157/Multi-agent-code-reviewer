#!/usr/bin/env python3
"""
Build evaluation set and RAG knowledge base from 6 code-review datasets.

Each dataset contributes N items to the eval set (default N=100).
Remaining items form the RAG knowledge base.

Datasets:
  1. Kaggle code-review-data-v2   local CSV, ~21K rows, multi-lang, RLHF reward
  2. SeRe                          GitHub ZIP, 6732 rows, security reviews, C/C++/Go/Java/Kotlin
  3. CRAVE                         HuggingFace, 1174 rows, multi-lang, PR approve/reject + explanation
  4. CodeReviewQA                  HuggingFace (gated), 900 rows, 9 languages × 100, ACL 2025
  5. Microsoft CodeReviewer        HuggingFace, up to 50K rows, multi-lang, train_refinement config
  6. SWE-bench Lite                HuggingFace, 300 Python issues + fix patches

Unified item schema:
  {
    "id":       "<source>_<split>_<idx>",
    "source":   dataset name,
    "code":     code diff / patch (capped at 8000 chars),
    "review":   review comment / bug description (capped at 2000 chars),
    "language": programming language (lowercase),
    "split":    "eval" | "rag",
    "metadata": {source-specific extra fields}
  }

Output files (under data/):
  eval_set.jsonl      -- N × 6 rows  (default 600 rows)
  rag_kb.jsonl        -- remaining rows for Milvus RAG ingestion
  dataset_stats.json  -- manifest: source, counts, language distribution

Usage:
  python src/data/build_dataset.py            # N=100 (default)
  python src/data/build_dataset.py --n 50     # N=50 per dataset
"""

from __future__ import annotations

import argparse
import io
import json
import os
import random
import time
import zipfile
from pathlib import Path

import re
import requests
from dotenv import load_dotenv

load_dotenv()

# Bridge non-standard env var names to the one HuggingFace Hub library reads
if not os.environ.get("HF_TOKEN"):
    for _alias in ("HUGGINGFACE_TOKEN_READ_ONLY", "HUGGINGFACE_TOKEN", "HF_TOKEN_READ_ONLY"):
        if os.environ.get(_alias):
            os.environ["HF_TOKEN"] = os.environ[_alias]
            break

DATA_DIR = Path("data")
RAW_DIR  = DATA_DIR / "raw"
SEED     = 42
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

MAX_CODE_CHARS   = 8_000
MAX_REVIEW_CHARS = 2_000


# ─── Unified item factory ─────────────────────────────────────────────────────

def make_item(source: str, code: str, review: str, language: str, **meta) -> dict:
    return {
        "id":       "",
        "source":   source,
        "code":     code[:MAX_CODE_CHARS],
        "review":   review[:MAX_REVIEW_CHARS],
        "language": (language or "unknown").lower().strip(),
        "split":    "",
        "metadata": {k: v for k, v in meta.items() if v is not None},
    }


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _gh_headers() -> dict:
    return {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def _raw_url(repo: str, branch: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"


def _get(url: str, *, timeout: int = 30) -> requests.Response:
    resp = requests.get(url, headers=_gh_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp


# ─── Language inference from diff ────────────────────────────────────────────

_EXT_TO_LANG: dict[str, str] = {
    "py": "python", "pyx": "python",
    "js": "javascript", "jsx": "javascript", "mjs": "javascript",
    "ts": "typescript", "tsx": "typescript",
    "java": "java",
    "go": "go", "gotmpl": "go",
    "rs": "rust",
    "cpp": "c++", "cc": "c++", "cxx": "c++", "hpp": "c++", "cuh": "c++",
    "c": "c", "h": "c",
    "cs": "c#",
    "rb": "ruby",
    "php": "php",
    "kt": "kotlin", "kts": "kotlin",
    "swift": "swift",
    "scala": "scala",
    "lua": "lua",
    "jl": "julia",
    "ex": "elixir", "exs": "elixir",
    "hs": "haskell",
    "sh": "shell", "bash": "shell",
    "r": "r",
    "cu": "cuda",
    "vue": "javascript",
    "svelte": "javascript",
    "v": "v",
    "sol": "solidity",
    "sql": "sql",
    "ipynb": "python",
}
# Extensions that carry no language signal
_SKIP_EXTS: set[str] = {
    "md", "mdx", "rst", "txt", "lock", "json", "toml", "yml", "yaml",
    "html", "css", "scss", "svg", "xml", "ini", "cfg", "gitignore",
    "gitkeep", "config", "gradle", "snap", "gz", "dic", "in", "out",
    "man", "nsi", "wxs", "vcxproj", "xaml", "ps1", "cmake", "nix",
    "docker", "dockerfile", "scm",
}


def _infer_lang_from_patch(patch: str) -> str:
    """Extract file extensions from 'diff --git a/...' headers, return dominant language."""
    exts = re.findall(r"diff --git a/[^\s]+\.(\w+)", patch)
    counts: dict[str, int] = {}
    for ext in exts:
        ext = ext.lower()
        if ext in _SKIP_EXTS:
            continue
        lang = _EXT_TO_LANG.get(ext, ext)
        counts[lang] = counts.get(lang, 0) + 1
    if not counts:
        return "unknown"
    return max(counts, key=lambda k: counts[k])


def _infer_lang_from_code_content(code: str) -> str:
    """
    Infer language from code syntax patterns when no file-header hints exist.
    Uses a scoring system: each matched pattern adds points; highest score wins.
    Designed for Kaggle patches that have no 'diff --git a/...' headers.
    """
    scores: dict[str, int] = {}

    def add(lang: str, pts: int) -> None:
        scores[lang] = scores.get(lang, 0) + pts

    # Go — distinctive: quoted imports, := walrus, func keyword
    if re.search(r'\bpackage\s+\w+', code):               add("go", 3)
    if re.search(r'\bfunc\s+\w*\s*\(', code):             add("go", 4)
    if re.search(r':=\s', code):                           add("go", 5)
    if re.search(r'import\s+"', code):                     add("go", 6)  # quoted string import
    if re.search(r'\berr\s*:=', code):                     add("go", 4)
    if re.search(r'\bgo\s+func\b', code):                  add("go", 6)
    if re.search(r'\bimport\s+\(', code):                  add("go", 5)  # block import

    # Python — distinctive: self., elif, dunder methods, from x import
    if re.search(r'\bdef\s+\w+\s*\(\s*self', code):       add("python", 7)
    if re.search(r'\belif\s+', code):                      add("python", 8)
    if re.search(r'\bself\.\w+', code):                    add("python", 4)
    if re.search(r'class\s+\w+\s*\(', code):              add("python", 4)  # class Foo(Bar):
    if re.search(r'\bfrom\s+\w[\w.]*\s+import\b', code):  add("python", 6)
    if re.search(r'__\w+__', code):                        add("python", 5)
    if re.search(r'\bdef\s+\w+\s*\(', code):              add("python", 2)  # weak: also Ruby

    # Java — distinctive: import java., @Override, System.out, throws
    if re.search(r'\bpublic\s+(?:(?:abstract|final|static)\s+)*class\s+\w+', code): add("java", 5)
    if re.search(r'\bpublic\s+(?:(?:abstract|static)\s+)?interface\s+\w+', code):   add("java", 6)
    if re.search(r'\bpublic\s+enum\s+\w+', code):         add("java", 6)
    if re.search(r'\bimport\s+java\.', code):              add("java", 10)
    if re.search(r'@Override\b', code):                    add("java", 7)
    if re.search(r'\bSystem\.out\.', code):                add("java", 8)
    if re.search(r'\bthrows\s+\w+', code):                 add("java", 5)
    if re.search(r'\bpublic\s+static\s+void\s+main\b', code): add("java", 10)
    if re.search(r'\bimplements\s+\w+', code):             add("java", 6)
    if re.search(r'\bextends\s+\w+', code):               add("java", 3)  # weak: also TS
    if re.search(r'\bnew\s+\w+\s*\(', code):              add("java", 2)  # weak: also C#
    if re.search(r'\bimport\s+(?!java\.|static\s)[\w.]+;', code): add("java", 3)

    # C# — distinctive: namespace, using System
    if re.search(r'\bnamespace\s+\w+', code):              add("c#", 8)
    if re.search(r'\busing\s+System\b', code):             add("c#", 8)
    if re.search(r'\busing\s+\w[\w.]+;', code):            add("c#", 4)
    if re.search(r'\bvar\s+\w+\s*=\s*new\b', code):       add("c#", 4)  # var x = new Foo()

    # JavaScript — distinctive: =>, require(), module.exports, console.log
    if re.search(r'\bconst\s+\w+\s*=.*=>', code):         add("javascript", 7)
    if re.search(r'\brequire\s*\(', code):                 add("javascript", 6)
    if re.search(r'\bmodule\.exports\b', code):            add("javascript", 8)
    if re.search(r'\bconsole\.log\b', code):               add("javascript", 7)
    if re.search(r'\bexport\s+(default|function|const|class)\b', code): add("javascript", 6)
    if re.search(r'=>\s*[\w{(]', code):                    add("javascript", 3)
    # Angular / AMD / test frameworks
    if re.search(r'\bangular\.', code):                    add("javascript", 6)
    if re.search(r'\bdefine\s*\(\s*\[', code):             add("javascript", 7)  # AMD define([
    if re.search(r"describe\s*\(['\"].*['\"],\s*function", code): add("javascript", 6)
    if re.search(r"it\s*\(['\"].*['\"],\s*function", code):      add("javascript", 6)
    if re.search(r'\bexpect\s*\(.*\)\.to[A-Z]', code):    add("javascript", 5)  # Jest expect().toBe()
    if re.search(r'\bjQuery\b|\$\s*\(', code):             add("javascript", 5)

    # Ruby — distinctive: class X < Y, attr_*, def self., do |var|, RSpec
    if re.search(r'class\s+\w+\s*<\s*\w+', code):         add("ruby", 9)
    if re.search(r'\battr_(?:accessor|reader|writer)\b', code): add("ruby", 10)
    if re.search(r'\bdef\s+self\.\w+', code):              add("ruby", 8)
    if re.search(r'\s+do\s+\|', code):                     add("ruby", 6)
    if re.search(r'\brequire_relative\b', code):           add("ruby", 9)
    if re.search(r"describe\s+[A-Z]\w*.*\s+do\b", code):  add("ruby", 7)  # RSpec: describe Foo do
    if re.search(r"\bit\s+['\"].*['\"].*\s+do\b", code):  add("ruby", 7)  # RSpec: it '...' do
    if re.search(r'\bexpect\s*\(.*\)\.to\s+\b', code):    add("ruby", 6)  # RSpec expect().to matcher
    if re.search(r'\.each\s+do\s+\|', code):               add("ruby", 7)
    if re.search(r'\bend\s*$', code, re.MULTILINE):        add("ruby", 2)  # weak: `end` block close

    # PHP — very distinctive: <?php, $var =, $this->
    if re.search(r'<\?php', code):                         add("php", 10)
    if re.search(r'\$[A-Za-z_]\w*(?:\s*\[.*?\])?\s*=', code): add("php", 6)  # $var = and $arr[] =
    if re.search(r'\$this->', code):                       add("php", 7)
    if re.search(r'\becho\s+', code):                      add("php", 5)
    if re.search(r'\bfunction\s+\w+\s*\(.*\)\s*\{', code): add("php", 2)  # weak

    # C++ — distinctive: std::, cout, template<, vector<, this-> without $
    if re.search(r'#include\s*<\w', code):                 add("c++", 6)
    if re.search(r'\bstd::', code):                        add("c++", 8)
    if re.search(r'\bcout\s*<<', code):                    add("c++", 9)
    if re.search(r'\btemplate\s*<', code):                 add("c++", 8)
    if re.search(r'\bvector\s*<', code):                   add("c++", 6)
    if re.search(r'\bthis->\w+', code):                    add("c++", 4)  # without $ prefix
    if re.search(r'::\w+\s*\(', code):                     add("c++", 3)  # Foo::bar() scope resolution

    # C — distinctive: malloc, printf, int main, kernel patterns
    if re.search(r'\bprintf\s*\(', code):                  add("c", 5)
    if re.search(r'\bmalloc\s*\(', code):                  add("c", 7)
    if re.search(r'\bsizeof\s*\(', code):                  add("c", 5)
    if re.search(r'\bint\s+main\s*\(', code):              add("c", 8)
    if re.search(r'#include\s*"[\w./]+\.h"', code):        add("c", 4)
    if re.search(r'\bstruct\s+\w+\s*\{', code):            add("c", 3)
    if re.search(r'\btypedef\s+\w+', code):                add("c", 4)

    # HTML/template markup — not a programming language, treat as unknown
    non_empty = [l.strip() for l in code.splitlines() if l.strip()]
    if non_empty:
        html_lines = sum(1 for l in non_empty if re.match(r'^[+\- ]?\s*<[/%!]?\w', l))
        if html_lines / len(non_empty) > 0.4:
            return "unknown"

    # Pure comment block — no actual code to infer from
    code_lines = [l for l in code.splitlines()
                  if l.strip() and not re.match(r'^[\s+\- ]*(?://|/\*|\*|#)', l)]
    if not code_lines:
        return "unknown"

    if not scores:
        return "unknown"
    return max(scores, key=lambda k: scores[k])


# ─── Dataset 1 — Kaggle code-review-data-v2 ──────────────────────────────────

def _kaggle_normalize_patch(patch: str) -> str:
    """Convert [KEEP]/[ADD]/[DEL] tags to standard unified diff format ( /+/-)."""
    lines = patch.splitlines()
    result = []
    for line in lines:
        if line.startswith("[KEEP]"):
            result.append(" " + line[6:])
        elif line.startswith("[ADD]"):
            result.append("+" + line[5:])
        elif line.startswith("[DEL]"):
            result.append("-" + line[5:])
        else:
            result.append(line)
    return "\n".join(result)


def _kaggle_clean_review(review: str) -> str:
    """Strip everything from 'refinement:' onwards; keep only the text comment."""
    return review.split("refinement:")[0].strip()


def load_kaggle() -> list[dict]:
    """
    Local CSV at data/kaggle_code_review_data.csv.
    Fields: patch (code), responce (review, has typo), lang, reward (RLHF score).
    Language distribution: unknown/go/java/py/cs/cpp/js/php/rb/c.
    Cleaning applied:
      - patch: [KEEP]/[ADD]/[DEL] → standard unified diff ( /+/-)
      - responce: strip 'refinement:' suffix (keeps only the text comment)
    """
    import pandas as pd

    csv_path = RAW_DIR / "kaggle_code_review_data.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Not found: {csv_path}\n"
            "Download from kaggle.com/datasets/bulivington/code-review-data-v2"
        )

    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["patch", "responce"])
    df = df.drop_duplicates(subset=["patch"])
    df = df[df["patch"].str.strip().str.len() > 20]
    # Apply cleaning before length filter so truncated reviews aren't wrongly kept
    df["responce"] = df["responce"].apply(_kaggle_clean_review)
    df = df[df["responce"].str.len() > 30]

    _KAGGLE_LANG = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "rb": "ruby", "go": "go", "java": "java", "cpp": "c++",
        ".cs": "c#", "cs": "c#", "php": "php", "c": "c",
        "none": "unknown",
    }
    items = []
    for _, row in df.iterrows():
        lang = str(row.get("lang", "unknown")).strip().lower()
        if lang in ("nan", "none", ""):
            lang = "unknown"
        lang = _KAGGLE_LANG.get(lang, lang)
        try:
            reward = float(row.get("reward", 0.0))
        except (TypeError, ValueError):
            reward = None
        normalized_patch = _kaggle_normalize_patch(str(row["patch"]))
        if lang == "unknown":
            lang = _infer_lang_from_code_content(normalized_patch)
        if lang == "unknown":
            continue
        items.append(make_item(
            source="kaggle",
            code=normalized_patch,
            review=str(row["responce"]),
            language=lang,
            reward=reward,
        ))
    return items


# ─── Dataset 2 — SeRe ────────────────────────────────────────────────────────

def _sere_extract_review(comment) -> str:
    """
    SeRe comment field has two formats:
      - single-round: plain string (reviewer's comment)
      - multi-round:  list of {role, message, author} dicts
    Extract only reviewer messages; join multiple rounds with newline.
    """
    if isinstance(comment, str):
        return comment.strip()
    if isinstance(comment, list):
        msgs = [m["message"] for m in comment if m.get("role") == "reviewer" and m.get("message")]
        return "\n".join(msgs).strip()
    return ""


def load_sere() -> list[dict]:
    """
    Download code/data/sere.zip from github.com/caagc/Sere, extract sere.jsonl.
    Confirmed fields: patch, context, comment, diff, code_refinement, language.
    Languages: C, C#, Go, C++, Java, Kotlin.
    Cleaning: multi-round comment (list) → extract reviewer messages only.
    """
    raw_path = RAW_DIR / "sere.jsonl"

    if not raw_path.exists():
        print("  Downloading SeRe ZIP from GitHub...")
        zip_url = _raw_url("caagc/Sere", "main", "code/data/sere.zip")
        resp = _get(zip_url, timeout=120)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = zf.namelist()
            jsonl_name = next((n for n in names if n.endswith(".jsonl")), None)
            if not jsonl_name:
                raise RuntimeError(f"No .jsonl found in sere.zip. Contents: {names}")
            with zf.open(jsonl_name) as jf:
                raw_path.write_bytes(jf.read())
        print(f"  Extracted {raw_path.stat().st_size // 1024} KB -> {raw_path}")
    else:
        print("  SeRe: using cached file")

    items = []
    with open(raw_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if lineno == 0:
                print(f"  SeRe fields: {list(obj.keys())}")

            code = (
                obj.get("patch") or obj.get("diff")
                or obj.get("code_change") or obj.get("hunk") or ""
            )
            review = _sere_extract_review(
                obj.get("comment") or obj.get("review_comment")
                or obj.get("msg") or obj.get("body") or ""
            )
            lang = (
                obj.get("language") or obj.get("lang")
                or obj.get("programming_language") or ""
            )
            if not code or not review:
                continue
            if len(review) <= 30:
                continue
            items.append(make_item(
                source="sere",
                code=code,
                review=review,
                language=lang or "unknown",
                label=obj.get("label"),
                db_name=obj.get("db_name"),
            ))
    return items


# ─── Dataset 3 — CRAVE ───────────────────────────────────────────────────────

def load_crave() -> list[dict]:
    """
    HuggingFace: TuringEnterprises/CRAVE, 1174 rows (train+val+test), no auth needed.
    Fields: diff (code), explanation (review), label (APPROVE/REQUEST_CHANGES), repo.
    Cleaning: APPROVE items have synthetic explanation "The commit was approved by the
    reviewer." (100% of 587 APPROVE rows) — discard entirely, keep REQUEST_CHANGES only.
    Language: inferred from diff file headers via _infer_lang_from_patch().
    """
    raw_path = RAW_DIR / "crave.jsonl"

    if not raw_path.exists():
        print("  Downloading CRAVE from HuggingFace...")
        try:
            from datasets import load_dataset  # type: ignore
        except ImportError:
            raise ImportError("Run:  uv pip install datasets")

        all_rows: list[dict] = []
        for split in ("train", "validation", "test"):
            try:
                ds = load_dataset("TuringEnterprises/CRAVE", split=split)
                all_rows.extend([dict(row) for row in ds])
            except Exception as exc:
                print(f"  Warning: split '{split}' failed: {exc}")

        with open(raw_path, "w", encoding="utf-8") as f:
            for row in all_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  Saved {len(all_rows)} rows")
    else:
        print("  CRAVE: using cached file")

    items = []
    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            # APPROVE items have synthetic explanation — no review value
            if obj.get("label") != "REQUEST_CHANGES":
                continue
            # patch = actual unified diff; diff = JSON commit hash object (not useful)
            code   = obj.get("patch") or ""
            review = obj.get("explanation") or obj.get("description") or obj.get("hint") or ""
            label  = obj.get("label")
            repo   = obj.get("repo", "")

            if not code or not review:
                continue

            lang = _infer_lang_from_patch(code)
            items.append(make_item(
                source="crave",
                code=code,
                review=review,
                language=lang,
                label=label,
                repo=repo,
                pr_number=obj.get("pr_number"),
            ))
    return items


# ─── Dataset 4 — CodeReviewQA ────────────────────────────────────────────────

def load_codereviewer_qa() -> list[dict]:
    """
    HuggingFace: Tomo-Melb/CodeReviewQA  (gated — requires huggingface-cli login)
    900 rows, 9 languages × 100 each: C, C++, CSharp, Go, Java, JavaScript, PHP, Python, Ruby.
    Fields used: old (pre-review code), review (review comment), lang.
    Bonus field: new (post-review revised code) stored in metadata.
    """
    raw_path = RAW_DIR / "codereviewer_qa.jsonl"

    if not raw_path.exists():
        print("  Downloading CodeReviewQA.jsonl from HuggingFace (requires web consent)...")
        hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN_READ_ONLY")
        headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
        url = "https://huggingface.co/datasets/Tomo-Melb/CodeReviewQA/resolve/main/CodeReviewQA.jsonl"
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code == 403:
            raise RuntimeError(
                "403 Forbidden — you need to accept dataset terms first.\n"
                "Visit https://huggingface.co/datasets/Tomo-Melb/CodeReviewQA\n"
                "and click 'Agree and access repository', then re-run."
            )
        resp.raise_for_status()
        raw_path.write_bytes(resp.content)
        lines = [l for l in resp.text.splitlines() if l.strip()]
        print(f"  Saved {len(lines)} rows ({raw_path.stat().st_size // 1024} KB)")
    else:
        print("  CodeReviewQA: using cached file")

    _QA_LANG = {
        "cpp": "c++", "csharp": "c#", "javascript": "javascript",
        "python": "python", "java": "java", "go": "go",
        "ruby": "ruby", "php": "php", "c": "c",
    }
    items: list[dict] = []
    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj    = json.loads(line)
            code   = obj.get("old") or obj.get("code") or obj.get("patch") or ""
            review = obj.get("review") or obj.get("review_comment") or obj.get("comment") or ""
            raw_lang = (obj.get("lang") or obj.get("language") or "unknown").lower().strip()
            lang = _QA_LANG.get(raw_lang, raw_lang)
            if not code or not review:
                continue
            items.append(make_item(
                source="codereviewer_qa",
                code=code,
                review=review,
                language=lang,
                revised_code=(obj.get("new") or "")[:500] or None,
            ))
    return items


# ─── Dataset 5 — Microsoft CodeReviewer ──────────────────────────────────────

def load_ms_codereviewer(max_rows: int = 50_000) -> list[dict]:
    """
    HuggingFace: fasterinnerlooper/codereviewer, config=train_refinement.
    Total: ~170K rows; we cap at max_rows to keep download manageable.
    Fields: old (code hunk), comment (review), lang, hunk (diff context).
    Config 'train_refinement' has the clearest (code, review_comment, language) triples.
    """
    raw_path = RAW_DIR / "ms_codereviewer.jsonl"

    if not raw_path.exists():
        print(f"  Downloading Microsoft CodeReviewer train_refinement (up to {max_rows:,} rows)...")
        try:
            from datasets import load_dataset  # type: ignore
        except ImportError:
            raise ImportError("Run:  uv pip install datasets")

        ds = load_dataset(
            "fasterinnerlooper/codereviewer",
            "train_refinement",
            split="train",
            streaming=True,
        )

        count = 0
        with open(raw_path, "w", encoding="utf-8") as f:
            for row in ds:
                f.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
                count += 1
                if count >= max_rows:
                    break
                if count % 10_000 == 0:
                    print(f"  Progress: {count:,}/{max_rows:,}")

        print(f"  Saved {count:,} rows -> {raw_path}")
    else:
        print("  Microsoft CodeReviewer: using cached file")

    _MS_LANG = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "rb": "ruby", "go": "go", "java": "java", "cpp": "c++",
        ".cs": "c#", "cs": "c#", "php": "php", "c": "c",
    }
    items: list[dict] = []
    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip 5 corrupted lines
            # old_hunk = diff hunk with @@ context and +/- markers (richer than plain `old`)
            code   = obj.get("old_hunk") or obj.get("old") or obj.get("oldf") or ""
            review = obj.get("comment") or obj.get("msg") or ""
            raw_lang = (obj.get("lang") or "unknown").lower().strip()
            lang = _MS_LANG.get(raw_lang, raw_lang)
            if not code or not review:
                continue
            if len(review) <= 30:
                continue
            items.append(make_item(
                source="ms_codereviewer",
                code=code,
                review=review,
                language=lang,
                repo=obj.get("repo", "") or None,
            ))
    return items


# ─── Dataset 6 — SWE-bench Lite ──────────────────────────────────────────────

def load_swb_lite() -> list[dict]:
    """
    HuggingFace: princeton-nlp/SWE-bench_Lite, 300 Python GitHub issues + fix patches.
    Fields: patch (code diff), problem_statement (issue = what reviewer should catch),
            hints_text, repo, instance_id.
    """
    raw_path = RAW_DIR / "swb_lite.jsonl"

    if not raw_path.exists():
        print("  Downloading SWE-bench Lite from HuggingFace...")
        try:
            from datasets import load_dataset  # type: ignore
        except ImportError:
            raise ImportError("Run:  uv pip install datasets")

        ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
        with open(raw_path, "w", encoding="utf-8") as f:
            for row in ds:
                f.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
        print(f"  Saved {len(ds)} rows")
    else:
        print("  SWE-bench Lite: using cached file")

    items: list[dict] = []
    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj     = json.loads(line)
            patch   = obj.get("patch", "")
            problem = obj.get("problem_statement", "")
            hints   = obj.get("hints_text", "")
            if not patch:
                continue
            review = problem + (f"\n\nHints: {hints}" if hints else "")
            items.append(make_item(
                source="swb_lite",
                code=patch,
                review=review,
                language="python",
                repo=obj.get("repo", ""),
                instance_id=obj.get("instance_id", ""),
            ))
    return items


# ─── Split & tag ─────────────────────────────────────────────────────────────

def split_and_tag(
    items: list[dict], n_eval: int, source: str
) -> tuple[list[dict], list[dict]]:
    """Deterministic shuffle then split eval / rag. Assign IDs in place."""
    rng  = random.Random(SEED)
    pool = items.copy()
    rng.shuffle(pool)

    actual_eval = min(n_eval, len(pool))
    eval_part   = pool[:actual_eval]
    rag_part    = pool[actual_eval:]

    for i, item in enumerate(eval_part):
        item["split"] = "eval"
        item["id"]    = f"{source}_eval_{i:04d}"
    for i, item in enumerate(rag_part):
        item["split"] = "rag"
        item["id"]    = f"{source}_rag_{i:04d}"

    return eval_part, rag_part


def lang_distribution(items: list[dict]) -> dict[str, int]:
    d: dict[str, int] = {}
    for item in items:
        lang = item.get("language", "unknown")
        d[lang] = d.get(lang, 0) + 1
    return dict(sorted(d.items(), key=lambda kv: -kv[1]))


# ─── Main ────────────────────────────────────────────────────────────────────

DATASETS: list[tuple[str, object]] = [
    ("kaggle",          load_kaggle),
    ("sere",            load_sere),
    ("crave",           load_crave),
    ("codereviewer_qa", load_codereviewer_qa),
    ("ms_codereviewer", load_ms_codereviewer),
    ("swb_lite",        load_swb_lite),
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build eval set + RAG KB from 6 code-review datasets"
    )
    parser.add_argument(
        "--n", type=int, default=100,
        help="Eval items per dataset (default 100). Remaining go to RAG KB.",
    )
    args = parser.parse_args()
    N = args.n

    DATA_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)

    print(f"=== Dataset Builder  (N={N} eval items per dataset, seed={SEED}) ===\n")

    all_eval: list[dict] = []
    all_rag:  list[dict] = []
    stats:    list[dict] = []

    for name, loader in DATASETS:  # type: ignore[assignment]
        print(f"[{name}]")
        try:
            items: list[dict] = loader()  # type: ignore[call-arg]
        except Exception as exc:
            print(f"  SKIP — {exc}\n")
            continue

        eval_part, rag_part = split_and_tag(items, N, name)
        all_eval.extend(eval_part)
        all_rag.extend(rag_part)

        dist = lang_distribution(items)
        stats.append({
            "source":                name,
            "total":                 len(items),
            "eval_count":            len(eval_part),
            "rag_count":             len(rag_part),
            "language_distribution": dist,
        })

        top = list(dist.items())[:5]
        print(f"  Total {len(items):>5} | Eval {len(eval_part):>4} | RAG KB {len(rag_part):>5}")
        print(f"  Languages: {', '.join(f'{l}({c})' for l, c in top)}\n")

    # ── Write outputs ───────────────────────────────────────────────────────

    eval_path  = DATA_DIR / "eval_set.jsonl"
    rag_path   = DATA_DIR / "rag_kb.jsonl"
    stats_path = DATA_DIR / "dataset_stats.json"

    with open(eval_path, "w", encoding="utf-8") as f:
        for item in all_eval:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(rag_path, "w", encoding="utf-8") as f:
        for item in all_rag:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    summary = {
        "n_per_dataset":  N,
        "random_seed":    SEED,
        "total_eval":     len(all_eval),
        "total_rag":      len(all_rag),
        "datasets":       stats,
    }
    stats_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ── Print summary table ─────────────────────────────────────────────────

    W = 70
    print("=" * W)
    print(f"{'Dataset':<20} {'Total':>7} {'Eval':>6} {'RAG KB':>8}  Top languages")
    print("-" * W)
    for s in stats:
        top = list(s["language_distribution"].items())[:3]
        langs = ", ".join(f"{l}({c})" for l, c in top)
        print(
            f"{s['source']:<20} {s['total']:>7} {s['eval_count']:>6}"
            f" {s['rag_count']:>8}  {langs}"
        )
    print("-" * W)
    grand = sum(s["total"] for s in stats)
    print(f"{'TOTAL':<20} {grand:>7} {len(all_eval):>6} {len(all_rag):>8}")
    print(f"\nOutput:")
    print(f"  {eval_path}   ({len(all_eval)} rows)")
    print(f"  {rag_path}   ({len(all_rag)} rows)")
    print(f"  {stats_path}")


if __name__ == "__main__":
    main()
