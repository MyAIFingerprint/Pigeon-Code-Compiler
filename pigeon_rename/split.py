"""pigeon_rename.split — Deterministic file splitting without LLM.

Splits oversized Python files into compliant chunks using AST analysis.
No external dependencies, no LLM calls — pure deterministic decomposition.

Usage:
    from pigeon_rename import split_file, scan_oversized
    
    # Find files over the limit
    oversized = scan_oversized(Path('.'))
    
    # Split a single file
    result = split_file(Path('big_module.py'), dry_run=True)
"""
import ast
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from pigeon_rename.limits import PIGEON_MAX, PIGEON_RECOMMENDED

MAX_SPLIT_ROUNDS = 5


@dataclass
class SplitItem:
    """A unit that can be moved between files."""
    name: str
    kind: str  # 'function', 'class', 'constant'
    start_line: int
    end_line: int
    lines: int
    source: str
    dependencies: List[str]  # names this item references


def scan_oversized(root: Path, threshold: int = PIGEON_MAX) -> List[dict]:
    """Find all Python files exceeding the line threshold.
    
    Returns list of {path, lines, excess} dicts.
    """
    skip = {'.venv', '__pycache__', 'node_modules', '.git', 'build'}
    oversized = []
    
    for py in sorted(root.rglob('*.py')):
        parts = py.relative_to(root).parts
        if any(p in skip or p.startswith('.') for p in parts):
            continue
        if py.name == '__init__.py':
            continue
        try:
            lines = len(py.read_text(encoding='utf-8').splitlines())
        except Exception:
            continue
        if lines > threshold:
            oversized.append({
                'path': str(py.relative_to(root)),
                'lines': lines,
                'excess': lines - threshold,
            })
    
    return oversized


