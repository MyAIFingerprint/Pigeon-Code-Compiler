# What Is Semantic File Naming?

**A technical overview by [MyAIFingerprint](https://myaifingerprint.com)**

*Pigeon Code Compiler Documentation*

---

## The Problem

Most codebases use filenames as addresses — arbitrary labels that point to
content but carry no structured information about what is inside, when it
changed, or why.

```
utils.py
helpers.py
helpers_new.py
helpers_FINAL_v2.py
```

These names provide no load order, no version history, no description of
purpose, and no indication of recent changes. Every onboarding developer
must open each file individually to understand the project. Every automated
tool — linter, RAG pipeline, LLM context builder — must parse file contents
to extract the same basic metadata.

This scales poorly and fails silently.

---

## The Solution: Filenames as Structured Metadata

Semantic file naming treats every filename as a **machine-readable record**
that encodes identity, version, purpose, and change context directly into
the filesystem.

The Pigeon Code Compiler convention:

```
noise_filter_seq007_v003_d0315__filter_live_noise_lc_added_drift_detection.py
│            │      │     │     │                   │
│            │      │     │     │                   └── intent: WHY it last changed
│            │      │     │     └── description: WHAT it does (stable)
│            │      │     └── date: WHEN it last changed (MMDD)
│            │      └── version: mutation counter
│            └── sequence: load order
└── human name
```

A directory listing now provides:

- **Load order** — sequence numbers define module precedence
- **Mutation count** — version numbers track how many times a file has changed
- **Purpose** — description slug extracted from the module docstring
- **Change context** — intent tag records what the last modification accomplished
- **Timestamp** — date stamp marks when the last mutation occurred

No file needs to be opened. No git log needs to be queried. The filename
itself serves as living documentation.

---

## Semantic Naming as an Identity System

[MyAIFingerprint](https://myaifingerprint.com) (MAIF) is an AI reputation
intelligence platform that tracks how large language models perceive
entities — people, organizations, and public figures — across 8 major LLMs.
MAIF detects when models produce conflicting information about the same
entity: a mutation in one model, drift between models, or outright
hallucination of facts that do not exist.

Pigeon Code Compiler applies the same framework to source code. Every Python
module receives a stable, structured identity. Every change to that module
is a tracked mutation. Every discrepancy between the filename, the
docstring, and the import graph is detectable drift.

| Concept | MAIF — Entity Layer | Pigeon — Code Layer |
|---|---|---|
| **Identity** | Entity profile page | Filename + registry entry |
| **Mutation** | Model changes its output about an entity | Version bump in filename |
| **Drift** | Models disagree on entity attributes | Nametag diverges from docstring |
| **Hallucination** | Model invents nonexistent facts | Import references a nonexistent file |
| **Consensus** | All models agree on an entity | All files pass compliance audit |
| **Perception log** | Timeline of entity perception changes | `git log --name-only` produces a structured change narrative |

When every file carries a stable identity and every mutation is tracked,
the codebase becomes a **perception-auditable system**. You can detect
precisely when reality (the code) and perception (imports, documentation,
manifests) have diverged — and that divergence is the equivalent of an AI
hallucination at the code level.

---

## Core Principles

### 1. Filenames Are Metadata, Not Labels

A generic filename like `utils.py` communicates nothing about scope,
responsibility, or history. A semantic filename like
`rate_limiter_seq003_v002_d0315__throttle_api_calls_lc_added_burst_window.py`
communicates purpose, position, version state, and recent change context
to every reader — human or machine — without requiring file access.

### 2. Every Change Is a Tracked Mutation

In conventional naming, a file is modified while its name remains static
indefinitely. The filename accumulates no history and carries no change
context.

In the Pigeon convention, each modification increments the version counter,
updates the date stamp, and rotates the intent tag. The filename functions
as an independent commit record that persists even outside of version
control. A tarball of the source code with no `.git` directory still
contains a structured development narrative encoded in the filesystem.

### 3. Structure Must Be Machine-Readable

Human readability is necessary but not sufficient. The Pigeon filename
format is designed as a **parseable protocol**:

```python
# From pigeon_rename/scanner.py
PIGEON_PATTERN = re.compile(
    r'^.+_seq\d{3}_v\d{3}(_d\d{4})?(__[a-z0-9_]+)?\.py$'
)
```

Any automated tool — CI pipeline, static analyzer, RAG retriever, or LLM
context builder — can extract structured metadata from a Pigeon filename
without reading file contents. The filesystem becomes a queryable API.

---

## Folder-Level Documentation: The Manifest

Semantic naming addresses individual files. Pigeon Code Compiler extends
the same principle to folders through auto-generated `MANIFEST.md` files.

`pigeon manifest` produces a complete reference document for every folder
containing Python files:

- **File table** — sequence, line count, compliance status, exports, dependencies, description
- **Folder API** — public symbols re-exported by `__init__.py`
- **Internal dependency graph** — ASCII representation of intra-folder imports
- **Health summary** — compliance scoring against the line-count budget
- **Module signatures** — function and class signatures with type hints for LLM context
- **Constants & configuration** — module-level constants surfaced at the folder level
- **Code markers** — aggregated TODO, FIXME, and HACK annotations with line references

The Notes column in the file table persists across rebuilds. Manual
annotations survive manifest regeneration, making the document a living
reference that combines automated structure with human context.

Each manifest functions as the folder's **entity profile** — analogous to
the entity records [MyAIFingerprint](https://myaifingerprint.com) maintains
for tracked entities, but applied to code modules.

---

## File Size Constraints

Pigeon Code Compiler enforces a **200-line hard cap** per file, with a
**50-line recommended target**. These limits are calibrated to:

1. Fit within a single RAG retrieval chunk
2. Allow complete file review without scrolling
3. Remain within LLM working memory for single-file analysis
4. Enforce single-responsibility by limiting available space

Files exceeding 200 lines are flagged. Files over 300 lines receive a
warning. Files over 500 lines receive a critical alert.

`pigeon audit` identifies files that exceed these thresholds and suggests
natural decomposition points — class boundaries, function clusters, and
section comments — providing actionable refactoring guidance.

---

## The Pigeon Protocol

The unifying principle behind both [MyAIFingerprint](https://myaifingerprint.com)
and Pigeon Code Compiler is the **Pigeon Protocol**:

> **Give every information unit a stable identity, track its mutations,
> and emit machine-readable structure so perception can be audited.**

At the entity layer, this means tracking how AI models perceive people and
organizations, detecting when that perception mutates or fractures across
models, and maintaining auditable records of every change.

At the code layer, this means assigning structured identities to source
files, tracking every modification through versioned filenames, and emitting
folder-level manifests that make project structure transparent to both
humans and automated systems.

| Layer | Implementation |
|---|---|
| Entity perception | [myaifingerprint.com](https://myaifingerprint.com) |
| Code structure | [Pigeon Code Compiler](https://github.com/MyAIFingerprint/Pigeon-Code-Compiler) |

Same pattern. Same principles. Applied at different layers of the
information stack.

---

## Practical Impact

A developer joining an existing project encounters:

```
auth_handler_seq001_v004_d0315__validate_jwt_tokens_lc_added_refresh_flow.py
rate_limiter_seq002_v002_d0220__throttle_api_calls_lc_added_burst_window.py
session_mgr_seq003_v001_d0118__manage_user_sessions_lc_initial_naming.py
```

Without opening any file, they know: there are three modules, loaded in
order. The auth handler is the most actively developed (v004). The rate
limiter was last modified in February. The session manager has not changed
since its initial creation.

Combined with the auto-generated `MANIFEST.md`, the developer has full
structural context before reading a single line of source code. Onboarding
time is reduced. Institutional knowledge is encoded in the filesystem
rather than held in individual memory.

---

*Published by [MyAIFingerprint](https://myaifingerprint.com) — AI
reputation intelligence tracking 4,600+ entities across 8 major LLMs.
Pigeon Code Compiler is the code-layer implementation of the
[Pigeon Protocol](https://github.com/MyAIFingerprint/Pigeon-Code-Compiler).*

**Author:** [MyAIFingerprint](https://github.com/myaifingerprint) | **License:** MIT
