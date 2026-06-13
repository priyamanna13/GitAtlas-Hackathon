"""
GitHub Fetcher — RepoMind Utility
Fetches repository structure and file contents via GitHub REST API.
"""

import requests
import os
import base64
import re
from typing import Optional

PRIORITY_FILES = [
    "main.py", "app.py", "index.py", "server.py", "run.py",
    "main.js", "app.js", "index.js", "server.js",
    "main.ts", "app.ts", "index.ts",
    "main.go", "main.rb", "main.java",
    "config.py", "config.js", "config.ts", "settings.py", "settings.js",
    "models.py", "models.js", "schema.py", "schema.js",
    "routes.py", "routes.js", "router.py", "router.js",
    "utils.py", "utils.js", "helpers.py", "helpers.js",
    "services.py", "services.js",
    "controllers.py", "controllers.js",
    "middleware.py", "middleware.js",
    "README.md", "readme.md", "README.rst",
    "package.json", "requirements.txt", "Pipfile", "pyproject.toml",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "Makefile", ".env.example", "setup.py", "setup.cfg",
    "pom.xml", "build.gradle", "go.mod", "Cargo.toml",
]

PRIORITY_DIRS = [
    "src", "app", "lib", "core", "api", "routes", "models",
    "controllers", "services", "utils", "helpers", "middleware",
    "config", "configs", "settings",
]

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".pytest_cache",
    "dist", "build", ".next", ".nuxt", "vendor", "venv",
    "env", ".env", "coverage", ".coverage", "htmlcov",
    "eggs", ".eggs", "*.egg-info", "migrations", "static",
    "assets", "public", "images", "img", "fonts", "css",
    "test", "tests", "spec", "specs", "__tests__",
}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3",
    ".lock", ".sum", ".min.js", ".min.css",
    ".pyc", ".pyo", ".class", ".o", ".so", ".dll",
}


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from GitHub URL."""
    url = url.strip().rstrip("/")
    patterns = [
        r"github\.com[:/]([^/]+)/([^/.\s]+?)(?:\.git)?$",
        r"github\.com/([^/]+)/([^/\s]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2).replace(".git", "")
    raise ValueError(f"Invalid GitHub URL: {url}")


def get_headers() -> dict:
    """Build request headers with optional auth token."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_repo_tree(owner: str, repo: str) -> list[dict]:
    """Fetch the full file tree of a repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    resp = requests.get(url, headers=get_headers(), timeout=30)
    
    if resp.status_code == 404:
        raise ValueError(f"Repository '{owner}/{repo}' not found or is private.")
    if resp.status_code == 403:
        raise PermissionError("GitHub rate limit exceeded. Add GITHUB_TOKEN to .env for higher limits.")
    if resp.status_code != 200:
        raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text[:200]}")
    
    data = resp.json()
    return [item for item in data.get("tree", []) if item["type"] == "blob"]


def score_file(path: str) -> int:
    """Score a file path for priority selection (higher = more important)."""
    filename = path.split("/")[-1].lower()
    dirname = "/".join(path.split("/")[:-1]).lower()
    ext = "." + filename.split(".")[-1] if "." in filename else ""
    
    # Skip unwanted extensions
    if ext in SKIP_EXTENSIONS:
        return -1
    
    # Skip unwanted directories
    parts = path.lower().split("/")
    for skip in SKIP_DIRS:
        if skip in parts:
            return -1
    
    score = 0
    
    # Exact filename match
    for i, priority in enumerate(PRIORITY_FILES):
        if filename == priority.lower():
            score += 100 - i
            break
    
    # Priority directory
    for i, pdir in enumerate(PRIORITY_DIRS):
        if pdir in parts[:-1]:  # directory part
            score += 50 - i
            break
    
    # Depth penalty (prefer shallower files)
    depth = path.count("/")
    score -= depth * 3
    
    # Code file bonus
    code_exts = {".py", ".js", ".ts", ".go", ".rb", ".java", ".rs", ".cpp", ".cs", ".php"}
    if ext in code_exts:
        score += 20
    
    # Config/doc bonus
    if ext in {".json", ".yaml", ".yml", ".toml", ".md", ".rst", ".txt"}:
        score += 10
    
    return score


def select_top_files(tree: list[dict], max_files: int = 15) -> list[str]:
    """Select the top N most important files from the tree."""
    scored = [(item["path"], score_file(item["path"])) for item in tree]
    scored = [(p, s) for p, s in scored if s >= 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in scored[:max_files]]


def fetch_file_content(owner: str, repo: str, path: str) -> Optional[str]:
    """Fetch content of a single file."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    resp = requests.get(url, headers=get_headers(), timeout=20)
    
    if resp.status_code != 200:
        return None
    
    data = resp.json()
    if data.get("encoding") == "base64":
        try:
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            # Truncate very large files
            if len(content) > 8000:
                content = content[:8000] + "\n\n[... file truncated for analysis ...]"
            return content
        except Exception:
            return None
    return None


def fetch_repo_metadata(owner: str, repo: str) -> dict:
    """Fetch basic repo metadata."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    resp = requests.get(url, headers=get_headers(), timeout=20)
    if resp.status_code == 200:
        data = resp.json()
        return {
            "name": data.get("name", repo),
            "full_name": data.get("full_name", f"{owner}/{repo}"),
            "description": data.get("description", ""),
            "language": data.get("language", "Unknown"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "topics": data.get("topics", []),
            "default_branch": data.get("default_branch", "main"),
        }
    return {"name": repo, "full_name": f"{owner}/{repo}", "description": "", "language": "Unknown"}


def fetch_repository(github_url: str) -> dict:
    """
    Main entry point — fetch everything needed for analysis.
    Returns a raw_repo_data dict consumed by the Perception Agent.
    """
    owner, repo = parse_github_url(github_url)
    
    metadata = fetch_repo_metadata(owner, repo)
    tree = fetch_repo_tree(owner, repo)
    
    top_files = select_top_files(tree, max_files=15)
    
    files_content = {}
    for path in top_files:
        content = fetch_file_content(owner, repo, path)
        if content:
            files_content[path] = content
    
    # Build folder structure summary
    all_paths = [item["path"] for item in tree]
    folder_structure = build_folder_summary(all_paths)
    
    return {
        "owner": owner,
        "repo": repo,
        "github_url": github_url,
        "metadata": metadata,
        "total_files": len(tree),
        "selected_files": top_files,
        "files_content": files_content,
        "folder_structure": folder_structure,
        "all_paths_sample": all_paths[:100],  # first 100 for structure analysis
    }


def build_folder_summary(paths: list[str]) -> str:
    """Build a compact folder structure summary string."""
    dirs = set()
    for path in paths:
        parts = path.split("/")
        for i in range(1, len(parts)):
            dirs.add("/".join(parts[:i]))
    
    top_dirs = sorted([d for d in dirs if d.count("/") == 0])
    summary_lines = []
    for d in top_dirs[:20]:
        children = [p for p in paths if p.startswith(d + "/") and p.count("/") == d.count("/") + 1]
        summary_lines.append(f"{d}/ ({len(children)} files)")
    
    root_files = [p for p in paths if "/" not in p]
    if root_files:
        summary_lines.append(f"[root]: {', '.join(root_files[:10])}")
    
    return "\n".join(summary_lines)
