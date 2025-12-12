# Learning Hub Quiz + Walkthrough Redesign

## Objectives

- Record and surface real quiz outcomes (pass and fail), not just perfect runs.
- Keep section-completion gating unchanged: users must answer all checks correctly to advance/unlock.
- Make attempts intelligible: expose correctness, errors, timings, and unlock drivers.
- Reduce surprise on refresh while a section is mid-run.
- Allow users to bind Learning Hub context to a specific analysis instead of always the latest.

## Execution Steps

- ✅ Frontend stepper: post a quiz attempt as soon as all questions have at least one answer; compute `correctCount` from answers; stop defaulting `final_answer` to correct; keep section completion gated on all-correct.
- ✅ Backend API/service: accept partial scores unchanged; ensure `passed` derives from posted `score_percent`; keep unlock logic (walkthrough 100% + best attempt >=80%) after removing any reliance on legacy `analysis_walkthroughs`.
- ✅ Attempt payload: include `incorrect_attempts_total`, per-question attempts/incorrects/timestamps, `duration_seconds`; never auto-fill answers; drop any unused fallbacks when serializing.
- ✅ Before-unload guard: add warning when the active section has unanswered or incorrect checks; do not block normal flow once a section is fully correct.
- ✅ Learning Hub attempts list: render Best + Latest badges, pass/fail badge, score %, correct/total, `incorrect_attempts_total`, `duration_seconds`, timestamp; add pass/fail filter; add detail drawer showing per-question stats.
- ✅ Learning Hub summary chip: compute `Best X% · Last Y% · Attempts N` per quiz.
- ✅ Analysis binding: add selector on module cards to choose which analysis populates the module; rehydrate CTAs/context from that analysis; persist choice (client-side and, if needed, in progress metadata) so hub state is analysis-bound.
- Cleanups: delete `analysis_walkthroughs` fallback once backend stops emitting it; prune any code paths that assume perfect attempts; document removed fallbacks inline.

## Quiz Attempt Logging (frontend → backend)

- Submit a quiz attempt once the user has answered every question at least once, even if some answers are wrong.
- Compute `correctCount` from actual answers; `scorePercent` = `(correct / total) * 100`; `passed` = `scorePercent >= 80`.
- Persist only user choices: `final_answer` = last selected option, never default to the correct answer.
- Keep per-question stats: `attempts`, `incorrect_attempts`, `first_attempt_at`, `completed_at`, `lastSelectedOption`, `incorrect_attempts_total`, `duration_seconds`.
- Still require all questions correct to mark the section complete; unlocking stays tied to walkthrough progress 100% + passing attempt.

## Stepper UX

- Wrong → right flow: users can retry until correct; section completes only when all checks are correct.
- Refresh handling: in-progress answers are local-only. Add a before-unload warning when any visible section has unanswered or incorrect checks to warn about loss on refresh/navigation.
- Persisted sections remain complete after refresh via backend metadata; incomplete sections reset locally.

## Learning Hub UI

- Show both Latest and Best attempts (per quiz/module). Highlight which attempt unlocked the module.
- Attempt row content: status badge (Pass/Fail), score %, `correct / total`, `incorrect_attempts_total`, `duration_seconds`, timestamp.
- Detail drawer/panel per attempt: per-question view with user answer, correct answer, attempts, first/last timestamps.
- Summary chip above the list: `Best 92% · Last 76% · Attempts 3`.
- Keep attempts sorted by attempted_at desc; allow filtering to Pass/Fail/all.

## Analysis Binding in Learning Hub

- Current behavior: modules are derived from the most recent analyses (sorted desc; first per module key). Users cannot choose which analysis backs a module card.
- Change: let users pick the source analysis per module (e.g., dropdown on the card: “Use analysis …”). Selecting rehydrates the module context (cta target, highlights, diffs, lessons) from that analysis. Persist choice client-side (and, if needed, via progress metadata) so the hub is analysis-bound per user preference instead of always latest.

## Cleanups

- Remove the final-answer defaulting to correct answers in attempt payloads.
- Drop the legacy `analysis_walkthroughs` fallback once backend stops emitting it and UI reads `metadata.sections.*` exclusively.
