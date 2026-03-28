"""pigeon_rename.planner — Generate rename plan for non-compliant files.

Takes scanner output, assigns sequence numbers per folder,
produces old_path -> new_path map with module path translations.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

from pigeon_rename.nametag import extract_desc_slug, build_nametag

SEQ_PATTERN = re.compile(r'_seq(\d{3})_v(\d{3})\.py$')


def build_rename_plan(catalog: dict, version: str = '001',
                      root: Path = None,
                      intent: str = 'initial_naming') -> dict:
    """Build a complete rename plan from scanner catalog.

    Groups files by folder, assigns sequence numbers,
    preserves already-compliant files' sequence numbers.
    """
    files = catalog['files']
    by_folder = _group_by_folder(files)
    renames = []
    import_map = {}
    today = datetime.now(timezone.utc).strftime('%m%d')

    for folder, folder_files in sorted(by_folder.items()):
        used_seqs = _collect_existing_seqs(folder_files)
        next_seq = max(used_seqs, default=0) + 1

        for f in folder_files:
            if f['is_pigeon'] or f['is_init']:
                continue
            base_name = _make_pigeon_stem(f['stem'], next_seq, version, today)
            py_path = Path(root) / f['path'] if root else None
            desc_slug = ''
            if py_path and py_path.exists():
                desc_slug = extract_desc_slug(py_path)
            new_name = build_nametag(base_name, desc_slug, intent)
            new_path = f"{folder}/{new_name}" if folder else new_name
            old_module = f['module_path']
            new_module = new_path.replace('/', '.').removesuffix('.py')
            renames.append({
                'old_path': f['path'],
                'new_path': new_path,
                'old_module': old_module,
                'new_module': new_module,
                'folder': folder,
                'old_stem': f['stem'],
                'new_stem': new_name.removesuffix('.py'),
            })
            import_map[old_module] = new_module
            next_seq += 1

    return {
        'renames': renames,
        'import_map': import_map,
        'stats': {
            'total_renames': len(renames),
            'folders_affected': len(set(r['folder'] for r in renames)),
        }
    }


def _group_by_folder(files: list) -> dict:
    groups = {}
    for f in files:
        groups.setdefault(f['folder'], []).append(f)
    return groups


def _collect_existing_seqs(files: list) -> list:
    seqs = []
    for f in files:
        m = SEQ_PATTERN.search(f['path'])
        if m:
            seqs.append(int(m.group(1)))
    return seqs


def _make_pigeon_stem(stem: str, seq: int, version: str,
                      date: str = '') -> str:
    clean = re.sub(r'_seq\d{3}_v\d{3}(_d\d{4})?(__[a-z0-9_]+)?$', '', stem)
    base = f"{clean}_seq{seq:03d}_v{version}"
    if date:
        base += f"_d{date}"
    return base
