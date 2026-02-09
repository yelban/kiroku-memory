"""FastAPI endpoints for memory system"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .db.database import init_db, close_db
from .db.repositories.factory import get_unit_of_work
from .db.entities import ResourceEntity, ItemEntity, CategoryEntity, GraphEdgeEntity
from .entity_resolution import resolve_entity
from .extract import extract_and_store, process_pending_resources
from .classify import classify_item
from .conflict import auto_resolve_conflicts
from .summarize import build_all_summaries, get_tiered_context
from .jobs import run_nightly_consolidation, run_weekly_maintenance, run_monthly_reindex
from .observability import metrics, get_health_status, logger


app = FastAPI(
    title="Kiroku Memory API",
    description="Tiered Retrieval Memory System for AI Agents",
    version="0.1.22",
)

# CORS middleware for Tauri desktop app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local desktop app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Schemas ============

class IngestRequest(BaseModel):
    content: str
    source: str
    metadata: Optional[dict] = None


class IngestResponse(BaseModel):
    resource_id: UUID
    created_at: datetime


class ResourceOut(BaseModel):
    id: UUID
    created_at: datetime
    source: str
    content: str
    metadata: dict = Field(validation_alias="metadata_")

    class Config:
        from_attributes = True


class ItemOut(BaseModel):
    id: UUID
    created_at: datetime
    subject: Optional[str]
    predicate: Optional[str]
    object: Optional[str]
    category: Optional[str]
    confidence: float
    status: str

    class Config:
        from_attributes = True


class CategoryOut(BaseModel):
    id: UUID
    name: str
    summary: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class RetrievalResponse(BaseModel):
    """Tiered retrieval response: summaries first, then items"""
    query: str
    categories: list[CategoryOut]
    items: list[ItemOut]
    total_items: int


# ============ Lifecycle ============

@app.on_event("startup")
async def startup():
    from .db.config import settings

    if settings.backend == "surrealdb":
        from .db.surrealdb import init_surreal_db
        await init_surreal_db()
    else:
        await init_db()



@app.on_event("shutdown")
async def shutdown():
    from .db.config import settings

    if settings.backend == "surrealdb":
        from .db.surrealdb import close_surreal_db
        await close_surreal_db()
    else:
        await close_db()


# ============ Helpers ============

UUID_NS = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # RFC 4122 DNS namespace


async def _get_categories_from_items(uow) -> list[CategoryOut]:
    """Aggregate categories from items, attach summary cache."""
    from uuid import uuid5

    cat_names = await uow.items.list_distinct_categories(status="active")
    result = []
    for name in sorted(cat_names):
        cached = await uow.categories.get_by_name(name)
        result.append(CategoryOut(
            id=cached.id if cached else uuid5(UUID_NS, name),
            name=name,
            summary=cached.summary if cached else None,
            updated_at=cached.updated_at if cached else datetime.utcnow(),
        ))
    return result


# ============ Endpoints ============

@app.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(request: IngestRequest):
    """Ingest a raw message into memory"""
    async with get_unit_of_work() as uow:
        entity = ResourceEntity(
            content=request.content,
            source=request.source,
            metadata=request.metadata or {},
        )
        resource_id = await uow.resources.create(entity)
        await uow.commit()
        resource = await uow.resources.get(resource_id)
        return IngestResponse(
            resource_id=resource_id,
            created_at=resource.created_at,
        )


@app.get("/resources", response_model=list[ResourceOut])
async def list_resources_endpoint(
    source: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 100,
):
    """List raw resources"""
    async with get_unit_of_work() as uow:
        entities = await uow.resources.list(source=source, since=since, limit=limit)
        return [
            ResourceOut(
                id=e.id,
                created_at=e.created_at,
                source=e.source,
                content=e.content,
                metadata_=e.metadata,
            )
            for e in entities
        ]


@app.get("/resources/{resource_id}", response_model=ResourceOut)
async def get_resource_endpoint(resource_id: UUID):
    """Get a specific resource by ID"""
    async with get_unit_of_work() as uow:
        entity = await uow.resources.get(resource_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Resource not found")
        return ResourceOut(
            id=entity.id,
            created_at=entity.created_at,
            source=entity.source,
            content=entity.content,
            metadata_=entity.metadata,
        )


@app.get("/retrieve", response_model=RetrievalResponse)
async def retrieve_memory(
    query: str,
    category: Optional[str] = None,
    limit: int = 20,
):
    """
    Tiered memory retrieval with intent-driven smart search.

    Automatically classifies query intent and routes to the best strategy
    (entity lookup, temporal, aspect filter, or semantic search).
    Returns category summaries first (for quick context),
    then relevant items for drill-down.
    """
    from .search import smart_search

    async with get_unit_of_work() as uow:
        # Get categories from items (source of truth)
        all_categories = await _get_categories_from_items(uow)
        if category:
            all_categories = [c for c in all_categories if c.name == category]

        # Use smart_search for intent-driven retrieval
        search_result = await smart_search(
            query=query, uow=uow, category=category, limit=limit,
        )

        # Count total
        total = await uow.items.count(category=category, status="active")

        return RetrievalResponse(
            query=query,
            categories=all_categories,
            items=[
                ItemOut(
                    id=r["id"],
                    created_at=r.get("created_at", datetime.utcnow()),
                    subject=r.get("subject"),
                    predicate=r.get("predicate"),
                    object=r.get("object"),
                    category=r.get("category"),
                    confidence=r.get("confidence", 1.0),
                    status=r.get("status", "active"),
                )
                for r in search_result["items"]
            ],
            total_items=total,
        )


@app.get("/categories", response_model=list[CategoryOut])
async def list_categories():
    """List all categories with summaries (derived from items)"""
    async with get_unit_of_work() as uow:
        return await _get_categories_from_items(uow)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": app.version}


# ============ Phase 2: Intelligence ============

class ExtractRequest(BaseModel):
    resource_id: UUID


class ExtractResponse(BaseModel):
    resource_id: UUID
    items_created: int
    item_ids: list[UUID]


@app.post("/extract", response_model=ExtractResponse)
async def extract_endpoint(request: ExtractRequest):
    """Extract facts from a resource into items"""
    async with get_unit_of_work() as uow:
        item_ids = await extract_and_store(uow, request.resource_id)
        # Auto-classify and resolve conflicts
        for item_id in item_ids:
            await classify_item(uow, item_id, use_llm=False)
            await auto_resolve_conflicts(uow, item_id)
        await uow.commit()
        return ExtractResponse(
            resource_id=request.resource_id,
            items_created=len(item_ids),
            item_ids=item_ids,
        )


@app.post("/process")
async def process_endpoint(limit: int = 100):
    """Process pending resources (extract facts)"""
    async with get_unit_of_work() as uow:
        count = await process_pending_resources(uow, limit=limit)
        await uow.commit()
        return {"processed": count}


@app.post("/summarize")
async def summarize_endpoint():
    """Build summaries for all categories"""
    async with get_unit_of_work() as uow:
        summaries = await build_all_summaries(uow)
        await uow.commit()
        return {"summaries": summaries}


@app.get("/context")
async def context_endpoint(
    categories: Optional[str] = None,
    max_chars: Optional[int] = None,
    max_items_per_category: int = 10,
):
    """
    Get tiered context for agent prompt.

    Categories are ordered by priority (preferences > facts > goals > etc.)
    with dynamic adjustment based on usage frequency and recency.

    Args:
        categories: Comma-separated list of categories to include
        max_chars: Maximum characters (truncates by complete category, never mid-block)
        max_items_per_category: Max recent items per category (default: 10)
    """
    async with get_unit_of_work() as uow:
        cat_list = categories.split(",") if categories else None
        context = await get_tiered_context(
            uow,
            cat_list,
            max_items_per_category=max_items_per_category,
            max_chars=max_chars,
        )
        await uow.commit()
        return {"context": context}


@app.get("/items", response_model=list[ItemOut])
async def list_items(
    category: Optional[str] = None,
    status: str = "active",
    limit: int = 100,
):
    """List items with optional filters"""
    async with get_unit_of_work() as uow:
        entities = await uow.items.list(category=category, status=status, limit=limit)
        return [
            ItemOut(
                id=e.id,
                created_at=e.created_at,
                subject=e.subject,
                predicate=e.predicate,
                object=e.object,
                category=e.category,
                confidence=e.confidence,
                status=e.status,
            )
            for e in entities
        ]


# ============ Phase 3: Maintenance Jobs ============

@app.post("/jobs/nightly")
async def nightly_job():
    """Run nightly consolidation job"""
    async with get_unit_of_work() as uow:
        stats = await run_nightly_consolidation(uow)
        await uow.commit()
        return stats


@app.post("/jobs/weekly")
async def weekly_job():
    """Run weekly maintenance job"""
    async with get_unit_of_work() as uow:
        stats = await run_weekly_maintenance(uow)
        await uow.commit()
        return stats


@app.post("/jobs/monthly")
async def monthly_job():
    """Run monthly re-indexing job"""
    async with get_unit_of_work() as uow:
        stats = await run_monthly_reindex(uow)
        await uow.commit()
        return stats


# ============ Phase 4: Observability ============

@app.get("/metrics")
async def metrics_endpoint():
    """Get application metrics"""
    return metrics.to_dict()


@app.post("/metrics/reset")
async def reset_metrics():
    """Reset all metrics"""
    metrics.reset()
    return {"status": "reset"}


@app.get("/health/detailed")
async def detailed_health():
    """Get detailed health status"""
    async with get_unit_of_work() as uow:
        status = await get_health_status(uow)
        return status


# ============ V2 Endpoints (Repository Pattern) ============

@app.post("/v2/ingest", response_model=IngestResponse, tags=["v2"])
async def ingest_v2_endpoint(request: IngestRequest):
    """
    Ingest a raw message into memory (v2 - uses repository pattern).

    This endpoint uses the new repository pattern that supports
    multiple backends (PostgreSQL, SurrealDB).
    """
    async with get_unit_of_work() as uow:
        entity = ResourceEntity(
            content=request.content,
            source=request.source,
            metadata=request.metadata or {},
        )
        resource_id = await uow.resources.create(entity)
        resource = await uow.resources.get(resource_id)
        return IngestResponse(
            resource_id=resource_id,
            created_at=resource.created_at,
        )


@app.get("/v2/resources", response_model=list[ResourceOut], tags=["v2"])
async def list_resources_v2_endpoint(
    source: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 100,
):
    """List raw resources (v2 - uses repository pattern)"""
    async with get_unit_of_work() as uow:
        entities = await uow.resources.list(source=source, since=since, limit=limit)
        # Convert entities to response format
        return [
            ResourceOut(
                id=e.id,
                created_at=e.created_at,
                source=e.source,
                content=e.content,
                metadata_=e.metadata,
            )
            for e in entities
        ]


@app.get("/v2/items", response_model=list[ItemOut], tags=["v2"])
async def list_items_v2(
    category: Optional[str] = None,
    status: str = "active",
    limit: int = 100,
):
    """List items with optional filters (v2 - uses repository pattern)"""
    async with get_unit_of_work() as uow:
        entities = await uow.items.list(category=category, status=status, limit=limit)
        return [
            ItemOut(
                id=e.id,
                created_at=e.created_at,
                subject=e.subject,
                predicate=e.predicate,
                object=e.object,
                category=e.category,
                confidence=e.confidence,
                status=e.status,
            )
            for e in entities
        ]


class CreateItemRequest(BaseModel):
    """Request to create a structured memory item directly (no LLM extraction needed)"""
    subject: str = Field(..., description="What/who the fact is about")
    predicate: str = Field(..., description="The relationship or action")
    object: str = Field(..., description="The value or target")
    category: Optional[str] = Field(None, description="Category name (preferences, facts, goals, etc.)")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")


@app.post("/v2/items", response_model=ItemOut, tags=["v2"])
async def create_item_v2(request: CreateItemRequest):
    """
    Create a structured memory item directly.

    This endpoint allows storing pre-extracted facts without requiring OpenAI API.
    Useful for Claude Code integration where Claude does the extraction.
    Auto-generates embedding and graph edge when possible.
    """
    from uuid import uuid4
    from datetime import datetime, timezone

    async with get_unit_of_work() as uow:
        # Use UTC time but remove tzinfo for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        entity = ItemEntity(
            id=uuid4(),
            created_at=now,
            subject=request.subject,
            predicate=request.predicate,
            object=request.object,
            category=request.category,
            confidence=request.confidence,
            status="active",
            canonical_subject=resolve_entity(request.subject) if request.subject else None,
            canonical_object=resolve_entity(request.object) if request.object else None,
        )

        item_id = await uow.items.create(entity)

        # Auto-generate embedding (skip if no OpenAI key)
        try:
            from .embedding.factory import generate_embedding, get_embedding_provider
            provider = get_embedding_provider()
            text = provider.build_text_for_item(
                request.subject, request.predicate, request.object, request.category
            )
            vector = await generate_embedding(text)
            await uow.embeddings.upsert(item_id, vector)
        except Exception:
            logger.debug("Skipping embedding generation (provider unavailable)")

        # Auto-create graph edge (use canonical forms)
        if request.subject and request.predicate and request.object:
            try:
                edge = GraphEdgeEntity(
                    subject=resolve_entity(request.subject),
                    predicate=request.predicate,
                    object=resolve_entity(request.object),
                )
                await uow.graph.create(edge)
            except Exception:
                logger.debug("Skipping graph edge creation")

        await uow.commit()

        return ItemOut(
            id=item_id,
            created_at=now,
            subject=request.subject,
            predicate=request.predicate,
            object=request.object,
            category=request.category,
            confidence=request.confidence,
            status="active",
        )


class MetaFactOut(BaseModel):
    """Meta-fact output"""
    id: UUID
    predicate: str
    object: Optional[str]
    confidence: float
    created_at: datetime
    meta_about: UUID

    class Config:
        from_attributes = True


class CreateMetaFactRequest(BaseModel):
    """Request to create a meta-fact about an item"""
    predicate: str = Field(..., description="Meta relationship (e.g. has_source, verified_by)")
    object: str = Field(..., description="Meta value (e.g. gpt-4o-mini, user)")
    confidence: float = Field(1.0, ge=0.0, le=1.0)


@app.get("/v2/items/{item_id}/meta", response_model=list[MetaFactOut], tags=["v2"])
async def get_item_meta(item_id: UUID):
    """Get all meta-facts about an item"""
    async with get_unit_of_work() as uow:
        item = await uow.items.get(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        meta_facts = await uow.items.get_meta_facts(item_id)
        return [
            MetaFactOut(
                id=m.id,
                predicate=m.predicate,
                object=m.object,
                confidence=m.confidence,
                created_at=m.created_at,
                meta_about=m.meta_about,
            )
            for m in meta_facts
        ]


@app.post("/v2/items/{item_id}/meta", response_model=MetaFactOut, tags=["v2"])
async def create_item_meta(item_id: UUID, request: CreateMetaFactRequest):
    """Create a meta-fact about an item"""
    async with get_unit_of_work() as uow:
        item = await uow.items.get(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        meta_id = await uow.items.create_meta_fact(
            about_item_id=item_id,
            predicate=request.predicate,
            object_value=request.object,
            confidence=request.confidence,
        )
        await uow.commit()
        meta = await uow.items.get(meta_id)
        return MetaFactOut(
            id=meta.id,
            predicate=meta.predicate,
            object=meta.object,
            confidence=meta.confidence,
            created_at=meta.created_at,
            meta_about=meta.meta_about,
        )


@app.get("/v2/categories", response_model=list[CategoryOut], tags=["v2"])
async def list_categories_v2():
    """List all categories with summaries (v2 - derived from items)"""
    async with get_unit_of_work() as uow:
        return await _get_categories_from_items(uow)


@app.get("/v2/stats")
async def stats_v2():
    """Get memory statistics (v2 - uses repository pattern)"""
    from .db.config import settings

    async with get_unit_of_work() as uow:
        total_items = await uow.items.count()
        active_items = await uow.items.count(status="active")
        archived_items = await uow.items.count(status="archived")
        cat_names = await uow.items.list_distinct_categories(status="active")

        return {
            "backend": settings.backend,
            "items": {
                "total": total_items,
                "active": active_items,
                "archived": archived_items,
            },
            "categories": len(cat_names),
        }


# ============ Search & Graph ============

class SearchResultOut(BaseModel):
    """Single search result"""
    id: UUID
    subject: Optional[str]
    predicate: Optional[str]
    object: Optional[str]
    category: Optional[str]
    confidence: float
    similarity: float

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Search response"""
    query: str
    intent: str
    results: list[SearchResultOut]
    total: int


