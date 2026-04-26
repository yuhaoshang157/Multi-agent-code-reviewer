"""RAG knowledge base: seed bug patterns + embed + Milvus store/query."""
import os
from pathlib import Path
from pymilvus import MilvusClient
from FlagEmbedding import BGEM3FlagModel

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_PATH = str(PROJECT_ROOT / "models" / "bge-m3")
MILVUS_URI = os.environ.get("MILVUS_URI", "http://localhost:19530")
COLLECTION = "bug_patterns"
DIMENSION = 1024

# ---------------------------------------------------------------------------
# Seed data: known bug patterns (code, label, comment)
# ---------------------------------------------------------------------------
SEED_BUGS = [
    {
        "code": "query = f'SELECT * FROM users WHERE id = {user_id}'\ndb.execute(query)",
        "label": "SQL injection",
        "comment": "f-string or %-format SQL is injectable; use parameterized queries instead.",
    },
    {
        "code": "query = 'SELECT * FROM orders WHERE name = ' + name\ndb.execute(query)",
        "label": "SQL injection",
        "comment": "String concatenation in SQL is injectable.",
    },
    {
        "code": "f = open(path)\ndata = f.read()\nreturn data",
        "label": "Resource leak",
        "comment": "File handle never closed; use 'with open(path) as f' instead.",
    },
    {
        "code": "conn = psycopg2.connect(dsn)\ncursor = conn.cursor()\ncursor.execute(sql)",
        "label": "Resource leak",
        "comment": "DB connection never closed; wrap in try/finally or context manager.",
    },
    {
        "code": "result = []\nfor item in items:\n    result = result + [item]",
        "label": "O(n^2) performance",
        "comment": "List concatenation in loop is O(n^2); use result.append(item) instead.",
    },
    {
        "code": "def is_palindrome(s):\n    return s == s[::-1]",
        "label": "Good practice",
        "comment": "Clean and correct palindrome check.",
    },
    {
        "code": "PASSWORD = 'admin123'\nSECRET_KEY = 'hardcoded-secret'",
        "label": "Hardcoded secret",
        "comment": "Credentials hardcoded in source; use environment variables.",
    },
    {
        "code": "token = 'ghp_abc123realtoken'\nheaders = {'Authorization': f'Bearer {token}'}",
        "label": "Hardcoded secret",
        "comment": "API token hardcoded; load from os.environ instead.",
    },
    {
        "code": "def hash_password(pwd):\n    return pwd",
        "label": "Plaintext password",
        "comment": "Password stored as plaintext; use bcrypt or argon2.",
    },
    {
        "code": "def hash_password(pwd):\n    return hashlib.md5(pwd.encode()).hexdigest()",
        "label": "Weak hash",
        "comment": "MD5 is broken for passwords; use bcrypt/argon2.",
    },
    {
        "code": "except Exception:\n    pass",
        "label": "Silent exception",
        "comment": "Swallowing exceptions hides bugs; at minimum log the error.",
    },
    {
        "code": "except:\n    pass",
        "label": "Silent exception",
        "comment": "Bare except catches even KeyboardInterrupt; always specify exception type.",
    },
    {
        "code": "eval(user_input)",
        "label": "Code injection",
        "comment": "eval() on user input allows arbitrary code execution.",
    },
    {
        "code": "os.system(f'ls {user_path}')",
        "label": "Command injection",
        "comment": "Shell injection via unsanitized input; use subprocess with list args.",
    },
    {
        "code": "subprocess.run(f'git clone {url}', shell=True)",
        "label": "Command injection",
        "comment": "shell=True with f-string is injectable; pass args as list.",
    },
    {
        "code": "time.sleep(5)\nresult = fetch_data()",
        "label": "Arbitrary sleep",
        "comment": "Fixed sleep is fragile; use retry with backoff or event-based waiting.",
    },
    {
        "code": "def get_items(lst=[]):\n    lst.append(1)\n    return lst",
        "label": "Mutable default argument",
        "comment": "Mutable default is shared across calls; use None and initialize inside.",
    },
    {
        "code": "import pickle\nobj = pickle.loads(user_data)",
        "label": "Unsafe deserialization",
        "comment": "pickle.loads on untrusted data allows RCE; use JSON or validate source.",
    },
    {
        "code": "assert user_id > 0, 'invalid id'",
        "label": "Assert for validation",
        "comment": "assert is stripped with -O flag; use if/raise for input validation.",
    },
    {
        "code": "SELECT * FROM users",
        "label": "SELECT *",
        "comment": "SELECT * fetches all columns; specify needed columns for performance.",
    },
    {
        "code": "for i in range(len(items)):\n    print(items[i])",
        "label": "Non-idiomatic loop",
        "comment": "Use 'for item in items' or enumerate(); range(len()) is unpythonic.",
    },
    {
        "code": "if type(x) == int:",
        "label": "Type check anti-pattern",
        "comment": "Use isinstance(x, int); type() breaks with subclasses.",
    },
    {
        "code": "requests.get(url, verify=False)",
        "label": "TLS verification disabled",
        "comment": "verify=False disables certificate checking; man-in-the-middle risk.",
    },
    {
        "code": "def safe_query(db, user_id):\n    return db.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
        "label": "Good practice",
        "comment": "Parameterized query correctly prevents SQL injection.",
    },
    {
        "code": "with open(path) as f:\n    return f.read()",
        "label": "Good practice",
        "comment": "Context manager ensures file is closed even on exception.",
    },
]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

