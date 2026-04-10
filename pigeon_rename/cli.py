"""pigeon_rename.cli — Command-line interface for Pigeon Code Compiler.

Semantic compression for Python codebases. Zero-config, runs on every push.

Commands:
  pigeon init <root>       — Scan project, create registry + manifests
  pigeon rename <root>     — Rename non-compliant files to pigeon convention
  pigeon glyph <root>      — Rename to Chinese glyph convention (semantic territory)
  pigeon split [file]      — Split oversized files into compliant chunks
  pigeon heal <root>       — Self-healing: rebuild manifests for changed files
  pigeon manifest <root>   — Regenerate all MANIFEST.md files
  pigeon audit <root>      — Run compliance audit (line count check)
  pigeon validate <root>   — Validate all internal imports resolve
  pigeon install-hook      — Install git post-commit hook (zero-config)
  pigeon self-test         — Run compiler on itself as test
  pigeon post-commit       — Git hook entry point

By MyAIFingerprint — https://myaifingerprint.com
"""
import argparse
import sys
from pathlib import Path


def main(argv: list[str] = None):
    parser = argparse.ArgumentParser(
        prog='pigeon',
        description='Pigeon Protocol for source code. '
                    'Semantic structure, mutation tracking, and drift detection. '
                    'By MyAIFingerprint.',
    )
    sub = parser.add_subparsers(dest='command')

    # -- init --
    p_init = sub.add_parser('init', help='Initialize pigeon in a project')
    p_init.add_argument('root', nargs='?', default='.',
                        help='Project root (default: current directory)')
    p_init.add_argument('--dry-run', action='store_true',
                        help='Show what would happen without writing')

    # -- rename --
    p_rename = sub.add_parser('rename', help='Rename files to pigeon convention')
    p_rename.add_argument('root', nargs='?', default='.')
    p_rename.add_argument('--dry-run', action='store_true', default=True,
                          help='Preview renames (default)')
    p_rename.add_argument('--execute', action='store_true',
                          help='Actually perform renames')
    p_rename.add_argument('--intent', default='initial_rename',
                          help='Intent label for this rename batch')

    # -- manifest --
    p_manifest = sub.add_parser('manifest', help='Regenerate MANIFEST.md files')
    p_manifest.add_argument('root', nargs='?', default='.')
    p_manifest.add_argument('--dry-run', action='store_true')

    # -- audit --
    p_audit = sub.add_parser('audit', help='Run compliance line-count audit')
    p_audit.add_argument('root', nargs='?', default='.')

    # -- validate --
    p_validate = sub.add_parser('validate', help='Validate all imports resolve')
    p_validate.add_argument('root', nargs='?', default='.')

    # -- heal --
    p_heal = sub.add_parser('heal', help='Self-healing: rebuild manifests for changed files')
    p_heal.add_argument('root', nargs='?', default='.')
    p_heal.add_argument('--full', action='store_true',
                        help='Rebuild ALL manifests, not just changed')
    p_heal.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing')

    # -- split --
    p_split = sub.add_parser('split', help='Split oversized files into compliant chunks')
    p_split.add_argument('target', nargs='?',
                         help='Specific file to split (default: scan all)')
    p_split.add_argument('--root', default='.',
                         help='Project root (default: current directory)')
    p_split.add_argument('--dry-run', action='store_true',
                         help='Preview splits without writing')

    # -- glyph --
    p_glyph = sub.add_parser('glyph', help='Rename files to semantic glyph convention')
    p_glyph.add_argument('root', nargs='?', default='.')
    p_glyph.add_argument('--dry-run', action='store_true', default=True,
                         help='Preview renames (default)')
    p_glyph.add_argument('--execute', action='store_true',
                         help='Actually perform glyph renames')

    # -- install-hook --
    p_install = sub.add_parser('install-hook', help='Install git post-commit hook')
    p_install.add_argument('root', nargs='?', default='.')

    # -- self-test --
    p_selftest = sub.add_parser('self-test', help='Run compiler on itself as test')

    # -- post-commit --
    p_hook = sub.add_parser('post-commit',
                            help='Git hook: regenerate manifests + audit')
    p_hook.add_argument('root', nargs='?', default='.')

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    root = Path(args.root if hasattr(args, 'root') else '.').resolve()
    if not root.is_dir():
        print(f'Error: {root} is not a directory', file=sys.stderr)
        return 1

    if args.command == 'init':
        return _cmd_init(root, args.dry_run)
    elif args.command == 'rename':
        return _cmd_rename(root, not args.execute, args.intent)
    elif args.command == 'manifest':
        return _cmd_manifest(root, args.dry_run)
    elif args.command == 'audit':
        return _cmd_audit(root)
    elif args.command == 'validate':
        return _cmd_validate(root)
    elif args.command == 'heal':
        return _cmd_heal(root, args.full, args.dry_run)
    elif args.command == 'split':
        return _cmd_split(args.target, root, args.dry_run)
    elif args.command == 'glyph':
        return _cmd_glyph(root, not args.execute)
    elif args.command == 'install-hook':
        return _cmd_install_hook(root)
    elif args.command == 'self-test':
        return _cmd_self_test()
    elif args.command == 'post-commit':
        return _cmd_post_commit(root)

    return 0


