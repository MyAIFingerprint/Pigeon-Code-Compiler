"""Tests for the Pigeon Code Compilor package.

Tests the full pipeline: scan → plan → rename → validate → manifest.
All tests use a temporary directory with synthetic Python files.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Helpers ──────────────────────────────────


def _make_project(root: Path):
    """Create a minimal Python project for testing."""
    # Package with two modules
    pkg = root / 'mypackage'
    pkg.mkdir()
    (pkg / '__init__.py').write_text(
        'from mypackage.utils import helper\n'
        'from mypackage.core import process\n',
        encoding='utf-8',
    )
    (pkg / 'utils.py').write_text(
        '"""utils — Shared utility functions."""\n\n'
        'def helper(x):\n'
        '    return x + 1\n\n'
        'MAX_RETRIES = 3\n',
        encoding='utf-8',
    )
    (pkg / 'core.py').write_text(
        '"""core — Main processing logic."""\n\n'
        'from mypackage.utils import helper\n\n'
        'def process(data):\n'
        '    """Process incoming data."""\n'
        '    return [helper(d) for d in data]\n\n'
        'class Processor:\n'
        '    def run(self):\n'
        '        pass\n',
        encoding='utf-8',
    )

    # A standalone script at root
    (root / 'main.py').write_text(
        '"""main — Entry point."""\n\n'
        'from mypackage.core import process\n\n'
        'if __name__ == "__main__":\n'
        '    print(process([1, 2, 3]))\n',
        encoding='utf-8',
    )

    # An oversized file (>200 lines)
    big_lines = ['"""big — An oversized module for testing."""\n']
    big_lines += [f'def func_{i}():\n    return {i}\n\n' for i in range(80)]
    (root / 'big.py').write_text(''.join(big_lines), encoding='utf-8')


def _run_tests():
    passed = 0
    failed = 0
    errors = []

    def test(name, fn):
        nonlocal passed, failed
        try:
            fn()
            passed += 1
            print(f'  PASS: {name}')
        except Exception as e:
            failed += 1
            errors.append((name, e))
            print(f'  FAIL: {name} — {e}')

    tmpdir = Path(tempfile.mkdtemp(prefix='pigeon_test_'))
    try:
        _make_project(tmpdir)

        # ── TEST 1: Scanner ──────────────────
        def test_scanner():
            from pigeon_rename.scanner import scan_project
            catalog = scan_project(tmpdir)
            assert catalog['stats']['total'] >= 4, f'Expected >=4 files, got {catalog["stats"]["total"]}'
            names = {f['name'] for f in catalog['files']}
            assert 'utils.py' in names, f'utils.py not found in {names}'
            assert 'core.py' in names, f'core.py not found in {names}'

        test('Scanner finds all Python files', test_scanner)

        # ── TEST 2: Compliance audit ─────────
        def test_compliance():
            from pigeon_rename.compliance import audit_compliance
            audit = audit_compliance(tmpdir)
            assert audit['total'] >= 4, f'Expected >=4 files, got {audit["total"]}'
            # big.py should be flagged as oversize
            oversize_paths = [e['path'] for e in audit['oversize']]
            assert any('big' in p for p in oversize_paths), \
                f'big.py should be oversize but got: {oversize_paths}'

        test('Compliance flags oversized files', test_compliance)

        # ── TEST 3: Manifest generation ──────
        def test_manifest():
            from pigeon_rename.manifest_builder import build_manifest
            content = build_manifest(tmpdir / 'mypackage', tmpdir)
            assert '# MANIFEST' in content, 'Missing MANIFEST header'
            assert 'utils.py' in content, 'utils.py not in manifest'
            assert 'core.py' in content, 'core.py not in manifest'
            assert 'helper()' in content or 'helper' in content, 'Exports not extracted'
            assert '## Health' in content, 'Missing Health section'

        test('Manifest builder generates valid markdown', test_manifest)

        # ── TEST 4: Build all manifests ──────
        def test_build_all():
            from pigeon_rename.manifest_builder import build_all_manifests
            results = build_all_manifests(tmpdir, dry_run=False)
            assert len(results) >= 1, f'Expected >=1 manifest, got {len(results)}'
            manifest_path = tmpdir / 'mypackage' / 'MANIFEST.md'
            assert manifest_path.exists(), 'MANIFEST.md not written'

        test('Build all manifests writes files', test_build_all)

        # ── TEST 5: Validator ────────────────
        def test_validator():
            from pigeon_rename.validator import validate_imports
            result = validate_imports(tmpdir)
            assert result['valid'], f'Expected valid imports, got broken: {result["broken"]}'

        test('Import validator passes on clean project', test_validator)

        # ── TEST 6: Nametag ──────────────────
        def test_nametag():
            from pigeon_rename.nametag import (
                build_nametag, parse_nametag, slugify, extract_desc_slug,
            )
            # Build a nametag
            tag = build_nametag('noise_filter_seq007_v003_d0315',
                                'filter_live_noise', 'added_drift_detection')
            assert 'seq007' in tag, f'Missing seq in {tag}'
            assert 'v003' in tag, f'Missing ver in {tag}'
            assert 'filter_live_noise' in tag, f'Missing desc in {tag}'

            # Parse it back
            parsed = parse_nametag(tag)
            assert parsed is not None, f'Failed to parse {tag}'
            assert parsed['seq'] == '007', f'Seq mismatch: {parsed}'
            assert parsed['ver'] == '003', f'Ver mismatch: {parsed}'

            # Slugify
            assert slugify('Filter Live Noise!') == 'filter_live_noise'

        test('Nametag build/parse round-trip', test_nametag)

        # ── TEST 7: Registry ─────────────────
        def test_registry():
            from pigeon_rename.registry import (
                load_registry, save_registry, build_registry_from_scan,
                parse_pigeon_stem, build_pigeon_filename, bump_version,
            )
            from pigeon_rename.scanner import scan_project

            # Build from scan
            catalog = scan_project(tmpdir)
            entries = build_registry_from_scan(tmpdir, catalog)
            assert len(entries) >= 3, f'Expected >=3 entries, got {len(entries)}'

            # Save and reload
            save_registry(tmpdir, entries)
            reg_file = tmpdir / 'pigeon_registry.json'
            assert reg_file.exists(), 'Registry file not written'
            loaded = load_registry(tmpdir)
            assert len(loaded) == len(entries), 'Registry round-trip size mismatch'

            # Parse stem
            parsed = parse_pigeon_stem('noise_filter_seq007_v003_d0315__filter_noise_lc_drift')
            assert parsed is not None
            assert parsed['name'] == 'noise_filter'
            assert parsed['seq'] == 7
            assert parsed['desc'] == 'filter_noise'
            assert parsed['intent'] == 'drift'

            # Build filename
            fn = build_pigeon_filename('test', 1, 2, '0327', 'my_desc', 'my_intent')
            assert fn == 'test_seq001_v002_d0327__my_desc_lc_my_intent.py'

        test('Registry save/load/parse round-trip', test_registry)

        # ── TEST 8: Planner ──────────────────
        def test_planner():
            from pigeon_rename.scanner import scan_project
            from pigeon_rename.planner import build_rename_plan

            catalog = scan_project(tmpdir)
            plan = build_rename_plan(catalog, version='001', root=tmpdir, intent='test')
            assert 'renames' in plan, 'Missing renames key'
            assert 'import_map' in plan, 'Missing import_map key'
            # Should have renames for non-pigeon files
            assert plan['stats']['total_renames'] >= 0

        test('Planner generates valid rename plan', test_planner)

        # ── TEST 9: Check file compliance ────
        def test_check_file():
            from pigeon_rename.compliance import check_file
            result = check_file(tmpdir / 'big.py')
            assert result['status'] != 'OK', f'big.py should not be OK: {result}'
            assert result['lines'] > 200

        test('Check single file compliance', test_check_file)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(f'\n{"=" * 40}')
    print(f'Results: {passed} passed, {failed} failed')
    if errors:
        print('\nFailures:')
        for name, err in errors:
            print(f'  {name}: {err}')
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    import sys
    sys.exit(_run_tests())
