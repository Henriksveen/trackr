# Graph Report - .  (2026-06-16)

## Corpus Check
- Corpus is ~13,207 words - fits in a single context window. You may not need a graph.

## Summary
- 343 nodes · 1105 edges · 19 communities (12 shown, 7 thin omitted)
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 259 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Storage & Persistence Layer|Storage & Persistence Layer]]
- [[_COMMUNITY_Task Domain Model|Task Domain Model]]
- [[_COMMUNITY_CLI Commands & Error Handling|CLI Commands & Error Handling]]
- [[_COMMUNITY_Dependency Linking Tests|Dependency Linking Tests]]
- [[_COMMUNITY_Tag & Filter Tests|Tag & Filter Tests]]
- [[_COMMUNITY_Status & Show Tests|Status & Show Tests]]
- [[_COMMUNITY_OpenCode Agent & Docs|OpenCode Agent & Docs]]
- [[_COMMUNITY_Error Classes|Error Classes]]
- [[_COMMUNITY_Init & Remove Tests|Init & Remove Tests]]
- [[_COMMUNITY_Add & Tag Tests|Add & Tag Tests]]
- [[_COMMUNITY_Topological Sort Tests|Topological Sort Tests]]
- [[_COMMUNITY_Test Fixtures|Test Fixtures]]
- [[_COMMUNITY_Feature Documentation|Feature Documentation]]
- [[_COMMUNITY_List Command Tests|List Command Tests]]
- [[_COMMUNITY_ID Generation|ID Generation]]
- [[_COMMUNITY_Remove Command Tests|Remove Command Tests]]
- [[_COMMUNITY_Unlink Tests|Unlink Tests]]
- [[_COMMUNITY_Task IDs|Task IDs]]

## God Nodes (most connected - your core abstractions)
1. `invoke()` - 80 edges
2. `Path` - 79 edges
3. `Path` - 47 edges
4. `Task` - 39 edges
5. `Status` - 32 edges
6. `load_tasks()` - 28 edges
7. `_state()` - 26 edges
8. `str` - 25 edges
9. `save_tasks()` - 25 edges
10. `_ids()` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Task Granularity Rule` --semantically_similar_to--> `Agent Execution Workflow`  [INFERRED] [semantically similar]
  README.md → opencode/agents/trackr.md
- `TestGenerateId` --uses--> `NotInitialized`  [INFERRED]
  tests/test_storage.py → src/trackr/errors.py
- `TestTopoOrder` --uses--> `InvalidStatus`  [INFERRED]
  tests/test_models.py → src/trackr/errors.py
- `TestGenerateId` --uses--> `CorruptState`  [INFERRED]
  tests/test_storage.py → src/trackr/errors.py
- `TestGenerateId` --uses--> `ProjectExists`  [INFERRED]
  tests/test_storage.py → src/trackr/errors.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Trackr Module Architecture** — trackr_cli_module, trackr_storage_module, trackr_models_module, trackr_errors_module [EXTRACTED 1.00]
- **Atomic Persistence Pattern** — trackr_storage_module, trackr_atomic_writes, trackr_storage_discovery [EXTRACTED 1.00]
- **Schema Versioning System** — trackr_schema_v3, trackr_schema_migration, trackr_storage_module [EXTRACTED 1.00]

## Communities (19 total, 7 thin omitted)

### Community 0 - "Storage & Persistence Layer"
Cohesion: 0.09
Nodes (40): bool, Path, str, Task, _active_path(), Path, str, _state_path() (+32 more)

### Community 1 - "Task Domain Model"
Cohesion: 0.09
Nodes (19): Enum, bool, Status, str, str, Task, TestGraphHelpers, TestStatusCoerce (+11 more)

### Community 2 - "CLI Commands & Error Handling"
Cohesion: 0.17
Nodes (29): Exception, bool, str, add(), link(), list_tasks(), _main(), _parse_tags() (+21 more)

### Community 3 - "Dependency Linking Tests"
Cohesion: 0.18
Nodes (6): _ids(), Path, TestLink, TestListDeps, TestListTopoOrder, TestShow

### Community 4 - "Tag & Filter Tests"
Cohesion: 0.15
Nodes (4): invoke(), TestListTagFilter, TestMisc, TestProject

### Community 5 - "Status & Show Tests"
Cohesion: 0.14
Nodes (5): _first_id(), TestShowTags, TestStatus, TestTagCommand, TestUntagCommand

### Community 6 - "OpenCode Agent & Docs"
Cohesion: 0.12
Nodes (18): opencode/agents/trackr.md, Atomic Write Pattern, trackr CLI Application, cli.py, Agent Execution Workflow, Error Handling Pattern, errors.py, Task Granularity Rule (+10 more)

### Community 8 - "Init & Remove Tests"
Cohesion: 0.15
Nodes (5): TestInit, TestListShowsTags, TestRemoveWithDeps, TestRequiresInit, TestStatusWithDeps

### Community 9 - "Add & Tag Tests"
Cohesion: 0.21
Nodes (4): str, _state(), TestAdd, TestTagAdd

### Community 11 - "Test Fixtures"
Cohesion: 0.33
Nodes (6): CliRunner, MonkeyPatch, initialized(), Path, runner(), workdir()

### Community 12 - "Feature Documentation"
Cohesion: 0.33
Nodes (6): Blocked Task Warning, Task Dependencies, Pipeline Ordering Algorithm, Schema Migration Strategy, Schema Version 3, Tags Feature

## Knowledge Gaps
- **13 isolated node(s):** `MonkeyPatch`, `errors.py`, `Task ID Generation`, `Project Management`, `TDD Development Rule` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `invoke()` connect `Tag & Filter Tests` to `Dependency Linking Tests`, `Status & Show Tests`, `Init & Remove Tests`, `Add & Tag Tests`, `Test Fixtures`, `List Command Tests`, `Remove Command Tests`, `Unlink Tests`?**
  _High betweenness centrality (0.199) - this node is a cross-community bridge._
- **Why does `Task` connect `Task Domain Model` to `Storage & Persistence Layer`, `CLI Commands & Error Handling`, `Topological Sort Tests`, `ID Generation`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Why does `Status` connect `Task Domain Model` to `Storage & Persistence Layer`, `CLI Commands & Error Handling`, `Topological Sort Tests`, `ID Generation`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 78 inferred relationships involving `invoke()` (e.g. with `.test_add_persists_task()` and `.test_description_is_trimmed()`) actually correct?**
  _`invoke()` has 78 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `Path` (e.g. with `CorruptState` and `InvalidProjectName`) actually correct?**
  _`Path` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `Task` (e.g. with `bool` and `str`) actually correct?**
  _`Task` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `Status` (e.g. with `bool` and `str`) actually correct?**
  _`Status` has 26 INFERRED edges - model-reasoned connections that need verification._