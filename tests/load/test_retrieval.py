"""Load testing for retrieval performance via API"""

import asyncio
import time
import random
import string

import pytest
import httpx


# Test configuration
BASE_URL = "http://localhost:8000"
NUM_ITEMS = 100
TARGET_LATENCY_MS = 500


def random_text(length: int = 50) -> str:
    """Generate random text"""
    return "".join(random.choices(string.ascii_letters + " ", k=length))


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for module scope"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def http_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Check if server is running
        try:
            response = await client.get("/health")
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("API server not running. Start with: uv run uvicorn memory.api:app")
        yield client


@pytest.fixture(scope="module")
async def setup_test_data(http_client):
    """Setup test data via API"""
    print(f"\nCreating {NUM_ITEMS} test items via API...")
    start = time.perf_counter()

    for i in range(NUM_ITEMS):
        content = f"Test user_{i % 20} likes {random_text(20)} and prefers {random_text(10)}"
        response = await http_client.post(
            "/ingest",
            json={"content": content, "source": "load_test"}
        )
        assert response.status_code == 200

    elapsed = time.perf_counter() - start
    print(f"Created {NUM_ITEMS} items in {elapsed:.2f}s")
    yield


@pytest.mark.asyncio
async def test_health_endpoint(http_client):
    """Test health endpoint"""
    response = await http_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    print(f"\nHealth: {data}")


@pytest.mark.asyncio
async def test_retrieve_latency(http_client, setup_test_data):
    """Test retrieve endpoint latency"""
    latencies = []

    for _ in range(30):
        start = time.perf_counter()
        response = await http_client.get("/retrieve", params={"query": "preferences"})
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

        assert response.status_code == 200

    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    print(f"\nRetrieve latency:")
    print(f"  Average: {avg_latency:.2f}ms")
    print(f"  P95: {p95_latency:.2f}ms")

    assert p95_latency < TARGET_LATENCY_MS


@pytest.mark.asyncio
async def test_items_endpoint(http_client, setup_test_data):
    """Test items listing latency"""
    latencies = []

    for _ in range(30):
        start = time.perf_counter()
        response = await http_client.get("/items", params={"limit": 20})
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

        assert response.status_code == 200

    avg_latency = sum(latencies) / len(latencies)
    print(f"\nItems listing latency: {avg_latency:.2f}ms avg")

    assert avg_latency < TARGET_LATENCY_MS


@pytest.mark.asyncio
async def test_categories_endpoint(http_client, setup_test_data):
    """Test categories endpoint"""
    response = await http_client.get("/categories")
    assert response.status_code == 200

    categories = response.json()
    print(f"\nCategories: {len(categories)}")

    assert len(categories) > 0


@pytest.mark.asyncio
async def test_ingest_throughput(http_client):
    """Test ingestion throughput"""
    num_messages = 20
    latencies = []

    for i in range(num_messages):
        start = time.perf_counter()
        response = await http_client.post(
            "/ingest",
            json={
                "content": f"Throughput test {i}: {random_text(30)}",
                "source": "throughput_test"
            }
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

        assert response.status_code == 200

    avg_latency = sum(latencies) / len(latencies)
    throughput = num_messages / (sum(latencies) / 1000)

    print(f"\nIngestion throughput:")
    print(f"  Average latency: {avg_latency:.2f}ms")
    print(f"  Throughput: {throughput:.2f} msg/s")


@pytest.mark.asyncio
async def test_metrics_endpoint(http_client, setup_test_data):
    """Test metrics endpoint"""
    response = await http_client.get("/metrics")
    assert response.status_code == 200

    metrics = response.json()
    print(f"\nMetrics:")
    print(f"  Counters: {metrics.get('counters', {})}")
    print(f"  Latencies: {metrics.get('latencies', {})}")


@pytest.mark.asyncio
async def test_detailed_health(http_client, setup_test_data):
    """Test detailed health endpoint"""
    response = await http_client.get("/health/detailed")
    assert response.status_code == 200

    health = response.json()
    print(f"\nDetailed health: {health.get('status')}")
    print(f"  Checks: {health.get('checks', {})}")

    assert health["status"] == "healthy"
