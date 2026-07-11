# Project agent guide

<!-- One source of truth for every AI coding agent. AGENTS.md is read by Codex,
     Cursor, Gemini CLI, Copilot and others; CLAUDE.md is a symlink to this file. -->

## What this project is

(One or two lines: what it does, the stack, anything an agent must know first.)

## Conventions

- (Commit format, branch rules, how to run tests, etc.)

## Skills

Reusable skills live in `.agents/skills/` and are shared across all agents.
Workflow packages live in `.agents/workflows/`.
Basic setup does not create `docs/`; docs are owned by installed workflows.

## Workflow Authority

- Canonical workflow policy: `.agents/workflows/workflow-contract/spec/*`
- Canonical validator: `python3 .agents/workflows/workflow-contract/scripts/validate_workflow.py`

## Start Here

1. Classify the task.
2. Run `python3 .agents/workflows/workflow-contract/scripts/validate_workflow.py`.
3. Read `docs/design/`.
4. Read `docs/implementation/`.
5. If behavior is unresolved, read or create `docs/changes/proposed/`.
6. Load required repo skill(s).
7. Inspect target service code before editing.

## Documentation Workflow

Use `$workflow-contract` for:

- design docs
- implementation docs
- backlog, phase, task, and status updates
- proposed changes
- docs-vs-code reconciliation
- workflow validation failures

Layer rules:

- `docs/design/`: approved product/system truth.
- `docs/implementation/`: execution plans, phases, tasks, and status only.
- `docs/changes/proposed/`: unresolved proposals only.

Do not define net-new behavior in implementation docs. Put unresolved behavior in `docs/changes/proposed` until accepted.
