# trackr — task tracking rule

For any non-trivial or multi-step task in a git repo:

- If `.trackr/` exists at the repo root → use trackr to track tasks.
- If substantial work is starting and no `.trackr/` exists → offer to run `trackr init`.
- Skip for throwaway / one-shot tasks.

**Granularity:** trackr tasks are **milestone-sized** — one project-meeting bullet (a feature, a migration, a deliverable). Implementation steps (write tests, bump schema, edit a model, update docs) stay in the TodoWrite session list. Do **not** mirror TodoWrite items into trackr 1:1.

**Loop:**
1. `trackr list` to discover existing tasks and IDs.
2. `trackr add "<milestone>"` when a new milestone-sized unit of work surfaces.
3. `trackr status <id> "In Progress"` when starting a task.
4. `trackr status <id> done` when finished.
5. TodoWrite tracks implementation steps; trackr tracks milestones. They operate at different levels — do not keep them in sync item-for-item.

For full CLI usage (commands, aliases, schema, exit codes), load the `trackr` skill.

**Opt-out:** if this repo's AGENTS.md disables trackr, or `.trackr/` is intentionally absent, do not use trackr.
