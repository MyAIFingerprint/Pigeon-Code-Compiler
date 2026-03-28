# Pigeon Code Compiler

**Pigeon Protocol for source code. Semantic structure, mutation tracking, and drift detection for Python codebases.**

[MyAIFingerprint](https://myaifingerprint.com) tracks how AI models perceive entities — detecting mutations, hallucinations, and consensus fractures across LLMs. Pigeon Code Compiler applies the same philosophy to source code: every file carries an identity, every change is a tracked mutation, and every folder emits a machine-readable manifest so both humans and AI systems can see what your code actually is.

```
noise_filter_seq007_v003_d0315__filter_live_noise_lc_added_drift_detection.py
│            │      │     │     │                   │
│            │      │     │     │                   └── intent: WHY it was last changed
│            │      │     │     └── description: WHAT it does (stable)
│            │      │     └── date: WHEN it was last changed (MMDD)
│            │      └── version: mutation counter
│            └── sequence: load order
└── human name
```

Zero dependencies. Pure stdlib. Python 3.10+.

## Install

```bash
pip install pigeon-code-compiler
```

## Quick Start

```bash
pigeon init /path/to/project        # Scan, register identities, emit manifests
pigeon audit /path/to/project       # Compliance audit — flag oversized files
pigeon rename /path/to/project --dry-run   # Preview structural renames
pigeon rename /path/to/project --execute   # Execute renames + rewrite imports
pigeon manifest /path/to/project    # Regenerate all MANIFEST.md files
pigeon validate /path/to/project    # Validate all internal imports resolve
```

## What It Does

### `pigeon init`
Scans your project, creates a `pigeon_registry.json` tracking module identity and version history, and generates `MANIFEST.md` files for folders that contain Python code. This is the initial entity registration — the same way [MyAIFingerprint](https://myaifingerprint.com) registers a new entity before tracking its perception across models.

### `pigeon rename`
Renames plain Python files to the Pigeon convention. Automatically:
- Assigns sequence numbers (load order)
- Extracts description from docstrings
- Rewrites all `import` / `from` statements across your entire project
- Creates rollback logs in `.pigeon/` so you can undo

### `pigeon manifest`
Generates self-documenting `MANIFEST.md` for every folder containing Python files. Each manifest includes:
- **File table** with status, exports, dependencies, description
- **Folder API** (public symbols from `__init__.py`)
- **Internal dependency graph** (ASCII)
- **Health summary** (compliance scoring)
- **Module signatures** with type hints (LLM-readable context)
- **Constants & configuration** values
- **Code markers** (TODO/FIXME/HACK tracker)

Notes column is preserved across rebuilds — add context manually and it survives.

### `pigeon audit`
Line-count enforcer. Flags files over 200 lines and recommends natural split points (class boundaries, function clusters, section comments).

### `pigeon validate`
Checks that every internal import resolves to an actual file. Catches phantom imports after renames — the code-level equivalent of hallucination detection.

Current scope is intentionally conservative: straightforward internal imports are validated first, with edge cases documented as the tool matures.

### `pigeon post-commit`
Git hook entry point. Regenerates manifests and runs a quick audit on every commit.

```bash
# Windows PowerShell
Copy-Item hooks/post-commit .git/hooks/post-commit

# macOS / Linux
cp hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

## Pigeon Protocol

[MyAIFingerprint](https://myaifingerprint.com) runs cross-model consensus audits on entities — people, organizations, events — to detect how AI perception mutates over time. Pigeon Code Compiler is the same pattern applied to code:

| MAIF (Entity Layer) | Pigeon Code Compiler (Code Layer) |
|---|---|
| Entity registration | `pigeon init` — register module identities |
| Mutation detection | Version bumps tracked in `pigeon_registry.json` |
| Drift tracking | `detect_drift` / `scan_drift` on nametag consistency |
| Hallucination flags | `pigeon validate` — catch phantom imports |
| Consensus scoring | `pigeon audit` — compliance scoring across files |
| Perception timeline | Git history + versioned filenames = narrative log |
| Entity profile page | `MANIFEST.md` per folder — the module's public record |

The Pigeon Protocol is: **give every information unit a stable identity, track its mutations, and emit machine-readable structure so perception can be audited.**

At the entity level, that's [myaifingerprint.com](https://myaifingerprint.com). At the code level, that's this tool.

## The Philosophy

**200 lines hard cap per file.** 50 lines recommended.

LLMs read your code. Humans read your code. RAG pipelines retrieve your code. None of them benefit from 800-line monoliths with ambiguous filenames. Pigeon enforces file sizes that fit inside a working context window, then emits folder-level documentation automatically so structure survives growth.

Filenames are living metadata — they mutate on every change to carry the WHAT (description) and WHY (intent) directly in the filesystem. `git log --name-only` becomes a narrative.

## Configuration

Default limits in `pigeon_rename/limits.py`:

| Constant | Default | Meaning |
|----------|---------|---------|
| `PIGEON_MAX` | 200 | Hard cap — files over this are flagged |
| `PIGEON_RECOMMENDED` | 50 | Target — aim for this or smaller |

## Python API

```python
from pigeon_rename import (
    scan_project,
    build_rename_plan,
    execute_rename,
    rewrite_all_imports,
    validate_imports,
    build_manifest,
    build_all_manifests,
    audit_compliance,
    format_report,
    detect_drift,
    scan_drift,
)

# Scan + register
catalog = scan_project('/path/to/project')

# Audit compliance
audit = audit_compliance('/path/to/project')
print(format_report(audit))

# Generate manifests
results = build_all_manifests('/path/to/project')

# Drift detection
from pigeon_rename import scan_drift
drift_report = scan_drift('/path/to/project')
```

## About

Pigeon Code Compiler is built by [MyAIFingerprint](https://myaifingerprint.com) (MAIF), the AI reputation intelligence platform that tracks how LLMs perceive 4,600+ entities across 8 major models. This tool extends the MAIF philosophy — identity, traceability, and semantic structure — from entities into source code.

**Author:** [MyAIFingerprint](https://github.com/myaifingerprint) | **Site:** [myaifingerprint.com](https://myaifingerprint.com) | **License:** MIT
