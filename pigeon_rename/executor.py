"""pigeon_rename.executor — Execute file renames with rollback capability.

Renames files on disk and maintains a rollback log for atomic recovery.
"""
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone


def execute_rename(root: Path, plan: dict,
                   dry_run: bool = False) -> dict:
    """Execute all file renames from the plan.

    Returns dict with 'renamed' list, 'rollback_log' path, 'errors' list.
    """
    root = Path(root)
    renamed = []
    errors = []
    rollback = []

    for r in plan['renames']:
        old = root / r['old_path']
        new = root / r['new_path']
        if not old.exists():
            errors.append(f"missing: {r['old_path']}")
            continue
        rollback.append({'old': r['old_path'], 'new': r['new_path']})
        if not dry_run:
            new.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old), str(new))
            renamed.append(r['new_path'])
        else:
            renamed.append(f"[dry-run] {r['old_path']} -> {r['new_path']}")

    log_path = None
    if not dry_run and rollback:
        log_path = _save_rollback(root, rollback)

    return {
        'renamed': renamed,
        'errors': errors,
        'rollback_log': str(log_path) if log_path else None,
    }


def rollback_rename(root: Path, log_path: Path) -> dict:
    """Reverse a rename operation using its rollback log."""
    root = Path(root)
    log = json.loads(Path(log_path).read_text(encoding='utf-8'))
    restored = []
    errors = []
    for entry in reversed(log['renames']):
        new = root / entry['new']
        old = root / entry['old']
        if new.exists():
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(new), str(old))
            restored.append(entry['old'])
        else:
            errors.append(f"missing: {entry['new']}")
    return {'restored': restored, 'errors': errors}


def _save_rollback(root: Path, entries: list) -> Path:
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    log_dir = root / '.pigeon' / 'rollback_logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f'rollback_{ts}.json'
    log_path.write_text(json.dumps({
        'timestamp': ts,
        'renames': entries,
    }, indent=2), encoding='utf-8')
    return log_path