def _cmd_init(root: Path, dry_run: bool) -> int:
    from pigeon_rename.scanner import scan_project
    from pigeon_rename.registry import (load_registry, save_registry,
                                        build_registry_from_scan)
    from pigeon_rename.manifest_builder import build_all_manifests

    print(f'Scanning {root} ...')
    catalog = scan_project(root)
    print(f'  Found {catalog["stats"]["total"]} Python files '
          f'in {catalog["stats"]["folders"]} folders')

    # Registry
    existing = load_registry(root)
    if existing:
        print(f'  Registry exists with {len(existing)} entries')
    else:
        entries = build_registry_from_scan(root, catalog)
        if not dry_run:
            save_registry(root, entries)
            print(f'  Created pigeon_registry.json ({len(entries)} entries)')
        else:
            print(f'  [dry-run] Would create registry with {len(entries)} entries')

    # Manifests
    results = build_all_manifests(root, dry_run=dry_run)
    wrote = sum(1 for r in results if r['wrote'])
    total_files = sum(r['files'] for r in results)
    if dry_run:
        print(f'  [dry-run] Would write {len(results)} MANIFEST.md files '
              f'covering {total_files} modules')
    else:
        print(f'  Wrote {wrote} MANIFEST.md files covering {total_files} modules')

    print('Done.')
    return 0


def _cmd_rename(root: Path, dry_run: bool, intent: str) -> int:
    from pigeon_rename.scanner import scan_project
    from pigeon_rename.planner import build_rename_plan
    from pigeon_rename.import_rewriter import rewrite_all_imports
    from pigeon_rename.executor import execute_rename
    from pigeon_rename.validator import validate_imports

    catalog = scan_project(root)
    plan = build_rename_plan(catalog, version=1, root=root, intent=intent)

    if not plan['renames']:
        print('All files already follow pigeon convention. Nothing to rename.')
        return 0

    print(f'Rename plan: {plan["stats"]["renames"]} files to rename')
    for r in plan['renames']:
        print(f'  {r["old"]} -> {r["new"]}')

    if dry_run:
        print(f'\n[dry-run] No files changed. Use --execute to apply.')
        return 0

    # Execute renames
    result = execute_rename(root, plan, dry_run=False)
    print(f'Renamed {result["renamed"]} files. Rollback log: {result.get("log")}')

    # Rewrite imports
    rewrites = rewrite_all_imports(root, plan['import_map'], dry_run=False)
    print(f'Rewrote imports in {rewrites["files_modified"]} files')

    # Validate
    validation = validate_imports(root)
    if validation['valid']:
        print('All imports validated successfully.')
    else:
        print(f'WARNING: {len(validation["broken"])} broken imports found!')
        for b in validation['broken'][:10]:
            print(f'  {b["file"]}:{b["line"]} -> {b["module"]}')
        return 1

    return 0


def _cmd_manifest(root: Path, dry_run: bool) -> int:
    from pigeon_rename.manifest_builder import build_all_manifests

    results = build_all_manifests(root, dry_run=dry_run)
    wrote = sum(1 for r in results if r['wrote'])
    total_files = sum(r['files'] for r in results)

    if dry_run:
        print(f'[dry-run] Would write {len(results)} MANIFEST.md files '
              f'covering {total_files} modules')
        for r in results:
            print(f'  {r["folder"]}/ ({r["files"]} files)')
    else:
        print(f'Wrote {wrote} MANIFEST.md files covering {total_files} modules')
        for r in results:
            print(f'  {r["folder"]}/ ({r["files"]} files)')

    return 0


