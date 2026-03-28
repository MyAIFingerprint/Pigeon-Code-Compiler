"""pigeon_rename.compliance — Line-count enforcer + split recommender.

Scans every .py file, flags oversize files, and generates
split recommendations with natural break points.
"""
import ast
import re
from pathlib import Path

from pigeon_rename.limits import PIGEON_MAX, is_excluded

SKIP_DIRS = {'.venv', '__pycache__', 'node_modules', '.git',
             '.next', '.pytest_cache', 'compiler_output',
             'rollback_logs', 'audit_backups', 'logs', '.vscode',
             'cache', '.pigeon'}

MAX_LINES = PIGEON_MAX
WARN_LINES = 300
CRIT_LINES = 500


def audit_compliance(root: Path) -> dict:
    """Full codebase line-count audit.

    Returns {total, compliant, compliance_pct, oversize: [...], by_folder: {...}}
    """
    root = Path(root)
    total = 0
    compliant = 0
    oversize = []
    by_folder = {}

    for py in sorted(root.rglob('*.py')):
        if _should_skip(py, root):
            continue
        if py.name == '__init__.py':
            continue

        try:
            text = py.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        lc = len(text.splitlines())
        total += 1
        rel = str(py.relative_to(root)).replace('\\', '/')
        folder = str(py.parent.relative_to(root)).replace('\\', '/')

        if folder not in by_folder:
            by_folder[folder] = {'total': 0, 'compliant': 0, 'files': []}
        by_folder[folder]['total'] += 1
        by_folder[folder]['files'].append({'name': py.name, 'lines': lc})

        if lc <= MAX_LINES:
            compliant += 1
            by_folder[folder]['compliant'] += 1
        else:
            status = _classify(lc)
            splits = _recommend_splits(text, lc) if lc > WARN_LINES else []
            oversize.append({
                'path': rel,
                'lines': lc,
                'status': status,
                'splits': splits,
            })

    oversize.sort(key=lambda x: -x['lines'])

    return {
        'total': total,
        'compliant': compliant,
        'compliance_pct': round(compliant / max(total, 1) * 100, 1),
        'oversize': oversize,
        'by_folder': by_folder,
    }


def check_file(py: Path) -> dict:
    """Check a single file's compliance."""
    try:
        text = py.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return {'path': str(py), 'lines': 0, 'status': 'ERROR'}

    lc = len(text.splitlines())
    status = 'OK' if lc <= MAX_LINES else _classify(lc)
    splits = _recommend_splits(text, lc) if lc > WARN_LINES else []

    return {
        'path': str(py),
        'lines': lc,
        'status': status,
        'splits': splits,
    }


def format_report(audit: dict) -> str:
    """Format audit results as readable text."""
    lines = []
    lines.append('=== PIGEON COMPLIANCE REPORT ===')
    lines.append(f'Total files: {audit["total"]}')
    lines.append(f'Compliant (\u2264{MAX_LINES} lines): {audit["compliant"]} '
                 f'({audit["compliance_pct"]}%)')
    lines.append(f'Oversize: {len(audit["oversize"])}')
    lines.append('')

    icons = {'OVER': '\u26a0\ufe0f', 'WARN': '\U0001f7e0', 'CRITICAL': '\U0001f534'}
    for entry in audit['oversize']:
        icon = icons.get(entry['status'], '?')
        lines.append(f'{icon} [{entry["status"]:>8}] '
                     f'{entry["lines"]:>5} lines  {entry["path"]}')
        for s in entry.get('splits', []):
            lines.append(f'          \u2192 split at L{s["line"]}: '
                         f'{s["reason"]} \u2192 {s["suggested_name"]}')

    return '\n'.join(lines)


def _classify(lc: int) -> str:
    if lc <= MAX_LINES:
        return 'OK'
    if lc <= WARN_LINES:
        return 'OVER'
    if lc <= CRIT_LINES:
        return 'WARN'
    return 'CRITICAL'


def _recommend_splits(text: str, total_lines: int) -> list[dict]:
    """Find natural split points in a file."""
    splits = []
    lines_list = text.splitlines()

    try:
        tree = ast.parse(text)
        classes = [n for n in ast.iter_child_nodes(tree)
                   if isinstance(n, ast.ClassDef)]
        if len(classes) >= 2:
            for cls in classes:
                splits.append({
                    'line': cls.lineno,
                    'reason': f'class {cls.name}',
                    'suggested_name': _snake(cls.name),
                })

        funcs = [n for n in ast.iter_child_nodes(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if len(funcs) >= 6:
            mid = len(funcs) // 2
            split_func = funcs[mid]
            splits.append({
                'line': split_func.lineno,
                'reason': f'function cluster at {split_func.name}()',
                'suggested_name': split_func.name,
            })
    except SyntaxError:
        pass

    section_pat = re.compile(r'^#\s*[=\-\u2500\u2550]{3,}\s*(.+?)\s*[=\-\u2500\u2550]*\s*$')
    for i, line in enumerate(lines_list, 1):
        m = section_pat.match(line.strip())
        if m:
            splits.append({
                'line': i,
                'reason': f'section: {m.group(1).strip()}',
                'suggested_name': _snake(m.group(1).strip()),
            })

    seen_lines = set()
    unique = []
    for s in sorted(splits, key=lambda x: x['line']):
        if s['line'] not in seen_lines:
            seen_lines.add(s['line'])
            unique.append(s)
    return unique


def _snake(name: str) -> str:
    name = re.sub(r'[^a-zA-Z0-9]', '_', name)
    name = re.sub(r'([A-Z])', r'_\1', name).lower()
    return re.sub(r'_+', '_', name).strip('_')


def _should_skip(py: Path, root: Path) -> bool:
    parts = py.relative_to(root).parts
    for p in parts:
        if p in SKIP_DIRS or p.startswith('.venv'):
            return True
    return False
