# Supabase Database Migrations & Architecture

This directory contains versioned SQL migrations for the **Multi-Agent AI Travel Intelligence & Dynamic Replanning Platform**.

---

## Migration Files

1. `20260928000001_initial_schema.sql`:
   - Creates `profiles`, `trips`, `trip_preferences`, `conversations`, `messages`, and `agent_runs` tables.
   - Creates indexes on foreign keys (`user_id`, `trip_id`, `conversation_id`) and timestamps.
   - Configures triggers for `updated_at` timestamps and automatic profile provisioning upon `auth.users` signup.
2. `20260928000002_rls_policies.sql`:
   - Enables Row Level Security (RLS) across all public tables.
   - Configures strict security policies restricting SELECT, INSERT, UPDATE, and DELETE operations to records owned by `auth.uid()`.

---

## Applying Migrations

### Method 1: Supabase CLI (Recommended for CI/CD)
```bash
# Link local repository to your remote Supabase project
supabase link --project-ref your-project-id

# Apply all pending migrations safely
supabase db push
```

### Method 2: Supabase Web Console SQL Editor
1. Log in to [Supabase Console](https://supabase.com/dashboard).
2. Open your project and navigate to the **SQL Editor**.
3. Run `20260928000001_initial_schema.sql`.
4. Run `20260928000002_rls_policies.sql`.

---

## Row Level Security (RLS) Strategy

The platform enforces absolute multi-tenant data isolation directly at the database engine level:
- Direct ownership tables (`profiles`, `trips`, `conversations`) require `auth.uid() = user_id`.
- Child tables (`trip_preferences`, `messages`, `agent_runs`) use `EXISTS` subqueries verifying that the referenced parent entity is owned by `auth.uid()`.
- Frontend code cannot spoof `user_id` to access or modify records of another traveler.
