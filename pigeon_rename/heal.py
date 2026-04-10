"""pigeon_rename.heal — Self-healing orchestrator.

Runs on every push (or on demand). The pipeline:

1. GIT DIFF — detect which files changed since last heal
2. MANIFEST REBUILD — regenerate MANIFEST.md for affected folders
3. COMPLIANCE CHECK — flag oversize files in manifests
4. INTENT TRACE — read docstrings from changed files,
   surface what the operator was doing in the manifest notes

The manifest IS the prompt box. It self-mutates.
Every LLM edit leaves a docstring → heal reads it →
manifest captures intent → next session reads manifest →
picks up exactly where operator left off.

Filenames stay _seqNNN_vNNN.py (stable for imports).
The MANIFEST description column IS the living filename extension.
"""
import ast
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pigeon_rename.manifest_builder import build_manifest
from pigeon_rename.compliance import audit_compliance

HEAL_LOG = 'logs/heal_log.json'


def heal(root: Path, full: bool = False, dry_run: bool = False) -> dict:
    """Run the self-healing pipeline.

    Args:
        root: project root
        full: if True, rebuild ALL manifests (not just changed folders)
        dry_run: if True, compute but don't write
    Returns:
        heal report dict
    """
    root = Path(root)
    report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'changed_files': [],
        'affected_folders': [],
        'manifests_updated': [],
        'compliance': {},
        'intent_traces': [],
    }

    # 1. Detect changes
    if full:
        changed = _all_py_files(root)
    else:
        changed = _git_changed_files(root)

    report['changed_files'] = changed

    # 2. Find affected folders
    affected = set()
    for f in changed:
        p = Path(f)
        folder = p.parent
        folder_abs = root / folder
        if folder_abs.exists():
            affected.add(str(folder).replace('\\', '/'))
    report['affected_folders'] = sorted(affected)

    # 3. Extract intent traces from changed files
    for f in changed:
        fpath = root / f
        if not fpath.exists() or not fpath.suffix == '.py':
            continue
        trace = _extract_intent(fpath)
        if trace:
            report['intent_traces'].append({
                'file': f,
                'intent': trace,
            })

    # 4. Rebuild manifests for affected folders
    for folder_rel in affected:
        folder_abs = root / folder_rel
        if folder_abs.is_dir():
            if not dry_run:
                build_manifest(folder_abs)
            report['manifests_updated'].append(folder_rel)

    # 5. Run compliance check
    compliance = audit_compliance(root)
    report['compliance'] = {
        'total': compliance['total'],
        'compliant': compliance['compliant'],
        'pct': compliance['compliance_pct'],
        'oversize_count': len(compliance['oversize']),
        'critical': [e['path'] for e in compliance['oversize']
                     if e['status'] == 'CRITICAL'],
    }

    # 6. Write heal log
    if not dry_run:
        _write_heal_log(root, report)

    return report


def heal_report_text(report: dict) -> str:
    """Format heal report as readable text."""
    lines = []
    ts = report.get('timestamp', '?')
    lines.append(f'=== HEAL REPORT | {ts} ===')
    lines.append('')

    changed = report.get('changed_files', [])
    lines.append(f'Changed files: {len(changed)}')
    for f in changed[:20]:
        lines.append(f'  {f}')
    if len(changed) > 20:
        lines.append(f'  ... +{len(changed) - 20} more')
    lines.append('')

    folders = report.get('affected_folders', [])
    lines.append(f'Affected folders: {len(folders)}')
    for f in folders:
        lines.append(f'  {f}/')
    lines.append('')

    manifests = report.get('manifests_updated', [])
    lines.append(f'Manifests updated: {len(manifests)}')
    lines.append('')

    traces = report.get('intent_traces', [])
    if traces:
        lines.append(f'Intent traces ({len(traces)}):')
        for t in traces:
            lines.append(f'  {t["file"]}: {t["intent"]}')
        lines.append('')

    comp = report.get('compliance', {})
    lines.append(f'Compliance: {comp.get("compliant", 0)}/{comp.get("total", 0)} '
                 f'({comp.get("pct", 0)}%)')
    crits = comp.get('critical', [])
    if crits:
        lines.append(f'Critical files ({len(crits)}):')
        for c in crits[:10]:
            lines.append(f'  🔴 {c}')
    lines.append('')

    return '\n'.join(lines)


# ── Git integration ───────────────────────────────────────

def _git_changed_files(root: Path) -> list[str]:
    """Get files changed since last heal (or last commit)."""
    # Try: changed in working tree + staged
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
            capture_output=True, text=True, cwd=str(root), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            files = [f for f in result.stdout.strip().split('\n')
                     if f.endswith('.py')]
            return files
    except Exception:
        pass

    # Fallback: all tracked .py files
    return _all_py_files(root)


def _all_py_files(root: Path) -> list[str]:
    """List all non-skipped .py files."""
    skip = {'.venv', '__pycache__', 'node_modules', '.git',
            '_llm_tests_put_all_test_and_debug_scripts_here',
            '.pytest_cache', 'rollback_logs', 'audit_backups',
            'json_uploads', 'logs', 'cache', 'build'}
    files = []
    for py in sorted(root.rglob('*.py')):
        parts = py.relative_to(root).parts
        if any(p in skip or p.startswith('.venv') or
               p.startswith('_llm_tests') for p in parts):
            continue
        files.append(str(py.relative_to(root)).replace('\\', '/'))
    return files


# ── Intent extraction ─────────────────────────────────────

def _extract_intent(py: Path) -> str:
    """Extract intent from a file's docstring.

    The first sentence of the module docstring IS the intent.
    If it contains action words (fix, add, build, refactor),
    that's the operator's trace.
    """
    try:
        text = py.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''

    try:
        tree = ast.parse(text)
        ds = ast.get_docstring(tree)
        if not ds:
            return ''
    except SyntaxError:
        return ''

    # Get first meaningful line
    for line in ds.split('\n'):
        line = line.strip()
        if not line or line.startswith(('Args:', 'Returns:', '---')):
            continue
        # Strip filename prefix
        if ' — ' in line:
            line = line.split(' — ', 1)[1]
        return line.rstrip('.')

    return ''


# ── Persistence ───────────────────────────────────────────

def _write_heal_log(root: Path, report: dict) -> None:
    """Append to heal log (keeps last 50 entries)."""
    log_path = root / HEAL_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)

    history = []
    if log_path.exists():
        try:
            history = json.loads(log_path.read_text(encoding='utf-8'))
        except Exception:
            history = []

    history.append(report)
    # Keep last 50
    history = history[-50:]

    log_path.write_text(
        json.dumps(history, indent=2, default=str),
        encoding='utf-8',
    )
