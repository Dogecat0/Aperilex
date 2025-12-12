# Learning Hub Quiz Follow-Up Notes

## Replace the staging helper with real quiz submissions

1. Remove the manual “Log practice attempt” CTA from the Learning Hub so quiz history reflects only authentic walkthrough completions.
2. Capture answer attempts inside the guided MD&A walkthrough (each comprehension check already reports correctness) and aggregate them by learning module.
3. When a learner finishes all comprehension checks for a module, POST the real attempt data (`quiz_id`, `question_count`, `correct_count`, `score_percent`, `responses`, and module metadata) to `/learning/quiz-attempts`.
4. Invalidate quiz attempt caches so the Learning Hub timeline refreshes with the just-recorded attempt.

## Auto-unlock modules on genuine quiz performance

1. Treat any attempt with `score_percent ≥ 80` as passing regardless of human review flags; unlock the linked module immediately after a passing score.
2. Update backend services to derive unlock state from the best attempt’s score, keeping `last_reviewed_at` for actual human reviews only.
3. Simplify frontend status chips and copy so they surface “Passed”/“Retake” states without referencing manual review queues.
4. Update fixtures and tests to assert the new unlock behaviour and removal of the manual logging fallback.
