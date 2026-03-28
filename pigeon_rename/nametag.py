"""pigeon_rename.nametag — Encode file description + intent into filenames.

Each filename becomes a prompt carrying TWO living metadata:
  desc   = what the file IS  (from docstring, stable)
  intent = what was LAST DONE (change context, mutates each push)

Naming convention:
  {name}_seq{NNN}_v{NNN}_d{MMDD}__{desc}_lc_{intent}.py
"""
import ast
import re
from pathlib import Path

MAX_DESC_WORDS = 5
MAX_INTENT_WORDS = 3
MAX_SLUG_CHARS = 50
DESC_SEPARATOR = '__'
LC_SEP = '_lc_'

NAMETAG_PATTERN = re.compile(
    r'^(.+_seq\d{3}_v\d{3}(?:_d\d{4})?)(__[a-z0-9_]+)?\.py$'
)


def extract_desc_slug(py_path: Path) -> str:
    """Extract a short description slug from a file's docstring."""
    try:
        text = py_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''
    first_line = _docstring_first_line(text)
    if not first_line:
        return ''
    return slugify(first_line)


def slugify(text: str, max_words: int = MAX_DESC_WORDS) -> str:
    """Convert a sentence to a filename-safe slug.

    'Filter background noise from live streams' -> 'filter_background_noise_from_live'
    """
    if ' \u2014 ' in text:
        text = text.split(' \u2014 ', 1)[1]
    elif ' - ' in text:
        parts = text.split(' - ', 1)
        if len(parts[0].split()) <= 3:
            text = parts[1]
    text = text.rstrip('.')
    slug = re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')
    slug = re.sub(r'_?seq\d{3}_v\d{3}_?', '_', slug).strip('_')
    words = [w for w in slug.split('_') if w]
    if len(words) > max_words:
        words = words[:max_words]
    slug = '_'.join(words)
    if len(slug) > MAX_SLUG_CHARS:
        slug = slug[:MAX_SLUG_CHARS].rstrip('_')
    return slug


def build_nametag(stem: str, desc_slug: str, intent_slug: str = '') -> str:
    """Combine a Pigeon stem with desc + intent.

    'noise_filter_seq007_v001' + 'filter_live_noise' + 'added_drift'
    -> 'noise_filter_seq007_v001__filter_live_noise_lc_added_drift.py'
    """
    if not desc_slug:
        return f'{stem}.py'
    if intent_slug:
        return f'{stem}{DESC_SEPARATOR}{desc_slug}{LC_SEP}{intent_slug}.py'
    return f'{stem}{DESC_SEPARATOR}{desc_slug}.py'


def parse_nametag(filename: str) -> dict:
    """Parse a nametag filename into components."""
    m = NAMETAG_PATTERN.match(filename)
    if not m:
        return {'stem': Path(filename).stem, 'seq': '', 'ver': '',
                'desc_slug': '', 'intent_slug': '', 'base_stem': Path(filename).stem}
    base = m.group(1)
    slug_raw = (m.group(2) or '').lstrip('_')
    desc_slug, intent_slug = '', ''
    if slug_raw:
        if LC_SEP in slug_raw:
            desc_slug, intent_slug = slug_raw.split(LC_SEP, 1)
        else:
            desc_slug = slug_raw
    seq_m = re.search(r'_seq(\d{3})_v(\d{3})', base)
    return {
        'stem': Path(filename).stem,
        'seq': seq_m.group(1) if seq_m else '',
        'ver': seq_m.group(2) if seq_m else '',
        'desc_slug': desc_slug,
        'intent_slug': intent_slug,
        'base_stem': base,
    }


def detect_drift(py_path: Path) -> dict:
    """Check if a file's name-description matches its docstring."""
    parsed = parse_nametag(py_path.name)
    current_slug = parsed['desc_slug']
    docstring_slug = extract_desc_slug(py_path)
    if not docstring_slug:
        return {'drifted': False, 'current_slug': current_slug,
                'docstring_slug': '', 'suggested_name': py_path.name}
    drifted = current_slug != docstring_slug
    suggested = build_nametag(parsed['base_stem'], docstring_slug)
    return {
        'drifted': drifted,
        'current_slug': current_slug,
        'docstring_slug': docstring_slug,
        'suggested_name': suggested,
    }


def scan_drift(root: Path, folders: list[str] = None) -> list[dict]:
    """Scan all files for name-description drift."""
    from pigeon_rename.scanner import scan_project
    catalog = scan_project(root, folders)
    drifts = []
    for f in catalog['files']:
        if f['is_init']:
            continue
        py = root / f['path']
        if not py.exists():
            continue
        result = detect_drift(py)
        if result['drifted'] and result['docstring_slug']:
            drifts.append({
                'path': f['path'],
                'current': py.name,
                'suggested': result['suggested_name'],
                'slug_current': result['current_slug'],
                'slug_new': result['docstring_slug'],
            })
    return drifts


def _docstring_first_line(text: str) -> str:
    try:
        tree = ast.parse(text)
        ds = ast.get_docstring(tree)
        if not ds:
            return ''
    except SyntaxError:
        return ''
    for line in ds.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith(('Args:', 'Returns:', '---', 'Usage:')):
            continue
        if line.endswith('.py') and ('/' in line or '\\' in line):
            continue
        if re.match(r'^[\w.]+\.py$', line):
            continue
        if ' \u2014 ' in line:
            line = line.split(' \u2014 ', 1)[1]
        elif ' - ' in line:
            parts = line.split(' - ', 1)
            if len(parts[0].split()) <= 4:
                line = parts[1]
        return line.rstrip('.')
    return ''
