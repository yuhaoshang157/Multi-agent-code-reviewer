"""RAG knowledge base: ingest code-review dataset into Milvus, query by code similarity."""
import json
import logging
import os
import threading
from pathlib import Path
from pymilvus import MilvusClient
from FlagEmbedding import BGEM3FlagModel

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_PATH = str(PROJECT_ROOT / "models" / "bge-m3")
MILVUS_URI = os.environ.get("MILVUS_URI", "http://localhost:19530")
COLLECTION = "code_review_rag"
DIMENSION = 1024

EMBED_BATCH_SIZE = 64
INSERT_BATCH_SIZE = 1000
RAG_KB_PATH = str(PROJECT_ROOT / "data" / "rag_kb.jsonl")           # full 73K
SAMPLED_RAG_KB_PATH = str(PROJECT_ROOT / "data" / "rag_kb_5k.jsonl")  # stratified ~4K sample

# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

_embedder: BGEM3FlagModel | None = None
_client: MilvusClient | None = None
_embedder_lock = threading.Lock()
_client_lock = threading.Lock()


def _get_embedder() -> BGEM3FlagModel:
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:  # double-checked: re-test after acquiring lock
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                _embedder = BGEM3FlagModel(MODEL_PATH, use_fp16=(device == "cuda"), device=device)
    return _embedder


def _get_client() -> MilvusClient:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = MilvusClient(uri=MILVUS_URI)
    return _client


def _embed(texts: list[str]) -> list[list[float]]:
    return _get_embedder().encode(texts, batch_size=32, max_length=512)["dense_vecs"].tolist()


def _count_collection(collection: str) -> int:
    try:
        stats = _get_client().get_collection_stats(collection_name=collection)
        return stats.get("row_count", 0)
    except Exception:
        return 0


def _extract_embed_text(item: dict, embed_field: str) -> str:
    """Return the text to embed for a record based on embed_field strategy."""
    if embed_field == "review":
        return item.get("review", "")
    if embed_field == "code+review":
        return item.get("code", "") + "\n" + item.get("review", "")
    return item.get("code", "")  # default: "code"


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def init_rag_from_dataset(
    jsonl_path: str = RAG_KB_PATH,
    force_reinit: bool = False,
    collection: str = COLLECTION,
    embed_field: str = "code",  # "code" | "review" | "code+review"
) -> None:
    """Stream a JSONL file, embed selected fields with BGE-M3, insert into Milvus.

    embed_field controls which content is vectorised:
      "code"         — embed code only (default, current baseline)
      "review"       — embed review text (experiment B)
      "code+review"  — embed concatenation (experiment C)

    Only ingests items with ``split == "rag"`` (eval items are excluded).
    """
    client = _get_client()

    if client.has_collection(collection):
        if not force_reinit:
            n = _count_collection(collection)
            log.info("[RAG] Collection '%s' already exists (%d items), skipping ingest.", collection, n)
            log.info("      Pass force_reinit=True or --force to re-ingest from scratch.")
            return
        client.drop_collection(collection)
        log.info("[RAG] Dropped existing '%s' collection.", collection)

    client.create_collection(
        collection_name=collection,
        dimension=DIMENSION,
        metric_type="COSINE",
    )
    log.info("[RAG] Created collection '%s' (dim=%d, embed_field='%s').", collection, DIMENSION, embed_field)

    batch_texts: list[str] = []
    batch_records: list[dict] = []
    total = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            if item.get("split") != "rag":
                continue

            batch_texts.append(_extract_embed_text(item, embed_field))
            batch_records.append(item)

            if len(batch_texts) >= EMBED_BATCH_SIZE:
                _ingest_batch(client, batch_texts, batch_records, total, collection)
                total += len(batch_texts)
                batch_texts.clear()
                batch_records.clear()

    if batch_texts:
        _ingest_batch(client, batch_texts, batch_records, total, collection)
        total += len(batch_texts)

    client.flush(collection)
    log.info("[RAG] Ingest complete: %d items in '%s'.", total, collection)


