-- ==============================================================================
-- Multi-Agent AI Travel Intelligence Platform
-- Migration: 20260928000002_rls_policies.sql
-- Description: Strict Row Level Security (RLS) policies for user data isolation.
--              Guarantees that authenticated users can ONLY access their own records.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Enable RLS on All Public Application Tables
-- ------------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trip_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_runs ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------
-- 2. Profiles Policies
-- Users can only read and update their own profile matching auth.uid()
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view their own profile" ON public.profiles;
CREATE POLICY "Users can view their own profile"
    ON public.profiles
    FOR SELECT
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;
CREATE POLICY "Users can update their own profile"
    ON public.profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- ------------------------------------------------------------------------------
-- 3. Trips Policies
-- Users can only SELECT, INSERT, UPDATE, DELETE trips where user_id = auth.uid()
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view their own trips" ON public.trips;
CREATE POLICY "Users can view their own trips"
    ON public.trips
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own trips" ON public.trips;
CREATE POLICY "Users can insert their own trips"
    ON public.trips
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own trips" ON public.trips;
CREATE POLICY "Users can update their own trips"
    ON public.trips
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own trips" ON public.trips;
CREATE POLICY "Users can delete their own trips"
    ON public.trips
    FOR DELETE
    USING (auth.uid() = user_id);

-- ------------------------------------------------------------------------------
-- 4. Trip Preferences Policies
-- Authorized via parent trip ownership (trips.user_id = auth.uid())
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view preferences for their trips" ON public.trip_preferences;
CREATE POLICY "Users can view preferences for their trips"
    ON public.trip_preferences
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.trips
            WHERE trips.id = trip_preferences.trip_id
            AND trips.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can insert preferences for their trips" ON public.trip_preferences;
CREATE POLICY "Users can insert preferences for their trips"
    ON public.trip_preferences
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.trips
            WHERE trips.id = trip_preferences.trip_id
            AND trips.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can update preferences for their trips" ON public.trip_preferences;
CREATE POLICY "Users can update preferences for their trips"
    ON public.trip_preferences
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.trips
            WHERE trips.id = trip_preferences.trip_id
            AND trips.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.trips
            WHERE trips.id = trip_preferences.trip_id
            AND trips.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can delete preferences for their trips" ON public.trip_preferences;
CREATE POLICY "Users can delete preferences for their trips"
    ON public.trip_preferences
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.trips
            WHERE trips.id = trip_preferences.trip_id
            AND trips.user_id = auth.uid()
        )
    );

-- ------------------------------------------------------------------------------
-- 5. Conversations Policies
-- Users can only access conversations where user_id = auth.uid()
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view their own conversations" ON public.conversations;
CREATE POLICY "Users can view their own conversations"
    ON public.conversations
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own conversations" ON public.conversations;
CREATE POLICY "Users can insert their own conversations"
    ON public.conversations
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own conversations" ON public.conversations;
CREATE POLICY "Users can update their own conversations"
    ON public.conversations
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own conversations" ON public.conversations;
CREATE POLICY "Users can delete their own conversations"
    ON public.conversations
    FOR DELETE
    USING (auth.uid() = user_id);

-- ------------------------------------------------------------------------------
-- 6. Messages Policies
-- Access permitted only if the parent conversation belongs to auth.uid()
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view messages for their conversations" ON public.messages;
CREATE POLICY "Users can view messages for their conversations"
    ON public.messages
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.conversations
            WHERE conversations.id = messages.conversation_id
            AND conversations.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can insert messages into their conversations" ON public.messages;
CREATE POLICY "Users can insert messages into their conversations"
    ON public.messages
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.conversations
            WHERE conversations.id = messages.conversation_id
            AND conversations.user_id = auth.uid()
        )
    );

-- ------------------------------------------------------------------------------
-- 7. Agent Runs Policies
-- Access permitted only if parent trip belongs to auth.uid()
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view agent runs for their trips" ON public.agent_runs;
CREATE POLICY "Users can view agent runs for their trips"
    ON public.agent_runs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.trips
            WHERE trips.id = agent_runs.trip_id
            AND trips.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can insert agent runs for their trips" ON public.agent_runs;
CREATE POLICY "Users can insert agent runs for their trips"
    ON public.agent_runs
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.trips
            WHERE trips.id = agent_runs.trip_id
            AND trips.user_id = auth.uid()
        )
    );
