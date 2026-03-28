"""pigeon_rename.import_rewriter — Rewrite all imports across the project.

Given a rename plan's import_map (old_module -> new_module),
scans every .py file and rewrites import statements atomically.
Handles: from X import Y, import X, from X.sub import Y.
"""
import re
from pathlib import Path

SKIP_DIRS = {'.venv', '__pycache__', 'node_modules', '.git',
             '.next', '.pytest_cache'}

# External packages — NEVER rewrite imports from these.
KNOWN_EXTERNAL = {
    'os', 'sys', 're', 'json', 'pathlib', 'datetime', 'collections',
    'functools', 'itertools', 'logging', 'hashlib', 'uuid', 'time',
    'typing', 'abc', 'ast', 'io', 'math', 'random', 'string',
    'threading', 'traceback', 'urllib', 'base64', 'copy', 'csv',
    'difflib', 'enum', 'glob', 'html', 'http', 'importlib', 'inspect',
    'operator', 'pickle', 'pprint', 'secrets', 'shutil', 'signal',
    'socket', 'sqlite3', 'struct', 'subprocess', 'tempfile', 'textwrap',
    'unittest', 'warnings', 'xml', 'zipfile', 'contextlib', 'dataclasses',
    'decimal', 'email', 'heapq', 'queue', 'types', 'weakref',
    'concurrent', 'multiprocessing', 'asyncio', 'ctypes', 'array',
    'argparse', 'configparser', 'platform',
    # common pip packages
    'flask', 'django', 'fastapi', 'requests', 'httpx',
    'pydantic', 'openai', 'anthropic', 'pytest', 'setuptools',
    'pip', 'pkg_resources', 'dotenv', 'click', 'rich',
    'numpy', 'pandas', 'torch', 'tensorflow',
}


def rewrite_all_imports(root: Path, import_map: dict,
                        dry_run: bool = False) -> list[dict]:
    """Rewrite imports across the entire project.

    Args:
        root: project root
        import_map: {old_module_path: new_module_path}
        dry_run: if True, compute changes but don't write
    Returns:
        list of change records [{file, old_line, new_line}]
    """
    root = Path(root)
    changes = []
    stem_map = _build_stem_map(import_map)

    for py in sorted(root.rglob('*.py')):
        if _should_skip(py, root):
            continue
        text = _safe_read(py)
        if not text:
            continue
        if not _has_any_reference(text, import_map, stem_map):
            continue
        new_text, file_changes = _rewrite_file(text, import_map, stem_map)
        if file_changes:
            rel = str(py.relative_to(root)).replace('\\', '/')
            for c in file_changes:
                c['file'] = rel
            changes.extend(file_changes)
            if not dry_run:
                py.write_text(new_text, encoding='utf-8')
    return changes


def _build_stem_map(import_map: dict) -> dict:
    stem_map = {}
    for old_mod, new_mod in import_map.items():
        old_stem = old_mod.rsplit('.', 1)[-1]
        stem_map[old_stem] = (old_mod, new_mod)
    return stem_map


def _has_any_reference(text: str, import_map: dict, stem_map: dict) -> bool:
    for old_mod in import_map:
        if old_mod in text:
            return True
    for stem in stem_map:
        if stem in text:
            return True
    return False


def _rewrite_file(text: str, import_map: dict, stem_map: dict) -> tuple:
    changes = []
    lines = text.split('\n')
    new_lines = []
    for line in lines:
        new_line = _rewrite_line(line, import_map, stem_map)
        if new_line != line:
            changes.append({'old_line': line.strip(), 'new_line': new_line.strip()})
        new_lines.append(new_line)
    return '\n'.join(new_lines), changes


def _rewrite_line(line: str, import_map: dict, stem_map: dict) -> str:
    stripped = line.lstrip()
    if not stripped.startswith(('from ', 'import ')):
        return line
    top_mod = _extract_top_module(stripped)
    if top_mod and top_mod.lower() in KNOWN_EXTERNAL:
        return line
    for old_mod, new_mod in import_map.items():
        if old_mod in line:
            return line.replace(old_mod, new_mod)
    for stem, (old_mod, new_mod) in stem_map.items():
        new_stem = new_mod.rsplit('.', 1)[-1]
        pat_abs = re.compile(
            rf'(from\s+\S+\.)({re.escape(stem)})(\s+import\s+)')
        m = pat_abs.search(line)
        if m:
            return line[:m.start(2)] + new_stem + line[m.end(2):]
        pat_rel = re.compile(
            rf'(from\s+\.)({re.escape(stem)})(\s+import\s+)')
        m = pat_rel.search(line)
        if m:
            return line[:m.start(2)] + new_stem + line[m.end(2):]
        pat_pkg = re.compile(
            rf'(from\s+\w[\w.]*\s+import\s+(?:.*?,\s*)?)(\b{re.escape(stem)}\b)')
        m = pat_pkg.search(line)
        if m:
            return line[:m.start(2)] + new_stem + line[m.end(2):]
        pat_bare = re.compile(
            rf'(import\s+\w[\w.]*\.)({re.escape(stem)})\b')
        m = pat_bare.search(line)
        if m:
            return line[:m.start(2)] + new_stem + line[m.end(2):]
    return line


def _extract_top_module(stripped: str) -> str:
    if stripped.startswith('from '):
        parts = stripped[5:].split()
        if parts:
            return parts[0].split('.')[0]
    elif stripped.startswith('import '):
        parts = stripped[7:].split(',')[0].split()
        if parts:
            return parts[0].split('.')[0]
    return ''


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''


def _should_skip(py: Path, root: Path) -> bool:
    parts = py.relative_to(root).parts
    return any(p in SKIP_DIRS for p in parts)
