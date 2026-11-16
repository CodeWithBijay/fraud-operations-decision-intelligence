# Evidence Folder — Weeks 12–13 Validation

| File | Contents | Matrix rows |
|---|---|---|
| `E01_synthetic_data.md` | Provenance, structural/logical checks, independent rule recomputation, plausibility, coverage, threshold sensitivity, privacy | TEST-01 to TEST-06 |
| `E02_reports_and_models.md` | Report reconciliation, generated summaries, fraud model and volume model validation | TEST-07 to TEST-18 |
| `E03_ui_and_assistant.md` | Smoke-test log, UI-to-requirement map, Assistant tests, roles, changes made | TEST-19 to TEST-26, TEST-22R, TEST-23R |
| `E04_user_test_2026-11-15.md` | Task-based user test record (participant outside the team) | TEST-20, 27, 30, 31 |
| `E05_end_to_end_walkthroughs.md` | Typical day (160) and spike (170→171) walkthroughs | TEST-28, TEST-29 |
| `validation_results.json` | Raw outputs of the database run (2026-11-15) | all data/report rows |
| `screenshots/` | App screenshots for TEST-07, TEST-08 and the user test (add here) | TEST-07, 08, 20+ |

**Reproduce:** from the project folder, `python3 scripts/validate_week12.py` (read-only SQL against the database in
`.streamlit/secrets.toml`) and `cd scripts && python3 smoke_test_app.py`. Dependencies: `requirements.txt`.
Model metrics come from `python3 src/modeling/evaluate_week11.py`, which needs the raw IEEE-CIS files in `data/raw/`.
**Previous submission preserved:** Git commit `e15d032` (Week 11) and `docs/20_week11_evaluation_report.md`.
