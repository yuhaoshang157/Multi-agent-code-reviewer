"""Day 1: Milvus + BGE-M3 basic demo — embed code → store → query."""
from pathlib import Path
from pymilvus import MilvusClient
from FlagEmbedding import BGEM3FlagModel

PROJECT_ROOT = Path(__file__).parent.parent

# --- 1. Load BGE-M3 (downloads model on first run, ~2GB) ---
print("Loading BGE-M3 model...")
embedder = BGEM3FlagModel(str(PROJECT_ROOT / "models" / "bge-m3"), use_fp16=True)

# --- 2. Embed sample code snippets ---
code_snippets = [
    "def get_user(db, user_id):\n    query = f'SELECT * FROM users WHERE id = {user_id}'\n    return db.execute(query)",
    "def read_file(path):\n    f = open(path)\n    return f.read()  # file handle never closed",
    "def process_list(items):\n    result = []\n    for item in items:\n        result = result + [item * 2]  # O(n^2) list concat",
    "def hash_password(pwd):\n    return pwd  # plaintext, no hashing",
    "def safe_query(db, user_id):\n    return db.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
]

labels = [
    "SQL injection vulnerability",
    "Resource leak: file not closed",
    "Performance: O(n^2) list concatenation",
    "Security: plaintext password storage",
    "Good practice: parameterized query",
]

print("Embedding code snippets with BGE-M3...")
result = embedder.encode(code_snippets, batch_size=5, max_length=512)
vectors = result["dense_vecs"].tolist()  # shape: (5, 1024)
print(f"Vector shape: {len(vectors)} x {len(vectors[0])}")

# --- 3. Connect to Milvus and create collection ---
client = MilvusClient(uri="http://localhost:19530")

COLLECTION = "code_issues"
if client.has_collection(COLLECTION):
    client.drop_collection(COLLECTION)

client.create_collection(
    collection_name=COLLECTION,
    dimension=1024,         # BGE-M3 dense vector dimension
    metric_type="COSINE",   # cosine similarity (best for text/code)
)
print(f"Collection '{COLLECTION}' created.")

# --- 4. Insert vectors with metadata ---
data = [
    {"id": i, "vector": vectors[i], "code": code_snippets[i], "label": labels[i]}
    for i in range(len(code_snippets))
]
client.insert(collection_name=COLLECTION, data=data)
client.flush(COLLECTION)  # ensure data is committed before search
print(f"Inserted {len(data)} records.")

# --- 5. Query: find issues similar to a new code snippet ---
query_code = "def login(db, username, password):\n    sql = f'SELECT * FROM users WHERE name={username}'"
query_vec = embedder.encode([query_code])["dense_vecs"].tolist()

results = client.search(
    collection_name=COLLECTION,
    data=query_vec,
    limit=3,
    output_fields=["label", "code"],
)

print("\n=== Query: suspicious login function ===")
print(f"Code: {query_code}\n")
print("Top-3 similar historical issues:")
for rank, hit in enumerate(results[0], 1):
    print(f"  [{rank}] similarity={hit['distance']:.3f} | {hit['entity']['label']}")
    print(f"       {hit['entity']['code'][:60]}...")
