"""pigeon_rename.validator — Post-rename import validation.

Scans every .py file, parses import statements,
checks that every internal import resolves to an existing file.
"""
import re
from pathlib import Path

SKIP_DIRS = {'.venv', '__pycache__', 'node_modules', '.git',
             '.next', '.pytest_cache', 'compiler_output'}


def validate_imports(root: Path, known_internal: set[str] = None) -> dict:
    """Validate all internal imports resolve to existing files.

    Args:
        root: project root
        known_internal: set of top-level package names to check.
                        If None, auto-detects from folders with __init__.py.
    Returns:
        dict with 'valid' bool, 'broken' list, 'total_checked' int.
    """
    root = Path(root)
    if known_internal is None:
        known_internal = _auto_detect_packages(root)
    broken = []
    total = 0

    for py in sorted(root.rglob('*.py')):
        if _should_skip(py, root):
            continue
        text = _safe_read(py)
        if not text:
            continue
        rel = str(py.relative_to(root)).replace('\\', '/')
        imports = _extract_imports(text)
        for imp in imports:
            if not _is_internal(imp['module'], known_internal):
                continue
            total += 1
            if not _resolves(root, imp['module']):
                broken.append({
                    'file': rel,
                    'line': imp['line'],
                    'import': imp['raw'],
                    'module': imp['module'],
                })

    return {
        'valid': len(broken) == 0,
        'broken': broken,
        'total_checked': total,
    }


def _auto_detect_packages(root: Path) -> set[str]:
    """Find top-level folders that have __init__.py."""
    packages = set()
    for d in root.iterdir():
        if d.is_dir() and (d / '__init__.py').exists():
            if d.name not in SKIP_DIRS and not d.name.startswith('.'):
                packages.add(d.name)
    return packages


def _extract_imports(text: str) -> list:
    results = []
    for i, line in enumerate(text.split('\n'), 1):
        s = line.strip()
        if s.startswith('from '):
            m = re.match(r'from\s+([\w.]+)\s+import', s)
            if m:
                results.append({'module': m.group(1), 'line': i, 'raw': s})
        elif s.startswith('import '):
            m = re.match(r'import\s+([\w.]+)', s)
            if m:
                results.append({'module': m.group(1), 'line': i, 'raw': s})
    return results


def _is_internal(module: str, known_internal: set[str]) -> bool:
    return module.split('.')[0] in known_internal


def _resolves(root: Path, module: str) -> bool:
    parts = module.split('.')
    file_path = root / '/'.join(parts)
    if file_path.with_suffix('.py').exists():
        return True
    if (file_path / '__init__.py').exists():
        return True
    if len(parts) >= 2:
        parent = root / '/'.join(parts[:-1])
        if (parent / '__init__.py').exists():
            init_text = _safe_read(parent / '__init__.py')
            if parts[-1] in init_text:
                return True
    return False


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''


def _should_skip(py: Path, root: Path) -> bool:
    parts = py.relative_to(root).parts
    return any(p in SKIP_DIRS for p in parts)
