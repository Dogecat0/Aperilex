# Stage 5 Identity Backfill Plan (PS5.0.3)

Stage 5.0.3 retires the legacy username/password authentication schema and prepares the
identity tables that will land in Stage 5.1. This document records the reset that was
performed and the backfill steps that must run immediately after the Stage 5 identity
migrations are applied.

## Current State

- Alembic revision `909acfb8d771` drops the legacy `users` table.
- Alembic revision `84b35cf4baad` stages the new identity schema (`users`,
  `user_identities`, `user_profiles`). The migration is committed but **not** applied yet.
- The Docker development database was reset via `docker compose exec postgres ...` so the
  migration history starts clean prior to introducing the Stage 5 tables.

```
docker compose up -d postgres
# Reset public schema
docker compose exec postgres psql -U aperilex -d aperilex \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO aperilex;"
# Verify schema is empty
docker compose exec postgres psql -U aperilex -d aperilex \
  -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
docker compose stop postgres
```

## Legacy Sentinel Mapping

Historical `analyses.user_id` values were backfilled to the sentinel UUID
`00000000-0000-0000-0000-000000000000` (see revision `1b7dc9a0872e`). The same value is
used anywhere a mock task reference was persisted. After the Stage 5 identity tables are
applied, we must replace this sentinel with the newly provisioned user record that the
OAuth flow will create.

## Backfill Script

A shell-ready helper lives at `scripts/backfill_stage5_identity.sh`. The script **does
not execute any SQL by default**; it prints the statements that should run once Stage 5
migrations are in place. Uncomment the final block when the production/staging rollout is
ready.

Usage:

```bash
NEW_USER_ID=11111111-2222-3333-4444-555555555555 \
NEW_USER_EMAIL=founder@aperilex.com \
PROVIDER_SUBJECT="google-oauth2|123456789012345678901" \
./scripts/backfill_stage5_identity.sh
```

What the script prepares (without running):

1. Inserts or updates the `users` record for the real account (schema_version defaults to 1).
2. Inserts or updates the `user_identities` Google mapping for the same user.
3. Ensures a `user_profiles` shell row exists so preference/progress tables can join on it.
4. Updates `analyses.user_id` and (when present) `tasks.user_id` from the legacy sentinel to the
   new UUID.

After reviewing the generated SQL, re-run the script with the execution block uncommented
or copy/paste the statements into `psql` inside the app container:

```bash
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U aperilex -d aperilex <<'SQL'
-- SQL emitted by the script goes here.
SQL
```

Keep this document with the migration pull request so the rollout playbook includes the
exact mapping that keeps analyses/tasks tied to the authenticated account once the mock
user disappears.
