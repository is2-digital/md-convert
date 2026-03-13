# Sandbox Notes

This file documents two separate environments the agent operates within:

1. **Agent sandbox** — Permission restrictions imposed by the AI agent's CLI (e.g., Claude's sandbox mode). Controls what the agent is *allowed* to run on the host.
2. **Host dev environment** — The project runs directly on the host (no Docker containers).

---

## Agent Sandbox

When the agent runs in sandbox mode, certain commands are blocked by default and require elevated permissions (e.g., dangerouslySkipPermissions for Claude, dangerouslyBypassApprovalsAndSandbox for Codex).

### Runs INSIDE the agent sandbox (no special permissions needed)

- Git commands (add, commit, diff, log, status)
- File operations (read, write, edit)
- `python`, `pip`, `pytest` commands (via `.venv/bin/` or after `source .venv/bin/activate`)

### Requires OUTSIDE the agent sandbox (needs elevated permissions)

- `bd` (beads) commands — requires Dolt database connection on localhost
- `git push` / `git pull`
- Network access (pip install from PyPI)

---

## Host Dev Environment

Python 3.12 is installed on the host. No Docker containers are used.
A virtual environment is located at `.venv/` in the project root. Always activate it before running Python commands.

### Development Commands

```bash
# Activate the virtual environment:
source .venv/bin/activate

# Install in editable mode with dev dependencies:
pip install -e ".[dev]"

# Run tests:
pytest

# Run the CLI:
md-convert INPUT.mht --output OUTPUT.md --assets-folder assets
```

### No services required

This is a standalone CLI tool with no background services, databases, or network dependencies at runtime.