_embedder: BGEM3FlagModel | None = None
_client: MilvusClient | None = None


def _get_embedder() -> BGEM3FlagModel:
    global _embedder
    if _embedder is None:
        _embedder = BGEM3FlagModel(MODEL_PATH, use_fp16=True)
    return _embedder


def _get_client() -> MilvusClient:
    global _client
    if _client is None:
        _client = MilvusClient(uri=MILVUS_URI)
    return _client


def _embed(texts: list[str]) -> list[list[float]]:
    return _get_embedder().encode(texts, batch_size=16, max_length=512)["dense_vecs"].tolist()


def init_knowledge_base(force_reinit: bool = False) -> None:
    """Embed seed bugs and store in Milvus. Skip if collection already exists."""
    client = _get_client()
    if client.has_collection(COLLECTION):
        if not force_reinit:
            print(f"[RAG] Collection '{COLLECTION}' already exists, skipping init.")
            return
        client.drop_collection(COLLECTION)

    client.create_collection(collection_name=COLLECTION, dimension=DIMENSION, metric_type="COSINE")

    texts = [f"{b['label']}: {b['code']}" for b in SEED_BUGS]
    vectors = _embed(texts)

    data = [
        {"id": i, "vector": vectors[i], "label": SEED_BUGS[i]["label"], "comment": SEED_BUGS[i]["comment"], "code": SEED_BUGS[i]["code"]}
        for i in range(len(SEED_BUGS))
    ]
    client.insert(collection_name=COLLECTION, data=data)
    client.flush(COLLECTION)
    print(f"[RAG] Initialized '{COLLECTION}' with {len(data)} bug patterns.")


def query_similar_bugs(code_chunk: str, top_k: int = 3) -> list[dict]:
    """Return top-k similar bug patterns for a given code chunk."""
    client = _get_client()
    if not client.has_collection(COLLECTION):
        init_knowledge_base()

    vec = _embed([code_chunk])
    results = client.search(
        collection_name=COLLECTION,
        data=vec,
        limit=top_k,
        output_fields=["label", "comment", "code"],
    )
    return [
        {
            "similarity": round(hit["distance"], 3),
            "label": hit["entity"]["label"],
            "comment": hit["entity"]["comment"],
            "code": hit["entity"]["code"],
        }
        for hit in results[0]
    ]


if __name__ == "__main__":
    init_knowledge_base(force_reinit=True)

    test_code = "sql = f'DELETE FROM logs WHERE user={uid}'\ndb.execute(sql)"
    hits = query_similar_bugs(test_code, top_k=3)
    print(f"\nQuery: {test_code}\nTop-3 similar bugs:")
    for h in hits:
        print(f"  [{h['similarity']}] {h['label']}: {h['comment']}")
