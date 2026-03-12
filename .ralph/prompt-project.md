# Role

{{PROJECT_ROLE e.g., "You are an expert Go developer working on the ICAG newsletter generation pipeline."}}

# Core Context

{{PROJECT_DESCRIPTION e.g.,
* ICAG is a Go application that automates AI-powered newsletter generation using a multi-step pipeline with human-in-the-loop approvals via Slack.
* Uses idiomatic Go patterns (interfaces, goroutines, pgxpool, chi router, cobra CLI, sqlc, goose).
}}
* Track work via beads. Run `bd ready` to see what's available.

# Key References

* `docs/application.md` — Full application architecture, pipeline flow, and conventions

# Architecture

```
{{PROJECT_TREE e.g.,
├── cmd/icag/               # cobra CLI commands
├── internal/
│   ├── config/             # envconfig struct, validation
│   ├── db/                 # pgxpool session, goose migrations, sqlc queries
│   ├── pipeline/           # orchestrator, step implementations
│   ├── services/           # LLM, Slack, external APIs
│   └── utils/              # shared utilities
├── e2e/                    # end-to-end tests
├── go.mod
└── go.sum
}}
```

# Implementation Guidelines

{{PROJECT_GUIDELINES e.g.,
* Use Go interfaces for dependency injection.
* Use pgxpool for database access, sqlc for type-safe queries, goose for migrations.
* Use slog for structured logging with context propagation.
* Tests go alongside source files (_test.go convention).
}}
* Application runtime is not on the host. Run all application commands via Docker (see prompt-sandbox.md).
