# trackr

A small, fast **per-repository CLI task tracker**. State is stored locally in a
hidden `.trackr/` directory at the repo root — just like Git's `.git/` — so each
repository keeps its own independent task list.

## Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- [`just`](https://just.systems) task runner

## Install

```bash
# install deps
just sync

# install trackr as a tool on your PATH
just install
trackr --help
```

### OpenCode integration (optional)

```bash
just install-opencode
```

Copies a **trackr agent + skill** into `~/.config/opencode/`. Lets you manage tasks in natural language via the OpenCode agent picker (`trackr` agent). The skill provides the full CLI reference for the agent.

## Usage

```bash
trackr init                          # create .trackr/ in the current repo
trackr add "Write the README"        # add a task (status: Todo)
trackr add "Fix login bug" --tags "bug,urgent"  # add with tags
trackr list                          # show open tasks (hides Done)
trackr list --all                    # show everything, including Done
trackr list --tag bug                # filter by tag
trackr list --tag bug --tag urgent   # filter by multiple tags (any match)
trackr status a3f9 "In Progress"     # update status (aliases ok: wip, done...)
trackr status a3f9 done
trackr tag a3f9 feature              # add a tag
trackr untag a3f9 feature            # remove a tag
trackr remove a3f9                   # delete a task
trackr show a3f9                     # show full task detail + deps + tags
trackr link a3f9 b2c1                # a3f9 depends on b2c1 (b2c1 must finish first)
trackr unlink a3f9 b2c1             # remove that dependency
trackr project list                  # list all projects (* marks active)
trackr project new <name>            # create a new project
trackr project switch <name>         # switch the active project
trackr --version
```
