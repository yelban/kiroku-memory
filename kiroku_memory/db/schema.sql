-- AI Agent Memory System Schema
-- PostgreSQL 15+ with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Raw Resources: append-only logs for provenance
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_resources_created_at ON resources(created_at DESC);
CREATE INDEX idx_resources_source ON resources(source);

-- Items: atomic facts extracted from resources
CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resource_id UUID REFERENCES resources(id) ON DELETE SET NULL,
    subject TEXT,
    predicate TEXT,
    object TEXT,
    category TEXT,
    confidence FLOAT DEFAULT 1.0,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    supersedes UUID REFERENCES items(id) ON DELETE SET NULL
);

CREATE INDEX idx_items_created_at ON items(created_at DESC);
CREATE INDEX idx_items_category ON items(category);
CREATE INDEX idx_items_status ON items(status);
CREATE INDEX idx_items_subject ON items(subject);
CREATE INDEX idx_items_resource_id ON items(resource_id);

-- Categories: evolving summaries
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    summary TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_categories_name ON categories(name);

-- Graph Edges: knowledge graph relationships
CREATE TABLE graph_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_graph_edges_subject ON graph_edges(subject);
CREATE INDEX idx_graph_edges_object ON graph_edges(object);
CREATE INDEX idx_graph_edges_predicate ON graph_edges(predicate);

-- Embeddings: vector index for semantic search
CREATE TABLE embeddings (
    item_id UUID PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,
    embedding VECTOR(1536)
);

-- Create HNSW index for fast similarity search
CREATE INDEX idx_embeddings_hnsw ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Category Accesses: track usage for dynamic priority
CREATE TABLE category_accesses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category TEXT NOT NULL,
    accessed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    source TEXT DEFAULT 'context'
);

CREATE INDEX idx_category_accesses_category ON category_accesses(category);
CREATE INDEX idx_category_accesses_accessed_at ON category_accesses(accessed_at DESC);
