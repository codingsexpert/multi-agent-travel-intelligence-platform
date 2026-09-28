-- ==============================================================================
-- Multi-Agent AI Travel Intelligence Platform
-- Migration: 20260928000003_pgvector_rag.sql
-- Description: pgvector extension, travel_documents table, vector index,
--              Row Level Security policies, and cosine similarity search RPC.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Enable pgvector Extension
-- ------------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;

-- ------------------------------------------------------------------------------
-- 2. Dedicated Table for Knowledge Base Documents and Vector Embeddings
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.travel_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    source TEXT NOT NULL,
    source_url TEXT,
    source_trust TEXT NOT NULL DEFAULT 'CURATED' CHECK (source_trust IN ('OFFICIAL', 'CURATED', 'REFERENCE', 'UNKNOWN')),
    destination TEXT,
    country TEXT,
    category TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_public BOOLEAN NOT NULL DEFAULT true,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 3. Automatic updated_at Trigger
-- ------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_travel_documents_updated_at ON public.travel_documents;
CREATE TRIGGER trg_travel_documents_updated_at
BEFORE UPDATE ON public.travel_documents
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ------------------------------------------------------------------------------
-- 4. Vector and B-Tree Indexes
-- ------------------------------------------------------------------------------
-- HNSW vector similarity search index using cosine distance
CREATE INDEX IF NOT EXISTS idx_travel_documents_embedding_hnsw
    ON public.travel_documents USING hnsw (embedding vector_cosine_ops);

-- Standard relational indexes for hybrid metadata filtering
CREATE INDEX IF NOT EXISTS idx_travel_documents_destination ON public.travel_documents(destination);
CREATE INDEX IF NOT EXISTS idx_travel_documents_country ON public.travel_documents(country);
CREATE INDEX IF NOT EXISTS idx_travel_documents_category ON public.travel_documents(category);
CREATE INDEX IF NOT EXISTS idx_travel_documents_user_id ON public.travel_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_travel_documents_document_id ON public.travel_documents(document_id);
CREATE INDEX IF NOT EXISTS idx_travel_documents_is_public ON public.travel_documents(is_public);
CREATE INDEX IF NOT EXISTS idx_travel_documents_content_hash ON public.travel_documents(content_hash);

-- ------------------------------------------------------------------------------
-- 5. Row Level Security (RLS) Policies
-- ------------------------------------------------------------------------------
ALTER TABLE public.travel_documents ENABLE ROW LEVEL SECURITY;

-- Policy 1: Anyone (authenticated or anonymous) can view global public curated documents
DROP POLICY IF EXISTS "Anyone can view public travel documents" ON public.travel_documents;
CREATE POLICY "Anyone can view public travel documents"
    ON public.travel_documents
    FOR SELECT
    USING (is_public = true);

-- Policy 2: Authenticated users can view their own private travel documents
DROP POLICY IF EXISTS "Users can view their private documents" ON public.travel_documents;
CREATE POLICY "Users can view their private documents"
    ON public.travel_documents
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy 3: Authenticated users can insert their own private travel documents
DROP POLICY IF EXISTS "Users can insert their private documents" ON public.travel_documents;
CREATE POLICY "Users can insert their private documents"
    ON public.travel_documents
    FOR INSERT
    WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- Policy 4: Authenticated users can update their own private travel documents
DROP POLICY IF EXISTS "Users can update their private documents" ON public.travel_documents;
CREATE POLICY "Users can update their private documents"
    ON public.travel_documents
    FOR UPDATE
    USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Policy 5: Authenticated users can delete their own private travel documents
DROP POLICY IF EXISTS "Users can delete their private documents" ON public.travel_documents;
CREATE POLICY "Users can delete their private documents"
    ON public.travel_documents
    FOR DELETE
    USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- ------------------------------------------------------------------------------
-- 6. Stored Procedure for Hybrid Vector + Metadata Similarity Retrieval
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.match_travel_documents (
    query_embedding vector(1536),
    match_count int DEFAULT 4,
    filter_destination text DEFAULT NULL,
    filter_country text DEFAULT NULL,
    filter_category text DEFAULT NULL,
    filter_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    document_id text,
    chunk_id text,
    title text,
    content text,
    source text,
    source_url text,
    source_trust text,
    destination text,
    country text,
    category text,
    metadata jsonb,
    is_public boolean,
    user_id uuid,
    similarity float
)
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        td.id,
        td.document_id,
        td.chunk_id,
        td.title,
        td.content,
        td.source,
        td.source_url,
        td.source_trust,
        td.destination,
        td.country,
        td.category,
        td.metadata,
        td.is_public,
        td.user_id,
        1 - (td.embedding <=> query_embedding) AS similarity
    FROM public.travel_documents td
    WHERE
        -- Security filter: public or owned by user
        (td.is_public = true OR (filter_user_id IS NOT NULL AND td.user_id = filter_user_id))
        -- Metadata filters (case-insensitive)
        AND (filter_destination IS NULL OR LOWER(td.destination) = LOWER(filter_destination))
        AND (filter_country IS NULL OR LOWER(td.country) = LOWER(filter_country))
        AND (filter_category IS NULL OR LOWER(td.category) = LOWER(filter_category))
    ORDER BY td.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
