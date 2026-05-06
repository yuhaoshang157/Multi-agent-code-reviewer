"""Week 4 evaluation framework: BERTScore-based ablation experiments.

Usage:
    python -m src.eval.evaluator --exp rag_ablation --n 5     # quick smoke test
    python -m src.eval.evaluator --exp rag_ablation --n 50    # full experiment 1
    python -m src.eval.evaluator --exp embed_strategy --n 30  # experiment 2
    python -m src.eval.evaluator --exp data_scale --n 30      # experiment 3

Install deps first:
    uv pip install bert-score scipy
"""

import argparse
import json
import logging
import random
from pathlib import Path

from src.agents.multi_agent import graph
from src.tools.rag_store import COLLECTION as DEFAULT_COLLECTION
from src.tools.token_tracker import TokenUsageCallback

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
EVAL_SET_PATH = PROJECT_ROOT / "data" / "eval_set.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "eval"


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_review(code: str, use_rag: bool, collection: str = DEFAULT_COLLECTION) -> dict:
    """Run the review pipeline and return review_text, score, issues_count."""
    tracker = TokenUsageCallback()
    result = graph.invoke(
        {"code": code, "plan": None, "review": None, "report": "",
         "use_rag": use_rag, "rag_collection": collection},
        config={"callbacks": [tracker]},
    )
    return {
        "review_text": result["review"].summary + "\n" + "\n".join(
            f"[{i.severity}] {i.description}" for i in result["review"].issues
        ),
        "review_score": result["review"].overall_score,
        "issues_count": len(result["review"].issues),
        "token_usage": tracker.summary(),
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_bertscore(predictions: list[str], references: list[str]) -> list[float]:
    """Compute BERTScore F1 for each (prediction, reference) pair.

    Uses microsoft/deberta-xlarge-mnli. Downloads ~900 MB on first run.
    Returns a list of float F1 scores, one per sample.
    """
    from bert_score import score as bert_score_fn
    _, _, f1 = bert_score_fn(
        predictions,
        references,
        model_type="microsoft/deberta-xlarge-mnli",
        verbose=False,
    )
    return f1.tolist()


# ---------------------------------------------------------------------------
# Experiment 1: RAG vs No-RAG ablation
# ---------------------------------------------------------------------------

def exp1_rag_ablation(n_samples: int = 50, seed: int = 42) -> None:
    """Compare review quality with and without RAG retrieval.

    Samples n_samples items from eval_set.jsonl, runs each through both
    RAG and No-RAG pipelines, computes BERTScore F1 vs ground truth,
    and performs a paired t-test to check significance.

    Output: outputs/eval/exp1_rag_ablation.json
    """
    from scipy import stats

    log.info("[Exp1] Loading eval set, sampling %d items (seed=%d)...", n_samples, seed)
    samples = _load_eval_samples(n_samples, seed)

    rag_results, no_rag_results = [], []
    ground_truth_reviews = [s["review"] for s in samples]

    for i, sample in enumerate(samples):
        log.info("[Exp1] Sample %d/%d...", i + 1, len(samples))
        rag_results.append(run_review(sample["code"], use_rag=True))
        no_rag_results.append(run_review(sample["code"], use_rag=False))

    log.info("[Exp1] Computing BERTScore...")
    rag_f1 = score_bertscore([r["review_text"] for r in rag_results], ground_truth_reviews)
    no_rag_f1 = score_bertscore([r["review_text"] for r in no_rag_results], ground_truth_reviews)

    t_stat, p_value = stats.ttest_rel(rag_f1, no_rag_f1)
    mean = lambda xs: sum(xs) / len(xs)
    std = lambda xs: (sum((x - mean(xs)) ** 2 for x in xs) / len(xs)) ** 0.5

    output = {
        "experiment": "rag_ablation",
        "n_samples": n_samples,
        "seed": seed,
        "rag": {
            "bertscore_f1_mean": round(mean(rag_f1), 4),
            "bertscore_f1_std": round(std(rag_f1), 4),
            "avg_review_score": round(mean([r["review_score"] for r in rag_results]), 2),
            "avg_issues_count": round(mean([r["issues_count"] for r in rag_results]), 2),
        },
        "no_rag": {
            "bertscore_f1_mean": round(mean(no_rag_f1), 4),
            "bertscore_f1_std": round(std(no_rag_f1), 4),
            "avg_review_score": round(mean([r["review_score"] for r in no_rag_results]), 2),
            "avg_issues_count": round(mean([r["issues_count"] for r in no_rag_results]), 2),
        },
        "delta_bertscore_f1": round(mean(rag_f1) - mean(no_rag_f1), 4),
        "t_stat": round(float(t_stat), 4),
        "p_value": round(float(p_value), 4),
        "significant_at_0.05": bool(p_value < 0.05),
        "per_sample": [
            {
                "source": samples[i].get("source", ""),
                "language": samples[i].get("language", ""),
                "rag_f1": round(rag_f1[i], 4),
                "no_rag_f1": round(no_rag_f1[i], 4),
            }
            for i in range(len(samples))
        ],
    }

    _save_output("exp1_rag_ablation.json", output)
    log.info("[Exp1] Done.")
    log.info("  RAG BERTScore F1:    %.4f ± %.4f", output['rag']['bertscore_f1_mean'], output['rag']['bertscore_f1_std'])
    log.info("  No-RAG BERTScore F1: %.4f ± %.4f", output['no_rag']['bertscore_f1_mean'], output['no_rag']['bertscore_f1_std'])
    log.info("  Delta: %+.4f  |  p=%.4f  |  significant=%s", output['delta_bertscore_f1'], output['p_value'], output['significant_at_0.05'])


# ---------------------------------------------------------------------------
# Experiment 2: Embedding strategy ablation
# ---------------------------------------------------------------------------

def exp2_embed_strategy(n_samples: int = 30, seed: int = 42) -> None:
    """Compare three RAG embedding strategies.

    Requires three Milvus collections to be pre-built:
      code_review_rag          — embed code field (current default, strategy A)
      code_review_embed_review — embed review field (strategy B)
      code_review_embed_both   — embed code+review (strategy C)

    Build missing collections with:
      python -m src.tools.rag_store --ingest --collection code_review_embed_review --embed-field review
      python -m src.tools.rag_store --ingest --collection code_review_embed_both --embed-field code+review

    Output: outputs/eval/exp2_embed_strategy.json
    """
    strategies = {
        "A_embed_code":   "code_review_rag",
        "B_embed_review": "code_review_embed_review",
        "C_embed_both":   "code_review_embed_both",
    }

    log.info("[Exp2] Embedding strategy ablation, n=%d", n_samples)
    samples = _load_eval_samples(n_samples, seed)
    ground_truth = [s["review"] for s in samples]
    results: dict[str, list] = {k: [] for k in strategies}

    for i, sample in enumerate(samples):
        log.info("[Exp2] Sample %d/%d...", i + 1, len(samples))
        for strategy_name, collection_name in strategies.items():
            r = run_review(sample["code"], use_rag=True, collection=collection_name)
            results[strategy_name].append(r)

    log.info("[Exp2] Computing BERTScore...")
    mean = lambda xs: sum(xs) / len(xs)
    strategy_scores = {}
    for strategy_name, res_list in results.items():
        f1 = score_bertscore([r["review_text"] for r in res_list], ground_truth)
        strategy_scores[strategy_name] = {
            "bertscore_f1_mean": round(mean(f1), 4),
            "avg_review_score": round(mean([r["review_score"] for r in res_list]), 2),
            "collection": strategies[strategy_name],
        }

    output = {
        "experiment": "embed_strategy",
        "n_samples": n_samples,
        "seed": seed,
        "strategies": strategy_scores,
        "best_strategy": max(strategy_scores, key=lambda k: strategy_scores[k]["bertscore_f1_mean"]),
    }

    _save_output("exp2_embed_strategy.json", output)
    log.info("[Exp2] Done.")
    for name, scores in strategy_scores.items():
        log.info("  %s: BERTScore F1 = %.4f", name, scores['bertscore_f1_mean'])
    log.info("  Best: %s", output['best_strategy'])


# ---------------------------------------------------------------------------
# Experiment 3: Data scale ablation
# ---------------------------------------------------------------------------

def exp3_data_scale(n_samples: int = 30, seed: int = 42) -> None:
    """Compare RAG quality across different knowledge base sizes.

    Requires three Milvus collections:
      code_review_1k   — 1K items
      code_review_10k  — 10K items
      code_review_rag  — full 73K (current default)

    Build smaller collections with:
      python -m src.tools.rag_store --ingest --collection code_review_1k --jsonl data/rag_kb_1k.jsonl
      python -m src.tools.rag_store --ingest --collection code_review_10k --jsonl data/rag_kb_10k.jsonl

    Output: outputs/eval/exp3_data_scale.json
    """
    scales = {
        "1k":  "code_review_1k",
        "10k": "code_review_10k",
        "73k": "code_review_rag",
    }

    log.info("[Exp3] Data scale ablation, n=%d", n_samples)
    samples = _load_eval_samples(n_samples, seed)
    ground_truth = [s["review"] for s in samples]
    results: dict[str, list] = {k: [] for k in scales}
    mean = lambda xs: sum(xs) / len(xs)

    for i, sample in enumerate(samples):
        log.info("[Exp3] Sample %d/%d...", i + 1, len(samples))
        for scale_name, collection_name in scales.items():
            r = run_review(sample["code"], use_rag=True, collection=collection_name)
            results[scale_name].append(r)

    log.info("[Exp3] Computing BERTScore...")
    scale_scores = {}
    for scale_name, res_list in results.items():
        f1 = score_bertscore([r["review_text"] for r in res_list], ground_truth)
        scale_scores[scale_name] = {
            "bertscore_f1_mean": round(mean(f1), 4),
            "avg_review_score": round(mean([r["review_score"] for r in res_list]), 2),
            "collection": scales[scale_name],
        }

    output = {
        "experiment": "data_scale",
        "n_samples": n_samples,
        "seed": seed,
        "scales": scale_scores,
        "best_scale": max(scale_scores, key=lambda k: scale_scores[k]["bertscore_f1_mean"]),
    }

    _save_output("exp3_data_scale.json", output)
    log.info("[Exp3] Done.")
    for name, scores in scale_scores.items():
        log.info("  %s: BERTScore F1 = %.4f", name, scores['bertscore_f1_mean'])
    log.info("  Best: %s", output['best_scale'])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_eval_samples(n: int, seed: int) -> list[dict]:
    """Load and randomly sample n items from eval_set.jsonl."""
    samples = []
    with open(EVAL_SET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            if item.get("code") and item.get("review"):
                samples.append(item)
    random.seed(seed)
    return random.sample(samples, min(n, len(samples)))


def _save_output(filename: str, data: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("[Eval] Results saved to: %s", out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Run evaluation experiments")
    parser.add_argument(
        "--exp",
        required=True,
        choices=["rag_ablation", "embed_strategy", "data_scale"],
        help="Which experiment to run",
    )
    parser.add_argument("--n", type=int, default=50, help="Number of eval samples (default: 50)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    if args.exp == "rag_ablation":
        exp1_rag_ablation(n_samples=args.n, seed=args.seed)
    elif args.exp == "embed_strategy":
        exp2_embed_strategy(n_samples=args.n, seed=args.seed)
    elif args.exp == "data_scale":
        exp3_data_scale(n_samples=args.n, seed=args.seed)