def _cmd_audit(root: Path) -> int:
    from pigeon_rename.compliance import audit_compliance, format_report

    audit = audit_compliance(root)
    print(format_report(audit))
    return 0 if not audit['oversize'] else 1


def _cmd_validate(root: Path) -> int:
    from pigeon_rename.validator import validate_imports

    result = validate_imports(root)
    print(f'Checked {result["total_checked"]} internal imports')
    if result['valid']:
        print('All imports resolve correctly.')
        return 0
    else:
        print(f'{len(result["broken"])} broken imports:')
        for b in result['broken']:
            print(f'  {b["file"]}:{b["line"]} -> {b["module"]}')
        return 1


def _cmd_heal(root: Path, full: bool, dry_run: bool) -> int:
    """Self-healing pipeline: rebuild manifests for changed files."""
    from pigeon_rename.heal import heal, heal_report_text

    mode = 'full' if full else 'incremental'
    print(f'Running heal ({mode})...')

    report = heal(root, full=full, dry_run=dry_run)
    print(heal_report_text(report))

    if dry_run:
        print('[dry-run] No files written.')

    return 0 if not report['compliance'].get('critical') else 1


def _cmd_split(target: str | None, root: Path, dry_run: bool) -> int:
    """Split oversized files into compliant chunks."""
    from pigeon_rename.split import scan_oversized, split_file, split_all_oversized

    if target:
        # Split specific file
        target_path = Path(target)
        if not target_path.exists():
            target_path = root / target
        if not target_path.exists():
            print(f'Error: file not found: {target}', file=sys.stderr)
            return 1

        print(f'Splitting: {target_path}')
        result = split_file(target_path, dry_run=dry_run)

        if result.get('files_created', 0) == 0:
            msg = result.get('message', result.get('error', 'unable to split'))
            print(f'  {msg}')
            return 0

        print(f'  Created {result["files_created"]} chunks:')
        for f in result.get('files', []):
            status = '✓' if f.get('compliant') else '⚠️'
            print(f'    {status} {f["file"]} ({f["lines"]} lines)')

        if dry_run:
            print('[dry-run] No files written.')
        return 0

    # Scan all
    print(f'Scanning for oversized files in {root}...')
    oversized = scan_oversized(root)

    if not oversized:
        print('All files compliant. Nothing to split.')
        return 0

    print(f'Found {len(oversized)} oversized file(s):')
    for item in oversized:
        print(f'  {item["path"]} ({item["lines"]} lines, +{item["excess"]})')

    results = split_all_oversized(root, dry_run=dry_run)

    if results['split'] == 0:
        print('\nNo files were split (items too large or no splittable items).')
    else:
        print(f'\nSplit {results["split"]}/{results["scanned"]} files → {results["files_created"]} chunks.')

    if dry_run:
        print('[dry-run] No files written.')

    return 0


def _cmd_post_commit(root: Path) -> int:
    """Git hook entry point: regenerate manifests + run audit."""
    from pigeon_rename.manifest_builder import build_all_manifests
    from pigeon_rename.compliance import audit_compliance

    # Manifests
    results = build_all_manifests(root, dry_run=False)
    total_files = sum(r['files'] for r in results)
    print(f'pigeon: updated {len(results)} manifests ({total_files} modules)')

    # Quick compliance check
    audit = audit_compliance(root)
    if audit['oversize']:
        print(f'pigeon: {len(audit["oversize"])} files over {PIGEON_MAX} lines')
        for entry in audit['oversize'][:5]:
            print(f'  {entry["status"]}: {entry["path"]} ({entry["lines"]} lines)')
    else:
        print(f'pigeon: all {audit["total"]} files compliant')

    return 0


def _cmd_glyph(root: Path, dry_run: bool) -> int:
    """Rename files to semantic glyph convention."""
    from pigeon_rename.glyph import scan_for_glyph_candidates
    from pigeon_rename.import_rewriter import rewrite_all_imports
    from pigeon_rename.executor import execute_rename

    print(f'Scanning for glyph rename candidates in {root}...')
    candidates = scan_for_glyph_candidates(root)

    if not candidates:
        print('No files to glyph-rename. All mapped modules already renamed or no mappings.')
        return 0

    print(f'Found {len(candidates)} file(s) to glyph-rename:')
    for c in candidates:
        print(f'  {c["old"]} → {c["new"]}')
        print(f'    glyph: {c["glyph"]} ({c["meaning"]})')

    if dry_run:
        print('\n[dry-run] No files renamed. Use --execute to apply.')
        return 0

    # Build rename map
    rename_map = {}
    for c in candidates:
        old_path = root / c['path']
        new_path = old_path.parent / c['new']
        rename_map[str(old_path)] = str(new_path)

    # Execute renames
    result = execute_rename(rename_map)
    if result.get('error'):
        print(f'Error: {result["error"]}', file=sys.stderr)
        return 1

    # Rewrite imports
    rewrite_all_imports(root, rename_map)

    print(f'\nRenamed {len(candidates)} files to glyph convention.')
    return 0


