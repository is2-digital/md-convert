# Ralph

Ralph is a loop runner for headless AI coding agents (Claude Code, OpenAI Codex, Amp). It runs an agent in a loop for N iterations using a concatenated prompt, streams and logs output, and stops early when the agent signals completion.

## Setup

Clone ralph as a sibling directory next to your project repo:

```
projects/
├── your-project/       # your app repo
└── .ralph/             # this content
     ├── ralph.sh
     ├── prompt-base.md
     ├── prompt-project.md
     └── prompt-sandbox.md
```

Ralph automatically `cd`s one level up from its own directory, so the agent operates inside your project repo.

### Add .ralph to your project's .gitignore

Add this line to your project's `.gitignore`:

```
.ralph/
```

This excludes ralph's log directory (`.ralph-logs/`) and any other ralph artifacts from your project's git history.

### Install Beads (bd)

Ralph uses [beads](https://github.com/steveyegge/beads) (`bd`) for issue tracking. The agent picks up tasks via `bd ready` and updates status as it works.

Install bd (one-time, system-wide):

```bash
npm install -g @beads/bd
```

Other install methods: `brew install beads`, `go install github.com/steveyegge/beads/cmd/bd@latest`, or the install script from the repo.

Initialize beads in your project repo:

```bash
cd your-project
bd init --prefix <PROJECT_CODE>
```

`--prefix` sets the issue ID prefix (e.g., `bd init --prefix ACME` produces issues like `ACME-1`, `ACME-2`).

Then set up the integration for your agent:

```bash
bd setup claude
bd setup codex
```

Each recipe writes workflow instructions where the agent expects them (e.g., hooks for Claude, `AGENTS.md` for Codex). Run `bd setup --list` to see all available recipes (cursor, aider, gemini, windsurf, etc.).

## Configuring the Prompt Templates

The prompt files contain `{{PLACEHOLDER}}` markers that must be replaced with your project-specific content. Each placeholder includes an inline example showing the expected format.

Replace the **entire placeholder block** — including the `{{`, the name, the example text, and the `}}` — with your actual content. For multi-line placeholders, replace everything from `{{PLACEHOLDER_NAME` through the closing `}}`.

### prompt-project.md

| Placeholder | What to write |
|---|---|
| `{{PROJECT_ROLE}}` | A one or two-sentence role description. e.g., `You are an expert Python developer working on the Acme REST API.` |
| `{{PROJECT_DESCRIPTION}}` | Bullet list describing what the project is, what it does, and key technologies. |
| `{{PROJECT_TREE}}` | ASCII directory tree showing the top-level architecture. Only include directories/files that help the agent orient — don't list every file. |
| `{{PROJECT_GUIDELINES}}` | Bullet list of implementation conventions: patterns, libraries, testing style, naming. |

### prompt-sandbox.md

| Placeholder | What to write |
|---|---|
| `{{CONTAINER_LANGUAGE}}` | Primary language runtime in the container. e.g., `Go`, `Python 3.12`, `Node.js 20`. |
| `{{CONTAINER_NOTES}}` | *(optional)* Any quirks about running commands in the container. Remove the line if not needed. |
| `{{DEV_COMMANDS}}` | The shell commands for build, test, lint, and run — as the agent should execute them (typically via `docker compose run`). |
| `{{SERVICES_TABLE}}` | Markdown table of services, ports, and URLs from your `docker-compose.yml`. |
| `{{SANDBOX_NOTES}}` | *(optional)* Additional sandbox constraints. Remove the line if not needed. |

### prompt-base.md

| Placeholder | What to write |
|---|---|
| `{{ARCHITECTURE_LAYERS}}` | Comma-separated list of your codebase's architectural layers. e.g., `routes, controllers, services, models, tests`. |

### Example: replacing a single-line placeholder

Before:

```
{{PROJECT_ROLE e.g., "You are an expert Go developer working on the ICAG newsletter generation pipeline."}}
```

After:

```
You are a senior Python developer working on the Acme e-commerce API.  There are three primary endpoints which each require various levels of authentication.
```

### Example: replacing a multi-line placeholder

Before:

```
{{DEV_COMMANDS e.g.,
# Start services:
docker compose up -d

# Build:
docker compose run --rm app go build ./...

# Test:
docker compose run --rm app go test ./...
}}
```

After:

```
# Start services:
docker compose up -d

# Run tests:
docker compose run --rm app pytest

# Lint:
docker compose run --rm app ruff check .
```

## Usage

```bash
./ralph.sh <llm> [iterations] [dangerous] [containers] [sleep]
```

| Param | Required | Default | Description |
|---|---|---|---|
| `llm` | yes | — | `claude`, `codex`, or `amp` |
| `iterations` | no | `1` | Number of loop iterations |
| `dangerous` | no | `on` | Skip agent permission prompts (`on`/`off`) |
| `containers` | no | `""` | Comma-separated Docker container names that must be running |
| `sleep` | no | `0` | Delay before starting (e.g., `30`, `5m`, `2h`) |

Examples:

```bash
./ralph.sh claude
./ralph.sh claude 5
./ralph.sh claude 5 off
./ralph.sh codex 3 on "app-1,db-1"
./ralph.sh claude 5 on "" 2h
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `KEEP_JSONL` | `1` (Claude), `0` (others) | Save raw NDJSON event log |
| `PROMPT_FILES` | `prompt-project.md prompt-sandbox.md prompt-base.md` | Space-separated list of prompt files to concatenate |
| `CLAUDE_BIN` | auto-detected | Path to claude binary |
| `CODEX_BIN` | auto-detected | Path to codex binary |
| `AMP_BIN` | auto-detected | Path to amp binary |

## How It Works

1. Concatenates all prompt files into a single prompt string
2. Runs the selected agent in headless/non-interactive mode with that prompt
3. Streams output to stdout and logs to `.ralph-logs/` (text log always, JSONL optional for Claude)
4. After each iteration, checks the log for `<promise>COMPLETE</promise>` — if found, exits 0
5. Repeats until N iterations or early completion
6. Exits 1 if max iterations reached without the completion marker

## Requirements

- `jq` — required for Claude mode (NDJSON stream parsing)
- `docker` — only if the `containers` parameter is used
