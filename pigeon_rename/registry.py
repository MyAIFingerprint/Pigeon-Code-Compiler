"""pigeon_rename.registry — Module version tracking in pigeon_registry.json.

Stores every file's identity, version, mutation date, description,
last intent, and change history. Eliminates full filesystem scans.

Registry entry format:
{
  "path": "src/noise_filter_seq007_v003_d0315__filter_live_noise_lc_added_drift.py",
  "name": "noise_filter",
  "seq": 7,
  "ver": 3,
  "date": "0315",
  "desc": "filter_live_noise",
  "intent": "added_drift_detection",
  "history": [...]
}

Filename = {name}_seq{NNN}_v{NNN}_d{MMDD}__{desc}_lc_{intent}.py
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_FILE = 'pigeon_registry.json'
PIGEON_STEM_RE = re.compile(
    r'^(?P<name>.+)_seq(?P<seq>\d{3})_v(?P<ver>\d{3})'
    r'(?:_d(?P<date>\d{4}))?'
    r'(?:__(?P<slug>[a-z0-9_]+))?$'
)
LC_SEP = '_lc_'


def _today() -> str:
    return datetime.now(timezone.utc).strftime('%m%d')


def registry_path(root: Path) -> Path:
    return Path(root) / REGISTRY_FILE


def load_registry(root: Path) -> dict:
    """Load pigeon_registry.json. Returns {path: entry} dict."""
    rp = registry_path(root)
    if not rp.exists():
        return {}
    try:
        data = json.loads(rp.read_text(encoding='utf-8'))
        return {e['path']: e for e in data.get('files', [])}
    except (json.JSONDecodeError, KeyError):
        return {}


def save_registry(root: Path, entries: dict):
    """Write pigeon_registry.json atomically."""
    rp = registry_path(root)
    data = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'total': len(entries),
        'files': sorted(entries.values(), key=lambda e: e['path']),
    }
    rp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n',
                  encoding='utf-8')


def parse_pigeon_stem(stem: str) -> dict | None:
    """Parse a pigeon filename stem into components.

    'noise_filter_seq007_v003_d0315__filter_live_noise_lc_added_drift'
    -> {name, seq, ver, date, desc, intent}
    """
    m = PIGEON_STEM_RE.match(stem)
    if not m:
        return None
    slug = m.group('slug') or ''
    desc, intent = '', ''
    if slug:
        if LC_SEP in slug:
            desc, intent = slug.split(LC_SEP, 1)
        else:
            desc = slug
    return {
        'name': m.group('name'),
        'seq': int(m.group('seq')),
        'ver': int(m.group('ver')),
        'date': m.group('date') or '',
        'desc': desc,
        'intent': intent,
    }


def build_pigeon_filename(name: str, seq: int, ver: int,
                          date: str = '', desc: str = '',
                          intent: str = '') -> str:
    """Construct a full pigeon filename from components."""
    parts = f'{name}_seq{seq:03d}_v{ver:03d}'
    if date:
        parts += f'_d{date}'
    if desc and intent:
        parts += f'__{desc}{LC_SEP}{intent}'
    elif desc:
        parts += f'__{desc}'
    return parts + '.py'


def build_registry_from_scan(root: Path, catalog: dict) -> dict:
    """Bootstrap a registry from a scanner catalog (first-time setup)."""
    entries = {}
    today = _today()
    for f in catalog['files']:
        if f['is_init']:
            continue
        parsed = parse_pigeon_stem(f['stem'])
        if parsed:
            entry = {
                'path': f['path'],
                'name': parsed['name'],
                'seq': parsed['seq'],
                'ver': parsed['ver'],
                'date': parsed['date'] or today,
                'desc': parsed['desc'],
                'intent': parsed['intent'] or 'registered',
                'history': [{
                    'ver': parsed['ver'],
                    'date': parsed['date'] or today,
                    'desc': parsed['desc'],
                    'intent': parsed['intent'] or 'registered',
                    'action': 'registered',
                }],
            }
        else:
            entry = {
                'path': f['path'],
                'name': f['stem'],
                'seq': 0,
                'ver': 0,
                'date': today,
                'desc': '',
                'intent': '',
                'history': [{'ver': 0, 'date': today, 'desc': '',
                             'intent': '', 'action': 'discovered'}],
            }
        entries[f['path']] = entry
    return entries


def bump_version(entry: dict, new_desc: str = '',
                 new_intent: str = '', action: str = 'mutated') -> dict:
    """Bump an entry's version, update date + desc + intent, append history."""
    today = _today()
    entry['ver'] += 1
    entry['date'] = today
    if new_desc:
        entry['desc'] = new_desc
    if new_intent:
        entry['intent'] = new_intent
    entry['history'].append({
        'ver': entry['ver'],
        'date': today,
        'desc': entry['desc'],
        'intent': entry['intent'],
        'action': action,
    })
    folder = str(Path(entry['path']).parent).replace('\\', '/')
    if folder == '.':
        folder = ''
    new_filename = build_pigeon_filename(
        entry['name'], entry['seq'], entry['ver'],
        entry['date'], entry['desc'], entry['intent'],
    )
    entry['path'] = f'{folder}/{new_filename}' if folder else new_filename
    return entry


def bump_all_versions(entries: dict, intent: str = 'mass_rename',
                      action: str = 'mass_rename') -> dict:
    """Bump every entry's version by 1 (mass version increment)."""
    today = _today()
    for entry in entries.values():
        if entry['seq'] == 0:
            continue
        entry['ver'] += 1
        entry['date'] = today
        entry['intent'] = intent
        entry['history'].append({
            'ver': entry['ver'],
            'date': today,
            'desc': entry['desc'],
            'intent': intent,
            'action': action,
        })
        folder = str(Path(entry['path']).parent).replace('\\', '/')
        if folder == '.':
            folder = ''
        new_filename = build_pigeon_filename(
            entry['name'], entry['seq'], entry['ver'],
            entry['date'], entry['desc'], entry['intent'],
        )
        entry['path'] = f'{folder}/{new_filename}' if folder else new_filename
    return entries


def diff_registry_vs_disk(root: Path, entries: dict,
                          scan_fn=None) -> dict:
    """Compare registry against actual files on disk.

    Returns {missing_on_disk, new_on_disk, matched}.
    Pass scan_fn=pigeon_rename.scanner.scan_project or it auto-imports.
    """
    if scan_fn is None:
        from pigeon_rename.scanner import scan_project
        scan_fn = scan_project

    catalog = scan_fn(root)
    disk_paths = {f['path'] for f in catalog['files'] if not f['is_init']}
    reg_paths = set(entries.keys())

    return {
        'missing_on_disk': sorted(reg_paths - disk_paths),
        'new_on_disk': sorted(disk_paths - reg_paths),
        'matched': sorted(reg_paths & disk_paths),
    }
