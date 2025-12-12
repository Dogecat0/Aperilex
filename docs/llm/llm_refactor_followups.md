# LLM Refactor

- [done] Update `create_section_summary_prompts` (and tighten `SectionSummaryResponse`) so `critical_findings` is capped at 3–5 bullet points, matching the deliverables guidance before we rely on structured validation.
  1. Add the bullet-count instruction to the `Deliverables` block in `create_section_summary_prompts` (backend).
  2. Constrain `SectionSummaryResponse.critical_findings` with `conlist(str, min_length=3, max_length=5)` and mirror the same limits in `SectionAnalysisResponse`.
  3. Regenerate the golden fixture (or update the test snapshots) to ensure new limits are enforced; then run `poetry run mypy src/ tests/` and `poetry run ruff check src/ tests/` followed by pytest inside Docker.
  4. Confirm the frontend still renders max 5 findings without layout regressions (see `frontend-ux-refactor.md` guidelines).