def _cmd_install_hook(root: Path) -> int:
    """Install git post-commit hook for auto-pigeon."""
    git_dir = root / '.git'
    if not git_dir.is_dir():
        print(f'Error: {root} is not a git repository', file=sys.stderr)
        return 1

    hooks_dir = git_dir / 'hooks'
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / 'post-commit'

    hook_script = '''#!/bin/sh
# Pigeon Code Compiler — auto-generated post-commit hook
# Regenerates manifests + runs compliance audit on every commit
# By MyAIFingerprint — https://myaifingerprint.com

python -m pigeon_rename post-commit .
'''

    # Check for existing hook
    if hook_path.exists():
        existing = hook_path.read_text(encoding='utf-8', errors='ignore')
        if 'pigeon_rename' in existing:
            print('Pigeon hook already installed.')
            return 0
        # Append to existing hook
        print('Appending to existing post-commit hook...')
        with open(hook_path, 'a', encoding='utf-8') as f:
            f.write('\n# Pigeon Code Compiler\n')
            f.write('python -m pigeon_rename post-commit .\n')
    else:
        hook_path.write_text(hook_script, encoding='utf-8')

    # Make executable (Unix)
    try:
        import os
        os.chmod(hook_path, 0o755)
    except Exception:
        pass

    print(f'Installed post-commit hook: {hook_path}')
    print('Pigeon will now run automatically on every commit.')
    return 0


def _cmd_self_test() -> int:
    """Run the compiler on itself as a test."""
    import pigeon_rename
    root = Path(pigeon_rename.__file__).parent

    print('=' * 60)
    print('PIGEON SELF-TEST — Running compiler on pigeon_rename/')
    print('=' * 60)

    # 1. Scan
    print('\n[1/5] Scanning project...')
    from pigeon_rename.scanner import scan_project
    catalog = scan_project(root.parent, folders=['pigeon_rename'])
    stats = catalog.get('stats', {})
    print(f'  Found {len(catalog["files"])} files in {stats.get("folders", 1)} folders')

    # 2. Audit compliance
    print('\n[2/5] Checking compliance...')
    from pigeon_rename.compliance import audit_compliance
    audit = audit_compliance(root)
    compliant = audit['total'] - len(audit['oversize'])
    pct = (compliant / audit['total'] * 100) if audit['total'] else 100
    print(f'  {compliant}/{audit["total"]} compliant ({pct:.0f}%)')
    if audit['oversize']:
        print(f'  ⚠️  {len(audit["oversize"])} files over {PIGEON_MAX} lines')

    # 3. Validate imports
    print('\n[3/5] Validating imports...')
    from pigeon_rename.validator import validate_imports
    validation = validate_imports(root)
    if validation['broken']:
        print(f'  ⚠️  {len(validation["broken"])} broken imports')
    else:
        print(f'  ✓ All {validation["total_checked"]} imports valid')

    # 4. Check glyph candidates
    print('\n[4/5] Checking glyph readiness...')
    from pigeon_rename.glyph import scan_for_glyph_candidates
    candidates = scan_for_glyph_candidates(root)
    if candidates:
        print(f'  {len(candidates)} files ready for glyph rename')
    else:
        print('  ✓ All modules glyph-ready or already renamed')

    # 5. Summary
    print('\n[5/5] Self-test complete.')
    print('=' * 60)

    issues = len(audit['oversize']) + len(validation.get('broken', []))
    if issues:
        print(f'RESULT: {issues} issue(s) found')
        return 1
    else:
        print('RESULT: All checks passed ✓')
        return 0


# Allow `python -m pigeon_rename` to work
PIGEON_MAX = 200  # for the post-commit print


if __name__ == '__main__':
    sys.exit(main() or 0)
