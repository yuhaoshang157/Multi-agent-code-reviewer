"""Parse Python code with tree-sitter and split into function/class chunks."""
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
_parser = Parser(PY_LANGUAGE)

# node types to extract as independent chunks
CHUNK_NODE_TYPES = {"function_definition", "class_definition"}


def chunk_python_code(source: str) -> list[dict]:
    """
    Parse Python source and return one chunk per top-level function/class.
    Each chunk: {"code": str, "type": str, "name": str, "start_line": int}
    Falls back to the whole source as one chunk if no functions/classes found.
    """
    source_bytes = source.encode("utf-8")
    tree = _parser.parse(source_bytes)
    chunks = []

    for node in tree.root_node.children:
        if node.type not in CHUNK_NODE_TYPES:
            continue
        code = source_bytes[node.start_byte:node.end_byte].decode("utf-8")
        name = _get_name(node, source_bytes)
        chunks.append({
            "code": code,
            "type": node.type,
            "name": name,
            "start_line": node.start_point[0] + 1,
        })

    if not chunks:
        chunks.append({"code": source, "type": "module", "name": "<module>", "start_line": 1})

    return chunks


def chunk_diff(diff: str) -> list[dict]:
    """
    Extract added Python code lines from a PR diff and chunk them.
    Returns chunks from the added (+) lines only.
    """
    added_lines = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])  # strip leading '+'

    added_source = "\n".join(added_lines)
    if not added_source.strip():
        return []

    return chunk_python_code(added_source)


def _get_name(node, source_bytes: bytes) -> str:
    for child in node.children:
        if child.type == "identifier":
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8")
    return "<unknown>"


if __name__ == "__main__":
    sample = """
def get_user(db, user_id):
    query = f'SELECT * FROM users WHERE id = {user_id}'
    return db.execute(query)

class UserService:
    def create(self, name):
        return User(name=name)

def safe_query(db, uid):
    return db.execute('SELECT * FROM users WHERE id = ?', (uid,))
"""
    chunks = chunk_python_code(sample)
    print(f"Found {len(chunks)} chunks:")
    for c in chunks:
        print(f"  [{c['start_line']}] {c['type']} '{c['name']}'")
        print(f"    {c['code'][:60].strip()}...")
