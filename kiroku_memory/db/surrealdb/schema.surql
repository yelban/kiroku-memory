-- Kiroku Memory SurrealDB Schema
-- Equivalent to PostgreSQL schema with native graph support
-- Storage: SurrealKV (embedded, file-based)

-- ============================================
-- Resources: Append-only logs for provenance
-- ============================================
DEFINE TABLE resource SCHEMAFULL;

DEFINE FIELD created_at ON resource TYPE datetime DEFAULT time::now();
DEFINE FIELD source ON resource TYPE string;
DEFINE FIELD content ON resource TYPE string;
DEFINE FIELD metadata ON resource TYPE object DEFAULT {};

-- Indexes
DEFINE INDEX idx_resource_created_at ON resource FIELDS created_at;
DEFINE INDEX idx_resource_source ON resource FIELDS source;


-- ============================================
-- Items: Atomic facts with embeddings
-- ============================================
DEFINE TABLE item SCHEMAFULL;

DEFINE FIELD created_at ON item TYPE datetime DEFAULT time::now();
DEFINE FIELD resource ON item TYPE option<record<resource>>;
DEFINE FIELD subject ON item TYPE option<string>;
DEFINE FIELD predicate ON item TYPE option<string>;
DEFINE FIELD object ON item TYPE option<string>;
DEFINE FIELD category ON item TYPE option<string>;
DEFINE FIELD confidence ON item TYPE float DEFAULT 1.0;
DEFINE FIELD status ON item TYPE string DEFAULT 'active'
    ASSERT $value IN ['active', 'archived', 'deleted'];
DEFINE FIELD supersedes ON item TYPE option<record<item>>;
DEFINE FIELD canonical_subject ON item TYPE option<string>;
DEFINE FIELD canonical_object ON item TYPE option<string>;
DEFINE FIELD meta_about ON item TYPE option<record<item>>;

-- Embedding fields (stored inline for simplicity)
DEFINE FIELD embedding ON item TYPE option<array<float>>;
DEFINE FIELD embedding_model ON item TYPE option<string>;
DEFINE FIELD embedding_dim ON item TYPE option<int>;

-- Indexes
DEFINE INDEX idx_item_created_at ON item FIELDS created_at;
DEFINE INDEX idx_item_category ON item FIELDS category;
DEFINE INDEX idx_item_status ON item FIELDS status;
DEFINE INDEX idx_item_subject ON item FIELDS subject;
DEFINE INDEX idx_item_resource ON item FIELDS resource;
DEFINE INDEX idx_item_canonical_subject ON item FIELDS canonical_subject;
DEFINE INDEX idx_item_canonical_object ON item FIELDS canonical_object;
DEFINE INDEX idx_item_meta_about ON item FIELDS meta_about;

-- Vector index for similarity search (HNSW)
-- Note: Dimension must match embedding_dimensions in config (default 1536)
DEFINE INDEX idx_item_embedding ON item FIELDS embedding HNSW DIMENSION 1536 DIST COSINE;


-- ============================================
-- Categories: Evolving summaries
-- ============================================
DEFINE TABLE category SCHEMAFULL;

DEFINE FIELD name ON category TYPE string;
DEFINE FIELD summary ON category TYPE option<string>;
DEFINE FIELD updated_at ON category TYPE datetime DEFAULT time::now();

-- Unique index on name
DEFINE INDEX idx_category_name ON category FIELDS name UNIQUE;


-- ============================================
-- Category Accesses: Track usage for priority
-- ============================================
DEFINE TABLE category_access SCHEMAFULL;

DEFINE FIELD category ON category_access TYPE string;
DEFINE FIELD accessed_at ON category_access TYPE datetime DEFAULT time::now();
DEFINE FIELD source ON category_access TYPE string DEFAULT 'context';

-- Indexes
DEFINE INDEX idx_access_category ON category_access FIELDS category;
DEFINE INDEX idx_access_accessed_at ON category_access FIELDS accessed_at;


-- ============================================
-- Graph Edges: Knowledge graph relationships
-- Using native RELATE for graph traversal
-- ============================================

-- Edge table for knowledge graph
-- Usage: RELATE item:a -> knows -> item:b SET weight = 0.8
DEFINE TABLE knows SCHEMAFULL TYPE RELATION IN item OUT item;
DEFINE FIELD weight ON knows TYPE float DEFAULT 1.0;
DEFINE FIELD created_at ON knows TYPE datetime DEFAULT time::now();

-- Generic edge table for custom predicates
-- Usage: RELATE item:a -> relates_to -> item:b SET predicate = "works_at"
DEFINE TABLE relates_to SCHEMAFULL TYPE RELATION IN item OUT item;
DEFINE FIELD predicate ON relates_to TYPE string;
DEFINE FIELD weight ON relates_to TYPE float DEFAULT 1.0;
DEFINE FIELD created_at ON relates_to TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_relates_predicate ON relates_to FIELDS predicate;


-- ============================================
-- Graph Edges: String-based knowledge graph
-- (Compatible with PostgreSQL schema)
-- ============================================
DEFINE TABLE graph_edge SCHEMAFULL;

DEFINE FIELD subject ON graph_edge TYPE string;
DEFINE FIELD predicate ON graph_edge TYPE string;
DEFINE FIELD object ON graph_edge TYPE string;
DEFINE FIELD weight ON graph_edge TYPE float DEFAULT 1.0;
DEFINE FIELD created_at ON graph_edge TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_edge_subject ON graph_edge FIELDS subject;
DEFINE INDEX idx_edge_object ON graph_edge FIELDS object;
DEFINE INDEX idx_edge_predicate ON graph_edge FIELDS predicate;


-- ============================================
-- Helper functions
-- ============================================

-- Function to search similar items by vector
DEFINE FUNCTION fn::search_similar($query_vec: array<float>, $limit: int, $min_sim: float) {
    SELECT
        *,
        vector::similarity::cosine(embedding, $query_vec) AS similarity
    FROM item
    WHERE status = 'active'
        AND embedding IS NOT NONE
        AND vector::similarity::cosine(embedding, $query_vec) >= $min_sim
    ORDER BY similarity DESC
    LIMIT $limit
};

-- Function to get item with related graph edges
DEFINE FUNCTION fn::item_with_relations($item_id: record<item>) {
    RETURN {
        item: (SELECT * FROM $item_id),
        outgoing: (SELECT * FROM relates_to WHERE in = $item_id),
        incoming: (SELECT * FROM relates_to WHERE out = $item_id),
    }
};

-- Function to traverse graph from an entity
DEFINE FUNCTION fn::traverse_from($start: record<item>, $depth: int) {
    -- For depth 1, just get direct connections
    IF $depth <= 1 THEN
        RETURN SELECT * FROM relates_to WHERE in = $start OR out = $start
    END;
    -- For deeper traversal, use recursive pattern
    -- Note: SurrealDB graph traversal with ->relates_to->item pattern
    RETURN SELECT * FROM $start->relates_to.* LIMIT 100
};
