-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create reels table
CREATE TABLE IF NOT EXISTS reels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_url TEXT NOT NULL,
    storage_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create analyses table
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reel_id UUID REFERENCES reels(id) ON DELETE CASCADE NOT NULL,
    analysis_text TEXT NOT NULL,
    embedding vector(384) -- Using 384 dimensions assuming all-MiniLM-L6-v2 model or similar
);

-- Note: We assume the Supabase Storage bucket 'reels' is created manually via the Supabase Dashboard.
-- Ensure the 'reels' bucket is set to PUBLIC so that the frontend can read the video URLs.

-- Create match_documents function for vector similarity search (cosine distance)
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding vector(384),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id UUID,
  reel_id UUID,
  analysis_text TEXT,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    analyses.id,
    analyses.reel_id,
    analyses.analysis_text,
    1 - (analyses.embedding <=> query_embedding) AS similarity
  FROM analyses
  WHERE 1 - (analyses.embedding <=> query_embedding) > match_threshold
  ORDER BY analyses.embedding <=> query_embedding
  LIMIT match_count;
$$;
