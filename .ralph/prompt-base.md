# Context Management

**Be judicious** — do NOT read large files upfront. Only read what the current task requires.

# Task Claiming

1. Identify the **single highest priority task** that is ready to work.
2. **Work on exactly ONE task** at a time.

Run `bd ready` to find available work. If multiple issues share the same priority, just pick one - don't ask which to work on. If any are code review tasks, choose one of those.

After claiming a task with `bd update <id> --status in_progress`, run `bd show <id>` and print the full output (all fields) so the task details are visible in context before starting work.

If the task is a parent task and all its children are closed, do one last code review, any remediation necessary, before closing the parent.

## Landing the Plane (Additions)

These rules supplement the Landing the Plane section in AGENTS.md:

- `git push` may require bypassing the sandbox (e.g., dangerouslySkipPermissions for Claude, dangerouslyBypassApprovalsAndSandbox for Codex).
- **Make one git commit** per task with a descriptive message.
- **Append a dated progress entry to `activity.md`** describing the task completed, the verification results, and the screenshot path (if applicable).
- Do not `git init`, do not change remotes.

## Work Process
Read `docs/application.md` to learn about the application architecture.

### Keep docs/application.md up to date
Before ending a session, review `docs/application.md` and update it to reflect any changes made during the session (new packages, config changes, CLI commands, architecture changes, etc.). This file is the single source of truth for the application and must stay current.

When you plan your work, trace the full path of the change through the relevant layers of the codebase: cli, converter, tests.

# Constraint

**Work on a single task at a time.** After committing, stop — the next session will pick up the next task.
