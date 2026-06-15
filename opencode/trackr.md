# trackr — task tracking rule

For any non-trivial or multi-step task in a git repo:

- If `.tasks/` exists at the repo root → use trackr to track tasks.
- If substantial work is starting and no `.tasks/` exists → offer to run `trackr init`.
- Skip for throwaway / one-shot tasks.

**Loop:**
1. `trackr list` to discover existing tasks and IDs.
2. `trackr add "<task>"` as new todos surface.
3. `trackr status <id> "In Progress"` when starting a task.
4. `trackr status <id> done` when finished.
5. Keep trackr in sync with the TodoWrite list — they should mirror each other.

For full CLI usage (commands, aliases, schema, exit codes), load the `trackr` skill.

**Opt-out:** if this repo's AGENTS.md disables trackr, or `.tasks/` is intentionally absent, do not use trackr.
