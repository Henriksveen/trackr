# trackr — task runner. Run `just` to see all recipes.

# List available recipes (default)
default:
    @just --list

# Install all dependencies (runtime + dev)
sync:
    uv sync

# Run the full test suite
test:
    uv run pytest

# Build the wheel + sdist
build:
    uv build

# Install trackr as a tool on your PATH
install:
    uv tool install . --force --reinstall --no-cache

# Sync deps then run the full suite (pre-commit check)
check: sync test

# Install trackr opencode integration (skill + rule + planner agent) into global config
install-opencode:
    mkdir -p ~/.config/opencode/skills
    mkdir -p ~/.config/opencode/agents
    cp -r opencode/skills/trackr ~/.config/opencode/skills/
    cp opencode/trackr.md ~/.config/opencode/
    cp opencode/agents/trackr.md ~/.config/opencode/agents/
    @echo ""
    @echo "Skill + rule + planner agent copied. To activate the always-on rule, add this to"
    @echo "the \"instructions\" array in ~/.config/opencode/opencode.jsonc:"
    @echo ""
    @echo '    "@~/.config/opencode/trackr.md"'
    @echo ""
    @echo "(Skill + agent work immediately — no config edit needed. Remove that line to disable the rule.)"
    @echo "Switch into the agent via the agent picker: \"trackr\". Restart opencode to load it."
