"""Observability - Structured logging and metrics"""

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional

import json


# ============ Structured Logging ============

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(level: str = "INFO", json_format: bool = True) -> logging.Logger:
    """
    Setup structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON format for logs

    Returns:
        Configured logger
    """
    logger = logging.getLogger("memory")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    handler = logging.StreamHandler()
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    logger.addHandler(handler)
    return logger


# Global logger
logger = setup_logging()


def log_with_context(**context):
    """Create a log record with extra context"""
    class ContextAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            kwargs.setdefault("extra", {})
            kwargs["extra"]["extra"] = {**self.extra, **kwargs["extra"].get("extra", {})}
            return msg, kwargs

    return ContextAdapter(logger, context)


# ============ Metrics ============

@dataclass
class Metrics:
    """In-memory metrics collector"""

    # Counters
    ingest_count: int = 0
    extract_count: int = 0
    retrieve_count: int = 0
    conflict_count: int = 0
    error_count: int = 0

    # Latency histograms (simplified as lists)
    ingest_latencies: list[float] = field(default_factory=list)
    extract_latencies: list[float] = field(default_factory=list)
    retrieve_latencies: list[float] = field(default_factory=list)

    # Gauges
    active_items: int = 0
    archived_items: int = 0
    total_resources: int = 0
    total_embeddings: int = 0

    # Cache for hit rate
    cache_hits: int = 0
    cache_misses: int = 0

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter"""
        if hasattr(self, name):
            setattr(self, name, getattr(self, name) + value)

    def record_latency(self, name: str, latency_ms: float) -> None:
        """Record a latency measurement"""
        latency_list = getattr(self, f"{name}_latencies", None)
        if latency_list is not None:
            latency_list.append(latency_ms)
            # Keep last 1000 measurements
            if len(latency_list) > 1000:
                latency_list.pop(0)

    def set_gauge(self, name: str, value: int) -> None:
        """Set a gauge value"""
        if hasattr(self, name):
            setattr(self, name, value)

    def get_percentile(self, name: str, percentile: float) -> Optional[float]:
        """Get percentile from latency histogram"""
        latencies = getattr(self, f"{name}_latencies", [])
        if not latencies:
            return None
        sorted_latencies = sorted(latencies)
        idx = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        """Export metrics as dictionary"""
        return {
            "counters": {
                "ingest_count": self.ingest_count,
                "extract_count": self.extract_count,
                "retrieve_count": self.retrieve_count,
                "conflict_count": self.conflict_count,
                "error_count": self.error_count,
            },
            "latencies": {
                "ingest_p50": self.get_percentile("ingest", 50),
                "ingest_p95": self.get_percentile("ingest", 95),
                "ingest_p99": self.get_percentile("ingest", 99),
                "extract_p50": self.get_percentile("extract", 50),
                "extract_p95": self.get_percentile("extract", 95),
                "retrieve_p50": self.get_percentile("retrieve", 50),
                "retrieve_p95": self.get_percentile("retrieve", 95),
                "retrieve_p99": self.get_percentile("retrieve", 99),
            },
            "gauges": {
                "active_items": self.active_items,
                "archived_items": self.archived_items,
                "total_resources": self.total_resources,
                "total_embeddings": self.total_embeddings,
            },
            "cache": {
                "hit_rate": round(self.get_hit_rate(), 3),
                "hits": self.cache_hits,
                "misses": self.cache_misses,
            },
        }

    def reset(self) -> None:
        """Reset all metrics"""
        self.ingest_count = 0
        self.extract_count = 0
        self.retrieve_count = 0
        self.conflict_count = 0
        self.error_count = 0
        self.ingest_latencies.clear()
        self.extract_latencies.clear()
        self.retrieve_latencies.clear()
        self.cache_hits = 0
        self.cache_misses = 0


# Global metrics instance
metrics = Metrics()


# ============ Decorators ============

def track_latency(operation: str):
    """Decorator to track operation latency"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                metrics.record_latency(operation, elapsed_ms)
                metrics.increment(f"{operation}_count")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                metrics.record_latency(operation, elapsed_ms)
                metrics.increment(f"{operation}_count")

        if asyncio_iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def asyncio_iscoroutinefunction(func):
    """Check if function is async"""
    import asyncio
    return asyncio.iscoroutinefunction(func)


def track_errors(func: Callable):
    """Decorator to track errors"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            metrics.increment("error_count")
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            metrics.increment("error_count")
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise

    if asyncio_iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# ============ Health Check ============

async def get_health_status(uow) -> dict:
    """
    Get comprehensive health status.

    Args:
        uow: Unit of work

    Returns:
        Health status dict
    """
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
    }

    # Database/data check
    try:
        active_items = await uow.items.count(status="active")
        total_resources = await uow.resources.count()
        total_embeddings = await uow.embeddings.count()

        # Update gauges
        metrics.set_gauge("active_items", active_items)
        metrics.set_gauge("total_resources", total_resources)
        metrics.set_gauge("total_embeddings", total_embeddings)

        status["checks"]["database"] = {"status": "ok"}
        status["checks"]["data"] = {
            "status": "ok",
            "active_items": active_items,
            "resources": total_resources,
            "embeddings": total_embeddings,
        }
    except Exception as e:
        status["checks"]["database"] = {"status": "error", "message": str(e)}
        status["checks"]["data"] = {"status": "error", "message": str(e)}
        status["status"] = "unhealthy"

    return status