def extract_items(source: str) -> List[SplitItem]:
    """Extract all top-level functions, classes, and constants from source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    lines = source.splitlines()
    items = []
    
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            items.append(_node_to_item(node, lines, 'function'))
        elif isinstance(node, ast.ClassDef):
            items.append(_node_to_item(node, lines, 'class'))
        elif isinstance(node, ast.Assign):
            # Top-level constant assignment
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    items.append(_node_to_item(node, lines, 'constant'))
                    break
    
    return items


def _node_to_item(node: ast.AST, lines: List[str], kind: str) -> SplitItem:
    """Convert an AST node to a SplitItem."""
    start = node.lineno - 1  # 0-indexed
    end = node.end_lineno or node.lineno
    
    # Get name
    if isinstance(node, ast.Assign):
        name = node.targets[0].id if isinstance(node.targets[0], ast.Name) else 'CONST'
    else:
        name = getattr(node, 'name', 'unknown')
    
    # Extract source lines
    source = '\n'.join(lines[start:end])
    
    # Find dependencies (names referenced)
    deps = _find_dependencies(node)
    
    return SplitItem(
        name=name,
        kind=kind,
        start_line=start + 1,
        end_line=end,
        lines=end - start,
        source=source,
        dependencies=deps,
    )


def _find_dependencies(node: ast.AST) -> List[str]:
    """Find all names referenced in a node."""
    deps = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            deps.add(child.id)
        elif isinstance(child, ast.Attribute):
            if isinstance(child.value, ast.Name):
                deps.add(child.value.id)
    return list(deps)


def bin_pack_items(items: List[SplitItem], 
                   max_lines: int = PIGEON_RECOMMENDED) -> List[List[SplitItem]]:
    """Pack items into bins that fit under the line limit.
    
    Uses first-fit decreasing algorithm.
    """
    if not items:
        return []
    
    # Sort by lines descending
    sorted_items = sorted(items, key=lambda x: x.lines, reverse=True)
    
    bins: List[List[SplitItem]] = []
    bin_sizes: List[int] = []
    
    for item in sorted_items:
        # Try to fit in existing bin
        placed = False
        for i, size in enumerate(bin_sizes):
            if size + item.lines <= max_lines:
                bins[i].append(item)
                bin_sizes[i] += item.lines
                placed = True
                break
        
        if not placed:
            # Create new bin
            bins.append([item])
            bin_sizes.append(item.lines)
    
    return bins


def split_file(source_path: Path, 
               target_dir: Path = None,
               dry_run: bool = False) -> dict:
    """Split an oversized file into compliant chunks.
    
    Args:
        source_path: Path to the oversized .py file
        target_dir: Output directory (default: same as source)
        dry_run: If True, compute but don't write
        
    Returns:
        {files_created: int, total_lines: int, files: []}
    """
    source_path = Path(source_path)
    if not source_path.exists():
        return {'error': 'file not found', 'files_created': 0}
    
    target_dir = target_dir or source_path.parent
    stem = source_path.stem
    
    # Strip existing seq/ver suffix for base name
    base_stem = re.sub(r'_seq\d{3}_v\d{3}.*$', '', stem)
    
    try:
        source = source_path.read_text(encoding='utf-8')
    except Exception as e:
        return {'error': str(e), 'files_created': 0}
    
    lines = source.splitlines()
    if len(lines) <= PIGEON_MAX:
        return {'files_created': 0, 'message': 'file already compliant'}
    
    # Extract top-level items
    items = extract_items(source)
    if not items:
        return {'files_created': 0, 'message': 'no splittable items found'}
    
    # Extract header (imports + module docstring)
    header = _extract_header(source)
    header_lines = len(header.splitlines()) if header else 0
    
    # Adjust max lines per bin for header
    effective_max = PIGEON_RECOMMENDED - header_lines - 5  # 5 for safety margin
    
    # Pack items into bins
    bins = bin_pack_items(items, max_lines=effective_max)
    
    if len(bins) <= 1:
        return {'files_created': 0, 'message': 'cannot split further'}
    
    # Generate output files
    created = []
    for i, bin_items in enumerate(bins, 1):
        filename = f'{base_stem}_seq{i:03d}_v001.py'
        filepath = target_dir / filename
        
        # Build file content
        parts = [header] if header else []
        for item in bin_items:
            parts.append(item.source)
        
        content = '\n\n'.join(parts) + '\n'
        file_lines = len(content.splitlines())
        
        if not dry_run:
            filepath.write_text(content, encoding='utf-8')
        
        created.append({
            'file': filename,
            'lines': file_lines,
            'items': [it.name for it in bin_items],
            'compliant': file_lines <= PIGEON_MAX,
        })
    
    # Write __init__.py to re-export everything
    if not dry_run:
        _write_split_init(target_dir, base_stem, created)
    
    return {
        'files_created': len(created),
        'total_lines': sum(f['lines'] for f in created),
        'files': created,
        'dry_run': dry_run,
    }


def _extract_header(source: str) -> str:
    """Extract imports and module docstring from source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ''
    
    lines = source.splitlines()
    header_end = 0
    
    # Find module docstring
    if (tree.body and isinstance(tree.body[0], ast.Expr) and
            isinstance(tree.body[0].value, ast.Constant)):
        header_end = tree.body[0].end_lineno or 0
    
    # Find last import
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            header_end = max(header_end, node.end_lineno or node.lineno)
    
    if header_end == 0:
        return ''
    
    return '\n'.join(lines[:header_end])


def _write_split_init(target_dir: Path, base_stem: str, created: List[dict]) -> None:
    """Write __init__.py that re-exports from split files."""
    init_path = target_dir / '__init__.py'
    
    # If splitting into same directory, skip init
    if any(f['file'].startswith(base_stem) for f in created):
        # Generate imports
        imports = []
        exports = []
        
        for f in created:
            mod_name = Path(f['file']).stem
            for item in f['items']:
                imports.append(f'from .{mod_name} import {item}')
                exports.append(item)
        
        content = f'"""{base_stem} — split into {len(created)} compliant modules."""\n\n'
        content += '\n'.join(imports)
        content += f'\n\n__all__ = {exports!r}\n'
        
        init_path.write_text(content, encoding='utf-8')


def split_all_oversized(root: Path, dry_run: bool = False) -> dict:
    """Split all oversized files in a project.
    
    Returns summary dict.
    """
    oversized = scan_oversized(root)
    results = []
    
    for entry in oversized:
        py = root / entry['path']
        result = split_file(py, dry_run=dry_run)
        result['source'] = entry['path']
        results.append(result)
    
    return {
        'scanned': len(oversized),
        'split': sum(1 for r in results if r.get('files_created', 0) > 0),
        'files_created': sum(r.get('files_created', 0) for r in results),
        'results': results,
    }
