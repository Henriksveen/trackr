# Graph Report - .  (2026-06-15)

## Corpus Check
- Corpus is ~5,074 words - fits in a single context window. You may not need a graph.

## Summary
- 151 nodes · 364 edges · 12 communities (8 shown, 4 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 73 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_CLI Test Suite|CLI Test Suite]]
- [[_COMMUNITY_Status & Aliases|Status & Aliases]]
- [[_COMMUNITY_App Entry & Repo Discovery|App Entry & Repo Discovery]]
- [[_COMMUNITY_Task Model & Persistence|Task Model & Persistence]]
- [[_COMMUNITY_Init & Error Handling|Init & Error Handling]]
- [[_COMMUNITY_Architecture & CLI Commands|Architecture & CLI Commands]]
- [[_COMMUNITY_Test Fixtures|Test Fixtures]]
- [[_COMMUNITY_ID Generation|ID Generation]]
- [[_COMMUNITY_User-Facing Commands Docs|User-Facing Commands Docs]]
- [[_COMMUNITY_Feature Overview Docs|Feature Overview Docs]]
- [[_COMMUNITY_Schema Reference|Schema Reference]]

## God Nodes (most connected - your core abstractions)
1. `Task` - 25 edges
2. `invoke()` - 25 edges
3. `Status` - 20 edges
4. `NotInitialized` - 14 edges
5. `CorruptState` - 13 edges
6. `load_tasks()` - 13 edges
7. `_state()` - 11 edges
8. `_first_id()` - 11 edges
9. `find_repo_root()` - 10 edges
10. `save_tasks()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `AGENTS.md - Atomic Writes` --references--> `save_tasks`  [INFERRED]
  AGENTS.md → src/trackr/storage.py
- `AGENTS.md - ID Generation` --references--> `generate_id`  [INFERRED]
  AGENTS.md → src/trackr/storage.py
- `README.md - Features` --semantically_similar_to--> `Usage Guide - Mental Model`  [INFERRED] [semantically similar]
  README.md → docs/usage.md
- `README.md - Commands` --semantically_similar_to--> `Usage Guide - Commands`  [INFERRED] [semantically similar]
  README.md → docs/usage.md
- `Path` --uses--> `NotInitialized`  [INFERRED]
  tests/test_storage.py → src/trackr/errors.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Layered Persistence Flow: CLI → Storage → Models** — cli_add_command, storage_load_tasks, storage_save_tasks, models_Task [EXTRACTED 1.00]
- **Status Input Coercion: Input → Aliases → Canonical** — models_Status, models_ALIASES, errors_InvalidStatus [EXTRACTED 1.00]
- **Error Handling: Exception → Handler → User Message** — errors_TrackrError, cli_handle_errors, errors_NotInitialized [EXTRACTED 1.00]

## Communities (12 total, 4 thin omitted)

### Community 0 - "CLI Test Suite"
Cohesion: 0.16
Nodes (12): invoke(), _first_id(), _ids(), Path, _state(), TestAdd, TestInit, TestList (+4 more)

### Community 1 - "Status & Aliases"
Cohesion: 0.13
Nodes (9): Enum, _ALIASES, Status, str, TestStatusCoerce, TestTaskSerde, InvalidStatus, Status (+1 more)

### Community 2 - "App Entry & Repo Discovery"
Cohesion: 0.13
Nodes (10): __version__, app, TestFindRepoRoot, TestFindTask, init(), list_tasks(), remove(), status() (+2 more)

### Community 3 - "Task Model & Persistence"
Cohesion: 0.26
Nodes (12): Path, Task, Path, TestInit, TestLoadSave, CorruptState, init_store(), load_tasks() (+4 more)

### Community 4 - "Init & Error Handling"
Cohesion: 0.17
Nodes (10): init command, Exception, init_store, TestInit (storage), add(), AlreadyInitialized, EmptyDescription, NotInitialized (+2 more)

### Community 5 - "Architecture & CLI Commands"
Cohesion: 0.23
Nodes (14): AGENTS.md - Architecture, AGENTS.md - TDD Rule, AGENTS.md - Atomic Writes, AGENTS.md - ID Generation, add command, handle_errors, list command, remove command (+6 more)

### Community 6 - "Test Fixtures"
Cohesion: 0.33
Nodes (6): CliRunner, MonkeyPatch, initialized(), Path, runner(), workdir()

## Knowledge Gaps
- **10 isolated node(s):** `MonkeyPatch`, `__version__`, `_ALIASES`, `TestInit (storage)`, `AGENTS.md - TDD Rule` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Task` connect `Status & Aliases` to `App Entry & Repo Discovery`, `Task Model & Persistence`, `Architecture & CLI Commands`, `ID Generation`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Why does `invoke()` connect `CLI Test Suite` to `Test Fixtures`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `Status` connect `Status & Aliases` to `App Entry & Repo Discovery`, `Task Model & Persistence`, `Architecture & CLI Commands`, `ID Generation`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `Task` (e.g. with `Path` and `Status`) actually correct?**
  _`Task` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `invoke()` (e.g. with `.test_add_persists_task()` and `.test_description_is_trimmed()`) actually correct?**
  _`invoke()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `Status` (e.g. with `InvalidStatus` and `Status`) actually correct?**
  _`Status` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `NotInitialized` (e.g. with `Path` and `init_store`) actually correct?**
  _`NotInitialized` has 9 INFERRED edges - model-reasoned connections that need verification._