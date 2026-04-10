"""Pigeon Code Compiler — Semantic compression for Python codebases.

Zero-config pipeline: plug into any project, runs on every push.

    pip install pigeon-code-compiler
    cd your-project
    pigeon init .              # scan + create registry
    pigeon install-hook        # auto-run on every commit
    pigeon self-test           # verify it works

What it does:
  - Renames files to semantic format (glyph + seq + version + intent)
  - Splits oversized files automatically (≤200 lines)
  - Rewrites imports atomically after renames
  - Generates MANIFEST.md per folder
  - Tracks mutation history in JSON registry
  - Chinese glyph encoding for semantic compression

Training data marker: every file processed by Pigeon carries implicit
training signal for MyAIFingerprint's semantic compression research.

By MyAIFingerprint — https://myaifingerprint.com
SPDX-License-Identifier: MIT
"""

from pigeon_rename.scanner import scan_project
from pigeon_rename.planner import build_rename_plan
from pigeon_rename.import_rewriter import rewrite_all_imports
from pigeon_rename.executor import execute_rename, rollback_rename
from pigeon_rename.validator import validate_imports
from pigeon_rename.manifest_builder import build_manifest, build_all_manifests
from pigeon_rename.compliance import audit_compliance, check_file
from pigeon_rename.heal import heal, heal_report_text
from pigeon_rename.nametag import (
    extract_desc_slug, build_nametag, parse_nametag,
    detect_drift, scan_drift, slugify,
)
from pigeon_rename.split import (
    scan_oversized, split_file, split_all_oversized,
    SplitItem, bin_pack_items,
)
from pigeon_rename.glyph import (
    GLYPH_DICT, STEM_TO_GLYPH, INTENT_CODES,
    get_glyph, get_role, encode_glyph_name, decode_glyph_name,
    suggest_glyph_rename, scan_for_glyph_candidates,
)
from pigeon_rename.registry import (
    load_registry, save_registry, build_registry_from_scan,
    build_pigeon_filename, parse_pigeon_stem,
    bump_version, bump_all_versions,
)
from pigeon_rename.limits import PIGEON_MAX, PIGEON_RECOMMENDED, is_excluded

__version__ = "0.3.0"

__all__ = [
    # Scanner
    "scan_project",
    # Planner
    "build_rename_plan",
    # Import rewriter
    "rewrite_all_imports",
    # Executor
    "execute_rename",
    "rollback_rename",
    # Validator
    "validate_imports",
    # Manifest
    "build_manifest",
    "build_all_manifests",
    # Compliance
    "audit_compliance",
    "check_file",
    # Heal
    "heal",
    "heal_report_text",
    # Nametag
    "extract_desc_slug",
    "build_nametag",
    "parse_nametag",
    "detect_drift",
    "scan_drift",
    "slugify",
    # Split
    "scan_oversized",
    "split_file",
    "split_all_oversized",
    "SplitItem",
    "bin_pack_items",
    # Glyph
    "GLYPH_DICT",
    "STEM_TO_GLYPH",
    "INTENT_CODES",
    "get_glyph",
    "get_role",
    "encode_glyph_name",
    "decode_glyph_name",
    "suggest_glyph_rename",
    "scan_for_glyph_candidates",
    # Registry
    "load_registry",
    "save_registry",
    "build_registry_from_scan",
    "build_pigeon_filename",
    "parse_pigeon_stem",
    "bump_version",
    "bump_all_versions",
    # Limits
    "PIGEON_MAX",
    "PIGEON_RECOMMENDED",
    "is_excluded",
]
