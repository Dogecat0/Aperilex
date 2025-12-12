# Commit Review – 2025-10-16

> Learning walkthrough bindings and manual review scheduling no longer exist in the codebase; this review is retained solely for historical reference.

Repository: aperilex
Reviewed Commits:

- 76df68a60774f5169a090764b616269daf4c5add
- d44ba0cf69325767f9f26b10dc4baaad8484ff38

## Findings

1. **Missing database migration for walkthrough bindings**
   *Commit:* 76df68a60774f5169a090764b616269daf4c5add
   *Details:* The change introduces `LearningWalkthroughBinding` ORM models and wires new repositories/query services, but no Alembic migration accompanies the schema. Running `alembic upgrade head` will not create the `learning_walkthrough_bindings` table, so any runtime use of the repository will fail with `relation "learning_walkthrough_bindings" does not exist`.
   *Impact:* Production deploys will break learning walkthrough persistence until a migration is added.

2. **Scheduled review counts overwritten during refresh**
   *Commit:* 76df68a60774f5169a090764b616269daf4c5add
   *Details:* `LearningService.schedule_review` stores the `pending_review_count` requested by the client, but `_refresh_module_progress` (invoked immediately after) recomputes the count from walkthrough binding approval status and replaces the explicit value. In environments where artifacts are already approved this returns `0`, disregarding the user’s request.
   *Impact:* Review scheduling endpoint cannot surface the intended reminder counts, leaving learners without the planned follow-up cadence.

## Suggested Next Steps

1. Ship an Alembic migration that creates `learning_walkthrough_bindings` with the same schema as the new ORM model, and ensure it is included in deploy instructions.
2. Adjust `_refresh_module_progress` to respect explicit scheduling inputs—e.g. only recompute pending counts when not supplied, or persist the scheduled value alongside binding-derived metrics.

## Notes

- No additional issues were observed in commit d44ba0cf69325767f9f26b10dc4baaad8484ff38 beyond the dependencies on the migration gap above.
