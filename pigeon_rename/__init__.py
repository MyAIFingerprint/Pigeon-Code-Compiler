"""Pigeon Code Compilor — Pigeon Protocol for source code.

Semantic structure, mutation tracking, and drift detection
for Python codebases. Renames files to carry identity metadata,
rewrites imports atomically, generates MANIFEST.md per folder,
and tracks version history in a JSON registry.

    pip install pigeon-code-compilor
    pigeon init .
    pigeon manifest .
    pigeon rename . --dry-run

By MyAIFingerprint — https://myaifingerprint.com
"""

from pigeon_rename.scanner import scan_project
from pigeon_rename.planner import build_rename_plan
from pigeon_rename.import_rewriter import rewrite_all_imports
from pigeon_rename.executor import execute_rename, rollback_rename
from pigeon_rename.validator import validate_imports
from pigeon_rename.manifest_builder import build_manifest, build_all_manifests
from pigeon_rename.compliance import audit_compliance, check_file
from pigeon_rename.nametag import (
    extract_desc_slug, build_nametag, parse_nametag,
    detect_drift, scan_drift, slugify,
)
from pigeon_rename.registry import (
    load_registry, save_registry, build_registry_from_scan,
    build_pigeon_filename, parse_pigeon_stem,
    bump_version, bump_all_versions,
)
from pigeon_rename.limits import PIGEON_MAX, PIGEON_RECOMMENDED, is_excluded

__version__ = "0.1.0"

__all__ = [
    "scan_project",
    "build_rename_plan",
    "rewrite_all_imports",
    "execute_rename",
    "rollback_rename",
    "validate_imports",
    "build_manifest",
    "build_all_manifests",
    "audit_compliance",
    "check_file",
    "extract_desc_slug",
    "build_nametag",
    "parse_nametag",
    "detect_drift",
    "scan_drift",
    "slugify",
    "load_registry",
    "save_registry",
    "build_registry_from_scan",
    "build_pigeon_filename",
    "parse_pigeon_stem",
    "bump_version",
    "bump_all_versions",
    "PIGEON_MAX",
    "PIGEON_RECOMMENDED",
    "is_excluded",
]
