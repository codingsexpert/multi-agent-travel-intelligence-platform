-- ==============================================================================
-- Multi-Agent AI Travel Intelligence Platform
-- Migration: 20260928000005_hitl_approvals.sql
-- Description: Human-in-the-Loop (HITL) approval tables with Row Level Security.
--              Enforces user approval for high-impact/transactional actions.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Create action_proposals Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.action_proposals (
    id TEXT PRIMARY KEY DEFAULT ('prop-' || substr(md5(random()::text), 1, 8)),
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'HIGH',
    proposed_by TEXT NOT NULL DEFAULT 'system',
    target_resource TEXT NOT NULL,
    parameters JSONB DEFAULT '{}'::jsonb,
    estimated_cost NUMERIC(12, 2) DEFAULT 0.0,
    currency TEXT DEFAULT 'USD',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    state_version INT NOT NULL DEFAULT 1,
    idempotency_key TEXT NOT NULL UNIQUE,
    requires_approval BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_action_proposals_trip_id ON public.action_proposals(trip_id);
CREATE INDEX IF NOT EXISTS idx_action_proposals_user_id ON public.action_proposals(user_id);
CREATE INDEX IF NOT EXISTS idx_action_proposals_idempotency ON public.action_proposals(idempotency_key);

-- ------------------------------------------------------------------------------
-- 2. Create approval_requests Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.approval_requests (
    id TEXT PRIMARY KEY DEFAULT ('appr-' || substr(md5(random()::text), 1, 8)),
    proposal_id TEXT NOT NULL REFERENCES public.action_proposals(id) ON DELETE CASCADE,
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'PENDING',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ,
    decision TEXT,
    rejection_reason TEXT,
    decided_by UUID REFERENCES public.profiles(id),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_approval_requests_trip_id ON public.approval_requests(trip_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_user_id ON public.approval_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON public.approval_requests(status);

-- ------------------------------------------------------------------------------
-- 3. Create action_executions Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.action_executions (
    id TEXT PRIMARY KEY DEFAULT ('exec-' || substr(md5(random()::text), 1, 8)),
    proposal_id TEXT NOT NULL REFERENCES public.action_proposals(id) ON DELETE CASCADE,
    approval_id TEXT NOT NULL REFERENCES public.approval_requests(id) ON DELETE CASCADE,
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'SUCCESS',
    provider TEXT NOT NULL DEFAULT 'MockProvider',
    confirmation_code TEXT,
    result_payload JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    latency_ms NUMERIC(10, 2) DEFAULT 0.0,
    is_demo BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_action_executions_trip_id ON public.action_executions(trip_id);
CREATE INDEX IF NOT EXISTS idx_action_executions_user_id ON public.action_executions(user_id);

-- ------------------------------------------------------------------------------
-- 4. Create approval_audit_events Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.approval_audit_events (
    id TEXT PRIMARY KEY DEFAULT ('aud-' || substr(md5(random()::text), 1, 8)),
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    proposal_id TEXT,
    approval_id TEXT,
    event_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor TEXT NOT NULL DEFAULT 'USER',
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_approval_audit_events_trip_id ON public.approval_audit_events(trip_id);
CREATE INDEX IF NOT EXISTS idx_approval_audit_events_user_id ON public.approval_audit_events(user_id);

-- ------------------------------------------------------------------------------
-- 5. Enable Row Level Security (RLS)
-- ------------------------------------------------------------------------------
ALTER TABLE public.action_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.action_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approval_audit_events ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------
-- 6. RLS Policies: User Data Isolation
-- ------------------------------------------------------------------------------
-- Proposals
DROP POLICY IF EXISTS "Users can view proposals for their own trips" ON public.action_proposals;
CREATE POLICY "Users can view proposals for their own trips"
    ON public.action_proposals FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert proposals for their own trips" ON public.action_proposals;
CREATE POLICY "Users can insert proposals for their own trips"
    ON public.action_proposals FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Approvals
DROP POLICY IF EXISTS "Users can view approvals for their own trips" ON public.approval_requests;
CREATE POLICY "Users can view approvals for their own trips"
    ON public.approval_requests FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update approvals for their own trips" ON public.approval_requests;
CREATE POLICY "Users can update approvals for their own trips"
    ON public.approval_requests FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert approvals for their own trips" ON public.approval_requests;
CREATE POLICY "Users can insert approvals for their own trips"
    ON public.approval_requests FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Executions
DROP POLICY IF EXISTS "Users can view executions for their own trips" ON public.action_executions;
CREATE POLICY "Users can view executions for their own trips"
    ON public.action_executions FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert executions for their own trips" ON public.action_executions;
CREATE POLICY "Users can insert executions for their own trips"
    ON public.action_executions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Audit Events
DROP POLICY IF EXISTS "Users can view approval audit events for their own trips" ON public.approval_audit_events;
CREATE POLICY "Users can view approval audit events for their own trips"
    ON public.approval_audit_events FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert approval audit events for their own trips" ON public.approval_audit_events;
CREATE POLICY "Users can insert approval audit events for their own trips"
    ON public.approval_audit_events FOR INSERT
    WITH CHECK (auth.uid() = user_id);
