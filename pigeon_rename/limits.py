"""pigeon_rename.limits — Central compliance thresholds and exclude logic.

Two-tier system:
  PIGEON_RECOMMENDED (50)  — target line count, generates warnings
  PIGEON_MAX         (200) — hard cap, blocks compliance

Exclude logic:
  is_excluded(path) returns True for files that skip compliance checks.
"""
import re
from pathlib import Path

PIGEON_RECOMMENDED = 50
PIGEON_MAX = 200
FILE_OVERHEAD = 5

EXCLUDE_NAMES = frozenset({
    "__init__.py",
    "conftest.py",
    "app.py",
    "Procfile",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
    "manage.py",
    "wsgi.py",
})

EXCLUDE_DIR_PATTERNS = frozenset({
    "__pycache__",
    ".venv",
    "node_modules",
    ".git",
    ".github",
    "logs",
    ".pytest_cache",
    ".next",
    "compiler_output",
    "cache",
    "rollback_logs",
    ".vscode",
})

EXCLUDE_STEM_PATTERNS = re.compile(
    r"^(?:prompt_"
    r"|stress_test"
    r"|test_all"
    r"|deep_test"
    r"|test_public"
    r"|conftest"
    r")",
    re.IGNORECASE,
)


def is_excluded(path: Path, root: Path = None) -> bool:
    """Return True if path should be excluded from compliance checks."""
    if path.name in EXCLUDE_NAMES:
        return True
    parts = path.parts
    for d in EXCLUDE_DIR_PATTERNS:
        if d in parts:
            return True
    if EXCLUDE_STEM_PATTERNS.search(path.stem):
        return True
    if path.suffix and path.suffix != ".py":
        return True
    return False
