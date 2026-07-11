# Validator Findings Guide

Use this guide to remediate validation failures from:

```bash
make -C .agents/workflows/workflow-contract validate
```

Script fallback:

```bash
python3 .agents/workflows/workflow-contract/scripts/validate_workflow.py
```

## STRUCTURE

Sample finding:

```text
STRUCTURE:docs/implementation/tasks:missing-required-directory
```

Meaning:

- A required directory or file from `repo.config.json` is missing.
- Or a disallowed directory/file exists.

Fix:

1. Compare repo tree against `required_directories` and `required_files`.
2. Create missing required paths.
3. Remove or rename disallowed paths.
4. Re-run validator.

## METADATA

Sample finding:

```text
METADATA:docs/implementation/project.md:missing-sections:Current Priorities,Active Phases
```

Meaning:

- A doc file is missing required headings expected by the metadata validator.

Fix:

1. Open the flagged file.
2. Add the missing `##` headings exactly as required.
3. Use templates from `.agents/workflows/workflow-contract/templates/` for shape alignment.
4. Re-run validator.

## TRANSITIONS

Sample finding:

```text
TRANSITIONS:docs/changes/proposed/my-proposal.md:invalid-proposal-status:accepted
```

Meaning:

- Proposal status under `## Status` is not listed in `statuses.proposal.allowed`.

Fix:

1. Replace status with an allowed value.
2. Or update `repo.config.json` status policy if intentionally changing process.
3. Re-run validator.

## REFERENCES

Sample finding:

```text
REFERENCES:docs/implementation/tasks/backlog.md:legacy-reference-found
```

Meaning:

- A forbidden legacy path pattern from `legacy_reference_patterns` was found.

Fix:

1. Remove or replace the stale reference in the flagged file.
2. Keep references aligned to current docs map.
3. Re-run validator.

## Final Check

Successful run should end with:

```text
WORKFLOW:ok
```