class GraphEdgeOut(BaseModel):
    """Graph edge output"""
    id: UUID
    subject: str
    predicate: str
    object: str
    weight: float

    class Config:
        from_attributes = True


class GraphNeighborsResponse(BaseModel):
    """Graph neighbors response"""
    entity: str
    depth: int
    edges: list[GraphEdgeOut]
    total: int


@app.get("/search", response_model=SearchResponse, tags=["search"])
async def search_endpoint(
    q: str,
    category: Optional[str] = None,
    limit: int = 10,
    min_similarity: float = 0.5,
):
    """
    Smart search with intent-driven retrieval.

    Automatically classifies query intent and routes to the best strategy:
    - Entity lookup: "about X" → graph traversal + item search
    - Temporal: "recent", "last week" → time-filtered items
    - Aspect filter: "preferences", "goals" → category-filtered items
    - Semantic search: free text → embedding similarity search
    """
    from .search import smart_search

    async with get_unit_of_work() as uow:
        results = await smart_search(
            query=q,
            uow=uow,
            category=category,
            limit=limit,
            min_similarity=min_similarity,
        )

        return SearchResponse(
            query=q,
            intent=results["intent"],
            results=[
                SearchResultOut(
                    id=r["id"],
                    subject=r.get("subject"),
                    predicate=r.get("predicate"),
                    object=r.get("object"),
                    category=r.get("category"),
                    confidence=r.get("confidence", 1.0),
                    similarity=r.get("similarity", 1.0),
                )
                for r in results["items"]
            ],
            total=results["total"],
        )