def _ingest_batch(
    client: MilvusClient,
    texts: list[str],
    records: list[dict],
    offset: int,
    collection: str,
) -> None:
    """Embed a batch, then insert into Milvus in sub-batches."""
    vectors = _embed(texts)

    insert_data: list[dict] = []
    for i, (vec, rec) in enumerate(zip(vectors, records)):
        insert_data.append({
            "id": offset + i,
            "vector": vec,
            "source": rec.get("source", ""),
            "code": rec.get("code", "")[:8000],
            "review": rec.get("review", "")[:2000],
            "language": rec.get("language", "unknown"),
        })

        if len(insert_data) >= INSERT_BATCH_SIZE:
            client.insert(collection_name=collection, data=insert_data)
            insert_data.clear()

    if insert_data:
        client.insert(collection_name=collection, data=insert_data)

    log.debug("[RAG] Embedded %d items...", offset + len(texts))


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def query_similar_bugs(
    code_chunk: str,
    top_k: int = 3,
    collection: str = COLLECTION,
) -> list[dict]:
    """Return top-k similar code-review examples for a code chunk.

    Returns list of dicts with: similarity, source, review, code, language.
    Auto-ingests from rag_kb.jsonl if the default collection doesn't exist yet.
    """
    client = _get_client()

    if not client.has_collection(collection):
        if collection == COLLECTION:
            log.info("[RAG] Collection '%s' not found. Auto-ingesting...", collection)
            init_rag_from_dataset()
        else:
            raise RuntimeError(
                f"[RAG] Collection '{collection}' not found. "
                f"Run: python -m src.tools.rag_store --ingest --collection {collection}"
            )

    vec = _embed([code_chunk])
    results = client.search(
        collection_name=collection,
        data=vec,
        limit=top_k,
        output_fields=["source", "review", "code", "language"],
    )
    return [
        {
            "similarity": round(hit["distance"], 3),
            "source": hit["entity"].get("source", "unknown"),
            "review": hit["entity"].get("review", ""),
            "code": hit["entity"].get("code", ""),
            "language": hit["entity"].get("language", "unknown"),
        }
        for hit in results[0]
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG store management")
    parser.add_argument("--ingest", action="store_true", help="Ingest JSONL into Milvus")
    parser.add_argument("--force", action="store_true", help="Drop and re-ingest if collection exists")
    parser.add_argument("--jsonl", default=RAG_KB_PATH, help="Path to JSONL file (default: rag_kb.jsonl)")
    parser.add_argument("--collection", default=COLLECTION, help="Milvus collection name")
    parser.add_argument(
        "--embed-field",
        default="code",
        choices=["code", "review", "code+review"],
        help="Which field to embed (default: code)",
    )
    args = parser.parse_args()

    if args.ingest:
        init_rag_from_dataset(
            jsonl_path=args.jsonl,
            force_reinit=args.force,
            collection=args.collection,
            embed_field=args.embed_field,
        )
    else:
        print("Usage examples:")
        print("  python -m src.tools.rag_store --ingest")
        print("  python -m src.tools.rag_store --ingest --force")
        print("  python -m src.tools.rag_store --ingest --collection code_review_1k --jsonl data/rag_kb_1k.jsonl")
        print("  python -m src.tools.rag_store --ingest --collection code_review_embed_review --embed-field review")
        print()

        if _get_client().has_collection(COLLECTION):
            test_code = "sql = f'DELETE FROM logs WHERE user={uid}'\ndb.execute(sql)"
            hits = query_similar_bugs(test_code, top_k=3)
            print(f"Query: `{test_code}`\n\nTop-3 similar reviews:")
            for h in hits:
                review_preview = h["review"][:150].replace("\n", " ")
                print(f"  [{h['similarity']}] [{h['source']}/{h['language']}] {review_preview}...")
        else:
            print("No collection found. Run with --ingest first.")
