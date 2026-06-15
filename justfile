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
    uv tool install .

# Sync deps then run the full suite (pre-commit check)
check: sync test
