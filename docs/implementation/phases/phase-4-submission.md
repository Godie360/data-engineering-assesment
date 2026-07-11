# Phase 4 — Submission Package

## Status

pending

## Scope

- `README.md`
- `report.md`
- `.gitignore`
- `.env.example`

## Features

- README enabling a reviewer to run the project from scratch
- Brief report (≤3 pages): approach, decisions, challenges, assumptions
- Clean repository: no secrets, no large data files committed
- End-to-end smoke test confirming README instructions are correct

## Tasks

- [ ] TASK-15: README
- [ ] TASK-16: Brief report
- [ ] TASK-17: Repo cleanup
- [ ] TASK-18: Final smoke test

## Acceptance Criteria

- `README.md` covers: Prerequisites, Setup, Download Dataset, Run Pipeline, Run App, Project Structure
- `report.md` is ≤3 pages and covers dataset rationale, architecture, cleaning decisions, RAG pattern choice
- `.env` and `data/` directory are git-ignored (dataset file must not be committed)
- `git grep -r "sk-"` returns no matches
- Full sequence — `docker compose up -d` → `python sql/apply_schema.py` → `python run_pipeline.py` → `streamlit run app.py` — succeeds following README only
