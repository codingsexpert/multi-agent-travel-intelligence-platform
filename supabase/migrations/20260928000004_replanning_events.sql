-- ==============================================================================
-- Multi-Agent AI Travel Intelligence Platform
-- Migration: 20260928000004_replanning_events.sql
-- Description: Dynamic Replanning Audit Trail table with strict Row Level Security.
--              Maintains immutable audit records of all change events and itinerary versions.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Create replanning_events Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.replanning_events (
    id TEXT PRIMARY KEY DEFAULT ('rpl-' || substr(md5(random()::text), 1, 8)),
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_payload JSONB DEFAULT '{}'::jsonb,
    impact_summary JSONB DEFAULT '{}'::jsonb,
    previous_itinerary_version INT NOT NULL DEFAULT 1,
    new_itinerary_version INT NOT NULL DEFAULT 2,
    human_explanation TEXT,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices for rapid querying by trip
CREATE INDEX IF NOT EXISTS idx_replanning_events_trip_id ON public.replanning_events(trip_id);
CREATE INDEX IF NOT EXISTS idx_replanning_events_created_at ON public.replanning_events(created_at DESC);

-- ------------------------------------------------------------------------------
-- 2. Enable Row Level Security (RLS)
-- ------------------------------------------------------------------------------
ALTER TABLE public.replanning_events ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------
-- 3. RLS Policies
-- Authenticated users can only read and insert replan records for their own trips
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view replanning events for their own trips" ON public.replanning_events;
CREATE POLICY "Users can view replanning events for their own trips"
    ON public.replanning_events
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.trips
            WHERE trips.id = replanning_events.trip_id
              AND trips.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can insert replanning events for their own trips" ON public.replanning_events;
CREATE POLICY "Users can insert replanning events for their own trips"
    ON public.replanning_events
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.trips
            WHERE trips.id = replanning_events.trip_id
              AND trips.user_id = auth.uid()
        )
    );