class GraphPathOut(BaseModel):
    """Graph path output"""
    source: str
    target: str
    hops: list[str]
    edges: list[GraphEdgeOut]
    distance: int
    weight: float


class GraphPathsResponse(BaseModel):
    """Graph paths response"""
    source: str
    target: Optional[str]
    max_depth: int
    paths: list[GraphPathOut]
    total: int


@app.get("/graph/paths", response_model=GraphPathsResponse, tags=["graph"])
async def graph_paths_endpoint(
    source: str,
    target: Optional[str] = None,
    max_depth: int = 2,
    max_paths: int = 20,
):
    """
    Find paths through the knowledge graph using BFS.

    Returns all reachable paths from source, or only paths to target if specified.
    max_depth is capped at 3 to prevent explosion.
    """
    async with get_unit_of_work() as uow:
        paths = await uow.graph.find_paths(
            source=source,
            target=target,
            max_depth=min(max_depth, 3),
            max_paths=max_paths,
        )
        return GraphPathsResponse(
            source=source,
            target=target,
            max_depth=min(max_depth, 3),
            paths=[
                GraphPathOut(
                    source=p.source,
                    target=p.target,
                    hops=p.hops,
                    edges=[
                        GraphEdgeOut(
                            id=e.id,
                            subject=e.subject,
                            predicate=e.predicate,
                            object=e.object,
                            weight=e.weight,
                        )
                        for e in p.edges
                    ],
                    distance=p.distance,
                    weight=p.weight,
                )
                for p in paths
            ],
            total=len(paths),
        )


@app.get("/graph/neighbors", response_model=GraphNeighborsResponse, tags=["graph"])
async def graph_neighbors_endpoint(
    entity: str,
    depth: int = 1,
):
    """
    Get knowledge graph neighbors for an entity.

    Returns all edges within N hops of the given entity name.
    """
    async with get_unit_of_work() as uow:
        edges = await uow.graph.get_neighbors(entity, depth=depth)
        return GraphNeighborsResponse(
            entity=entity,
            depth=depth,
            edges=[
                GraphEdgeOut(
                    id=e.id,
                    subject=e.subject,
                    predicate=e.predicate,
                    object=e.object,
                    weight=e.weight,
                )
                for e in edges
            ],
            total=len(edges),
        )
