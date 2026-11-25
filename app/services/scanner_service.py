from collections import Counter
from pathlib import PurePosixPath


LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".html": "HTML",
    ".css": "CSS",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".php": "PHP",
    ".go": "Go",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sql": "SQL",
}


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
}


def analyze_files(paths):
    files = []
    directories = set()
    languages = Counter()

    for raw_path in paths:
        path = PurePosixPath(raw_path)

        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue

        files.append(str(path))

        extension = path.suffix.lower()
        if extension in LANGUAGES:
            languages[LANGUAGES[extension]] += 1

        for parent in path.parents:
            if str(parent) != ".":
                directories.add(str(parent))

    return {
        "total_files": len(files),
        "total_directories": len(directories),
        "languages": dict(languages),
        "files": files[:500],
        "truncated": len(files) > 500,
    }
