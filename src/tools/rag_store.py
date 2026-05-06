"""RAG knowledge base: ingest code-review dataset into Milvus, query by code similarity."""
import json
import os
from pathlib import Path
from pymilvus import MilvusClient
from FlagEmbedding import BGEM3FlagModel

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


def _get_embedder() -> BGEM3FlagModel:
    global _embedder
    if _embedder is None:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _embedder = BGEM3FlagModel(MODEL_PATH, use_fp16=(device == "cuda"), device=device)
    return _embedder


def _get_client() -> MilvusClient:
    global _client
    if _client is None:
        _client = MilvusClient(uri=MILVUS_URI)
    return _client


def _embed(texts: list[str]) -> list[list[float]]:
    return _get_embedder().encode(texts, batch_size=32, max_length=512)["dense_vecs"].tolist()


def _count_collection() -> int:
    try:
        stats = _get_client().get_collection_stats(collection_name=COLLECTION)
        return stats.get("row_count", 0)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def init_rag_from_dataset(
    jsonl_path: str = RAG_KB_PATH,
    force_reinit: bool = False,
) -> None:
    """Stream rag_kb.jsonl, embed code fields with BGE-M3, insert into Milvus.

    Only ingests items with ``split == "rag"`` (eval items are excluded).
    Batches embeddings for GPU efficiency and inserts in sub-batches to
    avoid overwhelming the Milvus server.
    """
    client = _get_client()

    if client.has_collection(COLLECTION):
        if not force_reinit:
            n = _count_collection()
            print(f"[RAG] Collection '{COLLECTION}' already exists ({n} items), skipping ingest.")
            print(f"      Set force_reinit=True to re-ingest from scratch.")
            return
        client.drop_collection(COLLECTION)
        print(f"[RAG] Dropped existing '{COLLECTION}' collection.")

    client.create_collection(
        collection_name=COLLECTION,
        dimension=DIMENSION,
        metric_type="COSINE",
    )
    print(f"[RAG] Created collection '{COLLECTION}' (dim={DIMENSION}, metric=COSINE).")

    # Stream JSONL, accumulate batches
    batch_texts: list[str] = []
    batch_records: list[dict] = []
    total = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            if item.get("split") != "rag":
                continue

            batch_texts.append(item["code"])
            batch_records.append(item)

            if len(batch_texts) >= EMBED_BATCH_SIZE:
                _ingest_batch(client, batch_texts, batch_records, total)
                total += len(batch_texts)
                batch_texts.clear()
                batch_records.clear()

    # Final partial batch
    if batch_texts:
        _ingest_batch(client, batch_texts, batch_records, total)
        total += len(batch_texts)

    client.flush(COLLECTION)
    print(f"\n[RAG] Ingest complete: {total} items in '{COLLECTION}'.")


def _ingest_batch(
    client: MilvusClient,
    texts: list[str],
    records: list[dict],
    offset: int,
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
            client.insert(collection_name=COLLECTION, data=insert_data)
            insert_data.clear()

    if insert_data:
        client.insert(collection_name=COLLECTION, data=insert_data)

    print(f"[RAG] Embedded {offset + len(texts)} items...", end="\r")


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def query_similar_bugs(code_chunk: str, top_k: int = 3) -> list[dict]:
    """Return top-k similar code-review examples for a code chunk.

    Returns list of dicts with: similarity, source, review, code, language.
    Auto-ingests from rag_kb.jsonl if the collection doesn't exist yet.
    """
    client = _get_client()

    if not client.has_collection(COLLECTION):
        print(f"[RAG] Collection '{COLLECTION}' not found. Auto-ingesting...")
        init_rag_from_dataset()

    vec = _embed([code_chunk])
    results = client.search(
        collection_name=COLLECTION,
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
    import sys

    if "--ingest" in sys.argv:
        force = "--force" in sys.argv
        init_rag_from_dataset(force_reinit=force)
    else:
        print("Usage:  python -m src.tools.rag_store --ingest [--force]")
        print("        python -m src.tools.rag_store  (quick query demo)\n")

        if _get_client().has_collection(COLLECTION):
            test_code = "sql = f'DELETE FROM logs WHERE user={uid}'\ndb.execute(sql)"
            hits = query_similar_bugs(test_code, top_k=3)
            print(f"Query: `{test_code}`\n\nTop-3 similar reviews:")
            for h in hits:
                review_preview = h["review"][:150].replace("\n", " ")
                print(f"  [{h['similarity']}] [{h['source']}/{h['language']}] {review_preview}...")
        else:
            print("No collection found. Run with --ingest first.")
