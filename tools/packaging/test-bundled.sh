#!/bin/bash
# Test bundled Python with Kiroku Memory
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Detect architecture
ARCH=$(uname -m)
case "$ARCH" in
    arm64|aarch64)
        PBS_ARCH="aarch64"
        ;;
    x86_64)
        PBS_ARCH="x86_64"
        ;;
    *)
        echo "Error: Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

BUNDLED_PYTHON="$SCRIPT_DIR/dist/$PBS_ARCH/python/bin/python3"
PORT=8799
DATA_DIR="/tmp/kiroku-bundled-test-$$"

if [ ! -f "$BUNDLED_PYTHON" ]; then
    echo "Error: Bundled Python not found at $BUNDLED_PYTHON"
    echo "Run ./build-python.sh first"
    exit 1
fi

echo "=== Kiroku Memory Bundled Python Test ==="
echo "Python: $BUNDLED_PYTHON"
echo "Data: $DATA_DIR"
echo ""

# Create data directory
mkdir -p "$DATA_DIR"

# Start server
export PYTHONPATH="$PROJECT_ROOT"
export BACKEND=surrealdb
export SURREAL_URL="file://$DATA_DIR/kiroku"
export SURREAL_NAMESPACE=kiroku
export SURREAL_DATABASE=memory

echo "Starting server on port $PORT..."
$BUNDLED_PYTHON -m uvicorn kiroku_memory.api:app --host 127.0.0.1 --port $PORT &
SERVER_PID=$!

# Wait for startup
sleep 4

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    kill $SERVER_PID 2>/dev/null || true
    rm -rf "$DATA_DIR"
}
trap cleanup EXIT

# Test health
echo ""
echo "=== Test 1: Health Check ==="
HEALTH=$(curl -s http://127.0.0.1:$PORT/health)
echo "$HEALTH"
if echo "$HEALTH" | grep -q '"status":"ok"'; then
    echo "PASS: Health check succeeded"
else
    echo "FAIL: Health check failed"
    exit 1
fi

# Test stats (verify backend)
echo ""
echo "=== Test 2: Backend Verification ==="
STATS=$(curl -s http://127.0.0.1:$PORT/v2/stats)
echo "$STATS"
if echo "$STATS" | grep -q '"backend":"surrealdb"'; then
    echo "PASS: Backend is surrealdb"
else
    echo "FAIL: Backend is not surrealdb"
    exit 1
fi

# Test ingest
echo ""
echo "=== Test 3: Ingest Data ==="
INGEST=$(curl -s -X POST http://127.0.0.1:$PORT/v2/ingest \
    -H "Content-Type: application/json" \
    -d '{"content": "Test memory from bundled Python", "source": "bundled-test"}')
echo "$INGEST"
if echo "$INGEST" | grep -q '"resource_id"'; then
    echo "PASS: Ingest succeeded"
else
    echo "FAIL: Ingest failed"
    exit 1
fi

# Test list resources
echo ""
echo "=== Test 4: List Resources ==="
RESOURCES=$(curl -s http://127.0.0.1:$PORT/v2/resources)
echo "$RESOURCES"
if echo "$RESOURCES" | grep -q '"content":"Test memory from bundled Python"'; then
    echo "PASS: Data persisted and retrieved"
else
    echo "FAIL: Data not found"
    exit 1
fi

echo ""
echo "=== All Tests Passed ==="
echo "Bundled Python is ready for Tauri integration!"
