from pathlib import Path

from django.conf import settings


ALLOWED_EXTENSIONS = {".py", ".dart", ".yaml", ".yml", ".json", ".md", ".txt"}
IGNORED_PARTS = {
    ".git", "venv", ".venv", "build", ".dart_tool", "node_modules", "__pycache__", "media",
}
MAX_FILE_BYTES = 180_000
MAX_CONTEXT_CHARS = 28_000


def _repo_root() -> Path:
    # backend/ is BASE_DIR; repository root is its parent.
    return Path(settings.BASE_DIR).resolve().parent


def _safe_path(relative_path: str) -> Path:
    root = _repo_root()
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path is outside the ARI SMART RO repository.")
    return candidate


def read_project_file(relative_path: str) -> str:
    path = _safe_path(relative_path)
    if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Project file is not readable by ANDY.")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Project file is too large for ANDY context.")
    return path.read_text(encoding="utf-8", errors="replace")


def search_project(query: str, limit: int = 8):
    terms = [term.lower() for term in query.split() if len(term) >= 3][:8]
    if not terms:
        return []
    root = _repo_root()
    scored = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        haystack = f"{path.name}\n{text}".lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            scored.append((score, path, text))
    scored.sort(key=lambda item: item[0], reverse=True)
    result, used = [], 0
    for score, path, text in scored[:limit]:
        relative = path.relative_to(root).as_posix()
        excerpt = text[:5000]
        if used + len(excerpt) > MAX_CONTEXT_CHARS:
            excerpt = excerpt[: max(0, MAX_CONTEXT_CHARS - used)]
        if not excerpt:
            break
        result.append({"path": relative, "score": score, "content": excerpt})
        used += len(excerpt)
    return result


def build_project_context(query: str) -> str:
    matches = search_project(query)
    if not matches:
        return "No matching ARI SMART RO project files were found locally."
    blocks = []
    for match in matches:
        blocks.append(f"FILE: {match['path']}\n---\n{match['content']}")
    return "\n\n".join(blocks)
