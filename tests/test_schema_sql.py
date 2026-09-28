"""Unit tests verifying SQL schema migrations and Row Level Security policy specifications."""

from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent.parent / "supabase" / "migrations"


def test_schema_tables_and_indexes():
    """Verify core tables, constraints, and indexes in initial schema migration."""
    schema_file = MIGRATIONS_DIR / "20260928000001_initial_schema.sql"
    assert schema_file.exists(), "Initial schema migration file must exist"

    sql = schema_file.read_text()

    expected_tables = [
        "public.profiles",
        "public.trips",
        "public.trip_preferences",
        "public.conversations",
        "public.messages",
        "public.agent_runs",
    ]
    for table in expected_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql, f"Table {table} must be defined"

    # Foreign key references & constraints
    assert "REFERENCES public.profiles(id)" in sql
    assert "REFERENCES public.trips(id)" in sql
    assert "REFERENCES public.conversations(id)" in sql
    assert "chk_trip_dates" in sql
    assert "travelers >= 1" in sql
    assert "budget > 0" in sql

    # Indexes
    assert "CREATE INDEX IF NOT EXISTS idx_trips_user_id" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_conversations_user_id" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_agent_runs_trip_id" in sql


def test_rls_policies_coverage():
    """Verify that every public table enables RLS and defines auth.uid() isolation policies."""
    rls_file = MIGRATIONS_DIR / "20260928000002_rls_policies.sql"
    assert rls_file.exists(), "RLS migration file must exist"

    sql = rls_file.read_text()

    expected_tables = [
        "public.profiles",
        "public.trips",
        "public.trip_preferences",
        "public.conversations",
        "public.messages",
        "public.agent_runs",
    ]

    # Verify RLS is enabled on all tables
    for table in expected_tables:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in sql, f"RLS must be enabled on {table}"

    # Verify auth.uid() is used in security checks
    assert "auth.uid()" in sql
    assert "auth.uid() = user_id" in sql
    assert "auth.uid() = id" in sql
