# Sandbox Notes

This file documents two separate environments the agent operates within:

1. **Agent sandbox** — Permission restrictions imposed by the AI agent's CLI (e.g., Claude's sandbox mode). Controls what the agent is *allowed* to run on the host.
2. **Docker dev container** — Where the project's application code runs. The language runtime and dependencies live here, not on the host.

---

## Agent Sandbox

When the agent runs in sandbox mode, certain commands are blocked by default and require elevated permissions (e.g., dangerouslySkipPermissions for Claude, dangerouslyBypassApprovalsAndSandbox for Codex).

### Runs INSIDE the agent sandbox (no special permissions needed)

- Git commands (add, commit, diff, log, status)
- File operations (read, write, edit)
- `bd` (beads) commands

### Requires OUTSIDE the agent sandbox (needs elevated permissions)

- `git push` / `git pull`
- `docker compose` commands (up, run, build, down, logs)
- Any container interaction
- Network access

---

## Docker Dev Container

The project's language runtime and dependencies are NOT installed on the host.
All application commands (build, test, lint, run) must execute inside the Docker dev container via `docker compose run`.

{{CONTAINER_LANGUAGE e.g., "Go", "Python", "Node.js"}} is the primary language.
{{CONTAINER_NOTES optional — e.g., "The app service exits if required env vars are missing. Use docker compose run --rm app <command> for CLI commands."}}

### Development Commands

```bash
{{DEV_COMMANDS e.g.,
# Start services:
docker compose up -d

# Build:
docker compose run --rm app go build ./...

# Test:
docker compose run --rm app go test ./...
}}
```

### Services & Ports

Services are defined in `docker-compose.yml`.

{{SERVICES_TABLE e.g.,
| Service    | Port | URL                  |
|------------|------|----------------------|
| API server | 8080 | http://localhost:8080 |
| PostgreSQL | 5432 | localhost:5432        |
}}

{{SANDBOX_NOTES optional — e.g., "Agent cannot access network resources directly; all HTTP calls must go through the container."}}
